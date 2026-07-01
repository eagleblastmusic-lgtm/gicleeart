"""Logika obliczeń kalkulatora passe-partout (jednostki Allegro)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

RoundingMode = Literal["per_piece", "batch"]
StripeLayout = Literal["horizontal", "vertical"]

DEFAULTS = {
    "outer_width_cm": 30.0,
    "outer_height_cm": 40.0,
    "window_width_cm": 20.0,
    "window_height_cm": 28.7,
    "quantity": 1,
    "price_per_m2": 100.0,
    "unit_price": 2.5,
    "free_shipping_threshold": 49.9,
    "shipping_cost": 14.99,
    "rounding_mode": "per_piece",
    "stripe_layout": "horizontal",
}

SIZE_PRESETS: list[dict] = [
    {
        "id": "a4",
        "label": "A4",
        "outer_width_cm": 30.0,
        "outer_height_cm": 40.0,
        "window_width_cm": 20.0,
        "window_height_cm": 28.7,
    },
    {
        "id": "a3plus",
        "label": "A3+",
        "outer_width_cm": 47.0,
        "outer_height_cm": 62.0,
        "window_width_cm": 31.9,
        "window_height_cm": 47.3,
    },
]

def normalize_dimensions(width_cm: float, height_cm: float) -> tuple[float, float]:
    """Mniejszy wymiar = szerokość, większy = wysokość."""
    w = max(0.0, width_cm) if math.isfinite(width_cm) else 0.0
    h = max(0.0, height_cm) if math.isfinite(height_cm) else 0.0
    if w > h:
        return h, w
    return w, h


STRIPE_LABELS = {
    "horizontal": "PRĄŻKI POZIOME",
    "vertical": "PRĄŻKI PIONOWE",
}

ROUNDING_MODE_LABELS = {
    "per_piece": "Zaokrąglaj każdą sztukę osobno",
    "batch": "Zaokrąglaj całość zamówienia razem",
}


@dataclass(frozen=True)
class CalculationInput:
    outer_width_cm: float
    outer_height_cm: float
    window_width_cm: float
    window_height_cm: float
    quantity: int
    price_per_m2: float
    unit_price: float
    free_shipping_threshold: float
    shipping_cost: float
    rounding_mode: RoundingMode


@dataclass(frozen=True)
class SinglePieceMetrics:
    area_m2: float
    real_price: float
    units_raw: float
    units_rounded_per_piece: int
    price_rounded_per_piece: float
    loss_per_piece: float


@dataclass(frozen=True)
class OrderResult:
    units_total: int
    price_without_shipping: float
    shipping_cost_applied: float
    total_price: float
    price_per_piece: float
    rounding_loss: float
    free_shipping_reached: bool


@dataclass(frozen=True)
class QuantityTableRow:
    quantity: int
    units_total: int
    price_without_shipping: float
    shipping_cost_applied: float
    total_price: float
    price_per_piece: float
    rounding_loss: float
    free_shipping_reached: bool


@dataclass(frozen=True)
class QuantityTableInsights:
    cheapest_per_piece_quantity: int | None
    first_free_shipping_quantity: int | None
    most_profitable_quantity: int | None


@dataclass(frozen=True)
class ModeComparison:
    per_piece: OrderResult
    batch: OrderResult
    cheaper_mode: RoundingMode
    price_difference: float
    units_difference: int


@dataclass(frozen=True)
class ValidationState:
    window_too_large: bool
    unit_price_invalid: bool
    quantity_invalid: bool
    has_negative_values: bool


def _safe_positive(value: float, fallback: float = 0.0) -> float:
    if not math.isfinite(value):
        return fallback
    return max(0.0, value)


def _safe_quantity(value: float) -> int:
    if not math.isfinite(value) or value < 1:
        return 1
    return int(value)


def _safe_unit_price(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        return 0.0
    return value


def calculate_area_m2(outer_width_cm: float, outer_height_cm: float) -> float:
    w = _safe_positive(outer_width_cm)
    h = _safe_positive(outer_height_cm)
    return (w / 100.0) * (h / 100.0)


def calculate_real_price_per_piece(area_m2: float, price_per_m2: float) -> float:
    return area_m2 * _safe_positive(price_per_m2)


def calculate_units_raw_per_piece(real_price: float, unit_price: float) -> float:
    unit = _safe_unit_price(unit_price)
    if unit == 0:
        return 0.0
    return real_price / unit


def calculate_single_piece_metrics(inp: CalculationInput) -> SinglePieceMetrics:
    area_m2 = calculate_area_m2(inp.outer_width_cm, inp.outer_height_cm)
    real_price = calculate_real_price_per_piece(area_m2, inp.price_per_m2)
    units_raw = calculate_units_raw_per_piece(real_price, inp.unit_price)
    units_rounded_per_piece = math.ceil(units_raw)
    unit_price = _safe_unit_price(inp.unit_price)
    price_rounded_per_piece = units_rounded_per_piece * unit_price
    loss_per_piece = price_rounded_per_piece - real_price
    return SinglePieceMetrics(
        area_m2=area_m2,
        real_price=real_price,
        units_raw=units_raw,
        units_rounded_per_piece=units_rounded_per_piece,
        price_rounded_per_piece=price_rounded_per_piece,
        loss_per_piece=loss_per_piece,
    )


def calculate_total_units(
    units_raw_per_piece: float,
    quantity: int,
    rounding_mode: RoundingMode,
) -> int:
    qty = _safe_quantity(float(quantity))
    if rounding_mode == "per_piece":
        return math.ceil(units_raw_per_piece) * qty
    return math.ceil(units_raw_per_piece * qty)


def _calculate_shipping(
    price_without_shipping: float,
    free_shipping_threshold: float,
    shipping_cost: float,
) -> tuple[float, bool]:
    threshold = _safe_positive(free_shipping_threshold)
    reached = price_without_shipping >= threshold
    applied = 0.0 if reached else _safe_positive(shipping_cost)
    return applied, reached


def calculate_order_result(inp: CalculationInput) -> OrderResult:
    metrics = calculate_single_piece_metrics(inp)
    quantity = _safe_quantity(float(inp.quantity))
    unit_price = _safe_unit_price(inp.unit_price)

    units_total = calculate_total_units(metrics.units_raw, quantity, inp.rounding_mode)
    price_without_shipping = units_total * unit_price
    real_total = metrics.real_price * quantity
    rounding_loss = price_without_shipping - real_total

    shipping_cost_applied, free_shipping_reached = _calculate_shipping(
        price_without_shipping,
        inp.free_shipping_threshold,
        inp.shipping_cost,
    )
    total_price = price_without_shipping + shipping_cost_applied

    return OrderResult(
        units_total=units_total,
        price_without_shipping=price_without_shipping,
        shipping_cost_applied=shipping_cost_applied,
        total_price=total_price,
        price_per_piece=total_price / quantity,
        rounding_loss=rounding_loss,
        free_shipping_reached=free_shipping_reached,
    )


def calculate_quantity_table(inp: CalculationInput, max_quantity: int = 30) -> list[QuantityTableRow]:
    rows: list[QuantityTableRow] = []
    for q in range(1, max_quantity + 1):
        result = calculate_order_result(
            CalculationInput(
                outer_width_cm=inp.outer_width_cm,
                outer_height_cm=inp.outer_height_cm,
                window_width_cm=inp.window_width_cm,
                window_height_cm=inp.window_height_cm,
                quantity=q,
                price_per_m2=inp.price_per_m2,
                unit_price=inp.unit_price,
                free_shipping_threshold=inp.free_shipping_threshold,
                shipping_cost=inp.shipping_cost,
                rounding_mode=inp.rounding_mode,
            )
        )
        rows.append(
            QuantityTableRow(
                quantity=q,
                units_total=result.units_total,
                price_without_shipping=result.price_without_shipping,
                shipping_cost_applied=result.shipping_cost_applied,
                total_price=result.total_price,
                price_per_piece=result.price_per_piece,
                rounding_loss=result.rounding_loss,
                free_shipping_reached=result.free_shipping_reached,
            )
        )
    return rows


def analyze_quantity_table(rows: list[QuantityTableRow]) -> QuantityTableInsights:
    if not rows:
        return QuantityTableInsights(None, None, None)

    cheapest_q = rows[0].quantity
    lowest_ppp = rows[0].price_per_piece
    best_q = rows[0].quantity
    lowest_total = rows[0].total_price
    first_free: int | None = None

    for row in rows:
        if row.price_per_piece < lowest_ppp:
            lowest_ppp = row.price_per_piece
            cheapest_q = row.quantity
        if row.total_price < lowest_total:
            lowest_total = row.total_price
            best_q = row.quantity
        if first_free is None and row.free_shipping_reached:
            first_free = row.quantity

    return QuantityTableInsights(cheapest_q, first_free, best_q)


def compare_rounding_modes(inp: CalculationInput) -> ModeComparison:
    per_piece = calculate_order_result(
        CalculationInput(**{**inp.__dict__, "rounding_mode": "per_piece"})
    )
    batch = calculate_order_result(
        CalculationInput(**{**inp.__dict__, "rounding_mode": "batch"})
    )
    if per_piece.total_price < batch.total_price:
        cheaper: RoundingMode = "per_piece"
    elif batch.total_price < per_piece.total_price:
        cheaper = "batch"
    else:
        cheaper = inp.rounding_mode

    return ModeComparison(
        per_piece=per_piece,
        batch=batch,
        cheaper_mode=cheaper,
        price_difference=abs(per_piece.total_price - batch.total_price),
        units_difference=abs(per_piece.units_total - batch.units_total),
    )


def validate_input(inp: CalculationInput) -> ValidationState:
    values = (
        inp.outer_width_cm,
        inp.outer_height_cm,
        inp.window_width_cm,
        inp.window_height_cm,
        inp.price_per_m2,
        inp.unit_price,
        inp.free_shipping_threshold,
        inp.shipping_cost,
    )
    has_negative = any(math.isfinite(v) and v < 0 for v in values)
    window_too_large = (
        _safe_positive(inp.window_width_cm) > _safe_positive(inp.outer_width_cm)
        or _safe_positive(inp.window_height_cm) > _safe_positive(inp.outer_height_cm)
    )
    return ValidationState(
        window_too_large=window_too_large,
        unit_price_invalid=not math.isfinite(inp.unit_price) or inp.unit_price <= 0,
        quantity_invalid=not math.isfinite(float(inp.quantity)) or inp.quantity < 1,
        has_negative_values=has_negative,
    )


def _format_cm(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    rounded = round(value, 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.1f}".replace(".", ",")


@dataclass(frozen=True)
class CombinedOrderResult:
    total_units: int
    total_pieces: int
    price_without_shipping: float
    shipping_cost_applied: float
    total_price: float
    rounding_loss: float
    free_shipping_reached: bool


@dataclass(frozen=True)
class SavedLineItem:
    input: CalculationInput
    stripe_layout: StripeLayout


def _pricing_group_key(inp: CalculationInput) -> tuple:
    """Klucz grupy — ten sam format i cennik łączymy przy zaokrąglaniu „całość”."""
    ow, oh = normalize_dimensions(inp.outer_width_cm, inp.outer_height_cm)
    return (
        round(ow, 4),
        round(oh, 4),
        round(inp.price_per_m2, 6),
        round(inp.unit_price, 6),
        inp.rounding_mode,
    )


def _aggregate_pricing_group(
    inputs: list[CalculationInput],
) -> tuple[int, float, float]:
    """Zwraca (units_total, price_without_shipping, rounding_loss) dla grupy pozycji."""
    if not inputs:
        return 0, 0.0, 0.0

    rep = inputs[0]
    metrics = calculate_single_piece_metrics(rep)
    unit_price = _safe_unit_price(rep.unit_price)
    total_qty = sum(_safe_quantity(float(inp.quantity)) for inp in inputs)

    units_total = calculate_total_units(metrics.units_raw, total_qty, rep.rounding_mode)
    price_without_shipping = units_total * unit_price
    real_total = metrics.real_price * total_qty
    rounding_loss = price_without_shipping - real_total
    return units_total, price_without_shipping, rounding_loss


def combine_saved_lines(
    items: list[SavedLineItem],
    *,
    free_shipping_threshold: float,
    shipping_cost: float,
) -> CombinedOrderResult | None:
    if not items:
        return None

    total_units = 0
    total_pieces = 0
    price_without_shipping = 0.0
    rounding_loss = 0.0

    groups: dict[tuple, list[CalculationInput]] = {}
    for item in items:
        key = _pricing_group_key(item.input)
        groups.setdefault(key, []).append(item.input)

    for group_inputs in groups.values():
        units, subtotal, loss = _aggregate_pricing_group(group_inputs)
        total_units += units
        price_without_shipping += subtotal
        rounding_loss += loss
        total_pieces += sum(_safe_quantity(float(inp.quantity)) for inp in group_inputs)

    shipping_cost_applied, free_shipping_reached = _calculate_shipping(
        price_without_shipping,
        free_shipping_threshold,
        shipping_cost,
    )
    total_price = price_without_shipping + shipping_cost_applied

    return CombinedOrderResult(
        total_units=total_units,
        total_pieces=total_pieces,
        price_without_shipping=price_without_shipping,
        shipping_cost_applied=shipping_cost_applied,
        total_price=total_price,
        rounding_loss=rounding_loss,
        free_shipping_reached=free_shipping_reached,
    )


def _line_description(item: SavedLineItem) -> str:
    inp = item.input
    outer = f"{_format_cm(inp.outer_width_cm)} × {_format_cm(inp.outer_height_cm)}"
    if inp.window_width_cm > 0 and inp.window_height_cm > 0:
        window = f"{_format_cm(inp.window_width_cm)} × {_format_cm(inp.window_height_cm)}"
    else:
        window = "—"
    units = calculate_order_result(inp).units_total
    stripe = STRIPE_LABELS[item.stripe_layout]
    return (
        f"{inp.quantity} szt. — wymiar zewnętrzny {outer} cm, okienko {window} cm, "
        f"{stripe} ({units} jednostek)"
    )


def build_multi_seller_message(
    items: list[SavedLineItem],
    combined: CombinedOrderResult,
) -> str:
    lines = ["Dzień dobry, proszę o wykonanie passe-partout według poniższej listy:", ""]
    for idx, item in enumerate(items, start=1):
        lines.append(f"{idx}) {_line_description(item)}")
    lines.extend(
        [
            "",
            f"Zgodnie z obliczeniem zamawiam łącznie {combined.total_units} jednostek z aukcji.",
            "Proszę o ostrożność przy wewnętrznych krawędziach.",
        ]
    )
    return "\n".join(lines)


def format_saved_line_label(item: SavedLineItem) -> str:
    inp = item.input
    outer = f"{_format_cm(inp.outer_width_cm)}×{_format_cm(inp.outer_height_cm)}"
    if inp.window_width_cm > 0 and inp.window_height_cm > 0:
        window = f"{_format_cm(inp.window_width_cm)}×{_format_cm(inp.window_height_cm)}"
    else:
        window = "—"
    units = calculate_order_result(inp).units_total
    return outer, window, str(inp.quantity), str(units), STRIPE_LABELS[item.stripe_layout]


def build_seller_message(
    *,
    quantity: int,
    outer_width_cm: float,
    outer_height_cm: float,
    window_width_cm: float,
    window_height_cm: float,
    stripe_label: str,
    units_total: int,
) -> str:
    outer = f"{_format_cm(outer_width_cm)} × {_format_cm(outer_height_cm)}"
    if window_width_cm > 0 and window_height_cm > 0:
        window = f"{_format_cm(window_width_cm)} × {_format_cm(window_height_cm)}"
    else:
        window = "—"
    return (
        f"Dzień dobry, proszę o wykonanie {quantity} sztuk passe-partout o wymiarze zewnętrznym "
        f"{outer} cm, z okienkiem {window} cm. Układ prążków: {stripe_label}. "
        f"Zgodnie z obliczeniem zamawiam {units_total} jednostek z aukcji. "
        f"Proszę o ostrożność przy wewnętrznych krawędziach."
    )


def parse_number(raw: str) -> float:
    normalized = raw.strip().replace(" ", "").replace(",", ".")
    if not normalized:
        return 0.0
    try:
        value = float(normalized)
    except ValueError:
        return 0.0
    return value if math.isfinite(value) else 0.0


def fmt_money(value: float) -> str:
    if not math.isfinite(value):
        return "—"
    return f"{value:,.2f} zł".replace(",", "X").replace(".", ",").replace("X", " ")


def fmt_number(value: float, digits: int = 2) -> str:
    if not math.isfinite(value):
        return "—"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", " ")


def fmt_area(value: float) -> str:
    return f"{fmt_number(value, 4)} m²"
