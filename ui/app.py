"""
SENTINEL – Autonomous Open-Web Exposure Monitor
Split-panel layout: brand/form left · terminal/report right.
Run:  streamlit run ui/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from agent.config import Settings
from agent.orchestrator import ExposureMonitorAgent

# ── Palette ────────────────────────────────────────────────────────────────────
SEV_COLOR = {
    "critical": "#ff3b3b", "high": "#ff7b00", "medium": "#f5c518",
    "low":      "#00d4c8", "info": "#4a6282", "unknown": "#4a6282",
}
SEV_BG = {
    "critical": "rgba(255,59,59,0.12)",  "high":    "rgba(255,123,0,0.12)",
    "medium":   "rgba(245,197,24,0.10)", "low":     "rgba(0,212,200,0.10)",
    "info":     "rgba(74,98,130,0.10)",  "unknown": "rgba(74,98,130,0.10)",
}
STAGE_COLOR = {
    "plan":    "#a78bfa", "search":  "#00d4c8", "triage": "#60a5fa",
    "fetch":   "#38bdf8", "analyze": "#34d399", "report": "#fbbf24",
    "memory":  "#c084fc", "error":   "#f87171", "done":   "#00d4c8",
}
STAGE_ICON = {
    "plan": "◈", "search": "◎", "triage": "▦", "fetch":  "◉",
    "analyze": "◆", "report": "▲", "memory": "◈", "error": "✕", "done": "✓",
}

# ── Global CSS ─────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600;700;900&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: #060b14 !important;
    color: #c8d8f0 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Hide all Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebar"],
.stDeployButton { display: none !important; visibility: hidden !important; }

/* ── Remove all default padding / margins from the main container ── */
.main .block-container,
[data-testid="stMainBlockContainer"] {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #060b14; }
::-webkit-scrollbar-thumb { background: #1a2840; border-radius: 2px; }

/* ── Column layout ── */
[data-testid="stHorizontalBlock"] {
    gap: 0 !important;
    align-items: stretch !important;
    min-height: 100vh;
}

/* Left panel */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
    background: #070d1a !important;
    border-right: 1px solid #0e1a2e !important;
    min-height: 100vh;
    position: sticky !important;
    top: 0 !important;
    align-self: flex-start !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child > div {
    padding: 2.4rem 2rem !important;
    display: flex;
    flex-direction: column;
    height: 100%;
}

/* Right panel */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child > div {
    padding: 2.4rem 2.2rem !important;
}

/* ── Inputs ── */
.stTextInput label,
.stTextArea label {
    color: #4a6882 !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    margin-bottom: 4px !important;
}
.stTextInput input,
.stTextArea textarea {
    background: #0b1525 !important;
    border: 1px solid #192840 !important;
    border-radius: 8px !important;
    color: #c8d8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
    caret-color: #00d4c8 !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: #00d4c8 !important;
    box-shadow: 0 0 0 3px rgba(0,212,200,0.12) !important;
    outline: none !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder { color: #1e3050 !important; }

/* ── Run button ── */
button[kind="primary"],
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #00d4c8 0%, #0091a0 100%) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #030a10 !important;
    font-weight: 800 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    font-size: 0.73rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    padding: 0.65rem 1.2rem !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    width: 100% !important;
}
button[kind="primary"]:hover,
[data-testid="baseButton-primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(0,212,200,0.4) !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: rgba(245,197,24,0.07) !important;
    border: 1px solid rgba(245,197,24,0.25) !important;
    border-radius: 8px !important;
    color: #e5b700 !important;
}

/* ── Sentinel component classes ── */

/* shield shapes */
.snt-shield-lg {
    width: 58px; height: 58px;
    background: linear-gradient(145deg, #00d4c8 0%, #006070 100%);
    clip-path: polygon(50% 0%, 100% 22%, 100% 72%, 50% 100%, 0% 72%, 0% 22%);
    box-shadow: 0 0 36px rgba(0,212,200,0.28), 0 0 80px rgba(0,212,200,0.08);
    flex-shrink: 0;
}
.snt-shield-sm {
    width: 26px; height: 26px;
    background: linear-gradient(145deg, #00d4c8 0%, #006070 100%);
    clip-path: polygon(50% 0%, 100% 22%, 100% 72%, 50% 100%, 0% 72%, 0% 22%);
    flex-shrink: 0;
}

/* divider */
.snt-divider { border: none; border-top: 1px solid #131f35; margin: 1.4rem 0; }

/* section label */
.snt-section-label {
    font-size: 0.62rem; color: #4a6882;
    letter-spacing: 0.2em; text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
    margin-bottom: 0.85rem;
}

/* tech badges */
.snt-badges { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 0.4rem; }
.snt-badge-tech {
    border: 1px solid #1e3050; color: #4a6882;
    font-size: 0.58rem; letter-spacing: 0.18em;
    padding: 4px 11px; border-radius: 4px;
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
    text-transform: uppercase;
    transition: border-color 0.2s, color 0.2s;
}
.snt-badge-tech:hover { border-color: rgba(0,212,200,0.5); color: #00d4c8; }

/* new badge */
.snt-new {
    background: rgba(0,212,200,0.12); color: #00d4c8;
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em;
    padding: 2px 8px; border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    border: 1px solid rgba(0,212,200,0.28); text-transform: uppercase;
}

/* terminal */
.snt-terminal {
    background: #050e1c;
    border: 1px solid #0e1a2e;
    border-radius: 13px;
    overflow: hidden;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    box-shadow: 0 24px 70px rgba(0,0,0,0.65), 0 0 0 1px rgba(0,212,200,0.03);
}
.snt-titlebar {
    background: #091322;
    padding: 11px 18px;
    display: flex; align-items: center; gap: 8px;
    border-bottom: 1px solid #0e1a2e;
}
.snt-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.snt-dot-r { background: #ff5f57; } .snt-dot-y { background: #febc2e; } .snt-dot-g { background: #28c840; }
.snt-tbar-label { flex:1; text-align:center; color:#3a5878; font-size:0.67rem; letter-spacing:0.12em; }
.snt-body {
    padding: 18px 22px;
    height: 360px;
    overflow-y: auto;
    display: flex; flex-direction: column; gap: 5px;
}
.snt-body::-webkit-scrollbar { width: 3px; }
.snt-body::-webkit-scrollbar-thumb { background: #0e1a2e; }
.snt-line {
    display: grid;
    grid-template-columns: 18px 90px 1fr;
    gap: 10px; align-items: baseline;
    font-size: 0.79rem; line-height: 1.56;
    opacity: 0; animation: snt-in 0.2s ease forwards;
}
@keyframes snt-in {
    from { opacity:0; transform:translateY(5px); }
    to   { opacity:1; transform:none; }
}
.snt-li { font-size: 0.67rem; }
.snt-ls { font-weight: 700; font-size: 0.7rem; letter-spacing: 0.07em; }
.snt-lm { color: #4a6882; }
.snt-line.l-done   .snt-lm { color: #00d4c8; font-weight: 600; }
.snt-line.l-error  .snt-lm { color: #f87171; }
.snt-line.l-signal .snt-lm { color: #b0c8e8; }

/* idle terminal */
.snt-idle-line { color: #3a5878; font-size: 0.79rem; line-height: 2.1; }
.snt-idle-line .il-icon { color: #00d4c8; opacity: 0.5; }
.snt-idle-line .il-stage { color: #4a6882; font-weight: 600; }
.snt-idle-line .il-msg { color: #3a5878; }
.snt-cursor { display:inline-block; width:8px; height:13px;
              background:#3a5878; animation:blink 1.1s step-end infinite; vertical-align:middle; }
@keyframes blink { 50% { opacity: 0; } }

/* risk banner */
.snt-risk-banner {
    border-radius: 12px; padding: 1.3rem 1.6rem;
    margin-bottom: 1.6rem; position:relative; overflow:hidden;
}
.snt-risk-banner::after {
    content:''; position:absolute; inset:0;
    background: linear-gradient(135deg,rgba(255,255,255,0.018),transparent);
    pointer-events:none;
}
.snt-risk-label {
    font-size: 0.62rem; letter-spacing: 0.22em; text-transform: uppercase;
    color: #4a6882; font-family: 'JetBrains Mono', monospace;
    font-weight: 700; margin-bottom: 7px;
}
.snt-risk-level {
    font-size: 2.2rem; font-weight: 900;
    letter-spacing: 0.08em; text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace; line-height: 1;
}
.snt-risk-hl { color: #7090b0; font-size: 0.86rem; margin-top: 9px; line-height: 1.65; }

/* finding card */
.snt-card {
    border-radius: 10px; padding: 0.95rem 1.2rem;
    margin-bottom: 0.65rem; transition: transform 0.14s;
}
.snt-card:hover { transform: translateX(4px); }
.snt-sev-badge {
    display:inline-flex; align-items:center;
    font-size: 0.62rem; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    padding: 3px 9px; border-radius: 4px;
    font-family: 'JetBrains Mono', monospace; margin-right: 5px;
}
.snt-cat-badge {
    display:inline-flex; align-items:center;
    background: #0d1a2e; color: #4a6882;
    font-size: 0.65rem; padding: 3px 9px; border-radius: 4px;
    font-family: 'JetBrains Mono', monospace; margin-right: 5px;
}
.snt-card-summary { color: #8aa8c8; font-size: 0.84rem; line-height: 1.65; margin: 0.45rem 0 0.35rem; }
.snt-card-url { font-size: 0.68rem; color: #3a5878; font-family:'JetBrains Mono',monospace; word-break:break-all; margin-bottom:0.35rem; }
.snt-card-action { font-size: 0.8rem; color: #c8a840; }
.snt-card-action-lbl { color: #4a6882; }

/* next steps */
.snt-steps { list-style:none; padding:0; margin:0; }
.snt-steps li {
    display:flex; align-items:flex-start; gap:10px;
    color: #4a6882; font-size: 0.83rem; line-height: 1.7;
    padding: 7px 0; border-bottom: 1px solid #09142a;
}
.snt-steps li:last-child { border-bottom:none; }
.snt-step-arrow { color:#00d4c8; font-size:0.55rem; margin-top:5px; flex-shrink:0; }

/* memory chip */
.snt-mem-chip {
    display:inline-flex; align-items:center; gap:6px;
    background: rgba(192,132,252,0.07); border:1px solid rgba(192,132,252,0.18);
    border-radius:6px; padding:4px 11px;
    font-size:0.65rem; color:#7840b0;
    font-family:'JetBrains Mono',monospace; letter-spacing:0.07em; margin-top:8px;
}

/* footer tagline */
.snt-footer {
    font-size: 0.58rem; color: #2a4060;
    letter-spacing: 0.2em; text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
    margin-top: auto; padding-top: 2rem;
    border-top: 1px solid #131f35;
}
</style>
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _e(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _trace_line(stage: str, message: str) -> str:
    color = STAGE_COLOR.get(stage, "#4a6282")
    icon  = STAGE_ICON.get(stage, "·")
    cls   = ("l-done"   if stage == "done"  else
             "l-error"  if stage == "error" else
             "l-signal" if (stage == "analyze" and "signal" in message) else "")
    return (
        f'<div class="snt-line {cls}">'
        f'<span class="snt-li" style="color:{color}">{icon}</span>'
        f'<span class="snt-ls" style="color:{color}">{stage}</span>'
        f'<span class="snt-lm">{_e(message)}</span>'
        f'</div>'
    )


def _terminal(body: str, label: str = "sentinel · live trace") -> str:
    return f"""
<div class="snt-terminal">
  <div class="snt-titlebar">
    <div class="snt-dot snt-dot-r"></div>
    <div class="snt-dot snt-dot-y"></div>
    <div class="snt-dot snt-dot-g"></div>
    <div class="snt-tbar-label">{_e(label)}</div>
  </div>
  <div class="snt-body" id="snt-scroll">{body}</div>
</div>
<script>
  (function(){{var e=document.getElementById('snt-scroll');if(e)e.scrollTop=e.scrollHeight;}})();
</script>"""


def _idle_terminal() -> str:
    body = """
<div class="snt-idle-line">
  <span class="il-icon">◈</span>&nbsp;&nbsp;<span class="il-stage">sentinel</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="il-msg">initialized</span>
</div>
<div class="snt-idle-line">
  <span class="il-icon">◈</span>&nbsp;&nbsp;<span class="il-stage">memory</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="il-msg">cognee backend ready</span>
</div>
<div class="snt-idle-line">
  <span class="il-icon">◎</span>&nbsp;&nbsp;<span class="il-stage">bright data</span>&nbsp;<span class="il-msg">SERP + Web Unlocker connected</span>
</div>
<div class="snt-idle-line">
  <span class="il-icon">◆</span>&nbsp;&nbsp;<span class="il-stage">llm</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="il-msg">gemini model loaded</span>
</div>
<div class="snt-idle-line" style="margin-top:10px;color:#2a4060;">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;awaiting target &nbsp;<span class="snt-cursor"></span>
</div>"""
    return _terminal(body, "sentinel · ready")


def _finding_card(f: dict) -> str:
    sev    = (f.get("severity") or "info").lower()
    color  = SEV_COLOR.get(sev, "#4a6282")
    bg     = SEV_BG.get(sev, "rgba(74,98,130,0.10)")
    cat    = _e(f.get("category") or "unknown")
    sm     = _e(f.get("summary") or "")
    url    = _e(f.get("url") or "")
    action = _e(f.get("recommended_action") or "")
    nb     = '<span class="snt-new">new</span>' if f.get("is_new") else ""
    return f"""
<div class="snt-card" style="background:{bg};border:1px solid {color}28;border-left:3px solid {color};">
  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:5px;margin-bottom:4px;">
    <span class="snt-sev-badge" style="background:{color}18;color:{color};">{sev}</span>
    <span class="snt-cat-badge">{cat}</span>{nb}
  </div>
  <div class="snt-card-summary">{sm}</div>
  {'<div class="snt-card-url">'+url+'</div>' if url else ''}
  {'<div class="snt-card-action"><span class="snt-card-action-lbl">action → </span>'+action+'</div>' if action else ''}
</div>"""


# ── Panel renderers ────────────────────────────────────────────────────────────

def render_left_panel() -> None:
    # Logo + title
    st.markdown("""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:1rem;">
  <div class="snt-shield-lg"></div>
  <div>
    <div style="font-size:2rem;font-weight:900;letter-spacing:0.12em;color:#fff;
                font-family:'Inter',sans-serif;line-height:1;">SENTINEL</div>
    <div style="font-size:0.62rem;color:#00d4c8;letter-spacing:0.22em;
                font-family:'JetBrains Mono',monospace;margin-top:4px;text-transform:uppercase;">
      Autonomous Open-Web Exposure Monitor
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Track label
    st.markdown("""
<div style="font-size:0.6rem;color:#3a5878;letter-spacing:0.2em;font-family:'JetBrains Mono',monospace;
            font-weight:700;text-transform:uppercase;margin-bottom:1rem;">
  WEB DATA UNLOCKED · TRACK 3
</div>
""", unsafe_allow_html=True)

    # Description
    st.markdown("""
<p style="font-size:0.82rem;color:#5a7890;line-height:1.75;margin-bottom:0;">
  Hunts the open web for your organization's leaked credentials,
  impersonation domains, and brand abuse — then returns a
  prioritized risk report in real time.
</p>
""", unsafe_allow_html=True)

    st.markdown('<hr class="snt-divider">', unsafe_allow_html=True)

    # Form label
    st.markdown('<div class="snt-section-label">Scan Target</div>', unsafe_allow_html=True)


def render_left_footer() -> None:
    # Tech badges
    st.markdown("""
<hr class="snt-divider" style="margin-top:1.6rem;">
<div class="snt-section-label">Powered by</div>
<div class="snt-badges">
  <span class="snt-badge-tech">Bright Data</span>
  <span class="snt-badge-tech">LangChain</span>
  <span class="snt-badge-tech">Gemini</span>
  <span class="snt-badge-tech">Cognee</span>
</div>
""", unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""
<div style="margin-top:1.2rem;font-size:0.68rem;color:#3a5575;line-height:1.9;
            font-family:'JetBrains Mono',monospace;">
  Defensive use only.<br>
  Scope to organizations you own<br>
  or are authorized to protect.
</div>
""", unsafe_allow_html=True)

    # Footer tagline
    st.markdown("""
<div class="snt-footer">
  Built on Bright Data · Live Web Intelligence for Defenders
</div>
""", unsafe_allow_html=True)


def render_report(report: dict) -> None:
    overall  = (report.get("overall_risk") or "unknown").lower()
    color    = SEV_COLOR.get(overall, "#4a6282")
    bg       = SEV_BG.get(overall, "rgba(74,98,130,0.08)")
    headline = _e(report.get("headline") or "")

    st.markdown(f"""
<div class="snt-risk-banner" style="background:{bg};border:1px solid {color}30;border-left:4px solid {color};">
  <div class="snt-risk-label">Overall Risk</div>
  <div class="snt-risk-level" style="color:{color};">{overall}</div>
  {'<div class="snt-risk-hl">'+headline+'</div>' if headline else ''}
</div>""", unsafe_allow_html=True)

    findings = report.get("key_findings") or []
    if findings:
        st.markdown('<div class="snt-section-label">Key Findings</div>', unsafe_allow_html=True)
        st.markdown("".join(_finding_card(f) for f in findings), unsafe_allow_html=True)

    steps = report.get("recommended_next_steps") or []
    if steps:
        items = "".join(
            f'<li><span class="snt-step-arrow">▶</span>{_e(s)}</li>'
            for s in steps
        )
        st.markdown(f"""
<div style="margin-top:1.6rem;">
  <div class="snt-section-label">Recommended Next Steps</div>
  <ul class="snt-steps">{items}</ul>
</div>""", unsafe_allow_html=True)


# ── App entry ──────────────────────────────────────────────────────────────────

st.set_page_config(page_title="SENTINEL", page_icon="🛡️", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Config check (early, silent)
try:
    settings = Settings.load()
    config_ok, config_err = True, ""
except Exception as exc:
    config_ok, config_err = False, str(exc)

# ── Two-column split ──────────────────────────────────────────────────────────
left, right = st.columns([4, 6], gap="small")

# ── LEFT panel ────────────────────────────────────────────────────────────────
with left:
    render_left_panel()

    company = st.text_input("Company name", placeholder="e.g. Acme Corp")
    domain  = st.text_input("Primary domain", placeholder="e.g. acme.com")
    context = st.text_area(
        "Extra context",
        placeholder="industry · region · known aliases (optional)",
        height=80,
    )
    run = st.button("⬡  Run Scan", type="primary", use_container_width=True)

    if not config_ok:
        st.markdown(
            f'<div style="font-size:0.72rem;color:#ff3b3b;margin-top:0.6rem;'
            f'font-family:JetBrains Mono,monospace;">⚠ config error: {_e(config_err)}</div>',
            unsafe_allow_html=True,
        )

    render_left_footer()

# ── RIGHT panel ───────────────────────────────────────────────────────────────
with right:
    if not config_ok:
        st.markdown(_idle_terminal(), unsafe_allow_html=True)

    elif not run:
        # Idle state
        st.markdown(_idle_terminal(), unsafe_allow_html=True)

    elif not company or not domain:
        st.markdown(_idle_terminal(), unsafe_allow_html=True)
        st.markdown(
            '<div style="margin-top:0.8rem;font-size:0.78rem;color:#c8a840;'
            'font-family:JetBrains Mono,monospace;">⚠ enter company name and domain to begin</div>',
            unsafe_allow_html=True,
        )

    else:
        # Live scan
        agent = ExposureMonitorAgent(settings)

        st.markdown(
            '<div class="snt-section-label" style="margin-bottom:0.7rem;">Live Agent Trace</div>',
            unsafe_allow_html=True,
        )
        trace_ph = st.empty()

        trace_lines: list[str] = []
        final_report   = None
        memory_backend = None

        gen = agent.scan(company, domain, context)
        try:
            while True:
                ev = next(gen)
                trace_lines.append(_trace_line(ev.stage, ev.message))
                trace_ph.markdown(
                    _terminal("\n".join(trace_lines), f"sentinel · {company} · {domain}"),
                    unsafe_allow_html=True,
                )
                if ev.stage == "done":
                    final_report = ev.data
        except StopIteration as stop:
            res = stop.value
            if res and res.report:
                final_report = res.report
            if res and res.memory_backend:
                memory_backend = res.memory_backend

        if memory_backend:
            st.markdown(
                f'<div class="snt-mem-chip">◈ &nbsp;memory · {_e(memory_backend)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="snt-divider" style="margin:1.6rem 0;">', unsafe_allow_html=True)

        if final_report:
            render_report(final_report)
        else:
            st.markdown(
                '<div style="font-size:0.8rem;color:#4a6282;font-family:JetBrains Mono,monospace;">'
                'scan finished — no report generated. check trace for errors.</div>',
                unsafe_allow_html=True,
            )
