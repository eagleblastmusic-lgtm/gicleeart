"""Kursy walut FX dla aplikacji Giclee.

Shopify Admin API nie udostepnia kursow walut. Do przeliczania cen uzywamy
publicznego API NBP, a cache runtime zapisujemy poza source checkoutem.

Nowy zapis:
    %LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/_shared/data/fx_cache.json

Legacy read fallback:
    cursor-api/Komponenty/_shared/data/fx_cache.json
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text, cache_path


_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_LEGACY_CACHE_FILE = _LEGACY_DATA_DIR / "fx_cache.json"

# Zachowane punkty podmiany dla starszych testow/callerow. Domyslny runtime
# rozstrzyga AppData dynamicznie przez _store().
_DEFAULT_DATA_DIR = _LEGACY_DATA_DIR
_DEFAULT_CACHE_FILE = _LEGACY_CACHE_FILE
_DATA_DIR = _DEFAULT_DATA_DIR
_CACHE_FILE = _DEFAULT_CACHE_FILE

_RUNTIME_RELATIVE = "Komponenty/_shared/data/fx_cache.json"
_TTL_HOURS = 24
_NBP_URL_TEMPLATE = "https://api.nbp.pl/api/exchangerates/rates/A/{currency}/?format=json"


class FxError(Exception):
    """Blad pobierania kursu walut."""


def _store():
    return cache_path(_RUNTIME_RELATIVE, legacy=_LEGACY_CACHE_FILE)


def _override_cache_file() -> Path | None:
    cache_file = Path(_CACHE_FILE)
    if cache_file != _DEFAULT_CACHE_FILE:
        return cache_file

    data_dir = Path(_DATA_DIR)
    if data_dir != _DEFAULT_DATA_DIR:
        return data_dir / "fx_cache.json"
    return None


def _read_file() -> Path:
    override = _override_cache_file()
    return override if override is not None else _store().read_path()


def _write_file() -> Path:
    override = _override_cache_file()
    return override if override is not None else _store().write_path


def _ensure_dir() -> None:
    """Compatibility helper; normal writes use atomic_write_text directly."""

    _write_file().parent.mkdir(parents=True, exist_ok=True)


def load_cache() -> dict[str, Any]:
    path = _read_file()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict[str, Any]) -> None:
    atomic_write_text(
        _write_file(),
        json.dumps(cache, ensure_ascii=False, indent=2),
    )


def _store_rate(
    currency: str, rate: float, *, source: str, fetched_at: str | None = None
) -> None:
    cache = load_cache()
    cache[currency.upper()] = {
        "rate": float(rate),
        "source": source,
        "fetched_at": fetched_at or datetime.now().isoformat(timespec="seconds"),
    }
    save_cache(cache)


def _fetch_nbp(currency: str) -> float:
    url = _NBP_URL_TEMPLATE.format(currency=currency.upper())
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "GicleeApp/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:  # noqa: S310
            body = resp.read()
    except urllib.error.URLError as e:
        raise FxError(f"NBP niedostepne: {e}") from e
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise FxError(f"Zla odpowiedz NBP: {e}") from e
    rates = data.get("rates") or []
    if not rates:
        raise FxError(f"Brak kursu w odpowiedzi NBP dla {currency}")
    mid = rates[0].get("mid")
    if mid is None:
        raise FxError("Brak pola 'mid' w odpowiedzi NBP")
    return float(mid)


def _is_fresh(entry: dict[str, Any]) -> bool:
    """True jesli cache nie przekroczyl TTL (manual ma TTL nieskonczony)."""

    source = str(entry.get("source") or "").lower()
    if source == "manual":
        return True
    ts = str(entry.get("fetched_at") or "")
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return False
    return (datetime.now() - dt) < timedelta(hours=_TTL_HOURS)


def get_rate(
    currency: str = "EUR", *, force_refresh: bool = False,
) -> tuple[float, dict[str, Any]]:
    """Zwraca (rate, info) gdzie info = {source, fetched_at, stale?}."""

    currency = currency.upper()
    cache = load_cache()
    entry = cache.get(currency)

    if entry and not force_refresh and _is_fresh(entry):
        return float(entry["rate"]), {
            "source": entry.get("source", "cache"),
            "fetched_at": entry.get("fetched_at", ""),
            "stale": False,
        }

    if entry and str(entry.get("source") or "").lower() == "manual" and not force_refresh:
        return float(entry["rate"]), {
            "source": "manual",
            "fetched_at": entry.get("fetched_at", ""),
            "stale": False,
        }

    try:
        rate = _fetch_nbp(currency)
        _store_rate(currency, rate, source="NBP")
        return rate, {
            "source": "NBP",
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "stale": False,
        }
    except FxError as e:
        if entry:
            return float(entry["rate"]), {
                "source": entry.get("source", "cache"),
                "fetched_at": entry.get("fetched_at", ""),
                "stale": True,
                "error": str(e),
            }
        raise


def set_manual_rate(currency: str, rate: float) -> None:
    """Zapisuje reczny kurs (TTL nieskonczony)."""

    if rate <= 0:
        raise ValueError("Kurs musi byc > 0")
    _store_rate(currency, rate, source="manual")


def clear_manual_rate(currency: str) -> None:
    """Usuwa reczny kurs; nastepny get_rate pobierze wartosc z NBP."""

    cache = load_cache()
    entry = cache.get(currency.upper())
    if entry and str(entry.get("source") or "").lower() == "manual":
        cache.pop(currency.upper(), None)
        save_cache(cache)


def get_eur_rate(*, force_refresh: bool = False) -> float:
    """Szybki helper - zwraca sam kurs EUR (tyle PLN za 1 EUR)."""

    rate, _info = get_rate("EUR", force_refresh=force_refresh)
    return rate


def describe_rate(currency: str = "EUR") -> str:
    """Zwraca opis np. 'NBP: 4.31 PLN/EUR (2026-04-20 12:00)'."""

    try:
        rate, info = get_rate(currency)
    except FxError as e:
        return f"Blad pobierania kursu: {e}"
    source = info.get("source", "?")
    fetched = info.get("fetched_at", "")
    stale = " [CACHE]" if info.get("stale") else ""
    date_part = ""
    if fetched:
        date_part = f" ({fetched[:16].replace('T', ' ')})"
    return f"{source}: {rate:.4f} PLN/{currency.upper()}{stale}{date_part}"
