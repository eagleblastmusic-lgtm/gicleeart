"""Czyste helpery kolejności dla drag-and-drop kafelków launchera."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypeVar


_T = TypeVar("_T")


def _unique(items: Iterable[_T]) -> list[_T]:
    result: list[_T] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def reorder_relative(
    items: Sequence[_T],
    source: _T,
    target: _T,
    *,
    after: bool,
) -> list[_T]:
    """Przenosi ``source`` bezpośrednio przed albo za ``target``.

    Nie zmienia wejściowej sekwencji. Brakujące elementy oraz upuszczenie na samym
    sobie pozostawiają kolejność bez zmian.
    """

    ordered = _unique(items)
    if source not in ordered or target not in ordered or source == target:
        return ordered

    ordered.remove(source)
    target_index = ordered.index(target)
    insert_at = target_index + (1 if after else 0)
    ordered.insert(insert_at, source)
    return ordered


def replace_subset_order(
    existing_order: Sequence[_T],
    reordered_subset: Sequence[_T],
) -> list[_T]:
    """Podmienia kolejność podzbioru, zachowując pozycje pozostałych elementów.

    Używane m.in. do zachowania ukrytych komponentów pomiędzy widocznymi
    kafelkami oraz pustych kategorii w ``section_order``.
    """

    existing = _unique(existing_order)
    subset = _unique(reordered_subset)
    subset_set = set(subset)
    replacement = iter(subset)
    result: list[_T] = []

    for item in existing:
        if item in subset_set:
            try:
                result.append(next(replacement))
            except StopIteration:
                continue
        else:
            result.append(item)

    for item in replacement:
        if item not in result:
            result.append(item)
    return result


__all__ = ["reorder_relative", "replace_subset_order"]
