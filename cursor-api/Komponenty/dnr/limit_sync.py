"""Wspólny limit kwartalny DNR — źródło prawdy: dnr_settings.quarterly_limit."""

from __future__ import annotations

from .constants import DEFAULT_QUARTERLY_LIMIT
from .storage import load_settings, save_settings


def canonical_quarterly_limit() -> float:
    settings = load_settings()
    return round(float(settings.quarterly_limit or DEFAULT_QUARTERLY_LIMIT), 2)


def save_canonical_quarterly_limit(limit: float) -> float:
    """Zapisuje limit w DNR i synchronizuje kopię w ustawieniach KPiR."""
    value = round(float(limit), 2)
    settings = load_settings()
    settings.quarterly_limit = value
    save_settings(settings)
    try:
        from Komponenty.kpir.storage import load_settings as load_kpir_settings
        from Komponenty.kpir.storage import save_settings as save_kpir_settings

        kpir = load_kpir_settings()
        kpir.dnr_limit_quarterly = value
        save_kpir_settings(kpir)
    except Exception:
        pass
    return value
