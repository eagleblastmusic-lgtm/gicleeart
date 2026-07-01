"""Nawigacja między modułami finansowymi (hub → KPiR / DNR / Dokumenty)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

_PENDING: "FinanceNavTarget | None" = None
_OPEN_CALLBACK: Callable[[str], None] | None = None


@dataclass(frozen=True)
class FinanceNavTarget:
    module: str  # kpir | dnr | dokumentysprzedazy
    screen: str  # revenue | costs | refunds | import | orders | invoice
    ref: str = ""


def back_for_nav_entry(
    *,
    entry_screen: str | None,
    current_screen: str,
    hub_back: Callable[[], None],
    module_back: Callable[[], None],
) -> Callable[[], None]:
    """Wróć do huba Księgowość, gdy ekran został otwarty bezpośrednio z checklisty."""
    if entry_screen and entry_screen == current_screen:
        return hub_back
    return module_back


def register_open_callback(fn: Callable[[str], None] | None) -> None:
    global _OPEN_CALLBACK
    _OPEN_CALLBACK = fn


def open_finance_module(folder_name: str) -> bool:
    if _OPEN_CALLBACK is None:
        return False
    _OPEN_CALLBACK(folder_name)
    return True


def set_nav(module: str, screen: str, ref: str = "") -> None:
    global _PENDING
    _PENDING = FinanceNavTarget(module=module, screen=screen, ref=ref)


def consume_nav(module: str) -> FinanceNavTarget | None:
    global _PENDING
    if _PENDING is not None and _PENDING.module == module:
        target = _PENDING
        _PENDING = None
        return target
    return None


def checklist_nav_target(category: str, ref: str) -> FinanceNavTarget | None:
    cat = (category or "").strip().lower()
    r = (ref or "").strip()
    if not r:
        return None
    if cat == "order":
        return FinanceNavTarget("dokumentysprzedazy", "orders", r)
    if cat == "invoice":
        if r.isdigit():
            return FinanceNavTarget("dokumentysprzedazy", "orders", r)
        return FinanceNavTarget("dokumentysprzedazy", "invoice", r)
    if cat == "dnr":
        return FinanceNavTarget("dnr", "import", r)
    if cat == "cost":
        return FinanceNavTarget("kpir", "costs", r)
    if cat == "refund":
        return FinanceNavTarget("kpir", "refunds", r)
    return None
