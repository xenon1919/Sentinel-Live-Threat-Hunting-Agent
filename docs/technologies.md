# Technologies Used

This page explains every library, service, and framework used in SENTINEL — what it is, what problem it solves, and exactly where it's used in the code.

---

## External Services

### Bright Data

**What is it?**
Bright Data is a web data infrastructure company. They operate a massive network of real residential IP addresses around the world. When you route your web requests through Bright Data, websites see a real person visiting from a home internet connection — not a bot.

**Why do we need it?**
When you try to download Google search results with a normal Python script, Google blocks you within seconds. Paste sites, LinkedIn, and many other targets also block automated requests. Bright Data solves this with two specialized "zones":

| Zone | What it does | Used for |
|---|---|---|
| **SERP API** | Fetches search engine results pages from Google/Bing | Running search queries |
| **Web Unlocker** | Fetches any arbitrary URL, bypassing bot detection | Reading flagged pages in full |

**Where in the code:**
- [`bright_data/client.py`](../bright_data/client.py) — `BrightDataClient.search()` and `BrightDataClient.fetch_page()`
- Configuration: `BRIGHTDATA_API_KEY`, `BRIGHTDATA_SERP_ZONE`, `BRIGHTDATA_UNLOCKER_ZONE` in `.env`

**How it works (simplified):**
```python
# We send this to Bright Data's API
{
  "zone": "serp_api1",        # which zone to route through
  "url": "https://google.com/search?q=...",  # what to fetch
  "format": "raw"             # give us the raw HTML back
}

# Bright Data fetches it through a real browser and returns the HTML
```

---

### AI/ML API (or any OpenAI-compatible LLM)

**What is it?**
AI/ML API is a platform that gives you access to hundreds of AI models (GPT-4o, Claude, Gemini, DeepSeek, etc.) through a single API that looks exactly like OpenAI's API.

**Why OpenAI-compatible?**
The "OpenAI API format" has become the industry standard for LLMs. Almost every model provider now supports it. This means we write one piece of code and can swap between models just by changing two lines in `.env` — no code changes needed.

**What the LLM does in SENTINEL:**
1. Plans search queries tailored to the target company
2. Triages search results to pick which pages matter
3. Reads each page and judges whether it contains a real exposure
4. Writes the final risk report

**Where in the code:**
- [`agent/llm.py`](../agent/llm.py) — `build_llm()` creates the LangChain client
- [`agent/prompts.py`](../agent/prompts.py) — all the instructions sent to the LLM
- Configuration: `AIML_API_KEY`, `AIML_BASE_URL`, `AIML_MODEL` in `.env`

**Supported models (just change `AIML_MODEL` in `.env`):**
```
gpt-4o
anthropic/claude-sonnet-4-6
google/gemini-2.5-flash
deepseek/deepseek-chat
```

---

### Cognee

**What is it?**
Cognee is an open-source agent memory library. It stores information as a knowledge graph (a network of connected facts) in a local database. Unlike a simple list, a knowledge graph lets you ask semantic questions like "what credentials were found for Acme Corp?" even without remembering the exact words.

**Why do we need memory?**
Without memory, every scan alerts you on the same old findings. With memory, SENTINEL compares each new scan against previous ones and marks only the **new** findings. In a real security monitoring workflow, this is critical — you only want to be paged on things that are new since the last check.

**Fallback:** If Cognee fails (wrong API key, connection issue), the project automatically uses a simple JSON file (`.memory_store.json`) instead. Both backends behave identically to the rest of the code.

**Where in the code:**
- [`memory/store.py`](../memory/store.py) — `_CogneeMemory` class and `_LocalMemory` fallback
- Configuration: automatically uses `AIML_API_KEY` and `AIML_BASE_URL`

---

## Python Libraries

### Streamlit

**What is it?**
Streamlit is a Python library that lets you build interactive web apps with pure Python — no HTML, CSS, or JavaScript knowledge required.

**Why we use it:**
Streamlit makes it easy to build a live-updating dashboard. As the agent yields events, the UI re-renders the terminal panel with each new line.

**Key Streamlit features used:**
- `st.columns()` — splits the screen into left and right panels
- `st.empty()` — a placeholder that can be updated (used for the live trace)
- `st.text_input()`, `st.button()` — the form controls
- `st.markdown(unsafe_allow_html=True)` — custom HTML/CSS for the dark theme

**Where in the code:** [`ui/app.py`](../ui/app.py)

**How to run:**
```bash
streamlit run ui/app.py
```

---

### LangChain

**What is it?**
LangChain is a framework for building applications powered by language models. It provides:
- Standardized interfaces for calling different LLM providers
- Message types (`SystemMessage`, `HumanMessage`) that map to the LLM's chat format
- Connection pooling, retries, and timeout handling

**Why we use it:**
Using `ChatOpenAI` from LangChain means we can switch LLM providers by changing one line. LangChain also handles retries automatically when the API is slow.

**Where in the code:**
- [`agent/llm.py`](../agent/llm.py) — `build_llm()` returns a `ChatOpenAI` object
- [`agent/orchestrator.py`](../agent/orchestrator.py) — `self.llm.invoke(messages)` calls the LLM

**How a call looks:**
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4o", api_key="...", base_url="...")
response = llm.invoke([
    SystemMessage(content="You are a security analyst."),
    HumanMessage(content="Is this page a threat? <page text here>")
])
print(response.content)  # The LLM's answer as a string
```

---

### BeautifulSoup (bs4)

**What is it?**
BeautifulSoup is a Python library for parsing HTML. It turns the raw HTML text of a webpage into a tree of objects you can navigate and search.

**Why we need it:**
Bright Data returns raw HTML — thousands of lines of tags, scripts, and styles. We need to:
1. Extract just the URLs and text snippets from search results pages
2. Strip all HTML from fetched pages to get clean readable text for the LLM

**Where in the code:** [`bright_data/parsing.py`](../bright_data/parsing.py)

**Example:**
```python
from bs4 import BeautifulSoup

html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
soup = BeautifulSoup(html, "html.parser")
print(soup.get_text())  # → "Hello World"
```

---

### Requests

**What is it?**
Requests is the most popular Python library for making HTTP calls (fetching URLs, calling APIs).

**Why we use it:**
We use it to call Bright Data's REST API. It handles HTTPS connections, headers, JSON encoding, and timeouts.

**Where in the code:** [`bright_data/client.py`](../bright_data/client.py)

---

### python-dotenv

**What is it?**
Reads a `.env` file and makes all the key=value pairs available as environment variables in Python.

**Why we use it:**
API keys should never be hardcoded in source code. By putting them in `.env` and reading them at runtime, you can:
- Keep secrets out of git
- Use different keys in development vs. production without changing code

**Where in the code:** [`agent/config.py`](../agent/config.py) — `load_dotenv()` is called at the top

---

### Pydantic

**What is it?**
Pydantic is a Python library for data validation. You define a class with typed fields and Pydantic ensures the data matches those types.

**Where we use it:**
We use Python's built-in `dataclass` for most of the data structures (Settings, AgentEvent, ScanResult, SearchHit). Pydantic is installed as a dependency of LangChain.

---

## File formats

### `.env` file

A plain text file with one `KEY=VALUE` per line. Used to store secrets (API keys) that should never be committed to version control. The `python-dotenv` library reads this at startup.

```env
# This is a comment
BRIGHTDATA_API_KEY=abc123
AIML_MODEL=gpt-4o
```

### JSON (`.json` files)

The memory fallback (`.memory_store.json`) uses plain JSON — a simple, human-readable format for storing structured data. Example:

```json
{
  "acme corp": [
    "https://pastebin.com/abc123",
    "https://pastebin.com/xyz456"
  ]
}
```

### `pyproject.toml`

The modern Python project configuration file. Lists the project name, version, Python version requirement, and all dependencies.

---

## Why each technology was chosen

| Technology | Alternatives | Why we chose it |
|---|---|---|
| Bright Data | Scrapy, Playwright, SerpApi | Best-in-class for bypassing bot detection; partner for this hackathon |
| AI/ML API | OpenAI directly, Anthropic directly | Single API for any model; hackathon partner credits |
| Cognee | ChromaDB, Pinecone, SQLite | Designed for agent memory; graph-based recall; hackathon partner |
| LangChain | raw `openai` SDK, httpx | Handles retries, model-swapping, standardized messages |
| Streamlit | Flask, FastAPI+React, Gradio | Fastest path to a live-updating Python web UI |
| BeautifulSoup | lxml, Playwright | Simple, tolerant HTML parsing; doesn't need a browser |
