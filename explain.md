# E-IDSS, Explained in Plain English

This document explains the project without jargon. If a technical word shows
up, it gets explained right there.

---

## 1. The problem

Factories make parts. Some parts come out damaged — cracked, scratched,
rusted, or with holes punched where there shouldn't be any. Right now, a human
usually sits and looks at parts to catch the bad ones. That is slow, it is
boring, and tired people miss things.

The obvious fix is "use AI to spot the defects." But that fix, done naively,
creates three new problems that are worse than the one it solved.

### Problem A: Nobody trusts a number

Say the AI looks at a part and says **"crack, 97% sure."**

The operator's reasonable next question is: *where?* And: *why should I believe
you?* A number on its own gives them nothing to check. So they either ignore
the AI, or they trust it blindly. Both are bad.

### Problem B: AI doesn't know what it doesn't know

This is the dangerous one.

An AI trained on five kinds of metal surface will, if you show it a photo of a
dog, confidently tell you the dog is a scratch. It has no concept of "I have
never seen anything like this before." It only knows how to pick the
best-matching option out of the five it was taught.

On a factory floor this means a camera knocked out of alignment, a lens smeared
with oil, or a new part type nobody told the system about — all of these
produce confident, wrong answers. Silently. That is how you scrap a good batch
or ship a bad one.

### Problem C: Finding the defect doesn't fix anything

Even if the AI perfectly catches every cracked part, you still have a machine
somewhere producing cracked parts. Catching them is damage control. Nobody has
told you **which machine, which setting, and how much it is costing you.**

A quality report that says "8% defect rate" is a fact. It is not a decision.
The person reading it still has to figure out what to do.

---

## 2. What we were actually given

The competition provided a dataset: **12,000 images**, sorted into five
folders — crack, hole, normal, rust, scratch. 2,400 images each.

That's it. Images and folder names.

**No** labels saying where in the image the defect is. **No** machine sensor
readings. **No** production line logs. **No** cost data.

But the problem statement asks for root-cause analysis, bottleneck detection,
and profitability impact — all of which need exactly the data we don't have.

So we had a choice to make, and it's the most important decision in this
project.

### The choice

**Option 1:** Build only what the images support, and ignore the rest of the
problem statement. Honest, but answers maybe half the question.

**Option 2:** Generate the missing data and quietly present the whole thing as
if it were real. Looks impressive until a judge asks one pointed question, and
then the entire project's credibility is gone.

**Option 3 — what we did:** Build everything, generate the data we're missing,
and **label it as generated, everywhere, permanently.**

Every single response from the parts of the system running on generated data
carries a tag: `SYNTHETIC_DEMONSTRATION`. The screen shows an orange badge
saying **"Synthetic Demonstration Data"** on every panel that displays it. You
cannot look at this system and be confused about what is measured and what is
simulated.

This turned out to be a strength, not a compromise. Explained in section 4.

---

## 3. How we solved it

Four pieces, each answering one of the operator's real questions.

### Piece 1: "What is it?" — the classifier

A **neural network** (a program that learns patterns from examples rather than
following rules someone wrote) looks at the image and picks one of the five
categories.

We used an architecture called **ConvNeXt-Tiny**. "Architecture" here means the
blueprint for how the network is wired. "Tiny" means it's the small version —
it runs fast on an ordinary computer instead of needing a server farm.

We didn't train it from scratch. It came already knowing how to see general
visual things — edges, textures, shapes — from having been trained on millions
of ordinary photographs. We then retrained the last part of it on our metal
surfaces. This is called **transfer learning**, and it's why the whole thing
trained in hours on one desktop graphics card instead of weeks on a cluster.

**One extra step that matters: calibration.**

Neural networks are chronically overconfident. Left alone, one will say "99%
sure" about things it gets wrong a quarter of the time. That makes the
confidence number useless — you can't set a threshold on a number that lies.

So after training, we measured how wrong the confidence was and applied a
correction factor (a single number, 0.344, stored with the model). Now when it
says 80%, it's actually right about 80% of the time. The number means
something.

### Piece 2: "Where is it?" — the heatmap

Here's the honest constraint: the dataset never told us where defects are. It
only said "this image contains a crack," never "the crack is at these
coordinates."

So we can't train the model to draw boxes. We have to ask it a different
question — **which parts of this image did you actually look at when you
decided?**

There's a technique for this called **Grad-CAM++**. Roughly: you look inside
the network at the moment it makes its decision and measure which image regions
pushed that decision hardest. Turn those measurements into a colour overlay —
red where the model looked hardest, blue where it ignored — and you get a
heatmap showing the model's reasoning painted onto the part.

Then we draw a box around the hottest connected region.

One detail worth mentioning, because it's a bug we hit and fixed. The first
version drew a box around *every* pixel above the threshold. When the model's
attention was scattered across the image, that produced a box around the whole
image — technically correct, completely useless. Now we find all the separate
hot regions and box only the biggest connected one. The box is tight around the
actual defect.

The threshold is a slider in the interface. Drag it and the box re-extracts on
the server — it's a real control, not decoration.

**What this honestly is:** a region derived from the model's attention. It is
not a trained defect detector, because we had no box labels to train one. We
say so rather than implying otherwise.

### Piece 3: "Should I trust this?" — the trust gate

This is the part solving Problem B, and it's the piece I'd point at first.

Two independent checks run on every image. Both have to pass.

**Check 1 — Does this look like anything I've seen?**

While training, we recorded what each of the five categories "looks like" to
the network internally — an average fingerprint per class. For a new image, we
measure how far its fingerprint sits from the nearest of those five.

(The measurement is called **Mahalanobis distance**. The only thing that
matters about the name is that it accounts for the fact that some features
naturally vary a lot and others barely vary at all, so it doesn't get fooled by
normal variation.)

A photo of a dog lands enormously far from all five metal-surface fingerprints.
Too far, and we reject it.

**Check 2 — Does the model agree with itself?**

We run the same image through the network **twenty times**, randomly switching
off different parts of the network each time. (This is **MC-dropout** — "dropout"
being the switching-off, "MC" for the repeated random sampling.)

If the model genuinely recognises the defect, all twenty runs agree. If it's
essentially guessing, the answers scatter. Disagreement across the twenty runs
is a direct measure of *"the model is unsure."*

**If either check fails**, the system does not classify. It returns
`DEFER_TO_HUMAN` and the screen shows a red panel: *"Specimen rejected — no
prediction generated,"* with the exact numbers that triggered it.

This came from a real test. We fed the system a passport photo of a person. The
trust gate correctly flagged it as out-of-distribution — but the first version
of the interface **still drew a confident "SCRATCH" box on the man's face**. The
backend was right and the screen was lying. We fixed the screen: when the gate
fires, the box is suppressed, the confidence is visually greyed out, and an
explicit note says these numbers are not trustworthy.

**A limitation we documented rather than hid:** the gate is good at catching
wholly wrong images (a dog, a landscape, a face). It is weaker on a *correct*
metal part carrying a defect type it's never seen — because most of the image
still looks completely normal, and the unfamiliar part is a small patch. The
overall fingerprint stays close enough to pass. This is written up with
evidence in the architecture document instead of being left for someone to
discover.

### Piece 4: "Why did it happen, and what's it costing?"

Catching the defect is where most projects stop. This is the part that turns a
finding into a decision.

**The setup.** A real steel line has sensors — furnace temperature, roller
pressure, line speed, lubricant flow, vibration, humidity, cooling rate, strip
tension. Eight things you can measure and eight things you can adjust.

We didn't get that data, so we generated it — with real physics built in:

- Crack ← furnace too hot + cooling too fast + rolling force too high
- Scratch ← bearings vibrating + not enough lubricant + line running too fast
- Rust ← humidity too high + not enough lubricant + line running too slow
- Hole ← pressure spike + tension surge

3,500 production units' worth, from a fixed random seed so it's identical every
run.

**The model.** A second, much simpler model (**LightGBM** — a decision-tree
model, basically a large flowchart of yes/no questions learned from data)
learns to predict defect type from those eight sensor readings alone.

**The explanation.** Then **TreeSHAP** takes any single prediction apart and
says exactly how much each of the eight parameters contributed. Not "these
things correlate" — *this specific unit cracked, and here is how much of the
blame each setting carries.*

The screen shows this as a bar chart. Dark red bars push toward the defect,
navy bars protect against it, and each one is labelled with its exact
contribution. Alongside it: which parameters are outside their safe operating
range and by what percentage.

**Then the money.** How many units per day, at what defect rate, at what cost
per scrapped unit — that produces daily and monthly loss figures. And a
remediation plan with specific setpoints: *reduce rolling force by 14.5 bar,
lower the annealing temperature by 22°C, increase emulsion flow by 6.5 L/h.*

That's the difference between a report and a decision.

---

## 4. Why generated data makes this stronger, not weaker

This sounds like a rationalisation. It isn't, and here's the concrete reason.

With real factory data, if the model says "humidity caused the rust," **nobody
can check.** You'd need to go find out what actually caused it, which is the
whole reason you built the tool.

Because *we* wrote the rules that generate this data, we know the true answer
for every single unit. So we can grade the explanation.

We do, and the system reports it. Ask the system to attribute all the rust
cases: it identifies humidity as the driver. **Recall 1.0** — it finds the true
causes every time.

There's a harder test built in, deliberately. In our generated data, ambient
temperature *correlates* with rust — but only because it moves together with
humidity. It doesn't cause rust. Humidity does. This is a **confounder**, and
confusing correlation with causation here is exactly the failure mode that
makes root-cause AI worthless in practice.

The system ranks humidity **1st** and ambient temperature **4th**. It isn't
fooled.

That check runs on every startup and is exposed at `/api/rootcause/validation`,
so anyone can verify the claim instead of taking our word for it.

You cannot do this with real data. The explainability here is **measured**, not
asserted.

---

## 5. The architecture — three services, and why

```
   Browser                 Gateway                   Brain
  ┌────────┐            ┌────────────┐          ┌──────────────┐
  │ React  │───────────▶│ Spring Boot│─────────▶│   FastAPI    │
  │ :5173  │            │   :8080    │          │    :8000     │
  └────────┘            └────────────┘          └──────────────┘
   what you sees        who's allowed           the actual AI
                        + audit log
```

Three separate programs, each doing one job. Why not one?

**The brain (FastAPI, Python, port 8000).** Runs the AI. Python because every
machine-learning library in existence is Python. This service knows nothing
about users or permissions — it answers questions about images and numbers.

**The gatekeeper (Spring Boot, Java, port 8080).** Handles who is allowed to
see what. Three roles: an **operator** can inspect parts but cannot see
financial data; a **line lead** adds telemetry and root cause; a **plant
manager** sees everything.

It also keeps an **audit trail**, and specifically a tamper-evident one. Each
recorded entry includes a fingerprint of the previous entry, so the entries form
a chain. Alter any past record and every fingerprint after it stops matching.
You can't quietly rewrite history. `GET /api/audit/verify` recomputes the whole
chain on demand.

This matters because the system gives advice that costs money. Six months later
somebody will ask *"who approved that change?"* — and there's an answer.

**The screen (React, port 5173).** What people actually use.

**Why split them?** Separation of concerns, in one concrete sentence: the AI
code has no idea what a user role is, and the permission code has no idea what
a neural network is. Either can be replaced without touching the other. It also
means the security logic sits in Java's mature, battle-tested ecosystem rather
than being hand-rolled inside the AI service.

---

## 6. The tech stack, and why each piece

| Thing | What it is | Why it's here |
|---|---|---|
| **Python** | Programming language | Every ML library is written for it |
| **PyTorch** | Neural network library | Industry standard for training and running networks |
| **ConvNeXt-Tiny** | The network blueprint | Modern, accurate, small enough to run without a GPU |
| **FastAPI** | Python web framework | Fast, and auto-generates API documentation |
| **LightGBM** | Decision-tree model | Excellent on table-shaped data, trains in a few seconds |
| **SHAP** | Explanation library | Mathematically grounded — the contributions actually sum correctly |
| **Java + Spring Boot** | Language + web framework | The standard for enterprise security and access control |
| **JWT** | Login token standard | Proves who you are on each request without server-side sessions |
| **React** | UI library | Builds the interface as reusable pieces |
| **TypeScript** | JavaScript + type checking | Catches mistakes before the code runs, not after |
| **Vite** | Build tool | Near-instant reloads while developing |
| **Recharts** | Charting library | The probability and SHAP bar charts |
| **Docker Compose** | Container orchestration | One command starts all three services, in the right order |

### On Docker specifically

Without it, running this means: install Python 3.13, install PyTorch, install
Java 17, install Maven, install Node, run three programs in three terminals in
the right order, hope your versions match ours.

With it:

```bash
docker compose up --build
```

One command. Every service gets its exact dependencies in its own sealed box.
It works identically on any machine. The compose file also enforces the
ordering: the gateway and the frontend wait for the AI service to report
healthy before they start, so there's no race on boot.

---

## 7. One bug worth telling you about

Image upload worked perfectly when we ran everything directly on the laptop. The
moment we ran the identical code inside Docker, every upload failed — the AI
service reported *"no file was sent."* Same code, same file, different result.
No error message on either side.

We didn't guess. We captured the raw network traffic and compared it byte for
byte. **The bytes were identical.** So the bug wasn't in the sending — it was in
the reading.

The cause: the web server had two possible components for reading incoming
requests. On the laptop it picked the simpler one. Inside the container a faster
compiled one was available, so it picked that instead — and that faster one
mishandles the specific way Java was chunking up the file. It read the request,
found no file, and reported exactly that. Truthfully.

Fix: one flag telling the server to always use the reliable component.

We kept the test as a permanent check (`scripts/repro_gateway_multipart.py`) so
this can never silently come back.

The reason it's in this document: the difference between "a fix that worked" and
"a fix we understood" is whether you can explain *why* it broke. Guess-and-check
would have taken longer and taught us nothing.

---

## 8. Honest summary

**What's real:**
- The defect classifier — trained on the actual competition images, 99.89%
  accurate on held-out data it never saw during training
- The heatmaps — genuinely computed from the model's internal reasoning
- The trust gate — genuinely rejects out-of-distribution inputs
- The robustness numbers — measured on deliberately degraded images, and they
  include the weak results (89% under blur) alongside the strong ones

**What's generated, and labelled as such everywhere:**
- The eight machine sensor readings
- The production line station data
- The cost and margin figures

**What we chose not to hide:**
- The trust gate is weak on small localized defect types it hasn't seen
- Accuracy drops to 89% on badly out-of-focus images
- The bounding box comes from the heatmap, not from a trained detector, because
  the dataset had no box labels

A system that tells you when to distrust it is worth more than one that's
confident all the time. That's the whole idea, and it applies to the writeup as
much as to the software.
