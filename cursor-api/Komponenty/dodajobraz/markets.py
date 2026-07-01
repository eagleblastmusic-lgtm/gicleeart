"""Modul rynkow: czytanie/zapis konfiguracji markupow + helpery do liczenia cen.

Konfiguracja: `markets_config.json` w tym samym katalogu (zrodlo prawdy aplikacji).

Funkcje:
  * load_markets()       -> list[Market]
  * save_markets(items)  -> None
  * compute_prices(base_pln_price, markets) -> dict[code -> price_string]
  * format_price(value, currency) -> str
  * get_market(code)     -> Market
  * update_market_markup(code, percent) -> Market
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent / "markets_config.json"


@dataclass
class Market:
    code: str
    name_pl: str
    locale: str
    currency: str
    url_prefix: str
    markup_percent: float
    is_base: bool = False
    name_en: str = ""
    shopify_market_gid: str = ""
    shopify_price_list_gid: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Market":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in d.items() if k in known}
        extra = {k: v for k, v in d.items() if k not in known and not k.startswith("_")}
        kwargs["extra"] = extra
        return cls(**kwargs)

    def to_dict(self) -> dict:
        d = asdict(self)
        extra = d.pop("extra", {}) or {}
        d.update(extra)
        return d


def _read_raw() -> dict:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Brak pliku konfiguracji: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _write_raw(data: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_markets() -> list[Market]:
    raw = _read_raw()
    items = raw.get("markets") or []
    return [Market.from_dict(it) for it in items]


def save_markets(items: list[Market]) -> None:
    raw = _read_raw()
    raw["markets"] = [m.to_dict() for m in items]
    _write_raw(raw)


def get_market(code: str) -> Market:
    code_norm = (code or "").strip().lower()
    for m in load_markets():
        if m.code.lower() == code_norm:
            return m
    raise KeyError(f"Nieznany rynek: {code!r}")


def base_market_code() -> str:
    raw = _read_raw()
    return (raw.get("base_market") or "pl").strip().lower()


def update_market_markup(code: str, new_percent: float) -> Market:
    """Zapisuje nowy markup dla danego rynku. Zwraca zaktualizowany Market.

    Markup bazowego rynku jest zawsze 0% (zignorowane jesli przyslesz inne).
    """
    items = load_markets()
    base = base_market_code()
    updated: Market | None = None
    for m in items:
        if m.code.lower() == code.lower():
            if m.code.lower() == base:
                m.markup_percent = 0.0
            else:
                m.markup_percent = float(new_percent)
            updated = m
            break
    if updated is None:
        raise KeyError(f"Nieznany rynek: {code!r}")
    save_markets(items)
    return updated


def compute_market_price(
    base_price: float,
    markup_percent: float,
    *,
    currency: str = "PLN",
    fx_rate: float | None = None,
) -> float:
    """Zaokraglone do 2 miejsc po przecinku.

    Dla walut innych niz PLN cena jest przeliczona po kursie walut:
        price_in_foreign = base_pln / fx_rate * (1 + markup/100)

    gdzie `fx_rate` to kurs (ile PLN za 1 jednostke waluty docelowej, np. 4.31 PLN/EUR).
    Kiedy `currency == "PLN"`, przeliczenie jest pomijane.
    """
    cur = (currency or "PLN").upper()
    multiplier = 1.0 + float(markup_percent) / 100.0
    if cur == "PLN":
        return round(float(base_price) * multiplier, 2)
    if not fx_rate or fx_rate <= 0:
        # Fallback: bez kursu zwroc surowa liczbe z markupem (lepiej cos niz crash).
        return round(float(base_price) * multiplier, 2)
    return round(float(base_price) / float(fx_rate) * multiplier, 2)


def market_price_in_eur(
    base_price_pln: float,
    markup_percent: float,
    *,
    currency: str = "PLN",
    fx_rates: dict[str, float] | None = None,
) -> float | None:
    """Cena rynkowa przeliczona na EUR — do porównania między rynkami w dialogu Rynki."""
    fx = fx_rates or {}
    eur_rate = fx.get("EUR")
    if not eur_rate or eur_rate <= 0:
        return None
    cur = (currency or "PLN").upper()
    rate = fx.get(cur) if cur != "PLN" else None
    price = compute_market_price(
        base_price_pln,
        markup_percent,
        currency=cur,
        fx_rate=rate,
    )
    if cur == "EUR":
        return price
    return round(price / float(eur_rate), 2)


def compute_prices_for_markets(
    base_price: float,
    markets: list[Market] | None = None,
    *,
    fx_rates: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Dla danej ceny PL (bazowej) zwraca liste {code, name_pl, currency, price, markup_percent}.

    Bazowy rynek dostaje cene 1:1 (markup 0%). Dla walut obcych cena jest
    przeliczana po kursie z `fx_rates` (dict {currency: rate_pln_per_unit}).
    Jesli `fx_rates` jest None, funkcja probuje pobrac kurs EUR z NBP (z cache
    24h, zobacz `Komponenty/_shared/fx_rates.py`).
    """
    if markets is None:
        markets = load_markets()

    if fx_rates is None:
        fx_rates = _auto_fetch_fx_for_markets(markets)

    out: list[dict[str, Any]] = []
    for m in markets:
        cur = (m.currency or "PLN").upper()
        rate = fx_rates.get(cur)
        price = compute_market_price(
            base_price,
            0.0 if m.is_base else m.markup_percent,
            currency=cur, fx_rate=rate,
        )
        out.append({
            "code": m.code,
            "name_pl": m.name_pl,
            "currency": m.currency,
            "markup_percent": 0.0 if m.is_base else m.markup_percent,
            "price": price,
            "is_base": m.is_base,
            "fx_rate": rate,
        })
    return out


def _auto_fetch_fx_for_markets(markets: list[Market]) -> dict[str, float]:
    """Pobiera (z cache lub z NBP) kursy dla wszystkich niepolskich walut."""
    needed = sorted({(m.currency or "").upper() for m in markets if (m.currency or "").upper() not in ("", "PLN")})
    out: dict[str, float] = {}
    if not needed:
        return out
    try:
        from Komponenty._shared import fx_rates as fx
    except ImportError:
        return out
    for cur in needed:
        try:
            rate, _info = fx.get_rate(cur)
            out[cur] = rate
        except fx.FxError:
            continue
    return out


def format_price(value: float, currency: str) -> str:
    """Format ceny dla wyswietlenia w GUI (3 znakowy kod waluty na koncu)."""
    return f"{value:,.2f} {currency}".replace(",", " ")


# ---------------------------------------------------------------------------
# Helpery pod GUI: lista zmian (delta) do wyswietlenia w tabelce wynikow
# ---------------------------------------------------------------------------

def diff_markup(old_percent: float, new_percent: float) -> str:
    delta = float(new_percent) - float(old_percent)
    if abs(delta) < 0.01:
        return "= 0%"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.1f} pkt%"


# ---------------------------------------------------------------------------
# Shopify integration
# ---------------------------------------------------------------------------

# Mapping: lokalny code rynku -> kraje (ISO 3166-1 alpha-2) ktore powinien obejmowac
_MARKET_COUNTRY_MAP: dict[str, set[str]] = {
    "pl": {"PL"},
    "de": {"DE"},
    "fr": {"FR"},
    "es": {"ES"},
    "it": {"IT"},
    "nl": {"NL"},
    # EU = wszystkie panstwa UE (bez tych ktore maja juz swoj market)
    "eu": {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "GR",
        "HU", "IE", "LV", "LT", "LU", "MT", "PT", "RO", "SK", "SI",
        "SE",
    },
}

# Aliasy nazw / handle uzywane przez Shopify dla danego kraju (lowercased)
_MARKET_NAME_ALIASES: dict[str, set[str]] = {
    "pl": {"pl", "poland", "polska"},
    "de": {"de", "deu", "germany", "deutschland", "niemcy"},
    "fr": {"fr", "fra", "france", "francja"},
    "es": {"es", "esp", "spain", "espana", "españa", "hiszpania"},
    "it": {"it", "ita", "italy", "italia", "wlochy", "włochy"},
    "nl": {"nl", "nld", "netherlands", "nederland", "holandia", "holland"},
    "eu": {"eu", "european union", "europa", "europe", "rest of world",
           "rest of europe", "international", "europejski"},
}


def _select_price_list(catalogs: list[dict], expected_currency: str) -> dict:
    """Z listy katalogow zwraca pelny obiekt priceListu (id + parent.adjustment) z wlasciwa waluta."""
    cur_norm = (expected_currency or "").upper()
    fallback: dict = {}
    for c in catalogs or []:
        pl = (c or {}).get("priceList") or {}
        pid = pl.get("id") or ""
        if not pid:
            continue
        if (pl.get("currency") or "").upper() == cur_norm:
            return pl
        if not fallback:
            fallback = pl
    return fallback


def _markup_from_price_list(pl: dict) -> float | None:
    """Wyciaga aktualny markup % z pola parent.adjustment cennika Shopify.

    PERCENTAGE_INCREASE -> +X, PERCENTAGE_DECREASE -> -X. Inne typy (np. FIXED) -> None.
    """
    adj = ((pl or {}).get("parent") or {}).get("adjustment") or {}
    typ = (adj.get("type") or "").upper()
    val = adj.get("value")
    if val is None:
        return None
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    if typ == "PERCENTAGE_INCREASE":
        return v
    if typ == "PERCENTAGE_DECREASE":
        return -v
    return None


def discover_shopify_market_ids(
    logger=None, *, pull_markup: bool = True,
) -> list[Market]:
    """Pobiera liste rynkow z Shopify i mapuje je do lokalnych `Market`-ow.

    Algorytm dopasowania (priorytet od najmocniejszego do najslabszego):
      1. Country code w `regions` zdalnego marketu == jakiekolwiek z map
         `_MARKET_COUNTRY_MAP` dla lokalnego marketu (najlepsze dopasowanie).
      2. Handle / nazwa zdalnego marketu pasuje do `_MARKET_NAME_ALIASES`.
      3. Single-candidate na waluce (gdy zostal tylko jeden niedopasowany).

    Zapisuje `shopify_market_gid` i `shopify_price_list_gid` do markets_config.json.

    Gdy `pull_markup=True` (domyslnie) - rowniez sciaga aktualny `markup_percent`
    z `parent.adjustment` cennika Shopify (PERCENTAGE_INCREASE/DECREASE) i nadpisuje
    lokalna wartosc. Pozwala na rozwiazanie 'zmienilem markup w panelu Shopify -
    chce zsynchronizowac z aplikacja'.

    Wymaga scope: `read_markets` (do listowania) + `write_markets` (do pushu pozniej).
    Zwraca zaktualizowane Market-y.
    """
    from . import shopify_client as sc  # lazy import (zeby moduł sam w sobie nie wymagal sesji)
    shop, token = sc.load_session()
    remote = sc.list_markets(shop, token)
    local = load_markets()

    if logger:
        logger(f"[markets] Pobrano {len(remote)} rynkow z Shopify:")
        for r in remote:
            cats = r.get("catalogs") or []
            cat_info = []
            for c in cats:
                pl = (c or {}).get("priceList") or {}
                cat_info.append(f"PL[{pl.get('currency','?')}]={pl.get('id','-')}")
            logger(
                f"   - {r.get('name','?')} (handle={r.get('handle','-')}, "
                f"currency={r.get('currency','-')}, "
                f"countries={','.join(r.get('country_codes') or []) or '-'}, "
                f"primary={r.get('primary')}, gid={r.get('id')}, "
                f"catalogs={'; '.join(cat_info) or '-'})"
            )

    used_remote_ids: set[str] = set()
    matched: list[Market] = []

    def _try_match(m: Market) -> dict | None:
        code = m.code.lower()
        wanted_countries = _MARKET_COUNTRY_MAP.get(code, set())
        wanted_aliases = _MARKET_NAME_ALIASES.get(code, set())
        cur = (m.currency or "").upper()

        # 1) wg krajow
        if wanted_countries:
            best: tuple[int, dict] | None = None
            for r in remote:
                rid = r.get("id") or ""
                if rid in used_remote_ids:
                    continue
                ccs = set(r.get("country_codes") or [])
                overlap = ccs & wanted_countries
                if overlap:
                    score = len(overlap)
                    if best is None or score > best[0]:
                        best = (score, r)
            if best is not None:
                return best[1]

        # 2) wg handle/nazwy
        for r in remote:
            rid = r.get("id") or ""
            if rid in used_remote_ids:
                continue
            h = (r.get("handle") or "").lower()
            n = (r.get("name") or "").lower()
            if h in wanted_aliases or n in wanted_aliases:
                return r
            if any(a and (a in h or a in n) for a in wanted_aliases if len(a) >= 3):
                return r

        # 3) single-candidate na walucie wsrod tych jeszcze niezuzytych
        cands = [
            r for r in remote
            if (r.get("currency") or "").upper() == cur
            and (r.get("id") or "") not in used_remote_ids
        ]
        if len(cands) == 1:
            return cands[0]
        return None

    # Najpierw konkretne (de/fr/es/it/nl/pl), potem dopiero EU (zeby EU
    # nie zgarnal np. niemieckich krajow przed dopasowaniem 'de').
    order_score = {"pl": 0, "de": 1, "fr": 1, "es": 1, "it": 1, "nl": 1, "eu": 9}
    sorted_local = sorted(local, key=lambda x: order_score.get(x.code.lower(), 5))

    found: dict[str, dict] = {}
    for m in sorted_local:
        chosen = _try_match(m)
        if chosen:
            rid = chosen.get("id") or ""
            used_remote_ids.add(rid)
            found[m.code] = chosen

    # Zapisz w pierwotnej kolejnosci, zachowaj dane catalog/price_list
    for m in local:
        chosen = found.get(m.code)
        if chosen:
            m.shopify_market_gid = chosen.get("id") or ""
            pl = _select_price_list(chosen.get("catalogs") or [], m.currency)
            m.shopify_price_list_gid = pl.get("id") or ""

            markup_note = ""
            if pull_markup and not m.is_base:
                remote_markup = _markup_from_price_list(pl)
                if remote_markup is not None:
                    if abs(remote_markup - m.markup_percent) > 0.01:
                        markup_note = (
                            f" markup: {m.markup_percent:+.1f}% -> "
                            f"{remote_markup:+.1f}% (zaktualizowano z Shopify)"
                        )
                    else:
                        markup_note = f" markup: {remote_markup:+.1f}% (bez zmian)"
                    m.markup_percent = remote_markup
                elif pl:
                    markup_note = " markup: (typ adjustment != PERCENTAGE - pominieto)"

            if logger:
                logger(
                    f"[markets] {m.code}: OK -> '{chosen.get('name')}' "
                    f"(handle={chosen.get('handle','-')}, "
                    f"countries={','.join(chosen.get('country_codes') or []) or '-'}) "
                    f"market={m.shopify_market_gid} "
                    f"priceList={m.shopify_price_list_gid or '(brak)'}"
                    f"{markup_note}"
                )
        else:
            if not m.is_base:
                if logger:
                    logger(
                        f"[markets] {m.code}: NIE dopasowano w Shopify "
                        f"(currency={m.currency}, locale={m.locale}). "
                        f"Sprawdz logi powyzej i ew. dodaj market w Shopify, "
                        f"albo wpisz GID-y recznie do markets_config.json."
                    )
        matched.append(m)
    save_markets(matched)
    return matched


def push_markup_to_shopify(code: str, *, logger=None) -> dict[str, Any]:
    """Pushuje aktualny `markup_percent` rynku do jego cennika w Shopify.

    Wymaga: `shopify_price_list_gid` wypelnione w markets_config.json
    (lub uruchom `discover_shopify_market_ids()` zeby je wyciagnac).
    Wymaga scope: `write_markets` (lub `write_price_lists`).
    """
    from . import shopify_client as sc  # lazy import
    m = get_market(code)
    if m.is_base:
        return {"skipped": True, "reason": "Bazowy rynek - nic nie pushujemy."}
    if not m.shopify_price_list_gid:
        return {
            "skipped": True,
            "reason": (
                f"Rynek {m.code} nie ma 'shopify_price_list_gid'. "
                "Uruchom najpierw discover_shopify_market_ids() albo wpisz GID recznie."
            ),
        }
    shop, token = sc.load_session()
    out = sc.update_price_list_percentage_adjustment(
        shop, token,
        price_list_id=m.shopify_price_list_gid,
        percent=m.markup_percent,
    )
    if logger:
        logger(
            f"[markets] {m.code}: PUSH OK markup={m.markup_percent:+.1f}% "
            f"-> priceList={m.shopify_price_list_gid}"
        )
    return {"ok": True, "result": out}
