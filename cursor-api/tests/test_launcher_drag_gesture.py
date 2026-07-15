"""Testy LC-3E: czyste decyzje przejść gestu drag-and-drop."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from giclee_app import dragdrop_category_launcher as dnd
from giclee_app import launcher_tk_drag_feedback as feedback
from giclee_app.launcher_drag_gesture import (
    DragMotionKind,
    DragReleaseKind,
    resolve_drag_motion,
    resolve_drag_release,
)


@pytest.mark.parametrize(
    ("dragging", "threshold", "expected"),
    [
        (False, False, DragMotionKind.WAITING),
        (False, True, DragMotionKind.START),
        (True, False, DragMotionKind.CONTINUE),
        (True, True, DragMotionKind.CONTINUE),
    ],
)
def test_motion_decisions(
    dragging: bool,
    threshold: bool,
    expected: DragMotionKind,
) -> None:
    assert resolve_drag_motion(
        dragging=dragging,
        threshold_reached=threshold,
    ) is expected


@pytest.mark.parametrize(
    ("dragging", "drag_kind", "source", "target", "expected"),
    [
        (False, "component", "a", "", DragReleaseKind.ACTIVATE),
        (False, "unknown", "a", "a", DragReleaseKind.ACTIVATE),
        (True, "component", "a", "", DragReleaseKind.NOOP),
        (True, "component", "a", "a", DragReleaseKind.NOOP),
        (True, "unknown", "a", "b", DragReleaseKind.NOOP),
        (True, "category", "a", "b", DragReleaseKind.REORDER),
        (True, "component", "a", "b", DragReleaseKind.REORDER),
    ],
)
def test_release_decisions(
    dragging: bool,
    drag_kind: str,
    source: str,
    target: str,
    expected: DragReleaseKind,
) -> None:
    decision = resolve_drag_release(
        dragging=dragging,
        drag_kind=drag_kind,
        source_key=source,
        target_key=target,
        after=True,
    )
    assert decision.kind is expected
    assert decision.drag_kind == drag_kind
    assert decision.source_key == source
    assert decision.target_key == target
    assert decision.after is True


def test_release_decision_is_frozen_and_preserves_inputs() -> None:
    decision = resolve_drag_release(
        dragging=True,
        drag_kind="category",
        source_key=" A ",
        target_key=" B ",
        after=False,
    )
    assert decision.source_key == " A "
    assert decision.target_key == " B "
    with pytest.raises(FrozenInstanceError):
        decision.after = True  # type: ignore[misc]


def test_gesture_module_has_no_ui_geometry_or_application_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_drag_gesture.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "tkinter" not in imports
    assert not any(name.startswith("giclee_app") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)


class FakeTile:
    def __init__(self, key: str = "target") -> None:
        self._launcher_dnd_key = key
        self.border_calls: list[dict[str, object]] = []

    def configure(self, **kwargs: object) -> None:
        self.border_calls.append(kwargs)


class FakeRoot:
    def __init__(self) -> None:
        self.configure_calls: list[dict[str, object]] = []

    def configure(self, **kwargs: object) -> None:
        self.configure_calls.append(kwargs)


def _motion_app(*, dragging: bool):
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    source = FakeTile("source")
    app.root = FakeRoot()
    app._drag_state = dnd._DragState(
        kind="component",
        key="source",
        source=source,  # type: ignore[arg-type]
        start_x_root=0,
        start_y_root=0,
        activate=lambda: None,
        dragging=dragging,
    )
    calls: list[object] = []
    app._auto_scroll_drag = lambda y: calls.append(("scroll", y))
    target = FakeTile("target")
    app._find_drop_target = lambda *args, **kwargs: target  # type: ignore[assignment]
    app._set_drop_target = lambda *args: calls.append(("target", args[1]))
    return app, source, target, calls


def test_motion_waiting_has_no_side_effects() -> None:
    app, source, _target, calls = _motion_app(dragging=False)
    result = app._on_tile_motion(SimpleNamespace(x_root=3, y_root=4))
    assert result is None
    assert app._drag_state is not None and app._drag_state.dragging is False
    assert source.border_calls == []
    assert app.root.configure_calls == []
    assert calls == []


def test_motion_start_sets_visuals_once_then_continues() -> None:
    app, source, target, calls = _motion_app(dragging=False)
    result = app._on_tile_motion(SimpleNamespace(x_root=8, y_root=0))
    assert result == "break"
    assert app._drag_state is not None and app._drag_state.dragging is True
    assert source.border_calls == [
        {
            "highlightbackground": feedback.BORDER_DRAG_SOURCE,
            "highlightcolor": feedback.BORDER_DRAG_SOURCE,
        }
    ]
    assert app.root.configure_calls == [{"cursor": "fleur"}]
    assert calls == [("scroll", 0), ("target", target)]

    calls.clear()
    app._on_tile_motion(SimpleNamespace(x_root=9, y_root=1))
    assert len(source.border_calls) == 1
    assert len(app.root.configure_calls) == 1
    assert calls == [("scroll", 1), ("target", target)]


def _release_app(
    *,
    dragging: bool,
    kind: str = "component",
    source_key: str = "source",
    target_key: str | None = "target",
    after: bool = True,
):
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    events: list[object] = []
    source = FakeTile(source_key)
    target = FakeTile(target_key) if target_key is not None else None
    app._drag_state = dnd._DragState(
        kind=kind,
        key=source_key,
        source=source,  # type: ignore[arg-type]
        start_x_root=0,
        start_y_root=0,
        activate=lambda: events.append("activate"),
        dragging=dragging,
        target=target,  # type: ignore[arg-type]
        after=after,
    )

    def clear() -> None:
        events.append("clear")
        app._drag_state = None

    app._clear_drag_state = clear
    app._find_drop_target = lambda *args, **kwargs: None  # type: ignore[assignment]
    app._reorder_category = lambda source, target, *, after: events.append(
        ("category", source, target, after)
    )
    app._reorder_component = lambda source, target, *, after: events.append(
        ("component", source, target, after)
    )
    return app, events


def test_click_release_clears_reference_and_activates() -> None:
    app, events = _release_app(dragging=False, target_key=None)
    result = app._on_tile_release(SimpleNamespace(x_root=0, y_root=0))
    assert result == "break"
    assert app._drag_state is None
    assert events == ["activate"]


@pytest.mark.parametrize("kind", ["category", "component"])
def test_drag_release_clears_before_reorder(kind: str) -> None:
    app, events = _release_app(dragging=True, kind=kind, after=True)
    result = app._on_tile_release(SimpleNamespace(x_root=0, y_root=0))
    assert result == "break"
    assert events == ["clear", (kind, "source", "target", True)]


@pytest.mark.parametrize(
    ("kind", "target"),
    [
        ("component", None),
        ("component", "source"),
        ("unknown", "target"),
    ],
)
def test_drag_release_noop_only_clears(kind: str, target: str | None) -> None:
    app, events = _release_app(
        dragging=True,
        kind=kind,
        target_key=target,
    )
    app._on_tile_release(SimpleNamespace(x_root=0, y_root=0))
    assert events == ["clear"]


def test_dragdrop_source_delegates_motion_and_release_decisions() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    motion = source.split("def _on_tile_motion", 1)[1].split("\n    def ", 1)[0]
    release = source.split("def _on_tile_release", 1)[1].split("\n    def ", 1)[0]

    assert "resolve_drag_motion(" in motion
    assert "DragMotionKind.WAITING" in motion
    assert "DragMotionKind.START" in motion
    assert "state.dragging = True" in motion
    assert "begin_drag_feedback(" in motion
    assert "self._auto_scroll_drag(" in motion

    assert release.count("resolve_drag_release(") == 2
    assert "DragReleaseKind.ACTIVATE" in release
    assert "DragReleaseKind.REORDER" in release
    assert "self._clear_drag_state()" in release
    assert "self._reorder_category(" in release
    assert "self._reorder_component(" in release
