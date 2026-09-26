# ⚡ Tireless Hand

> **Autonomous Agentic UI & Reliability Auditor for FlytBase Cockpits & Web Applications.**  
> Features self-healing selectors, multi-viewport layout verification, invariant telemetry checking, floating interactive HUD, and automated dual visual evidence (HD PNG snapshots + WebM video recordings). Runs 100% locally on free Ollama models with seamless Cloud API fallback.

---

## 🚀 One-Command Instant Launch (Zero Setup)

Launch the entire platform (Mock server, Agent Backend, Defect Mutation Lab, and Floating Interactive HUD) with a **single command**:

```bash
# 1. Install dependencies & browser engine
pip install -e .
playwright install chromium

# 2. Start all components & open UI in one command
python run.py
```
*(Or use the CLI command: `tireless start`)*

This instantly opens the **Interactive Agent HUD** in your default browser at **`http://localhost:8000/ui`**.

---

## 🎛️ Interactive Floating Agent HUD (No Terminal Needed)

Tireless Hand includes a built-in floating glassmorphic HUD that lets you test any website or drone cockpit directly from your browser:

* **Target URL Input**: Enter any target URL (e.g. `http://localhost:4010` for FlytBase Cockpit, `http://localhost:8000/broken`, or your own web app).
* **`[x] Watch Live` Toggle**: Toggles live headed Chromium browser observation so you can watch the agent click, inspect, and audit in real-time.
* **⚡ Audit**: Triggers complete Level-1 defect analysis across viewports (1280px / 768px / 375px), auth guards, and forms.
* **🔍 Explore**: Crawls and builds persistent memory graphs of pages and interactive buttons.
* **📊 Benchmark**: Runs the full 12-scenario evaluation matrix and live updates metrics.
* **📄 Reports**: Opens the latest interactive HTML report with video recordings and snapshot proofs.
* **Live Log Drawer**: Real-time streaming console showing defect detection and agent actions.

---

## 🧠 Multi-Tier Model Cascading (Local + Cloud Fallback)

Tireless Hand is engineered to work reliably on any machine without blocking:

1. **Tier 1 (Primary - 100% Free & Local)**: Local **Ollama** (`qwen2.5-coder:1.5b` or custom `tireless-resolver`). Zero API keys, zero cloud costs, 100% private.
2. **Tier 2 (Secondary - Cloud API Fallback)**: If Ollama is not installed or running, automatically uses **OpenAI API** (`gpt-5-nano`, `gpt-4o-mini`, etc.) configured in `.env`.
3. **Tier 3 (Tertiary - Deterministic Heuristics)**: Built-in deterministic DOM TreeWalker and geometric layout analyzers guarantee 0% crash rate even if no LLMs are reachable.

### Optional Cloud Setup
Copy the template and add your API key if you want cloud inference:
```bash
cp .env.example .env
```
*(Edit `.env` and insert your `OPENAI_API_KEY` or `SMALLEST_API_KEY`)*

---

## 📊 Evaluation Matrix & Benchmark Results

We benchmarked Tireless Hand against **12 distinct clean and mutated test vectors** spanning login forms, telemetry streams, mission planners, responsive fleet tables, hardware sensors, and protected security routes:

```bash
python benchmarks/run_benchmark.py
```

### Benchmark Results Table

| Test ID | Scenario Name | Category | Expected | Detected | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Clean Login Form | Form Invariant | Clean | Clean | **TN (True Negative)** |
| **TC-02** | Clean Cockpit Telemetry | Telemetry Invariant | Clean | Clean | **TN (True Negative)** |
| **TC-03** | Clean Mission Planner | Form Invariant | Clean | Clean | **TN (True Negative)** |
| **TC-04** | Clean Fleet Responsive Layout | Responsive Layout | Clean | Clean | **TN (True Negative)** |
| **TC-05** | Clean Sensor Diagnostics | Telemetry Invariant | Clean | Clean | **TN (True Negative)** |
| **TC-06** | Enforced Route Guard on Settings | Auth Guard | Clean | Clean | **TN (True Negative)** |
| **TC-07** | Login Orphan Form (Stripped Submit) | Form Invariant | Bug | Bug | **TP (True Positive)** |
| **TC-08** | Mission Planner Orphan Form | Form Invariant | Bug | Bug | **TP (True Positive)** |
| **TC-09** | Drone Offline with Live Telemetry Conflict | Telemetry Invariant | Bug | Bug | **TP (True Positive)** |
| **TC-10** | Sensor Disconnected with Active Sampling | Telemetry Invariant | Bug | Bug | **TP (True Positive)** |
| **TC-11** | Mobile Viewport Clipped RTH Button | Responsive Layout | Bug | Bug | **TP (True Positive)** |
| **TC-12** | Unauthenticated Access to Fleet Registry | Auth Guard | Bug | Bug | **TP (True Positive)** |

### Performance Metrics Summary

| Metric | Formula | Value |
| :--- | :--- | :--- |
| **True Positives (TP)** | Caught actual injected mutations | **6 / 6 (100%)** |
| **True Negatives (TN)** | Passed clean pages with zero false alarms | **6 / 6 (100%)** |
| **False Positives (FP)** | Clean pages flagged falsely | **0 (0%)** |
| **False Negatives (FN)** | Mutations missed | **0 (0%)** |
| **Precision** | $\frac{\text{TP}}{\text{TP} + \text{FP}}$ | **100.0% (1.0000)** |
| **Recall** | $\frac{\text{TP}}{\text{TP} + \text{FN}}$ | **100.0% (1.0000)** |
| **Accuracy** | $\frac{\text{TP} + \text{TN}}{\text{Total}}$ | **100.0% (1.0000)** |
| **F1-Score** | $2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$ | **100.0% (1.0000)** |
| **Benchmark Runtime** | Total Execution Time (12 vectors) | **28.62s** |

---

## 📁 Dual Evidence Pipeline (Screenshots + Videos)

Every audit automatically generates dual visual evidence for complete transparency:
- **📸 High-Resolution Visual Snapshots**: Captured at the exact moment a defect is identified (`reports/screenshots/`).
- **📹 Full-Length WebM Video Recordings**: Recorded across multi-viewport interactions with stream buffer flushes (`reports/videos/`).
- **🌐 Interactive Submission Report**: View rich cards with side-by-side video players and screenshot proof in `reports/submission.html`.
- **📝 Markdown Submission Summary**: Generated at `reports/SUBMISSION.md`.

---

## 🧪 Testing with FlytBase Starter Kit & Custom Sites

### Testing the Official FlytBase Drone Starter Kit
If you have the FlytBase Hackathon Docker container running:
```bash
# 1. Start the FlytBase Docker container (if applicable)
docker compose up --build

# 2. Audit the FlytBase Cockpit at port 4010
tireless audit http://localhost:4010 --no-headless
```

### Testing the Built-in Mutation Testbed
```bash
# Run complete Level-1 mutation suite
tireless audit --suite
```

---

## 🛠️ Complete CLI Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `python run.py` | **One-command launch** for server, backend & browser HUD | `python run.py` |
| `tireless start` | Starts all components and opens the HUD in browser | `tireless start` |
| `tireless ui` | Opens the floating interactive HUD at `http://localhost:8000/ui` | `tireless ui` |
| `tireless audit <URL>` | Full multi-viewport audit with video and screenshot proof | `tireless audit http://localhost:4010` |
| `tireless audit <URL> --no-headless` | Runs audit with a visible browser window | `tireless audit http://localhost:8000/broken --no-headless` |
| `tireless audit --suite` | Runs full Level-1 mutation testbed suite | `tireless audit --suite` |
| `tireless explore <URL>` | Autonomous web crawler & graph knowledge mapper | `tireless explore http://localhost:8000 --depth 3` |
| `tireless test <URL>` | Runs test flows with AI self-healing selectors | `tireless test http://localhost:8000/login --report` |
| `tireless status` | Shows discovered pages and graph knowledge | `tireless status` |
| `tireless report` | Displays healing, coverage, and cost statistics | `tireless report --healing --coverage --cost` |
| `python benchmarks/run_benchmark.py` | Runs and evaluates the 12-scenario benchmark matrix | `python benchmarks/run_benchmark.py` |

---

## 🧠 Architecture & Technical Highlights

```
Target URL ──► Playwright Browser ──► JS TreeWalker (Compact A11y DOM)
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
          Autonomous Auditors                            Local AI Reasoner (Ollama)
   ┌───────────────────────────────┐                  ┌───────────────────────────────┐
   │ • Responsive (1280/768/375px) │                  │ • Goal Planning & Crawling    │
   │ • Orphan Forms & Invariants   │                  │ • 6-Signal Self-Healing Engine│
   │ • Auth & Security Bypasses    │                  │ • Bug vs Feature Classifier   │
   │ • Screenshots & Video Proofs  │                  └───────────────────────────────┘
   └───────────────────────────────┘                               │
                     │                                             │
                     └──────────────────────┬──────────────────────┘
                                            ▼
                           Reports & Evidence (HTML / Markdown)
```

1. **Deterministic Fast DOM (<10ms)**: Compact accessibility tree extraction avoids massive token overhead and token window overflow.
2. **6-Signal Weighted Self-Healing**: Recovers altered UI selectors via weighted signal matching (ID, Tag, ARIA, Text, Tree Hierarchy, Bounding Box).
3. **Multi-Viewport Layout Auditing**: Calculates exact pixel boundary violations across Desktop (1280px), Tablet (768px), and Mobile (375px) to catch clipped CTAs and overflow bugs.
4. **Buffer-Safe Video & Screenshot Recording**: Enforces video encoder stream flushing before context destruction to guarantee playable videos and captures instant high-res PNGs.
