"""Launcher kategorii z trwałym drag-and-drop kafelków."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from collections.abc import Callable

from . import launcher as _launcher
from .category_launcher import category_display_title, category_map
from .component_loader import Component
from .launcher_drag_category_persistence import persist_category_reorder
from .launcher_drag_geometry import (
    DragPoint,
    drag_threshold_reached,
    drop_after,
)
from .launcher_tk_drag_auto_scroll import auto_scroll_drag
from .launcher_tk_drag_feedback import (
    begin_drag_feedback,
    clear_drag_tile_feedback,
    clear_previous_drop_target,
    reset_drag_cursor,
    show_drop_target,
)
from .launcher_tk_drag_targets import find_drop_target, widget_drag_rect
from .launcher_drag_gesture import (
    DragMotionKind,
    DragReleaseKind,
    resolve_drag_motion,
    resolve_drag_release,
)
from .launcher_layout import resolve_sections, save_layout
from .launcher_tk_drag_bindings import install_tile_drag_bindings
from .launcher_tile_order import reorder_relative, replace_subset_order
from .options_category_launcher import OptionsCategoryGicleeApp


_DRAG_THRESHOLD_PX = 8
_DROP_VERTICAL_RATIO = 0.22


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
        install_tile_drag_bindings(
            tile,
            on_press=lambda event: self._on_tile_press(
                event, tile, kind, key, activate
            ),
            on_motion=self._on_tile_motion,
            on_release=self._on_tile_release,
        )

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
            begin_drag_feedback(self.root, state.source)

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
        return find_drop_target(
            self.root,
            tiles_area=self.canvas,
            tiles=self._dnd_tiles,
            drag_kind=kind,
            point=DragPoint(x_root, y_root),
            exclude=exclude,
        )

    def _set_drop_target(
        self,
        state: _DragState,
        target: tk.Frame | None,
        x_root: int,
        y_root: int,
    ) -> None:
        clear_previous_drop_target(state.target, target)
        state.target = target
        if target is None:
            state.after = False
            return
        state.after = self._drop_after(target, x_root, y_root)
        show_drop_target(target)

    @staticmethod
    def _drop_after(target: tk.Frame, x_root: int, y_root: int) -> bool:
        rect = widget_drag_rect(target)
        if rect is None:
            return False
        return drop_after(
            rect,
            DragPoint(x_root, y_root),
            vertical_ratio=_DROP_VERTICAL_RATIO,
        )

    def _clear_drag_state(self) -> None:
        state = self._drag_state
        if state is not None:
            clear_drag_tile_feedback(state.source, state.target)
        self._drag_state = None
        reset_drag_cursor(self.root)

    def _auto_scroll_drag(self, y_root: int) -> None:
        auto_scroll_drag(self.canvas, y_root)

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
        changed = persist_category_reorder(
            self._layout,
            visible_titles,
            source,
            target,
            after=after,
        )
        if not changed:
            return

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
