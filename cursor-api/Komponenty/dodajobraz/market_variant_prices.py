"""Reczne ceny wariantow (grupa drewno+rozmiar) per rynek — obok markup % w Rynki."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text, config_path

_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_LEGACY_PRICES_FILE = _LEGACY_DATA_DIR / "market_variant_prices.json"
_DATA_DIR = _LEGACY_DATA_DIR
_PRICES_FILE = _LEGACY_PRICES_FILE


def _prices_path(*, for_write: bool = False) -> Path:
    data_dir = Path(_DATA_DIR)
    current = Path(_PRICES_FILE)
    if data_dir != _LEGACY_DATA_DIR and current == _LEGACY_PRICES_FILE:
        current = data_dir / "market_variant_prices.json"
    if current != _LEGACY_PRICES_FILE:
        return current
    app_path = config_path(
        "Komponenty/dodajobraz/data/market_variant_prices.json",
        legacy=_LEGACY_PRICES_FILE,
    )
    return app_path.write_path if for_write else app_path.read_path()


def group_key(wood: str, size: str) -> str:
    return f"{(wood or '').strip()}|{(size or '').strip()}"


def parse_group_key(key: str) -> tuple[str, str] | None:
    if "|" not in key:
        return None
    wood, size = key.split("|", 1)
    return wood, size


def _read_raw() -> dict[str, Any]:
    path = _prices_path()
    if not path.is_file():
        return {"markets": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"markets": {}}
    if not isinstance(data, dict):
        return {"markets": {}}
    if "markets" not in data or not isinstance(data["markets"], dict):
        data["markets"] = {}
    return data


def _write_raw(data: dict[str, Any]) -> None:
    atomic_write_text(
        _prices_path(for_write=True),
        json.dumps(data, ensure_ascii=False, indent=2),
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
