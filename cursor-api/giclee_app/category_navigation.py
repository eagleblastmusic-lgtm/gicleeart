"""Czysty model trasy kategorii klasycznego launchera."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from .component_loader import Component
from .launcher_layout import LauncherLayout, resolve_sections


class CategoryViewKind(str, Enum):
    """Ekran, który powinien wyrenderować klasyczny launcher kategorii."""

    NO_COMPONENTS = "no_components"
    NO_VISIBLE_SECTIONS = "no_visible_sections"
    CATEGORY_INDEX = "category_index"
    CATEGORY_COMPONENTS = "category_components"


CategorySection = tuple[str, tuple[Component, ...]]


@dataclass(frozen=True)
class CategoryNavigationPlan:
    """Niemutowalny wynik rozstrzygnięcia aktualnej trasy kategorii."""

    kind: CategoryViewKind
    active_section: str | None
    sections: tuple[CategorySection, ...] = ()
    active_components: tuple[Component, ...] = ()


def resolve_category_navigation(
    all_components: Sequence[Component],
    layout: LauncherLayout,
    *,
    normally_visible: set[str],
    active_section: str | None,
) -> CategoryNavigationPlan:
    """Rozstrzyga ekran bez Tk, I/O i mutacji wejściowego stanu."""

    components = tuple(all_components)
    if not components:
        return CategoryNavigationPlan(
            kind=CategoryViewKind.NO_COMPONENTS,
            active_section=None,
        )

    resolved = resolve_sections(
        list(components),
        layout,
        normally_visible=normally_visible,
    )
    sections: tuple[CategorySection, ...] = tuple(
        (title, tuple(section_components))
        for title, section_components in resolved
    )
    if not sections:
        return CategoryNavigationPlan(
            kind=CategoryViewKind.NO_VISIBLE_SECTIONS,
            active_section=None,
        )

    by_title = dict(sections)
    normalized_active = active_section if active_section in by_title else None
    if normalized_active is None:
        return CategoryNavigationPlan(
            kind=CategoryViewKind.CATEGORY_INDEX,
            active_section=None,
            sections=sections,
        )

    return CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_COMPONENTS,
        active_section=normalized_active,
        sections=sections,
        active_components=by_title[normalized_active],
    )
