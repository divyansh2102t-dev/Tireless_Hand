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

# Pull the lightweight local AI model (fast & free)
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

## 📊 Where to View Results & Videos

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
4. **100% Local & Free**: Uses local models (`qwen2.5-coder:1.5b`, `tireless-resolver`) via Ollama. No third-party API keys, zero cloud costs.
