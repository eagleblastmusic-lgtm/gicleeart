"""GicleeApp Studio — shell CustomTkinter (preview obok klasycznego launchera)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from giclee_app import __version__
from giclee_app.component_loader import Component
from giclee_app.launcher_delegate import LaunchOutcome, launch
from giclee_app.studio.background_capabilities import capability_for
from giclee_app.studio.categories import category_label
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.studio.state import StudioState

from .ui.background_panel import BackgroundPanelView
from .ui.component_hub import ComponentHubView
from .ui.dashboard import DashboardView
from .ui.inline_host import InlineHostView
from .ui.sidebar import Sidebar
from .ui.topbar import Topbar
from .ui import theme

_INLINE_W_MIN, _INLINE_W_MAX = 900, 1800
_INLINE_H_MIN, _INLINE_H_MAX = 650, 1200
_INLINE_MIN_W_LO, _INLINE_MIN_W_HI = 600, 1800
_INLINE_MIN_H_LO, _INLINE_MIN_H_HI = 400, 1200


def _safe_int(value: object, lo: int, hi: int, default: int = 0) -> int:
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if n <= 0:
        return default
    return max(lo, min(hi, n))


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
        self._background_host: BackgroundPanelView | None = None
        self._inline_stack: list[tuple[Component, str]] = []
        self._inline_return_category = "products"
        self._background_return_category = "theme"
        self._geometry_before_inline: str | None = None
        self._minsize_before_inline: tuple[int, int] | None = None

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

    def _read_window_minsize(self) -> tuple[int, int]:
        """Odczyt minsize — CTk.minsize() bez argumentów zeruje _min_width/_min_height."""
        try:
            raw = self.tk.call("wm", "minsize", self._w)
            w_i, h_i = (int(v) for v in self.tk.splitlist(raw))
            if w_i > 0 and h_i > 0:
                return w_i, h_i
        except (tk.TclError, TypeError, ValueError):
            pass
        return theme.WindowMin

    def _ensure_ctk_geometry_state(self) -> None:
        """CTk.geometry() wymaga ustawionych _min/_max width/height."""
        if getattr(self, "_min_width", None) is None or getattr(self, "_min_height", None) is None:
            w, h = self._read_window_minsize()
            self._min_width = w
            self._min_height = h
        if getattr(self, "_max_width", None) is None or getattr(self, "_max_height", None) is None:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self._max_width = max(int(sw), theme.WindowMin[0])
            self._max_height = max(int(sh), theme.WindowMin[1])

    def _safe_geometry(self, geometry_string: str) -> None:
        self._ensure_ctk_geometry_state()
        self.geometry(geometry_string)

    def _safe_minsize(self, width: int, height: int) -> None:
        self._ensure_ctk_geometry_state()
        self.minsize(width, height)

    def _hide_cached_views(self, *, except_key: str | None = None) -> None:
        for key, view in self._view_cache.items():
            if except_key is not None and key == except_key:
                continue
            if hasattr(view, "on_hide"):
                view.on_hide()
            view.grid_remove()

    def _restore_window_geometry(self) -> None:
        if not self._geometry_before_inline:
            return
        target = self._geometry_before_inline
        prior = self._minsize_before_inline or theme.WindowMin
        self._geometry_before_inline = None
        self._minsize_before_inline = None
        try:
            self._safe_minsize(*prior)
            self._safe_geometry(target)
        except (TypeError, tk.TclError):
            try:
                self._safe_minsize(*theme.WindowMin)
                self._safe_geometry(target)
            except (TypeError, tk.TclError):
                pass

    def _apply_inline_window_size(self, comp: Component) -> None:
        """Opcjonalny resize okna z component.json extras — tylko bezpieczny zakres."""
        w = _safe_int(comp.extras.get("inline_width"), _INLINE_W_MIN, _INLINE_W_MAX)
        h = _safe_int(comp.extras.get("inline_height"), _INLINE_H_MIN, _INLINE_H_MAX)
        if w <= 0 or h <= 0:
            return

        min_w = _safe_int(comp.extras.get("inline_min_width"), _INLINE_MIN_W_LO, _INLINE_MIN_W_HI, w)
        min_h = _safe_int(comp.extras.get("inline_min_height"), _INLINE_MIN_H_LO, _INLINE_MIN_H_HI, h)
        min_w = min(min_w, w)
        min_h = min(min_h, h)
        min_w = max(theme.WindowMin[0], min_w)
        min_h = max(theme.WindowMin[1], min_h)

        if self._geometry_before_inline is None:
            self._geometry_before_inline = self.geometry()
            self._minsize_before_inline = self._read_window_minsize()

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(w, max(theme.WindowMin[0], sw - 40))
        h = min(h, max(theme.WindowMin[1], sh - 80))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self._safe_geometry(f"{w}x{h}+{x}+{y}")
        self._safe_minsize(min_w, min_h)

    def _destroy_background_host(self) -> None:
        if self._background_host is None:
            return
        self._unbind_inline_escape()
        if hasattr(self._background_host, "on_hide"):
            self._background_host.on_hide()
        self._background_host.destroy()
        self._background_host = None

    def _destroy_inline_host(self, *, restore_geometry: bool = True) -> None:
        if self._inline_host is None:
            return
        self._unbind_inline_escape()
        if hasattr(self._inline_host, "on_hide"):
            self._inline_host.on_hide()
        self._inline_host.destroy()
        self._inline_host = None
        if restore_geometry:
            try:
                self._restore_window_geometry()
            except (TypeError, tk.TclError):
                self._geometry_before_inline = None
                self._minsize_before_inline = None

    def _bind_inline_escape(self) -> None:
        self.bind("<Escape>", self._on_escape_back)

    def _unbind_inline_escape(self) -> None:
        self.unbind("<Escape>")

    def _escape_blocked_by_focus(self) -> bool:
        focus = self.focus_get()
        if focus is None:
            return False
        widget: tk.Misc | None = focus
        for _ in range(10):
            if widget is None:
                break
            try:
                cls = widget.winfo_class().lower()
            except tk.TclError:
                break
            if "entry" in cls or "text" in cls or "combobox" in cls:
                return True
            try:
                widget = widget.master
            except (AttributeError, tk.TclError):
                break
        return False

    def _on_escape_back(self, _event: tk.Event | None = None) -> None:
        if self._background_host is not None:
            if self._escape_blocked_by_focus():
                return
            self._return_from_background_panel()
            return
        if self._inline_host is None:
            return
        if self._escape_blocked_by_focus():
            return
        self._return_from_inline()

    def _inline_breadcrumb(self, comp: Component) -> str:
        cat = category_label(self._inline_return_category)
        if self._inline_stack:
            prev = " / ".join(c.name for c, _ in self._inline_stack)
            return f"{cat} / {prev} / {comp.name}"
        return f"{cat} / {comp.name}"

    def _present_inline(self, comp: Component, return_category_id: str) -> None:
        self._inline_return_category = return_category_id
        self._current_category = return_category_id
        self._topbar.set_breadcrumb(self._inline_breadcrumb(comp))
        self._sidebar.set_active(return_category_id)

        back_label = "Wróć" if self._inline_stack else "Wróć do huba"
        self._inline_host = InlineHostView(
            self._content,
            comp,
            on_back=self._return_from_inline,
            on_status=self._set_status,
            on_opened=self._on_inline_opened,
            on_open_component=self._on_open_component_from_inline,
            back_label=back_label,
        )
        self._inline_host.grid(row=0, column=0, sticky="nsew")
        self._content.update_idletasks()
        self._apply_inline_window_size(comp)
        self._bind_inline_escape()

    def _on_open_component_from_inline(self, folder_name: str) -> None:
        key = (folder_name or "").strip()
        if not key:
            self._set_status("Brak nazwy komponentu do otwarcia.")
            return

        comp = self._component_index.by_folder.get(key)
        if comp is None:
            self._set_status(f"Nie znaleziono komponentu: {key}")
            return

        if comp.mode == "inline":
            self._show_inline_component(
                comp,
                self._inline_return_category,
                cross_nav=True,
            )
            return

        result = launch(comp, on_status=self._set_status)
        if result.outcome != LaunchOutcome.OK:
            self._set_status(result.message or f"Nie udało się otworzyć: {comp.name}")

    def _show_view(self, key: str, factory: Callable[[], ctk.CTkBaseClass]) -> None:
        self._destroy_inline_host()
        self._destroy_background_host()
        self._inline_stack.clear()

        if key not in self._view_cache:
            self._view_cache[key] = factory()

        self._hide_cached_views(except_key=key)

        view = self._view_cache[key]
        view.grid(row=0, column=0, sticky="nsew")
        if hasattr(view, "on_show"):
            view.on_show()
        self._content.update_idletasks()

    def _on_inline_opened(self, comp: Component) -> None:
        self._studio_state.record_launch(comp)
        self._studio_state.save()

    def _handoff_background_to_inline(self, comp: Component) -> None:
        category = self._background_return_category or self._current_category or "theme"
        if capability_for(comp.folder_name) is None:
            return
        if comp.mode != "inline":
            self._set_status(f"{comp.name}: brak inline handoff")
            return
        self._show_inline_component(comp, category)

    def _return_from_background_panel(self) -> None:
        category = self._background_return_category or self._current_category or "theme"
        self._destroy_background_host()
        self._set_status("Wrócono do huba")
        self._show_hub(category)

    def _show_background_panel(self, comp: Component, return_category_id: str) -> None:
        cap = capability_for(comp.folder_name)
        if cap is None:
            return
        category = (return_category_id or self._current_category or "theme").strip()
        self._background_return_category = category
        self._inline_stack.clear()
        self._destroy_inline_host(restore_geometry=True)
        self._hide_cached_views()
        self._destroy_background_host()

        self._current_category = category
        cat_label = category_label(category)
        self._topbar.set_breadcrumb(f"{cat_label} / {comp.name} / Tło")
        self._sidebar.set_active(category)

        self._background_host = BackgroundPanelView(
            self._content,
            comp,
            cap,
            on_back=self._return_from_background_panel,
            on_status=self._set_status,
            on_open_inline=lambda c=comp: self._handoff_background_to_inline(c),
        )
        self._background_host.grid(row=0, column=0, sticky="nsew")
        self._content.update_idletasks()
        self._bind_inline_escape()

    def _return_from_inline(self) -> None:
        if self._inline_stack:
            comp, cat = self._inline_stack.pop()
            self._destroy_inline_host(restore_geometry=False)
            self._present_inline(comp, cat)
            return
        category = self._inline_return_category
        self._destroy_inline_host(restore_geometry=True)
        self._inline_stack.clear()
        self._set_status("Wrócono do huba")
        self._show_hub(category)

    def _show_inline_component(
        self,
        comp: Component,
        return_category_id: str,
        *,
        cross_nav: bool = False,
    ) -> None:
        if cross_nav:
            if self._inline_host is not None:
                self._inline_stack.append((self._inline_host.comp, self._inline_return_category))
            self._destroy_inline_host(restore_geometry=False)
            self._destroy_background_host()
            self._present_inline(comp, self._inline_return_category)
            return

        self._inline_return_category = return_category_id
        self._inline_stack.clear()
        self._hide_cached_views()
        self._destroy_background_host()
        self._destroy_inline_host(restore_geometry=True)
        self._present_inline(comp, return_category_id)

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
                on_open_background=self._show_background_panel,
            ),
        )

    def _on_nav(self, category_id: str) -> None:
        if (
            category_id == self._current_category
            and self._inline_host is None
            and self._background_host is None
        ):
            return
        if self._inline_host is not None or self._background_host is not None:
            self._inline_stack.clear()
            self._destroy_inline_host()
            self._destroy_background_host()
        if category_id == "dashboard":
            self._show_dashboard()
        else:
            self._show_hub(category_id)
