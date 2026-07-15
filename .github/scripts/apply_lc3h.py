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
    geometry_tests = TESTS / "test_launcher_drag_geometry.py"
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

    replace_exact(
        gesture_tests,
        "from giclee_app import dragdrop_category_launcher as dnd\n",
        "from giclee_app import dragdrop_category_launcher as dnd\n"
        "from giclee_app import launcher_tk_drag_feedback as feedback\n",
    )
    replace_exact(
        gesture_tests,
        "            \"highlightbackground\": dnd._BORDER_DRAG_SOURCE,\n"
        "            \"highlightcolor\": dnd._BORDER_DRAG_SOURCE,\n",
        "            \"highlightbackground\": feedback.BORDER_DRAG_SOURCE,\n"
        "            \"highlightcolor\": feedback.BORDER_DRAG_SOURCE,\n",
    )
    replace_exact(
        gesture_tests,
        "    assert \"state.dragging = True\" in motion\n"
        "    assert \"self._auto_scroll_drag(\" in motion\n",
        "    assert \"state.dragging = True\" in motion\n"
        "    assert \"begin_drag_feedback(\" in motion\n"
        "    assert \"self._auto_scroll_drag(\" in motion\n",
    )
    replace_exact(
        geometry_tests,
        "    assert 'self.root.configure(cursor=\"fleur\")' in motion\n",
        "    assert \"begin_drag_feedback(\" in motion\n",
    )

    replace_exact(
        launcher_docs,
        "**LC-3G Tk drag target adapter:** `launcher_tk_drag_targets.py` izoluje direct widget lookup, traversal master, odczyt geometrii i nearest fallback. `DragDropCategoryGicleeApp` zachowuje stan gestu, feedback, auto-scroll, decyzję after i persistence.\n\n---",
        "**LC-3G Tk drag target adapter:** `launcher_tk_drag_targets.py` izoluje direct widget lookup, traversal master, odczyt geometrii i nearest fallback. `DragDropCategoryGicleeApp` zachowuje stan gestu, feedback, auto-scroll, decyzję after i persistence.\n\n"
        "**LC-3H Tk drag visual feedback adapter:** `launcher_tk_drag_feedback.py` izoluje kolory ramek oraz kursor `fleur`/reset. `DragDropCategoryGicleeApp` zachowuje `_DragState`, target, decyzję `after`, auto-scroll i persistence.\n\n---",
    )
    replace_exact(
        contract,
        "## 7. Allowlista implementacyjna\n\nKod:",
        "## 7. Allowlista implementacyjna\n\n"
        "### Finding z focused validation\n\n"
        "Pierwszy focused run wykazał jedną przestarzałą source assertion w `test_launcher_drag_geometry.py`, która nadal wymagała bezpośredniego `self.root.configure(cursor=\"fleur\")` w launcherze. Po LC-3H odpowiedzialność jest delegowana do `begin_drag_feedback()`. To finding testowy, nie regresja runtime; kontrakt zostaje rozszerzony o ten jeden plik przed jego edycją.\n\n"
        "Kod:",
    )
    replace_exact(
        contract,
        "Testy:\n\n"
        "3. nowy `cursor-api/tests/test_launcher_tk_drag_feedback.py`;\n"
        "4. `cursor-api/tests/test_launcher_drag_gesture.py` — przeniesienie szczegółowych asercji efektów Tk do adaptera i potwierdzenie orchestration klasy.\n\n"
        "Dokumentacja:\n\n"
        "5. `cursor-api/giclee_app/docs/launcher.md`;\n"
        "6. ten kontrakt.\n\n"
        "Finalny implementation PR obejmuje dokładnie sześć plików. Każde rozszerzenie wymaga osobnego findingu i aktualizacji kontraktu przed edycją.",
        "Testy:\n\n"
        "3. nowy `cursor-api/tests/test_launcher_tk_drag_feedback.py`;\n"
        "4. `cursor-api/tests/test_launcher_drag_gesture.py` — przeniesienie szczegółowych asercji efektów Tk do adaptera i potwierdzenie orchestration klasy;\n"
        "5. `cursor-api/tests/test_launcher_drag_geometry.py` — aktualizacja przestarzałej source assertion kursora do delegacji LC-3H.\n\n"
        "Dokumentacja:\n\n"
        "6. `cursor-api/giclee_app/docs/launcher.md`;\n"
        "7. ten kontrakt.\n\n"
        "Finalny implementation PR obejmuje dokładnie siedem plików. Każde dalsze rozszerzenie wymaga osobnego findingu i aktualizacji kontraktu przed edycją.",
    )
    replace_exact(
        contract,
        "- dokładny scope guard sześciu plików;",
        "- dokładny scope guard siedmiu plików;",
    )
    replace_exact(
        contract,
        "- finalny diff obejmuje dokładnie sześć allowlistowanych plików;",
        "- finalny diff obejmuje dokładnie siedem allowlistowanych plików;",
    )
    replace_exact(
        contract,
        "**Status:** fresh reconnaissance · contract freeze  ",
        "**Status:** LC-3H implemented  ",
    )


if __name__ == "__main__":
    main()
