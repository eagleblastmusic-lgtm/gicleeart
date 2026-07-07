"""GicleeApp Studio — shell CustomTkinter (preview obok klasycznego launchera)."""

from __future__ import annotations

import os
import time
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from giclee_app import __version__
from giclee_app.component_loader import Component, find_components_dir
from giclee_app.launcher_delegate import LaunchOutcome, launch
from giclee_app.studio.background_capabilities import capability_for
from giclee_app.studio.categories import category_label
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.studio.perf import log_event, span
from giclee_app.studio.state import StudioState

from .ui.asset_lab_view import AssetLabView
from .ui.background_panel import BackgroundPanelView
from .ui.component_hub import ComponentHubView
from .ui.dashboard import DashboardView
from .ui.inline_host import InlineHostView
from .ui.gicleeframe_view import GicleeFrameView
from .ui.katalog_view import KatalogView
from .ui.sidebar import Sidebar
from .ui.topbar import Topbar
from .ui import theme

_INLINE_W_MIN, _INLINE_W_MAX = 900, 1800
_INLINE_H_MIN, _INLINE_H_MAX = 650, 1200
_INLINE_MIN_W_LO, _INLINE_MIN_W_HI = 600, 1800
_INLINE_MIN_H_LO, _INLINE_MIN_H_HI = 400, 1200
_STUDIO_IDLE_PREWARM_ENV = "GICLEE_STUDIO_IDLE_PREWARM"
_PREWARM_DELAY_MS = 1200
_PREWARM_STEP_DELAY_MS = 700
_PREWARM_MIN_QUIET_MS = 5000


def _env_enabled(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "debug"}


def _studio_idle_prewarm_enabled() -> bool:
    return _env_enabled(_STUDIO_IDLE_PREWARM_ENV, default=False)


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
        with span("studio.component_index.build"):
            self._component_index = StudioComponentIndex.build()
        with span("studio.state.load"):
            self._studio_state = StudioState.load()
        pruned = False
        with span("studio.state.prune"):
            pruned = self._studio_state.prune(self._component_index.by_folder.keys())
        if pruned:
            self._studio_state.save()

        self.title(f"{theme.APP_TITLE} · v{__version__} · {theme.PREVIEW_BADGE}")
        self.configure(fg_color=theme.AppBg)
        w, h = theme.WindowDefault
        self.geometry(f"{w}x{h}")
        self.minsize(*theme.WindowMin)

        self._status_var = ctk.StringVar(value="")
        self._current_category = "dashboard"
        self._view_cache: dict[str, ctk.CTkBaseClass] = {}
        self._route_shell_frame: ctk.CTkFrame | None = None
        self._route_shell_key: str | None = None
        self._view_mount_generation = 0
        self._prewarm_after_ids: list[str] = []
        self._prewarm_cancelled = False
        self._prewarm_active = False
        self._last_user_route_action_ts = time.monotonic()
        self._inline_host: InlineHostView | None = None
        self._background_host: BackgroundPanelView | None = None
        self._inline_stack: list[tuple[Component, str]] = []
        self._inline_return_category = "products"
        self._background_return_category = "theme"
        self._katalog_return_category: str | None = None
        self._gicleeframe_return_category: str | None = None
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

        with span("studio.dashboard.first_show"):
            self._show_dashboard(skip_route_shell=True)

        self._schedule_idle_prewarm()

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

    def _destroy_route_shell(self) -> None:
        if self._route_shell_frame is None:
            return
        try:
            self._route_shell_frame.destroy()
        except tk.TclError:
            pass
        self._route_shell_frame = None
        self._route_shell_key = None

    def _route_shell_title_for_key(self, key: str) -> str:
        if key == "dashboard":
            return "Dashboard"
        if key == "asset_lab":
            return "Asset Lab"
        if key == "katalog":
            return "Katalog"
        if key == "gicleeframe":
            return "GICLÉE FRAME™"
        if key.startswith("hub:"):
            return category_label(key.split(":", 1)[1])
        return "Ładowanie…"

    def _show_route_shell(self, key: str, title: str = "Ładowanie…") -> None:
        self._destroy_route_shell()
        self._hide_cached_views()
        self._route_shell_frame = ctk.CTkFrame(self._content, fg_color=theme.AppBg, corner_radius=0)
        inner = ctk.CTkFrame(self._route_shell_frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.42, anchor="center")
        ctk.CTkLabel(
            inner,
            text=title,
            font=theme.get_font(18, "bold"),
            text_color=theme.TextPrimary,
        ).pack(pady=(0, 8))
        ctk.CTkLabel(
            inner,
            text="Przygotowuję widok…",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
        ).pack()
        self._route_shell_frame.grid(row=0, column=0, sticky="nsew")
        self._route_shell_key = key
        log_event("studio.route_shell.visible", key=key)

    def _diag_elapsed_ms(self, start: float) -> float:
        return round((time.perf_counter() - start) * 1000, 2)

    def _diag_since_ms(self, factory_enter_mono: float) -> float:
        return round((time.perf_counter() - factory_enter_mono) * 1000, 2)

    def _view_mount_diag_fields(
        self,
        view: ctk.CTkBaseClass,
        *,
        key: str,
        cache_hit: bool,
        generation: int | None = None,
        factory_enter_mono: float | None = None,
    ) -> dict[str, object]:
        uses_async = bool(getattr(view, "uses_async_first_paint", False))
        uses_route_shell = bool(getattr(view, "uses_route_shell", False))
        fields: dict[str, object] = {
            "key": key,
            "cache_hit": cache_hit,
            "uses_async_first_paint": uses_async,
            "uses_route_shell": uses_route_shell,
            "will_update_idletasks": not uses_async and not uses_route_shell,
        }
        if generation is not None:
            fields["generation"] = generation
        if factory_enter_mono is not None:
            fields["since_factory_enter_ms"] = self._diag_since_ms(factory_enter_mono)
        return fields

    def _log_mount_lane_event(
        self,
        event: str,
        view: ctk.CTkBaseClass,
        *,
        key: str,
        cache_hit: bool,
        generation: int | None = None,
        factory_enter_mono: float | None = None,
        elapsed_ms: float | None = None,
    ) -> None:
        fields = self._view_mount_diag_fields(
            view,
            key=key,
            cache_hit=cache_hit,
            generation=generation,
            factory_enter_mono=factory_enter_mono,
        )
        log_event(event, elapsed_ms=elapsed_ms, **fields)

    def _mount_view_lane(
        self,
        *,
        key: str,
        cache_hit: bool,
        generation: int | None = None,
        factory_enter_mono: float | None = None,
        destroy_route_shell: bool = True,
        pre_grid: Callable[[ctk.CTkBaseClass], None] | None = None,
    ) -> None:
        view = self._view_cache[key]
        common = {
            "key": key,
            "cache_hit": cache_hit,
            "generation": generation,
            "factory_enter_mono": factory_enter_mono,
        }

        if destroy_route_shell:
            t0 = time.perf_counter()
            self._log_mount_lane_event("studio.show_view.pre_destroy_route_shell", view, **common)
            self._destroy_route_shell()
            self._log_mount_lane_event(
                "studio.show_view.post_destroy_route_shell",
                view,
                elapsed_ms=self._diag_elapsed_ms(t0),
                **common,
            )

        t0 = time.perf_counter()
        self._log_mount_lane_event("studio.show_view.pre_hide_cached_views", view, **common)
        self._hide_cached_views(except_key=key)
        self._log_mount_lane_event(
            "studio.show_view.post_hide_cached_views",
            view,
            elapsed_ms=self._diag_elapsed_ms(t0),
            **common,
        )

        if pre_grid is not None:
            pre_grid(view)

        t0 = time.perf_counter()
        self._log_mount_lane_event("studio.show_view.pre_grid", view, **common)
        view.grid(row=0, column=0, sticky="nsew")
        self._log_mount_lane_event(
            "studio.show_view.post_grid",
            view,
            elapsed_ms=self._diag_elapsed_ms(t0),
            **common,
        )

        t0 = time.perf_counter()
        self._log_mount_lane_event("studio.show_view.pre_on_show", view, **common)
        if hasattr(view, "on_show"):
            try:
                view.on_show(cache_hit=cache_hit)
            except TypeError:
                view.on_show()
        self._log_mount_lane_event(
            "studio.show_view.post_on_show",
            view,
            elapsed_ms=self._diag_elapsed_ms(t0),
            **common,
        )

        t0 = time.perf_counter()
        self._log_mount_lane_event("studio.show_view.pre_update_idletasks", view, **common)
        self._maybe_update_idletasks_for_view(view)
        self._log_mount_lane_event(
            "studio.show_view.post_update_idletasks",
            view,
            elapsed_ms=self._diag_elapsed_ms(t0),
            **common,
        )

        self._log_mount_lane_event("studio.show_view.pre_mounted", view, **common)
        log_event("studio.show_view.mounted", key=key, cache_hit=cache_hit)
        self._log_mount_lane_event("studio.show_view.post_mounted", view, **common)

    def _maybe_update_idletasks_for_view(self, view: ctk.CTkBaseClass) -> None:
        view_class = type(view).__name__
        uses_async = bool(getattr(view, "uses_async_first_paint", False))
        uses_route_shell = bool(getattr(view, "uses_route_shell", False))
        if uses_async or uses_route_shell:
            log_event(
                "studio.show_view.update_idletasks.skipped",
                view_class=view_class,
                uses_async_first_paint=uses_async,
                uses_route_shell=uses_route_shell,
            )
            return
        log_event(
            "studio.show_view.update_idletasks.executed",
            view_class=view_class,
            uses_async_first_paint=uses_async,
            uses_route_shell=uses_route_shell,
        )
        self._content.update_idletasks()

    def _touch_user_route_action(self) -> None:
        self._last_user_route_action_ts = time.monotonic()

    def _prewarm_quiet_ms(self) -> float:
        return (time.monotonic() - self._last_user_route_action_ts) * 1000

    def _cancel_idle_prewarm(self, *, due_user_action: bool = False) -> None:
        if due_user_action and self._prewarm_active:
            log_event("studio.prewarm.cancelled_due_user_action")
        self._prewarm_cancelled = True
        self._prewarm_active = False
        while self._prewarm_after_ids:
            after_id = self._prewarm_after_ids.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass

    def _schedule_idle_prewarm(self) -> None:
        if not _studio_idle_prewarm_enabled():
            log_event("studio.prewarm.skipped_disabled")
            return
        self._prewarm_cancelled = False
        after_id = self.after(_PREWARM_DELAY_MS, self._start_idle_prewarm)
        self._prewarm_after_ids.append(after_id)

    def _start_idle_prewarm(self) -> None:
        if self._prewarm_cancelled:
            return
        if not _studio_idle_prewarm_enabled():
            log_event("studio.prewarm.skipped_disabled")
            return
        quiet_ms = self._prewarm_quiet_ms()
        if quiet_ms < _PREWARM_MIN_QUIET_MS:
            remaining = max(1, int(_PREWARM_MIN_QUIET_MS - quiet_ms))
            log_event(
                "studio.prewarm.skipped_recent_user_action",
                quiet_ms=round(quiet_ms, 2),
                reschedule_ms=remaining,
            )
            after_id = self.after(remaining, self._start_idle_prewarm)
            self._prewarm_after_ids.append(after_id)
            return
        log_event("studio.prewarm.start")
        self._prewarm_active = True
        self._prewarm_step_index = 0
        self._prewarm_next_step()

    def _prewarm_factory_for_key(self, key: str) -> Callable[[], ctk.CTkBaseClass] | None:
        if key == "hub:theme":
            return lambda: ComponentHubView(
                self._content,
                category_id="theme",
                component_index=self._component_index,
                studio_state=self._studio_state,
                on_status=self._set_status,
                on_open_inline=self._show_inline_component,
                on_open_background=self._show_background_panel,
            )
        if key == "hub:products":
            return lambda: ComponentHubView(
                self._content,
                category_id="products",
                component_index=self._component_index,
                studio_state=self._studio_state,
                on_status=self._set_status,
                on_open_inline=self._show_inline_component,
                on_open_background=self._show_background_panel,
            )
        if key == "katalog":
            return lambda: KatalogView(
                self._content,
                components_root=find_components_dir(),
                on_status=self._set_status,
                on_back=None,
            )
        return None

    def _prewarm_next_step(self) -> None:
        if self._prewarm_cancelled:
            return
        if not _studio_idle_prewarm_enabled():
            log_event("studio.prewarm.skipped_disabled")
            self._prewarm_active = False
            return
        quiet_ms = self._prewarm_quiet_ms()
        if quiet_ms < _PREWARM_MIN_QUIET_MS:
            remaining = max(1, int(_PREWARM_MIN_QUIET_MS - quiet_ms))
            log_event(
                "studio.prewarm.skipped_recent_user_action",
                quiet_ms=round(quiet_ms, 2),
                reschedule_ms=remaining,
            )
            self._prewarm_after_ids.append(self.after(remaining, self._prewarm_next_step))
            return
        keys = ("hub:theme", "hub:products", "katalog")
        if self._prewarm_step_index >= len(keys):
            self._prewarm_active = False
            return
        key = keys[self._prewarm_step_index]
        self._prewarm_step_index += 1
        if key in self._view_cache:
            self._prewarm_after_ids.append(self.after(_PREWARM_STEP_DELAY_MS, self._prewarm_next_step))
            return
        factory = self._prewarm_factory_for_key(key)
        if factory is None:
            self._prewarm_after_ids.append(self.after(_PREWARM_STEP_DELAY_MS, self._prewarm_next_step))
            return
        if self._prewarm_cancelled:
            return
        quiet_ms = self._prewarm_quiet_ms()
        if quiet_ms < _PREWARM_MIN_QUIET_MS:
            remaining = max(1, int(_PREWARM_MIN_QUIET_MS - quiet_ms))
            log_event(
                "studio.prewarm.skipped_recent_user_action",
                quiet_ms=round(quiet_ms, 2),
                reschedule_ms=remaining,
            )
            self._prewarm_step_index -= 1
            self._prewarm_after_ids.append(self.after(remaining, self._prewarm_next_step))
            return
        log_event("studio.prewarm.factory_allowed", key=key, quiet_ms=round(quiet_ms, 2))
        log_event("studio.prewarm.view_started", key=key)
        with span("studio.prewarm.factory", key=key):
            self._view_cache[key] = factory()
        log_event("studio.prewarm.view_done", key=key)
        self._prewarm_after_ids.append(self.after(_PREWARM_STEP_DELAY_MS, self._prewarm_next_step))

    def _create_and_mount_view_deferred(
        self,
        key: str,
        factory: Callable[[], ctk.CTkBaseClass],
        generation: int,
    ) -> None:
        if generation != self._view_mount_generation:
            return
        factory_enter = time.perf_counter()
        log_event(
            "studio.show_view.deferred_factory.enter",
            key=key,
            cache_hit=False,
            generation=generation,
            since_factory_enter_ms=0,
        )
        with span("studio.show_view.deferred_factory", key=key):
            if key not in self._view_cache:
                self._view_cache[key] = factory()
        log_event(
            "studio.show_view.deferred_factory.returned",
            key=key,
            cache_hit=False,
            generation=generation,
            since_factory_enter_ms=self._diag_since_ms(factory_enter),
        )
        if generation != self._view_mount_generation:
            return
        self._mount_view_lane(
            key=key,
            cache_hit=False,
            generation=generation,
            factory_enter_mono=factory_enter,
        )

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

    def _show_view(
        self,
        key: str,
        factory: Callable[[], ctk.CTkBaseClass],
        *,
        skip_route_shell: bool = False,
    ) -> None:
        cache_hit = key in self._view_cache
        self._touch_user_route_action()
        log_event("studio.show_view.request", key=key, cache_hit=cache_hit)
        self._cancel_idle_prewarm(due_user_action=True)
        self._destroy_inline_host()
        self._destroy_background_host()
        self._inline_stack.clear()

        if not cache_hit and not skip_route_shell:
            self._view_mount_generation += 1
            generation = self._view_mount_generation
            with span("studio.show_view.route_shell", key=key):
                self._show_route_shell(key, self._route_shell_title_for_key(key))
            after_id = self.after(
                1,
                lambda k=key, f=factory, g=generation: self._create_and_mount_view_deferred(k, f, g),
            )
            return

        with span("studio.show_view", key=key, cache_hit=cache_hit):
            if not cache_hit:
                with span("studio.show_view.factory", key=key):
                    self._view_cache[key] = factory()

            self._mount_view_lane(key=key, cache_hit=cache_hit)

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

    def _show_katalog_shell(self, return_category_id: str | None = None) -> None:
        """F1 read-only Katalog workflow — sidebar nav or hub handoff."""
        self._katalog_return_category = return_category_id
        self._inline_stack.clear()
        self._destroy_inline_host(restore_geometry=True)
        self._destroy_background_host()

        if return_category_id:
            cat_label = category_label(return_category_id)
            self._current_category = return_category_id
            self._topbar.set_breadcrumb(f"{cat_label} / Katalog")
            self._sidebar.set_active(return_category_id)
        else:
            self._current_category = "katalog"
            self._topbar.set_breadcrumb("Katalog")
            self._sidebar.set_active("katalog")

        key = "katalog"
        cache_hit = key in self._view_cache
        self._touch_user_route_action()
        log_event("studio.show_view.request", key=key, cache_hit=cache_hit)
        self._cancel_idle_prewarm(due_user_action=True)
        on_back = self._return_from_katalog if return_category_id else None

        if not cache_hit:
            self._view_mount_generation += 1
            generation = self._view_mount_generation
            with span("studio.show_view.route_shell", key=key):
                self._show_route_shell(key, "Katalog")
            self.after(
                1,
                lambda g=generation, ob=on_back: self._mount_katalog_deferred(g, ob),
            )
            return

        with span("studio.katalog.open", return_category=return_category_id or "", cache_hit=cache_hit):
            self._hide_cached_views(except_key=key)

            view = self._view_cache[key]
            if hasattr(view, "set_navigation"):
                view.set_navigation(on_back=on_back)

            view.grid(row=0, column=0, sticky="nsew")

            if hasattr(view, "on_show"):
                try:
                    view.on_show(cache_hit=cache_hit)
                except TypeError:
                    view.on_show()
            self._maybe_update_idletasks_for_view(view)
            log_event("studio.show_view.mounted", key=key, cache_hit=True)

    def _mount_katalog_deferred(self, generation: int, on_back: Callable[[], None] | None) -> None:
        if generation != self._view_mount_generation:
            return
        key = "katalog"
        with span("studio.show_view.deferred_factory", key=key):
            if key not in self._view_cache:
                self._view_cache[key] = KatalogView(
                    self._content,
                    components_root=find_components_dir(),
                    on_status=self._set_status,
                    on_back=on_back,
                )
        if generation != self._view_mount_generation:
            return
        with span("studio.katalog.open", return_category="", cache_hit=False):
            self._mount_view_lane(
                key=key,
                cache_hit=False,
                generation=generation,
                pre_grid=lambda v, _ob=on_back: v.set_navigation(on_back=_ob)
                if hasattr(v, "set_navigation")
                else None,
            )

    def _return_from_katalog(self) -> None:
        category = self._katalog_return_category or "theme"
        self._katalog_return_category = None

        view = self._view_cache.get("katalog")
        if view is not None and hasattr(view, "set_navigation"):
            view.set_navigation(on_back=None)

        self._set_status("Wrócono do huba")
        self._show_hub(category)

    def _show_gicleeframe_shell(self, return_category_id: str | None = None) -> None:
        """Planning shell GICLÉE FRAME™ — cached RAM-only workbench."""
        with span("studio.gicleeframe.open", return_category=return_category_id or ""):
            self._gicleeframe_return_category = return_category_id
            self._inline_stack.clear()
            self._destroy_inline_host(restore_geometry=True)
            self._destroy_background_host()

            if return_category_id:
                cat_label = category_label(return_category_id)
                self._current_category = return_category_id
                self._topbar.set_breadcrumb(f"{cat_label} / GICLÉE FRAME™")
                self._sidebar.set_active(return_category_id)
                on_back = self._return_from_gicleeframe
            else:
                self._current_category = "theme"
                self._topbar.set_breadcrumb("GICLÉE FRAME™")
                self._sidebar.set_active("theme")
                on_back = None

            key = "gicleeframe"
            cache_hit = key in self._view_cache
            self._touch_user_route_action()
            log_event("studio.show_view.request", key=key, cache_hit=cache_hit)
            self._cancel_idle_prewarm(due_user_action=True)
            log_event(
                "studio.gicleeframe.visual.enter",
                cache_hit=cache_hit,
                source="launcher",
            )
            log_event(
                "studio.gicleeframe.lifecycle",
                cache_hit=cache_hit,
                return_category=return_category_id or "",
            )

            if not cache_hit:
                self._view_mount_generation += 1
                generation = self._view_mount_generation
                with span("studio.show_view.route_shell", key=key):
                    self._show_route_shell(key, "GICLÉE FRAME™")
                self.after(
                    1,
                    lambda g=generation, ob=on_back: self._mount_gicleeframe_deferred(g, ob),
                )
                return

            self._mount_view_lane(
                key=key,
                cache_hit=True,
                destroy_route_shell=False,
                pre_grid=lambda v, _ob=on_back: v.set_navigation(on_back=_ob)
                if hasattr(v, "set_navigation")
                else None,
            )

    def _mount_gicleeframe_deferred(
        self,
        generation: int,
        on_back: Callable[[], None] | None,
    ) -> None:
        if generation != self._view_mount_generation:
            return
        key = "gicleeframe"
        factory_enter = time.perf_counter()
        log_event(
            "studio.show_view.deferred_factory.enter",
            key=key,
            cache_hit=False,
            generation=generation,
            since_factory_enter_ms=0,
        )
        with span("studio.show_view.deferred_factory", key=key):
            if key not in self._view_cache:
                with span("studio.gicleeframe.factory"):
                    self._view_cache[key] = GicleeFrameView(
                        self._content,
                        on_status=self._set_status,
                        on_back=on_back,
                    )
        log_event(
            "studio.show_view.deferred_factory.returned",
            key=key,
            cache_hit=False,
            generation=generation,
            since_factory_enter_ms=self._diag_since_ms(factory_enter),
        )
        if generation != self._view_mount_generation:
            return
        self._mount_view_lane(
            key=key,
            cache_hit=False,
            generation=generation,
            factory_enter_mono=factory_enter,
            pre_grid=lambda v, _ob=on_back: v.set_navigation(on_back=_ob)
            if hasattr(v, "set_navigation")
            else None,
        )

    def _return_from_gicleeframe(self) -> None:
        category = self._gicleeframe_return_category or "theme"
        self._gicleeframe_return_category = None

        view = self._view_cache.get("gicleeframe")
        if view is not None and hasattr(view, "set_navigation"):
            view.set_navigation(on_back=None)

        self._set_status("Wrócono do huba")
        self._show_hub(category)

    def _show_inline_component(
        self,
        comp: Component,
        return_category_id: str,
        *,
        cross_nav: bool = False,
    ) -> None:
        if not cross_nav and comp.folder_name == "katalog":
            self._show_katalog_shell(return_category_id)
            return
        if comp.folder_name == "gicleeframe":
            self._show_gicleeframe_shell(return_category_id)
            return
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

    def _show_dashboard(self, *, skip_route_shell: bool = False) -> None:
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
            skip_route_shell=skip_route_shell,
        )

    def _show_asset_lab(self) -> None:
        self._current_category = "asset_lab"
        self._topbar.set_breadcrumb("Asset Lab")
        self._sidebar.set_active("asset_lab")
        self._show_view(
            "asset_lab",
            lambda: AssetLabView(
                self._content,
                component_index=self._component_index,
                studio_state=self._studio_state,
                on_status=self._set_status,
            ),
        )

    def _show_katalog(self) -> None:
        self._show_katalog_shell(None)

    def _show_hub(self, category_id: str) -> None:
        count = len(self._component_index.components_for_category(category_id))
        log_event("studio.hub.open", category=category_id, component_count=count)
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
        self._touch_user_route_action()
        self._cancel_idle_prewarm(due_user_action=True)
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
        elif category_id == "asset_lab":
            self._show_asset_lab()
        elif category_id == "katalog":
            self._show_katalog()
        else:
            self._show_hub(category_id)
