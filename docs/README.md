# SENTINEL — Documentation Index

**SENTINEL** is an autonomous security agent that scans the open web for publicly-exposed credentials, impersonation domains, and brand abuse for a company you own or are authorized to protect.

---

## What does it do in plain English?

Imagine you run a company called **Acme Corp**. You want to know:

- Has anyone leaked your employees' passwords on a paste site like Pastebin?
- Is someone running a fake `acme-login.com` site to phish your users?
- Is your company mentioned in a data-breach database?

SENTINEL answers these questions **automatically** — it searches the web, reads the suspicious pages, and hands you a color-coded risk report in real time.

---

## Documentation Files

| File | What it covers |
|---|---|
| [getting-started.md](getting-started.md) | Install, configure, and run the app — step by step |
| [architecture.md](architecture.md) | Folder structure and how the pieces fit together |
| [how-it-works.md](how-it-works.md) | The 7-stage agent pipeline explained with examples |
| [technologies.md](technologies.md) | Every library/service used — what it is and why |
| [ui-guide.md](ui-guide.md) | The Streamlit UI explained panel by panel |

---

## Quick-start (30 seconds)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Fill in your API keys in .env (already partially filled)

# 3. Run the web UI
streamlit run ui/app.py
```

Open `http://localhost:8501`, type a company name and domain, click **Run Scan**.

---

## Project at a glance

```
SENTINEL
├── agent/          ← Brain: LLM calls, planning, orchestration
├── bright_data/    ← Eyes: web search + page fetching
├── memory/         ← Memory: Cognee + local JSON fallback
├── ui/             ← Face: Streamlit dark-theme dashboard
├── docs/           ← You are here
├── .env            ← API keys (never commit this)
└── run_cli.py      ← Terminal mode (no browser needed)
```
