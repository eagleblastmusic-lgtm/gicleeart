"""GicleeApp Studio — shell CustomTkinter (preview obok klasycznego launchera)."""

from __future__ import annotations

import customtkinter as ctk

from giclee_app import __version__
from giclee_app.studio.categories import category_label
from giclee_app.studio.component_index import StudioComponentIndex

from .ui.component_hub import ComponentHubView
from .ui.dashboard import DashboardView
from .ui.sidebar import Sidebar
from .ui.topbar import Topbar
from .ui import theme


class GicleeAppStudio(ctk.CTk):
    """Preview shell — bez pollingów / backupów / synców z launcher.py."""

    def __init__(self) -> None:
        super().__init__()
        self._component_index = StudioComponentIndex.build()

        self.title(f"{theme.APP_TITLE} · v{__version__} · {theme.PREVIEW_BADGE}")
        self.configure(fg_color=theme.AppBg)
        w, h = theme.WindowDefault
        self.geometry(f"{w}x{h}")
        self.minsize(*theme.WindowMin)

        self._status_var = ctk.StringVar(value="")
        self._current_category = "dashboard"

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

        self._dashboard: DashboardView | None = None
        self._hub: ComponentHubView | None = None

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

    def _clear_content(self) -> None:
        for child in self._content.winfo_children():
            child.destroy()
        self._dashboard = None
        self._hub = None

    def _show_dashboard(self) -> None:
        self._clear_content()
        self._current_category = "dashboard"
        self._topbar.set_breadcrumb("Dashboard")
        self._dashboard = DashboardView(
            self._content,
            component_index=self._component_index,
        )
        self._dashboard.grid(row=0, column=0, sticky="nsew")

    def _show_hub(self, category_id: str) -> None:
        self._clear_content()
        self._current_category = category_id
        label = category_label(category_id)
        self._topbar.set_breadcrumb(label)
        self._hub = ComponentHubView(
            self._content,
            category_id=category_id,
            component_index=self._component_index,
            on_status=self._set_status,
        )
        self._hub.grid(row=0, column=0, sticky="nsew")

    def _on_nav(self, category_id: str) -> None:
        if category_id == "dashboard":
            self._show_dashboard()
        else:
            self._show_hub(category_id)
