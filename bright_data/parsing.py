"""
Parsing helpers: turn raw Bright Data responses into structured data the
agent can reason over.

Two jobs:
  1. parse_serp_html  -> list[SearchHit] from a search-engine results page
  2. extract_text     -> clean, truncated visible text from an arbitrary page

We keep parsing tolerant: search engines change markup constantly, so we try
a few strategies and degrade gracefully rather than throwing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import List

from bs4 import BeautifulSoup


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_serp_html(html: str, max_hits: int = 10) -> List[SearchHit]:
    """Extract result links + snippets from a Google/Bing results page.

    Heuristic and defensive: we look for anchor tags carrying real http(s)
    hrefs and pair them with nearby text. This won't be perfect, but it gives
    the agent a usable set of candidate URLs to investigate.
    """
    soup = BeautifulSoup(html, "html.parser")
    hits: List[SearchHit] = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Google wraps real URLs as /url?q=<real>&...
        m = re.search(r"/url\?q=(https?://[^&]+)", href)
        if m:
            href = urllib_unquote(m.group(1))
        if not href.startswith("http"):
            continue
        if any(bad in href for bad in ("google.", "bing.", "yandex.", "/search?", "webcache.")):
            continue
        if href in seen:
            continue
        seen.add(href)

        title = _clean(a.get_text())
        if not title:
            continue
        # snippet: grab text from the nearest container
        container = a.find_parent(["div", "li"])
        snippet = ""
        if container:
            snippet = _clean(container.get_text())
            snippet = snippet.replace(title, "", 1).strip()[:300]

        hits.append(SearchHit(title=title[:200], url=href, snippet=snippet))
        if len(hits) >= max_hits:
            break

    return hits


def extract_text(html: str, max_chars: int = 6000) -> str:
    """Strip a fetched page down to visible text for LLM consumption."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "head"]):
        tag.decompose()
    text = _clean(soup.get_text(separator=" "))
    return text[:max_chars]


def urllib_unquote(s: str) -> str:
    import urllib.parse

    return urllib.parse.unquote(s)
