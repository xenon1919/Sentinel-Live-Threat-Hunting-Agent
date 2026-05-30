"""
Agent memory.

Drives the "only alert on NEW exposures since last scan" behaviour, which is
both genuinely useful for a monitoring tool and the hook for the Cognee
"Best Use of Agent Memory" partner prize.

We try to use Cognee if it's installed and configured. If not (or if Cognee
errors), we fall back to a small local JSON store so the project always runs.
Both backends expose the same interface:

    remember_findings(company, findings)   # persist this scan
    recall_known_urls(company) -> set[str] # URLs we've already reported

The agent uses recall_known_urls to mark findings as NEW vs. previously seen.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path
from typing import List, Set


def _run_async(coro) -> None:
    """Run a coroutine safely whether or not an event loop is already running.

    Streamlit owns an event loop on the main thread, so asyncio.run() raises
    RuntimeError('This event loop is already running').  Spinning up a
    dedicated daemon thread with its own fresh loop sidesteps that entirely.
    """
    def _worker():
        asyncio.run(coro)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=60)


class _LocalMemory:
    """Simple JSON-file memory. Always available."""

    def __init__(self, path: str = ".memory_store.json"):
        self.path = Path(path)
        if not self.path.exists():
            self.path.write_text("{}")

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text() or "{}")
        except json.JSONDecodeError:
            return {}

    def recall_known_urls(self, company: str) -> Set[str]:
        return set(self._load().get(company.lower(), []))

    def remember_findings(self, company: str, findings: List[dict]) -> None:
        data = self._load()
        key = company.lower()
        known = set(data.get(key, []))
        for f in findings:
            if f.get("url"):
                known.add(f["url"])
        data[key] = sorted(known)
        self.path.write_text(json.dumps(data, indent=2))

    @property
    def backend(self) -> str:
        return "local-json"


class _CogneeMemory:
    """Cognee-backed memory. Stores findings as knowledge the agent can later
    cognify and search. Falls back to local for the URL-diff bookkeeping so the
    NEW/seen logic stays exact (Cognee is semantic, not a key-value set).
    """

    def __init__(self):
        # ── Configure Cognee's LLM before the first import ──────────────────
        # Cognee reads its LLM provider from these env vars.  We mirror the
        # project's AIML_* settings so Cognee uses the same key/endpoint.
        # dotenv has already been loaded by agent/config.py at startup.
        api_key  = os.getenv("AIML_API_KEY", "")
        base_url = os.getenv("AIML_BASE_URL", "")
        model    = os.getenv("AIML_MODEL", "gpt-4o")

        if api_key:
            os.environ.setdefault("OPENAI_API_KEY", api_key)
            os.environ.setdefault("LLM_API_KEY",    api_key)
        if base_url:
            os.environ.setdefault("LLM_ENDPOINT",    base_url)
            os.environ.setdefault("OPENAI_BASE_URL", base_url)
        if model:
            os.environ.setdefault("LLM_MODEL", model)

        # Also try the async config API as a belt-and-suspenders measure
        import cognee

        async def _configure():
            try:
                await cognee.config.set_llm_config({
                    "llm_provider": "openai",
                    "llm_api_key":  api_key,
                    "llm_model":    model,
                    "llm_endpoint": base_url,
                })
            except Exception:
                pass  # env vars above are the primary mechanism

        _run_async(_configure())

        self._cognee = cognee
        self._local  = _LocalMemory(".memory_store_cognee.json")

    def recall_known_urls(self, company: str) -> Set[str]:
        return self._local.recall_known_urls(company)

    def remember_findings(self, company: str, findings: List[dict]) -> None:
        self._local.remember_findings(company, findings)

        try:
            text = self._render(company, findings)

            async def _store():
                await self._cognee.add(text)
                await self._cognee.cognify()

            _run_async(_store())
        except Exception as exc:
            print(f"[memory] Cognee store skipped: {exc}")

    @staticmethod
    def _render(company: str, findings: List[dict]) -> str:
        lines = [f"Exposure scan for {company}:"]
        for f in findings:
            lines.append(
                f"- [{f.get('severity','?')}] {f.get('category','?')}: "
                f"{f.get('summary','')} ({f.get('url','')})"
            )
        return "\n".join(lines)

    @property
    def backend(self) -> str:
        return "cognee"


def build_memory(enable_memory: bool):
    """Return the best available memory backend, or None if disabled."""
    if not enable_memory:
        return None
    try:
        return _CogneeMemory()
    except Exception as exc:
        print(f"[memory] Cognee unavailable ({exc}); using local JSON memory.")
        return _LocalMemory()
