"""
Offline smoke test. Mocks Bright Data + the LLM so we can verify the agent
loop, SERP parsing, memory NEW/seen diffing, and event streaming WITHOUT any
API keys or network. Run: python selftest.py
"""

import json
import types

from agent.config import Settings
from agent.orchestrator import ExposureMonitorAgent, AgentEvent
from bright_data.parsing import parse_serp_html, extract_text


# ---- 1) parsing works -------------------------------------------------------
SAMPLE_SERP = """
<html><body>
  <div><a href="/url?q=https://pastebin.com/raw/abc123&sa=U">Acme leaked creds dump</a>
       <span>emails and hashes posted for acme.com users</span></div>
  <div><a href="https://acme-login.support">Acme Login Portal</a>
       <span>sign in to your acme account</span></div>
  <div><a href="https://www.google.com/search?q=foo">ignore me</a></div>
</body></html>
"""
hits = parse_serp_html(SAMPLE_SERP)
assert any("pastebin.com" in h.url for h in hits), "should extract pastebin url"
assert all("google." not in h.url for h in hits), "should drop google links"
assert extract_text("<html><body><script>x</script><p>Hello  world</p></body></html>") == "Hello world"
print(f"[ok] parsing: {len(hits)} hits extracted, text extraction clean")


# ---- 2) build agent with mocked dependencies --------------------------------
settings = Settings(
    brightdata_api_key="x", brightdata_unlocker_zone="uz", brightdata_serp_zone="sz",
    aiml_api_key="x", aiml_base_url="http://x", aiml_model="gpt-4o",
    max_search_results=5, max_pages_to_fetch=3, enable_memory=True,
)

# bypass real __init__ network/LLM construction
agent = ExposureMonitorAgent.__new__(ExposureMonitorAgent)
agent.settings = settings

# mock Bright Data
class FakeBD:
    def search(self, query, engine="google", num=10):
        return SAMPLE_SERP
    def fetch_page(self, url):
        if "pastebin" in url:
            return "<html><body>Dump of acme.com accounts: 1200 email:hash pairs leaked.</body></html>"
        return "<html><body>Generic page about acme, nothing sensitive.</body></html>"
agent.bd = FakeBD()

# mock LLM by overriding _ask_json to return canned, stage-appropriate JSON
def fake_ask_json(system, user):
    if "planning module" in system:
        return {"queries": [
            {"query": "acme.com leaked credentials", "engine": "google", "rationale": "creds"},
            {"query": "acme login phishing", "engine": "bing", "rationale": "phish"},
        ]}
    if "triage module" in system:
        return {"selected": [
            {"url": "https://pastebin.com/raw/abc123", "reason": "dump", "suspected_category": "credentials"},
            {"url": "https://acme-login.support", "reason": "lookalike", "suspected_category": "phishing"},
        ]}
    if "analysis module" in system:
        if "pastebin" in user:
            return {"is_real_signal": True, "category": "credentials", "severity": "critical",
                    "summary": "Public dump references acme.com account data.", "evidence_note": "bulk email/hash pairs"}
        return {"is_real_signal": False, "category": "none", "severity": "info",
                "summary": "no signal", "evidence_note": "n/a"}
    if "reporting module" in system:
        return {"overall_risk": "critical", "headline": "Leaked credentials exposed publicly",
                "key_findings": [{"category": "credentials", "severity": "critical",
                                  "summary": "Public dump references acme.com accounts.",
                                  "url": "https://pastebin.com/raw/abc123",
                                  "recommended_action": "Force password resets; notify affected users."}],
                "recommended_next_steps": ["Rotate credentials", "File takedown for lookalike domain"]}
    return {}
agent._ask_json = fake_ask_json

# real local memory (fresh)
import os
for f in (".memory_store.json", ".memory_store_cognee.json"):
    if os.path.exists(f):
        os.remove(f)
from memory.store import _LocalMemory
agent.memory = _LocalMemory(".selftest_mem.json")
if os.path.exists(".selftest_mem.json"):
    os.remove(".selftest_mem.json")
agent.memory = _LocalMemory(".selftest_mem.json")


# ---- 3) first scan: everything should be NEW --------------------------------
def run_scan():
    gen = agent.scan("Acme Corp", "acme.com")
    events, result = [], None
    try:
        while True:
            events.append(next(gen))
    except StopIteration as s:
        result = s.value
    return events, result

events, result = run_scan()
stages = [e.stage for e in events]
assert "plan" in stages and "search" in stages and "analyze" in stages and "done" in stages
assert result.report["overall_risk"] == "critical"
assert len(result.findings) == 1 and result.findings[0]["is_new"] is True
print(f"[ok] first scan: {len(events)} events streamed, 1 NEW critical finding, report synthesized")

# ---- 4) second scan: same finding should now be 'seen before' ---------------
events2, result2 = run_scan()
assert result2.findings[0]["is_new"] is False, "finding should be recalled as seen"
print("[ok] memory diffing: repeat finding correctly marked as seen (not new)")

# cleanup
if os.path.exists(".selftest_mem.json"):
    os.remove(".selftest_mem.json")

print("\nALL SELFTESTS PASSED ✅")
