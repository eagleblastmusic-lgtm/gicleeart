from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "cursor-api" / "giclee_app"
TESTS = ROOT / "cursor-api" / "tests"


def replace_exact(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one match in {path}: found {count}")
    path.write_text(source.replace(old, new), encoding="utf-8")


def main() -> None:
    launcher = APP / "dragdrop_category_launcher.py"
    gesture_tests = TESTS / "test_launcher_drag_gesture.py"
    launcher_docs = APP / "docs" / "launcher.md"
    contract = APP / "docs" / "launcher-composition-lc3h-contract.md"

    replace_exact(
        launcher,
        "from .launcher_tk_drag_targets import find_drop_target, widget_drag_rect\n",
        "from .launcher_tk_drag_feedback import (\n"
        "    begin_drag_feedback,\n"
        "    clear_drag_tile_feedback,\n"
        "    clear_previous_drop_target,\n"
        "    reset_drag_cursor,\n"
        "    show_drop_target,\n"
        ")\n"
        "from .launcher_tk_drag_targets import find_drop_target, widget_drag_rect\n",
    )
    replace_exact(
        launcher,
        "_DRAG_THRESHOLD_PX = 8\n"
        "_DROP_VERTICAL_RATIO = 0.22\n"
        "_BORDER_NORMAL = \"#dcdce2\"\n"
        "_BORDER_DRAG_SOURCE = \"#7b8798\"\n"
        "_BORDER_DROP_TARGET = \"#496a9b\"\n",
        "_DRAG_THRESHOLD_PX = 8\n"
        "_DROP_VERTICAL_RATIO = 0.22\n",
    )
    replace_exact(
        launcher,
        "        if motion is DragMotionKind.START:\n"
        "            state.dragging = True\n"
        "            self._set_tile_border(state.source, _BORDER_DRAG_SOURCE)\n"
        "            try:\n"
        "                self.root.configure(cursor=\"fleur\")\n"
        "            except tk.TclError:\n"
        "                pass\n",
        "        if motion is DragMotionKind.START:\n"
        "            state.dragging = True\n"
        "            begin_drag_feedback(self.root, state.source)\n",
    )
    replace_exact(
        launcher,
        "        if state.target is not None and state.target is not target:\n"
        "            self._set_tile_border(state.target, _BORDER_NORMAL)\n"
        "        state.target = target\n"
        "        if target is None:\n"
        "            state.after = False\n"
        "            return\n"
        "        state.after = self._drop_after(target, x_root, y_root)\n"
        "        self._set_tile_border(target, _BORDER_DROP_TARGET)\n",
        "        clear_previous_drop_target(state.target, target)\n"
        "        state.target = target\n"
        "        if target is None:\n"
        "            state.after = False\n"
        "            return\n"
        "        state.after = self._drop_after(target, x_root, y_root)\n"
        "        show_drop_target(target)\n",
    )
    replace_exact(
        launcher,
        "    @staticmethod\n"
        "    def _set_tile_border(tile: tk.Frame, color: str) -> None:\n"
        "        try:\n"
        "            tile.configure(highlightbackground=color, highlightcolor=color)\n"
        "        except tk.TclError:\n"
        "            pass\n\n",
        "",
    )
    replace_exact(
        launcher,
        "    def _clear_drag_state(self) -> None:\n"
        "        state = self._drag_state\n"
        "        if state is not None:\n"
        "            self._set_tile_border(state.source, _BORDER_NORMAL)\n"
        "            if state.target is not None:\n"
        "                self._set_tile_border(state.target, _BORDER_NORMAL)\n"
        "        self._drag_state = None\n"
        "        try:\n"
        "            self.root.configure(cursor=\"\")\n"
        "        except (AttributeError, tk.TclError):\n"
        "            pass\n",
        "    def _clear_drag_state(self) -> None:\n"
        "        state = self._drag_state\n"
        "        if state is not None:\n"
        "            clear_drag_tile_feedback(state.source, state.target)\n"
        "        self._drag_state = None\n"
        "        reset_drag_cursor(self.root)\n",
    )

    (APP / "launcher_tk_drag_feedback.py").write_text(
        '''"""Best-effort adapter Tk dla wizualnego feedbacku drag-and-drop."""\n\n'
        'from __future__ import annotations\n\n'
        'import tkinter as tk\n\n\n'
        'BORDER_NORMAL = "#dcdce2"\n'
        'BORDER_DRAG_SOURCE = "#7b8798"\n'
        'BORDER_DROP_TARGET = "#496a9b"\n'
        '_DRAG_CURSOR = "fleur"\n'
        '_DEFAULT_CURSOR = ""\n\n\n'
        'def _set_tile_border(tile: tk.Frame, color: str) -> None:\n'
        '    try:\n'
        '        tile.configure(highlightbackground=color, highlightcolor=color)\n'
        '    except tk.TclError:\n'
        '        pass\n\n\n'
        'def begin_drag_feedback(root: tk.Misc, source: tk.Frame) -> None:\n'
        '    """Pokazuje źródło gestu i kursor przeciągania."""\n\n'
        '    _set_tile_border(source, BORDER_DRAG_SOURCE)\n'
        '    try:\n'
        '        root.configure(cursor=_DRAG_CURSOR)\n'
        '    except tk.TclError:\n'
        '        pass\n\n\n'
        'def clear_previous_drop_target(\n'
        '    previous_target: tk.Frame | None,\n'
        '    next_target: tk.Frame | None,\n'
        ') -> None:\n'
        '    """Czyści poprzedni cel wyłącznie przy rzeczywistej zmianie."""\n\n'
        '    if previous_target is None or previous_target is next_target:\n'
        '        return\n'
        '    _set_tile_border(previous_target, BORDER_NORMAL)\n\n\n'
        'def show_drop_target(target: tk.Frame) -> None:\n'
        '    """Podświetla bieżący cel upuszczenia."""\n\n'
        '    _set_tile_border(target, BORDER_DROP_TARGET)\n\n\n'
        'def clear_drag_tile_feedback(\n'
        '    source: tk.Frame,\n'
        '    target: tk.Frame | None,\n'
        ') -> None:\n'
        '    """Przywraca normalne ramki source, a następnie targetu."""\n\n'
        '    _set_tile_border(source, BORDER_NORMAL)\n'
        '    if target is not None:\n'
        '        _set_tile_border(target, BORDER_NORMAL)\n\n\n'
        'def reset_drag_cursor(root: tk.Misc) -> None:\n'
        '    """Best-effort przywraca domyślny kursor root."""\n\n'
        '    try:\n'
        '        root.configure(cursor=_DEFAULT_CURSOR)\n'
        '    except (AttributeError, tk.TclError):\n'
        '        pass\n\n\n'
        '__all__ = [\n'
        '    "BORDER_DRAG_SOURCE",\n'
        '    "BORDER_DROP_TARGET",\n'
        '    "BORDER_NORMAL",\n'
        '    "begin_drag_feedback",\n'
        '    "clear_drag_tile_feedback",\n'
        '    "clear_previous_drop_target",\n'
        '    "reset_drag_cursor",\n'
        '    "show_drop_target",\n'
        ']\n''',
        encoding="utf-8",
    )

    replace_exact(
        gesture_tests,
        "from giclee_app import dragdrop_category_launcher as dnd\n",
        "from giclee_app import dragdrop_category_launcher as dnd\n"
        "from giclee_app import launcher_tk_drag_feedback as feedback\n",
    )
    replace_exact(
        gesture_tests,
        "dnd._BORDER_DRAG_SOURCE",
        "feedback.BORDER_DRAG_SOURCE",
    )
    replace_exact(
        gesture_tests,
        "    assert \"state.dragging = True\" in motion\n"
        "    assert \"self._auto_scroll_drag(\" in motion\n",
        "    assert \"state.dragging = True\" in motion\n"
        "    assert \"begin_drag_feedback(\" in motion\n"
        "    assert \"self._auto_scroll_drag(\" in motion\n",
    )

    (TESTS / "test_launcher_tk_drag_feedback.py").write_text(
        '''"""Testy LC-3H: best-effort visual feedback Tk dla drag-and-drop."""\n\n'
        'from __future__ import annotations\n\n'
        'import ast\n'
        'from pathlib import Path\n'
        'from types import SimpleNamespace\n\n'
        'import pytest\n\n'
        'from giclee_app import dragdrop_category_launcher as dnd\n'
        'from giclee_app import launcher_tk_drag_feedback as feedback\n\n\n'
        'class FakeWidget:\n'
        '    def __init__(\n'
        '        self,\n'
        '        name: str,\n'
        '        log: list[tuple[object, ...]],\n'
        '        *,\n'
        '        fail: bool = False,\n'
        '    ) -> None:\n'
        '        self.name = name\n'
        '        self.log = log\n'
        '        self.fail = fail\n\n'
        '    def configure(self, **kwargs: object) -> None:\n'
        '        self.log.append((self.name, kwargs))\n'
        '        if self.fail:\n'
        '            raise feedback.tk.TclError(f"{self.name} failed")\n\n\n'
        'def test_begin_feedback_preserves_border_then_cursor_order() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    source = FakeWidget("source", log)\n'
        '    root = FakeWidget("root", log)\n\n'
        '    feedback.begin_drag_feedback(root, source)  # type: ignore[arg-type]\n\n'
        '    assert log == [\n'
        '        (\n'
        '            "source",\n'
        '            {\n'
        '                "highlightbackground": feedback.BORDER_DRAG_SOURCE,\n'
        '                "highlightcolor": feedback.BORDER_DRAG_SOURCE,\n'
        '            },\n'
        '        ),\n'
        '        ("root", {"cursor": "fleur"}),\n'
        '    ]\n\n\n'
        'def test_begin_border_error_does_not_block_cursor() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    feedback.begin_drag_feedback(\n'
        '        FakeWidget("root", log),  # type: ignore[arg-type]\n'
        '        FakeWidget("source", log, fail=True),  # type: ignore[arg-type]\n'
        '    )\n'
        '    assert log[-1] == ("root", {"cursor": "fleur"})\n\n\n'
        'def test_begin_cursor_tcl_error_is_best_effort() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    feedback.begin_drag_feedback(\n'
        '        FakeWidget("root", log, fail=True),  # type: ignore[arg-type]\n'
        '        FakeWidget("source", log),  # type: ignore[arg-type]\n'
        '    )\n'
        '    assert len(log) == 2\n\n\n'
        'def test_previous_target_clears_only_when_object_changes() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    previous = FakeWidget("previous", log)\n'
        '    next_target = FakeWidget("next", log)\n\n'
        '    feedback.clear_previous_drop_target(None, next_target)  # type: ignore[arg-type]\n'
        '    feedback.clear_previous_drop_target(previous, previous)  # type: ignore[arg-type]\n'
        '    assert log == []\n\n'
        '    feedback.clear_previous_drop_target(\n'
        '        previous,  # type: ignore[arg-type]\n'
        '        next_target,  # type: ignore[arg-type]\n'
        '    )\n'
        '    assert log == [\n'
        '        (\n'
        '            "previous",\n'
        '            {\n'
        '                "highlightbackground": feedback.BORDER_NORMAL,\n'
        '                "highlightcolor": feedback.BORDER_NORMAL,\n'
        '            },\n'
        '        )\n'
        '    ]\n\n\n'
        'def test_show_drop_target_uses_exact_color() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    feedback.show_drop_target(FakeWidget("target", log))  # type: ignore[arg-type]\n'
        '    assert log == [\n'
        '        (\n'
        '            "target",\n'
        '            {\n'
        '                "highlightbackground": feedback.BORDER_DROP_TARGET,\n'
        '                "highlightcolor": feedback.BORDER_DROP_TARGET,\n'
        '            },\n'
        '        )\n'
        '    ]\n\n\n'
        'def test_clear_tiles_preserves_source_then_target_order() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    feedback.clear_drag_tile_feedback(\n'
        '        FakeWidget("source", log),  # type: ignore[arg-type]\n'
        '        FakeWidget("target", log),  # type: ignore[arg-type]\n'
        '    )\n'
        '    assert [entry[0] for entry in log] == ["source", "target"]\n'
        '    assert all(\n'
        '        entry[1]\n'
        '        == {\n'
        '            "highlightbackground": feedback.BORDER_NORMAL,\n'
        '            "highlightcolor": feedback.BORDER_NORMAL,\n'
        '        }\n'
        '        for entry in log\n'
        '    )\n\n\n'
        'def test_clear_without_target_only_resets_source() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    feedback.clear_drag_tile_feedback(\n'
        '        FakeWidget("source", log),  # type: ignore[arg-type]\n'
        '        None,\n'
        '    )\n'
        '    assert [entry[0] for entry in log] == ["source"]\n\n\n'
        'def test_clear_source_error_does_not_block_target() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    feedback.clear_drag_tile_feedback(\n'
        '        FakeWidget("source", log, fail=True),  # type: ignore[arg-type]\n'
        '        FakeWidget("target", log),  # type: ignore[arg-type]\n'
        '    )\n'
        '    assert [entry[0] for entry in log] == ["source", "target"]\n\n\n'
        'def test_reset_cursor_and_expected_errors_are_best_effort() -> None:\n'
        '    log: list[tuple[object, ...]] = []\n'
        '    feedback.reset_drag_cursor(FakeWidget("root", log))  # type: ignore[arg-type]\n'
        '    assert log == [("root", {"cursor": ""})]\n\n'
        '    feedback.reset_drag_cursor(FakeWidget("broken", [], fail=True))  # type: ignore[arg-type]\n'
        '    feedback.reset_drag_cursor(SimpleNamespace())  # type: ignore[arg-type]\n\n\n'
        'def test_adapter_has_no_application_or_state_imports() -> None:\n'
        '    path = (\n'
        '        Path(__file__).resolve().parents[1]\n'
        '        / "giclee_app"\n'
        '        / "launcher_tk_drag_feedback.py"\n'
        '    )\n'
        '    source = path.read_text(encoding="utf-8")\n'
        '    tree = ast.parse(source)\n'
        '    imports: set[str] = set()\n'
        '    for node in ast.walk(tree):\n'
        '        if isinstance(node, ast.Import):\n'
        '            imports.update(alias.name for alias in node.names)\n'
        '        elif isinstance(node, ast.ImportFrom) and node.module:\n'
        '            imports.add(node.module)\n\n'
        '    assert imports == {"__future__", "tkinter"}\n'
        '    assert "_DragState" not in source\n'
        '    assert "DragDropCategoryGicleeApp" not in source\n'
        '    assert "Komponenty" not in source\n\n\n'
        'class TrackingState:\n'
        '    def __init__(self, target, log: list[object]) -> None:\n'
        '        self._target = target\n'
        '        self._after = False\n'
        '        self.log = log\n\n'
        '    @property\n'
        '    def target(self):\n'
        '        return self._target\n\n'
        '    @target.setter\n'
        '    def target(self, value) -> None:\n'
        '        self.log.append(("assign-target", value))\n'
        '        self._target = value\n\n'
        '    @property\n'
        '    def after(self) -> bool:\n'
        '        return self._after\n\n'
        '    @after.setter\n'
        '    def after(self, value: bool) -> None:\n'
        '        self.log.append(("assign-after", value))\n'
        '        self._after = value\n\n\n'
        'def test_set_drop_target_preserves_orchestration_order(monkeypatch) -> None:\n'
        '    log: list[object] = []\n'
        '    previous = object()\n'
        '    target = object()\n'
        '    state = TrackingState(previous, log)\n'
        '    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)\n\n'
        '    monkeypatch.setattr(\n'
        '        dnd,\n'
        '        "clear_previous_drop_target",\n'
        '        lambda old, new: log.append(("clear-previous", old, new)),\n'
        '    )\n'
        '    monkeypatch.setattr(\n'
        '        app,\n'
        '        "_drop_after",\n'
        '        lambda current, x, y: log.append(("drop-after", current, x, y)) or True,\n'
        '    )\n'
        '    monkeypatch.setattr(\n'
        '        dnd,\n'
        '        "show_drop_target",\n'
        '        lambda current: log.append(("show-target", current)),\n'
        '    )\n\n'
        '    app._set_drop_target(state, target, 11, 22)  # type: ignore[arg-type]\n\n'
        '    assert log == [\n'
        '        ("clear-previous", previous, target),\n'
        '        ("assign-target", target),\n'
        '        ("drop-after", target, 11, 22),\n'
        '        ("assign-after", True),\n'
        '        ("show-target", target),\n'
        '    ]\n\n\n'
        'def test_none_target_zeros_after_without_show(monkeypatch) -> None:\n'
        '    log: list[object] = []\n'
        '    state = TrackingState(object(), log)\n'
        '    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)\n'
        '    monkeypatch.setattr(\n'
        '        dnd,\n'
        '        "clear_previous_drop_target",\n'
        '        lambda old, new: log.append(("clear-previous", old, new)),\n'
        '    )\n'
        '    monkeypatch.setattr(\n'
        '        dnd,\n'
        '        "show_drop_target",\n'
        '        lambda current: pytest.fail("target feedback must not be shown"),\n'
        '    )\n\n'
        '    app._set_drop_target(state, None, 0, 0)  # type: ignore[arg-type]\n'
        '    assert state.target is None\n'
        '    assert state.after is False\n'
        '    assert [entry[0] for entry in log] == [\n'
        '        "clear-previous",\n'
        '        "assign-target",\n'
        '        "assign-after",\n'
        '    ]\n\n\n'
        'def test_clear_state_cleans_tiles_then_nulls_state_then_cursor(monkeypatch) -> None:\n'
        '    events: list[object] = []\n'
        '    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)\n'
        '    app.root = object()\n'
        '    state = SimpleNamespace(source=object(), target=object())\n'
        '    app._drag_state = state\n\n'
        '    monkeypatch.setattr(\n'
        '        dnd,\n'
        '        "clear_drag_tile_feedback",\n'
        '        lambda source, target: events.append(("clear-tiles", source, target)),\n'
        '    )\n'
        '    monkeypatch.setattr(\n'
        '        dnd,\n'
        '        "reset_drag_cursor",\n'
        '        lambda root: events.append(("reset-cursor", app._drag_state, root)),\n'
        '    )\n\n'
        '    app._clear_drag_state()\n'
        '    assert events == [\n'
        '        ("clear-tiles", state.source, state.target),\n'
        '        ("reset-cursor", None, app.root),\n'
        '    ]\n'
        '    assert app._drag_state is None\n\n\n'
        'def test_clear_without_state_still_resets_cursor(monkeypatch) -> None:\n'
        '    calls: list[object] = []\n'
        '    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)\n'
        '    app.root = object()\n'
        '    app._drag_state = None\n'
        '    monkeypatch.setattr(\n'
        '        dnd,\n'
        '        "clear_drag_tile_feedback",\n'
        '        lambda *_args: pytest.fail("no tiles should be cleared"),\n'
        '    )\n'
        '    monkeypatch.setattr(dnd, "reset_drag_cursor", lambda root: calls.append(root))\n\n'
        '    app._clear_drag_state()\n'
        '    assert calls == [app.root]\n\n\n'
        'def test_launcher_delegates_feedback_without_duplicating_constants() -> None:\n'
        '    path = (\n'
        '        Path(__file__).resolve().parents[1]\n'
        '        / "giclee_app"\n'
        '        / "dragdrop_category_launcher.py"\n'
        '    )\n'
        '    source = path.read_text(encoding="utf-8")\n'
        '    assert "begin_drag_feedback(" in source\n'
        '    assert "clear_previous_drop_target(" in source\n'
        '    assert "show_drop_target(" in source\n'
        '    assert "clear_drag_tile_feedback(" in source\n'
        '    assert "reset_drag_cursor(" in source\n'
        '    assert "def _set_tile_border" not in source\n'
        '    assert "#dcdce2" not in source\n'
        '    assert "#7b8798" not in source\n'
        '    assert "#496a9b" not in source\n''',
        encoding="utf-8",
    )

    replace_exact(
        launcher_docs,
        "**LC-3G Tk drag target adapter:** `launcher_tk_drag_targets.py` izoluje direct widget lookup, traversal master, odczyt geometrii i nearest fallback. `DragDropCategoryGicleeApp` zachowuje stan gestu, feedback, auto-scroll, decyzję after i persistence.\n\n---",
        "**LC-3G Tk drag target adapter:** `launcher_tk_drag_targets.py` izoluje direct widget lookup, traversal master, odczyt geometrii i nearest fallback. `DragDropCategoryGicleeApp` zachowuje stan gestu, feedback, auto-scroll, decyzję after i persistence.\n\n"
        "**LC-3H Tk drag visual feedback adapter:** `launcher_tk_drag_feedback.py` izoluje kolory ramek oraz kursor `fleur`/reset. `DragDropCategoryGicleeApp` zachowuje `_DragState`, target, decyzję `after`, auto-scroll i persistence.\n\n---",
    )
    replace_exact(
        contract,
        "**Status:** fresh reconnaissance · contract freeze  ",
        "**Status:** LC-3H implemented  ",
    )


if __name__ == "__main__":
    main()
