import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { postInspect } from "../api/client";
import type { InspectResponse } from "../types/api";
import { MockDataBadge, StubModeBadge } from "../components/ProvenanceBadge";
import "./InspectionView.css";

const NEUTRAL_BAR = "#94A3B8";
const DEFECT_BAR = "#991B1B";
const NORMAL_BAR = "#166534";

interface Props {
  result: InspectResponse | null;
  imageUrl: string | null;
  isMock: boolean;
  onResult: (
    result: InspectResponse | null,
    imageUrl: string | null,
    isMock: boolean
  ) => void;
}

export function InspectionView({ result, imageUrl, isMock, onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.6);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [renderedSize, setRenderedSize] = useState({ w: 0, h: 0 });

  const fileRef = useRef<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const annotatedImgRef = useRef<HTMLImageElement>(null);

  const runInspect = useCallback(
    async (file: File, activationThreshold: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await postInspect(file, activationThreshold);
        onResult(res.data, URL.createObjectURL(file), res.isMock);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Inspection failed");
      } finally {
        setLoading(false);
      }
    },
    [onResult]
  );

  const onFileChosen = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (!file) return;
      fileRef.current = file;
      setFileName(file.name);
      runInspect(file, threshold);
    },
    [runInspect, threshold]
  );

  // Re-extract the bounding region when the activation threshold moves. The
  // box comes from the backend's Grad-CAM heatmap, so the slider has to round
  // trip rather than being recomputed client side.
  useEffect(() => {
    const file = fileRef.current;
    if (!file) return;
    const timer = setTimeout(() => runInspect(file, threshold), 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threshold]);

  const onAnnotatedLoad = useCallback(() => {
    if (annotatedImgRef.current) {
      setRenderedSize({
        w: annotatedImgRef.current.clientWidth,
        h: annotatedImgRef.current.clientHeight,
      });
    }
  }, []);

  const isValid = result ? result.decision !== "DEFER_TO_HUMAN" : true;
  const probEntries = result
    ? Object.entries(result.class_probabilities)
        .map(([name, value]) => ({ name: name.toUpperCase(), value: value * 100 }))
        .sort((a, b) => a.value - b.value)
    : [];

  const boxStyle = (() => {
    if (!result?.bbox || renderedSize.w === 0) return null;
    const { x, y, width, height, image_width, image_height } = result.bbox;
    const sx = renderedSize.w / image_width;
    const sy = renderedSize.h / image_height;
    return {
      left: x * sx,
      top: y * sy,
      width: width * sx,
      height: height * sy,
    };
  })();

  return (
    <div className="inspection-view">
      <div className="inspection-top">
        <section>
          <div className="section-title">Specimen Input &amp; Upload</div>

          <div
            className={"dropzone" + (dragOver ? " drag-over" : "")}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              onFileChosen(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg"
              hidden
              onChange={(e) => onFileChosen(e.target.files)}
            />
            <span className="dropzone-title">
              Upload Inspection Specimen (PNG, JPG, JPEG)
            </span>
            <span className="dropzone-hint">
              Drop an optical micrograph here, or click to browse.
            </span>
          </div>

          {fileName && (
            <div className="specimen-caption">
              Active Specimen: <span className="mono">{fileName}</span>
            </div>
          )}

          <label className="threshold-row">
            <div className="threshold-label">
              <span>Grad-CAM Bounding Box Threshold (Activation &gt; T):</span>
              <span className="mono threshold-value">{threshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.4}
              max={0.85}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
            />
            <span className="threshold-help">
              Minimum convolutional activation intensity required to trigger
              connected-component bounding box extraction.
            </span>
          </label>

          <div className="inspection-badges">
            {result && <StubModeBadge stubMode={result.stub_mode} />}
            <MockDataBadge isMock={isMock} />
          </div>
        </section>

        <section>
          <div className="section-title">
            Classification Output &amp; Quality Gate
          </div>

          {!result && (
            <div className="alert-panel">
              Awaiting specimen. Upload an image to run the inspection pipeline.
            </div>
          )}

          {result && !isValid && (
            <div className="ood-panel">
              <div className="ood-eyebrow">
                Out-of-Distribution Guard Triggered
              </div>
              <div className="ood-title">
                Specimen Rejected — No Prediction Generated
              </div>
              <p className="ood-body">
                This input falls outside the distribution the inspection model
                was trained on. Classification is deliberately withheld to
                eliminate false positive quality alerts.
              </p>
              <div className="ood-criterion mono">
                <strong>GATE CRITERION:</strong>
                <br />
                Mahalanobis distance {result.mahalanobis_distance.toFixed(2)} ·
                epistemic uncertainty {result.epistemic_uncertainty.toFixed(3)} ·
                calibrated confidence{" "}
                {(result.calibrated_confidence * 100).toFixed(1)}%
              </div>
            </div>
          )}

          {result && isValid && (
            <>
              <div className="classification-row">
                <span className="classification-label">
                  Classification Result:
                </span>
                <span className={`status-pill status-${result.predicted_class}`}>
                  {result.predicted_class}
                </span>
                <span className="mono classification-confidence">
                  [{(result.calibrated_confidence * 100).toFixed(2)}% Confidence]
                </span>
              </div>

              <div className="prob-chart">
                <ResponsiveContainer width="100%" height={probEntries.length * 32}>
                  <BarChart
                    layout="vertical"
                    data={probEntries}
                    margin={{ top: 4, right: 52, left: 0, bottom: 4 }}
                  >
                    <XAxis type="number" domain={[0, 100]} hide />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={76}
                      tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Bar dataKey="value" barSize={14} isAnimationActive={false}>
                      {probEntries.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={
                            entry.name !== result.predicted_class.toUpperCase()
                              ? NEUTRAL_BAR
                              : result.predicted_class === "normal"
                                ? NORMAL_BAR
                                : DEFECT_BAR
                          }
                        />
                      ))}
                      <LabelList
                        dataKey="value"
                        position="right"
                        formatter={(v) => `${Number(v).toFixed(1)}%`}
                        style={{ fill: "#0F172A", fontSize: 10.5, fontWeight: 700 }}
                      />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="prob-axis-label">Class Probability (%)</div>
              </div>

              <div className="evidence-grid">
                <div className="evidence-cell">
                  <span className="evidence-label">Raw confidence</span>
                  <span className="mono evidence-value">
                    {(result.raw_confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="evidence-cell">
                  <span className="evidence-label">Epistemic uncertainty</span>
                  <span className="mono evidence-value">
                    {result.epistemic_uncertainty.toFixed(3)}
                  </span>
                </div>
                <div className="evidence-cell">
                  <span className="evidence-label">Mahalanobis distance</span>
                  <span className="mono evidence-value">
                    {result.mahalanobis_distance.toFixed(2)}
                  </span>
                </div>
                <div className="evidence-cell">
                  <span className="evidence-label">Part ID</span>
                  <span className="mono evidence-value">{result.part_id}</span>
                </div>
              </div>
            </>
          )}

          {error && <div className="alert-panel alert-critical">{error}</div>}
        </section>
      </div>

      {result && (
        <>
          <hr className="rule" />

          {!isValid ? (
            <>
              <div className="section-title">Submitted Specimen Evaluation</div>
              <div className="rejected-grid">
                <div>
                  <div className="subsection-label">Submitted Specimen</div>
                  {imageUrl && (
                    <img src={imageUrl} alt="Submitted specimen" className="scan-img" />
                  )}
                </div>
                <div>
                  <div className="subsection-label">Diagnostics Summary</div>
                  <div className="alert-panel alert-critical">
                    <strong>ANALYSIS SUPPRESSED:</strong> Grad-CAM heatmaps and
                    defect bounding boxes are only reported for specimens that
                    clear the trust gate.
                    <br />
                    <br />
                    <strong>Measured Specimen Metrics:</strong>
                    <br />• Mahalanobis distance:{" "}
                    <code className="mono">
                      {result.mahalanobis_distance.toFixed(2)}
                    </code>
                    <br />• Epistemic uncertainty (MC-dropout):{" "}
                    <code className="mono">
                      {result.epistemic_uncertainty.toFixed(3)}
                    </code>
                    <br />• Calibrated confidence:{" "}
                    <code className="mono">
                      {(result.calibrated_confidence * 100).toFixed(1)}%
                    </code>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="section-title">
                Micrograph Scan vs. Convolutional Grad-CAM Localization
              </div>

              <div className={"scan-grid" + (loading ? " loading" : "")}>
                <div>
                  <div className="subsection-label">Raw Optical Scan</div>
                  {imageUrl && (
                    <img src={imageUrl} alt="Raw optical scan" className="scan-img" />
                  )}
                </div>
                <div>
                  <div className="subsection-label">Grad-CAM Heatmap</div>
                  <img
                    src={`data:image/png;base64,${result.overlay_png_base64}`}
                    alt="Grad-CAM heatmap overlay"
                    className="scan-img"
                  />
                </div>
                <div>
                  <div className="subsection-label">
                    Bounding Box (Act &gt; {threshold.toFixed(2)})
                  </div>
                  <div className="annotated-stage">
                    {imageUrl && (
                      <img
                        ref={annotatedImgRef}
                        src={imageUrl}
                        alt="Annotated scan"
                        className="scan-img"
                        onLoad={onAnnotatedLoad}
                      />
                    )}
                    {boxStyle && (
                      <div className="scan-bbox" style={boxStyle}>
                        <span className="scan-bbox-label">
                          {result.predicted_class}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="section-title">
                Extracted Defect Bounding Coordinates
              </div>

              {result.bbox ? (
                <div className="data-table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Region</th>
                        <th>X (px)</th>
                        <th>Y (px)</th>
                        <th>Width (px)</th>
                        <th>Height (px)</th>
                        <th>Area (px²)</th>
                        <th>Frame Coverage</th>
                        <th>Peak Activation</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Region #1</td>
                        <td className="num">{result.bbox.x}</td>
                        <td className="num">{result.bbox.y}</td>
                        <td className="num">{result.bbox.width}</td>
                        <td className="num">{result.bbox.height}</td>
                        <td className="num">
                          {result.bbox.width * result.bbox.height}
                        </td>
                        <td className="num">
                          {(result.bbox.coverage * 100).toFixed(1)}%
                        </td>
                        <td className="num">
                          {result.bbox.peak_activation?.toFixed(3) ?? "—"}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              ) : result.predicted_class === "normal" ? (
                <div className="alert-panel alert-normal">
                  <strong>VERIFICATION PASSED:</strong> Nominal surface
                  topography. No localized activation region exceeded threshold
                  &gt; {threshold.toFixed(2)}.
                </div>
              ) : (
                <div className="alert-panel alert-warning">
                  <strong>NOTICE:</strong> Diffuse convolutional activation
                  detected. No isolated spatial cluster exceeded the localized
                  threshold &gt; {threshold.toFixed(2)}.
                </div>
              )}

              {result.bbox && result.bbox.n_components > 1 && (
                <div className="region-note">
                  {result.bbox.n_components} activation components exceeded the
                  threshold; the box bounds the largest connected region.
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
