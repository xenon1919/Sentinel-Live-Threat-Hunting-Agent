# UI Guide

SENTINEL's web interface is built with Streamlit. This page explains every part of the UI and what it does.

---

## Layout overview

The screen is split into two panels:

```
┌─────────────────────────┬────────────────────────────────────┐
│                         │                                    │
│   LEFT PANEL            │   RIGHT PANEL                      │
│   (branding + form)     │   (live trace + report)            │
│                         │                                    │
│   🛡 SENTINEL           │   ● ● ●  sentinel · ready         │
│   Autonomous Open-Web   │                                    │
│   Exposure Monitor      │   ◈  sentinel    initialized       │
│                         │   ◈  memory      cognee ready      │
│   SCAN TARGET           │   ◎  bright data connected         │
│   Company name          │   ◆  llm         model loaded      │
│   [____________]        │                                    │
│   Primary domain        │   awaiting target ▌                │
│   [____________]        │                                    │
│   Extra context         │                                    │
│   [____________]        │                                    │
│                         │                                    │
│   [⬡ RUN SCAN]          │                                    │
│                         │                                    │
│   POWERED BY            │                                    │
│   Bright Data  LangChain│                                    │
│   Gemini  Cognee        │                                    │
└─────────────────────────┴────────────────────────────────────┘
```

---

## Left Panel

### Logo and header

```
🛡 SENTINEL
Autonomous Open-Web Exposure Monitor
WEB DATA UNLOCKED · TRACK 3
```

The hexagon shield icon is a CSS `clip-path` polygon with a teal gradient — no image file needed. The "WEB DATA UNLOCKED · TRACK 3" line is the hackathon track this project was built for.

### Description

```
Hunts the open web for your organization's leaked credentials,
impersonation domains, and brand abuse — then returns a
prioritized risk report in real time.
```

A brief one-sentence pitch explaining what the tool does.

### Scan Target form

**Company name** — The name of the company to scan. The LLM uses this to craft relevant search queries. Example: `Acme Corp`

**Primary domain** — The company's main website domain. Used to identify results that mention the company. Example: `acme.com` (not `https://www.acme.com`)

**Extra context** (optional) — Any additional information that helps the LLM craft better queries. Examples:
- `fintech, San Francisco` — narrows queries to the right industry/location
- `formerly known as OldName` — catches results that use an old name
- Leave blank if you have nothing to add

**Run Scan button** — Starts the scan. The button uses a teal gradient and glows on hover.

### Powered by

Tech badges showing the four main technologies:
- **Bright Data** — web search and page fetching
- **LangChain** — LLM orchestration
- **Gemini** — the AI model (or whichever model is set in `.env`)
- **Cognee** — agent memory

### Footer

```
Built on Bright Data · Live Web Intelligence for Defenders
```

Disclaimer below that: "Defensive use only. Scope to organizations you own or are authorized to protect."

---

## Right Panel

### Idle state (before a scan)

When no scan is running, the terminal shows:

```
◈  sentinel    initialized
◈  memory      cognee backend ready
◎  bright data SERP + Web Unlocker connected
◆  llm         gemini model loaded

               awaiting target ▌
```

The blinking cursor (`▌`) is a CSS animation — it blinks every 1.1 seconds.

### Live trace (during a scan)

Once you click Run Scan, the right panel becomes a live terminal. Each line appears as the agent completes that step.

**Stage icons and colors:**

| Icon | Stage | Color | Meaning |
|---|---|---|---|
| ◈ | plan | Purple | LLM planning phase |
| ◎ | search | Teal | Running a search query |
| ▦ | triage | Blue | Picking which URLs to read |
| ◉ | fetch | Light blue | Downloading a page |
| ◆ | analyze | Green | LLM analyzing a page |
| ▲ | report | Gold | Writing the risk report |
| ◈ | memory | Purple | Saving to Cognee |
| ✓ | done | Teal + bold | Scan complete |
| ✕ | error | Red | Something went wrong |

**Reading a trace line:**
```
◎  search   → 8 results
│   │         │
│   │         └── The message
│   └────────── Stage name (colored)
└──────────── Stage icon (colored)
```

**Signal lines** (when a real threat is found):
```
◆  analyze  → signal [CRITICAL/credentials] (NEW)
```

This line turns white to make it stand out from the other analyze lines.

**Error lines:**
```
✕  error   Search failed: Read timed out
```

Red text. The scan continues — errors are non-fatal.

### Memory chip

After the trace completes:
```
◈  memory · cognee
```

A small purple badge showing which memory backend was used (cognee or local-json).

---

## Risk Report

After the scan, a risk report appears below the trace.

### Overall Risk banner

A colored banner with the risk level:

| Color | Level | Meaning |
|---|---|---|
| 🔴 Red | CRITICAL | Immediate action required |
| 🟠 Orange | HIGH | Urgent attention needed |
| 🟡 Yellow | MEDIUM | Should be addressed soon |
| 🟢 Teal | LOW | No significant threats found |

Below the risk level, a headline summarizing what was found.

### Key Findings

Each finding is a card with a left-colored border:

```
┌─────────────────────────────────────────┐
│ CRITICAL  credentials  NEW              │
│                                         │
│ A Pastebin post contains 47 email:      │
│ password pairs for acme.com employees.  │
│                                         │
│ https://pastebin.com/abc123             │
│                                         │
│ action → Immediately require password   │
│ resets for all listed accounts and      │
│ enable MFA.                             │
└─────────────────────────────────────────┘
```

- **Severity badge** — color-coded (red=critical, orange=high, yellow=medium, teal=low)
- **Category badge** — what type of threat (credentials, phishing, impersonation, etc.)
- **NEW badge** — appears if this finding wasn't seen in previous scans
- **Summary** — 2-3 sentence description of the exposure
- **URL** — the source page where the exposure was found
- **Action** — what the security team should do

### Recommended Next Steps

A bulleted list of actionable items, like:
- Enable MFA for all employee accounts
- Monitor for new typosquatted domains registered in the last 30 days
- Contact the hosting provider to take down the phishing page

---

## Running without a browser (CLI mode)

If you don't want the web UI, run:

```bash
python run_cli.py --company "Acme Corp" --domain acme.com
```

Output looks like:
```
=== Exposure scan: Acme Corp (acme.com) ===

🧭 [plan] Planning search strategy...
🔎 [search] Searching (google): site:pastebin.com "acme.com"
🔎 [search]   -> 3 results
...
✅ [done] Scan complete.

=== FINAL RISK REPORT ===
{
  "overall_risk": "low",
  "headline": "No significant exposures found.",
  ...
}
```

Same information, no browser required.

---

## Customizing the UI

The entire visual style is defined by CSS injected in [`ui/app.py`](../ui/app.py) in the `GLOBAL_CSS` constant at the top of the file.

Key colors you can change:

```python
# In ui/app.py
SEV_COLOR = {
    "critical": "#ff3b3b",   # Red
    "high":     "#ff7b00",   # Orange
    "medium":   "#f5c518",   # Yellow
    "low":      "#00d4c8",   # Teal
}

STAGE_COLOR = {
    "plan":    "#a78bfa",    # Purple
    "search":  "#00d4c8",    # Teal
    "analyze": "#34d399",    # Green
    "done":    "#00d4c8",    # Teal
    ...
}
```

The main background color is `#060b14` (very dark navy). The left panel background is `#070d1a` (slightly lighter navy).
