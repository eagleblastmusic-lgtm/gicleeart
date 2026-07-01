"""Parsowanie odpowiedzi Gemini (czat z blokiem kodu / API)."""

from __future__ import annotations

import re

from Komponenty.dodajobraz.description_update import (
    normalize_title_alternatives,
    parse_title_change_fields,
)

_CODE_FENCE_RE = re.compile(r"```(?:\w+)?\s*\n?(.*?)```", re.DOTALL | re.IGNORECASE)
_ORIG_SLASH_RE = re.compile(
    r"^Tytu[lł]\s+oryginalny\s*/[^:]+:\s*",
    re.MULTILINE | re.IGNORECASE,
)


def strip_markdown_code_block(text: str) -> str:
    raw = (text or "").strip()
    if "```" not in raw:
        return raw
    m = _CODE_FENCE_RE.search(raw)
    if m:
        return m.group(1).strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            return "\n".join(lines[1:]).strip()
    return raw


_ALT_SPLIT: dict[str, str] = {
    "pl": r"\s+lub\s+",
    "en": r"\s+or\s+",
    "de": r"\s+oder\s+",
    "fr": r"\s+ou\s+",
    "es": r"\s+o\s+",
    "it": r"\s+o\s+",
    "nl": r"\s+of\s+",
    "orig": r"\s+of\s+",
}


def _coerce_bare_alternatives(value: str, lang_key: str) -> str:
    pat = _ALT_SPLIT.get(lang_key)
    if not pat:
        return value
    parts = re.split(pat, value, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return value
    return f"{parts[0].strip()} lub {parts[1].strip()}"


def parse_gemini_title_fields(text: str) -> dict[str, str]:
    """Parsuje odpowiedz Gemini; «A lub B» / «A or B» -> «A (lub B)» dla workflow sklepu."""
    out = strip_markdown_code_block(text)
    out = _ORIG_SLASH_RE.sub("Tytuł oryginalny: ", out)
    fields = parse_title_change_fields(out)
    normalized: dict[str, str] = {}
    for key, val in fields.items():
        v = _coerce_bare_alternatives(val, key)
        v = normalize_title_alternatives(v, key)
        if key == "orig":
            v = re.split(r"\s+lub\s+", v, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            v = re.split(r"\s+of\s+", v, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        normalized[key] = v
    return normalized
