"""
LLM access via the AI/ML API (a hackathon partner).

AI/ML API is OpenAI-compatible, so we use langchain_openai.ChatOpenAI and just
point base_url at https://api.aimlapi.com/v1. This keeps us inside the
LangChain ecosystem (per the chosen stack) while using the partner's models
and credits.
"""

from __future__ import annotations

import json
from typing import Optional

from langchain_openai import ChatOpenAI

from .config import Settings


def build_llm(settings: Settings, temperature: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.aiml_model,
        api_key=settings.aiml_api_key,
        base_url=settings.aiml_base_url,
        temperature=temperature,
        timeout=90,
        max_retries=2,
    )


def parse_json_response(content: str) -> dict:
    """LLMs sometimes wrap JSON in ```json fences or add prose. Strip and parse
    defensively so a stray backtick doesn't crash the agent loop.
    """
    text = content.strip()
    if "```" in text:
        # take the largest fenced block
        parts = text.split("```")
        # parts alternate text/code; pick the longest that looks like json
        candidates = [p for p in parts if "{" in p]
        if candidates:
            text = max(candidates, key=len)
    text = text.replace("json", "", 1) if text.lstrip().startswith("json") else text
    # find first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)
