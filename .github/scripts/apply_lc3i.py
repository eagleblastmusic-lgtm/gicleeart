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
    contract = APP / "docs" / "launcher-composition-lc3i-contract.md"

    replace_exact(
        launcher,
        "from .launcher_tk_drag_feedback import (\n",
        "from .launcher_tk_drag_auto_scroll import auto_scroll_drag\n"
        "from .launcher_tk_drag_feedback import (\n",
    )
    replace_exact(
        launcher,
        "    def _auto_scroll_drag(self, y_root: int) -> None:\n"
        "        try:\n"
        "            top = self.canvas.winfo_rooty()\n"
        "            bottom = top + self.canvas.winfo_height()\n"
        "        except tk.TclError:\n"
        "            return\n"
        "        margin = 42\n"
        "        if y_root < top + margin:\n"
        "            self.canvas.yview_scroll(-1, \"units\")\n"
        "        elif y_root > bottom - margin:\n"
        "            self.canvas.yview_scroll(1, \"units\")\n",
        "    def _auto_scroll_drag(self, y_root: int) -> None:\n"
        "        auto_scroll_drag(self.canvas, y_root)\n",
    )

    replace_exact(
        gesture_tests,
        "    assert \"self._reorder_component(\" in release\n",
        "    assert \"self._reorder_component(\" in release\n\n\n"
        "def test_auto_scroll_wrapper_delegates_canvas_and_y(monkeypatch) -> None:\n"
        "    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)\n"
        "    app.canvas = object()\n"
        "    calls: list[tuple[object, int]] = []\n"
        "    monkeypatch.setattr(\n"
        "        dnd,\n"
        "        \"auto_scroll_drag\",\n"
        "        lambda canvas, y_root: calls.append((canvas, y_root)),\n"
        "    )\n\n"
        "    app._auto_scroll_drag(123)\n\n"
        "    assert calls == [(app.canvas, 123)]\n\n"
        "    path = (\n"
        "        Path(__file__).resolve().parents[1]\n"
        "        / \"giclee_app\"\n"
        "        / \"dragdrop_category_launcher.py\"\n"
        "    )\n"
        "    source = path.read_text(encoding=\"utf-8\")\n"
        "    wrapper = source.split(\"def _auto_scroll_drag\", 1)[1].split(\"\\n    def \", 1)[0]\n"
        "    assert \"auto_scroll_drag(self.canvas, y_root)\" in wrapper\n"
        "    assert \"yview_scroll\" not in wrapper\n"
        "    assert \"42\" not in wrapper\n",
    )

    replace_exact(
        launcher_docs,
        "**LC-3H Tk drag visual feedback adapter:** `launcher_tk_drag_feedback.py` izoluje kolory ramek oraz kursor `fleur`/reset. `DragDropCategoryGicleeApp` zachowuje `_DragState`, target, decyzję `after`, auto-scroll i persistence.\n\n---",
        "**LC-3H Tk drag visual feedback adapter:** `launcher_tk_drag_feedback.py` izoluje kolory ramek oraz kursor `fleur`/reset. `DragDropCategoryGicleeApp` zachowuje `_DragState`, target, decyzję `after`, auto-scroll i persistence.\n\n"
        "**LC-3I Tk drag auto-scroll adapter:** `launcher_tk_drag_auto_scroll.py` izoluje geometrię canvasu, margin 42 px i pojedynczy `yview_scroll()`. `DragDropCategoryGicleeApp` zachowuje orchestration motion, target lookup i persistence.\n\n---",
    )
    replace_exact(
        contract,
        "**Status:** fresh reconnaissance · contract freeze  ",
        "**Status:** LC-3I implemented  ",
    )


if __name__ == "__main__":
    main()
