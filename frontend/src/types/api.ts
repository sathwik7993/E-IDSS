// Types matching the E-IDSS backend API contract exactly.

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  stub_mode: boolean;
  device: string;
}

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
  image_width: number;
  image_height: number;
  coverage: number;
  peak_x: number;
  peak_y: number;
  peak_activation: number;
  n_components: number;
  threshold: number;
}

export interface InspectResponse {
  part_id: string;
  predicted_class: string;
  is_defective: boolean;
  calibrated_confidence: number;
  raw_confidence: number;
  epistemic_uncertainty: number;
  mahalanobis_distance: number;
  novel_or_uncertain: boolean;
  decision: "AUTO" | "DEFER_TO_HUMAN";
  class_probabilities: Record<string, number>;
  heatmap_png_base64: string;
  overlay_png_base64: string;
  bbox: BBox | null;
  stub_mode: boolean;
  data_provenance: string;
}

export interface RobustnessCondition {
  accuracy: number;
  macro_f1: number;
  false_accept_rate: number;
  false_reject_rate: number;
  [key: string]: number;
}

export interface MetricsResponse {
  available?: boolean;
  clean_test?: Record<string, number>;
  robustness?: Record<string, RobustnessCondition>;
}

export interface RootCauseDriver {
  feature: string;
  station: string;
  observed: number;
  nominal: number;
  unit: string;
  deviation_sigma: number;
  shap_value: number;
  attribution_pct: number;
  direction: string;
}

export interface RootCauseResponse {
  defect_class: string;
  drivers: RootCauseDriver[];
  narrative: string;
  data_provenance: string;
}

export interface RootCauseValidationEntry {
  true_drivers: string[];
  top_ranked: string[];
  recovered: string[];
  recall: number;
}

export interface RootCauseValidationResponse {
  [defectClass: string]: RootCauseValidationEntry | any;
  confounder_check?: Record<string, unknown>;
  mean_recall?: number;
}

export interface Station {
  id: string;
  name: string;
  nominal_cycle_s: number;
  actual_cycle_s: number;
  utilisation: number;
  buffer_level: number;
  starved_pct: number;
  blocked_pct: number;
}

export interface LineStateResponse {
  stations: Station[];
  bottleneck_station_id: string;
  bottleneck_reason: string;
  line_throughput_units_hr: number;
  theoretical_throughput_units_hr: number;
  data_provenance: string;
}

export interface EconomicsResponse {
  units_produced: number;
  good_units: number;
  reworked_units: number;
  scrapped_units: number;
  revenue: number;
  variable_cost: number;
  quality_penalties: number;
  net_margin_per_shift: number;
  margin_per_unit: number;
  data_provenance: string;
}

export interface LineRecommendationResponse {
  action: string;
  target_station_id?: string;
  rationale: string;
  current_throughput_units_hr?: number;
  projected_throughput_units_hr?: number;
  throughput_delta_pct?: number;
  projected_margin_delta_per_shift?: number;
  data_provenance: string;
}

export interface EconomicsRecommendationResponse {
  action: string;
  rationale: string;
  speed_delta_pct?: number;
  defect_rate_delta_pct?: number;
  projected_margin_delta_per_shift?: number;
  baseline?: EconomicsResponse;
  intervened?: EconomicsResponse;
  data_provenance: string;
}

export interface TelemetrySpec {
  label: string;
  unit: string;
  nominal_min: number;
  nominal_max: number;
  desc: string;
  step: number;
}

export type Telemetry = Record<string, number>;

export interface PresetUnit {
  id: string;
  label: string;
  telemetry: Telemetry;
}

export interface TelemetrySpecsResponse {
  feature_cols: string[];
  specs: Record<string, TelemetrySpec>;
  nominal: Telemetry;
  presets: PresetUnit[];
  defect_profiles: Record<string, Telemetry>;
  model_test_accuracy: number;
  n_training_rows: number;
  data_provenance: string;
}

export interface ShapContribution {
  feature: string;
  label: string;
  value: number;
  unit: string;
  shap_value: number;
  abs_shap: number;
  nominal_min: number;
  nominal_max: number;
  drift_status: string;
}

export interface OutOfSpecParameter {
  feature: string;
  label: string;
  value: number;
  unit: string;
  nominal_range: string;
  status: "CRITICAL_HIGH" | "CRITICAL_LOW";
  drift_pct: number;
}

export interface AttributionResponse {
  predicted_defect: string;
  confidence: number;
  all_probabilities: Record<string, number>;
  base_value: number;
  contributions: ShapContribution[];
  out_of_spec_parameters: OutOfSpecParameter[];
  top_drivers: string[];
  raw_features: Telemetry;
  model_test_accuracy: number;
  data_provenance: string;
}

export interface StationRow {
  station: string;
  cycle_time_s: number;
  buffer_queue: number;
  utilisation_pct: number;
  bottleneck: boolean;
}

export interface ExecutiveKpi {
  tone: "danger" | "warning" | "neutral" | "info";
  label: string;
  value: string;
  subtext: string;
}

export interface RemediationGroup {
  title: string;
  actions: string[];
}

export interface LineHealthResponse {
  stations: StationRow[];
  bottleneck_notice: string;
  executive_kpis: ExecutiveKpi[];
  remediation_plan: RemediationGroup[];
  data_provenance: string;
}

export interface FinancialImpactResponse {
  daily_units: number;
  defect_rate_pct: number;
  scrap_cost_per_unit: number;
  flagged_units_daily: number;
  daily_loss: number;
  operating_days_per_month: number;
  monthly_loss: number;
  data_provenance: string;
}

export interface CounterfactualRequest {
  defect_rate: number;
  throughput: number;
  speed_delta_pct: number;
  defect_rate_delta_pct: number;
}

export interface CounterfactualResponse {
  baseline: EconomicsResponse;
  intervened: EconomicsResponse;
  margin_delta_per_shift: number;
  recommendation: "ADOPT" | "REJECT";
  data_provenance: string;
}
