"""
Configuration loaded from environment (.env supported via python-dotenv).

Keep all secrets and tunables here so the rest of the code never reads
os.environ directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill it in."
        )
    return val


@dataclass
class Settings:
    # Bright Data
    brightdata_api_key: str
    brightdata_unlocker_zone: str
    brightdata_serp_zone: str

    # AI/ML API (OpenAI-compatible)
    aiml_api_key: str
    aiml_base_url: str
    aiml_model: str

    # Agent tunables
    max_search_results: int
    max_pages_to_fetch: int
    enable_memory: bool

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            brightdata_api_key=_require("BRIGHTDATA_API_KEY"),
            brightdata_unlocker_zone=os.getenv("BRIGHTDATA_UNLOCKER_ZONE", "web_unlocker1").strip(),
            brightdata_serp_zone=os.getenv("BRIGHTDATA_SERP_ZONE", "serp_api1").strip(),
            aiml_api_key=_require("AIML_API_KEY"),
            aiml_base_url=os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1").strip(),
            aiml_model=os.getenv("AIML_MODEL", "gpt-4o").strip(),
            max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", "8")),
            max_pages_to_fetch=int(os.getenv("MAX_PAGES_TO_FETCH", "5")),
            enable_memory=os.getenv("ENABLE_MEMORY", "true").strip().lower() == "true",
        )
