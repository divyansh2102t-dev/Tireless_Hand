# Tireless Hand

Autonomous UI testing agent with self-healing selectors, persistent app memory, bug vs feature differentiation, and automated video evidence capture. Runs entirely on local LLMs via Ollama — zero API keys, zero cloud costs.

---

## ⚡ 3-Minute Quickstart (For Any Web Page)

### 1. Installation & Prerequisites
Make sure [Ollama](https://ollama.ai) is running locally, then:

```bash
# Clone the repository
git clone https://github.com/divyansh2102t-dev/Tireless_Hand.git
cd Tireless_Hand

# Install dependencies and browser engine
pip install -e .
playwright install chromium

# Pull the lightweight local AI model (fast & 100% free)
ollama pull qwen2.5-coder:1.5b
```

### 2. Test Any Web Page

#### Option A: Full Quality & Security Audit (with Video Proofs)
Run a complete audit for responsive UI breaks, orphan forms, contradictory telemetry, and security bypasses:

```bash
# Headless background mode (Fast)
tireless audit https://example.com

# Headed mode (Opens a visible browser so you can watch it live!)
tireless audit http://localhost:8000/login --no-headless
```

#### Option B: Autonomous AI Exploration & Page Mapping
Have the AI explore any website, discover interactive buttons/forms, and map them to memory:

```bash
tireless explore https://example.com --depth 2
```

#### Option C: Step-by-Step Test with Self-Healing Selectors
Run a test flow that automatically heals broken selectors if the website's HTML/CSS changes:

```bash
tireless test http://localhost:8000/login --report
```

---

## 📊 Evaluation Matrix & Benchmark Results

We benchmarked Tireless Hand across a diverse matrix of **12 distinct clean and mutated test vectors** spanning login portals, cockpit telemetry, mission planners, responsive fleet tables, hardware diagnostics, and protected security routes:

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
| **Benchmark Runtime** | Total Execution Time (12 vectors) | **29.33s** |

---

## 📁 Where to View Results & Videos

After running an audit or test, check the generated artifacts in `reports/`:
- **Interactive HTML Report**: Open `reports/submission.html` in your browser.
- **Summary Document**: Check `reports/SUBMISSION.md`.
- **Screen Recordings**: High-definition `.webm` video proofs are automatically saved in `reports/videos/`.

---

## 🧪 Built-in Local Benchmark / Demo Server

To practice and verify Level-1 mutation scenarios offline without any external setup:

1. **Start the local drone mission control server**:
   ```bash
   tireless demo --port 8000
   ```
2. **In another terminal, run the full mutation audit suite**:
   ```bash
   tireless audit --suite
   ```

---

## 🛠️ CLI Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `tireless audit <URL>` | Full multi-viewport audit with video recording | `tireless audit http://localhost:4010` |
| `tireless audit --suite` | Runs full Level-1 mutation testbed suite | `tireless audit --suite` |
| `tireless explore <URL>` | Autonomous web crawler & knowledge mapper | `tireless explore https://example.com --depth 3` |
| `tireless test <URL>` | Runs test flows with AI self-healing | `tireless test https://example.com --report` |
| `tireless generate <URL>` | Auto-generates declarative YAML test specs | `tireless generate https://example.com --output-dir test_specs/` |
| `tireless status` | Shows discovered pages and graph knowledge | `tireless status` |
| `tireless report` | Displays healing, coverage, and cost stats | `tireless report --healing --coverage --cost` |
| `tireless demo` | Starts the built-in drone testbed on port 8000 | `tireless demo --port 8000` |

---

## 🧠 Architecture & How It Works

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
   │ • Video Capture (.webm)       │                  └───────────────────────────────┘
   └───────────────────────────────┘                               │
                     │                                             │
                     └──────────────────────┬──────────────────────┘
                                            ▼
                           Reports & Evidence (HTML / Markdown)
```

### Key Technical Pillars
1. **Deterministic DOM First (<10ms)**: Uses a custom JavaScript TreeWalker to extract clean, accessible roles, labels, text, and bounding boxes instead of dumping bloated raw HTML.
2. **Cascading 6-Signal Self-Healing**: Recovers altered UI selectors via weighted multi-signal matching (ID, tag, ARIA, text, hierarchy, layout) with zero-shot local LLM fallback.
3. **Multi-Viewport Layout Auditing**: Calculates exact pixel boundary violations across Desktop (1280px), Tablet (768px), and Mobile (375px) to catch clipped CTAs and overflow bugs.
4. **100% Local & Free**: Uses local models (`qwen2.5-coder:1.5b`, `tireless-resolver`) via Ollama. No third-party API keys required, zero cloud costs.
