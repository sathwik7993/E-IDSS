import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { postTelemetryAttribution } from "../api/client";
import type { AttributionResponse, Telemetry } from "../types/api";
import { MockDataBadge, ProvenanceBadge } from "../components/ProvenanceBadge";
import "./AttributionView.css";

const PUSH_COLOR = "#991B1B";
const DAMPEN_COLOR = "#1E40AF";

interface Props {
  telemetry: Telemetry;
  specimenRejected: boolean;
}

export function AttributionView({ telemetry, specimenRejected }: Props) {
  const [result, setResult] = useState<AttributionResponse | null>(null);
  const [isMock, setIsMock] = useState(false);

  useEffect(() => {
    if (specimenRejected) return;
    let cancelled = false;
    postTelemetryAttribution(telemetry).then((r) => {
      if (cancelled) return;
      setResult(r.data);
      setIsMock(r.isMock);
    });
    return () => {
      cancelled = true;
    };
  }, [telemetry, specimenRejected]);

  if (specimenRejected) {
    return (
      <div className="attribution-view">
        <div className="section-title">
          TreeSHAP Operational Root-Cause Attribution
        </div>
        <div className="alert-panel alert-critical">
          <strong>ROOT-CAUSE ATTRIBUTION SUSPENDED:</strong> Machine process
          telemetry attribution is only computed for verified industrial defect
          modes. The submitted specimen was rejected by the trust gate as
          out-of-distribution data.
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="attribution-view">
        <div className="section-title">
          TreeSHAP Operational Root-Cause Attribution
        </div>
        <div className="alert-panel">Computing TreeSHAP attribution…</div>
      </div>
    );
  }

  // Chart reads top-down by impact, so the largest contributor sits at the top.
  const chartData = result.contributions
    .slice()
    .reverse()
    .map((c) => ({ name: c.label, value: c.shap_value }));

  const span = Math.max(...chartData.map((d) => Math.abs(d.value)), 0.1) * 1.35;

  return (
    <div className="attribution-view">
      <div className="attribution-header">
        <div className="section-title">
          TreeSHAP Operational Root-Cause Attribution
        </div>
        <div className="attribution-badges">
          <ProvenanceBadge provenance={result.data_provenance} />
          <MockDataBadge isMock={isMock} />
        </div>
      </div>

      <p className="attribution-caption">
        Deconstructs machine telemetry parameters into marginal SHAP
        contributions toward predicted defect occurrence.
      </p>

      <div className="attribution-grid">
        <section>
          <div className="subsection-label">
            Local Feature Contributions (TreeSHAP Values)
          </div>
          <div className="attribution-target">
            Target Classification:{" "}
            <strong>{result.predicted_defect.toUpperCase()}</strong> · Classifier
            Confidence: <strong>{(result.confidence * 100).toFixed(1)}%</strong>
          </div>

          <div className="shap-chart">
            <ResponsiveContainer width="100%" height={chartData.length * 36 + 24}>
              <BarChart
                layout="vertical"
                data={chartData}
                margin={{ top: 4, right: 56, left: 0, bottom: 4 }}
              >
                <XAxis type="number" domain={[-span, span]} hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={128}
                  tick={{ fill: "#475569", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <ReferenceLine x={0} stroke="#475569" strokeDasharray="3 3" />
                <Bar dataKey="value" barSize={16} isAnimationActive={false}>
                  {chartData.map((d) => (
                    <Cell
                      key={d.name}
                      fill={d.value > 0 ? PUSH_COLOR : DAMPEN_COLOR}
                    />
                  ))}
                  <LabelList
                    dataKey="value"
                    position="right"
                    formatter={(v) => {
                      const n = Number(v);
                      return `${n >= 0 ? "+" : ""}${n.toFixed(3)}`;
                    }}
                    style={{ fill: "#0F172A", fontSize: 10.5, fontWeight: 700 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="shap-axis-label">
              TreeSHAP Marginal Contribution to Log-Odds
            </div>
          </div>

          <div className="shap-legend">
            <span>
              <i className="legend-swatch" style={{ background: PUSH_COLOR }} />
              Crimson: positive push toward the defect mode
            </span>
            <span>
              <i className="legend-swatch" style={{ background: DAMPEN_COLOR }} />
              Navy: protective dampening factor
            </span>
          </div>
        </section>

        <section>
          <div className="subsection-label">Primary Root-Cause Diagnostics</div>
          <ul className="driver-list">
            {result.top_drivers.map((driver) => (
              <li key={driver}>
                <span className="driver-tag">Root Cause</span>
                {driver}
              </li>
            ))}
          </ul>

          <div className="subsection-label drift-heading">
            Out-of-Spec Parameter Drift
          </div>
          {result.out_of_spec_parameters.length > 0 ? (
            result.out_of_spec_parameters.map((item) => {
              const isHigh = item.status === "CRITICAL_HIGH";
              return (
                <div
                  key={item.feature}
                  className={
                    "alert-panel " + (isHigh ? "alert-critical" : "alert-warning")
                  }
                >
                  <div className="drift-label">{item.label}</div>
                  <div className="mono drift-value">
                    Value:{" "}
                    <strong>
                      {item.value} {item.unit}
                    </strong>{" "}
                    <span className={isHigh ? "drift-high" : "drift-low"}>
                      [{isHigh ? "CRITICAL HIGH" : "CRITICAL LOW"}:{" "}
                      {item.drift_pct}% drift]
                    </span>
                  </div>
                  <div className="drift-nominal">
                    Nominal Range: {item.nominal_range} {item.unit}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="alert-panel alert-normal">
              <strong>NOMINAL STATUS:</strong> All measured parameters conform to
              certified tolerance envelopes.
            </div>
          )}
        </section>
      </div>

      <hr className="rule" />
      <div className="section-title">Telemetry Parameter Snapshot Table</div>
      <div className="data-table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Machine Parameter</th>
              <th>Measured Value</th>
              <th>Nominal Safe Envelope</th>
              <th>Tolerance Status</th>
              <th>TreeSHAP Contribution</th>
            </tr>
          </thead>
          <tbody>
            {result.contributions.map((c) => (
              <tr
                key={c.feature}
                className={c.drift_status === "Nominal" ? "" : "row-critical"}
              >
                <td>{c.label}</td>
                <td className="num">
                  {c.value} {c.unit}
                </td>
                <td className="num">
                  {c.nominal_min} – {c.nominal_max} {c.unit}
                </td>
                <td>{c.drift_status}</td>
                <td className="num">
                  {c.shap_value >= 0 ? "+" : ""}
                  {c.shap_value.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="attribution-footnote">
        LightGBM telemetry classifier · held-out test accuracy{" "}
        <span className="mono">
          {(result.model_test_accuracy * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}
