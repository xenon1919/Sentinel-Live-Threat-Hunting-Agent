"""
The exposure-monitor agent orchestrator.

A hand-legible LangChain-powered loop with explicit stages. It is written as a
generator that YIELDS AgentEvent objects as it works, so the UI (or CLI) can
stream the agent's reasoning live — type a company, watch it think. That live
trace is the core of the demo.

Stages:
  1. plan     - LLM proposes targeted, defensive search queries
  2. search   - Bright Data SERP API runs each query
  3. triage   - LLM picks which result URLs are worth reading
  4. fetch    - Bright Data Web Unlocker retrieves each page
  5. analyze  - LLM assesses each page for a real exposure signal
  6. report   - LLM synthesizes a prioritized risk report
  7. remember - memory persists findings; NEW vs seen is computed

Every external call is defensive (try/except) so one bad page can't kill a run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from .config import Settings
from .llm import build_llm, parse_json_response
from . import prompts
from bright_data.client import BrightDataClient, BrightDataConfig, BrightDataError
from bright_data.parsing import parse_serp_html, extract_text
from memory.store import build_memory


@dataclass
class AgentEvent:
    stage: str          # plan|search|triage|fetch|analyze|report|memory|error|done
    message: str        # human-readable line for the live trace
    data: Any = None    # optional structured payload


@dataclass
class ScanResult:
    company: str
    domain: str
    report: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    memory_backend: Optional[str] = None


class ExposureMonitorAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = build_llm(settings)
        self.bd = BrightDataClient(
            BrightDataConfig(
                api_key=settings.brightdata_api_key,
                unlocker_zone=settings.brightdata_unlocker_zone,
                serp_zone=settings.brightdata_serp_zone,
            )
        )
        self.memory = build_memory(settings.enable_memory)

    # ----- LLM helper ----------------------------------------------------

    def _ask_json(self, system: str, user: str) -> dict:
        msgs = [SystemMessage(content=system), HumanMessage(content=user)]
        resp = self.llm.invoke(msgs)
        return parse_json_response(resp.content)

    # ----- main loop -----------------------------------------------------

    def scan(self, company: str, domain: str, context: str = "") -> Generator[AgentEvent, None, ScanResult]:
        result = ScanResult(company=company, domain=domain)
        if self.memory:
            result.memory_backend = self.memory.backend

        known_urls = self.memory.recall_known_urls(company) if self.memory else set()
        if known_urls:
            yield AgentEvent("memory", f"Recalled {len(known_urls)} URL(s) from previous scans of {company}.")

        # 1) PLAN -----------------------------------------------------------
        yield AgentEvent("plan", f"Planning search strategy for {company} ({domain})...")
        try:
            plan = self._ask_json(
                prompts.PLANNER_SYSTEM,
                prompts.PLANNER_USER.format(company=company, domain=domain, context=context or "none"),
            )
            queries = plan.get("queries", [])[:7]
        except Exception as exc:
            yield AgentEvent("error", f"Planning failed: {exc}")
            return result
        yield AgentEvent("plan", f"Planned {len(queries)} queries.", data=queries)

        # 2) SEARCH ---------------------------------------------------------
        all_hits: List[dict] = []
        for q in queries:
            qstr = q.get("query", "")
            engine = q.get("engine", "google")
            if not qstr:
                continue
            yield AgentEvent("search", f"Searching ({engine}): {qstr}")
            try:
                html = self.bd.search(qstr, engine=engine, num=self.settings.max_search_results)
                hits = parse_serp_html(html, max_hits=self.settings.max_search_results)
            except BrightDataError as exc:
                yield AgentEvent("error", f"Search failed for {qstr!r}: {exc}")
                continue
            for h in hits:
                d = h.to_dict()
                d["_query"] = qstr
                all_hits.append(d)
            yield AgentEvent("search", f"  -> {len(hits)} results", data=[h.to_dict() for h in hits])

        if not all_hits:
            yield AgentEvent("error", "No search results gathered; aborting.")
            return result

        # de-dupe by url
        deduped = {h["url"]: h for h in all_hits}
        all_hits = list(deduped.values())

        # 3) TRIAGE ---------------------------------------------------------
        yield AgentEvent("triage", f"Triaging {len(all_hits)} unique results...")
        results_block = "\n".join(
            f"- {h['title']} | {h['url']} | {h.get('snippet','')[:140]}" for h in all_hits[:40]
        )
        try:
            triage = self._ask_json(
                prompts.TRIAGE_SYSTEM.format(max_pages=self.settings.max_pages_to_fetch),
                prompts.TRIAGE_USER.format(company=company, domain=domain, results=results_block),
            )
            selected = triage.get("selected", [])[: self.settings.max_pages_to_fetch]
        except Exception as exc:
            yield AgentEvent("error", f"Triage failed: {exc}")
            selected = [{"url": h["url"], "suspected_category": "other"} for h in all_hits[: self.settings.max_pages_to_fetch]]
        yield AgentEvent("triage", f"Selected {len(selected)} pages to investigate.", data=selected)

        # 4) FETCH + 5) ANALYZE --------------------------------------------
        findings: List[dict] = []
        for sel in selected:
            url = sel.get("url")
            if not url:
                continue
            yield AgentEvent("fetch", f"Fetching: {url}")
            try:
                page_html = self.bd.fetch_page(url)
                page_text = extract_text(page_html)
            except BrightDataError as exc:
                yield AgentEvent("error", f"Fetch failed for {url}: {exc}")
                continue

            yield AgentEvent("analyze", f"Analyzing: {url}")
            try:
                assessment = self._ask_json(
                    prompts.ANALYST_SYSTEM,
                    prompts.ANALYST_USER.format(
                        company=company,
                        domain=domain,
                        url=url,
                        category=sel.get("suspected_category", "other"),
                        page_text=page_text,
                    ),
                )
            except Exception as exc:
                yield AgentEvent("error", f"Analysis failed for {url}: {exc}")
                continue

            if assessment.get("is_real_signal"):
                assessment["url"] = url
                assessment["is_new"] = url not in known_urls
                findings.append(assessment)
                tag = "NEW" if assessment["is_new"] else "seen before"
                yield AgentEvent(
                    "analyze",
                    f"  -> signal [{assessment.get('severity','?')}/{assessment.get('category','?')}] ({tag})",
                    data=assessment,
                )
            else:
                yield AgentEvent("analyze", "  -> no real signal (likely false positive)")

        result.findings = findings

        # 6) REPORT ---------------------------------------------------------
        yield AgentEvent("report", f"Synthesizing risk report from {len(findings)} finding(s)...")
        new_count = sum(1 for f in findings if f.get("is_new"))
        memory_note = (
            f"Note: {new_count} of {len(findings)} findings are NEW since the last scan; "
            f"prioritize these."
            if known_urls
            else "Note: this is the first scan; all findings are new."
        )
        try:
            report = self._ask_json(
                prompts.REPORT_SYSTEM,
                prompts.REPORT_USER.format(
                    company=company,
                    domain=domain,
                    findings=json.dumps(findings, indent=2),
                    memory_note=memory_note,
                ),
            )
        except Exception as exc:
            yield AgentEvent("error", f"Report synthesis failed: {exc}")
            report = {"overall_risk": "unknown", "headline": "Report generation failed", "key_findings": findings}
        result.report = report

        # 7) REMEMBER -------------------------------------------------------
        if self.memory and findings:
            try:
                self.memory.remember_findings(company, findings)
                yield AgentEvent("memory", f"Persisted {len(findings)} finding(s) to {self.memory.backend} memory.")
            except Exception as exc:
                yield AgentEvent("error", f"Memory write failed: {exc}")

        yield AgentEvent("done", "Scan complete.", data=report)
        return result
