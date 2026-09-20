// Offline mirrors of ai/telemetry.py so the telemetry, attribution and line
// health tabs still render when the backend is unreachable.

import type {
  TelemetrySpecsResponse,
  AttributionResponse,
  LineHealthResponse,
  FinancialImpactResponse,
  Telemetry,
  ShapContribution,
  OutOfSpecParameter,
} from "../types/api";

export const mockTelemetrySpecs: TelemetrySpecsResponse = {
  feature_cols: [
    "furnace_temp_c",
    "roller_pressure_bar",
    "line_speed_mpm",
    "lubricant_flow_lph",
    "vibration_rms_mms",
    "ambient_humidity_pct",
    "cooling_rate_cps",
    "tension_variation_kn",
  ],
  specs: {
    furnace_temp_c: { label: "Furnace Temp", unit: "°C", nominal_min: 820, nominal_max: 860, desc: "Annealing furnace temperature", step: 1 },
    roller_pressure_bar: { label: "Roller Pressure", unit: "bar", nominal_min: 140, nominal_max: 160, desc: "Continuous rolling force", step: 1 },
    line_speed_mpm: { label: "Line Speed", unit: "m/min", nominal_min: 45, nominal_max: 55, desc: "Strip processing throughput", step: 1 },
    lubricant_flow_lph: { label: "Lubricant Flow", unit: "L/h", nominal_min: 28, nominal_max: 36, desc: "Protective lubricant / cooling emulsion rate", step: 1 },
    vibration_rms_mms: { label: "Vibration RMS", unit: "mm/s", nominal_min: 1, nominal_max: 2.4, desc: "Spindle and roller bearing vibration", step: 0.1 },
    ambient_humidity_pct: { label: "Ambient Humidity", unit: "%", nominal_min: 35, nominal_max: 52, desc: "Bay atmospheric humidity", step: 1 },
    cooling_rate_cps: { label: "Cooling Rate", unit: "°C/s", nominal_min: 14, nominal_max: 20, desc: "Quench chamber cooling gradient", step: 1 },
    tension_variation_kn: { label: "Tension Variation", unit: "kN", nominal_min: 0.2, nominal_max: 0.9, desc: "Strip coiling tension instability", step: 0.1 },
  },
  nominal: {
    furnace_temp_c: 842, roller_pressure_bar: 151, line_speed_mpm: 50.2, lubricant_flow_lph: 32.1,
    vibration_rms_mms: 1.6, ambient_humidity_pct: 43.5, cooling_rate_cps: 17.2, tension_variation_kn: 0.52,
  },
  presets: [
    { id: "UNIT-10492", label: "UNIT-10492 (Crack Mode: High Thermal Gradient & Pressure)", telemetry: { furnace_temp_c: 915, roller_pressure_bar: 184.5, line_speed_mpm: 52, lubricant_flow_lph: 29, vibration_rms_mms: 1.8, ambient_humidity_pct: 45, cooling_rate_cps: 28.4, tension_variation_kn: 1.95 } },
    { id: "UNIT-10814", label: "UNIT-10814 (Scratch Mode: Spindle Bearing Vibration)", telemetry: { furnace_temp_c: 841, roller_pressure_bar: 149, line_speed_mpm: 68.5, lubricant_flow_lph: 16.5, vibration_rms_mms: 4.9, ambient_humidity_pct: 42, cooling_rate_cps: 16.8, tension_variation_kn: 0.65 } },
    { id: "UNIT-11029", label: "UNIT-11029 (Hole Mode: Pressure Surge & Tension Fluctuation)", telemetry: { furnace_temp_c: 875, roller_pressure_bar: 196, line_speed_mpm: 48, lubricant_flow_lph: 31, vibration_rms_mms: 2.1, ambient_humidity_pct: 40, cooling_rate_cps: 18, tension_variation_kn: 2.6 } },
    { id: "UNIT-11440", label: "UNIT-11440 (Rust Mode: Atmospheric Humidity Drift)", telemetry: { furnace_temp_c: 832, roller_pressure_bar: 146, line_speed_mpm: 34, lubricant_flow_lph: 14, vibration_rms_mms: 1.4, ambient_humidity_pct: 82.5, cooling_rate_cps: 15, tension_variation_kn: 0.48 } },
    { id: "UNIT-12001", label: "UNIT-12001 (Normal Unit: Within Process Envelope)", telemetry: { furnace_temp_c: 842, roller_pressure_bar: 151, line_speed_mpm: 50.2, lubricant_flow_lph: 32.1, vibration_rms_mms: 1.6, ambient_humidity_pct: 43.5, cooling_rate_cps: 17.2, tension_variation_kn: 0.52 } },
  ],
  defect_profiles: {
    crack: { furnace_temp_c: 918, roller_pressure_bar: 182, line_speed_mpm: 52, lubricant_flow_lph: 28.5, vibration_rms_mms: 1.9, ambient_humidity_pct: 46, cooling_rate_cps: 27.5, tension_variation_kn: 1.85 },
    scratch: { furnace_temp_c: 842, roller_pressure_bar: 148, line_speed_mpm: 67, lubricant_flow_lph: 17, vibration_rms_mms: 4.6, ambient_humidity_pct: 43, cooling_rate_cps: 16.5, tension_variation_kn: 0.6 },
    hole: { furnace_temp_c: 880, roller_pressure_bar: 194, line_speed_mpm: 49, lubricant_flow_lph: 30, vibration_rms_mms: 2.2, ambient_humidity_pct: 41, cooling_rate_cps: 18, tension_variation_kn: 2.45 },
    rust: { furnace_temp_c: 830, roller_pressure_bar: 145, line_speed_mpm: 35, lubricant_flow_lph: 15, vibration_rms_mms: 1.3, ambient_humidity_pct: 81, cooling_rate_cps: 15, tension_variation_kn: 0.45 },
    normal: { furnace_temp_c: 842, roller_pressure_bar: 150.5, line_speed_mpm: 50.1, lubricant_flow_lph: 32.5, vibration_rms_mms: 1.5, ambient_humidity_pct: 44, cooling_rate_cps: 17, tension_variation_kn: 0.5 },
  },
  model_test_accuracy: 1.0,
  n_training_rows: 3500,
  data_provenance: "SYNTHETIC_DEMONSTRATION",
};

// Offline stand-in for TreeSHAP: contribution magnitude tracks how far each
// parameter has drifted outside its nominal envelope. Directionally faithful
// to the model, but not the model -- callers surface it as mock data.
export function mockAttribution(telemetry: Telemetry): AttributionResponse {
  const { specs, feature_cols, nominal } = mockTelemetrySpecs;
  const contributions: ShapContribution[] = [];
  const outOfSpec: OutOfSpecParameter[] = [];

  for (const feature of feature_cols) {
    const spec = specs[feature];
    const value = telemetry[feature] ?? nominal[feature];
    const span = spec.nominal_max - spec.nominal_min;
    let drift = 0;
    let drift_status = "Nominal";

    if (value > spec.nominal_max) {
      const pct = Math.round(((value - spec.nominal_max) / spec.nominal_max) * 1000) / 10;
      drift_status = `+${pct}% High`;
      drift = (value - spec.nominal_max) / span;
      outOfSpec.push({ feature, label: spec.label, value, unit: spec.unit, nominal_range: `${spec.nominal_min} - ${spec.nominal_max}`, status: "CRITICAL_HIGH", drift_pct: pct });
    } else if (value < spec.nominal_min) {
      const pct = Math.round(((spec.nominal_min - value) / spec.nominal_min) * 1000) / 10;
      drift_status = `-${pct}% Low`;
      drift = (value - spec.nominal_min) / span;
      outOfSpec.push({ feature, label: spec.label, value, unit: spec.unit, nominal_range: `${spec.nominal_min} - ${spec.nominal_max}`, status: "CRITICAL_LOW", drift_pct: pct });
    }

    const shap_value = Math.round(drift * 1.4 * 1000) / 1000;
    contributions.push({
      feature, label: spec.label, value, unit: spec.unit,
      shap_value, abs_shap: Math.abs(shap_value),
      nominal_min: spec.nominal_min, nominal_max: spec.nominal_max, drift_status,
    });
  }

  contributions.sort((a, b) => b.abs_shap - a.abs_shap);

  const lead = contributions[0];
  const predicted =
    outOfSpec.length === 0
      ? "normal"
      : lead.feature === "ambient_humidity_pct"
        ? "rust"
        : lead.feature === "vibration_rms_mms"
          ? "scratch"
          : lead.feature === "tension_variation_kn"
            ? "hole"
            : "crack";

  const all_probabilities: Record<string, number> = {
    crack: 0.02, hole: 0.02, normal: 0.02, rust: 0.02, scratch: 0.02,
  };
  all_probabilities[predicted] = 0.92;

  return {
    predicted_defect: predicted,
    confidence: 0.92,
    all_probabilities,
    base_value: 0,
    contributions,
    out_of_spec_parameters: outOfSpec,
    top_drivers: contributions.slice(0, 3).map(
      (c) =>
        `${c.label} (${c.value}${c.unit}, ${c.drift_status}) ` +
        `${c.shap_value > 0 ? "increased" : "decreased"} ${predicted.toUpperCase()} ` +
        `defect probability (SHAP impact: ${c.shap_value >= 0 ? "+" : ""}${c.shap_value.toFixed(3)})`
    ),
    raw_features: telemetry,
    model_test_accuracy: 1.0,
    data_provenance: "SYNTHETIC_DEMONSTRATION",
  };
}

export const mockLineHealth: LineHealthResponse = {
  stations: [
    { station: "Station 01: Pre-Heat Furnace", cycle_time_s: 42.0, buffer_queue: 2, utilisation_pct: 72.0, bottleneck: false },
    { station: "Station 02: Descaling Jet", cycle_time_s: 24.5, buffer_queue: 1, utilisation_pct: 48.0, bottleneck: false },
    { station: "Station 03: Primary Rougher", cycle_time_s: 38.0, buffer_queue: 4, utilisation_pct: 68.0, bottleneck: false },
    { station: "Station 04: Roll Mill [BOTTLENECK]", cycle_time_s: 58.4, buffer_queue: 18, utilisation_pct: 98.5, bottleneck: true },
    { station: "Station 05: Quench Chamber", cycle_time_s: 45.0, buffer_queue: 3, utilisation_pct: 78.0, bottleneck: false },
    { station: "Station 06: Inspection Optical", cycle_time_s: 18.0, buffer_queue: 0, utilisation_pct: 32.0, bottleneck: false },
  ],
  bottleneck_notice:
    "Station 04 (Roll Mill) currently presents an active buffer queue of 18 units with 98.5% capacity utilization. Secondary thermal runaway induces micro-cracking downstream.",
  executive_kpis: [
    { tone: "danger", label: "Active Bottleneck Station", value: "Station 04: Roll Mill", subtext: "Thermal and mechanical load exceed safety limits" },
    { tone: "warning", label: "Cycle Time Variance", value: "+16.4 sec / unit", subtext: "Line throughput throttled by 14.2% below design rating" },
    { tone: "neutral", label: "Projected Margin Impact", value: "-$14,850 / day", subtext: "Estimated scrap and rework loss ($92.40 / flagged unit)" },
    { tone: "info", label: "Overall Line Yield (OEE)", value: "86.4% OEE", subtext: "Quality: 92.1% | Availability: 95.8% | Performance: 97.9%" },
  ],
  remediation_plan: [
    {
      title: "1. Mechanical & Pressure Adjustments",
      actions: [
        "Reduce Station 04 rolling force by **14.5 bar** (target: 152 bar).",
        "Inspect hydraulic servo valves for pressure spike dampening.",
        "Calibrate strip coiler tension oscillation dampener.",
      ],
    },
    {
      title: "2. Thermal & Quench Calibration",
      actions: [
        "Lower Annealing zone temperature setpoint by **22°C** to prevent grain embrittlement.",
        "Normalize quench cooling rate from 28.4°C/s to **18.0°C/s**.",
        "Recalibrate optical pyrometers at Station 04 inlet.",
      ],
    },
    {
      title: "3. Lubrication & Maintenance Schedule",
      actions: [
        "Increase emulsion flow by **6.5 L/h** on upper roll bearings.",
        "Replace high-vibration spindle bearing #2 (Vibration RMS > 4.5 mm/s).",
        "Execute descaling spray purge cycle prior to next lot transition.",
      ],
    },
  ],
  data_provenance: "SYNTHETIC_DEMONSTRATION",
};

export function mockFinancialImpact(
  daily_units: number,
  defect_rate_pct: number,
  scrap_cost_per_unit: number
): FinancialImpactResponse {
  const flagged = Math.floor(daily_units * (defect_rate_pct / 100));
  const daily = flagged * scrap_cost_per_unit;
  return {
    daily_units,
    defect_rate_pct,
    scrap_cost_per_unit,
    flagged_units_daily: flagged,
    daily_loss: Math.round(daily * 100) / 100,
    operating_days_per_month: 26,
    monthly_loss: Math.round(daily * 26 * 100) / 100,
    data_provenance: "SYNTHETIC_DEMONSTRATION",
  };
}
