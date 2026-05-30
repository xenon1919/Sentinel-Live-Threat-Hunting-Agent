# Project Architecture

This page explains how the project is structured — which folder does what, and how each piece connects to the others.

---

## Folder structure

```
exposure-monitor/
│
├── agent/                  ← The "brain" — all AI/LLM logic lives here
│   ├── config.py           ← Reads API keys from .env
│   ├── llm.py              ← Builds the LLM client; parses JSON responses
│   ├── orchestrator.py     ← Runs the 7-stage scan pipeline
│   └── prompts.py          ← Every prompt sent to the LLM
│
├── bright_data/            ← The "eyes" — how SENTINEL sees the web
│   ├── client.py           ← Sends requests to Bright Data's API
│   └── parsing.py          ← Turns raw HTML into structured data
│
├── memory/                 ← The "memory" — remembers previous scans
│   └── store.py            ← Cognee backend + local JSON fallback
│
├── ui/                     ← The "face" — the web dashboard
│   └── app.py              ← Streamlit app (left panel + live trace)
│
├── docs/                   ← Documentation (you are here)
│
├── run_cli.py              ← Terminal version of the app (no browser)
├── main.py                 ← Minimal entry point
├── pyproject.toml          ← Project metadata + dependencies
├── requirements.txt        ← pip-installable dependencies
└── .env                    ← API keys (private — never commit)
```

---

## Data flow diagram

Here is how data moves through the system when you click **Run Scan**:

```
User types company + domain
         │
         ▼
  ┌─────────────┐
  │  agent/     │   Step 1: LLM plans 5–7 search queries
  │  orchestrator│
  └──────┬──────┘
         │ search queries
         ▼
  ┌─────────────┐
  │ bright_data/│   Step 2: Bright Data SERP API runs each query
  │ client.py   │   Returns raw HTML of the search results page
  └──────┬──────┘
         │ HTML
         ▼
  ┌─────────────┐
  │ bright_data/│   Step 3: BeautifulSoup extracts URLs + snippets
  │ parsing.py  │   from the HTML → list of SearchHit objects
  └──────┬──────┘
         │ list of URLs
         ▼
  ┌─────────────┐
  │  agent/     │   Step 4: LLM triages the list — picks which
  │  orchestrator│  URLs are worth reading in full
  └──────┬──────┘
         │ selected URLs
         ▼
  ┌─────────────┐
  │ bright_data/│   Step 5: Bright Data Web Unlocker fetches each
  │ client.py   │   page (bypasses bot-blocking)
  └──────┬──────┘
         │ page HTML
         ▼
  ┌─────────────┐
  │ bright_data/│   Step 6: BeautifulSoup strips HTML → plain text
  │ parsing.py  │
  └──────┬──────┘
         │ plain text
         ▼
  ┌─────────────┐
  │  agent/     │   Step 7: LLM reads each page and decides:
  │  orchestrator│  "Is this a real exposure signal? How severe?"
  └──────┬──────┘
         │ findings
         ▼
  ┌─────────────┐
  │  agent/     │   Step 8: LLM synthesizes a final risk report
  │  orchestrator│  (overall risk level + key findings + next steps)
  └──────┬──────┘
         │ report
         ▼
  ┌─────────────┐
  │  memory/    │   Step 9: Findings saved to Cognee/JSON so the
  │  store.py   │   next scan can flag only NEW findings
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │   ui/       │   Displays live trace + final report in browser
  │   app.py    │
  └─────────────┘
```

---

## Module responsibilities

### `agent/config.py`
Reads the `.env` file on startup and exposes every setting as a typed Python dataclass (`Settings`). This means the rest of the code never touches `os.environ` directly — it asks `settings.brightdata_api_key`, `settings.aiml_model`, etc.

### `agent/llm.py`
Two jobs:
1. **`build_llm()`** — creates a `ChatOpenAI` client pointed at whatever URL is in `AIML_BASE_URL`. This works with any OpenAI-compatible API (AI/ML API, Google Gemini, OpenRouter, etc.)
2. **`parse_json_response()`** — LLMs sometimes add markdown fences, extra text, or truncate their output. This function tries 7 different strategies to extract a valid JSON object before giving up.

### `agent/prompts.py`
Plain-text strings — one for each LLM role:
- **PLANNER** — "Given this company, write 5–7 search queries"
- **TRIAGE** — "Given these search results, pick the ones worth reading"
- **ANALYST** — "Given this page text, is there a real exposure signal?"
- **REPORT** — "Given these findings, write an executive risk report"

### `agent/orchestrator.py`
The main loop. It calls all the other modules in the right order and `yield`s `AgentEvent` objects as it works — one event per step — so the UI can stream them to the browser in real time.

### `bright_data/client.py`
A thin HTTP wrapper around Bright Data's `/request` endpoint. One method (`search()`) for SERP queries, one method (`fetch_page()`) for full-page fetches.

### `bright_data/parsing.py`
Two functions:
- `parse_serp_html()` — scrapes a Google/Bing results page, returns a list of `SearchHit(title, url, snippet)`
- `extract_text()` — strips all HTML tags from a fetched page, returns clean text (max 6000 characters)

### `memory/store.py`
Two backends that share the same interface (`recall_known_urls()` + `remember_findings()`):
- **`_CogneeMemory`** — uses Cognee's graph-based semantic memory; tries first
- **`_LocalMemory`** — stores a simple JSON file (`.memory_store.json`); used if Cognee fails

### `ui/app.py`
The Streamlit web app. Splits the screen into two columns:
- **Left** — branding, scan form, "Powered by" badges
- **Right** — live agent trace terminal + final risk report

### `run_cli.py`
Same scan flow but printed to the terminal instead of a browser. Useful for scripting or servers without a display.

---

## How the live trace works

The agent is a Python **generator function** — it uses `yield` instead of `return`.

```python
# Simplified version of what the orchestrator does
def scan(company, domain):
    yield AgentEvent("plan", "Planning search queries...")
    # ... does work ...
    yield AgentEvent("search", "Searching Google...")
    # ... does work ...
    yield AgentEvent("done", "Scan complete.")
    return ScanResult(...)
```

The UI calls `next(generator)` in a loop. Each time it gets an event, it appends a line to the terminal and re-renders the HTML — that's how you see each step appear as it happens.
