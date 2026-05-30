# How It Works — The 7-Stage Pipeline

When you click **Run Scan**, SENTINEL runs through seven stages automatically. This page explains each stage in plain English, what happens technically, and what you see in the live trace.

---

## Overview

```
Stage 1 → PLAN      "What should I search for?"
Stage 2 → SEARCH    "Run the queries on Google/Bing"
Stage 3 → TRIAGE    "Which results are worth reading?"
Stage 4 → FETCH     "Download those pages"
Stage 5 → ANALYZE   "Is there a real threat on this page?"
Stage 6 → REPORT    "Write the risk report"
Stage 7 → MEMORY    "Remember what I found"
```

---

## Stage 1 — PLAN

**What happens:** The LLM reads the company name and domain, then generates 5–7 targeted search queries.

**Example input to LLM:**
```
Target company: Acme Corp
Primary domain: acme.com
```

**Example output from LLM:**
```json
{
  "queries": [
    {"query": "site:pastebin.com \"acme.com\" password", "engine": "google"},
    {"query": "intitle:\"Acme Corp\" inurl:login -site:acme.com", "engine": "google"},
    {"query": "\"acme.com\" data breach OR leak", "engine": "bing"}
  ]
}
```

**What you see in the trace:**
```
◈  plan    Planning search strategy for Acme Corp (acme.com)...
◈  plan    Planned 5 queries.
```

**Why:** Instead of hardcoding the same queries for every company, the LLM tailors them to the specific company name and domain. This finds more relevant results.

---

## Stage 2 — SEARCH

**What happens:** Each query runs through Bright Data's SERP API, which acts like a real browser visiting Google or Bing. The raw HTML of the results page comes back and is parsed into a list of URLs + snippets.

**Bright Data's role:** Google blocks automated requests. Bright Data's SERP zone routes your request through a real residential IP, gets the real results page, and sends back the HTML.

**What you see in the trace:**
```
◎  search   Searching (google): site:pastebin.com "acme.com" password
◎  search   → 5 results
◎  search   Searching (bing): "acme.com" data breach
◎  search   → 8 results
```

After all queries run, duplicate URLs are removed. You might start with 30 results and end up with 15 unique ones.

---

## Stage 3 — TRIAGE

**What happens:** The LLM looks at the full list of search results (title, URL, and snippet for each) and picks which pages are actually worth fetching and reading in full.

**Why triage?** You can have 15 results but most are LinkedIn profiles, news articles, or the company's own website — none of those contain exposed credentials. The LLM filters them to the high-value targets (paste sites, suspicious domains, breach databases).

**Example LLM decision:**
```
LinkedIn profile → skip (no exposure signal)
pastebin.com/abc123 → FETCH (paste sites often contain leaked data)
acme-login.support → FETCH (suspicious domain that could be phishing)
```

**What you see in the trace:**
```
▦  triage   Triaging 15 unique results...
▦  triage   Selected 5 pages to investigate.
```

The number of pages fetched is capped by `MAX_PAGES_TO_FETCH` in `.env` (default: 5).

---

## Stage 4 — FETCH

**What happens:** Each selected URL is downloaded using Bright Data's Web Unlocker zone.

**Why Web Unlocker?** Many sites (LinkedIn, Cloudflare-protected pages, some paste sites) block normal download requests. Web Unlocker routes the request through real browsers with real IPs, solving CAPTCHAs and bot-blocking automatically.

**What you see in the trace:**
```
◉  fetch    Fetching: https://pastebin.com/abc123
```

The raw HTML is then stripped of all tags, leaving only plain text (up to 6,000 characters) for the LLM to read.

---

## Stage 5 — ANALYZE

**What happens:** For each fetched page, the LLM reads the plain text and makes a judgment:
- Is there a real exposure signal here, or is this a false positive?
- If real: what category is it (credentials? phishing? brand abuse?)?
- How severe is it (critical / high / medium / low)?

**Example LLM assessment:**

For a paste site with leaked email:password pairs:
```json
{
  "is_real_signal": true,
  "category": "credentials",
  "severity": "critical",
  "summary": "A paste contains 47 email:password pairs mentioning acme.com employees. Passwords appear to be plaintext.",
  "evidence_note": "The paste lists corporate email addresses alongside passwords."
}
```

For a LinkedIn profile:
```json
{
  "is_real_signal": false,
  "category": "none",
  "severity": "info",
  "summary": "This is the official LinkedIn company page for Acme Corp."
}
```

**What you see in the trace:**
```
◆  analyze   Analyzing: https://pastebin.com/abc123
◆  analyze   → signal [CRITICAL/credentials] (NEW)
◆  analyze   Analyzing: https://linkedin.com/company/acme
◆  analyze   → no real signal (likely false positive)
```

The `(NEW)` tag means memory recognized this URL hasn't been seen in previous scans.

---

## Stage 6 — REPORT

**What happens:** The LLM takes all confirmed findings and writes a structured executive risk report:
- **Overall risk level** — the single most important number: CRITICAL / HIGH / MEDIUM / LOW
- **Headline** — one sentence summarizing the situation
- **Key findings** — each finding with severity, category, summary, URL, and recommended action
- **Next steps** — 3–5 concrete things the security team should do

**What you see in the trace:**
```
▲  report   Synthesizing risk report from 2 finding(s)...
```

Then the report renders on screen with color-coded cards.

---

## Stage 7 — MEMORY

**What happens:** The URLs of confirmed findings are saved to memory so the next time you scan the same company, SENTINEL knows which findings are **NEW** vs. **already seen**.

**Why this matters:** In a real security monitoring workflow, you run scans repeatedly. Without memory, every scan would alert you on the same old findings. With memory, you only get notifications for things that appeared since the last scan.

**Two memory backends:**

1. **Cognee (preferred)** — stores findings in a local graph database. Cognee can do semantic search over past scans (e.g. "what credentials were found for Acme Corp last month?").

2. **Local JSON (fallback)** — if Cognee fails, findings are stored in `.memory_store.json`. Simpler but still tracks seen URLs.

**What you see in the trace:**
```
◈  memory   Persisted 2 finding(s) to cognee memory.
✓  done     Scan complete.
```

---

## What a full trace looks like

Here is a real trace from scanning MetaNova AI:

```
◈  plan     Planning search strategy for MetaNova AI (www.metanovaai.com)...
◈  plan     Planned 5 queries.
◎  search   Searching (google): site:pastebin.com "metanovaai.com" password
◎  search   → 0 results
◎  search   Searching (google): intitle:"MetaNova AI" -site:metanovaai.com
◎  search   → 8 results
◎  search   Searching (bing): "metanovaai.com" AND (breach OR leak)
◎  search   → 1 results
▦  triage   Triaging 8 unique results...
▦  triage   Selected 5 pages to investigate.
◉  fetch    Fetching: https://www.linkedin.com/company/metanovaai
◆  analyze  Analyzing: https://www.linkedin.com/company/metanovaai
◆  analyze  → no real signal (likely false positive)
◉  fetch    Fetching: https://www.f6s.com/company/metanova-ai
◆  analyze  → no real signal (likely false positive)
▲  report   Synthesizing risk report from 0 finding(s)...
◈  memory   Persisted scan baseline to cognee memory.
✓  done     Scan complete.
```

**Result:** Overall risk **LOW** — no public exposures found. This is a good baseline scan.

---

## How errors are handled

Every external call (Bright Data, LLM) is wrapped in a try/except:

- If a **search query** fails → the agent logs the error and continues with the next query
- If a **page fetch** fails → the agent logs the error and skips that URL
- If **triage** fails → the agent falls back to taking the top N results by default
- If **Cognee** fails → the agent falls back to local JSON memory
- If the **LLM** returns malformed JSON → the parser tries 7 recovery strategies before giving up

This means a single bad query or slow connection never kills the whole scan.
