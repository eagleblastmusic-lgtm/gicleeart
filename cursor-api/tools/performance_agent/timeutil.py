"""Timezone-aware timestamps for Performance Agent."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def parse_iso_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def duration_ms_between(start_ts: str | None, end_ts: str | None) -> float | None:
    start = parse_iso_ts(start_ts)
    end = parse_iso_ts(end_ts)
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds() * 1000.0)
