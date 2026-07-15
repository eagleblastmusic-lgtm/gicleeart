from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "cursor-api" / "giclee_app"


def replace_exact(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one match in {path}: found {count}")
    path.write_text(source.replace(old, new), encoding="utf-8")


def main() -> None:
    launcher = APP / "dragdrop_category_launcher.py"
    launcher_docs = APP / "docs" / "launcher.md"
    contract = APP / "docs" / "launcher-composition-lc3j-contract.md"

    replace_exact(
        launcher,
        "from .launcher_drag_geometry import (\n",
        "from .launcher_drag_category_persistence import persist_category_reorder\n"
        "from .launcher_drag_geometry import (\n",
    )
    replace_exact(
        launcher,
        "        visible_titles = [title for title, _components in sections]\n"
        "        reordered = reorder_relative(visible_titles, source, target, after=after)\n"
        "        if reordered == visible_titles:\n"
        "            return\n\n"
        "        existing = self._layout.section_order or visible_titles\n"
        "        self._layout.section_order = replace_subset_order(existing, reordered)\n"
        "        save_layout(self._layout)\n"
        "        self._render_tiles()\n",
        "        visible_titles = [title for title, _components in sections]\n"
        "        changed = persist_category_reorder(\n"
        "            self._layout,\n"
        "            visible_titles,\n"
        "            source,\n"
        "            target,\n"
        "            after=after,\n"
        "        )\n"
        "        if not changed:\n"
        "            return\n\n"
        "        self._render_tiles()\n",
    )
    replace_exact(
        launcher_docs,
        "**LC-3I Tk drag auto-scroll adapter:** `launcher_tk_drag_auto_scroll.py` izoluje geometrię canvasu, margin 42 px i pojedynczy `yview_scroll()`. `DragDropCategoryGicleeApp` zachowuje orchestration motion, target lookup i persistence.\n\n---",
        "**LC-3I Tk drag auto-scroll adapter:** `launcher_tk_drag_auto_scroll.py` izoluje geometrię canvasu, margin 42 px i pojedynczy `yview_scroll()`. `DragDropCategoryGicleeApp` zachowuje orchestration motion, target lookup i persistence.\n\n"
        "**LC-3J category order persistence adapter:** `launcher_drag_category_persistence.py` izoluje zmianę `section_order`, zachowanie niewidocznych slotów i pojedynczy `save_layout()`. `DragDropCategoryGicleeApp` zachowuje resolve widocznych sekcji, rerender, reset nawigacji i status.\n\n---",
    )
    replace_exact(
        contract,
        "Status: fresh reconnaissance · contract freeze",
        "Status: LC-3J implemented",
    )


if __name__ == "__main__":
    main()
