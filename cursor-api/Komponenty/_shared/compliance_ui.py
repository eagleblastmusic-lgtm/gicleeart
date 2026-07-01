"""Wspólne monitory compliance do wyświetlania w modułach finansowych."""

from __future__ import annotations

from datetime import date
from typing import Any


def compliance_monitors(year: int | None = None) -> list[dict[str, Any]]:
    """Zwraca listę monitorów: title, message, level."""
    y = year or date.today().year
    try:
        from Komponenty._shared.compliance_monitors import (
            foreign_service_alerts,
            ksef_b2b_monthly_status,
            wsto_oss_status,
        )
    except ImportError:
        return []

    rows: list[dict[str, Any]] = []
    for title, fn, kwargs in (
        ("WSTO / OSS", wsto_oss_status, {"year": y}),
        ("KSeF B2B (mies.)", ksef_b2b_monthly_status, {"year": y}),
        ("Art. 28b / VAT-UE", foreign_service_alerts, {"year": y}),
    ):
        try:
            st = fn(**kwargs)
            rows.append({
                "title": title,
                "message": str(st.get("message") or ""),
                "level": str(st.get("level") or "ok"),
            })
        except Exception as exc:
            rows.append({
                "title": title,
                "message": f"Błąd monitora: {exc}",
                "level": "warn",
            })
    return rows


_LEVEL_COLORS = {
    "ok": "#2e7d32",
    "caution": "#ef6c00",
    "warn": "#e65100",
    "over": "#b71c1c",
}


def level_color(level: str) -> str:
    return _LEVEL_COLORS.get(level, "#333")
