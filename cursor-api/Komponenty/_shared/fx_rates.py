"""Kursy walut FX dla aplikacji Giclee.

Shopify Admin API **nie udostepnia kursow walut** - udostepnia tylko kod waluty
(`currencyCode`) i procentowy markup na price list. Zeby liczyc EUR z kursu,
uzywamy publicznego API NBP.

API NBP (darmowe, bez klucza):
    https://api.nbp.pl/api/exchangerates/rates/A/EUR/?format=json

Cache: `cursor-api/Komponenty/_shared/data/fx_cache.json`:
{
  "EUR": {
    "rate": 4.31,
    "source": "NBP",
    "fetched_at": "2026-04-20T12:00:00"
  }
}

TTL 24h - po tym czasie `get_rate()` probuje odswiezyc z NBP; przy bledzie
sieci uzywa cache (z ostrzezeniem). Rec zny override: `set_manual_rate(4.35)`.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CACHE_FILE = _DATA_DIR / "fx_cache.json"

_TTL_HOURS = 24

_NBP_URL_TEMPLATE = "https://api.nbp.pl/api/exchangerates/rates/A/{currency}/?format=json"


class FxError(Exception):
    """Blad pobierania kursu walut."""


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_cache() -> dict[str, Any]:
    _ensure_dir()
    if not _CACHE_FILE.is_file():
        return {}
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict[str, Any]) -> None:
    _ensure_dir()
    _CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
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
    """True jesli cache nie przekroczyl TTL (dla source=manual TTL jest nieskonczony)."""
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
    """Zwraca (rate, info) gdzie info = {source, fetched_at, stale?}.

    Algorytm:
      1. Jesli cache swiezy i nie force_refresh - zwracamy cache.
      2. W przeciwnym razie probujemy NBP. Przy sukcesie - zapisujemy cache.
      3. Przy bledzie - fallback do cache (z `stale=True`) albo raise FxError.
    """
    currency = currency.upper()
    cache = load_cache()
    entry = cache.get(currency)

    if entry and not force_refresh and _is_fresh(entry):
        return float(entry["rate"]), {
            "source": entry.get("source", "cache"),
            "fetched_at": entry.get("fetched_at", ""),
            "stale": False,
        }

    # Manual rate ma priorytet i zawsze traktujemy jako swiezy (nie odswiezamy NBP)
    if entry and str(entry.get("source") or "").lower() == "manual" and not force_refresh:
        return float(entry["rate"]), {
            "source": "manual",
            "fetched_at": entry.get("fetched_at", ""),
            "stale": False,
        }

    # Probujemy NBP
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
    """Zapisuje reczny kurs (TTL nieskonczony - nie odswieza automatycznie)."""
    if rate <= 0:
        raise ValueError("Kurs musi byc > 0")
    _store_rate(currency, rate, source="manual")


def clear_manual_rate(currency: str) -> None:
    """Usuwa reczny kurs - przy nastepnym `get_rate` pobierze z NBP."""
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
    """Zwraca czytelny opis np. 'NBP: 4.31 PLN/EUR (2026-04-20 12:00)'."""
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
