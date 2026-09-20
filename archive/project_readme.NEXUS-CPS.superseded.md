> **Superseded.** This early-draft architecture ("NEXUS-CPS") has been consolidated into
> `readme_E-IDSS.md` at the project root, which is the canonical architecture doc for this
> submission. Kept here for history only — do not build against this file.

# NEXUS-CPS: Causal & Explainable Industrial Decision-Support System

> **A software-only, closed-loop advisory intelligence platform unifying visual defect localization, dynamic bottleneck discovery, and plant margin simulation.**

## 1. Executive Summary & Philosophy

In modern high-throughput discrete and batch manufacturing, quality, throughput, and unit economics do not fail in isolation—they interact dynamically. Traditional operational technology (OT) stacks fracture these domains:

* **Isolated Quality Inspection:** Vision models classify defects as black boxes without explaining spatial rationale or connecting failures to upstream machine drift.

* **Disconnected Process Diagnostics:** SCADA and MES dashboards track cycle times and machine states without understanding how micro-stoppages and rework loops penalize downstream buffers.

* **Retrospective Accounting:** Financial reporting quantifies scrap and margin degradation days or weeks after production runs, rather than projecting real-time financial impact during active line drift.

**NEXUS-CPS** bridges these islands into a unified decision-support engine. Built upon **Explainable AI (XAI)**, **Structural Causal Models (SCM)**, and **Discrete-Event Simulation (DES)**, the platform shifts industrial management from reactive triage to predictive, evidence-based counterfactual intervention.

## 2. Core Architecture

The platform operates as a 4-tier computational pipeline designed strictly for read-only ingestion, offline simulation, and human-in-the-loop advisory.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               MULTI-STAGE DATA INGESTION                               │
│  ├── Optical/Inspection Streams: Surface scans, multi-spectral images, spatial masks   │
│  ├── Machine & Process Telemetry: Thermocouples, vibration, spindle RPM, pressure     │
│  ├── Event Logs & Tracking: Station cycle times, buffer states, WIP, batch changes     │
│  └── Economic Ledgers: Bill of Materials (BOM), scrap penalties, hourly energy tariffs │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               CORE INTELLIGENCE ENGINE                                 │
│                                                                                        │
│  ┌─────────────────────────────────────┐   ┌────────────────────────────────────────┐  │
│  │ Tier 1: Trust-Gated Inspection      │   │ Tier 2: Flow & Capacity Engine         │  │
│  │ ├─ Spatial Localization & Saliency  │   │ ├─ Active Utilization & Starvation     │  │
│  │ ├─ Epistemic OOD Detection ($u_e$)  │   │ ├─ Shifting Bottleneck Detection (ToC) │  │
│  │ └─ Defect Family Categorization     │   │ └─ Cycle-Time Drift Tracking           │  │
│  └──────────────────┬──────────────────┘   └───────────────────┬────────────────────┘  │
│                     │                                          │                       │
│                     └────────────────────┬─────────────────────┘                       │
│                                          ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Tier 3: Causal Attribution & Root-Cause Layer                                    │  │
│  │ ├─ Structural Causal Modeling (DAG-based Do-Calculus)                            │  │
│  │ ├─ Sensor-to-Defect Feature Attribution (TreeSHAP & Integrated Gradients)        │  │
│  │ └─ Plain-Language Diagnostic Translation                                         │  │
│  └───────────────────────────────────────┬──────────────────────────────────────────┘  │
│                                          ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Tier 4: Economic Sensitivity & Counterfactual Simulator                          │  │
│  │ ├─ Dynamic Unit-Level Margin Modeling                                            │  │
│  │ ├─ Scrap, Rework, & Energy Cost Penalty Aggregation                              │  │
│  │ └─ "What-If" Counterfactual Intervention Planner                                 │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                            DECISION SUPPORT CONSOLE (UI)                               │
│  ├── Operator View: Annotated Defect Saliency Heatmaps + Epistemic Confidence Bands    │
│  ├── Line Lead View: Dynamic Flow Topology, Starvation Maps, & Bottleneck Alerts       │
│  └── Plant Manager View: Financial Margin Projection & Counterfactual Interventions    │
└────────────────────────────────────────────────────────────────────────────────────────┘

```

## 3. Methodological Pillars

### 3.1 Trust-Calibrated Visual Inspection (Tier 1)

High-speed classifiers frequently hallucinate confidence when confronted with novel defects, lighting variances, or camera lens smudges. NEXUS-CPS embeds active safety bounds:

* **Spatial Attribution:** Computes fine-grained pixel attribution via Grad-CAM++ and Integrated Gradients, outputting heatmaps alongside predicted defect bounding boundaries.

* **Epistemic Uncertainty Gating:** Uses Monte Carlo Dropout and Deep Evidential Regression to quantify epistemic uncertainty $u_e$:
  

  $$
  u_e = \frac{1}{M} \sum_{m=1}^{M} \left( \hat{y}_m - \bar{y} \right)^2
  $$

  
  If $u_e \ge \tau_{\text{novelty}}$, the system refuses to force an arbitrary label. It flags the part as **"Novel / Anomalous Defect Signature"** and routes it to an active learning queue.

### 3.2 Causal Root-Cause Attribution (Tier 2 & 3)

Correlation on a factory floor is misleading (e.g., ambient shop floor temperature correlating with downstream finish defects).

* **Directed Acyclic Graphs (DAG):** Encodes the physical dependencies across manufacturing stages.

* **Interventional Inference:** Leverages Pearl's $do$-calculus to isolate the genuine root cause:
  

  $$
  P(\text{Defect} \mid do(\text{Parameter}_k = v))
  $$

* **Operator Summaries:** Translates Shapley additive attributions ($-\phi_i, +\phi_i$) into plain human language:

  > *"Part #L-8820 flagged with Micro-Porosity (96.2% confidence). Primary root cause: Stage 2 Solder Pot Temperature drifted* $+6.8^\circ\text{C}$ *above nominal (Attribution:* $+54\%$*). Feed rate at Stage 1 contributed* $+21\%$*."*

### 3.3 Dynamic Line Flow & Bottleneck Discovery (Tier 2)

Static throughput analysis fails during mixed-model production runs.

* Evaluates instantaneous buffer states ($B_t$), station cycle-time variance ($\sigma_{\text{cycle}}^2$), and starvation/blocking probabilities.

* Identifies primary and shifting bottlenecks under shifting product variants using Theory of Constraints (ToC) principles.

### 3.4 Economic Modeling & Counterfactual Simulator (Tier 4)

Operational changes always carry trade-offs. Slowing down a station may reduce scrap but starve downstream assembly.

* **Net Margin Function:**
  

  $$
  \Pi = \sum_{i=1}^{N} \left[ P_i \cdot Y_i - \left( C_{\text{raw}, i} + C_{\text{energy}, i} + C_{\text{labor}, i} + \mathbb{I}_{\text{rework}} \cdot C_{\text{rework}} + \mathbb{I}_{\text{scrap}} \cdot C_{\text{scrap}} \right) \right]
  $$

* **Counterfactual Advisory:** Allows engineers to evaluate interventions prior to physical deployment:

  > *"Advisory: Decreasing feed rate at CNC-03 by 8% will lower micro-cracking by 34%, yielding a net margin gain of* $+\$4,120/\text{shift}$ *despite a* $2.1\%$ *reduction in gross line speed."*

## 4. Repository Structure

```
nexus-cps/
├── configs/
│   ├── line_topology.yaml        # Station nodes, buffers, and dependencies
│   ├── model_params.yaml         # Vision models, XAI methods, and OOD thresholds
│   └── cost_structure.yaml       # BOM costs, energy rates, and scrap costs
├── data/
│   ├── raw/                      # Organizer-provided datasets (telemetry, images, logs)
│   └── processed/                # Normalized tensors and aligned time-series
├── src/
│   ├── inspection/
│   │   ├── detector.py           # Segmentation and classification architectures
│   │   └── uncertainty.py        # Epistemic & aleatoric uncertainty estimation
│   ├── process_flow/
│   │   ├── flow_analyzer.py      # WIP, cycle-time variance, starvation tracking
│   │   └── bottleneck_engine.py  # Shifting bottleneck detection algorithms
│   ├── xai/
│   │   ├── visual_saliency.py    # Grad-CAM++, Integrated Gradients overlays
│   │   ├── tabular_shap.py       # TreeSHAP and KernelSHAP for sensor telemetry
│   │   └── causal_dag.py         # Structural causal model and do-calculus solver
│   ├── economics/
│   │   ├── margin_calculator.py  # Unit-level cost and profit impact model
│   │   └── counterfactual.py     # "What-if" scenario optimization solver
│   └── advisory/
│       └── report_generator.py   # Natural-language operator recommendations
├── dashboard/
│   ├── app.py                    # Multi-view decision-support dashboard
│   └── components/               # Heatmaps, topology charts, and financial dials
├── notebooks/
│   ├── 01_eda_and_alignment.ipynb
│   ├── 02_causal_graph_validation.ipynb
│   └── 03_xai_faithfulness_benchmarks.ipynb
├── tests/
│   ├── test_uncertainty_gate.py
│   ├── test_bottleneck_detection.py
│   └── test_economic_model.py
├── requirements.txt
├── LICENSE
└── README.md

```

## 5. Quick Start Guide

### Prerequisites

* Python 3.10 or higher

* Recommended: NVIDIA GPU with CUDA 11.8+ (CPU fallback supported for all modules)

### Step 1: Environment Setup

```
# Clone the repository
git clone https://github.com/your-team/nexus-cps.git
cd nexus-cps

# Create and activate a clean environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

```

### Step 2: Ingest and Validate Datasets

```
python -m src.inspection.ingest --data-dir ./data/raw/ --validate-schema

```

### Step 3: Run the Full Advisory Pipeline

Execute batch analysis across inspection, process flow, and economics:

```
python main.py \
  --config configs/line_topology.yaml \
  --compute-saliency \
  --evaluate-bottlenecks \
  --simulate-interventions

```

### Step 4: Launch the Decision-Support Console

```
streamlit run dashboard/app.py

```

Open your browser at `http://localhost:8501` to explore the interactive operator and manager console.

## 6. Evaluation & Validation Benchmarks

The system is evaluated against four balanced axes to prove real-world viability:

| **Evaluation Dimension** | **Metric** | **Benchmark Target** | **Description** | 
| **Visual Accuracy** | Macro F1-Score | $\ge 0.92$ | Robust performance across extreme defect imbalance | 
| **Novelty Awareness** | AUROC (OOD Gate) | $\ge 0.90$ | Rejects novel/unseen defects without guessing | 
| **XAI Faithfulness** | Pixel Deletion AUC | $\le 0.12$ | Confirms heatmaps track true physical defect features | 
| **Bottleneck Precision** | Top-1 Station Match | $\ge 0.89$ | Accurately identifies current throughput-limiting constraint | 
| **Financial Fidelity** | Profit MAPE | $\le 3.8\%$ | Accurate margin projections under observed scrap rates | 

## 7. Safety, Constraints, and Ethical Boundary

* **Strictly Software-Only Advisory:** In strict accordance with competition rules, NEXUS-CPS connects to no physical PLCs, actuators, or live machine controls.

* **Human-in-the-Loop:** All counterfactual interventions, setpoint adjustments, and routing suggestions are advisory. The final authority remains with qualified industrial process engineers.

* **Data Privacy:** Raw operational telemetry and visual models can be executed entirely on-premise without third-party cloud data transmission.

## 8. License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.