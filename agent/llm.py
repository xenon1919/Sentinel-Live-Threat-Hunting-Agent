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
    """LLMs sometimes wrap JSON in ```json fences, add prose, return list roots,
    or truncate the response. Try multiple extraction strategies before giving up.
    Always returns a dict; list-at-root is wrapped under 'items'.
    """
    text = content.strip()

    # 1. Strip markdown fences — take the largest block that contains { or [
    if "```" in text:
        parts = text.split("```")
        candidates = [p.lstrip("json").strip() for p in parts if "{" in p or "[" in p]
        if candidates:
            text = max(candidates, key=len)

    # 2. Strip a bare leading "json" label (no fence)
    if text.lstrip().startswith("json"):
        text = text.lstrip()[4:].lstrip()

    def _to_dict(parsed) -> dict:
        """Ensure the parsed value is a dict; wrap lists under 'items'."""
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"items": parsed}
        return {"value": parsed}

    # 3. Slice the outermost { ... } block
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return _to_dict(json.loads(text[start : end + 1]))
        except json.JSONDecodeError:
            pass

    # 4. Slice the outermost [ ... ] array (LLM returned a list at the root)
    arr_start = text.find("[")
    arr_end   = text.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        try:
            return _to_dict(json.loads(text[arr_start : arr_end + 1]))
        except json.JSONDecodeError:
            pass

    # 5. Missing outer braces — try wrapping in {}
    if start == -1 and '"' in text:
        try:
            return _to_dict(json.loads("{" + text + "}"))
        except json.JSONDecodeError:
            pass

    # 6. Truncated response — close all unclosed brackets/braces and retry
    def _close(s: str) -> str:
        stack = []
        for ch in s:
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack and stack[-1] == ch:
                stack.pop()
        return s + "".join(reversed(stack))

    base = text[start:] if start != -1 else text
    try:
        return _to_dict(json.loads(_close(base)))
    except json.JSONDecodeError:
        pass

    # 7. Last resort: raw parse; log the snippet so failures are diagnosable
    try:
        return _to_dict(json.loads(text))
    except json.JSONDecodeError as exc:
        snippet = repr(content[:120])
        raise ValueError(f"JSON parse failed. Raw snippet: {snippet}") from exc
