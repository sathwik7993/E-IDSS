import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import { getHealth, getLineHealth, getTelemetrySpecs } from "./api/client";
import type {
  HealthResponse,
  InspectResponse,
  LineHealthResponse,
  Telemetry,
  TelemetrySpecsResponse,
} from "./types/api";
import {
  TelemetrySidebar,
  type TelemetryMode,
} from "./components/TelemetrySidebar";
import { InspectionView } from "./views/InspectionView";
import { AttributionView } from "./views/AttributionView";
import { LineHealthView } from "./views/LineHealthView";

type TabKey = "inspection" | "attribution" | "analytics";

const TABS: { key: TabKey; label: string }[] = [
  { key: "inspection", label: "I. Optical Defect Inspection & Grad-CAM" },
  { key: "attribution", label: "II. Operational Telemetry & TreeSHAP Attribution" },
  { key: "analytics", label: "III. Line Health & Financial Impact Analytics" },
];

const KPI_TONE_CLASS: Record<string, string> = {
  danger: "kpi-card-danger",
  warning: "kpi-card-warning",
  neutral: "kpi-card-neutral",
  info: "kpi-card-info",
};

function App() {
  const [tab, setTab] = useState<TabKey>("inspection");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [specs, setSpecs] = useState<TelemetrySpecsResponse | null>(null);
  const [lineHealth, setLineHealth] = useState<LineHealthResponse | null>(null);
  const [lineHealthIsMock, setLineHealthIsMock] = useState(false);

  const [mode, setMode] = useState<TelemetryMode>("SIMULATE_FROM_DEFECT");
  const [presetId, setPresetId] = useState("UNIT-10492");
  const [manualTelemetry, setManualTelemetry] = useState<Telemetry | null>(null);

  const [inspection, setInspection] = useState<InspectResponse | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [inspectionIsMock, setInspectionIsMock] = useState(false);

  useEffect(() => {
    getHealth().then((r) => setHealth(r.data));
    getTelemetrySpecs().then((r) => {
      setSpecs(r.data);
      setManualTelemetry({ ...r.data.nominal });
    });
    getLineHealth().then((r) => {
      setLineHealth(r.data);
      setLineHealthIsMock(r.isMock);
    });
  }, []);

  const specimenRejected = inspection?.decision === "DEFER_TO_HUMAN";
  const detectedClass = specimenRejected
    ? null
    : (inspection?.predicted_class ?? null);

  // The active parameter vector: what the sidebar shows and what Tab II
  // attributes against. Each input source resolves to the same shape.
  const telemetry = useMemo<Telemetry>(() => {
    if (!specs) return {};
    if (mode === "MANUAL_INPUT") return manualTelemetry ?? specs.nominal;
    if (mode === "PRESET_UNIT") {
      return (
        specs.presets.find((p) => p.id === presetId)?.telemetry ?? specs.nominal
      );
    }
    if (detectedClass && specs.defect_profiles[detectedClass]) {
      return specs.defect_profiles[detectedClass];
    }
    return specs.nominal;
  }, [specs, mode, manualTelemetry, presetId, detectedClass]);

  const onParameterChange = useCallback((feature: string, value: number) => {
    setManualTelemetry((prev) => (prev ? { ...prev, [feature]: value } : prev));
  }, []);

  const onInspectResult = useCallback(
    (result: InspectResponse | null, url: string | null, isMock: boolean) => {
      setInspection(result);
      setImageUrl(url);
      setInspectionIsMock(isMock);
    },
    []
  );

  const online = health?.status === "ok";

  return (
    <div className="app-shell">
      <TelemetrySidebar
        specs={specs}
        telemetry={telemetry}
        mode={mode}
        presetId={presetId}
        detectedClass={detectedClass}
        onModeChange={setMode}
        onPresetChange={setPresetId}
        onParameterChange={onParameterChange}
      />

      <main className="app-main">
        <header className="app-banner">
          <div>
            <div className="banner-eyebrow">
              Enterprise Industrial Intelligence System
            </div>
            <div className="banner-title">HUNGRY INNOVATORS</div>
            <div className="banner-subtitle">
              Automated Surface Inspection | Convolutional Grad-CAM Localization
              | TreeSHAP Process Attribution
            </div>
          </div>
          <div className={"status-chip" + (online ? "" : " offline")}>
            <span className="status-dot" />
            {health
              ? `STATUS: ${online ? "ONLINE" : "DEGRADED"}${health.stub_mode ? " | STUB" : ""} | LINE 04`
              : "STATUS: CONNECTING"}
          </div>
        </header>

        {lineHealth && (
          <div className="kpi-strip">
            {lineHealth.executive_kpis.map((kpi) => (
              <div
                key={kpi.label}
                className={`kpi-card ${KPI_TONE_CLASS[kpi.tone] ?? ""}`}
              >
                <div className="kpi-label">{kpi.label}</div>
                <div className="kpi-value">{kpi.value}</div>
                <div className="kpi-subtext">{kpi.subtext}</div>
              </div>
            ))}
          </div>
        )}

        <nav className="tab-bar" role="tablist" aria-label="Analysis stage">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              className={"tab-item" + (tab === t.key ? " active" : "")}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="tab-panel" role="tabpanel">
          {tab === "inspection" && (
            <InspectionView
              result={inspection}
              imageUrl={imageUrl}
              isMock={inspectionIsMock}
              onResult={onInspectResult}
            />
          )}
          {tab === "attribution" && (
            <AttributionView
              telemetry={telemetry}
              specimenRejected={!!specimenRejected}
            />
          )}
          {tab === "analytics" && (
            <LineHealthView health={lineHealth} healthIsMock={lineHealthIsMock} />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
