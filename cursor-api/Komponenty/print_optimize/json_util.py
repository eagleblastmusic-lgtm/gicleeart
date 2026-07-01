"""Wyciaganie JSON z odpowiedzi Gemini."""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Pusta odpowiedz modelu.")

    fence = _JSON_FENCE_RE.search(raw)
    if fence:
        raw = fence.group(1).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Brak obiektu JSON w odpowiedzi modelu.")
    blob = raw[start : end + 1]
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError as exc:
        blob = blob.replace("\n", " ")
        blob = re.sub(r",\s*}", "}", blob)
        blob = re.sub(r",\s*]", "]", blob)
        parsed = json.loads(blob)
    if not isinstance(parsed, dict):
        raise ValueError("Oczekiwano obiektu JSON.")
    return parsed
