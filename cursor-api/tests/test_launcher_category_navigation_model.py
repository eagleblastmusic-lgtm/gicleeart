"""Testy LC-2A: czysty model trasy kategorii."""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

from giclee_app.category_navigation import (
    CategoryViewKind,
    resolve_category_navigation,
)
from giclee_app.component_loader import Component
from giclee_app.launcher_layout import LauncherLayout, TileLayoutEntry


def _component(folder: str, name: str | None = None) -> Component:
    return Component(
        folder_name=folder,
        package_path=Path("/fake") / folder,
        name=name or folder,
        description="",
        order=0,
    )


def _layout(*entries: TileLayoutEntry, order: list[str] | None = None) -> LauncherLayout:
    return LauncherLayout(
        entries={entry.folder: entry for entry in entries},
        section_order=list(order or []),
    )


def test_no_components_returns_no_components_plan() -> None:
    plan = resolve_category_navigation(
        [],
        LauncherLayout(),
        normally_visible=set(),
        active_section="Missing",
    )

    assert plan.kind is CategoryViewKind.NO_COMPONENTS
    assert plan.active_section is None
    assert plan.sections == ()
    assert plan.active_components == ()


def test_existing_components_without_visible_sections_return_empty_visible_plan() -> None:
    comp = _component("a")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=False, sort_key=0),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [comp],
        layout,
        normally_visible={"a"},
        active_section="Pierwsza",
    )

    assert plan.kind is CategoryViewKind.NO_VISIBLE_SECTIONS
    assert plan.active_section is None
    assert plan.sections == ()


def test_missing_active_section_returns_category_index() -> None:
    comp = _component("a")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=0),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [comp],
        layout,
        normally_visible={"a"},
        active_section=None,
    )

    assert plan.kind is CategoryViewKind.CATEGORY_INDEX
    assert plan.active_section is None
    assert plan.sections == (("Pierwsza", (comp,)),)


def test_valid_active_section_returns_immutable_components_route() -> None:
    first = _component("a")
    second = _component("b")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=20),
        TileLayoutEntry(folder="b", section="Pierwsza", visible=True, sort_key=10),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [first, second],
        layout,
        normally_visible={"a", "b"},
        active_section="Pierwsza",
    )

    assert plan.kind is CategoryViewKind.CATEGORY_COMPONENTS
    assert plan.active_section == "Pierwsza"
    assert plan.sections == (("Pierwsza", (second, first)),)
    assert plan.active_components == (second, first)
    assert isinstance(plan.sections, tuple)
    assert isinstance(plan.active_components, tuple)


def test_invalid_or_now_hidden_active_section_returns_index() -> None:
    comp = _component("a")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=0),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [comp],
        layout,
        normally_visible={"a"},
        active_section="Usunięta",
    )

    assert plan.kind is CategoryViewKind.CATEGORY_INDEX
    assert plan.active_section is None
    assert plan.sections == (("Pierwsza", (comp,)),)


def test_section_and_component_order_matches_launcher_layout() -> None:
    a = _component("a")
    b = _component("b")
    c = _component("c")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Druga", visible=True, sort_key=10),
        TileLayoutEntry(folder="b", section="Pierwsza", visible=True, sort_key=20),
        TileLayoutEntry(folder="c", section="Pierwsza", visible=True, sort_key=10),
        order=["Pierwsza", "Druga"],
    )

    plan = resolve_category_navigation(
        [a, b, c],
        layout,
        normally_visible={"a", "b", "c"},
        active_section=None,
    )

    assert plan.sections == (
        ("Pierwsza", (c, b)),
        ("Druga", (a,)),
    )


def test_resolver_does_not_mutate_inputs() -> None:
    comp = _component("a")
    components = [comp]
    visible = {"a"}
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=0),
        order=["Pierwsza"],
    )
    layout_before = deepcopy(layout.to_dict())
    components_before = list(components)
    visible_before = set(visible)

    resolve_category_navigation(
        components,
        layout,
        normally_visible=visible,
        active_section="Pierwsza",
    )

    assert layout.to_dict() == layout_before
    assert components == components_before
    assert visible == visible_before


def test_model_module_has_no_tk_or_ui_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "category_navigation.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name == "tkinter" or name.startswith("tkinter.") for name in imports)
    assert not any(name.startswith("giclee_app.ui") for name in imports)


def test_category_renderer_consumes_navigation_plan_and_keeps_hooks() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "category_launcher.py"
    source = path.read_text(encoding="utf-8")
    render_block = source.split("def _render_tiles", 1)[1].split("\n    def ", 1)[0]

    assert "resolve_category_navigation(" in render_block
    assert "CategoryViewKind.NO_COMPONENTS" in render_block
    assert "CategoryViewKind.NO_VISIBLE_SECTIONS" in render_block
    assert "CategoryViewKind.CATEGORY_INDEX" in render_block
    assert "Brak wykrytych komponentów" in render_block
    assert "Brak widocznych komponentów" in render_block
    assert "def _render_category_index" in source
    assert "def _render_category_components" in source
    assert "def _build_category_tile" in source
