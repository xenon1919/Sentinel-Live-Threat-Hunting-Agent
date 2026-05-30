# Code Reference

Quick reference for the key classes and functions in the codebase. Useful if you want to extend or modify the project.

---

## `agent/config.py`

### `Settings` (dataclass)

Holds all configuration loaded from `.env`.

```python
settings = Settings.load()

settings.brightdata_api_key       # str
settings.brightdata_unlocker_zone # str
settings.brightdata_serp_zone     # str
settings.aiml_api_key             # str
settings.aiml_base_url            # str  e.g. "https://api.aimlapi.com/v1"
settings.aiml_model               # str  e.g. "gpt-4o"
settings.max_search_results       # int  default 8
settings.max_pages_to_fetch       # int  default 5
settings.enable_memory            # bool default True
```

**Usage:**
```python
from agent.config import Settings
settings = Settings.load()  # reads .env automatically
```

---

## `agent/llm.py`

### `build_llm(settings, temperature=0.2)`

Returns a LangChain `ChatOpenAI` client configured for the AI/ML API endpoint.

```python
from agent.llm import build_llm
llm = build_llm(settings)
response = llm.invoke([...messages...])
print(response.content)  # the LLM's reply as a string
```

**Parameters:**
- `settings` — a `Settings` instance
- `temperature` — how creative the LLM should be (0.0 = deterministic, 1.0 = creative). Default `0.2` keeps answers factual and consistent.

### `parse_json_response(content)`

Extracts and parses a JSON object from LLM output. Handles markdown fences, leading prose, missing braces, list-at-root, and truncated responses.

```python
from agent.llm import parse_json_response

raw = '```json\n{"key": "value"}\n```'
result = parse_json_response(raw)
# → {"key": "value"}
```

**Returns:** `dict` — always a dictionary. If the LLM returns a JSON array, it's wrapped as `{"items": [...]}`.

**Raises:** `ValueError` with a helpful message including the raw response snippet if all 7 strategies fail.

---

## `agent/orchestrator.py`

### `AgentEvent` (dataclass)

A single event yielded by the scan generator.

```python
@dataclass
class AgentEvent:
    stage: str    # "plan"|"search"|"triage"|"fetch"|"analyze"|"report"|"memory"|"error"|"done"
    message: str  # human-readable description
    data: Any     # optional structured payload (e.g. the report dict for "done")
```

### `ScanResult` (dataclass)

The final return value of the scan generator.

```python
@dataclass
class ScanResult:
    company: str
    domain: str
    report: dict          # the full risk report
    findings: list        # all confirmed exposure findings
    memory_backend: str   # "cognee" or "local-json"
```

### `ExposureMonitorAgent`

The main agent class.

```python
from agent.config import Settings
from agent.orchestrator import ExposureMonitorAgent

settings = Settings.load()
agent = ExposureMonitorAgent(settings)
```

### `agent.scan(company, domain, context="")`

A generator that yields `AgentEvent` objects and returns a `ScanResult`.

```python
gen = agent.scan("Acme Corp", "acme.com", "fintech, SF")

try:
    while True:
        event = next(gen)
        print(f"[{event.stage}] {event.message}")
except StopIteration as stop:
    result = stop.value   # ScanResult
    print(result.report)
```

**Important:** Use `stop.value` (not `gen.send(None)`) to get the final `ScanResult`.

---

## `bright_data/client.py`

### `BrightDataClient`

Thin wrapper around Bright Data's REST API.

```python
from bright_data.client import BrightDataClient, BrightDataConfig

client = BrightDataClient(BrightDataConfig(
    api_key="...",
    unlocker_zone="mcp_unlocker",
    serp_zone="serp_api1",
    timeout=90,  # seconds
))
```

### `client.search(query, engine="google", num=10)`

Runs a search query and returns the raw HTML of the results page.

```python
html = client.search(
    'site:pastebin.com "acme.com"',
    engine="google",  # or "bing"
    num=8
)
```

**Returns:** `str` — raw HTML of the search results page.  
**Raises:** `BrightDataError` on network failure or non-200 response.

### `client.fetch_page(url)`

Fetches a full page through the Web Unlocker zone.

```python
html = client.fetch_page("https://pastebin.com/abc123")
```

**Returns:** `str` — raw HTML of the page.  
**Raises:** `BrightDataError` on failure.

---

## `bright_data/parsing.py`

### `parse_serp_html(html, max_hits=10)`

Extracts search results from a raw Google/Bing HTML page.

```python
from bright_data.parsing import parse_serp_html

hits = parse_serp_html(html, max_hits=8)
for hit in hits:
    print(hit.url)      # "https://pastebin.com/abc123"
    print(hit.title)    # "Leaked credentials - Pastebin"
    print(hit.snippet)  # "acme.com admin:password123..."
    print(hit.to_dict()) # {"title": "...", "url": "...", "snippet": "..."}
```

**Returns:** `List[SearchHit]`

### `extract_text(html, max_chars=6000)`

Strips HTML tags and returns plain text suitable for LLM consumption.

```python
from bright_data.parsing import extract_text

text = extract_text(page_html)
# → "Welcome to Pastebin. acme.com credentials admin:password123 ..."
```

**Returns:** `str` — clean text, truncated to `max_chars`.

---

## `memory/store.py`

### `build_memory(enable_memory)`

Factory function — returns the best available memory backend.

```python
from memory.store import build_memory

memory = build_memory(enable_memory=True)
# Returns _CogneeMemory if Cognee works, else _LocalMemory
# Returns None if enable_memory=False
```

### Memory interface

Both `_CogneeMemory` and `_LocalMemory` implement the same two methods:

```python
# Get URLs seen in previous scans for this company
known_urls = memory.recall_known_urls("Acme Corp")
# → {"https://pastebin.com/abc123", "https://pastebin.com/xyz456"}

# Save findings from this scan
memory.remember_findings("Acme Corp", [
    {"url": "https://pastebin.com/new123", "severity": "critical", ...}
])

# Which backend is active
print(memory.backend)  # "cognee" or "local-json"
```

---

## Adding a new search engine

1. Open [`bright_data/client.py`](../bright_data/client.py)
2. Add a new entry to `_SEARCH_TEMPLATES`:
   ```python
   _SEARCH_TEMPLATES = {
       "google":  "https://www.google.com/search?q={q}&num={n}",
       "bing":    "https://www.bing.com/search?q={q}&count={n}",
       "yandex":  "https://yandex.com/search/?text={q}",
       "duckduckgo": "https://duckduckgo.com/?q={q}",  # ← add this
   }
   ```
3. The LLM planner can now suggest `"engine": "duckduckgo"` in its queries.

---

## Adding a new LLM prompt

1. Open [`agent/prompts.py`](../agent/prompts.py)
2. Add your prompt as a constant (no `.format()` calls in the system prompt if it contains `{...}` JSON examples):
   ```python
   MY_SYSTEM = """You are a specialist in X. Return JSON: {"result": "..."}"""
   MY_USER = """Input: {input_data}"""
   ```
3. Call it in the orchestrator:
   ```python
   result = self._ask_json(
       prompts.MY_SYSTEM,
       prompts.MY_USER.format(input_data=my_data),
   )
   ```

---

## Environment variables quick reference

```bash
# Required
BRIGHTDATA_API_KEY=       # Bright Data account key
AIML_API_KEY=             # LLM provider API key

# Bright Data zone names (must match names in your Bright Data control panel)
BRIGHTDATA_UNLOCKER_ZONE=mcp_unlocker
BRIGHTDATA_SERP_ZONE=serp_api1

# LLM settings
AIML_BASE_URL=https://api.aimlapi.com/v1
AIML_MODEL=gpt-4o

# Agent tunables
MAX_SEARCH_RESULTS=8      # How many results to collect per query
MAX_PAGES_TO_FETCH=5      # How many pages to fetch and read per scan
ENABLE_MEMORY=true        # Set false to disable Cognee/JSON memory
```
