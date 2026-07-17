"""Widget cache layer for classic launcher category navigation."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk

from . import launcher as _launcher
from .category_navigation import resolve_category_navigation
from .dragdrop_category_launcher import DragDropCategoryGicleeApp
from .launcher_navigation_cache import (
    NavigationViewCache,
    navigation_view_key,
    navigation_view_signature,
)


_VIEW_BACKGROUND = "#f4f4f7"


@dataclass(frozen=True)
class _CachedNavigationView:
    frame: tk.Frame
    dnd_tiles: tuple[tk.Frame, ...]
    window_title: str
    subtitle: str


class CachedNavigationGicleeApp(DragDropCategoryGicleeApp):
    """Reuse unchanged category screens instead of rebuilding every widget."""

    def __init__(self, root: tk.Tk) -> None:
        self._navigation_views: NavigationViewCache[_CachedNavigationView] = (
            NavigationViewCache()
        )
        self._navigation_cache_host: tk.Frame | None = None
        self._active_navigation_frame: tk.Frame | None = None
        super().__init__(root)

    def _render_tiles(self) -> None:
        host = self._navigation_cache_host
        if host is None:
            host = self.tiles_frame
            self._navigation_cache_host = host

        plan = resolve_category_navigation(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
            active_section=self._active_section,
        )
        self._active_section = plan.active_section
        key = navigation_view_key(plan)
        signature = navigation_view_signature(plan)

        self._tile_hover.clear_active()
        self._clear_drag_state()

        cached = self._navigation_views.get(key, signature)
        if cached is not None and self._cached_view_exists(cached):
            self._activate_cached_view(cached)
            return

        stale = self._navigation_views.pop(key)
        if stale is not None:
            self._destroy_cached_view(stale)

        frame = tk.Frame(host, bg=_VIEW_BACKGROUND)
        self._hide_active_navigation_frame()
        frame.pack(fill="both", expand=True)
        self.tiles_frame = frame

        try:
            super()._render_tiles()
        except Exception:
            frame.destroy()
            self.tiles_frame = host
            self._active_navigation_frame = None
            raise

        built = _CachedNavigationView(
            frame=frame,
            dnd_tiles=tuple(self._dnd_tiles),
            window_title=self._read_window_title(),
            subtitle=self._read_subtitle(),
        )
        replaced = self._navigation_views.put(key, signature, built)
        if replaced is not None and replaced is not stale:
            self._destroy_cached_view(replaced)
        self._active_navigation_frame = frame

    def _activate_cached_view(self, cached: _CachedNavigationView) -> None:
        self._hide_active_navigation_frame()
        cached.frame.pack(fill="both", expand=True)
        self.tiles_frame = cached.frame
        self._active_navigation_frame = cached.frame
        self._dnd_tiles = list(cached.dnd_tiles)
        try:
            self.root.title(cached.window_title)
        except tk.TclError:
            pass
        self._set_subtitle(cached.subtitle)

    def _hide_active_navigation_frame(self) -> None:
        frame = self._active_navigation_frame
        if frame is None:
            return
        try:
            if frame.winfo_exists():
                frame.pack_forget()
        except tk.TclError:
            pass

    @staticmethod
    def _cached_view_exists(cached: _CachedNavigationView) -> bool:
        try:
            return bool(cached.frame.winfo_exists())
        except tk.TclError:
            return False

    @staticmethod
    def _destroy_cached_view(cached: _CachedNavigationView) -> None:
        try:
            if cached.frame.winfo_exists():
                cached.frame.destroy()
        except tk.TclError:
            pass

    def _read_window_title(self) -> str:
        try:
            return str(self.root.title())
        except tk.TclError:
            return ""

    def _read_subtitle(self) -> str:
        widget = self._subtitle_widget
        if widget is None:
            return ""
        try:
            return str(widget.cget("text"))
        except (tk.TclError, TypeError):
            return ""


def main() -> None:
    """Run the classic launcher with navigation view caching enabled."""

    _launcher.main(app_factory=CachedNavigationGicleeApp)


__all__ = ["CachedNavigationGicleeApp", "main"]
