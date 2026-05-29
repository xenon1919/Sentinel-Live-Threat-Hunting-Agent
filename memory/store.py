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

import json
import os
from pathlib import Path
from typing import Iterable, List, Set


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
        import cognee  # noqa: F401  (import-time check)

        self._cognee = cognee
        self._local = _LocalMemory(".memory_store_cognee.json")

    def recall_known_urls(self, company: str) -> Set[str]:
        return self._local.recall_known_urls(company)

    def remember_findings(self, company: str, findings: List[dict]) -> None:
        # exact URL set for diffing
        self._local.remember_findings(company, findings)
        # semantic memory for the prize / richer recall
        try:
            import asyncio

            text = self._render(company, findings)

            async def _store():
                await self._cognee.add(text)
                await self._cognee.cognify()

            asyncio.run(_store())
        except Exception as exc:  # never let memory crash a scan
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
