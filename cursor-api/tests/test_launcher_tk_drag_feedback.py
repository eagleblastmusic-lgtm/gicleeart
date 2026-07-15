"""Testy LC-3H: best-effort visual feedback Tk dla drag-and-drop."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from giclee_app import dragdrop_category_launcher as dnd
from giclee_app import launcher_tk_drag_feedback as feedback


class FakeWidget:
    def __init__(
        self,
        name: str,
        log: list[tuple[object, ...]],
        *,
        fail: bool = False,
    ) -> None:
        self.name = name
        self.log = log
        self.fail = fail

    def configure(self, **kwargs: object) -> None:
        self.log.append((self.name, kwargs))
        if self.fail:
            raise feedback.tk.TclError(f"{self.name} failed")


def test_begin_feedback_preserves_border_then_cursor_order() -> None:
    log: list[tuple[object, ...]] = []
    source = FakeWidget("source", log)
    root = FakeWidget("root", log)

    feedback.begin_drag_feedback(root, source)  # type: ignore[arg-type]

    assert log == [
        (
            "source",
            {
                "highlightbackground": feedback.BORDER_DRAG_SOURCE,
                "highlightcolor": feedback.BORDER_DRAG_SOURCE,
            },
        ),
        ("root", {"cursor": "fleur"}),
    ]


def test_begin_border_error_does_not_block_cursor() -> None:
    log: list[tuple[object, ...]] = []
    feedback.begin_drag_feedback(
        FakeWidget("root", log),  # type: ignore[arg-type]
        FakeWidget("source", log, fail=True),  # type: ignore[arg-type]
    )
    assert log[-1] == ("root", {"cursor": "fleur"})


def test_begin_cursor_tcl_error_is_best_effort() -> None:
    log: list[tuple[object, ...]] = []
    feedback.begin_drag_feedback(
        FakeWidget("root", log, fail=True),  # type: ignore[arg-type]
        FakeWidget("source", log),  # type: ignore[arg-type]
    )
    assert len(log) == 2


def test_previous_target_clears_only_when_object_changes() -> None:
    log: list[tuple[object, ...]] = []
    previous = FakeWidget("previous", log)
    next_target = FakeWidget("next", log)

    feedback.clear_previous_drop_target(None, next_target)  # type: ignore[arg-type]
    feedback.clear_previous_drop_target(previous, previous)  # type: ignore[arg-type]
    assert log == []

    feedback.clear_previous_drop_target(
        previous,  # type: ignore[arg-type]
        next_target,  # type: ignore[arg-type]
    )
    assert log == [
        (
            "previous",
            {
                "highlightbackground": feedback.BORDER_NORMAL,
                "highlightcolor": feedback.BORDER_NORMAL,
            },
        )
    ]


def test_show_drop_target_uses_exact_color() -> None:
    log: list[tuple[object, ...]] = []
    feedback.show_drop_target(FakeWidget("target", log))  # type: ignore[arg-type]
    assert log == [
        (
            "target",
            {
                "highlightbackground": feedback.BORDER_DROP_TARGET,
                "highlightcolor": feedback.BORDER_DROP_TARGET,
            },
        )
    ]


def test_clear_tiles_preserves_source_then_target_order() -> None:
    log: list[tuple[object, ...]] = []
    feedback.clear_drag_tile_feedback(
        FakeWidget("source", log),  # type: ignore[arg-type]
        FakeWidget("target", log),  # type: ignore[arg-type]
    )
    assert [entry[0] for entry in log] == ["source", "target"]
    assert all(
        entry[1]
        == {
            "highlightbackground": feedback.BORDER_NORMAL,
            "highlightcolor": feedback.BORDER_NORMAL,
        }
        for entry in log
    )


def test_clear_without_target_only_resets_source() -> None:
    log: list[tuple[object, ...]] = []
    feedback.clear_drag_tile_feedback(
        FakeWidget("source", log),  # type: ignore[arg-type]
        None,
    )
    assert [entry[0] for entry in log] == ["source"]


def test_clear_source_error_does_not_block_target() -> None:
    log: list[tuple[object, ...]] = []
    feedback.clear_drag_tile_feedback(
        FakeWidget("source", log, fail=True),  # type: ignore[arg-type]
        FakeWidget("target", log),  # type: ignore[arg-type]
    )
    assert [entry[0] for entry in log] == ["source", "target"]


def test_reset_cursor_and_expected_errors_are_best_effort() -> None:
    log: list[tuple[object, ...]] = []
    feedback.reset_drag_cursor(FakeWidget("root", log))  # type: ignore[arg-type]
    assert log == [("root", {"cursor": ""})]

    feedback.reset_drag_cursor(FakeWidget("broken", [], fail=True))  # type: ignore[arg-type]
    feedback.reset_drag_cursor(SimpleNamespace())  # type: ignore[arg-type]


def test_adapter_has_no_application_or_state_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_tk_drag_feedback.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert imports == {"__future__", "tkinter"}
    assert "_DragState" not in source
    assert "DragDropCategoryGicleeApp" not in source
    assert "Komponenty" not in source


class TrackingState:
    def __init__(self, target, log: list[object]) -> None:
        self._target = target
        self._after = False
        self.log = log

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value) -> None:
        self.log.append(("assign-target", value))
        self._target = value

    @property
    def after(self) -> bool:
        return self._after

    @after.setter
    def after(self, value: bool) -> None:
        self.log.append(("assign-after", value))
        self._after = value


def test_set_drop_target_preserves_orchestration_order(monkeypatch) -> None:
    log: list[object] = []
    previous = object()
    target = object()
    state = TrackingState(previous, log)
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)

    monkeypatch.setattr(
        dnd,
        "clear_previous_drop_target",
        lambda old, new: log.append(("clear-previous", old, new)),
    )
    monkeypatch.setattr(
        app,
        "_drop_after",
        lambda current, x, y: log.append(("drop-after", current, x, y)) or True,
    )
    monkeypatch.setattr(
        dnd,
        "show_drop_target",
        lambda current: log.append(("show-target", current)),
    )

    app._set_drop_target(state, target, 11, 22)  # type: ignore[arg-type]

    assert log == [
        ("clear-previous", previous, target),
        ("assign-target", target),
        ("drop-after", target, 11, 22),
        ("assign-after", True),
        ("show-target", target),
    ]


def test_none_target_zeros_after_without_show(monkeypatch) -> None:
    log: list[object] = []
    state = TrackingState(object(), log)
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    monkeypatch.setattr(
        dnd,
        "clear_previous_drop_target",
        lambda old, new: log.append(("clear-previous", old, new)),
    )
    monkeypatch.setattr(
        dnd,
        "show_drop_target",
        lambda current: pytest.fail("target feedback must not be shown"),
    )

    app._set_drop_target(state, None, 0, 0)  # type: ignore[arg-type]
    assert state.target is None
    assert state.after is False
    assert [entry[0] for entry in log] == [
        "clear-previous",
        "assign-target",
        "assign-after",
    ]


def test_clear_state_cleans_tiles_then_nulls_state_then_cursor(monkeypatch) -> None:
    events: list[object] = []
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    app.root = object()
    state = SimpleNamespace(source=object(), target=object())
    app._drag_state = state

    monkeypatch.setattr(
        dnd,
        "clear_drag_tile_feedback",
        lambda source, target: events.append(("clear-tiles", source, target)),
    )
    monkeypatch.setattr(
        dnd,
        "reset_drag_cursor",
        lambda root: events.append(("reset-cursor", app._drag_state, root)),
    )

    app._clear_drag_state()
    assert events == [
        ("clear-tiles", state.source, state.target),
        ("reset-cursor", None, app.root),
    ]
    assert app._drag_state is None


def test_clear_without_state_still_resets_cursor(monkeypatch) -> None:
    calls: list[object] = []
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    app.root = object()
    app._drag_state = None
    monkeypatch.setattr(
        dnd,
        "clear_drag_tile_feedback",
        lambda *_args: pytest.fail("no tiles should be cleared"),
    )
    monkeypatch.setattr(dnd, "reset_drag_cursor", lambda root: calls.append(root))

    app._clear_drag_state()
    assert calls == [app.root]


def test_launcher_delegates_feedback_without_duplicating_constants() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    assert "begin_drag_feedback(" in source
    assert "clear_previous_drop_target(" in source
    assert "show_drop_target(" in source
    assert "clear_drag_tile_feedback(" in source
    assert "reset_drag_cursor(" in source
    assert "def _set_tile_border" not in source
    assert "#dcdce2" not in source
    assert "#7b8798" not in source
    assert "#496a9b" not in source
