"""Kursy NBP historyczne — ostatni dzień roboczy przed datą przychodu."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any

from Komponenty._shared import fx_rates as shared_fx

from .storage import find_cached_rate, store_exchange_rate

_NBP_DATE_URL = "https://api.nbp.pl/api/exchangerates/rates/a/{currency}/{ymd}/?format=json"
_MAX_LOOKBACK_DAYS = 14


class NbpRateError(Exception):
    pass


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw).date()
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def last_business_day_before(d: date) -> date:
    """Ostatni dzień roboczy poprzedzający datę d (nie włącznie z d jeśli d to poniedziałek → piątek)."""
    cur = d - timedelta(days=1)
    while is_weekend(cur):
        cur -= timedelta(days=1)
    return cur


def income_date_from_order(payment_date: str, created_at: str) -> date:
    return parse_iso_date(payment_date) or parse_iso_date(created_at) or date.today()


def _fetch_nbp_for_date(currency: str, rate_date: date) -> tuple[float, str]:
    cur = currency.upper()
    if cur == "PLN":
        return 1.0, ""
    ymd = rate_date.isoformat()
    cached = find_cached_rate(cur, ymd)
    if cached:
        return float(cached.get("rate_value") or 0), str(cached.get("table_number") or "")

    url = _NBP_DATE_URL.format(currency=cur.lower(), ymd=ymd)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "GicleeApp/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:  # noqa: S310
            body = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise NbpRateError(f"Brak kursu NBP dla {cur} w dniu {ymd}") from e
        raise NbpRateError(f"NBP HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise NbpRateError(str(e)) from e

    data = json.loads(body.decode("utf-8"))
    rates = data.get("rates") or []
    if not rates:
        raise NbpRateError("Pusta odpowiedź NBP")
    mid = float(rates[0].get("mid") or 0)
    table_no = str(rates[0].get("no") or data.get("table") or "")
    store_exchange_rate({
        "currency": cur,
        "rate_date": ymd,
        "rate_value": mid,
        "table_number": table_no,
        "source": "NBP",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    })
    return mid, table_no


def fetch_rate_for_income_date(
    currency: str,
    income_date: date,
    *,
    manual_rate: float | None = None,
) -> dict[str, Any]:
    cur = (currency or "PLN").upper()
    if cur == "PLN":
        return {
            "original_currency": "PLN",
            "exchange_rate_source": "NBP",
            "exchange_rate_table_number": "",
            "exchange_rate_date": income_date.isoformat(),
            "exchange_rate_value": 1.0,
            "exchange_rate_status": "not_needed",
        }
    if manual_rate is not None and manual_rate > 0:
        return {
            "original_currency": cur,
            "exchange_rate_source": "manual",
            "exchange_rate_table_number": "",
            "exchange_rate_date": income_date.isoformat(),
            "exchange_rate_value": float(manual_rate),
            "exchange_rate_status": "manual",
        }

    target = last_business_day_before(income_date)
    errors: list[str] = []
    for _ in range(_MAX_LOOKBACK_DAYS):
        if is_weekend(target):
            target -= timedelta(days=1)
            continue
        try:
            rate, table_no = _fetch_nbp_for_date(cur, target)
            return {
                "original_currency": cur,
                "exchange_rate_source": "NBP",
                "exchange_rate_table_number": table_no,
                "exchange_rate_date": target.isoformat(),
                "exchange_rate_value": rate,
                "exchange_rate_status": "fetched",
            }
        except NbpRateError as exc:
            errors.append(str(exc))
            target -= timedelta(days=1)

    # Fallback: bieżący kurs z shared fx_rates
    try:
        rate, info = shared_fx.get_rate(cur, force_refresh=False)
        return {
            "original_currency": cur,
            "exchange_rate_source": str(info.get("source") or "NBP"),
            "exchange_rate_table_number": "",
            "exchange_rate_date": str(info.get("fetched_at") or "")[:10],
            "exchange_rate_value": float(rate),
            "exchange_rate_status": "error" if info.get("stale") else "fetched",
        }
    except shared_fx.FxError:
        return {
            "original_currency": cur,
            "exchange_rate_source": "NBP",
            "exchange_rate_table_number": "",
            "exchange_rate_date": "",
            "exchange_rate_value": 0.0,
            "exchange_rate_status": "missing",
        }


def convert_amounts_to_pln(
    *,
    products: float,
    shipping: float,
    discounts: float,
    total: float,
    rate: float,
) -> dict[str, float]:
    if rate <= 0:
        rate = 1.0
    return {
        "products_amount_pln": round(products * rate, 2),
        "shipping_amount_pln": round(shipping * rate, 2),
        "discounts_amount_pln": round(discounts * rate, 2),
        "total_amount_pln": round(total * rate, 2),
    }
