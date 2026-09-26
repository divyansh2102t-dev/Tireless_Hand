# Tireless Hand

Autonomous UI testing agent. Self-healing selectors, persistent app memory, bug vs feature detection. Runs entirely on local LLMs via Ollama — no API keys, no cloud costs.

## Setup

```bash
pip install -e .
playwright install chromium
cp .env.example .env
```

Pull local models (you need at least the 1.5b one):

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull qwen2.5-coder:7b   # for smarter analysis
ollama pull llava               # for visual fallback
```

## Usage

```bash
# explore an app, build the memory graph
tireless explore https://your-app.com --depth 3

# generate YAML test specs from what was discovered
tireless generate https://your-app.com

# run tests with self-healing
tireless test https://your-app.com --heal

# run a specific test spec
tireless test https://your-app.com --spec test_specs/login.yaml

# check what the agent knows
tireless status

# reports
tireless report --healing --coverage
```

## How it works

Most actions use deterministic DOM fingerprinting (text, role, aria-label, position). When a selector breaks:

1. Fuzzy attribute matching against stored fingerprints
2. Local LLM resolves the element from compact DOM (qwen2.5-coder 1.5b, ~50ms)
3. Smarter model for ambiguous cases (qwen2.5-coder 7b)
4. Vision fallback via llava if DOM matching fails entirely

Everything persists to SQLite (`memory/app_graph.db`). Second run onwards, the agent already knows the app.

Bug vs feature changes are classified by heuristics first (error keywords, HTTP codes, coordinated element changes), LLM only for edge cases.

## Project structure

```
src/tireless_hand/
├── agent/         # orchestrator, executor
├── browser/       # playwright wrapper, DOM parser, screenshots
├── healing/       # fingerprinting, fuzzy matching, self-healing resolver
├── memory/        # SQLite store, app graph, baselines
├── reasoning/     # ollama client, bug analyzer, prompts
├── testing/       # test generator
└── reporting/     # rich terminal + HTML reports
```

## Custom model (optional)

Fine-tune qwen2.5-coder:1.5b on DOM resolution tasks:

```bash
python training/generate_data.py --url https://your-app.com
ollama create tireless-resolver -f training/Modelfile
```

Then set `fast_model: tireless-resolver` in config.
