"""Testy liczenia maili Resend z listy (bez sieci)."""

from __future__ import annotations

from datetime import datetime, timezone

from Komponenty.limity.collectors import _parse_resend_created_at


def test_parse_resend_created_at_utc() -> None:
    dt = _parse_resend_created_at("2026-06-04 18:17:57.949105+00")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 6 and dt.day == 4


def test_parse_resend_created_at_z_suffix() -> None:
    dt = _parse_resend_created_at("2026-06-04T18:17:57Z")
    assert dt is not None
    assert dt.tzinfo == timezone.utc
