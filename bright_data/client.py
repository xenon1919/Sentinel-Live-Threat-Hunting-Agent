"""
Bright Data client.

Wraps Bright Data's single REST endpoint (https://api.brightdata.com/request),
which powers BOTH the SERP API and the Web Unlocker. The endpoint takes a
`zone` (which Bright Data zone to route through), a target `url`, and a
`format` ("raw" for HTML/text, "json" for structured wrapper).

Docs:
  - Web Unlocker: https://docs.brightdata.com/scraping-automation/web-unlocker/send-your-first-request
  - SERP API:     https://docs.brightdata.com/scraping-automation/serp-api/introduction

You need two zones in your Bright Data control panel:
  - a Web Unlocker zone (for fetching arbitrary pages past bot/CAPTCHA/geo walls)
  - a SERP zone         (for search-engine result pages)
Set their names in .env (see .env.example).
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Optional

import requests

BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"

# Search engine result URLs. Bright Data's SERP zone resolves these like a
# real browser/search client and returns the rendered results page.
_SEARCH_TEMPLATES = {
    "google": "https://www.google.com/search?q={q}&num={n}",
    "bing": "https://www.bing.com/search?q={q}&count={n}",
    "yandex": "https://yandex.com/search/?text={q}",
}


@dataclass
class BrightDataConfig:
    api_key: str
    unlocker_zone: str
    serp_zone: str
    timeout: int = 90


class BrightDataError(RuntimeError):
    """Raised when a Bright Data request fails."""


class BrightDataClient:
    """Thin, typed wrapper over the Bright Data /request endpoint."""

    def __init__(self, config: BrightDataConfig):
        self.config = config
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }
        )

    # ----- low-level -----------------------------------------------------

    def _request(self, zone: str, url: str, fmt: str = "raw") -> str:
        payload = {"zone": zone, "url": url, "format": fmt}
        try:
            resp = self._session.post(
                BRIGHTDATA_ENDPOINT, json=payload, timeout=self.config.timeout
            )
        except requests.RequestException as exc:  # network-level failure
            raise BrightDataError(f"Network error calling Bright Data: {exc}") from exc

        if resp.status_code != 200:
            raise BrightDataError(
                f"Bright Data returned {resp.status_code} for zone={zone!r}: "
                f"{resp.text[:300]}"
            )
        return resp.text

    # ----- public API ----------------------------------------------------

    def fetch_page(self, url: str) -> str:
        """Fetch a single page through the Web Unlocker zone. Returns raw HTML/text.

        Use for paste sites, forums, lookalike domains — anything that may
        block a naive requests.get().
        """
        return self._request(self.config.unlocker_zone, url, fmt="raw")

    def search(self, query: str, engine: str = "google", num: int = 10) -> str:
        """Run a search-engine query through the SERP zone. Returns the raw
        results page (HTML). Parsing into structured hits is handled in
        parsing.py so this stays a thin transport layer.
        """
        engine = engine.lower()
        if engine not in _SEARCH_TEMPLATES:
            raise ValueError(f"Unsupported engine {engine!r}; pick one of {list(_SEARCH_TEMPLATES)}")
        q = urllib.parse.quote_plus(query)
        url = _SEARCH_TEMPLATES[engine].format(q=q, n=num)
        return self._request(self.config.serp_zone, url, fmt="raw")
