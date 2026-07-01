"""Reczne ceny wariantow (grupa drewno+rozmiar) per rynek — obok markup % w Rynki."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_PRICES_FILE = _DATA_DIR / "market_variant_prices.json"


def group_key(wood: str, size: str) -> str:
    return f"{(wood or '').strip()}|{(size or '').strip()}"


def parse_group_key(key: str) -> tuple[str, str] | None:
    if "|" not in key:
        return None
    wood, size = key.split("|", 1)
    return wood, size


def _read_raw() -> dict[str, Any]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _PRICES_FILE.is_file():
        return {"markets": {}}
    try:
        data = json.loads(_PRICES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"markets": {}}
    if not isinstance(data, dict):
        return {"markets": {}}
    if "markets" not in data or not isinstance(data["markets"], dict):
        data["markets"] = {}
    return data


def _write_raw(data: dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _PRICES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_market_prices(market_code: str) -> dict[str, str]:
    code = (market_code or "").strip().lower()
    markets = _read_raw().get("markets") or {}
    raw = markets.get(code) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if v is None:
            continue
        txt = str(v).strip().replace(",", ".")
        if not txt:
            continue
        if re.fullmatch(r"\d+(\.\d{1,2})?", txt):
            out[str(k)] = txt
    return out


def set_market_variant_price(
    market_code: str,
    wood: str,
    size: str,
    price: str | float | None,
) -> None:
    """Ustaw reczna cene (pusty/None = usun override, wraca do markup %)."""
    code = (market_code or "").strip().lower()
    data = _read_raw()
    markets: dict[str, Any] = dict(data.get("markets") or {})
    bucket = dict(markets.get(code) or {})

    gk = group_key(wood, size)
    if price is None or str(price).strip() == "":
        bucket.pop(gk, None)
    else:
        txt = str(price).strip().replace(",", ".")
        val = float(txt)
        if val <= 0:
            bucket.pop(gk, None)
        else:
            bucket[gk] = f"{val:.2f}"

    if bucket:
        markets[code] = bucket
    else:
        markets.pop(code, None)

    data["markets"] = markets
    _write_raw(data)


def get_market_variant_price(market_code: str, wood: str, size: str) -> str | None:
    return load_market_prices(market_code).get(group_key(wood, size))


def clear_market_prices(market_code: str) -> None:
    code = (market_code or "").strip().lower()
    data = _read_raw()
    markets = dict(data.get("markets") or {})
    markets.pop(code, None)
    data["markets"] = markets
    _write_raw(data)
