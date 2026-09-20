"""Synthetic process telemetry, line events, and cost ledger.

SYNTHETIC DEMONSTRATION DATA. The organizer dataset contains images only, so
every process/economic signal here is generated. It is never presented as
organizer-derived; the API labels it and the UI shows it as such.

Design intent: the causal structure is *constructed*, so the attribution layer
can be validated against known ground truth rather than merely asserted. Some
variables are deliberately correlated-but-not-causal so the attribution engine
has to distinguish them.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ai.data import CLASSES

STATIONS = [
    {"id": "S1", "name": "Stamping",       "nominal_cycle_s": 12.0},
    {"id": "S2", "name": "Heat Treatment", "nominal_cycle_s": 18.0},
    {"id": "S3", "name": "Surface Finish", "nominal_cycle_s": 15.0},
    {"id": "S4", "name": "Coating",        "nominal_cycle_s": 14.0},
    {"id": "S5", "name": "Inspection",     "nominal_cycle_s": 9.0},
]

# name -> (station, nominal, sigma, unit)
PROCESS_FEATURES = {
    "press_force_kn":        ("S1", 420.0, 25.0, "kN"),
    "feed_rate_mm_s":        ("S1", 85.0, 6.0, "mm/s"),
    "pot_temperature_c":     ("S2", 245.0, 8.0, "°C"),
    "dwell_time_s":          ("S2", 18.0, 1.5, "s"),
    "abrasive_wear_index":   ("S3", 0.35, 0.10, "index"),
    "spindle_rpm":           ("S3", 9500.0, 450.0, "rpm"),
    "coating_thickness_um":  ("S4", 62.0, 5.0, "µm"),
    "chamber_humidity_pct":  ("S4", 41.0, 6.0, "%"),
    "ambient_temperature_c": ("--", 23.0, 2.5, "°C"),
    "line_speed_units_hr":   ("--", 240.0, 15.0, "units/hr"),
}

# Ground-truth causal structure: defect -> {feature: z-shift}. Only these
# features actually move the label. Everything else is nuisance.
CAUSAL_STRUCTURE = {
    "crack":   {"press_force_kn": +2.1, "pot_temperature_c": -1.8},
    "hole":    {"feed_rate_mm_s": +2.3, "press_force_kn": -1.4},
    "rust":    {"chamber_humidity_pct": +2.4, "coating_thickness_um": -1.7},
    "scratch": {"abrasive_wear_index": +2.2, "spindle_rpm": +1.5},
    "normal":  {},
}


@dataclass
class SyntheticPlant:
    seed: int = 1337
    n_parts: int = 6000
    rng: np.random.Generator = field(init=False)

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)

    def telemetry(self) -> pd.DataFrame:
        labels = self.rng.choice(CLASSES, size=self.n_parts)
        rows = {}

        for feature, (_station, nominal, sigma, _unit) in PROCESS_FEATURES.items():
            values = self.rng.normal(nominal, sigma, self.n_parts)
            for defect, shifts in CAUSAL_STRUCTURE.items():
                if feature in shifts:
                    mask = labels == defect
                    values[mask] += shifts[feature] * sigma
            rows[feature] = values

        # Ambient temperature tracks chamber humidity: a genuine correlate of
        # rust that is not a cause of it. The attribution engine should rank it
        # below humidity, and we assert exactly that in validate_attribution().
        rows["ambient_temperature_c"] += 0.45 * (
            rows["chamber_humidity_pct"] - PROCESS_FEATURES["chamber_humidity_pct"][1]
        )

        df = pd.DataFrame(rows)
        df["defect_class"] = labels
        df["part_id"] = [f"P-{i:06d}" for i in range(self.n_parts)]
        df["batch_id"] = [f"B-{i // 500:03d}" for i in range(self.n_parts)]
        df["station_of_origin"] = [
            next((PROCESS_FEATURES[f][0] for f in CAUSAL_STRUCTURE.get(lbl, {})), "--")
            for lbl in labels
        ]
        return df

    def line_state(self) -> dict:
        """ILLUSTRATIVE. Station utilisation, buffers, and the active constraint."""
        rng = np.random.default_rng(self.seed + 1)
        stations = []
        for station in STATIONS:
            cycle = station["nominal_cycle_s"] * rng.uniform(0.95, 1.35)
            stations.append({
                **station,
                "actual_cycle_s": round(cycle, 2),
                "utilisation": round(min(cycle / 20.0, 0.99), 3),
                "buffer_level": int(rng.integers(0, 40)),
                "starved_pct": round(float(rng.uniform(0, 18)), 2),
                "blocked_pct": round(float(rng.uniform(0, 22)), 2),
            })

        constraint = max(stations, key=lambda s: s["actual_cycle_s"])
        takt = max(s["actual_cycle_s"] for s in stations)
        return {
            "stations": stations,
            "bottleneck_station_id": constraint["id"],
            "bottleneck_reason": (
                f"{constraint['name']} holds the longest actual cycle time "
                f"({constraint['actual_cycle_s']}s vs {constraint['nominal_cycle_s']}s nominal), "
                f"setting line takt and starving downstream stations."
            ),
            "line_throughput_units_hr": round(3600.0 / takt, 1),
            "theoretical_throughput_units_hr": round(
                3600.0 / max(s["nominal_cycle_s"] for s in STATIONS), 1
            ),
            "data_provenance": "SYNTHETIC_DEMONSTRATION",
        }


COST_MODEL = {
    "unit_sale_price": 42.00,
    "raw_material_cost": 11.50,
    "value_added_per_station": 3.20,
    "scrap_disposal_cost": 1.80,
    "rework_cost": 6.40,
    "energy_cost_per_unit": 2.10,
    "labour_cost_per_unit": 4.75,
}


def unit_economics(defect_rate: float, throughput_units_hr: float, rework_fraction: float = 0.35) -> dict:
    """ILLUSTRATIVE. Margin per shift under a given defect rate."""
    c = COST_MODEL
    shift_hours = 8.0
    units = throughput_units_hr * shift_hours

    defective = units * defect_rate
    good = units - defective
    reworked = defective * rework_fraction
    scrapped = defective - reworked

    revenue = (good + reworked) * c["unit_sale_price"]
    variable = units * (
        c["raw_material_cost"]
        + c["value_added_per_station"] * len(STATIONS)
        + c["energy_cost_per_unit"]
        + c["labour_cost_per_unit"]
    )
    penalties = scrapped * c["scrap_disposal_cost"] + reworked * c["rework_cost"]
    margin = revenue - variable - penalties

    return {
        "units_produced": round(units, 1),
        "good_units": round(good, 1),
        "reworked_units": round(reworked, 1),
        "scrapped_units": round(scrapped, 1),
        "revenue": round(revenue, 2),
        "variable_cost": round(variable, 2),
        "quality_penalties": round(penalties, 2),
        "net_margin_per_shift": round(margin, 2),
        "margin_per_unit": round(margin / max(units, 1), 3),
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }


def bottleneck_recommendation(line_state: dict, defect_rate: float = 0.08) -> dict:
    """A synthesized recommendation, not a raw metric: given the current
    bottleneck, estimate the cycle-time reduction needed to bring it to
    nominal, project the resulting throughput, and quantify the margin
    impact -- tying Layer 2B (flow) to Layer 4 (economics) into one advisory,
    which is the actual point of a "unified" decision-support system.
    """
    stations = {s["id"]: s for s in line_state["stations"]}
    bottleneck = stations[line_state["bottleneck_station_id"]]
    excess_s = bottleneck["actual_cycle_s"] - bottleneck["nominal_cycle_s"]

    if excess_s <= 0.01:
        return {
            "action": "No intervention recommended",
            "rationale": "The current bottleneck is already running at or below its nominal cycle time.",
            "data_provenance": "SYNTHETIC_DEMONSTRATION",
        }

    # Recommend closing 70% of the gap to nominal -- full closure is rarely
    # achievable in one pass on a real line; this is a defensible, stated
    # assumption rather than an unexplained number.
    target_reduction_pct = round(100 * 0.7 * excess_s / bottleneck["actual_cycle_s"], 1)
    new_cycle_s = bottleneck["actual_cycle_s"] * (1 - target_reduction_pct / 100)

    other_cycles = [s["actual_cycle_s"] for s in stations.values() if s["id"] != bottleneck["id"]]
    new_takt = max(new_cycle_s, *other_cycles) if other_cycles else new_cycle_s
    new_throughput = round(3600.0 / new_takt, 1)

    before = unit_economics(defect_rate, line_state["line_throughput_units_hr"])
    after = unit_economics(defect_rate, new_throughput)
    margin_delta = round(after["net_margin_per_shift"] - before["net_margin_per_shift"], 2)

    return {
        "action": (
            f"Reduce {bottleneck['name']} cycle time by {target_reduction_pct}% "
            f"({bottleneck['actual_cycle_s']}s -> {round(new_cycle_s, 1)}s)"
        ),
        "target_station_id": bottleneck["id"],
        "rationale": (
            f"{bottleneck['name']} exceeds its nominal cycle time by {round(excess_s, 1)}s, "
            f"setting line takt and starving downstream stations. Closing most of that gap "
            f"raises throughput and, at the current defect rate, increases margin."
        ),
        "current_throughput_units_hr": line_state["line_throughput_units_hr"],
        "projected_throughput_units_hr": new_throughput,
        "throughput_delta_pct": round(100 * (new_throughput / line_state["line_throughput_units_hr"] - 1), 1),
        "projected_margin_delta_per_shift": margin_delta,
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }


def best_counterfactual(defect_rate: float, throughput: float) -> dict:
    """Grid-search the intervention space and return the margin-maximizing
    one as a recommendation, instead of making the operator find it by
    dragging sliders themselves.
    """
    speed_options = range(-20, 21, 4)
    # Speed and defect rate are coupled in reality (a faster line runs hotter,
    # tighter tolerances, more misses), so only test pairs that respect that
    # trade-off: slower-with-fewer-defects or faster-with-more-defects, not
    # both improving for free. This mirrors the architecture doc's own worked
    # example (reduced feed rate -> lower micro-cracking, at a speed cost).
    defect_options_for = lambda speed_delta: (  # noqa: E731
        range(-40, 1, 10) if speed_delta <= 0 else range(0, 41, 10)
    )

    best = None
    for speed_delta in speed_options:
        for defect_delta in defect_options_for(speed_delta):
            result = counterfactual(defect_rate, throughput, speed_delta, defect_delta)
            if best is None or result["margin_delta_per_shift"] > best["margin_delta_per_shift"]:
                best = {**result, "speed_delta_pct": speed_delta, "defect_rate_delta_pct": defect_delta}

    if best["margin_delta_per_shift"] <= 0:
        return {
            "action": "No intervention in the tested range improves margin",
            "rationale": "Every evaluated combination of speed and defect-rate change reduced margin versus baseline.",
            "data_provenance": "SYNTHETIC_DEMONSTRATION",
        }

    direction = "Increase" if best["speed_delta_pct"] > 0 else "Decrease"
    return {
        "action": (
            f"{direction} line speed by {abs(best['speed_delta_pct'])}% "
            f"with a {best['defect_rate_delta_pct']:+d}% defect-rate change"
        ),
        "rationale": (
            f"Of the interventions evaluated, this combination yields the largest margin gain: "
            f"{best['margin_delta_per_shift']:+.2f}/shift versus baseline."
        ),
        "speed_delta_pct": best["speed_delta_pct"],
        "defect_rate_delta_pct": best["defect_rate_delta_pct"],
        "projected_margin_delta_per_shift": best["margin_delta_per_shift"],
        "baseline": best["baseline"],
        "intervened": best["intervened"],
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }


def counterfactual(defect_rate: float, throughput: float, speed_delta_pct: float,
                   defect_rate_delta_pct: float) -> dict:
    """ILLUSTRATIVE. Trade a line-speed change against its quality effect."""
    baseline = unit_economics(defect_rate, throughput)
    new_rate = max(0.0, defect_rate * (1 + defect_rate_delta_pct / 100.0))
    new_throughput = throughput * (1 + speed_delta_pct / 100.0)
    intervened = unit_economics(new_rate, new_throughput)

    delta = intervened["net_margin_per_shift"] - baseline["net_margin_per_shift"]
    return {
        "baseline": baseline,
        "intervened": intervened,
        "margin_delta_per_shift": round(delta, 2),
        "recommendation": "ADOPT" if delta > 0 else "REJECT",
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }
