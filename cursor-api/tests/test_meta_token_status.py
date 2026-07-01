"""Testy meta_token_status (bez sieci)."""

from __future__ import annotations

from datetime import datetime, timezone

from Komponenty.socialmedia.cykl.meta_token_status import (
    _days_left_from_expires,
    _estimate_days_from_checked,
    _expires_unix,
)


def test_expires_unix_prefers_expires_at() -> None:
    assert _expires_unix({"expires_at": 1000, "data_access_expires_at": 2000}) == 1000


def test_days_left_from_expires() -> None:
    future = int(datetime.now(timezone.utc).timestamp()) + 10 * 86400
    assert _days_left_from_expires(future) in (9, 10)


def test_days_left_zero_means_no_expiry() -> None:
    assert _days_left_from_expires(0) is None


def test_estimate_days_from_checked() -> None:
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    est = _estimate_days_from_checked(checked)
    assert est is not None
    assert 55 <= est <= 60


def test_latest_renewal_iso_prefers_newest() -> None:
    from Komponenty.socialmedia.cykl.meta_token_status import _latest_renewal_iso

    raw = {
        "token_renewed_at": "2026-06-01T10:00:00+00:00",
        "fb_pl": {"checked_at": "2026-06-04T10:00:00+00:00"},
    }
    assert _latest_renewal_iso(raw, raw["fb_pl"]) == "2026-06-04T10:00:00+00:00"
