import { useEffect, useRef, useState } from "react";
import { getFinancialImpact } from "../api/client";
import type { FinancialImpactResponse, LineHealthResponse } from "../types/api";
import { MockDataBadge, ProvenanceBadge } from "../components/ProvenanceBadge";
import "./LineHealthView.css";

function currency(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// The remediation copy uses **bold** to mark the engineering setpoint in each
// action; render those spans rather than printing the asterisks.
function renderAction(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

interface Props {
  health: LineHealthResponse | null;
  healthIsMock: boolean;
}

export function LineHealthView({ health, healthIsMock }: Props) {
  const [dailyUnits, setDailyUnits] = useState(2400);
  const [defectRatePct, setDefectRatePct] = useState(3.8);
  const [scrapCost, setScrapCost] = useState(92.4);

  const [financial, setFinancial] = useState<FinancialImpactResponse | null>(null);
  const [finIsMock, setFinIsMock] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      getFinancialImpact(dailyUnits, defectRatePct, scrapCost).then((r) => {
        setFinancial(r.data);
        setFinIsMock(r.isMock);
      });
    }, 250);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [dailyUnits, defectRatePct, scrapCost]);

  if (!health) {
    return (
      <div className="line-health-view">
        <div className="section-title">
          Production Line Health &amp; Bottleneck Breakdown
        </div>
        <div className="alert-panel">Loading line state…</div>
      </div>
    );
  }

  return (
    <div className="line-health-view">
      <div className="line-health-header">
        <div className="section-title">
          Production Line Health &amp; Bottleneck Breakdown
        </div>
        <div className="line-health-badges">
          <ProvenanceBadge provenance={health.data_provenance} />
          <MockDataBadge isMock={healthIsMock || finIsMock} />
        </div>
      </div>

      <div className="line-health-grid">
        <section>
          <div className="subsection-label">
            Station Capacity &amp; Cycle Delay Matrix
          </div>
          <div className="data-table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Station Identifier</th>
                  <th>Cycle (s)</th>
                  <th>Buffer (units)</th>
                  <th>Utilization (%)</th>
                </tr>
              </thead>
              <tbody>
                {health.stations.map((s) => (
                  <tr key={s.station} className={s.bottleneck ? "row-critical" : ""}>
                    <td>{s.station}</td>
                    <td className="num">{s.cycle_time_s.toFixed(1)}</td>
                    <td className="num">{s.buffer_queue}</td>
                    <td className="num">{s.utilisation_pct.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="alert-panel alert-critical bottleneck-notice">
            <strong>BOTTLENECK NOTICE:</strong> {health.bottleneck_notice}
          </div>
        </section>

        <section>
          <div className="subsection-label">
            Projected Scrap Cost &amp; Financial Margin Erosion
          </div>

          <div className="financial-controls">
            <label className="control-row">
              <div className="control-label">
                <span>Daily Production Volume (units):</span>
                <span className="mono control-value">{dailyUnits}</span>
              </div>
              <input
                type="range"
                min={500}
                max={5000}
                step={100}
                value={dailyUnits}
                onChange={(e) => setDailyUnits(parseInt(e.target.value, 10))}
              />
            </label>

            <label className="control-row">
              <div className="control-label">
                <span>Observed Defect Rate (%):</span>
                <span className="mono control-value">
                  {defectRatePct.toFixed(1)}
                </span>
              </div>
              <input
                type="range"
                min={0.5}
                max={12}
                step={0.1}
                value={defectRatePct}
                onChange={(e) => setDefectRatePct(parseFloat(e.target.value))}
              />
            </label>

            <label className="control-row">
              <div className="control-label">
                <span>Average Cost per Scrapped Unit ($):</span>
              </div>
              <input
                type="number"
                className="control-number"
                min={0}
                step={5}
                value={scrapCost}
                onChange={(e) => setScrapCost(parseFloat(e.target.value) || 0)}
              />
            </label>
          </div>

          {financial && (
            <div className="loss-card">
              <div className="kpi-label">Daily Direct Financial Loss</div>
              <div className="loss-value">{currency(financial.daily_loss)} / day</div>
              <div className="kpi-subtext">
                Calculated on {financial.flagged_units_daily} defective units per
                operating day
              </div>

              <div className="loss-divider">
                <div className="kpi-label">
                  Projected Monthly Margin Loss (
                  {financial.operating_days_per_month} Operating Days)
                </div>
                <div className="loss-value-secondary">
                  {currency(financial.monthly_loss)} / month
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      <hr className="rule" />
      <div className="section-title">
        Prescriptive Engineering Remediation Plan
      </div>
      <div className="remediation-grid">
        {health.remediation_plan.map((group) => (
          <div className="remediation-card" key={group.title}>
            <div className="remediation-title">{group.title}</div>
            <ul>
              {group.actions.map((action) => (
                <li key={action}>{renderAction(action)}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
