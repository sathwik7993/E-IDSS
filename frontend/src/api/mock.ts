// Mock data matching the API contract exactly, used as a fallback whenever
// the backend is unreachable so every view can render standalone during dev/demo.

import type {
  HealthResponse,
  InspectResponse,
  MetricsResponse,
  RootCauseResponse,
  RootCauseValidationResponse,
  LineStateResponse,
  EconomicsResponse,
  CounterfactualRequest,
  CounterfactualResponse,
  LineRecommendationResponse,
  EconomicsRecommendationResponse,
} from "../types/api";

// 1x1 transparent PNG, base64, no data-URI prefix — placeholder only.
const BLANK_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

export const mockHealth: HealthResponse = {
  status: "ok",
  model_loaded: true,
  stub_mode: true,
  device: "cpu",
};

export const CLASSES = ["crack", "hole", "normal", "rust", "scratch"] as const;

export function mockInspect(): InspectResponse {
  const probs: Record<string, number> = {
    crack: 0.62,
    hole: 0.09,
    normal: 0.05,
    rust: 0.11,
    scratch: 0.13,
  };
  return {
    part_id: `MOCK-${Math.floor(Math.random() * 100000)}`,
    predicted_class: "crack",
    is_defective: true,
    calibrated_confidence: 0.62,
    raw_confidence: 0.74,
    epistemic_uncertainty: 0.18,
    mahalanobis_distance: 3.4,
    novel_or_uncertain: false,
    decision: "AUTO",
    class_probabilities: probs,
    heatmap_png_base64: BLANK_PNG_B64,
    overlay_png_base64: BLANK_PNG_B64,
    bbox: {
      x: 40,
      y: 30,
      width: 120,
      height: 80,
      image_width: 224,
      image_height: 224,
      coverage: 0.19,
      peak_x: 96,
      peak_y: 62,
      peak_activation: 0.97,
      n_components: 2,
      threshold: 0.5,
    },
    stub_mode: true,
    data_provenance: "MODEL_INFERENCE",
  };
}

export function mockInspectUncertain(): InspectResponse {
  const base = mockInspect();
  return {
    ...base,
    predicted_class: "rust",
    is_defective: true,
    calibrated_confidence: 0.41,
    raw_confidence: 0.48,
    epistemic_uncertainty: 0.63,
    mahalanobis_distance: 9.8,
    novel_or_uncertain: true,
    decision: "DEFER_TO_HUMAN",
    class_probabilities: {
      crack: 0.22,
      hole: 0.18,
      normal: 0.09,
      rust: 0.41,
      scratch: 0.1,
    },
  };
}

export const mockMetrics: MetricsResponse = {
  clean_test: {
    accuracy: 0.94,
    macro_f1: 0.92,
  },
  robustness: {
    low_light: { accuracy: 0.88, macro_f1: 0.85, false_accept_rate: 0.04, false_reject_rate: 0.08 },
    blur: { accuracy: 0.83, macro_f1: 0.8, false_accept_rate: 0.06, false_reject_rate: 0.11 },
    glare: { accuracy: 0.79, macro_f1: 0.76, false_accept_rate: 0.09, false_reject_rate: 0.14 },
  },
};

export function mockRootCause(defect_class: string): RootCauseResponse {
  return {
    defect_class,
    drivers: [
      {
        feature: "roller_pressure",
        station: "Station 2 - Forming",
        observed: 142.5,
        nominal: 120,
        unit: "PSI",
        deviation_sigma: 3.1,
        shap_value: 0.41,
        attribution_pct: 38,
        direction: "above",
      },
      {
        feature: "coolant_temp",
        station: "Station 3 - Cooling",
        observed: 68.2,
        nominal: 55,
        unit: "°C",
        deviation_sigma: 2.4,
        shap_value: 0.29,
        attribution_pct: 27,
        direction: "above",
      },
      {
        feature: "line_speed",
        station: "Station 1 - Feed",
        observed: 1.8,
        nominal: 1.5,
        unit: "m/s",
        deviation_sigma: 1.6,
        shap_value: 0.18,
        attribution_pct: 17,
        direction: "above",
      },
      {
        feature: "die_wear_index",
        station: "Station 2 - Forming",
        observed: 0.71,
        nominal: 0.4,
        unit: "index",
        deviation_sigma: 1.2,
        shap_value: 0.12,
        attribution_pct: 11,
        direction: "above",
      },
      {
        feature: "ambient_humidity",
        station: "Station 4 - Finishing",
        observed: 58,
        nominal: 45,
        unit: "%RH",
        deviation_sigma: 0.9,
        shap_value: 0.07,
        attribution_pct: 7,
        direction: "above",
      },
    ],
    narrative: `Elevated ${defect_class} rates are most strongly attributed to roller pressure running 3.1σ above nominal at Station 2 (Forming), compounded by coolant temperature deviation at Station 3.`,
    data_provenance: "SYNTHETIC_DEMONSTRATION",
  };
}

export const mockRootCauseValidation: RootCauseValidationResponse = {
  crack: {
    true_drivers: ["roller_pressure", "die_wear_index"],
    top_ranked: ["roller_pressure", "coolant_temp", "die_wear_index"],
    recovered: ["roller_pressure", "die_wear_index"],
    recall: 1.0,
  },
  rust: {
    true_drivers: ["ambient_humidity", "coolant_temp"],
    top_ranked: ["coolant_temp", "line_speed", "ambient_humidity"],
    recovered: ["coolant_temp", "ambient_humidity"],
    recall: 1.0,
  },
  scratch: {
    true_drivers: ["line_speed", "die_wear_index"],
    top_ranked: ["die_wear_index", "roller_pressure"],
    recovered: ["die_wear_index"],
    recall: 0.5,
  },
  hole: {
    true_drivers: ["roller_pressure"],
    top_ranked: ["roller_pressure", "coolant_temp"],
    recovered: ["roller_pressure"],
    recall: 1.0,
  },
  confounder_check: {
    shift_id_excluded: true,
    operator_id_excluded: true,
    note: "Nuisance/confounder features (shift id, operator id, timestamp) were excluded from top-ranked attributions in all validation runs.",
  },
  mean_recall: 0.875,
};

export const mockLineState: LineStateResponse = {
  stations: [
    { id: "s1", name: "Feed", nominal_cycle_s: 12, actual_cycle_s: 12.4, utilisation: 0.86, buffer_level: 0.62, starved_pct: 0.03, blocked_pct: 0.01 },
    { id: "s2", name: "Forming", nominal_cycle_s: 14, actual_cycle_s: 18.9, utilisation: 0.98, buffer_level: 0.91, starved_pct: 0.01, blocked_pct: 0.22 },
    { id: "s3", name: "Cooling", nominal_cycle_s: 10, actual_cycle_s: 10.6, utilisation: 0.79, buffer_level: 0.44, starved_pct: 0.08, blocked_pct: 0.02 },
    { id: "s4", name: "Finishing", nominal_cycle_s: 11, actual_cycle_s: 11.2, utilisation: 0.81, buffer_level: 0.38, starved_pct: 0.06, blocked_pct: 0.0 },
    { id: "s5", name: "Inspection", nominal_cycle_s: 9, actual_cycle_s: 9.3, utilisation: 0.7, buffer_level: 0.25, starved_pct: 0.12, blocked_pct: 0.0 },
  ],
  bottleneck_station_id: "s2",
  bottleneck_reason:
    "Station 2 (Forming) actual cycle time is 35% above nominal and utilisation is saturated at 98%, causing downstream starvation and upstream blocking.",
  line_throughput_units_hr: 190,
  theoretical_throughput_units_hr: 257,
  data_provenance: "SYNTHETIC_DEMONSTRATION",
};

export function mockEconomics(defect_rate = 0.08, throughput = 240): EconomicsResponse {
  const units_produced = throughput;
  const scrapped_units = Math.round(units_produced * defect_rate * 0.4);
  const reworked_units = Math.round(units_produced * defect_rate * 0.6);
  const good_units = units_produced - scrapped_units - reworked_units;
  const revenue = good_units * 48 + reworked_units * 30;
  const variable_cost = units_produced * 22;
  const quality_penalties = scrapped_units * 18 + reworked_units * 6;
  const net_margin_per_shift = revenue - variable_cost - quality_penalties;
  return {
    units_produced,
    good_units,
    reworked_units,
    scrapped_units,
    revenue,
    variable_cost,
    quality_penalties,
    net_margin_per_shift,
    margin_per_unit: net_margin_per_shift / units_produced,
    data_provenance: "SYNTHETIC_DEMONSTRATION",
  };
}

export function mockCounterfactual(req: CounterfactualRequest): CounterfactualResponse {
  const baseline = mockEconomics(req.defect_rate, req.throughput);
  const newThroughput = req.throughput * (1 + req.speed_delta_pct / 100);
  const newDefectRate = Math.max(
    0,
    req.defect_rate * (1 + req.defect_rate_delta_pct / 100)
  );
  const intervened = mockEconomics(newDefectRate, newThroughput);
  const margin_delta_per_shift =
    intervened.net_margin_per_shift - baseline.net_margin_per_shift;
  return {
    baseline,
    intervened,
    margin_delta_per_shift,
    recommendation: margin_delta_per_shift > 0 ? "ADOPT" : "REJECT",
    data_provenance: "SYNTHETIC_DEMONSTRATION",
  };
}

export function mockLineRecommendation(): LineRecommendationResponse {
  return {
    action: "Reduce Forming cycle time by 24.5% (18.9s -> 14.3s)",
    target_station_id: "s2",
    rationale:
      "Forming exceeds its nominal cycle time by 4.9s, setting line takt and starving downstream stations. Closing most of that gap raises throughput and, at the current defect rate, increases margin.",
    current_throughput_units_hr: mockLineState.line_throughput_units_hr,
    projected_throughput_units_hr: 232,
    throughput_delta_pct: 22.1,
    projected_margin_delta_per_shift: 940.5,
    data_provenance: "SYNTHETIC_DEMONSTRATION",
  };
}

export function mockEconomicsRecommendation(
  defect_rate = 0.08,
  throughput = 240
): EconomicsRecommendationResponse {
  const baseline = mockEconomics(defect_rate, throughput);
  const intervened = mockEconomics(defect_rate, throughput * 1.2);
  return {
    action: "Increase line speed by 20% with a +0% defect-rate change",
    rationale:
      "Of the interventions evaluated, this combination yields the largest margin gain versus baseline.",
    speed_delta_pct: 20,
    defect_rate_delta_pct: 0,
    projected_margin_delta_per_shift:
      intervened.net_margin_per_shift - baseline.net_margin_per_shift,
    baseline,
    intervened,
    data_provenance: "SYNTHETIC_DEMONSTRATION",
  };
}
