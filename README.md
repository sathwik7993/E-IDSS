# E-IDSS — Explainable Industrial Decision-Support System

Surface-defect inspection that tells you **what it found, where it found it,
why it happened, and what it costs** — and that refuses to answer when it
shouldn't.

Built solo for **Neurax Hackathon 3.0, Domain 2 — AI in Industry and
Automation.**

---

## The problem

A quality-control model that outputs `crack, 0.97` is not usable on a factory
floor. Nobody can verify it, nobody can act on it, and when something outside
its training distribution arrives it will confidently classify that too.

E-IDSS closes all four gaps:

| Question an operator actually asks | How the system answers |
|---|---|
| *What is the defect?* | ConvNeXt-Tiny 5-class classifier (crack / hole / normal / rust / scratch) with temperature-calibrated confidence |
| *Where is it?* | Grad-CAM++ heatmap over the final conv stage, reduced to a bounding box by largest-connected-component extraction at an adjustable activation threshold |
| *Should I trust this?* | A trust gate combining Mahalanobis distance to class-conditional feature centroids with MC-dropout epistemic uncertainty. Off-distribution inputs are **rejected**, not classified |
| *Why did it happen, and what's it costing me?* | TreeSHAP attribution over eight machine telemetry parameters, plus bottleneck analysis and a scrap-cost / margin-erosion model |

---

## What it looks like

One console, three analysis stages, and a persistent operational-telemetry
sidebar that supplies the parameter vector every stage reasons over.

**I. Optical Defect Inspection & Grad-CAM**
Specimen upload → classification pill, calibrated confidence, class-probability
chart, and a raw / heatmap / bounding-box triptych with the extracted
coordinates. The activation threshold is a live control: moving it re-runs
region extraction on the server, not a cosmetic redraw.

**II. Operational Telemetry & TreeSHAP Attribution**
Local SHAP contribution per machine parameter, ranked root-cause diagnostics in
plain language, out-of-spec drift panels against each parameter's nominal
envelope, and a full telemetry snapshot table.

**III. Line Health & Financial Impact Analytics**
Station capacity and cycle-delay matrix with the bottleneck flagged,
scrap-cost and monthly margin-erosion model, and a prescriptive engineering
remediation plan.

The sidebar offers three telemetry sources — **Simulate from Detected Defect**
(Stage I's verdict selects the machine settings recorded for that defect mode),
**Preset Test Unit** (five certified incident records), and **Manual Parameter
Input** (eight sliders bounded by nominal tolerances). A specimen rejected by
the trust gate **suspends Stage II entirely**: attribution is only computed for
verified defect modes.

---

## Measured results

ConvNeXt-Tiny on the held-out test split, and on programmatically degraded
copies of it. False-accept rate is the number that matters in QC — it is the
rate at which a genuine defect is passed as good.

| Condition | Accuracy | Macro-F1 | False-accept | False-reject |
|---|---|---|---|---|
| Clean | 99.89% | 0.9989 | 0.00% | 0.00% |
| Bright lighting | 99.78% | 0.9978 | 0.07% | 0.00% |
| Dim lighting | 99.89% | 0.9989 | 0.14% | 0.00% |
| Low contrast | 99.83% | 0.9983 | 0.21% | 0.00% |
| Rotated 15° | 99.89% | 0.9989 | 0.00% | 0.00% |
| Rotated 90° | 99.89% | 0.9989 | 0.07% | 0.00% |
| Defocus blur | 89.06% | 0.8799 | 11.53% | 0.00% |
| Combined hard | 90.17% | 0.8998 | 4.44% | 23.89% |

Attribution quality is **measured, not asserted**: because the telemetry's
causal structure is constructed, TreeSHAP can be checked against ground truth.
It recovers the true drivers at **mean recall 1.0**, and correctly ranks
chamber humidity (the causal parent of rust) above ambient temperature (a
non-causal correlate) — the confounder check the validation endpoint reports.

Full analysis, including a documented blind spot in the trust gate, is in
[`readme_E-IDSS.md`](readme_E-IDSS.md).

---

## Data provenance — read this

The organizer dataset contains **images only**: 5 classes × 2400 images, no
bounding boxes, no masks, no telemetry, no cost ledgers.

So the system draws a hard line, and the line is visible in the product:

- The **vision tier runs on real organizer data.** Its responses carry
  `data_provenance: "ORGANIZER_DATASET"`.
- The **telemetry, attribution, line-health and economic tiers run on
  generated data.** Every one of their responses carries
  `data_provenance: "SYNTHETIC_DEMONSTRATION"`, and the console renders a
  badge for it on every panel that shows such data.

Nothing simulated is ever presented as measured. The generator, its seed and
its causal structure are in [`ai/telemetry.py`](ai/telemetry.py) and
[`ai/synthetic.py`](ai/synthetic.py), so the attribution layer is verifiable
rather than merely plausible.

---

## Running it

```bash
cp .env.example .env
docker compose up --build
```

That is the whole thing — one command brings up all three services with
health-gated startup ordering.

| Service | Port | Role |
|---|---|---|
| Console (React + Vite) | 5173 | Three analysis stages, telemetry sidebar |
| Intelligence API (FastAPI) | 8000 | Inference, XAI, attribution, simulation |
| Governance gateway (Spring Boot) | 8080 | JWT auth, RBAC, hash-chained audit trail |

Demo identities, seeded at gateway boot:
`operator/operator123`, `linelead/linelead123`, `manager/manager123`.

**The trained checkpoint is not in this repository** (114 MB, gitignored). The
backend detects its absence and starts in a clearly-flagged **stub mode** —
deterministic seeded responses carrying `stub_mode: true` — so the console is
fully demonstrable without it. Drop `convnext_tiny_eidss.pt` into `models/`
for live inference; no rebuild needed, the directory is bind-mounted.

### Verify the stack

```bash
python scripts/smoke_test.py                                    # 38-point API contract test
python scripts/repro_gateway_multipart.py --base localhost:8080 # upload regression check
python scripts/edge_case_battery.py                             # adversarial inputs
```

---

## Architecture

```
Console (React)  ──▶  Governance gateway (Spring Boot)  ──▶  Intelligence API (FastAPI)
  3 stages              JWT · RBAC · audit chain              ai/ — model, XAI, attribution
```

`ai/` is a standalone package shared by the training scripts and the backend,
so what trains is exactly what serves.

| Module | Responsibility |
|---|---|
| `ai/model.py`, `ai/train.py` | ConvNeXt-Tiny, temperature calibration, Mahalanobis statistics, OOD threshold — all baked into one checkpoint |
| `ai/explain.py` | Grad-CAM++, heatmap→box extraction, trust gate |
| `ai/robustness.py` | Picklable degradation transforms for the robustness battery |
| `ai/telemetry.py` | Telemetry specs, LightGBM + TreeSHAP attribution, line health, financial model |
| `ai/rootcause.py`, `ai/synthetic.py` | Causal structure, attribution validation, drift detection |

The gateway is not decoration: RBAC is enforced declaratively before any
request reaches the proxy (an operator asking for economics gets a 403), and
every advisory call is written to a hash-chained audit record that
`GET /api/audit/verify` can re-derive.

### Key API surface

| Endpoint | Returns |
|---|---|
| `POST /api/inspect?activation_threshold=` | Class, calibrated + raw confidence, epistemic uncertainty, Mahalanobis distance, decision (`AUTO` / `DEFER_TO_HUMAN`), heatmap, overlay, bounding box |
| `GET /api/telemetry/specs` | Parameter envelopes, presets, per-defect machine profiles |
| `POST /api/telemetry/attribution` | TreeSHAP contributions, out-of-spec drift, ranked root causes |
| `GET /api/rootcause/validation` | Attribution recall against ground truth + confounder check |
| `GET /api/line/health`, `/api/line/financial` | Station matrix, bottleneck, scrap cost, margin erosion |
| `GET /api/metrics` | Full robustness report from the checkpoint |

---

## Documentation

- **[`explain.md`](explain.md)** — the whole project in plain English: what the
  problem was, how each piece solves it, and what every technology is for.
  Start here if you want the reasoning rather than the spec.
- **[`readme_E-IDSS.md`](readme_E-IDSS.md)** — full architecture, approach,
  evaluation, reproducibility notes, and the documented known limitation.
- **[`ps Industries and automation.docx`](ps%20Industries%20and%20automation.docx)** — the
  original problem statement.

## License

Built for Neurax Hackathon 3.0. No license granted for reuse.
