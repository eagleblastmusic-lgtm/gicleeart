"""Host inline komponentów w Studio Preview — bez importu launcher.py."""

from __future__ import annotations

import importlib
import inspect
import os
import re
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from typing import Any

import customtkinter as ctk

from giclee_app.component_loader import Component
from giclee_app.launcher_delegate import component_log_path
from giclee_app.studio.bg import run_async

from . import theme
from .widgets import SectionHeader

_SECRET_KEY_PATTERN = re.compile(
    r"(token|accesstoken|secret|password|api_key|apikey|authorization|bearer)"
    r"\s*[:=]\s*['\"]?(\S+)",
    re.IGNORECASE,
)
_BEARER_PATTERN = re.compile(r"\bBearer\s+\S+", re.IGNORECASE)
_STUDIO_INLINE_ENV = "GICLEE_STUDIO_INLINE"


def _sanitize_error_text(text: str) -> str:
    """Maskuje potencjalne sekrety w komunikatach błędów."""
    if not text:
        return text
    out = _BEARER_PATTERN.sub("Bearer [redacted]", text)
    out = _SECRET_KEY_PATTERN.sub(r"\1=[redacted]", out)
    return out


def _short_error(exc: BaseException) -> str:
    name = type(exc).__name__
    msg = _sanitize_error_text(str(exc).strip().replace("\n", " "))
    if len(msg) > 120:
        msg = msg[:117] + "…"
    return f"{name}: {msg}" if msg else name


def _supports_on_open_component(builder: Callable[..., Any]) -> bool:
    try:
        sig = inspect.signature(builder)
    except (TypeError, ValueError):
        return False
    if "on_open_component" in sig.parameters:
        return True
    return any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )


def _invoke_build_view(
    builder: Callable[..., Any],
    parent: tk.Widget,
    on_back: Callable[[], None],
    on_open_component: Callable[[str], None] | None = None,
) -> Any:
    if _supports_on_open_component(builder):
        return builder(parent, on_back, on_open_component=on_open_component)
    return builder(parent, on_back)


class InlineHostView(ctk.CTkFrame):
    """Osadza Komponenty.<folder>.view przez build_view(parent, on_back)."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        *,
        on_back: Callable[[], None],
        on_status: Callable[[str], None] | None = None,
        on_opened: Callable[[Component], None] | None = None,
        on_open_component: Callable[[str], None] | None = None,
        back_label: str = "Wróć do huba",
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._comp = comp
        self._on_back = on_back
        self._on_status = on_status
        self._on_opened = on_opened
        self._on_open_component = on_open_component
        self._back_label = back_label
        self._tk_mount: tk.Frame | None = None
        self._load_ok = False
        self._loading_label: ctk.CTkLabel | None = None
        self._build_shell()
        self._show_loading()
        # Import modułu w wątku roboczym + budowa widoku po pierwszej klatce —
        # okno nie zamraża się na czas ładowania ciężkiego komponentu.
        self.after(1, self._start_mount)

    @property
    def load_ok(self) -> bool:
        return self._load_ok

    @property
    def comp(self) -> Component:
        return self._comp

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=10)
        ctk.CTkLabel(
            left,
            text=self._comp.name,
            font=theme.get_font(16, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            left,
            text=f"{self._comp.folder_name}  ·  Inline Studio",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))
        ctk.CTkButton(
            header,
            text=self._back_label,
            width=120,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            command=self._on_back,
        ).pack(side="right", padx=16, pady=10)

        self._body = ctk.CTkFrame(self, fg_color=theme.AppBg, corner_radius=0)
        self._body.pack(fill="both", expand=True)
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)

    def _show_error(self, title: str, detail: str) -> None:
        safe_detail = _sanitize_error_text(detail)
        panel = ctk.CTkFrame(
            self._body,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="both", expand=True, padx=24, pady=24)
        SectionHeader(panel, title).pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            panel,
            text=safe_detail,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=520,
        ).pack(fill="x", padx=16, pady=(0, 16))

    def _append_log(self, line: str) -> None:
        try:
            path = component_log_path(self._comp)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n========== {datetime.now().isoformat()} studio inline ==========\n")
                f.write(_sanitize_error_text(line) + "\n")
        except OSError:
            pass

    def _set_studio_inline_flag(self, active: bool) -> None:
        if active:
            os.environ[_STUDIO_INLINE_ENV] = "1"
        else:
            os.environ.pop(_STUDIO_INLINE_ENV, None)

    def _show_loading(self) -> None:
        self._loading_label = ctk.CTkLabel(
            self._body,
            text=f"Ładowanie: {self._comp.name}…",
            font=theme.get_font(13),
            text_color=theme.TextMuted,
        )
        self._loading_label.grid(row=0, column=0)

    def _hide_loading(self) -> None:
        if self._loading_label is None:
            return
        try:
            self._loading_label.destroy()
        except tk.TclError:
            pass
        self._loading_label = None

    def _start_mount(self) -> None:
        run_async(
            self,
            lambda: importlib.import_module(self._comp.view_module_path),
            self._on_module_ready,
            on_error=self._on_import_error,
        )

    def _on_import_error(self, exc: BaseException) -> None:
        self._hide_loading()
        err = _short_error(exc)
        self._append_log(f"import failed: {err}")
        self._show_error(
            "Nie udało się załadować widoku",
            f"Moduł {self._comp.view_module_path} nie jest dostępny.\n{err}",
        )

    def _on_module_ready(self, mod: Any) -> None:
        self._hide_loading()
        self._mount_inline(mod)

    def _mount_inline(self, mod: Any) -> None:
        builder = getattr(mod, "build_view", None)
        if not callable(builder):
            self._append_log("missing build_view(parent, on_back)")
            self._show_error(
                "Brak build_view",
                f"Komponent '{self._comp.folder_name}' nie ma funkcji "
                "build_view(parent, on_back) w view.py.",
            )
            return

        self._tk_mount = tk.Frame(self._body, bg=theme.AppBg)
        self._tk_mount.grid(row=0, column=0, sticky="nsew")
        self._set_studio_inline_flag(True)

        try:
            view = _invoke_build_view(
                builder,
                self._tk_mount,
                self._on_back,
                self._on_open_component,
            )
        except Exception as exc:  # noqa: BLE001
            err = _short_error(exc)
            self._append_log(f"build_view failed: {err}")
            self._clear_tk_mount()
            self._show_error("Błąd budowy widoku", err)
            return

        if view is not None and hasattr(view, "pack"):
            try:
                view.pack(fill="both", expand=True)
            except tk.TclError:
                pass

        self._load_ok = True
        if callable(self._on_opened):
            self._on_opened(self._comp)
        if callable(self._on_status):
            self._on_status(f"Inline: {self._comp.name}")

    def _clear_tk_mount(self) -> None:
        self._set_studio_inline_flag(False)
        if self._tk_mount is None:
            return
        try:
            for child in self._tk_mount.winfo_children():
                child.destroy()
            self._tk_mount.destroy()
        except tk.TclError:
            pass
        self._tk_mount = None

    def on_hide(self) -> None:
        self._clear_tk_mount()

    def destroy(self) -> None:
        self._clear_tk_mount()
        super().destroy()
