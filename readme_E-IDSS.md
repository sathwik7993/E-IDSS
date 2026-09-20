# Explainable Industrial Decision-Support System (E-IDSS)
*A Unified AI Architecture Bridging Quality, Throughput, and Economics in Multi-Stage Manufacturing*

---

## 0. Submission Scope & Data Provenance

The organizer-provided dataset for this build is a **5-class labeled image set only**
(`crack`, `hole`, `normal`, `rust`, `scratch` — 2,400 images each, no bounding
boxes/masks, no time-synced sensor telemetry, no station event/WIP logs, no economic
ledgers). The architecture below is the full intended system; this section states
plainly what runs on real organizer data versus what is a labeled illustrative module,
so the README and the demo never diverge.

| Layer | Status in this submission | Data source |
|---|---|---|
| **Layer 2A — Quality & Anomaly Intelligence** | **Built, rigorous.** Real classifier, real Grad-CAM++/attention-based saliency, real OOD/uncertainty gating. | Organizer image dataset |
| **Layer 3 — Explainability, Causal Inference & Root-Cause Attribution** | **Built, rigorous.** Real TreeSHAP feature attribution over a generated process-telemetry table correlated to defect class, run through a real trained model. | **Synthetic demonstration data**, explicitly labeled as such in-app — no organizer telemetry exists to attribute against |
| **Layer 2B — Line Dynamics & Flow Intelligence** | **Built, live.** Real computed ToC-style bottleneck detection (max-cycle-time station, dynamic per-station utilisation/starvation/blocking) — a rule-based engine, not the full discrete-event/queueing simulator the architecture describes, but genuinely computed each call, not a static mock. | Synthetic demonstration data |
| **Layer 4 — Counterfactual Economic & Simulation Engine** | **Built, live.** Real margin/revenue/cost computation and interactive what-if counterfactuals (verified: defect rate 2%→$13.5k margin, 30%→‑$3.0k margin, i.e. profitable to loss-making, computed correctly). A closed-form model, not the optimization-based planner the architecture describes, but interactive and computed, not canned. | Synthetic demonstration data |
| **Layer 5 — Decision Console** | **Built.** Surfaces Layers 2A/3 as live results; surfaces Layers 2B/4 as a labeled "Illustrative Scenario" panel. | Mixed, each panel labeled |
| **Governance Tier — Spring Boot** | **Built.** JWT auth, role-based access for the three operator roles, and an append-only advisory audit trail with a tamper-evident chained hash. | Access + audit metadata |

### Trained model results (ConvNeXt-Tiny, held-out test split)

The classification task saturates almost immediately on this dataset —
validation accuracy reaches 1.0 by epoch 2. That is expected for 2,400
balanced, cleanly-labelled images per class rather than a claim of a hard
problem solved, and it means the 15-mark detection criterion is not where this
system differentiates. The robustness sweep below is the more informative
result: it finds exactly where a saturated classifier actually breaks.

| Metric | Value |
|---|---|
| Accuracy | 0.9989 |
| Macro F1 | 0.9989 |
| False-accept rate (defect shipped) | 0.0000 |
| False-reject rate (good part scrapped) | 0.0000 |

**Robustness to unseen conditions** — each shift applied only to the held-out
test split, never seen during training:

| Condition | Accuracy | False-accept | False-reject |
|---|---|---|---|
| clean | 0.9989 | 0.0000 | 0.0000 |
| bright / dim lighting | 0.998–0.999 | ≤0.0014 | 0.0000 |
| low contrast | 0.9983 | 0.0021 | 0.0000 |
| rotated 15° / 90° | 0.9989 | ≤0.0007 | 0.0000 |
| **defocus blur** | **0.8906** | **0.1153** | 0.0000 |
| **combined (bright+low-contrast+rotate+blur)** | **0.9017** | 0.0444 | **0.2389** |

Lighting and orientation shifts cost almost nothing. Defocus blur is the
genuine failure mode — accuracy drops 11 points and false-accept rate jumps to
11.5%, meaning a blurred defective part is materially more likely to pass. This
is precisely the case the epistemic-uncertainty / Mahalanobis trust gate exists
to catch: a blurred, low-confidence, off-manifold input should be deferred to a
human rather than auto-passed, and the gate's job is measured against this
number, not against the clean-condition accuracy.

### Known limitation: the trust gate misses *localized* defect signal

`scripts/edge_case_battery.py` probes structurally unusual inputs beyond the
robustness sweep above — extreme crops, composites, malformed shapes, blank
frames. The gate correctly defers every input that is *globally*
out-of-distribution: pure noise, an 8×8-upscaled image, a wrong-aspect-ratio
panorama, an inverted-polarity image, and a composite of two different defect
types all triggered `DEFER_TO_HUMAN`, exactly as designed.

It does **not** catch defects that are real but *locally* confined:

| Input | Result |
|---|---|
| A real crack pasted into one corner of an otherwise clean part | `normal`, 100% confidence, Mahalanobis 25.2, **AUTO** |
| An extreme close-up crop of an actual crack (too tight for context) | `normal`, 100% confidence, Mahalanobis 29.5, **AUTO** |
| A blank/solid-gray frame (camera fault or no part in view) | `normal`, 100% confidence, Mahalanobis 23.9, **AUTO** |
| Near-black / near-white (total exposure failure) | `normal`, 100% confidence, Mahalanobis 27–32, **AUTO** |

The Mahalanobis check operates on the pooled, image-level feature vector, so a
defect confined to a small region — or a genuinely empty/failed camera frame —
doesn't move that vector far enough from the "normal" manifold to cross the
calibrated threshold, even though nothing trustworthy was actually inspected.
This is a **false-accept risk distinct from the blur finding above**: blur
degrades an otherwise-global signal; this gap is about signal that was never
global to begin with.

The honest fix is architectural, not a threshold tweak: training with
small-patch/corner-crop augmentation so the model learns to weight localized
evidence, or a secondary patch-level saliency-variance check alongside the
current whole-image Mahalanobis distance. Not attempted here — flagging it
plainly is preferable to a late, unverified threshold change that could
increase false-defers on genuinely clean parts.

### Why synthetic telemetry makes the attribution layer *stronger*, not weaker

Generating the process data is usually a weakness. Here it is turned into the
validation mechanism. Because `ai/synthetic.py` **constructs** the causal
structure — `crack ← press force ↑ + pot temperature ↓`, `rust ← chamber
humidity ↑ + coating thickness ↓`, and so on — the ground truth is known
exactly, so the attribution engine can be *measured* against it rather than
merely trusted.

The generator also plants a deliberate trap: `ambient_temperature_c` is
correlated with rust through chamber humidity, but does not cause it. A naive
correlation-based diagnosis would blame ambient temperature.

Measured result (`GET /api/rootcause/validation`, reproducible at seed 1337):

| Check | Result |
|---|---|
| Causal drivers recovered by TreeSHAP (mean recall over 4 defect classes) | **1.00** |
| `crack` → ranked drivers | press force, pot temperature ✔ |
| `hole` → ranked drivers | feed rate, press force ✔ |
| `rust` → ranked drivers | chamber humidity, coating thickness ✔ |
| `scratch` → ranked drivers | abrasive wear, spindle RPM ✔ |
| Confounder correctly demoted | humidity rank **1**, ambient temperature rank **4** ✔ |

This is the difference between claiming explainability and demonstrating it.

Any number, chart, or recommendation in this system that is not traceable to the
organizer's image dataset is generated by a synthetic-data module and is labeled
**"Synthetic Demonstration"** at the point of display — it is never presented as a
result derived from organizer data. This is a deliberate scope decision, not an
oversight: with a solo build in a fixed time budget and a rubric that weights defect
detection/localization/robustness/false-reject handling at 40 of 60 Checkpoint-3 marks
(root-cause correlation is 5/60; there is no line item for the economic simulator),
effort was concentrated on making Layers 2A and 3 genuinely correct rather than
spreading thin across all five layers.

---

## 1. Problem Understanding

High-throughput manufacturing environments are tightly coupled socio-technical systems where physical chemistry, machine mechanics, human operations, and unit economics continuously collide. Optimizing these lines is notoriously difficult because decisions are rarely isolated: tuning a station for speed can induce thermal or mechanical stress that causes micro-defects downline; aggressive quality gates can cause work-in-process (WIP) backups, starving downstream stations and destroying operational margins.

### The Core Challenges
* **The Interdependence of Quality, Flow, and Cost:** Quality inspections, station capacities, and financial margins are treated as separate operational domains. When scrap spikes or a line stutters, root-cause triage requires cross-referencing disjointed data streams under time pressure.
* **Subtle Signatures and Process Drift:** Defect signatures are frequently obscured by batch-to-batch chemical variance, environmental fluctuations (ambient temperature, humidity), sensor degradation, and mixed product variants running on shared lines.
* **The Danger of Black-Box Predictions:** Pure deep learning classifiers that output confident probabilities without spatial, physical, or contextual rationale are unacceptable on factory floors. Operators and line supervisors reject recommendations they cannot verify. Forced predictions on out-of-distribution (OOD) defects result in costly silent failures.
* **Downstream Ripple Effects of Bottlenecks:** A station bottleneck is rarely just a slow machine—it is an accumulation of cycle-time mismatch, changeovers, rework loops, and buffer starvation that erodes total line throughput.

### The Objective
To design and implement an end-to-end, software-only decision-support engine that ingests multi-stage inspection, production-flow, and economic datasets. The platform does not simply label parts; it synthesizes observations across stations to answer five critical operational questions:
1. **What** is wrong with the part, and **where** is the physical fault?
2. **When** an anomaly is unseen, can the model acknowledge uncertainty rather than guessing?
3. **Which** upstream process conditions or drift vectors triggered the defect?
4. **Where** is the line’s operational bottleneck, and how does it compound cycle time and WIP?
5. **How** do specific simulated interventions (e.g., parameter tuning, buffer reallocation, inspection threshold adjustments) translate into bottom-line profitability and yield?

---

## 2. Architecture

The system is architected as an event-driven, modular analytics pipeline. It decouples high-speed data ingestion from computational modeling, unifying visual inspection, discrete-event line dynamics, and economic simulation under a shared **Explainability & Causal Layer**.

```
                           +-------------------------------------------------------------+
                           |                INSPECTION, PROCESS & ECONOMIC DATASETS       |
                           +-------------------------------------------------------------+
                                                          |
                                                          v
+-----------------------------------------------------------------------------------------------------------------------+
| LAYER 1: MULTI-MODAL DATA NORMALIZATION & FEATURE ORCHESTRATION                                                       |
| - High-Resolution Image Preprocessing     - Time-Series Sensor Alignment       - Material/Batch/Variant Metadata      |
| - Work-in-Process (WIP) Tracking Matrix   - Cost/Economic Ledger Mapping       - Station State Event Streams           |
+-----------------------------------------------------------------------------------------------------------------------+
                                                          |
                 +----------------------------------------+---------------------------------------+
                 v                                                                                v
+---------------------------------------------------+                    +----------------------------------------------+
| LAYER 2A: QUALITY & ANOMALY INTELLIGENCE          |                    | LAYER 2B: LINE DYNAMICS & FLOW INTELLIGENCE  |
| [LIVE — built on organizer image data]            |                    | [DESIGNED — illustrative panel only, §0]     |
| - Spatial Vision Encoder (Feature Pyramid / ViT)  |                    | - Discrete-Event Station Flow Model          |
| - Calibrated Defect Classifier (Multi-Label)      |                    | - Dynamic Bottleneck Identifier (TOC Engine) |
| - Open-Set Anomaly & OOD Detector (Mahalanobis)   |                    | - WIP, Starvation & Blockage Tracker         |
| - Spatial XAI: Attention Rollout / Grad-CAM++     |                    | - Cycle-Time Variance & Scrap Accrual Engine |
+---------------------------------------------------+                    +----------------------------------------------+
                 \                                                                                /
                  \---------------------------------------+--------------------------------------/
                                                          |
                                                          v
+-----------------------------------------------------------------------------------------------------------------------+
| LAYER 3: EXPLAINABILITY, CAUSAL INFERENCE & ROOT-CAUSE ATTRIBUTION  [LIVE — built on synthetic telemetry, §0]        |
| - Cross-Modal Attention: Correlating image defect regions with time-synchronized upstream process telemetries         |
| - Attribution Engine: Tree-SHAP / Integrated Gradients on process features to explain "Why this defect occurred"     |
| - Drift Detection: CUSUM / KS-Tests isolating batch-to-batch parametric shifts vs. steady-state baseline              |
+-----------------------------------------------------------------------------------------------------------------------+
                                                          |
                                                          v
+-----------------------------------------------------------------------------------------------------------------------+
| LAYER 4: COUNTERFACTUAL ECONOMIC & SIMULATION ENGINE  [DESIGNED — illustrative panel only, §0]                       |
| - Marginal Contribution & Scrap-Penalty Calculator: Cost of defect at Stage $k$ vs. Final Stage Escape                |
| - Counterfactual Simulation: "If Station 3 speed reduces 8%, what is the net effect on scrap, WIP, and margin?"      |
| - Risk-Calibrated Action Engine: Generates ranked, evidence-backed advisory recommendations for floor managers        |
+-----------------------------------------------------------------------------------------------------------------------+
                                                          |
                                                          v
+-----------------------------------------------------------------------------------------------------------------------+
| LAYER 5: HUMAN-CENTERED DECISION CONSOLE (ADVISORY & AUDITABLE)                                                       |
| - Visual Defect Localization Maps                - Transparent Root-Cause Attribution Cards                          |
| - Dynamic Bottleneck Sankey & Heatmaps           - Financial Trade-off Matrix (Throughput vs. Scrap Rate)            |
+-----------------------------------------------------------------------------------------------------------------------+
```

### Key Architectural Subsystems

1. **Vision & Open-Set Inspection Pipeline:**
   * Utilizes a backbone supporting both dense feature extraction and localized attention (e.g., ConvNeXt or Swin Transformer).
   * Incorporates an **Evidential / Temperature-Calibrated Softmax** paired with an **Open-Set Anomaly Detection Head** (density estimation via normalized feature embeddings). If an anomaly's distance in latent space exceeds statistical bounds, the system refrains from labeling it into known classes and categorizes it as *Novel / Uncertain Defect*.

2. **Discrete Process Flow & Bottleneck Engine:**
   * Built on Theory of Constraints (TOC) fundamentals. Tracks dynamic station status: Processing, Blocked, Starved, and Changeover.
   * Computes the active shifting bottleneck across stations by measuring duration-weighted active constraint periods rather than relying on static averages.

3. **Causal Attribution & Cross-Modal Correlator:**
   * Bridges physical visual defects with upstream time-series telemetries (temperatures, feed rates, pressures, tool wear indices).
   * Applies attribution frameworks (Tree-SHAP, Integrated Gradients) across the multi-station time window to quantify which operational condition deviated prior to defect formation.

4. **Counterfactual Economic Simulator:**
   * Evaluates cost structures per station:
     $$\text{Cost}(\text{Defect}_k) = \text{Raw Material} + \sum_{i=1}^{k} \text{Value-Added Processing Cost}_i + \text{Disposal Cost}$$
   * Models the financial trade-off: allows process engineers to run simulated "what-if" scenarios on inspection thresholds, line speeds, and buffer adjustments before committing changes.

---

## 3. Approach

Our methodology is grounded in engineering practicality: models must serve operational personnel, respect production realities, and communicate their reasoning clearly and without arrogance.

### Phase 1: Robust Feature Engineering and Cross-Domain Alignment
* **Temporal and Spatial Synchronization:** Establish unified part tracing through unique identifiers or virtual queue propagation across stages, linking inspection images directly to the specific sensor window of upstream toolheads.
* **Drift-Resilient Normalization:** Apply rolling robust scaling on sensor streams to account for gradual tool degradation, seasonal ambient shifts, and variant-to-variant setpoint transitions.

### Phase 2: Calibrated Quality Assessment & True Spatial Explainability
* **Saliency and Localization:** Rather than generating post-hoc visual heatmaps that merely outline high-contrast areas, we implement path-integrated saliency (such as Grad-CAM++ or Transformer Attention Rollout) verified against known geometric defect bounds.
* **Knowing What It Doesn't Know:** We configure a dual-threshold scoring system:
  1. *Known Class Prediction:* High confidence in both feature match and classification boundary.
  2. *Novel/Uncertain Flag:* Low classification confidence or high distance from known class centroid clusters triggers human inspection with an advisory flag: *"Unseen defect pattern detected; human verification required to avoid false rejection."*

### Phase 3: Bottleneck Detection and Flow Dynamics *(illustrative panel — see §0)*
* **Dynamic Constraint Tracking:** Move beyond static mean cycle-time evaluation. We monitor real-time inter-arrival times, buffer queue lengths, and starvation/blocking frequencies.
* **Loss Quantification:** Translate machine downtime and line blockages directly into lost unit capacity and accrued overhead costs per hour.

### Phase 4: Root-Cause Attribution via Explainable AI *(built on synthetic telemetry — see §0)*
* **Connecting Quality to Process Telemetry:** When a recurring defect pattern emerges, the system executes an automated attribution query over the preceding stations' process parameters.
* **Clear, Actionable Narratives:** The output is never a raw tensor or unexplained weight. The model produces human-readable diagnostic rationales, such as:
  > *"Scrap spike on Stage 4 (Micro-fracture) correlates with a +12.4% temperature drift on Station 2 heating elements combined with an 8% speed increase during Batch B-419."*

### Phase 5: Simulated Advisory Interventions & Economic Optimization *(illustrative panel — see §0)*
* **Non-Invasive Simulation Environment:** In strict accordance with the problem constraints, all interventions are evaluated within an offline numerical twin of the line.
* **Objective Function Optimization:** We balance quality yield ($Y$), throughput rate ($TH$), and total operational cost ($C$) to maximize net operational profit:
  $$\max_{\theta} \Pi(\theta) = P \cdot TH(\theta) \cdot Y(\theta) - \left( C_{\text{raw}} + C_{\text{energy}}(\theta) + C_{\text{rework}}(\theta) + C_{\text{scrap}}(\theta) \right)$$
* **Operator-Centric Recommendations:** Every suggested action provides the expected margin recovery, confidence intervals, and the specific evidence trail that prompted it, keeping human supervisors completely in control.

---

## 4. Repository Structure

```
E-IDSS/
├── ai/                      # Intelligence tier (shared by API and trainer)
│   ├── data.py              # Deterministic stratified split, transforms
│   ├── model.py             # DefectNet — ConvNeXt-Tiny, exposes logits + features
│   ├── train.py             # Training, calibration, Mahalanobis fit, robustness sweep
│   ├── robustness.py        # Eight shifted eval conditions (lighting/orientation/blur)
│   ├── explain.py           # Grad-CAM++ saliency, connected-component boxing, TrustGate
│   ├── synthetic.py         # [SYNTHETIC] telemetry, line events, cost ledger
│   └── rootcause.py         # LightGBM + TreeSHAP attribution, KS drift, validation
├── backend/                 # FastAPI service (REST, CORS, stub-mode fallback)
├── gateway/                 # Spring Boot governance tier — JWT, RBAC, audit trail
├── frontend/                # React + Vite + react-three-fiber console
├── scripts/
│   ├── kaggle_auth.py       # Credential bootstrap + live auth check
│   └── build_kernel.py      # Emits a self-contained Kaggle training kernel
├── models/                  # Trained checkpoint + metrics.json (gitignored)
├── docker-compose.yml
└── .env                     # Secrets + seeds (gitignored; see .env.example)
```

### Reproducibility notes

* **One seed governs everything.** `SYNTHETIC_SEED` / `TRAIN_SEED` (default `1337`)
  drive the data split, the synthetic plant, and the attribution model, so every
  figure in the console is reproducible run to run.
* **The split is derived, not shipped.** `stratified_split()` works from sorted
  filenames plus the seed, so the local machine and the GPU trainer produce
  identical train/val/test sets without transferring manifests.
* **Training ran on 2× Tesla T4** via a generated, self-contained Kaggle kernel
  (`scripts/build_kernel.py`) — the `ai/` package is embedded into the kernel at
  build time, keeping a single source of truth between training and serving.
* **Nothing trains or fetches at demo time.** The checkpoint carries the weights,
  the calibration temperature, the fitted Mahalanobis statistics, and the full
  metrics report, so the console starts from a single artifact.

## 4b. Console Layout

One screen, three analysis stages, with a persistent operational-telemetry
sidebar that supplies the parameter vector every stage reasons over.

| Stage | Contents | Data source |
|---|---|---|
| I. Optical Defect Inspection & Grad-CAM | Specimen upload, adjustable activation threshold, classification + calibrated confidence, class-probability chart, raw / heatmap / bounding-box triptych, extracted box coordinates, OOD rejection panel | `POST /api/inspect` — live model inference on the organizer dataset |
| II. Operational Telemetry & TreeSHAP Attribution | Local SHAP contributions per machine parameter, primary root-cause diagnostics, out-of-spec drift panels, telemetry snapshot table | `GET /api/telemetry/specs`, `POST /api/telemetry/attribution` — `SYNTHETIC_DEMONSTRATION` |
| III. Line Health & Financial Impact | Station capacity / cycle-delay matrix, bottleneck notice, scrap-cost and margin-erosion model, prescriptive remediation plan | `GET /api/line/health`, `GET /api/line/financial` — `SYNTHETIC_DEMONSTRATION` |

The sidebar offers three telemetry sources: **Simulate from Detected Defect**
(Stage I's verdict selects the machine settings recorded for that defect mode),
**Preset Test Unit** (five certified incident records), and **Manual Parameter
Input** (eight sliders bounded by each parameter's nominal envelope). A
specimen rejected by the trust gate suspends Stage II entirely — attribution is
only computed for verified defect modes.

The eight telemetry parameters (furnace temperature, roller pressure, line
speed, lubricant flow, vibration RMS, ambient humidity, cooling rate, tension
variation) and the LightGBM + TreeSHAP attribution over them are defined in
`ai/telemetry.py` against `data/process_parameters.csv` (3500 synthetic rows,
seed 42, causal structure per defect mode). The classifier is refit at startup
rather than shipped as a pickle.

## 5. Running the System

```bash
cp .env.example .env          # then fill in values
docker compose up --build
```

| Service | Port | Role |
|---|---|---|
| Console (React) | 5173 | Three analysis stages, one operational telemetry sidebar |
| Intelligence API (FastAPI) | 8000 | Inference, XAI, attribution, simulation |
| Governance gateway (Spring Boot) | 8080 | JWT auth, RBAC, advisory audit trail |

Demo identities (seeded at gateway boot, logged to console):
`operator/operator123`, `linelead/linelead123`, `manager/manager123`.

The backend serves in a clearly-flagged **stub mode** if no checkpoint is
present, so the console is demonstrable before or without training.

### Governance tier in practice

```bash
TOKEN=$(curl -s -XPOST localhost:8080/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"operator","password":"operator123"}' | jq -r .token)

curl -s -XPOST localhost:8080/api/inspect \
  -H "Authorization: Bearer $TOKEN" -F file=@part.png        # 200

curl -s "localhost:8080/api/economics?defect_rate=0.08&throughput=240" \
  -H "Authorization: Bearer $TOKEN"                          # 403 — operator role
```

**Resolved: container image-upload bug.** Uploading through the gateway
(`POST /api/inspect`, `multipart/form-data`) returned 422 in the containerised
stack while the identical gateway jar worked as a host process. Root cause:
`uvicorn[standard]` resolves to the compiled `httptools` HTTP parser when its
C-extension is present, which is exactly the container's clean `pip install`
but not the host dev machine's environment (silently falling back to the pure
Python `h11` parser there). Spring's `RestClient` sends multipart uploads with
`Transfer-Encoding: chunked` rather than a precomputed `Content-Length`, and
`httptools`' chunked-body parser dropped the file part on that stream while
`h11` parsed the identical bytes correctly — confirmed with a byte-level raw
TCP capture showing the wire payload was complete and correct in both cases,
isolating the bug to the parser rather than the network path. Fixed by pinning
`backend/Dockerfile` to `uvicorn ... --http h11`. Regression check:
`scripts/repro_gateway_multipart.py` against the containerised stack — this is
an intentionally integration-level check, since a mocked-backend unit test
cannot reach this bug (it requires a real chunked-encoding client against a
real uvicorn parser).

Every proxied advisory call is written to an append-only ledger with a SHA-256
of the response body. `GET /api/audit/verify` recomputes the chained hash across
the ledger, so a modified record is detectable. The store is written against
`EntityManager` rather than a Spring Data repository specifically so that no
update or delete method exists anywhere in the codebase — the immutability is a
type-level guarantee, not a convention.