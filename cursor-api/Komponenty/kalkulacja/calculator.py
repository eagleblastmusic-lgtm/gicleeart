"""Logika kalkulatora kosztów produkcji ramek (odwzorowanie arkusza CENNIK)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .store import (
    load_cost_lines,
    load_helpers,
    load_materials,
    load_price_table,
    load_sales_mix,
    load_settings,
    load_wood_defaults,
)

FORMATS = ("A4", "A3+", "A2")
WOODS = ("SOSNA", "DĄB")
WOOD_ORIGINS = ("stolarz24", "drewno dla majsterkowicza")
MAJSTERKOWICZ_OAK_WOOD_COSTS: dict[str, float] = {
    "A4": 12.0,
    "A3+": 24.0,
    "A2": 24.0,
}
FIXED_SALES_MIX_VARIANTS: tuple[tuple[str, str], ...] = tuple(
    (wood, fmt) for wood in WOODS for fmt in FORMATS
)
DEFAULT_MIX_UNITS: dict[str, int] = {
    "SOSNA_A4": 22,
    "SOSNA_A3+": 27,
    "SOSNA_A2": 11,
    "DĄB_A4": 13,
    "DĄB_A3+": 18,
    "DĄB_A2": 9,
}
SECTION_LABELS = {
    "production": "Produkcja ramy",
    "print": "Wydruk i papier",
    "packaging": "Opakowanie",
    "shipping": "Wysyłka",
}


def variant_key(wood: str, fmt: str) -> str:
    suffix = "sosna" if wood.upper().startswith("S") else "dab"
    return f"{fmt}_{suffix}"


def sell_key(wood: str, fmt: str) -> str:
    return f"{wood}_{fmt}"


def fmt_money(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f} zł".replace(",", " ").replace(".", ",")


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f} %"


def fmt_hourly(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{fmt_money(value)}/h"


def production_hours_from_minutes(minutes: float) -> float:
    return minutes / 60.0


def production_minutes_from_hours(hours: float) -> float:
    return hours * 60.0


def fmt_production_hours(minutes: float) -> str:
    hours = production_hours_from_minutes(minutes)
    text = f"{hours:.2f}".replace(".", ",")
    if text.endswith(",00"):
        return text[:-3]
    if text.endswith("0"):
        return text[:-1]
    return text


def resolve_production_minutes(
    wood: str,
    fmt: str,
    *,
    settings: dict[str, Any] | None = None,
    minutes: float | None = None,
) -> float:
    if minutes is not None and minutes > 0:
        return minutes
    settings = settings or load_settings()
    key = sell_key(wood, fmt)
    stored = (settings.get("variant_production_minutes") or {}).get(key)
    if stored is not None:
        return float(stored)
    return float(settings.get("default_production_minutes") or 45)


def hourly_profit(profit: float, production_minutes: float) -> float | None:
    if production_minutes <= 0:
        return None
    return profit * 60.0 / production_minutes


@dataclass(frozen=True)
class CostLineResult:
    name: str
    section: str
    cost: float


@dataclass(frozen=True)
class VariantResult:
    wood: str
    format: str
    profile: str
    lines: list[CostLineResult]
    production_total: float
    print_total: float
    packaging_total: float
    shipping_total: float
    total_cost: float
    full_cost: float
    sell_price: float
    profit: float
    profit_full: float
    margin: float


@dataclass(frozen=True)
class WoodBatchRow:
    batch: int
    meters: float
    wood_cost: float
    shipping: float
    shipping_per_piece: float
    marginal_gain: float | None
    gain_ratio: float | None
    cost_per_frame: float


@dataclass(frozen=True)
class WoodOptimization:
    species: str
    fmt: str
    profile: str
    price_per_meter: float
    pieces_per_frame: float
    shipping: float
    max_gain_ratio: float
    optimal_batch: int
    optimal_cost_per_frame: float
    rows: list[WoodBatchRow]


def margin(cost: float, price: float) -> float:
    if price <= 0:
        return 0.0
    return (price - cost) / price


def margin_pct_from_price(cost: float, price: float) -> float:
    return margin(cost, price) * 100.0


def markup_pct_from_price(cost: float, price: float) -> float:
    """Narzut % = (cena - koszt) / koszt × 100."""
    if cost <= 0:
        return 0.0
    return ((price / cost) - 1.0) * 100.0


def price_from_markup(cost: float, markup_pct: float) -> float:
    return cost * (1.0 + markup_pct / 100.0)


def price_from_margin_pct(cost: float, margin_pct: float) -> float:
    if margin_pct >= 100.0:
        return cost
    return cost / (1.0 - margin_pct / 100.0)


def pricing_snapshot(cost: float, price: float) -> dict[str, float]:
    return {
        "sell_price": round(price, 2),
        "markup_pct": round(markup_pct_from_price(cost, price), 2),
        "margin_pct": round(margin_pct_from_price(cost, price), 2),
    }


def resolve_sell_price(
    total_cost: float,
    *,
    settings: dict[str, Any] | None = None,
    wood: str,
    fmt: str,
    sell_price: float | None = None,
    markup_pct: float | None = None,
    margin_pct: float | None = None,
    driver: str | None = None,
) -> tuple[float, dict[str, float]]:
    """Ustal cenę sprzedaży z pól UI lub zapisu lokalnego (bez Excela)."""
    settings = settings or load_settings()
    key = sell_key(wood, fmt)
    stored = dict((settings.get("variant_pricing") or {}).get(key) or {})
    default_markup = float(settings.get("default_markup_pct") or 250.0)

    if sell_price is not None and driver == "price":
        price = sell_price
    elif markup_pct is not None and driver == "markup":
        price = price_from_markup(total_cost, markup_pct)
    elif margin_pct is not None and driver == "margin":
        price = price_from_margin_pct(total_cost, margin_pct)
    elif stored:
        mode = str(stored.get("driver") or "markup")
        if mode == "price" and stored.get("sell_price") is not None:
            price = float(stored["sell_price"])
        elif mode == "margin" and stored.get("margin_pct") is not None:
            price = price_from_margin_pct(total_cost, float(stored["margin_pct"]))
        elif stored.get("markup_pct") is not None:
            price = price_from_markup(total_cost, float(stored["markup_pct"]))
        elif stored.get("sell_price") is not None:
            price = float(stored["sell_price"])
        else:
            price = price_from_markup(total_cost, default_markup)
    else:
        price = price_from_markup(total_cost, default_markup)

    snap = pricing_snapshot(total_cost, price)
    return price, snap


def material_price_by_id(material_id: str, materials: list[dict[str, Any]] | None = None) -> float | None:
    rows = materials if materials is not None else load_materials()
    for row in rows:
        if row.get("id") == material_id:
            return float(row.get("price") or 0)
    return None


def material_price_by_product(product: str, materials: list[dict[str, Any]] | None = None) -> float | None:
    rows = materials if materials is not None else load_materials()
    product_u = product.strip().upper()
    for row in rows:
        if str(row.get("product") or "").strip().upper() == product_u:
            return float(row.get("price") or 0)
    return None


def lookup_price_table(
    *,
    id_tr: str | None = None,
    id_full: str | None = None,
    table: list[dict[str, Any]] | None = None,
) -> float | None:
    rows = table if table is not None else load_price_table()
    for row in rows:
        if id_tr and row.get("id_tr") == id_tr:
            return float(row["cost"])
        if id_full and row.get("id_full") == id_full:
            return float(row["cost"])
    return None


def optimize_wood_batch(
    *,
    pieces_per_frame: float,
    price_per_meter: float,
    shipping: float,
    max_batch: int = 30,
    max_gain_ratio: float = 0.2,
) -> WoodOptimization:
    """Koszt drewna na sztukę — pierwsza partia, gdzie H < max_gain_ratio (Excel H7=0.2)."""
    rows: list[WoodBatchRow] = []
    prev_cost: float | None = None
    prev_ship_pp: float | None = None
    optimal_batch = 1
    optimal_cost = float("inf")

    for batch in range(1, max_batch + 1):
        meters = batch * pieces_per_frame
        wood_cost = meters * price_per_meter
        cost_per_frame = round((wood_cost + shipping) / batch, 2)
        ship_pp = shipping / batch
        marginal: float | None = None
        ratio: float | None = None
        if prev_cost is not None and prev_ship_pp:
            marginal = prev_cost - cost_per_frame
            ratio = marginal / prev_ship_pp
            if ratio < max_gain_ratio and optimal_cost == float("inf"):
                optimal_batch = batch
                optimal_cost = cost_per_frame
        rows.append(
            WoodBatchRow(
                batch=batch,
                meters=meters,
                wood_cost=wood_cost,
                shipping=shipping,
                shipping_per_piece=ship_pp,
                marginal_gain=marginal,
                gain_ratio=ratio,
                cost_per_frame=cost_per_frame,
            )
        )
        prev_cost = cost_per_frame
        prev_ship_pp = ship_pp

    if optimal_cost == float("inf") and rows:
        optimal_batch = rows[-1].batch
        optimal_cost = rows[-1].cost_per_frame

    defaults = load_wood_defaults()
    return WoodOptimization(
        species=str(defaults.get("species") or "SOSNA"),
        fmt=str(defaults.get("format") or "A4"),
        profile=str(defaults.get("profile") or "20X20"),
        price_per_meter=price_per_meter,
        pieces_per_frame=pieces_per_frame,
        shipping=shipping,
        max_gain_ratio=max_gain_ratio,
        optimal_batch=optimal_batch,
        optimal_cost_per_frame=optimal_cost,
        rows=rows,
    )


def wood_cost_for_variant(
    wood: str,
    fmt: str,
    *,
    profile: str = "20X20",
    materials: list[dict[str, Any]] | None = None,
    helpers: dict[str, dict[str, float | None]] | None = None,
    shipping: float = 25,
    max_batch: int = 30,
) -> WoodOptimization:
    """Przelicza koszt drewna dla gatunku i formatu."""
    helpers = helpers or load_helpers()
    pieces = float((helpers.get("POTRZEBNE DREWNO") or {}).get(fmt) or 0)
    mat_id = f"{wood}{profile}"
    price = material_price_by_id(mat_id, materials)
    if price is None:
        price = material_price_by_product(wood, materials) or 0.0
    defaults = load_wood_defaults()
    max_ratio = float(defaults.get("max_gain_ratio") or 0.2)
    opt = optimize_wood_batch(
        pieces_per_frame=pieces,
        price_per_meter=price,
        shipping=shipping,
        max_batch=max_batch,
        max_gain_ratio=max_ratio,
    )
    return WoodOptimization(
        species=wood,
        fmt=fmt,
        profile=profile,
        price_per_meter=price,
        pieces_per_frame=pieces,
        shipping=shipping,
        max_gain_ratio=max_ratio,
        optimal_batch=opt.optimal_batch,
        optimal_cost_per_frame=opt.optimal_cost_per_frame,
        rows=opt.rows,
    )


def _section_total(lines: list[CostLineResult], section: str) -> float:
    return sum(ln.cost for ln in lines if ln.section == section)


def resolve_drewno_cost(
    wood: str,
    fmt: str,
    base_cost: float,
    *,
    settings: dict[str, Any] | None = None,
) -> float:
    """Nadpisuje koszt drewna dla Dębu przy pochodzeniu „drewno dla majsterkowicza”."""
    settings = settings or load_settings()
    origin = str(settings.get("wood_origin") or "stolarz24")
    if origin != "drewno dla majsterkowicza":
        return base_cost
    if not str(wood or "").upper().startswith("D"):
        return base_cost
    return float(MAJSTERKOWICZ_OAK_WOOD_COSTS.get(fmt, base_cost))


def compute_variant(
    wood: str,
    fmt: str,
    *,
    cost_lines: list[dict[str, Any]] | None = None,
    settings: dict[str, Any] | None = None,
    sell_price: float | None = None,
    markup_pct: float | None = None,
    margin_pct: float | None = None,
    pricing_driver: str | None = None,
) -> VariantResult:
    cost_lines = cost_lines or load_cost_lines()
    settings = settings or load_settings()
    key = variant_key(wood, fmt)
    profile = str(settings.get("profile") or "20X20")

    lines: list[CostLineResult] = []
    for row in cost_lines:
        costs = row.get("costs") or {}
        if key not in costs:
            continue
        cost = float(costs[key])
        name = str(row.get("name") or "")
        if name == "Drewno":
            cost = resolve_drewno_cost(wood, fmt, cost, settings=settings)
        lines.append(
            CostLineResult(
                name=name,
                section=str(row.get("section") or "production"),
                cost=cost,
            )
        )

    production = _section_total(lines, "production")
    print_t = _section_total(lines, "print")
    packaging = _section_total(lines, "packaging")
    shipping = _section_total(lines, "shipping")
    total = production + print_t + packaging
    full = total + shipping

    price, _snap = resolve_sell_price(
        total,
        settings=settings,
        wood=wood,
        fmt=fmt,
        sell_price=sell_price,
        markup_pct=markup_pct,
        margin_pct=margin_pct,
        driver=pricing_driver,
    )
    profit = price - total
    profit_full = price - full

    return VariantResult(
        wood=wood,
        format=fmt,
        profile=profile,
        lines=lines,
        production_total=production,
        print_total=print_t,
        packaging_total=packaging,
        shipping_total=shipping,
        total_cost=total,
        full_cost=full,
        sell_price=price,
        profit=profit,
        profit_full=profit_full,
        margin=margin(total, price),
    )


_SHOP_SIZE_TO_FORMAT: dict[str, str] = {"m": "A4", "s": "A4", "l": "A3+", "xl": "A2"}


def _normalize_shop_wood_label(label: str) -> str | None:
    s = (label or "").strip().lower().replace("ą", "a").replace("ę", "e")
    if s.startswith("sos"):
        return "SOSNA"
    if s.startswith("dab") or s.startswith("deb"):
        return "DĄB"
    return None


def calc_sell_price_for_shop_labels(
    wood_label: str,
    size_label: str,
    *,
    settings: dict[str, Any] | None = None,
) -> float | None:
    """Cena sprzedaży z kalkulatora kosztów dla etykiet ze sklepu (np. Dąb + L)."""
    wood = _normalize_shop_wood_label(wood_label)
    fmt = _SHOP_SIZE_TO_FORMAT.get((size_label or "").strip().lower())
    if not wood or not fmt:
        return None
    return compute_variant(wood, fmt, settings=settings).sell_price


def weighted_sales_averages(mix: list[dict[str, Any]] | None = None) -> dict[str, float]:
    """Średni przychód/koszt/dochód ważony mixem sprzedaży."""
    mix = resolved_sales_mix(mix)
    total_w = sum(float(r.get("weight") or 0) for r in mix)
    if total_w <= 0:
        return {"avg_revenue": 0.0, "avg_cost": 0.0, "avg_profit": 0.0}

    rev = sum(float(r.get("sell_price") or 0) * float(r.get("weight") or 0) for r in mix) / total_w
    cost = sum(float(r.get("full_cost") or r.get("total_cost") or 0) * float(r.get("weight") or 0) for r in mix) / total_w
    profit = sum(float(r.get("profit") or 0) * float(r.get("weight") or 0) for r in mix) / total_w
    return {"avg_revenue": rev, "avg_cost": cost, "avg_profit": profit}


def fmt_work_hours(hours: float | None) -> str:
    if hours is None:
        return "—"
    text = f"{hours:.1f}".replace(".", ",")
    if text.endswith(",0"):
        return f"{text[:-2]} h"
    return f"{text} h"


def normalize_manual_frames_per_day(value: float | None) -> int:
    """Ręczny tryb: tylko całkowite ramek/dzień (min. 1)."""
    try:
        n = int(round(float(value or 1)))
    except (TypeError, ValueError):
        n = 1
    return max(1, n)


def fmt_work_days(days: float | None) -> str:
    if days is None:
        return "—"
    n = max(0, math.ceil(days - 1e-9))
    if n == 1:
        return "1 dzień"
    return f"{n} dni"


def mix_work_time_rows(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Czas pracy per wariant: godziny na szt. × liczba sztuk."""
    settings = settings or load_settings()
    mix = resolved_sales_mix(mix, settings=settings)
    out: list[dict[str, Any]] = []
    for row in mix:
        wood = str(row.get("wood") or "")
        fmt = str(row.get("format") or "")
        units = int(row.get("units") or 0)
        hours_per_unit = production_hours_from_minutes(
            resolve_production_minutes(wood, fmt, settings=settings)
        )
        out.append(
            {
                **row,
                "hours_per_unit": hours_per_unit,
                "total_hours": hours_per_unit * units,
            }
        )
    return out


def weighted_production_hours_per_frame(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> float:
    """Średni czas produkcji jednej ramki (h) ważony mixem — z Kalkulatora."""
    settings = settings or load_settings()
    rows = apply_mix_weights(normalize_sales_mix(load_sales_mix() if mix is None else mix))
    total_units = sum(int(row.get("units") or 0) for row in rows)
    if total_units <= 0:
        return production_hours_from_minutes(float(settings.get("default_production_minutes") or 45))

    total_hours = 0.0
    for row in rows:
        wood = str(row.get("wood") or "")
        fmt = str(row.get("format") or "")
        hours = production_hours_from_minutes(resolve_production_minutes(wood, fmt, settings=settings))
        total_hours += hours * int(row.get("units") or 0)
    return total_hours / total_units


def frames_per_day_from_calculator(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> float:
    """Ramek/dzień = godziny pracy dziennie ÷ średni czas ramki z Kalkulatora."""
    settings = settings or load_settings()
    work_day = float(settings.get("work_hours_per_day") or 8.0)
    avg_hours = weighted_production_hours_per_frame(mix, settings=settings)
    if avg_hours <= 0:
        return 0.0
    return work_day / avg_hours


def effective_frames_per_day(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
    frames_per_day: float | None = None,
    mode: str | None = None,
) -> float:
    settings = settings or load_settings()
    resolved_mode = str(mode or settings.get("frames_per_day_mode") or "manual")
    if resolved_mode == "calculator":
        return frames_per_day_from_calculator(mix, settings=settings)
    if frames_per_day is not None:
        return float(normalize_manual_frames_per_day(frames_per_day))
    return float(normalize_manual_frames_per_day(settings.get("frames_per_day")))


def work_days_from_sales(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
    frames_per_day: float | None = None,
    mode: str | None = None,
) -> float | None:
    """Dni pracy = suma szacowanej sprzedaży (ramek) ÷ ramek na dzień."""
    total = total_mix_units(mix)
    fpd = effective_frames_per_day(
        mix,
        settings=settings,
        frames_per_day=frames_per_day,
        mode=mode,
    )
    if total <= 0 or fpd <= 0:
        return None
    return total / fpd


def monthly_work_hours(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> float:
    return sum(float(row.get("total_hours") or 0) for row in mix_work_time_rows(mix, settings=settings))


def monthly_revenue_forecast(mix: list[dict[str, Any]] | None = None) -> float:
    """Przychód brutto miesięczny = suma (cena sprzedaży × liczba sztuk) z mixu."""
    mix = resolved_sales_mix(mix)
    return sum(float(row.get("sell_price") or 0) * int(row.get("units") or 0) for row in mix)


def daily_revenue_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> float:
    return monthly_revenue_forecast(mix) / work_days_per_month(settings)


def fmt_monthly_revenue_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> str:
    monthly = monthly_revenue_forecast(mix)
    return f"{fmt_money(monthly)} / {fmt_money(daily_revenue_forecast(mix, settings=settings))}"


def monthly_full_cost_forecast(mix: list[dict[str, Any]] | None = None) -> float:
    """Prognoza kosztu produkcji z wysyłką = suma (full_cost × liczba sztuk) z mixu."""
    mix = resolved_sales_mix(mix)
    return sum(float(row.get("full_cost") or 0) * int(row.get("units") or 0) for row in mix)


def daily_full_cost_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> float:
    return monthly_full_cost_forecast(mix) / work_days_per_month(settings)


def fmt_monthly_full_cost_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> str:
    monthly = monthly_full_cost_forecast(mix)
    return f"{fmt_money(monthly)} / {fmt_money(daily_full_cost_forecast(mix, settings=settings))}"


def monthly_profit_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    after_shipping: bool = False,
) -> float:
    """Prognoza zysku miesięcznego = suma (zysk na szt. × liczba sztuk) z mixu."""
    mix = resolved_sales_mix(mix)
    field = "profit_full" if after_shipping else "profit"
    return sum(float(row.get(field) or 0) * int(row.get("units") or 0) for row in mix)


def work_days_per_month(settings: dict[str, Any] | None = None) -> int:
    """Liczba dni roboczych w miesiącu (do prognozy zysku dziennego)."""
    settings = settings or load_settings()
    return max(1, int(round(float(settings.get("work_days_per_month") or 22))))


def daily_profit_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> float:
    return monthly_profit_forecast(mix) / work_days_per_month(settings)


def fmt_monthly_profit_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> str:
    monthly = monthly_profit_forecast(mix)
    return f"{fmt_money(monthly)} / {fmt_money(daily_profit_forecast(mix, settings=settings))}"


def frames_for_financial_goal(
    goal_profit: float,
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> dict[str, float | int | None]:
    """Szacuje liczbę ramek do osiągnięcia celu zysku (średni zysk ważony mixem)."""
    mix = resolved_sales_mix(mix, settings=settings)
    avg_profit = float(weighted_sales_averages(mix)["avg_profit"])
    goal = float(goal_profit)
    if goal <= 0 or avg_profit <= 0:
        return {
            "goal": goal,
            "avg_profit": avg_profit,
            "frames_needed": None,
            "projected_profit": 0.0,
        }
    frames_needed = int(math.ceil(goal / avg_profit))
    return {
        "goal": goal,
        "avg_profit": avg_profit,
        "frames_needed": frames_needed,
        "projected_profit": frames_needed * avg_profit,
    }


def parse_mix_units(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        n = int(value)
        return n if n >= 0 else None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    head = text.split()[0]
    try:
        n = int(float(head))
    except ValueError:
        return None
    return n if n >= 0 else None


def format_mix_units(units: int | float | None) -> str:
    if units is None:
        return "0 SZTUK"
    n = int(units)
    word = "SZTUKA" if n == 1 else "SZTUK"
    return f"{n} {word}"


def format_frame_count(units: int | float | None) -> str:
    if units is None:
        return "0 ramek"
    n = int(units)
    if n == 1:
        return "1 ramka"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return f"{n} ramki"
    return f"{n} ramek"


def total_mix_units(mix: list[dict[str, Any]] | None = None) -> int:
    rows = normalize_sales_mix(load_sales_mix() if mix is None else mix)
    return sum(int(row.get("units") or 0) for row in rows)


def mix_share_weights(rows: list[dict[str, Any]]) -> list[int]:
    """Stałe wagi udziału — z share_per_100, nie z bieżących sztuk."""
    return [int(row.get("share_per_100") or row.get("units") or 0) for row in rows]


def normalize_sales_mix(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Stała lista 6 wariantów + sztuki i zapisany udział (share_per_100)."""
    stored = {
        sell_key(str(row.get("wood") or ""), str(row.get("format") or "")): row
        for row in (rows or [])
    }
    out: list[dict[str, Any]] = []
    for wood, fmt in FIXED_SALES_MIX_VARIANTS:
        key = sell_key(wood, fmt)
        row = stored.get(key) or {}
        units = parse_mix_units(row.get("units"))
        if units is None:
            units = parse_mix_units(row.get("units_label"))
        if units is None:
            units = DEFAULT_MIX_UNITS.get(key, 0)
        share = parse_mix_units(row.get("share_per_100"))
        if share is None:
            share = units
        out.append({"wood": wood, "format": fmt, "units": units, "share_per_100": share})
    return out


def redistribute_mix_total(rows: list[dict[str, Any]], total: int) -> list[dict[str, Any]]:
    """Rozdziela `total` sztuk wg zapisanego udziału procentowego."""
    base = normalize_sales_mix(rows)
    weights = mix_share_weights(base)
    total = max(0, int(total))
    if sum(weights) <= 0:
        return [{**row, "units": 0} for row in base]
    new_units = allocate_total_by_share(base, total, weights=weights)
    return [
        {
            **row,
            "units": unit,
            "share_per_100": int(row.get("share_per_100") or weight),
        }
        for row, unit, weight in zip(base, new_units, weights, strict=True)
    ]


def apply_mix_shares(rows: list[dict[str, Any]] | None, shares: list[int]) -> list[dict[str, Any]]:
    """Zapisuje udział na 100 szt. i przelicza sztuki przy dotychczasowej sumie."""
    base = normalize_sales_mix(rows)
    current_total = sum(int(row.get("units") or 0) for row in base)
    if current_total <= 0:
        current_total = sum(shares) or 100
    staged = [
        {**row, "share_per_100": max(0, int(share))}
        for row, share in zip(base, shares, strict=True)
    ]
    return redistribute_mix_total(staged, current_total)


def allocate_units_by_share(
    rows: list[dict[str, Any]],
    extra: int,
    *,
    weights: list[int] | None = None,
) -> list[int]:
    """Rozdziela dodatkowe sztuki wg zapisanego udziału (domyślnie share_per_100)."""
    w = weights if weights is not None else mix_share_weights(rows)
    return _distribute_int_by_weights(w, extra)


def allocate_total_by_share(
    rows: list[dict[str, Any]],
    total: int,
    *,
    weights: list[int] | None = None,
) -> list[int]:
    """Rozdziela `total` sztuk wg wag udziału."""
    w = weights if weights is not None else mix_share_weights(rows)
    return _distribute_int_by_weights(w, total)


def _distribute_int_by_weights(weights: list[int], total: int) -> list[int]:
    n = len(weights)
    if total <= 0 or n == 0:
        return [0] * n
    weight_sum = sum(weights)
    if weight_sum <= 0:
        base, rem = divmod(total, n)
        return [base + (1 if i < rem else 0) for i in range(n)]

    raw = [w / weight_sum * total for w in weights]
    allocated = [int(v) for v in raw]
    remainder = total - sum(allocated)
    if remainder > 0:
        order = sorted(
            range(n),
            key=lambda i: (raw[i] - allocated[i], weights[i]),
            reverse=True,
        )
        for i in order[:remainder]:
            allocated[i] += 1
    return allocated


def allocate_removals_by_share(rows: list[dict[str, Any]], remove: int) -> list[int]:
    """Odejmuje `remove` sztuk wg udziału, bez schodzenia poniżej zera."""
    units = [int(row.get("units") or 0) for row in rows]
    n = len(units)
    remove = min(max(0, remove), sum(units))
    if remove <= 0 or n == 0:
        return [0] * n

    removals = [0] * n
    remaining = remove
    pool = units[:]
    while remaining > 0 and sum(pool) > 0:
        chunk = allocate_units_by_share([{"units": u} for u in pool], remaining)
        applied = 0
        for i in range(n):
            take = min(chunk[i], pool[i])
            removals[i] += take
            pool[i] -= take
            applied += take
        if applied <= 0:
            break
        remaining -= applied
    return removals


def apply_sales_change(rows: list[dict[str, Any]] | None, delta: int) -> list[dict[str, Any]]:
    """Zmienia łączną sprzedaż o `delta`, zachowując zapisany udział procentowy."""
    base = normalize_sales_mix(rows)
    current_total = sum(int(row.get("units") or 0) for row in base)
    new_total = max(0, current_total + delta)
    return redistribute_mix_total(base, new_total)


def apply_sales_growth(rows: list[dict[str, Any]] | None, extra: int) -> list[dict[str, Any]]:
    """Dodaje sztuki do mixu zgodnie z bieżącym podziałem procentowym."""
    return apply_sales_change(rows, extra)


def apply_mix_weights(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weights = mix_share_weights(rows)
    total_w = sum(weights)
    out: list[dict[str, Any]] = []
    for row, share in zip(rows, weights, strict=True):
        units = int(row.get("units") or 0)
        weight = (share / total_w) if total_w > 0 else 0.0
        out.append(
            {
                **row,
                "weight": weight,
                "units_label": format_mix_units(units),
            }
        )
    return out


def scale_units_to_total(units: list[int], target: int) -> list[int]:
    """Zachowuje proporcje i skaluje listę sztuk do sumy `target`."""
    return allocate_total_by_share([{"units": int(u)} for u in units], target)


def per_hundred_from_mix(rows: list[dict[str, Any]] | None = None) -> list[int]:
    """Zapisany udział na 100 szt. (share_per_100), przeskalowany do sumy 100 do podglądu."""
    base = normalize_sales_mix(rows)
    return scale_units_to_total(mix_share_weights(base), 100)


def sales_mix_for_store(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "wood": row["wood"],
            "format": row["format"],
            "units": int(row.get("units") or 0),
            "share_per_100": int(row.get("share_per_100") or row.get("units") or 0),
        }
        for row in normalize_sales_mix(rows)
    ]


def resolved_sales_mix(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Mix sprzedaży: stałe warianty, udział z liczby sztuk, ceny z kalkulatora."""
    mix = apply_mix_weights(normalize_sales_mix(load_sales_mix() if mix is None else mix))
    settings = settings or load_settings()
    out: list[dict[str, Any]] = []
    for row in mix:
        wood = str(row.get("wood") or "")
        fmt = str(row.get("format") or "")
        result = compute_variant(wood, fmt, settings=settings)
        out.append(
            {
                **row,
                "sell_price": result.sell_price,
                "total_cost": result.total_cost,
                "full_cost": result.full_cost,
                "shipping_total": result.shipping_total,
                "profit": result.profit,
                "profit_full": result.profit_full,
            }
        )
    return out


def all_variants_summary(
    *,
    cost_lines: list[dict[str, Any]] | None = None,
    settings: dict[str, Any] | None = None,
) -> list[VariantResult]:
    out: list[VariantResult] = []
    for wood in WOODS:
        for fmt in FORMATS:
            out.append(compute_variant(wood, fmt, cost_lines=cost_lines, settings=settings))
    return out


def update_wood_line_cost(
    wood: str,
    fmt: str,
    new_cost: float,
    *,
    cost_lines: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Aktualizuje wiersz „Drewno” po przeliczeniu optymalizacji."""
    rows = [dict(r) for r in (cost_lines or load_cost_lines())]
    key = variant_key(wood, fmt)
    for row in rows:
        if row.get("name") == "Drewno":
            costs = dict(row.get("costs") or {})
            costs[key] = new_cost
            row["costs"] = costs
            break
    return rows
