from __future__ import annotations

from pathlib import Path


APP = Path("cursor-api/giclee_app")


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    dragdrop = APP / "dragdrop_category_launcher.py"

    replace_exact(
        dragdrop,
        "from dataclasses import dataclass\nimport math\nimport tkinter as tk\n",
        "from dataclasses import dataclass\nimport tkinter as tk\n",
    )
    replace_exact(
        dragdrop,
        "from .launcher_layout import resolve_sections, save_layout\n"
        "from .launcher_tile_order import reorder_relative, replace_subset_order\n",
        "from .launcher_drag_geometry import (\n"
        "    DragPoint,\n"
        "    DragRect,\n"
        "    drag_threshold_reached,\n"
        "    drop_after,\n"
        "    nearest_rect_index,\n"
        "    point_inside,\n"
        ")\n"
        "from .launcher_layout import resolve_sections, save_layout\n"
        "from .launcher_tile_order import reorder_relative, replace_subset_order\n",
    )
    replace_exact(
        dragdrop,
        "_DRAG_THRESHOLD_PX = 8\n"
        "_BORDER_NORMAL = \"#dcdce2\"\n",
        "_DRAG_THRESHOLD_PX = 8\n"
        "_DROP_VERTICAL_RATIO = 0.22\n"
        "_BORDER_NORMAL = \"#dcdce2\"\n",
    )
    replace_exact(
        dragdrop,
        '''        distance = math.hypot(
            int(event.x_root) - state.start_x_root,
            int(event.y_root) - state.start_y_root,
        )
        if not state.dragging and distance < _DRAG_THRESHOLD_PX:
            return None
''',
        '''        threshold_reached = drag_threshold_reached(
            DragPoint(state.start_x_root, state.start_y_root),
            DragPoint(int(event.x_root), int(event.y_root)),
            _DRAG_THRESHOLD_PX,
        )
        if not state.dragging and not threshold_reached:
            return None
''',
    )
    replace_exact(
        dragdrop,
        '''        candidates: list[tk.Frame] = []
        for tile in self._dnd_tiles:
            if tile is exclude or getattr(tile, "_launcher_dnd_kind", None) != kind:
                continue
            try:
                if tile.winfo_exists():
                    candidates.append(tile)
            except tk.TclError:
                continue
        if not candidates:
            return None

        def distance(tile: tk.Frame) -> float:
            try:
                center_x = tile.winfo_rootx() + tile.winfo_width() / 2
                center_y = tile.winfo_rooty() + tile.winfo_height() / 2
            except tk.TclError:
                return float("inf")
            return math.hypot(x_root - center_x, y_root - center_y)

        return min(candidates, key=distance)
''',
        '''        candidates: list[tk.Frame] = []
        candidate_rects: list[DragRect] = []
        for tile in self._dnd_tiles:
            if tile is exclude or getattr(tile, "_launcher_dnd_kind", None) != kind:
                continue
            try:
                exists = bool(tile.winfo_exists())
            except tk.TclError:
                continue
            if not exists:
                continue
            rect = self._widget_drag_rect(tile)
            if rect is None:
                continue
            candidates.append(tile)
            candidate_rects.append(rect)

        index = nearest_rect_index(
            candidate_rects,
            DragPoint(x_root, y_root),
        )
        return candidates[index] if index is not None else None
''',
    )
    replace_exact(
        dragdrop,
        '''    @staticmethod
    def _point_inside_tile(tile: tk.Frame, x_root: int, y_root: int) -> bool:
        try:
            left = tile.winfo_rootx()
            top = tile.winfo_rooty()
            right = left + tile.winfo_width()
            bottom = top + tile.winfo_height()
        except tk.TclError:
            return False
        return left <= x_root < right and top <= y_root < bottom

    def _pointer_over_tiles_area(self, x_root: int, y_root: int) -> bool:
        try:
            left = self.canvas.winfo_rootx()
            top = self.canvas.winfo_rooty()
            right = left + self.canvas.winfo_width()
            bottom = top + self.canvas.winfo_height()
        except tk.TclError:
            return False
        return left <= x_root < right and top <= y_root < bottom
''',
        '''    @staticmethod
    def _widget_drag_rect(widget: tk.Misc) -> DragRect | None:
        try:
            return DragRect(
                left=widget.winfo_rootx(),
                top=widget.winfo_rooty(),
                width=widget.winfo_width(),
                height=widget.winfo_height(),
            )
        except tk.TclError:
            return None

    @staticmethod
    def _point_inside_tile(tile: tk.Frame, x_root: int, y_root: int) -> bool:
        rect = DragDropCategoryGicleeApp._widget_drag_rect(tile)
        if rect is None:
            return False
        return point_inside(rect, DragPoint(x_root, y_root))

    def _pointer_over_tiles_area(self, x_root: int, y_root: int) -> bool:
        rect = self._widget_drag_rect(self.canvas)
        if rect is None:
            return False
        return point_inside(rect, DragPoint(x_root, y_root))
''',
    )
    replace_exact(
        dragdrop,
        '''    @staticmethod
    def _drop_after(target: tk.Frame, x_root: int, y_root: int) -> bool:
        try:
            center_x = target.winfo_rootx() + target.winfo_width() / 2
            center_y = target.winfo_rooty() + target.winfo_height() / 2
            height = max(1, target.winfo_height())
        except tk.TclError:
            return False
        vertical_delta = y_root - center_y
        if abs(vertical_delta) > height * 0.22:
            return vertical_delta > 0
        return x_root > center_x
''',
        '''    @staticmethod
    def _drop_after(target: tk.Frame, x_root: int, y_root: int) -> bool:
        rect = DragDropCategoryGicleeApp._widget_drag_rect(target)
        if rect is None:
            return False
        return drop_after(
            rect,
            DragPoint(x_root, y_root),
            vertical_ratio=_DROP_VERTICAL_RATIO,
        )
''',
    )

    replace_exact(
        APP / "docs" / "launcher.md",
        "**LC-3C Tk binding adapter:** `launcher_tk_shortcut_bindings.py` izoluje class binding, rekursywne bindtagi i bezpośredni fallback bez duplikatów. Lifecycle, fokus, aktywacja i handler eventu pozostają w `OptionsCategoryGicleeApp`.\n\n---\n",
        "**LC-3C Tk binding adapter:** `launcher_tk_shortcut_bindings.py` izoluje class binding, rekursywne bindtagi i bezpośredni fallback bez duplikatów. Lifecycle, fokus, aktywacja i handler eventu pozostają w `OptionsCategoryGicleeApp`.\n\n"
        "**LC-3D pure drag geometry:** `launcher_drag_geometry.py` izoluje próg ruchu, prostokąty, hit-testing, `drop_after` i wybór najbliższego celu. Stan gestu, eventy Tk, feedback, auto-scroll i zapis pozostają w `DragDropCategoryGicleeApp`.\n\n---\n",
    )
    replace_exact(
        APP / "docs" / "launcher-composition-lc3d-contract.md",
        "**Status:** fresh reconnaissance · contract freeze  ",
        "**Status:** LC-3D implemented",
    )


if __name__ == "__main__":
    main()
