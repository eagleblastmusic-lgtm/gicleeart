"""GicleeApp Studio — shell CustomTkinter (preview obok klasycznego launchera)."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app import __version__
from giclee_app.component_loader import Component
from giclee_app.studio.categories import category_label
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.studio.state import StudioState

from .ui.component_hub import ComponentHubView
from .ui.dashboard import DashboardView
from .ui.inline_host import InlineHostView
from .ui.sidebar import Sidebar
from .ui.topbar import Topbar
from .ui import theme


class GicleeAppStudio(ctk.CTk):
    """Preview shell — bez pollingów / backupów / synców z launcher.py."""

    def __init__(self) -> None:
        super().__init__()
        self._component_index = StudioComponentIndex.build()
        self._studio_state = StudioState.load()
        if self._studio_state.prune(self._component_index.by_folder.keys()):
            self._studio_state.save()

        self.title(f"{theme.APP_TITLE} · v{__version__} · {theme.PREVIEW_BADGE}")
        self.configure(fg_color=theme.AppBg)
        w, h = theme.WindowDefault
        self.geometry(f"{w}x{h}")
        self.minsize(*theme.WindowMin)

        self._status_var = ctk.StringVar(value="")
        self._current_category = "dashboard"
        self._view_cache: dict[str, ctk.CTkBaseClass] = {}
        self._inline_host: InlineHostView | None = None
        self._inline_return_category = "products"
        self._geometry_before_inline: str | None = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._sidebar = Sidebar(
            self,
            version=__version__,
            on_select=self._on_nav,
        )
        self._sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self._topbar = Topbar(self)
        self._topbar.grid(row=0, column=1, sticky="ew")

        self._content = ctk.CTkFrame(self, fg_color=theme.AppBg, corner_radius=0)
        self._content.grid(row=1, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._status_bar = ctk.CTkLabel(
            self,
            textvariable=self._status_var,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=4)

        self._show_dashboard()

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def _hide_cached_views(self) -> None:
        for view in self._view_cache.values():
            if hasattr(view, "on_hide"):
                view.on_hide()
            view.grid_remove()

    def _restore_window_geometry(self) -> None:
        if not self._geometry_before_inline:
            return
        self.geometry(self._geometry_before_inline)
        self._geometry_before_inline = None
        self.minsize(*theme.WindowMin)

    def _apply_inline_window_size(self, comp: Component) -> None:
        """Opcjonalny resize okna z component.json extras — tylko bezpieczny zakres."""
        try:
            w = int(comp.extras.get("inline_width") or 0)
            h = int(comp.extras.get("inline_height") or 0)
        except (TypeError, ValueError):
            return
        if not (900 <= w <= 1800 and 650 <= h <= 1200):
            return
        self._geometry_before_inline = self.geometry()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(w, max(theme.WindowMin[0], sw - 40))
        h = min(h, max(theme.WindowMin[1], sh - 80))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _destroy_inline_host(self) -> None:
        if self._inline_host is None:
            return
        if hasattr(self._inline_host, "on_hide"):
            self._inline_host.on_hide()
        self._inline_host.destroy()
        self._inline_host = None
        self._restore_window_geometry()

    def _show_view(self, key: str, factory: Callable[[], ctk.CTkBaseClass]) -> None:
        self._destroy_inline_host()
        self._hide_cached_views()

        if key not in self._view_cache:
            self._view_cache[key] = factory()

        view = self._view_cache[key]
        view.grid(row=0, column=0, sticky="nsew")
        if hasattr(view, "on_show"):
            view.on_show()
        self._content.update_idletasks()

    def _on_inline_opened(self, comp: Component) -> None:
        self._studio_state.record_launch(comp)
        self._studio_state.save()

    def _return_from_inline(self) -> None:
        self._destroy_inline_host()
        self._show_hub(self._inline_return_category)

    def _show_inline_component(self, comp: Component, return_category_id: str) -> None:
        self._inline_return_category = return_category_id
        self._current_category = return_category_id
        self._hide_cached_views()
        self._destroy_inline_host()

        self._topbar.set_breadcrumb(f"Inline / {comp.name}")
        self._sidebar.set_active(return_category_id)

        self._inline_host = InlineHostView(
            self._content,
            comp,
            on_back=self._return_from_inline,
            on_status=self._set_status,
            on_opened=self._on_inline_opened,
        )
        self._inline_host.grid(row=0, column=0, sticky="nsew")
        self._content.update_idletasks()
        self._apply_inline_window_size(comp)

    def _show_dashboard(self) -> None:
        self._current_category = "dashboard"
        self._topbar.set_breadcrumb("Dashboard")
        self._sidebar.set_active("dashboard")
        self._show_view(
            "dashboard",
            lambda: DashboardView(
                self._content,
                component_index=self._component_index,
                studio_state=self._studio_state,
                on_status=self._set_status,
                on_open_inline=self._show_inline_component,
            ),
        )

    def _show_hub(self, category_id: str) -> None:
        self._current_category = category_id
        label = category_label(category_id)
        self._topbar.set_breadcrumb(label)
        self._sidebar.set_active(category_id)
        key = f"hub:{category_id}"
        self._show_view(
            key,
            lambda cid=category_id: ComponentHubView(
                self._content,
                category_id=cid,
                component_index=self._component_index,
                studio_state=self._studio_state,
                on_status=self._set_status,
                on_open_inline=self._show_inline_component,
            ),
        )

    def _on_nav(self, category_id: str) -> None:
        if category_id == self._current_category and self._inline_host is None:
            return
        if self._inline_host is not None:
            self._destroy_inline_host()
        if category_id == "dashboard":
            self._show_dashboard()
        else:
            self._show_hub(category_id)
