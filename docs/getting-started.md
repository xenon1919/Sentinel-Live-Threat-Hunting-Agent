# Getting Started

This guide walks you through setting up SENTINEL from scratch, even if you have never built a Python AI project before.

---

## Prerequisites

You need these installed on your computer:

| Tool | Why | How to check |
|---|---|---|
| Python 3.11+ | The programming language | `python --version` |
| pip | Python package installer | `pip --version` |
| Git | Source control (optional) | `git --version` |

If you don't have Python, download it from [python.org](https://python.org).

---

## Step 1 — Clone or download the project

If you have Git:
```bash
git clone <repo-url>
cd exposure-monitor
```

Or just unzip the downloaded folder and open a terminal inside it.

---

## Step 2 — Create a virtual environment (recommended)

A virtual environment keeps this project's packages separate from everything else on your computer.

```bash
# Create the environment
python -m venv .venv

# Activate it — Windows
.venv\Scripts\activate

# Activate it — Mac/Linux
source .venv/bin/activate
```

You'll see `(.venv)` at the start of your terminal prompt. That means it's active.

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs all the libraries the project needs. It may take a couple of minutes the first time.

---

## Step 4 — Configure your API keys

The project needs three external services. Their keys go in the `.env` file in the project root.

Open `.env` in any text editor. It looks like this:

```env
BRIGHTDATA_API_KEY=your_key_here
BRIGHTDATA_UNLOCKER_ZONE=mcp_unlocker
BRIGHTDATA_SERP_ZONE=serp_api1

AIML_API_KEY=your_key_here
AIML_BASE_URL=https://api.aimlapi.com/v1
AIML_MODEL=gpt-4o

MAX_SEARCH_RESULTS=8
MAX_PAGES_TO_FETCH=5
ENABLE_MEMORY=true
```

### Getting each key

**Bright Data** (web search + page fetching)
1. Sign up at [brightdata.com](https://brightdata.com)
2. Go to **Scraping Automation → SERP API** → create a zone, note its name
3. Go to **Scraping Automation → Web Unlocker** → create a zone, note its name
4. Go to **Settings → Users** → copy your API key
5. Fill in `BRIGHTDATA_API_KEY`, `BRIGHTDATA_SERP_ZONE`, `BRIGHTDATA_UNLOCKER_ZONE`

**AI/ML API** (the LLM that thinks and reasons)
1. Sign up at [aimlapi.com](https://aimlapi.com)
2. Copy your API key from the account page
3. Fill in `AIML_API_KEY`
4. Change `AIML_MODEL` to any supported model (e.g. `gpt-4o`, `claude-sonnet-4-6`)

**Cognee** (agent memory — optional)
- Cognee runs locally using SQLite — no separate account needed
- It automatically uses the same `AIML_API_KEY` you already set
- If Cognee fails, the project automatically falls back to a local JSON file

---

## Step 5 — Run the app

### Option A: Web UI (recommended)

```bash
streamlit run ui/app.py
```

Your browser opens at `http://localhost:8501`.

1. Type a **company name** (e.g. `Acme Corp`)
2. Type the **primary domain** (e.g. `acme.com`)
3. Optionally add context like `fintech, San Francisco`
4. Click **Run Scan**
5. Watch the live trace in the terminal window on the right

### Option B: Terminal / CLI

```bash
python run_cli.py --company "Acme Corp" --domain acme.com
```

With optional context:
```bash
python run_cli.py --company "Acme Corp" --domain acme.com --context "fintech, SF"
```

The agent prints each step as it runs, then outputs the full JSON risk report at the end.

---

## Common problems

| Problem | Cause | Fix |
|---|---|---|
| `Missing required environment variable 'BRIGHTDATA_API_KEY'` | `.env` not filled in | Open `.env` and add your key |
| `Read timed out` | Bright Data took too long | Try again; the query may just be slow |
| `Triage failed` | LLM returned malformed JSON | The agent retries automatically; check the model name in `.env` |
| `Cognee store skipped` | Cognee can't reach its LLM | The agent falls back to local JSON — everything still works |
| `streamlit: command not found` | Streamlit not installed | Run `pip install streamlit` |

---

## Environment variables explained

| Variable | What it controls | Default |
|---|---|---|
| `BRIGHTDATA_API_KEY` | Your Bright Data account key | required |
| `BRIGHTDATA_SERP_ZONE` | Zone name for search queries | `serp_api1` |
| `BRIGHTDATA_UNLOCKER_ZONE` | Zone name for fetching pages | `mcp_unlocker` |
| `AIML_API_KEY` | LLM API key (OpenAI-compatible) | required |
| `AIML_BASE_URL` | Base URL of the LLM API | `https://api.aimlapi.com/v1` |
| `AIML_MODEL` | Which AI model to use | `gpt-4o` |
| `MAX_SEARCH_RESULTS` | Results to fetch per query | `8` |
| `MAX_PAGES_TO_FETCH` | Pages to read per scan | `5` |
| `ENABLE_MEMORY` | Whether to remember past scans | `true` |
