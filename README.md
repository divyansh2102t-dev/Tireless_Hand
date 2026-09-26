# Tireless Hand

Autonomous UI testing agent with self-healing selectors, persistent app memory, bug vs feature differentiation, and automated video evidence capture. Runs entirely on local LLMs via Ollama — zero API keys, zero cloud costs.

## Setup

```bash
pip install -e .
playwright install chromium
cp .env.example .env
```

Pull local models:

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull qwen2.5-coder:7b   # optional for deeper reasoning
ollama pull llava               # optional for vision fallback
```

Or build the specialized local resolver model:
```bash
ollama create tireless-resolver -f training/Modelfile
```

## Quick Start & CLI Usage

### 1. Level-1 Full Quality & Security Audit (with Video Evidence)
Runs multi-vector audits across responsive viewports, state invariants, orphan forms, and unauthenticated route guards. Records full `.webm` video proofs and generates hackathon-ready `SUBMISSION.md`:

```bash
tireless audit http://localhost:4010
```

### 2. Autonomous App Exploration & State Graph Discovery
Crawls an application, maps routes and interactive elements, and saves knowledge to persistent memory (`memory/app_graph.db`):

```bash
tireless explore https://your-app.com --depth 3
```

### 3. Generate YAML Test Specs
Auto-generates declarative test specifications from what was learned during exploration:

```bash
tireless generate https://your-app.com --output-dir test_specs/
```

### 4. Run Test Specs with Self-Healing
Executes test suites and auto-recovers broken selectors using multi-signal fingerprinting and local LLM fallback:

```bash
tireless test https://your-app.com --spec test_specs/login.yaml --heal
```

### 5. Memory & Reporting
```bash
tireless status
tireless report --healing --coverage
```

### 6. Local Demo Testbed
Run the built-in FlytBase drone telemetry simulator to test and practice Level-1 mutation scenarios offline:

```bash
tireless demo --port 8000
```

## How It Works

### Deterministic DOM First (95% of actions, <10ms)
Extracts a compact semantic accessibility tree (`role`, `aria-label`, `text`, `bounding box`) instead of sending raw HTML. 

### Cascading Self-Healing Resolver
When an element's selector or position changes:
1. **Exact Locator**: Try Playwright semantic locator.
2. **Fingerprint Match**: Weighted cosine similarity across text, role, aria-label, and relative layout.
3. **Local LLM Resolver**: Compact DOM passed to `qwen2.5-coder:1.5b` / `tireless-resolver` (~50ms).
4. **Vision Fallback**: Screenshot passed to `llava:latest` if DOM hierarchy is collapsed.

### Specialized Quality Auditors
- **Responsive Auditor**: Checks viewports ($1280\text{px}$ Desktop, $768\text{px}$ Tablet, $375\text{px}$ Mobile) for clipped primary CTAs and horizontal scroll overflows.
- **Invariant Auditor**: Catches orphan forms (inputs without submit buttons) and contradictory telemetry states (e.g. drone marked Offline while actively broadcasting live altitude/stream).
- **Security Auditor**: Dispatches clean unauthenticated browser contexts to verify route guards on private dashboards.
- **Persistence Auditor**: Validates client state survival across page reloads.

## Project Structure

```
src/tireless_hand/
├── agent/         # orchestrator, executor, full audit runner
├── auditors/      # responsive, invariant, security, persistence checkers
├── browser/       # playwright wrapper, compact DOM parser, screenshots, video
├── healing/       # fingerprinting, fuzzy matcher, self-healing resolver
├── memory/        # SQLite store (app_graph.db), baselines, healing logs
├── reasoning/     # ollama client, bug analyzer, prompt templates
├── testing/       # test generator (YAML specs)
└── reporting/     # terminal tables, HTML reports, SUBMISSION.md generator
```

## Custom Model Training (Optional)

Fine-tune `qwen2.5-coder:1.5b` for sub-20ms DOM resolution:

```bash
python training/generate_data.py --url https://your-app.com
ollama create tireless-resolver -f training/Modelfile
```
