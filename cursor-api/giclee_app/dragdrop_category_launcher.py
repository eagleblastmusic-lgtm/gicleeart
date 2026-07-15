"""Launcher kategorii z trwałym drag-and-drop kafelków."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from collections.abc import Callable

from . import launcher as _launcher
from .category_launcher import category_display_title, category_map
from .component_loader import Component
from .launcher_drag_geometry import (
    DragPoint,
    DragRect,
    drag_threshold_reached,
    drop_after,
    nearest_rect_index,
    point_inside,
)
from .launcher_drag_gesture import (
    DragMotionKind,
    DragReleaseKind,
    resolve_drag_motion,
    resolve_drag_release,
)
from .launcher_layout import resolve_sections, save_layout
from .launcher_tile_order import reorder_relative, replace_subset_order
from .options_category_launcher import OptionsCategoryGicleeApp


_DRAG_THRESHOLD_PX = 8
_DROP_VERTICAL_RATIO = 0.22
_BORDER_NORMAL = "#dcdce2"
_BORDER_DRAG_SOURCE = "#7b8798"
_BORDER_DROP_TARGET = "#496a9b"


@dataclass
class _DragState:
    kind: str
    key: str
    source: tk.Frame
    start_x_root: int
    start_y_root: int
    activate: Callable[[], None]
    dragging: bool = False
    target: tk.Frame | None = None
    after: bool = False


class DragDropCategoryGicleeApp(OptionsCategoryGicleeApp):
    """Pełny launcher z trwałym porządkowaniem kategorii i komponentów."""

    def __init__(self, root: tk.Tk) -> None:
        self._dnd_tiles: list[tk.Frame] = []
        self._drag_state: _DragState | None = None
        super().__init__(root)

    def _render_tiles(self) -> None:
        self._dnd_tiles = []
        self._clear_drag_state()
        super()._render_tiles()

    def _build_category_tile(
        self,
        parent: tk.Misc,
        title: str,
        count: int,
    ) -> tk.Frame:
        tile = super()._build_category_tile(parent, title, count)
        self._enable_tile_drag(
            tile,
            kind="category",
            key=title,
            activate=lambda selected=title: self._open_category(selected),
        )
        return tile

    def _build_tile(self, parent: tk.Misc, comp: Component) -> tk.Frame:
        tile = super()._build_tile(parent, comp)
        self._enable_tile_drag(
            tile,
            kind="component",
            key=comp.folder_name,
            activate=lambda selected=comp: self._launch(selected),
        )
        return tile

    def _enable_tile_drag(
        self,
        tile: tk.Frame,
        *,
        kind: str,
        key: str,
        activate: Callable[[], None],
    ) -> None:
        setattr(tile, "_launcher_dnd_kind", kind)
        setattr(tile, "_launcher_dnd_key", key)
        self._dnd_tiles.append(tile)

        def bind_recursive(widget: tk.Widget) -> None:
            # Bazowe kafelki uruchamiały akcję już na Button-1. Przy DnD klik
            # wykonujemy dopiero na zwolnieniu przycisku, o ile nie rozpoczęto drag.
            try:
                widget.unbind("<Button-1>")
            except tk.TclError:
                pass
            widget.bind(
                "<ButtonPress-1>",
                lambda event: self._on_tile_press(event, tile, kind, key, activate),
                add="+",
            )
            widget.bind("<B1-Motion>", self._on_tile_motion, add="+")
            widget.bind("<ButtonRelease-1>", self._on_tile_release, add="+")
            try:
                widget.configure(cursor="hand2")
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(tile)

    def _on_tile_press(
        self,
        event: tk.Event,
        tile: tk.Frame,
        kind: str,
        key: str,
        activate: Callable[[], None],
    ) -> str | None:
        self._clear_drag_state()
        self._drag_state = _DragState(
            kind=kind,
            key=key,
            source=tile,
            start_x_root=int(event.x_root),
            start_y_root=int(event.y_root),
            activate=activate,
        )
        return None

    def _on_tile_motion(self, event: tk.Event) -> str | None:
        state = self._drag_state
        if state is None:
            return None

        threshold_reached = drag_threshold_reached(
            DragPoint(state.start_x_root, state.start_y_root),
            DragPoint(int(event.x_root), int(event.y_root)),
            _DRAG_THRESHOLD_PX,
        )
        motion = resolve_drag_motion(
            dragging=state.dragging,
            threshold_reached=threshold_reached,
        )
        if motion is DragMotionKind.WAITING:
            return None

        if motion is DragMotionKind.START:
            state.dragging = True
            self._set_tile_border(state.source, _BORDER_DRAG_SOURCE)
            try:
                self.root.configure(cursor="fleur")
            except tk.TclError:
                pass

        self._auto_scroll_drag(int(event.y_root))
        target = self._find_drop_target(
            state.kind,
            int(event.x_root),
            int(event.y_root),
            exclude=state.source,
        )
        self._set_drop_target(state, target, int(event.x_root), int(event.y_root))
        return "break"

    def _on_tile_release(self, event: tk.Event) -> str | None:
        state = self._drag_state
        if state is None:
            return None

        if not state.dragging:
            decision = resolve_drag_release(
                dragging=False,
                drag_kind=state.kind,
                source_key=state.key,
                target_key="",
                after=False,
            )
            self._drag_state = None
            if decision.kind is DragReleaseKind.ACTIVATE:
                state.activate()
            return "break"

        target = state.target or self._find_drop_target(
            state.kind,
            int(event.x_root),
            int(event.y_root),
            exclude=state.source,
        )
        after = state.after
        if target is not None and state.target is None:
            after = self._drop_after(target, int(event.x_root), int(event.y_root))

        target_key = str(getattr(target, "_launcher_dnd_key", "")) if target is not None else ""
        decision = resolve_drag_release(
            dragging=True,
            drag_kind=state.kind,
            source_key=state.key,
            target_key=target_key,
            after=after,
        )
        self._clear_drag_state()

        if decision.kind is DragReleaseKind.REORDER:
            if decision.drag_kind == "category":
                self._reorder_category(
                    decision.source_key,
                    decision.target_key,
                    after=decision.after,
                )
            elif decision.drag_kind == "component":
                self._reorder_component(
                    decision.source_key,
                    decision.target_key,
                    after=decision.after,
                )
        return "break"

    def _find_drop_target(
        self,
        kind: str,
        x_root: int,
        y_root: int,
        *,
        exclude: tk.Frame,
    ) -> tk.Frame | None:
        # Ruch ręki wewnątrz źródłowego kafelka nie może sam z siebie wybrać
        # najbliższego sąsiada i przypadkowo zmienić kolejności.
        if self._point_inside_tile(exclude, x_root, y_root):
            return None

        try:
            widget = self.root.winfo_containing(x_root, y_root)
        except tk.TclError:
            widget = None

        current: tk.Misc | None = widget
        while current is not None:
            if (
                current is not exclude
                and getattr(current, "_launcher_dnd_kind", None) == kind
            ):
                return current if isinstance(current, tk.Frame) else None
            try:
                current = current.master
            except (AttributeError, tk.TclError):
                break

        if not self._pointer_over_tiles_area(x_root, y_root):
            return None

        candidates: list[tk.Frame] = []
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

    @staticmethod
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

    def _set_drop_target(
        self,
        state: _DragState,
        target: tk.Frame | None,
        x_root: int,
        y_root: int,
    ) -> None:
        if state.target is not None and state.target is not target:
            self._set_tile_border(state.target, _BORDER_NORMAL)
        state.target = target
        if target is None:
            state.after = False
            return
        state.after = self._drop_after(target, x_root, y_root)
        self._set_tile_border(target, _BORDER_DROP_TARGET)

    @staticmethod
    def _drop_after(target: tk.Frame, x_root: int, y_root: int) -> bool:
        rect = DragDropCategoryGicleeApp._widget_drag_rect(target)
        if rect is None:
            return False
        return drop_after(
            rect,
            DragPoint(x_root, y_root),
            vertical_ratio=_DROP_VERTICAL_RATIO,
        )

    @staticmethod
    def _set_tile_border(tile: tk.Frame, color: str) -> None:
        try:
            tile.configure(highlightbackground=color, highlightcolor=color)
        except tk.TclError:
            pass

    def _clear_drag_state(self) -> None:
        state = self._drag_state
        if state is not None:
            self._set_tile_border(state.source, _BORDER_NORMAL)
            if state.target is not None:
                self._set_tile_border(state.target, _BORDER_NORMAL)
        self._drag_state = None
        try:
            self.root.configure(cursor="")
        except (AttributeError, tk.TclError):
            pass

    def _auto_scroll_drag(self, y_root: int) -> None:
        try:
            top = self.canvas.winfo_rooty()
            bottom = top + self.canvas.winfo_height()
        except tk.TclError:
            return
        margin = 42
        if y_root < top + margin:
            self.canvas.yview_scroll(-1, "units")
        elif y_root > bottom - margin:
            self.canvas.yview_scroll(1, "units")

    def _reorder_category(
        self,
        source: str,
        target: str,
        *,
        after: bool,
    ) -> None:
        sections = resolve_sections(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
        )
        visible_titles = [title for title, _components in sections]
        reordered = reorder_relative(visible_titles, source, target, after=after)
        if reordered == visible_titles:
            return

        existing = self._layout.section_order or visible_titles
        self._layout.section_order = replace_subset_order(existing, reordered)
        save_layout(self._layout)
        self._render_tiles()
        self._finish_navigation_render()
        self.status_var.set("Zapisano nową kolejność kategorii")

    def _reorder_component(
        self,
        source: str,
        target: str,
        *,
        after: bool,
    ) -> None:
        section = self._active_section
        if not section:
            return
        sections = resolve_sections(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
        )
        components = category_map(sections).get(section, [])
        visible_order = [component.folder_name for component in components]
        reordered_visible = reorder_relative(
            visible_order,
            source,
            target,
            after=after,
        )
        if reordered_visible == visible_order:
            return

        all_in_section = [
            entry.folder
            for entry in sorted(
                (
                    entry
                    for entry in self._layout.entries.values()
                    if entry.section == section
                ),
                key=lambda entry: (entry.sort_key, entry.folder.lower()),
            )
        ]
        full_order = replace_subset_order(all_in_section, reordered_visible)
        for index, folder in enumerate(full_order):
            entry = self._layout.entries.get(folder)
            if entry is not None:
                entry.sort_key = index * 10

        save_layout(self._layout)
        self._render_tiles()
        self._finish_navigation_render()
        self.status_var.set(
            f"{category_display_title(section)}: zapisano kolejność kafelków"
        )


def main() -> None:
    """Uruchamia pełny launcher z menu Opcje i drag-and-drop."""

    _launcher.main(app_factory=DragDropCategoryGicleeApp)


if __name__ == "__main__":
    main()
