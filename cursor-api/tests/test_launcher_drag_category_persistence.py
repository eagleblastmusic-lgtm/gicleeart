from __future__ import annotations

import ast
from pathlib import Path

import pytest

from giclee_app import dragdrop_category_launcher as dnd
from giclee_app import launcher_drag_category_persistence as persistence
from giclee_app.launcher_layout import LauncherLayout


class _Status:
    def __init__(self, events: list[object]) -> None:
        self._events = events

    def set(self, text: str) -> None:
        self._events.append(("status", text))


def test_persist_moves_before_and_preserves_hidden_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = LauncherLayout(section_order=["A", "Hidden", "B", "C"])
    saved: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saved.append)

    changed = persistence.persist_category_reorder(
        layout,
        ["A", "B", "C"],
        "C",
        "B",
        after=False,
    )

    assert changed is True
    assert layout.section_order == ["A", "Hidden", "C", "B"]
    assert saved == [layout]


def test_persist_moves_after(monkeypatch: pytest.MonkeyPatch) -> None:
    layout = LauncherLayout(section_order=["A", "B", "C"])
    monkeypatch.setattr(persistence, "save_layout", lambda _layout: None)

    changed = persistence.persist_category_reorder(
        layout,
        ["A", "B", "C"],
        "A",
        "B",
        after=True,
    )

    assert changed is True
    assert layout.section_order == ["B", "A", "C"]


def test_empty_section_order_falls_back_to_visible_without_mutating_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visible = ["A", "B", "C"]
    layout = LauncherLayout()
    snapshots: list[list[str]] = []
    monkeypatch.setattr(
        persistence,
        "save_layout",
        lambda saved: snapshots.append(list(saved.section_order)),
    )

    changed = persistence.persist_category_reorder(
        layout,
        visible,
        "C",
        "A",
        after=False,
    )

    assert changed is True
    assert visible == ["A", "B", "C"]
    assert layout.section_order == ["C", "A", "B"]
    assert snapshots == [["C", "A", "B"]]


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("A", "A"),
        ("missing", "B"),
        ("A", "missing"),
    ],
)
def test_noop_does_not_mutate_or_save(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    target: str,
) -> None:
    layout = LauncherLayout(section_order=["A", "Hidden", "B"])
    original = list(layout.section_order)
    saves: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saves.append)

    changed = persistence.persist_category_reorder(
        layout,
        ["A", "B"],
        source,
        target,
        after=False,
    )

    assert changed is False
    assert layout.section_order == original
    assert saves == []


def test_save_receives_same_layout_after_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = LauncherLayout(section_order=["A", "B"])
    observed: list[tuple[bool, list[str]]] = []

    def save(saved: LauncherLayout) -> None:
        observed.append((saved is layout, list(saved.section_order)))

    monkeypatch.setattr(persistence, "save_layout", save)

    assert persistence.persist_category_reorder(
        layout,
        ["A", "B"],
        "A",
        "B",
        after=True,
    )
    assert observed == [(True, ["B", "A"])]


def test_save_error_propagates_without_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = LauncherLayout(section_order=["A", "B"])

    def fail(_layout: LauncherLayout) -> None:
        raise OSError("write failed")

    monkeypatch.setattr(persistence, "save_layout", fail)

    with pytest.raises(OSError, match="write failed"):
        persistence.persist_category_reorder(
            layout,
            ["A", "B"],
            "A",
            "B",
            after=True,
        )

    assert layout.section_order == ["B", "A"]


def test_adapter_imports_only_domain_dependencies() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_drag_category_persistence.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "tkinter" not in imported
    assert all("dragdrop_category_launcher" not in module for module in imported_from)
    assert all("category_launcher" not in module for module in imported_from)
    assert all("renderer" not in module for module in imported_from)
    assert all("Komponenty" not in module for module in imported_from)
    assert "persist_category_reorder" in persistence.__all__


def _launcher_app(events: list[object]) -> dnd.DragDropCategoryGicleeApp:
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    app._all_components = []
    app._layout = LauncherLayout(section_order=["A", "B"])
    app._normally_visible = set()
    app._render_tiles = lambda: events.append("render")  # type: ignore[method-assign]
    app._finish_navigation_render = lambda: events.append("finish")  # type: ignore[method-assign]
    app.status_var = _Status(events)
    return app


def test_launcher_category_writer_orders_persist_then_ui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    app = _launcher_app(events)
    monkeypatch.setattr(
        dnd,
        "resolve_sections",
        lambda *_args, **_kwargs: [("A", []), ("B", [])],
    )

    def persist(
        layout: LauncherLayout,
        visible_titles: list[str],
        source: str,
        target: str,
        *,
        after: bool,
    ) -> bool:
        events.append(
            (
                "persist",
                layout is app._layout,
                list(visible_titles),
                source,
                target,
                after,
            )
        )
        return True

    monkeypatch.setattr(dnd, "persist_category_reorder", persist)

    app._reorder_category("A", "B", after=True)

    assert events == [
        ("persist", True, ["A", "B"], "A", "B", True),
        "render",
        "finish",
        ("status", "Zapisano nową kolejność kategorii"),
    ]


def test_launcher_category_noop_has_no_ui_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    app = _launcher_app(events)
    monkeypatch.setattr(
        dnd,
        "resolve_sections",
        lambda *_args, **_kwargs: [("A", []), ("B", [])],
    )
    monkeypatch.setattr(dnd, "persist_category_reorder", lambda *_args, **_kwargs: False)

    app._reorder_category("A", "B", after=False)

    assert events == []


def test_launcher_category_save_error_blocks_ui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    app = _launcher_app(events)
    monkeypatch.setattr(
        dnd,
        "resolve_sections",
        lambda *_args, **_kwargs: [("A", []), ("B", [])],
    )

    def fail(*_args: object, **_kwargs: object) -> bool:
        raise OSError("write failed")

    monkeypatch.setattr(dnd, "persist_category_reorder", fail)

    with pytest.raises(OSError, match="write failed"):
        app._reorder_category("A", "B", after=False)

    assert events == []


def test_launcher_category_method_is_thin_and_component_writer_is_unchanged() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    category = source.split("def _reorder_category", 1)[1].split("\n    def ", 1)[0]
    component = source.split("def _reorder_component", 1)[1].split("\n\n\ndef main", 1)[0]

    assert "persist_category_reorder(" in category
    assert "save_layout(" not in category
    assert "reorder_relative(" not in category
    assert "replace_subset_order(" not in category
    assert "self._render_tiles()" in category
    assert "self._finish_navigation_render()" in category
    assert 'self.status_var.set("Zapisano nową kolejność kategorii")' in category

    assert "reorder_relative(" in component
    assert "replace_subset_order(" in component
    assert "entry.sort_key = index * 10" in component
    assert "save_layout(self._layout)" in component
