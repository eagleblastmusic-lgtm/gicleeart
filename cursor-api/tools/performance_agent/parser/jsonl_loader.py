"""JSONL loader for studio_perf.log."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None


@dataclass
class PerfEvent:
    line_no: int
    ts: str | None
    event: str
    elapsed_ms: float | None = None
    since_enter_ms: float | None = None
    since_click_ms: float | None = None
    since_request_ms: float | None = None
    since_details_cta_ms: float | None = None
    queue_latency_ms: float | None = None
    element_id: str | None = None
    element_type: str | None = None
    generation: int | None = None
    stage: str | None = None
    module: str | None = None
    cache_hit: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, line_no: int, raw: dict[str, Any]) -> PerfEvent:
        generation = raw.get("generation")
        if generation is None:
            generation = raw.get("selection_generation_next")
        return cls(
            line_no=line_no,
            ts=raw.get("ts"),
            event=str(raw.get("event", "")),
            elapsed_ms=_optional_float(raw.get("elapsed_ms")),
            since_enter_ms=_optional_float(raw.get("since_enter_ms")),
            since_click_ms=_optional_float(raw.get("since_click_ms")),
            since_request_ms=_optional_float(raw.get("since_request_ms")),
            since_details_cta_ms=_optional_float(raw.get("since_details_cta_ms")),
            queue_latency_ms=_optional_float(raw.get("queue_latency_ms")),
            element_id=raw.get("element_id"),
            element_type=raw.get("element_type"),
            generation=_optional_int(generation),
            stage=raw.get("stage"),
            module=raw.get("module"),
            cache_hit=_optional_bool(raw.get("cache_hit")),
            raw=raw,
        )

    def primary_ms(self) -> float | None:
        for value in (
            self.elapsed_ms,
            self.since_click_ms,
            self.since_enter_ms,
            self.since_request_ms,
            self.since_details_cta_ms,
            self.queue_latency_ms,
        ):
            if value is not None:
                return value
        return None


@dataclass
class LoadResult:
    events: list[PerfEvent]
    malformed_lines: int
    total_lines: int


def load_jsonl(path: Path) -> LoadResult:
    events: list[PerfEvent] = []
    malformed_lines = 0
    total_lines = 0

    text = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        total_lines += 1
        stripped = line.strip()
        if not stripped:
            malformed_lines += 1
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue
        if not isinstance(raw, dict):
            malformed_lines += 1
            continue
        events.append(PerfEvent.from_raw(line_no, raw))

    return LoadResult(events=events, malformed_lines=malformed_lines, total_lines=total_lines)
