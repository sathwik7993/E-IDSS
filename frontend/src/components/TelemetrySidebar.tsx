import type { TelemetrySpecsResponse, Telemetry } from "../types/api";
import "./TelemetrySidebar.css";

export type TelemetryMode =
  | "SIMULATE_FROM_DEFECT"
  | "PRESET_UNIT"
  | "MANUAL_INPUT";

const MODE_LABELS: { key: TelemetryMode; label: string }[] = [
  { key: "SIMULATE_FROM_DEFECT", label: "Simulate from Detected Defect" },
  { key: "PRESET_UNIT", label: "Preset Test Unit" },
  { key: "MANUAL_INPUT", label: "Manual Parameter Input" },
];

interface Props {
  specs: TelemetrySpecsResponse | null;
  telemetry: Telemetry;
  mode: TelemetryMode;
  presetId: string;
  detectedClass: string | null;
  onModeChange: (mode: TelemetryMode) => void;
  onPresetChange: (presetId: string) => void;
  onParameterChange: (feature: string, value: number) => void;
}

export function TelemetrySidebar({
  specs,
  telemetry,
  mode,
  presetId,
  detectedClass,
  onModeChange,
  onPresetChange,
  onParameterChange,
}: Props) {
  return (
    <aside className="telemetry-sidebar">
      <div className="sidebar-heading">Operational Telemetry</div>
      <p className="sidebar-caption">
        Machine settings linked to current production lot
      </p>

      <label className="sidebar-field">
        <span className="sidebar-field-label">Telemetry Input Source:</span>
        <div className="radio-group" role="radiogroup">
          {MODE_LABELS.map((m) => (
            <label key={m.key} className="radio-row">
              <input
                type="radio"
                name="telemetry-mode"
                checked={mode === m.key}
                onChange={() => onModeChange(m.key)}
              />
              <span>{m.label}</span>
            </label>
          ))}
        </div>
      </label>

      {mode === "SIMULATE_FROM_DEFECT" && (
        <div className="sidebar-note">
          {detectedClass
            ? `Loaded the machine settings recorded for the last ${detectedClass.toUpperCase()} event on Line 04.`
            : "Inspect a specimen on Tab I to load the machine settings recorded for that defect mode."}
        </div>
      )}

      {mode === "PRESET_UNIT" && specs && (
        <label className="sidebar-field">
          <span className="sidebar-field-label">
            Select Certified Incident Record:
          </span>
          <select
            className="sidebar-select"
            value={presetId}
            onChange={(e) => onPresetChange(e.target.value)}
          >
            {specs.presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      )}

      {mode === "MANUAL_INPUT" && specs && (
        <div className="sidebar-sliders">
          {specs.feature_cols.map((feature) => {
            const spec = specs.specs[feature];
            const value = telemetry[feature];
            const min = Math.round(spec.nominal_min * 0.6 * 10) / 10;
            const max = Math.round(spec.nominal_max * 1.5 * 10) / 10;
            return (
              <label key={feature} className="slider-row">
                <div className="slider-label">
                  <span>
                    {spec.label} [{spec.unit}]
                  </span>
                  <span className="mono slider-value">{value}</span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={spec.step}
                  value={value}
                  onChange={(e) =>
                    onParameterChange(feature, parseFloat(e.target.value))
                  }
                />
                <span className="slider-tolerance">
                  Nominal Tolerance: {spec.nominal_min} – {spec.nominal_max}{" "}
                  {spec.unit}
                </span>
              </label>
            );
          })}
        </div>
      )}

      <div className="sidebar-spec-note">
        <strong>Grad-CAM Specification</strong>
        <p>
          Gradient-weighted class activations extracted at the final
          convolutional stage. Regions where activation exceeds the designated
          threshold trigger connected-component extraction and bounding box
          registration.
        </p>
      </div>
    </aside>
  );
}
