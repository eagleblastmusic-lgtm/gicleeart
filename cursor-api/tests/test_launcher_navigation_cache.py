from __future__ import annotations

from pathlib import Path

from giclee_app.category_navigation import CategoryNavigationPlan, CategoryViewKind
from giclee_app.component_loader import Component
from giclee_app.launcher_navigation_cache import (
    NavigationViewCache,
    navigation_view_key,
    navigation_view_signature,
)


def _component(name: str, *, extras: dict | None = None) -> Component:
    return Component(
        folder_name=name,
        package_path=Path("C:/components") / name,
        name=name.title(),
        description="Opis",
        icon="■",
        color="#445566",
        mode="inline",
        availability=("classic", "studio_preview", "studio"),
        extras=extras or {},
    )


def test_cache_requires_matching_signature() -> None:
    cache = NavigationViewCache[str]()
    plan = CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_COMPONENTS,
        active_section="Administracja",
        active_components=(_component("one"),),
    )
    key = navigation_view_key(plan)
    signature = navigation_view_signature(plan)

    assert cache.get(key, signature) is None
    assert cache.put(key, signature, "frame") is None
    assert cache.get(key, signature) == "frame"
    assert cache.get(key, ("changed",)) is None


def test_component_metadata_changes_category_signature() -> None:
    first = CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_COMPONENTS,
        active_section="Administracja",
        active_components=(_component("one", extras={"flags": [1, 2]}),),
    )
    second = CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_COMPONENTS,
        active_section="Administracja",
        active_components=(_component("one", extras={"flags": [1, 3]}),),
    )

    assert navigation_view_key(first) == navigation_view_key(second)
    assert navigation_view_signature(first) != navigation_view_signature(second)


def test_index_tracks_all_sections_but_category_tracks_only_active_content() -> None:
    one = _component("one")
    two = _component("two")
    three = _component("three")
    index_before = CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_INDEX,
        active_section=None,
        sections=(("A", (one,)), ("B", (two,))),
    )
    index_after = CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_INDEX,
        active_section=None,
        sections=(("A", (one,)), ("B", (three,))),
    )
    category_before = CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_COMPONENTS,
        active_section="A",
        sections=index_before.sections,
        active_components=(one,),
    )
    category_after = CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_COMPONENTS,
        active_section="A",
        sections=index_after.sections,
        active_components=(one,),
    )

    assert navigation_view_signature(index_before) != navigation_view_signature(index_after)
    assert navigation_view_signature(category_before) == navigation_view_signature(category_after)


def test_put_pop_and_clear_return_replaced_values() -> None:
    cache = NavigationViewCache[str]()
    empty = CategoryNavigationPlan(CategoryViewKind.NO_COMPONENTS, None)
    index = CategoryNavigationPlan(CategoryViewKind.CATEGORY_INDEX, None)
    empty_key = navigation_view_key(empty)
    index_key = navigation_view_key(index)

    assert cache.put(empty_key, navigation_view_signature(empty), "first") is None
    assert cache.put(empty_key, navigation_view_signature(empty), "second") == "first"
    cache.put(index_key, navigation_view_signature(index), "index")

    assert cache.pop(empty_key) == "second"
    assert cache.clear() == ("index",)
    assert len(cache) == 0
