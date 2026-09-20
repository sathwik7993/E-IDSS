"""Root-cause attribution over process telemetry.

A LightGBM multiclass model maps process parameters to defect class; TreeSHAP
explains individual predictions. Because ml.synthetic constructs the causal
structure, validate_attribution() can check that SHAP recovers the true drivers
and correctly ranks a non-causal correlate below its causal parent. That turns
attribution quality into something measured rather than asserted.
"""

import numpy as np
import pandas as pd
from scipy import stats

from ai.data import CLASSES
from ai.synthetic import CAUSAL_STRUCTURE, PROCESS_FEATURES, SyntheticPlant

FEATURE_NAMES = list(PROCESS_FEATURES.keys())


class RootCauseEngine:
    def __init__(self, seed: int = 1337):
        self.seed = seed
        self.model = None
        self.explainer = None
        self.baseline = None
        self.telemetry = None

    def fit(self, n_parts: int = 6000):
        import lightgbm as lgb
        import shap

        self.telemetry = SyntheticPlant(seed=self.seed, n_parts=n_parts).telemetry()
        X = self.telemetry[FEATURE_NAMES]
        y = self.telemetry["defect_class"].map({c: i for i, c in enumerate(CLASSES)})

        self.model = lgb.LGBMClassifier(
            objective="multiclass",
            num_class=len(CLASSES),
            n_estimators=350,
            learning_rate=0.06,
            num_leaves=31,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=self.seed,
            verbose=-1,
        ).fit(X, y)

        self.explainer = shap.TreeExplainer(self.model)
        self.baseline = X.median().to_dict()
        return self

    def _shap_for(self, X: pd.DataFrame, class_idx: int) -> np.ndarray:
        values = self.explainer.shap_values(X)
        # shap returns either a list per class or a (n, features, classes) array
        if isinstance(values, list):
            return np.asarray(values[class_idx])
        values = np.asarray(values)
        return values[..., class_idx] if values.ndim == 3 else values

    def attribute(self, observation: dict, defect_class: str, top_k: int = 4) -> dict:
        """Attribute one part's defect to its process parameters."""
        class_idx = CLASSES.index(defect_class)
        X = pd.DataFrame([{f: observation.get(f, self.baseline[f]) for f in FEATURE_NAMES}])
        contributions = self._shap_for(X, class_idx)[0]

        total = np.abs(contributions).sum()
        ranked = sorted(
            range(len(FEATURE_NAMES)), key=lambda i: abs(contributions[i]), reverse=True
        )[:top_k]

        drivers = []
        for i in ranked:
            name = FEATURE_NAMES[i]
            station, nominal, sigma, unit = PROCESS_FEATURES[name]
            observed = float(X.iloc[0][name])
            drivers.append({
                "feature": name,
                "station": station,
                "observed": round(observed, 2),
                "nominal": nominal,
                "unit": unit,
                "deviation_sigma": round((observed - nominal) / sigma, 2),
                "shap_value": round(float(contributions[i]), 4),
                "attribution_pct": round(100 * abs(contributions[i]) / max(total, 1e-9), 1),
                "direction": "above" if observed > nominal else "below",
            })

        return {
            "defect_class": defect_class,
            "drivers": drivers,
            "narrative": self._narrative(defect_class, drivers),
            "data_provenance": "SYNTHETIC_DEMONSTRATION",
        }

    @staticmethod
    def _narrative(defect_class: str, drivers: list) -> str:
        if not drivers:
            return f"No process parameter deviated materially for {defect_class}."
        lead = drivers[0]
        text = (
            f"{defect_class.capitalize()} attributed primarily to "
            f"{lead['feature'].replace('_', ' ')} at station {lead['station']}, "
            f"observed {lead['observed']}{lead['unit']} versus {lead['nominal']}{lead['unit']} nominal "
            f"({lead['deviation_sigma']:+.2f}σ, {lead['attribution_pct']}% attribution)."
        )
        if len(drivers) > 1:
            second = drivers[1]
            text += (
                f" Secondary contribution from {second['feature'].replace('_', ' ')} "
                f"at {second['station']} ({second['deviation_sigma']:+.2f}σ, "
                f"{second['attribution_pct']}%)."
            )
        return text

    def validate_attribution(self) -> dict:
        """Does SHAP recover the causal structure we constructed?"""
        X = self.telemetry[FEATURE_NAMES]
        results = {}

        for defect, truth in CAUSAL_STRUCTURE.items():
            if not truth:
                continue
            class_idx = CLASSES.index(defect)
            mask = (self.telemetry["defect_class"] == defect).to_numpy()
            contributions = self._shap_for(X[mask], class_idx)
            mean_abs = np.abs(contributions).mean(axis=0)
            ranked = [FEATURE_NAMES[i] for i in np.argsort(-mean_abs)]

            true_drivers = set(truth)
            recovered = len(true_drivers & set(ranked[: len(true_drivers)]))
            results[defect] = {
                "true_drivers": sorted(true_drivers),
                "top_ranked": ranked[: len(true_drivers)],
                "recovered": recovered,
                "recall": round(recovered / len(true_drivers), 3),
            }

        # The confounder check: ambient temperature correlates with rust via
        # humidity but does not cause it, so it must rank below humidity.
        rust_rank = results.get("rust", {}).get("top_ranked", [])
        full_rust = self._shap_for(
            X[(self.telemetry["defect_class"] == "rust").to_numpy()], CLASSES.index("rust")
        )
        order = [FEATURE_NAMES[i] for i in np.argsort(-np.abs(full_rust).mean(axis=0))]
        results["confounder_check"] = {
            "correlate": "ambient_temperature_c",
            "causal_parent": "chamber_humidity_pct",
            "humidity_rank": order.index("chamber_humidity_pct") + 1,
            "ambient_rank": order.index("ambient_temperature_c") + 1,
            "correctly_ranked": order.index("chamber_humidity_pct") < order.index("ambient_temperature_c"),
        }
        results["mean_recall"] = round(
            float(np.mean([v["recall"] for k, v in results.items() if isinstance(v, dict) and "recall" in v])), 3
        )
        return results

    def detect_drift(self, batch_id: str) -> dict:
        """KS-test each parameter in one batch against the remaining population."""
        batch = self.telemetry[self.telemetry["batch_id"] == batch_id]
        rest = self.telemetry[self.telemetry["batch_id"] != batch_id]
        findings = []

        for name in FEATURE_NAMES:
            statistic, p_value = stats.ks_2samp(batch[name], rest[name])
            if p_value < 0.05:
                findings.append({
                    "feature": name,
                    "station": PROCESS_FEATURES[name][0],
                    "ks_statistic": round(float(statistic), 4),
                    "p_value": float(f"{p_value:.3e}"),
                    "batch_mean": round(float(batch[name].mean()), 2),
                    "population_mean": round(float(rest[name].mean()), 2),
                })

        findings.sort(key=lambda f: -f["ks_statistic"])
        return {
            "batch_id": batch_id,
            "n_parts": len(batch),
            "drifted_features": findings,
            "drift_detected": bool(findings),
            "data_provenance": "SYNTHETIC_DEMONSTRATION",
        }
