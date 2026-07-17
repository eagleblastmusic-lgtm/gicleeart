"""Neutral cache keys and signatures for classic launcher navigation views."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from .category_navigation import CategoryNavigationPlan, CategoryViewKind
from .component_loader import Component


T = TypeVar("T")


@dataclass(frozen=True)
class NavigationViewKey:
    """Stable identity of one launcher navigation screen."""

    kind: CategoryViewKind
    active_section: str | None = None


@dataclass(frozen=True)
class _CacheRecord(Generic[T]):
    signature: Hashable
    value: T


class NavigationViewCache(Generic[T]):
    """Small signature-aware cache without Tk or filesystem side effects."""

    def __init__(self) -> None:
        self._records: dict[NavigationViewKey, _CacheRecord[T]] = {}

    def get(self, key: NavigationViewKey, signature: Hashable) -> T | None:
        record = self._records.get(key)
        if record is None or record.signature != signature:
            return None
        return record.value

    def put(self, key: NavigationViewKey, signature: Hashable, value: T) -> T | None:
        previous = self._records.get(key)
        self._records[key] = _CacheRecord(signature=signature, value=value)
        return previous.value if previous is not None else None

    def pop(self, key: NavigationViewKey) -> T | None:
        record = self._records.pop(key, None)
        return record.value if record is not None else None

    def clear(self) -> tuple[T, ...]:
        values = tuple(record.value for record in self._records.values())
        self._records.clear()
        return values

    def __len__(self) -> int:
        return len(self._records)


def navigation_view_key(plan: CategoryNavigationPlan) -> NavigationViewKey:
    """Return a key that separates index, empty states and each category."""

    return NavigationViewKey(
        kind=plan.kind,
        active_section=(
            plan.active_section
            if plan.kind is CategoryViewKind.CATEGORY_COMPONENTS
            else None
        ),
    )


def navigation_view_signature(plan: CategoryNavigationPlan) -> Hashable:
    """Fingerprint only the data that changes the selected rendered screen."""

    if plan.kind is CategoryViewKind.CATEGORY_INDEX:
        return (
            plan.kind.value,
            tuple(
                (title, tuple(_component_signature(component) for component in components))
                for title, components in plan.sections
            ),
        )

    if plan.kind is CategoryViewKind.CATEGORY_COMPONENTS:
        return (
            plan.kind.value,
            plan.active_section,
            tuple(_component_signature(component) for component in plan.active_components),
        )

    return (plan.kind.value,)


def _component_signature(component: Component) -> Hashable:
    return (
        component.folder_name,
        str(component.package_path),
        component.name,
        component.description,
        component.icon,
        component.color,
        int(component.order),
        component.mode,
        component.url,
        bool(component.hidden),
        tuple(component.availability),
        component.stability,
        _freeze(component.extras),
    )


def _freeze(value: object) -> Hashable:
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (str(key), _freeze(item))
                for key, item in value.items()
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze(item) for item in value)
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value  # type: ignore[return-value]


__all__ = [
    "NavigationViewCache",
    "NavigationViewKey",
    "navigation_view_key",
    "navigation_view_signature",
]
