"""Testy parserów komponentu limity (bez sieci)."""

from __future__ import annotations

from Komponenty.limity.collectors import (
    ServiceSection,
    WORKER_DAILY_REQUEST_QUOTA,
    _analytics_usage_from_worker_stats,
    _parse_quota_header,
    _worst_status,
)


def test_parse_quota_header_plain() -> None:
    assert _parse_quota_header("42") == 42


def test_parse_quota_header_fraction() -> None:
    assert _parse_quota_header("15/3000") == 15


def test_parse_quota_header_empty() -> None:
    assert _parse_quota_header(None) is None
    assert _parse_quota_header("") is None


def test_worst_status_picks_critical() -> None:
    sections = [
        ServiceSection(key="a", title="A", status="OK", status_color="#2e7d32"),
        ServiceSection(key="b", title="B", status="Krytycznie", status_color="#e65100"),
    ]
    label, _ = _worst_status(sections)
    assert label == "Krytycznie"


def test_analytics_usage_meter_with_events_today() -> None:
    meter, lines = _analytics_usage_from_worker_stats(
        {
            "ok": True,
            "analytics": True,
            "total_events": 120,
            "events_today": 42,
            "bot_events": 5,
            "last_event_at": "2026-06-15T19:00:00Z",
        }
    )
    assert meter is not None
    assert meter.used == 42
    assert meter.quota == WORKER_DAILY_REQUEST_QUOTA
    assert any("łącznie: 120" in ln for ln in lines)


def test_analytics_usage_no_secret() -> None:
    meter, lines = _analytics_usage_from_worker_stats({"ok": False, "error": "no secret"})
    assert meter is None
    assert lines


def test_worst_status_error_beats_ok() -> None:
    sections = [
        ServiceSection(key="a", title="A", status="OK", status_color="#2e7d32"),
        ServiceSection(key="b", title="B", error="fail"),
    ]
    label, color = _worst_status(sections)
    assert label == "Błąd"
    assert color == "#c62828"
