"""Operational telemetry, TreeSHAP attribution, line health and financial impact.

Ported from the defect_detection prototype: the same eight machine parameters,
the same nominal envelopes, the same LightGBM + TreeSHAP attribution, and the
same station / remediation reference data. All of it is
SYNTHETIC_DEMONSTRATION -- the organizer dataset carries images only.
"""

import os
import pickle
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

DEFECT_CLASSES = ["crack", "hole", "normal", "rust", "scratch"]

TELEMETRY_SPECS = {
    "furnace_temp_c": {
        "label": "Furnace Temp",
        "unit": "°C",
        "nominal_min": 820.0,
        "nominal_max": 860.0,
        "desc": "Annealing furnace temperature",
        "step": 1.0,
    },
    "roller_pressure_bar": {
        "label": "Roller Pressure",
        "unit": "bar",
        "nominal_min": 140.0,
        "nominal_max": 160.0,
        "desc": "Continuous rolling force",
        "step": 1.0,
    },
    "line_speed_mpm": {
        "label": "Line Speed",
        "unit": "m/min",
        "nominal_min": 45.0,
        "nominal_max": 55.0,
        "desc": "Strip processing throughput",
        "step": 1.0,
    },
    "lubricant_flow_lph": {
        "label": "Lubricant Flow",
        "unit": "L/h",
        "nominal_min": 28.0,
        "nominal_max": 36.0,
        "desc": "Protective lubricant / cooling emulsion rate",
        "step": 1.0,
    },
    "vibration_rms_mms": {
        "label": "Vibration RMS",
        "unit": "mm/s",
        "nominal_min": 1.0,
        "nominal_max": 2.4,
        "desc": "Spindle and roller bearing vibration",
        "step": 0.1,
    },
    "ambient_humidity_pct": {
        "label": "Ambient Humidity",
        "unit": "%",
        "nominal_min": 35.0,
        "nominal_max": 52.0,
        "desc": "Bay atmospheric humidity",
        "step": 1.0,
    },
    "cooling_rate_cps": {
        "label": "Cooling Rate",
        "unit": "°C/s",
        "nominal_min": 14.0,
        "nominal_max": 20.0,
        "desc": "Quench chamber cooling gradient",
        "step": 1.0,
    },
    "tension_variation_kn": {
        "label": "Tension Variation",
        "unit": "kN",
        "nominal_min": 0.2,
        "nominal_max": 0.9,
        "desc": "Strip coiling tension instability",
        "step": 0.1,
    },
}

FEATURE_COLS = list(TELEMETRY_SPECS.keys())

NOMINAL_TELEMETRY = {
    "furnace_temp_c": 842.0,
    "roller_pressure_bar": 151.0,
    "line_speed_mpm": 50.2,
    "lubricant_flow_lph": 32.1,
    "vibration_rms_mms": 1.6,
    "ambient_humidity_pct": 43.5,
    "cooling_rate_cps": 17.2,
    "tension_variation_kn": 0.52,
}

# Certified incident records offered as presets in the telemetry sidebar.
PRESET_UNITS = [
    {
        "id": "UNIT-10492",
        "label": "UNIT-10492 (Crack Mode: High Thermal Gradient & Pressure)",
        "telemetry": {
            "furnace_temp_c": 915.0,
            "roller_pressure_bar": 184.5,
            "line_speed_mpm": 52.0,
            "lubricant_flow_lph": 29.0,
            "vibration_rms_mms": 1.8,
            "ambient_humidity_pct": 45.0,
            "cooling_rate_cps": 28.4,
            "tension_variation_kn": 1.95,
        },
    },
    {
        "id": "UNIT-10814",
        "label": "UNIT-10814 (Scratch Mode: Spindle Bearing Vibration)",
        "telemetry": {
            "furnace_temp_c": 841.0,
            "roller_pressure_bar": 149.0,
            "line_speed_mpm": 68.5,
            "lubricant_flow_lph": 16.5,
            "vibration_rms_mms": 4.9,
            "ambient_humidity_pct": 42.0,
            "cooling_rate_cps": 16.8,
            "tension_variation_kn": 0.65,
        },
    },
    {
        "id": "UNIT-11029",
        "label": "UNIT-11029 (Hole Mode: Pressure Surge & Tension Fluctuation)",
        "telemetry": {
            "furnace_temp_c": 875.0,
            "roller_pressure_bar": 196.0,
            "line_speed_mpm": 48.0,
            "lubricant_flow_lph": 31.0,
            "vibration_rms_mms": 2.1,
            "ambient_humidity_pct": 40.0,
            "cooling_rate_cps": 18.0,
            "tension_variation_kn": 2.6,
        },
    },
    {
        "id": "UNIT-11440",
        "label": "UNIT-11440 (Rust Mode: Atmospheric Humidity Drift)",
        "telemetry": {
            "furnace_temp_c": 832.0,
            "roller_pressure_bar": 146.0,
            "line_speed_mpm": 34.0,
            "lubricant_flow_lph": 14.0,
            "vibration_rms_mms": 1.4,
            "ambient_humidity_pct": 82.5,
            "cooling_rate_cps": 15.0,
            "tension_variation_kn": 0.48,
        },
    },
    {
        "id": "UNIT-12001",
        "label": "UNIT-12001 (Normal Unit: Within Process Envelope)",
        "telemetry": dict(NOMINAL_TELEMETRY),
    },
]

# Machine settings the line was running when each defect mode was last observed.
# Drives the "Simulate from Detected Defect" telemetry source.
DEFECT_TELEMETRY_PROFILES = {
    "crack": {
        "furnace_temp_c": 918.0,
        "roller_pressure_bar": 182.0,
        "line_speed_mpm": 52.0,
        "lubricant_flow_lph": 28.5,
        "vibration_rms_mms": 1.9,
        "ambient_humidity_pct": 46.0,
        "cooling_rate_cps": 27.5,
        "tension_variation_kn": 1.85,
    },
    "scratch": {
        "furnace_temp_c": 842.0,
        "roller_pressure_bar": 148.0,
        "line_speed_mpm": 67.0,
        "lubricant_flow_lph": 17.0,
        "vibration_rms_mms": 4.6,
        "ambient_humidity_pct": 43.0,
        "cooling_rate_cps": 16.5,
        "tension_variation_kn": 0.60,
    },
    "hole": {
        "furnace_temp_c": 880.0,
        "roller_pressure_bar": 194.0,
        "line_speed_mpm": 49.0,
        "lubricant_flow_lph": 30.0,
        "vibration_rms_mms": 2.2,
        "ambient_humidity_pct": 41.0,
        "cooling_rate_cps": 18.0,
        "tension_variation_kn": 2.45,
    },
    "rust": {
        "furnace_temp_c": 830.0,
        "roller_pressure_bar": 145.0,
        "line_speed_mpm": 35.0,
        "lubricant_flow_lph": 15.0,
        "vibration_rms_mms": 1.3,
        "ambient_humidity_pct": 81.0,
        "cooling_rate_cps": 15.0,
        "tension_variation_kn": 0.45,
    },
    "normal": {
        "furnace_temp_c": 842.0,
        "roller_pressure_bar": 150.5,
        "line_speed_mpm": 50.1,
        "lubricant_flow_lph": 32.5,
        "vibration_rms_mms": 1.5,
        "ambient_humidity_pct": 44.0,
        "cooling_rate_cps": 17.0,
        "tension_variation_kn": 0.50,
    },
}

STATION_MATRIX = [
    {"station": "Station 01: Pre-Heat Furnace", "cycle_time_s": 42.0, "buffer_queue": 2, "utilisation_pct": 72.0, "bottleneck": False},
    {"station": "Station 02: Descaling Jet", "cycle_time_s": 24.5, "buffer_queue": 1, "utilisation_pct": 48.0, "bottleneck": False},
    {"station": "Station 03: Primary Rougher", "cycle_time_s": 38.0, "buffer_queue": 4, "utilisation_pct": 68.0, "bottleneck": False},
    {"station": "Station 04: Roll Mill [BOTTLENECK]", "cycle_time_s": 58.4, "buffer_queue": 18, "utilisation_pct": 98.5, "bottleneck": True},
    {"station": "Station 05: Quench Chamber", "cycle_time_s": 45.0, "buffer_queue": 3, "utilisation_pct": 78.0, "bottleneck": False},
    {"station": "Station 06: Inspection Optical", "cycle_time_s": 18.0, "buffer_queue": 0, "utilisation_pct": 32.0, "bottleneck": False},
]

BOTTLENECK_NOTICE = (
    "Station 04 (Roll Mill) currently presents an active buffer queue of 18 units with "
    "98.5% capacity utilization. Secondary thermal runaway induces micro-cracking downstream."
)

EXECUTIVE_KPIS = [
    {
        "tone": "danger",
        "label": "Active Bottleneck Station",
        "value": "Station 04: Roll Mill",
        "subtext": "Thermal and mechanical load exceed safety limits",
    },
    {
        "tone": "warning",
        "label": "Cycle Time Variance",
        "value": "+16.4 sec / unit",
        "subtext": "Line throughput throttled by 14.2% below design rating",
    },
    {
        "tone": "neutral",
        "label": "Projected Margin Impact",
        "value": "-$14,850 / day",
        "subtext": "Estimated scrap and rework loss ($92.40 / flagged unit)",
    },
    {
        "tone": "info",
        "label": "Overall Line Yield (OEE)",
        "value": "86.4% OEE",
        "subtext": "Quality: 92.1% | Availability: 95.8% | Performance: 97.9%",
    },
]

REMEDIATION_PLAN = [
    {
        "title": "1. Mechanical & Pressure Adjustments",
        "actions": [
            "Reduce Station 04 rolling force by **14.5 bar** (target: 152 bar).",
            "Inspect hydraulic servo valves for pressure spike dampening.",
            "Calibrate strip coiler tension oscillation dampener.",
        ],
    },
    {
        "title": "2. Thermal & Quench Calibration",
        "actions": [
            "Lower Annealing zone temperature setpoint by **22°C** to prevent grain embrittlement.",
            "Normalize quench cooling rate from 28.4°C/s to **18.0°C/s**.",
            "Recalibrate optical pyrometers at Station 04 inlet.",
        ],
    },
    {
        "title": "3. Lubrication & Maintenance Schedule",
        "actions": [
            "Increase emulsion flow by **6.5 L/h** on upper roll bearings.",
            "Replace high-vibration spindle bearing #2 (Vibration RMS > 4.5 mm/s).",
            "Execute descaling spray purge cycle prior to next lot transition.",
        ],
    },
]

OPERATING_DAYS_PER_MONTH = 26


def generate_synthetic_telemetry(csv_path: str, n_samples: int = 3500, seed: int = 42) -> pd.DataFrame:
    """Regenerate the telemetry table when the shipped CSV is unavailable.

    Same generator and seed as the prototype, so the reconstructed table is
    identical to the one checked in at data/process_parameters.csv.
    """
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)

    rng = np.random.RandomState(seed)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    records = []
    unit_idx = 10001
    for defect_label in DEFECT_CLASSES:
        for _ in range(n_samples // len(DEFECT_CLASSES)):
            unit_id = f"UNIT-{unit_idx}"
            unit_idx += 1
            line_id = rng.choice(["LINE-A", "LINE-B", "LINE-C"], p=[0.45, 0.35, 0.20])

            furnace_temp = rng.normal(840.0, 8.0)
            roller_pressure = rng.normal(150.0, 5.0)
            line_speed = rng.normal(50.0, 2.5)
            lubricant_flow = rng.normal(32.0, 2.0)
            vibration = rng.normal(1.6, 0.3)
            humidity = rng.normal(44.0, 4.0)
            cooling_rate = rng.normal(17.0, 1.5)
            tension_var = rng.normal(0.5, 0.15)

            # Physical root-cause structure -- the ground truth TreeSHAP has to recover.
            if defect_label == "crack":
                furnace_temp += rng.uniform(40.0, 90.0)
                cooling_rate += rng.uniform(8.0, 18.0)
                roller_pressure += rng.uniform(15.0, 35.0)
                tension_var += rng.uniform(0.6, 1.8)
            elif defect_label == "scratch":
                vibration += rng.uniform(2.2, 5.0)
                lubricant_flow -= rng.uniform(10.0, 20.0)
                line_speed += rng.uniform(8.0, 22.0)
            elif defect_label == "hole":
                roller_pressure += rng.uniform(30.0, 50.0)
                tension_var += rng.uniform(1.2, 2.5)
                furnace_temp += rng.uniform(25.0, 60.0)
            elif defect_label == "rust":
                humidity += rng.uniform(22.0, 45.0)
                lubricant_flow -= rng.uniform(12.0, 22.0)
                line_speed -= rng.uniform(10.0, 20.0)

            records.append({
                "unit_id": unit_id,
                "line_id": line_id,
                "furnace_temp_c": round(float(furnace_temp), 2),
                "roller_pressure_bar": round(float(roller_pressure), 2),
                "line_speed_mpm": round(float(line_speed), 2),
                "lubricant_flow_lph": round(max(5.0, float(lubricant_flow)), 2),
                "vibration_rms_mms": round(max(0.2, float(vibration)), 2),
                "ambient_humidity_pct": round(min(98.0, max(15.0, float(humidity))), 2),
                "cooling_rate_cps": round(max(4.0, float(cooling_rate)), 2),
                "tension_variation_kn": round(max(0.05, float(tension_var)), 2),
                "defect_class": defect_label,
            })

    df = pd.DataFrame(records).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df.to_csv(csv_path, index=False)
    return df


def train_attribution_bundle(csv_path: str, model_save_path: Optional[str] = None) -> Dict:
    """Fit the LightGBM telemetry classifier and its TreeSHAP explainer."""
    import lightgbm as lgb
    import shap
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split

    df = generate_synthetic_telemetry(csv_path)

    X = df[FEATURE_COLS]
    y = df["defect_class"]
    class_names = sorted(y.unique().tolist())
    class_to_idx = {name: i for i, name in enumerate(class_names)}
    y_encoded = y.map(class_to_idx)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    clf = lgb.LGBMClassifier(
        n_estimators=180,
        learning_rate=0.04,
        max_depth=5,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    ).fit(X_train, y_train)

    accuracy = float(accuracy_score(y_test, clf.predict(X_test)))
    report = classification_report(y_test, clf.predict(X_test), target_names=class_names, output_dict=True)

    bundle = {
        "model": clf,
        "explainer": shap.TreeExplainer(clf),
        "feature_cols": FEATURE_COLS,
        "class_names": class_names,
        "idx_to_class": {i: name for name, i in class_to_idx.items()},
        "test_accuracy": accuracy,
        "classification_report": report,
        "n_training_rows": int(len(df)),
    }

    if model_save_path:
        os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
        with open(model_save_path, "wb") as handle:
            pickle.dump(bundle, handle)
    return bundle


def explain_unit(unit_features: Union[Dict, pd.Series], bundle: Dict) -> Dict:
    """Local TreeSHAP attribution: which machine parameters drove this defect."""
    model = bundle["model"]
    explainer = bundle["explainer"]
    class_names = bundle["class_names"]
    idx_to_class = bundle["idx_to_class"]

    values = {col: float(unit_features.get(col, NOMINAL_TELEMETRY[col])) for col in FEATURE_COLS}
    df_unit = pd.DataFrame([values])

    pred_idx = int(model.predict(df_unit)[0])
    pred_class = idx_to_class[pred_idx]
    probs = model.predict_proba(df_unit)[0]
    probabilities = {class_names[i]: float(probs[i]) for i in range(len(class_names))}

    raw = explainer.shap_values(df_unit)
    if isinstance(raw, list):
        class_shap = raw[pred_idx][0]
    elif np.asarray(raw).ndim == 3:
        class_shap = np.asarray(raw)[0, :, pred_idx]
    else:
        class_shap = np.asarray(raw)[0]

    base_value = explainer.expected_value
    base_value = float(base_value[pred_idx]) if isinstance(base_value, (list, np.ndarray)) else float(base_value)

    contributions: List[Dict] = []
    out_of_spec: List[Dict] = []

    for i, col in enumerate(FEATURE_COLS):
        value = values[col]
        shap_value = float(class_shap[i])
        spec = TELEMETRY_SPECS[col]
        n_min, n_max = spec["nominal_min"], spec["nominal_max"]

        drift_status = "Nominal"
        if value > n_max:
            drift_pct = round(((value - n_max) / n_max) * 100, 1)
            drift_status = f"+{drift_pct}% High"
            out_of_spec.append({
                "feature": col, "label": spec["label"], "value": value, "unit": spec["unit"],
                "nominal_range": f"{n_min} - {n_max}", "status": "CRITICAL_HIGH", "drift_pct": drift_pct,
            })
        elif value < n_min:
            drift_pct = round(((n_min - value) / n_min) * 100, 1)
            drift_status = f"-{drift_pct}% Low"
            out_of_spec.append({
                "feature": col, "label": spec["label"], "value": value, "unit": spec["unit"],
                "nominal_range": f"{n_min} - {n_max}", "status": "CRITICAL_LOW", "drift_pct": drift_pct,
            })

        contributions.append({
            "feature": col,
            "label": spec["label"],
            "value": value,
            "unit": spec["unit"],
            "shap_value": shap_value,
            "abs_shap": abs(shap_value),
            "nominal_min": n_min,
            "nominal_max": n_max,
            "drift_status": drift_status,
        })

    contributions.sort(key=lambda c: c["abs_shap"], reverse=True)

    top_drivers = [
        f"{c['label']} ({c['value']}{c['unit']}, {c['drift_status']}) "
        f"{'increased' if c['shap_value'] > 0 else 'decreased'} {pred_class.upper()} "
        f"defect probability (SHAP impact: {c['shap_value']:+.3f})"
        for c in contributions[:3]
    ]

    return {
        "predicted_defect": pred_class,
        "confidence": probabilities[pred_class],
        "all_probabilities": probabilities,
        "base_value": base_value,
        "contributions": contributions,
        "out_of_spec_parameters": out_of_spec,
        "top_drivers": top_drivers,
        "raw_features": values,
        "model_test_accuracy": bundle["test_accuracy"],
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }


def financial_impact(daily_units: int, defect_rate_pct: float, scrap_cost_per_unit: float) -> Dict:
    flagged_units_daily = int(daily_units * (defect_rate_pct / 100.0))
    daily_loss = flagged_units_daily * scrap_cost_per_unit
    return {
        "daily_units": daily_units,
        "defect_rate_pct": defect_rate_pct,
        "scrap_cost_per_unit": scrap_cost_per_unit,
        "flagged_units_daily": flagged_units_daily,
        "daily_loss": round(daily_loss, 2),
        "operating_days_per_month": OPERATING_DAYS_PER_MONTH,
        "monthly_loss": round(daily_loss * OPERATING_DAYS_PER_MONTH, 2),
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }


def line_health() -> Dict:
    return {
        "stations": STATION_MATRIX,
        "bottleneck_notice": BOTTLENECK_NOTICE,
        "executive_kpis": EXECUTIVE_KPIS,
        "remediation_plan": REMEDIATION_PLAN,
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }
