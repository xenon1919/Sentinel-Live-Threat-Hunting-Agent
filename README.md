# 🛡️ Open-Web Exposure Monitor

**An autonomous defensive-security agent that hunts the open web for your organization's exposure — leaked credentials, impersonation domains, and brand abuse — then returns a prioritized risk report.**

Built for the **Web Data UNLOCKED Hackathon** · Track 3: Security & Compliance.

> Give it a company you're authorized to monitor. The agent autonomously plans search queries, scours the open web through Bright Data, reasons over what it finds, and tells your security team what to act on first — no human in the loop.

---

## Why this exists

Threats, leaked credentials, and brand impersonation don't show up in your internal systems — they surface across the open web, on sources no SIEM was built to monitor. This agent gives a security team live, autonomous coverage of that surface and returns **structured, actionable** findings instead of raw noise.

It is a **defensive** tool: it only surfaces information that is *already public*, so defenders can respond (force resets, file takedowns, alert users). It does not access private systems, exploit anything, or collect credentials.

---

## What it does (the agent loop)

A hand-legible, LangChain-powered loop with explicit stages. It runs as a streaming generator, so you can **watch the agent think** live:

```
plan ──▶ search ──▶ triage ──▶ fetch ──▶ analyze ──▶ report ──▶ remember
 │         │          │          │          │           │           │
 LLM    SERP API   LLM picks  Web Unlocker LLM judges  LLM ranks   memory
proposes  (Bright   URLs worth  (Bright    each page   findings    diffs NEW
 queries   Data)    reading      Data)     for signal  by severity  vs seen
```

1. **Plan** — the LLM proposes targeted, defensive search queries (credential leaks, lookalike domains, phishing, breach mentions).
2. **Search** — each query runs through **Bright Data SERP API**.
3. **Triage** — the LLM picks which result URLs are actually worth reading.
4. **Fetch** — each selected page is retrieved through **Bright Data Web Unlocker** (past bot detection / CAPTCHA / geo-blocks).
5. **Analyze** — the LLM assesses each page for a *real* exposure signal and assigns a severity (skeptical of false positives; never echoes sensitive values).
6. **Report** — the LLM synthesizes a prioritized risk report with recommended actions.
7. **Remember** — **Cognee** memory persists findings so future scans flag only **NEW** exposures.

---

## Tech stack

| Layer | Tool |
|---|---|
| Web data | **Bright Data** — SERP API + Web Unlocker (single `/request` endpoint) |
| LLM reasoning | **AI/ML API** (OpenAI-compatible) via `langchain-openai` |
| Agent framework | **LangChain** |
| Memory | **Cognee** (with automatic local-JSON fallback) |
| UI | **Streamlit** (live trace + report) |

---

## Setup

### 1. Install
```bash
git clone <your-repo-url>
cd exposure-monitor
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
```
Fill in `.env`:

- **Bright Data**: get your API key, redeem the `unlocked` promo for $250 credit, and create two zones (a Web Unlocker zone and a SERP zone). Put the key and the two **zone names** in `.env`.
- **AI/ML API**: get your key (and $200 partner credit), keep the base URL as-is, pick any chat model.

### 3. Verify without spending a cent
The offline self-test mocks both APIs and checks the full loop, parsing, and memory logic:
```bash
python selftest.py
# -> ALL SELFTESTS PASSED ✅
```

---

## Usage

### Streamlit UI (recommended for the demo)
```bash
streamlit run ui/app.py
```
Enter a company + domain, hit **Run scan**, and watch the live trace populate stage by stage before the risk report renders.

### CLI
```bash
python run_cli.py --company "Acme Corp" --domain acme.com --context "fintech, SF"
```

---

## Project layout

```
exposure-monitor/
├── agent/
│   ├── config.py         # env-driven settings
│   ├── llm.py            # AI/ML API client (LangChain) + robust JSON parsing
│   ├── prompts.py        # per-stage prompts (defensive framing baked in)
│   └── orchestrator.py   # the streaming agent loop
├── bright_data/
│   ├── client.py         # Web Unlocker + SERP over the /request endpoint
│   └── parsing.py        # SERP HTML -> hits; page -> clean text
├── memory/
│   └── store.py          # Cognee memory + local fallback (NEW-vs-seen diff)
├── ui/app.py             # Streamlit live-trace UI
├── run_cli.py            # terminal runner
├── selftest.py           # offline end-to-end verification
├── requirements.txt
└── .env.example
```

---

## How it maps to the judging criteria

- **Application of Technology** — a genuine multi-stage autonomous agent that uses Bright Data the way it's meant to be used (SERP API for discovery, Web Unlocker for blocked pages), with AI/ML API reasoning at every stage and Cognee for memory.
- **Business Value** — "detect leaked credentials and impersonation before they're exploited" is an immediate, legible enterprise need that internal tools can't cover.
- **Originality** — most builders reach for sales/competitor tools; an autonomous open-web threat-hunting agent stands apart.
- **Presentation** — the live trace makes the agent's reasoning visible in real time, and it demos in under two minutes.

---

## Responsible use

This is a defensive tool. Use it only for organizations you own or are authorized to protect. It surfaces **already-public** exposure so a security team can respond; it does not access private systems, exploit vulnerabilities, or collect credentials, and it never reproduces sensitive values it encounters.
