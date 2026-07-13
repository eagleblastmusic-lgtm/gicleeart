"""GicleeApp - launcher z kafelkami komponentow.

Uruchamia kazdy komponent jako osobny proces (`python -m Komponenty.<nazwa>`),
zeby ewentualne crashe nie ubily launchera, a Tkinter mial swoj wlasny root
w kazdym z procesow.
"""

from __future__ import annotations

import importlib
import math
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk
from collections.abc import Callable
from typing import Any

from . import __version__
from .component_loader import Component, discover_components, find_components_dir
from .launcher_layout import (
    SECTION_OTHER as _SECTION_OTHER,
    DEFAULT_SECTIONS as _SECTIONS,
    load_layout,
    merge_layout,
    resolve_sections,
)
from .launcher_options import show_launcher_options
from .component_logs import (
    DEFAULT_COMPONENT_LOGS_DIR,
    component_log_read_path,
    component_log_write_path,
)
from .launcher_shortcuts import (
    LAUNCHER_KEY_SHORTCUTS,
    dialog_blocks_shortcuts,
    focus_blocks_shortcuts,
    shortcut_key_from_event,
)
from .runtime import get_bundle_root, get_component_cwd, resolve_python_interpreter

try:
    from Komponenty._shared.window_geometry import position_toplevel_screen_center
except ImportError:

    def position_toplevel_screen_center(win: tk.Misc, width: int, height: int) -> None:
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x, y = max(0, (sw - width) // 2), max(0, (sh - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

APP_TITLE = "GicleeApp - launcher komponentow"
LAUNCHER_WIDTH = 920
LAUNCHER_HEIGHT = 780
LAUNCHER_MIN_WIDTH = 840
LAUNCHER_MIN_HEIGHT = 640

# Hasło przy starcie launchera — False = wyłączone (tymczasowo).
_LAUNCHER_AUTH_ENABLED = False

# Logi subprocess-ow komponentow (stdout/stderr przekierowany tutaj)
_LOGS_DIR = DEFAULT_COMPONENT_LOGS_DIR

_TILES_PER_ROW = 3
_TILE_W = 280
_TILE_H = 170
_TILE_PAD_X = 6   # poziomy odstep miedzy kafelkami w wierszu
_TILE_PAD_Y = 6   # pionowy odstep wewnatrz sekcji
_SECTION_GAP_TOP = 4    # gora pierwszej sekcji
_SECTION_GAP_BETWEEN = 12  # odstep miedzy kolejnymi sekcjami

# Domyślny układ sekcji: giclee_app/launcher_layout.py (DEFAULT_SECTIONS).
# Użytkownik może go zmienić w Opcje → zapis launcher_layout.json.

class GicleeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"{APP_TITLE} · v{__version__}")
        # Rozmiar okna dobrany pod 3 sekcje x 3 kafelki w rzedzie
        # (3 * (170 + 24) + 3 * naglowek_sekcji + paddingi + status bar).
        position_toplevel_screen_center(self.root, LAUNCHER_WIDTH, LAUNCHER_HEIGHT)
        self.root.minsize(LAUNCHER_MIN_WIDTH, LAUNCHER_MIN_HEIGHT)

        self.components_dir: Path = find_components_dir()
        self._all_components: list[Component] = []
        self._running_procs: list[subprocess.Popen] = []  # noqa: PLR0402
        # Aktualnie zamontowany widok inline (None = pokazujemy siatke kafelkow)
        self._inline_view: Any = None
        self._geometry_before_inline: str | None = None
        self._current_inline_folder: str | None = None
        self._next_inline_on_back: Callable[[], None] | None = None
        # Hover na kafelkach: podczas scrolla canvas kafelki przesuwaja sie pod kursorem
        # i Tk generuje lawine Enter/Leave -> set bg na wielu widgetach = przycinanie UI.
        self._suppress_tile_hover_until = 0.0
        self._tile_hover_clearers: list[Callable[[], None]] = []
        # Szybkie kolo / touchpad: lacz delty w jednym idle — mniej rysowan canvasu.
        self._wheel_delta_acc = 0
        self._wheel_idle_id: str | None = None
        # Stan zwinietych sekcji na ekranie startowym (nazwa sekcji -> True = zwinieta).
        self._section_collapsed: dict[str, bool] = {}
        self._layout = load_layout()
        self._normally_visible: set[str] = set()

        self.status_var = tk.StringVar(value="")

        self._build_ui()
        self._refresh_components()

        # Co ~3s odswiez liste, zeby ewentualnie nowe komponenty pojawialy sie
        # bez restartu launchera.
        self._auto_rescan()

        # Powiadomienie miesieczne (1-szy dzien miesiaca -> plan marketingowy).
        # Odpalamy 1.5s po starcie, zeby UI zdazyl sie pokazac, zanim wyskoczy dialog.
        self.root.after(1500, self._check_monthly_reminder)

        # Sprawdz przypomnienia (np. "1-szy dzien miesiaca - wygeneruj plan").
        # Odpalamy z lekkim opoznieniem, zeby okno juz sie wyrenderowalo.
        self.root.after(800, self._check_monthly_plan_reminder)

        # Polling zamowien Shopify -> Produkcja (co 5 minut).
        # Pierwszy sync po 30s (zeby OAuth / siec byly juz gotowe).
        self.root.after(30_000, self._poll_orders_from_shopify)

        # Polling zamówień Shopify → Księgowość / Dokumenty sprzedaży (co 5 min).
        self.root.after(35_000, self._poll_accounting_orders)

        # Auto-backup raz dziennie (idempotentne).
        self.root.after(2000, self._run_daily_backup)

        # Monitor konca utwardzania ramek - raz na minute sprawdza i wysyla toast
        # (zeby user nie musial patrzec na apke).
        self.root.after(15_000, self._check_cure_done_notifications)

        # Publisher cyklu social-media - co 60s sprawdza zaplanowane posty.
        # Pierwszy poll po 45s (po pierwszej synchronizacji zamowien).
        self.root.after(45_000, self._poll_cykl_publisher)

        # Reminder tygodniowy: jesli zostalo <=2 dni wygenerowanej tresci cyklu,
        # pokaz toast po 3s od startu.
        self.root.after(3000, self._check_cykl_weekly_reminder)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        # Naglowek
        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")
        title = ttk.Label(
            header, text="GicleeApp", font=("Segoe UI", 22, "bold"),
        )
        title.pack(side="left")
        subtitle = ttk.Label(
            header,
            text="Wybierz komponent, ktory chcesz uruchomic",
            foreground="#666",
        )
        subtitle.pack(side="left", padx=(12, 0), pady=(8, 0))
        ttk.Label(
            header,
            text=f"v{__version__}",
            foreground="#999",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(10, 0), pady=(10, 0))

        # Toolbar (refresh, otworz folder, instrukcja)
        tools = ttk.Frame(header)
        tools.pack(side="right")
        ttk.Button(tools, text="Token setup", command=self._show_token_setup).pack(side="left", padx=4)
        ttk.Button(tools, text="Stan sesji", command=self._show_session_status).pack(side="left", padx=4)
        ttk.Button(tools, text="Theme dev…", command=self._show_theme_dev).pack(side="left", padx=4)
        ttk.Button(tools, text="Zamknij porty", command=self._close_theme_dev_ports).pack(side="left", padx=4)
        ttk.Button(tools, text="Dziennik akcji", command=self._show_activity_log).pack(side="left", padx=4)
        ttk.Button(tools, text="Opcje", command=self._show_launcher_options).pack(side="left", padx=4)
        ttk.Button(tools, text="Instrukcja", command=self._show_help).pack(side="left", padx=4)
        ttk.Button(tools, text="Odswiez", command=self._refresh_components).pack(side="left", padx=4)
        ttk.Button(tools, text="Otworz folder Komponenty", command=self._open_components_dir).pack(
            side="left", padx=4
        )

        # Container body - zawiera dwa "ekrany":
        #  1) tiles_view (siatka kafelkow) - domyslny
        #  2) inline_view (zamontowany komponent inline z back button) - na zadanie
        # Przelaczanie przez pack_forget/pack.
        self._body_container = ttk.Frame(self.root)
        self._body_container.pack(fill="both", expand=True, padx=12, pady=4)

        self.tiles_view = ttk.Frame(self._body_container)
        self.tiles_view.pack(fill="both", expand=True)
        self._inline_host: ttk.Frame | None = None  # tworzymy on-demand

        self.canvas = tk.Canvas(self.tiles_view, highlightthickness=0, bd=0, bg="#f4f4f7")
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(self.tiles_view, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        # Wewnetrzna ramka w canvas
        self.tiles_frame = tk.Frame(self.canvas, bg="#f4f4f7")
        self._tiles_window = self.canvas.create_window(
            (0, 0), window=self.tiles_frame, anchor="nw",
        )

        def _on_tiles_configure(_evt: object) -> None:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_configure(evt: tk.Event) -> None:
            self.canvas.itemconfigure(self._tiles_window, width=evt.width)

        self.tiles_frame.bind("<Configure>", _on_tiles_configure)
        self.canvas.bind("<Configure>", _on_canvas_configure)

        # Scroll kolem / touchpadem (delta < 120 na Windows = glowny powod "klejenia" przy // 120)
        self._ensure_tiles_wheel_binding()

        # Klawiatura: canvas musi móc przejąć fokus (kafelki mają takefocus=False).
        self.canvas.configure(takefocus=True)
        self.canvas.bind("<Button-1>", self._focus_tiles_canvas, add="+")
        self.tiles_frame.bind("<Button-1>", self._focus_tiles_canvas, add="+")

        # Status bar
        status = ttk.Frame(self.root, padding=(12, 4))
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.status_var, foreground="#777").pack(side="left")
        ttk.Label(
            status,
            text=f"wersja {__version__}  ·  Komponenty: {self.components_dir}",
            foreground="#aaa",
        ).pack(side="right")

        self._bind_launcher_shortcuts()
        self.root.after_idle(self._focus_tiles_canvas)

    def _focus_tiles_canvas(self, _event: object = None) -> None:
        if not self.tiles_view.winfo_ismapped():
            return
        try:
            self.canvas.focus_set()
        except tk.TclError:
            pass

    def _bind_launcher_shortcuts(self) -> None:
        self.root.bind_all("<KeyPress>", self._on_launcher_key_shortcut, add="+")

    def _launcher_shortcut_key(self, event: tk.Event) -> str | None:
        return shortcut_key_from_event(event)

    def _launcher_shortcuts_active(self) -> bool:
        """Skróty literowe działają tylko na siatce kafelków (nie w inline / dialogu)."""
        if not self.tiles_view.winfo_ismapped():
            return False
        if dialog_blocks_shortcuts(self.root):
            return False
        if focus_blocks_shortcuts(self.root):
            return False
        return True

    def _on_launcher_key_shortcut(self, event: tk.Event) -> str | None:
        if not self._launcher_shortcuts_active():
            return None
        if event.state & (0x4 | 0x8):  # Control, Alt
            return None
        key = self._launcher_shortcut_key(event)
        if not key:
            return None
        folder = LAUNCHER_KEY_SHORTCUTS.get(key)
        if not folder:
            return None
        comp = self._component_by_folder(folder)
        if comp is None:
            self.status_var.set(f"Skrót «{key}»: brak komponentu {folder}")
            return "break"
        self._launch(comp)
        return "break"

    def _pointer_is_over_tiles_canvas(self, evt: tk.Event) -> bool:
        """True gdy zdarzenie dotyczy obszaru canvas z kafelkami (nie naglowka / innego okna)."""
        try:
            w = self.root.winfo_containing(evt.x_root, evt.y_root)
        except tk.TclError:
            return False
        if w is None:
            return False
        cur: tk.Misc | None = w
        while cur is not None:
            if cur == self.canvas:
                return True
            if isinstance(cur, tk.Toplevel) and cur != self.root:
                return False
            cur = cur.master  # type: ignore[assignment]
        return False

    def _on_canvas_mousewheel(self, evt: tk.Event) -> None:
        if not self.tiles_view.winfo_ismapped():
            return
        if not self._pointer_is_over_tiles_canvas(evt):
            return
        d = evt.delta
        if not d:
            return
        self._wheel_delta_acc += d
        if self._wheel_idle_id is not None:
            try:
                self.root.after_cancel(self._wheel_idle_id)
            except (tk.TclError, ValueError):
                pass
        self._wheel_idle_id = self.root.after_idle(self._flush_tiles_canvas_wheel)

    def _flush_tiles_canvas_wheel(self) -> None:
        self._wheel_idle_id = None
        d = self._wheel_delta_acc
        self._wheel_delta_acc = 0
        if not d:
            return
        self._suppress_tile_hover_until = time.monotonic() + 0.18
        for clear in self._tile_hover_clearers:
            try:
                clear()
            except tk.TclError:
                pass
        step = -d / 120.0
        if -1 < step < 1 and step != 0:
            step = math.copysign(1.0, float(-d))
        self.canvas.yview_scroll(int(step), "units")

    def _sync_tiles_canvas_scroll(self) -> None:
        """Po zwinięciu/rozwinięciu sekcji odśwież wysokość obszaru przewijania."""
        self.tiles_frame.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    # ---------- Discover + rendering ----------
    def _sync_component_lists(self) -> bool:
        """Odświeża listy komponentów. Zwraca True gdy metadane się zmieniły."""
        new_visible = discover_components(self.components_dir)
        new_all = discover_components(self.components_dir, include_hidden=True)
        old_keys = [(c.folder_name, c.name, c.description, c.color, c.order) for c in self._all_components]
        new_keys = [(c.folder_name, c.name, c.description, c.color, c.order) for c in new_all]
        changed = new_keys != old_keys
        self._all_components = new_all
        self._normally_visible = {c.folder_name for c in new_visible}
        self._layout = merge_layout(
            self._layout,
            self._all_components,
            normally_visible=self._normally_visible,
        )
        return changed

    def _refresh_components(self) -> None:
        changed = self._sync_component_lists()
        if not changed and self.tiles_frame.winfo_children():
            return
        self._render_tiles()
        self._sync_tiles_canvas_scroll()
        if not self._all_components:
            self.status_var.set(f"Brak komponentow w {self.components_dir}")
        else:
            self.status_var.set(
                f"Komponentow: {len(self._all_components)} "
                f"(widocznych na siatce: {self._visible_tile_count()})"
            )

    def _visible_tile_count(self) -> int:
        from .launcher_layout import is_tile_visible

        return sum(
            1
            for c in self._all_components
            if is_tile_visible(c.folder_name, self._layout, normally_visible=self._normally_visible)
        )

    def _show_launcher_options(self) -> None:
        show_launcher_options(
            self.root,
            all_components=self._all_components or discover_components(
                self.components_dir, include_hidden=True,
            ),
            normally_visible=self._normally_visible,
            layout=self._layout,
            on_saved=self._apply_launcher_layout,
        )

    def _apply_launcher_layout(self, layout: object) -> None:
        from .launcher_layout import LauncherLayout

        if isinstance(layout, LauncherLayout):
            self._layout = layout
        self._render_tiles()
        self._sync_tiles_canvas_scroll()
        self.status_var.set(
            f"Komponentow: {len(self._all_components)} "
            f"(widocznych na siatce: {self._visible_tile_count()})"
        )

    def _render_tiles(self) -> None:
        self._tile_hover_clearers.clear()
        for child in list(self.tiles_frame.winfo_children()):
            child.destroy()

        if not self._all_components:
            empty = tk.Label(
                self.tiles_frame,
                text=(
                    "Brak komponentow.\n\n"
                    f"Dodaj nowy komponent jako podkatalog w:\n{self.components_dir}\n\n"
                    "Komponent powinien zawierac plik __main__.py.\n"
                    "Opcjonalny component.json definiuje nazwe, opis, ikonke i kolor."
                ),
                bg="#f4f4f7",
                fg="#666",
                font=("Segoe UI", 10),
                justify="center",
                pady=40,
            )
            empty.pack(fill="both", expand=True)
            return

        # Kolumny maja weight=1 zeby calosc rozkladala sie po szerokosci, ale
        # POJEDYNCZY kafelek NIE jest rozciagany (sticky=""). Dzieki temu kazdy
        # ma stale wymiary _TILE_W x _TILE_H i wyswietla sie wysrodkowany w
        # swoim slocie - bez deformacji przy szerokim oknie.
        for i in range(_TILES_PER_ROW):
            self.tiles_frame.columnconfigure(i, weight=1, uniform="tiles")

        sections = resolve_sections(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
        )
        if not sections:
            empty = tk.Label(
                self.tiles_frame,
                text=(
                    "Brak widocznych kafelków.\n\n"
                    "Kliknij „Opcje” w górnym pasku, aby włączyć komponenty\n"
                    "i przypisać je do sekcji."
                ),
                bg="#f4f4f7",
                fg="#666",
                font=("Segoe UI", 10),
                justify="center",
                pady=40,
            )
            empty.pack(fill="both", expand=True)
            return

        # Renderowanie sekcja po sekcji (naglowek rozwijany / zwijany).
        row_cursor = 0
        for sec_idx, (section_title, comps) in enumerate(sections):
            collapsed = self._section_collapsed.get(section_title, False)
            section_outer = tk.Frame(self.tiles_frame, bg="#f4f4f7")
            section_outer.grid(
                row=row_cursor,
                column=0,
                columnspan=_TILES_PER_ROW,
                sticky="ew",
                padx=_TILE_PAD_X,
                pady=(
                    _SECTION_GAP_TOP if sec_idx == 0 else _SECTION_GAP_BETWEEN,
                    0,
                ),
            )
            row_cursor += 1

            header = tk.Frame(section_outer, bg="#ececf1", cursor="hand2")
            header.grid(row=0, column=0, sticky="ew")
            section_outer.columnconfigure(0, weight=1)

            chevron_var = tk.StringVar(value="▶" if collapsed else "▼")
            chevron_lbl = tk.Label(
                header,
                textvariable=chevron_var,
                bg="#ececf1",
                fg="#444",
                font=("Segoe UI", 11),
                width=2,
                anchor="center",
            )
            chevron_lbl.pack(side="left", padx=(6, 2), pady=6)

            title_lbl = tk.Label(
                header,
                text=section_title,
                bg="#ececf1",
                fg="#222",
                font=("Segoe UI", 13, "bold"),
                anchor="w",
            )
            title_lbl.pack(side="left", pady=6)

            count_lbl = tk.Label(
                header,
                text=f"({len(comps)})",
                bg="#ececf1",
                fg="#666",
                font=("Segoe UI", 10),
                anchor="w",
            )
            count_lbl.pack(side="left", padx=(6, 0), pady=6)

            sep = tk.Frame(section_outer, height=1, bg="#dcdce2")
            body = tk.Frame(section_outer, bg="#f4f4f7")
            for i in range(_TILES_PER_ROW):
                body.columnconfigure(i, weight=1, uniform="tiles")

            for i, comp in enumerate(comps):
                sub_row, col = divmod(i, _TILES_PER_ROW)
                tile = self._build_tile(body, comp)
                tile.grid(
                    row=sub_row,
                    column=col,
                    padx=_TILE_PAD_X,
                    pady=_TILE_PAD_Y,
                    sticky="",
                )

            def _toggle(
                *,
                _title: str = section_title,
                _body: tk.Frame = body,
                _sep: tk.Frame = sep,
                _chevron: tk.StringVar = chevron_var,
            ) -> None:
                now_collapsed = not self._section_collapsed.get(_title, False)
                self._section_collapsed[_title] = now_collapsed
                _chevron.set("▶" if now_collapsed else "▼")
                if now_collapsed:
                    _sep.grid_remove()
                    _body.grid_remove()
                else:
                    _sep.grid(row=1, column=0, sticky="ew", pady=(0, 2))
                    _body.grid(row=2, column=0, sticky="ew")
                self._sync_tiles_canvas_scroll()

            for widget in (header, chevron_lbl, title_lbl, count_lbl):
                widget.bind("<Button-1>", lambda _e, fn=_toggle: fn())

            if collapsed:
                sep.grid_remove()
                body.grid_remove()
            else:
                sep.grid(row=1, column=0, sticky="ew", pady=(0, 2))
                body.grid(row=2, column=0, sticky="ew")

    def _show_tile_context_menu(self, event: tk.Event, comp: Component) -> None:
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Uruchom", command=lambda c=comp: self._launch(c))
        m.add_separator()
        m.add_command(label="Pokaz log", command=lambda c=comp: self._show_component_log(c))
        m.add_command(label="Wyczysc log", command=lambda c=comp: self._clear_component_log(c))
        m.add_command(label="Otworz folder komponentu",
                      command=lambda c=comp: self._open_component_dir(c))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _component_log_path(self, comp: Component) -> Path:
        return component_log_read_path(comp.folder_name, logs_dir=_LOGS_DIR)

    def _component_log_write_path(self, comp: Component) -> Path:
        return component_log_write_path(comp.folder_name, logs_dir=_LOGS_DIR)

    def _show_component_log(self, comp: Component) -> None:
        path = self._component_log_path(comp)
        win = tk.Toplevel(self.root)
        win.title(f"Log: {comp.name}")
        position_toplevel_screen_center(win, 900, 560)
        try:
            win.transient(self.root)
        except tk.TclError:
            pass

        header = ttk.Frame(win, padding=(10, 6))
        header.pack(fill="x")
        ttk.Label(
            header, text=f"Log komponentu: {comp.name}",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")
        ttk.Label(
            header, text=str(path), foreground="#777",
        ).pack(side="left", padx=(10, 0))

        text_frame = ttk.Frame(win)
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        txt = tk.Text(text_frame, wrap="none", font=("Consolas", 9),
                      bg="#1e1e1e", fg="#d4d4d4", insertbackground="#fff")
        sb_v = ttk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
        sb_h = ttk.Scrollbar(text_frame, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        txt.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        def _reload() -> None:
            content = ""
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError as e:
                    content = f"(nie udalo sie odczytac: {e})"
            else:
                content = "(plik jeszcze nie istnieje - uruchom komponent zeby zobaczyc logi)"
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", content)
            txt.see("end")
            txt.configure(state="disabled")

        _reload()

        btn_row = ttk.Frame(win, padding=(10, 4))
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Odswiez", command=_reload).pack(side="left")
        ttk.Button(btn_row, text="Otworz plik",
                   command=lambda: self._open_log_file(path)).pack(side="left", padx=(6, 0))

        # Auto-odswiezaj co 2s jesli komponent dziala
        def _auto() -> None:
            if not win.winfo_exists():
                return
            _reload()
            win.after(2000, _auto)
        win.after(2000, _auto)

        ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right")

    def _clear_component_log(self, comp: Component) -> None:
        path = self._component_log_write_path(comp)
        if path.is_file():
            try:
                path.write_text("", encoding="utf-8")
                self.status_var.set(f"Wyczyszczono log: {comp.name}")
            except OSError as e:
                messagebox.showerror("Logi", f"Nie udalo sie wyczyscic:\n{e}")

    def _open_component_dir(self, comp: Component) -> None:
        try:
            comp_path = self.components_dir / comp.folder_name
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(comp_path))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(comp_path)])  # noqa: S607
            else:
                subprocess.Popen(["xdg-open", str(comp_path)])  # noqa: S607
        except OSError:
            pass

    def _open_log_file(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(path))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])  # noqa: S607
            else:
                subprocess.Popen(["xdg-open", str(path)])  # noqa: S607
        except OSError:
            pass

    def _build_tile(self, parent: tk.Misc, comp: Component) -> tk.Frame:
        # Tla - normalne i hover (subtle szary).
        BG_NORMAL = "#ffffff"
        BG_HOVER = "#f0f2f7"

        # KLUCZOWE FIXY na "miganie / dziwne ksztalty / zmniejszanie sie":
        #
        # 1) pack_propagate(False) zamiast grid_propagate(False).
        #    Outer ma DZIECI PAKOWANE (accent.pack, body.pack), wiec to
        #    pack_propagate kontroluje czy outer rosnie/zweza sie pod presja
        #    swoich dzieci. grid_propagate na nim NIE robil nic - dlatego
        #    najmniejsze zmiany w srodku (focus na buttonie, relief change)
        #    propagowaly sie na caly kafelek = "zmniejszanie".
        #
        # 2) Hover zmienia TYLKO bg (kolor tla) wszystkich dzieci - bez
        #    ruszania ramki, paddingow, fontow czy reliefu. Zero zmian
        #    geometrycznych = zero flickeru.
        #
        # 3) Button ma highlightthickness=0 + takefocus=False, zeby focus
        #    ring nie powodowal subtelnego resize'u przy klikach.
        outer = tk.Frame(
            parent, bg=BG_NORMAL, bd=0,
            highlightthickness=1,
            highlightbackground="#dcdce2",
            highlightcolor="#dcdce2",
            width=_TILE_W, height=_TILE_H,
        )
        outer.pack_propagate(False)

        accent = tk.Frame(outer, bg=comp.color, width=6)
        accent.pack(side="left", fill="y")

        body = tk.Frame(outer, bg=BG_NORMAL)
        body.pack(side="left", fill="both", expand=True, padx=14, pady=12)

        title_row = tk.Frame(body, bg=BG_NORMAL)
        title_row.pack(fill="x")
        if comp.icon:
            tk.Label(
                title_row, text=comp.icon, bg=BG_NORMAL,
                font=("Segoe UI Emoji", 18),
            ).pack(side="left", padx=(0, 8))
        tk.Label(
            title_row, text=comp.name, bg=BG_NORMAL,
            font=("Segoe UI", 13, "bold"), fg="#222",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        if comp.description:
            tk.Label(
                body, text=comp.description, bg=BG_NORMAL,
                font=("Segoe UI", 9), fg="#555",
                wraplength=_TILE_W - 50, justify="left", anchor="w",
            ).pack(fill="x", pady=(6, 0))

        tk.Frame(body, bg=BG_NORMAL).pack(fill="both", expand=True)
        run_btn = tk.Button(
            body, text="Uruchom",
            bg=comp.color, fg="white",
            activebackground=self._darken(comp.color),
            activeforeground="white",
            relief="flat", bd=0, padx=14, pady=4,
            highlightthickness=0,
            takefocus=False,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            command=lambda c=comp: self._launch(c),
        )
        run_btn.pack(side="right")

        # Zbierz wszystkie widgety, ktorym zmieniamy bg na hover - pomijamy
        # przycisk (ma swoje tlo) i kolorowy accent po lewej.
        bg_widgets: list[tk.Widget] = []

        def _collect_bg(widget: tk.Widget) -> None:
            if widget is run_btn or widget is accent:
                return
            bg_widgets.append(widget)
            for child in widget.winfo_children():
                _collect_bg(child)

        _collect_bg(outer)

        def _set_hover(active: bool) -> None:
            new_bg = BG_HOVER if active else BG_NORMAL
            for w in bg_widgets:
                try:
                    w.configure(bg=new_bg)
                except tk.TclError:
                    pass

        self._tile_hover_clearers.append(lambda: _set_hover(False))

        def _on_enter(_evt: object) -> None:
            if time.monotonic() < self._suppress_tile_hover_until:
                return
            _set_hover(True)

        def _on_leave(_evt: object) -> None:
            if time.monotonic() < self._suppress_tile_hover_until:
                return
            # W Tk rodzic dostaje <Leave> gdy mysz wjedzie na DZIECKO.
            # Sprawdzamy czy mysz wciaz jest w bbox outer-a - jesli tak,
            # ignorujemy (nie ma faktycznego opuszczenia kafelka).
            try:
                px, py = outer.winfo_pointerxy()
                ox, oy = outer.winfo_rootx(), outer.winfo_rooty()
                ow, oh = outer.winfo_width(), outer.winfo_height()
            except tk.TclError:
                return
            if ox <= px < ox + ow and oy <= py < oy + oh:
                return
            _set_hover(False)

        def _on_click(_evt: object, c: Component = comp) -> None:
            self._launch(c)

        def _on_right_click(evt: tk.Event, c: Component = comp) -> None:
            self._show_tile_context_menu(evt, c)

        def _bind_recursive(widget: tk.Widget) -> None:
            widget.bind("<Enter>", _on_enter, add="+")
            widget.bind("<Leave>", _on_leave, add="+")
            widget.bind("<Button-3>", _on_right_click, add="+")
            if widget is not run_btn:
                widget.bind("<Button-1>", _on_click, add="+")
                try:
                    widget.configure(cursor="hand2")
                except tk.TclError:
                    pass
            for child in widget.winfo_children():
                _bind_recursive(child)

        _bind_recursive(outer)
        return outer

    @staticmethod
    def _darken(hex_color: str) -> str:
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r, g, b = max(0, r - 30), max(0, g - 30), max(0, b - 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return hex_color

    # ---------- Launching ----------
    def _launch(self, comp: Component) -> None:
        # Tryby:
        #  - "url"       -> otworz w przegladarce
        #  - "inline"    -> zamontuj widok wewnatrz launchera (back wraca do siatki)
        #  - "subprocess"-> osobny proces python -m Komponenty.<x>
        if comp.mode == "url":
            url = (comp.url or "").strip()
            if not url:
                messagebox.showwarning(comp.name, "Brak URL w component.json (pole \"url\").")
                return
            try:
                webbrowser.open(url)
                self.status_var.set(f"Otwarto w przegladarce: {url}")
            except Exception as e:  # noqa: BLE001
                messagebox.showerror(comp.name, f"Nie udalo sie otworzyc:\n{url}\n\n{e}")
            return

        if comp.mode == "inline":
            self._show_inline(comp)
            return

        # ----- subprocess (default) -----
        cwd = get_component_cwd()
        prefix, py_err = resolve_python_interpreter()
        if prefix is None:
            messagebox.showerror(
                "Brak Pythona",
                f"Nie mozna uruchomic komponentu '{comp.name}'.\n\n{py_err}",
            )
            return
        cmd = [*prefix, "-m", comp.module_path]
        # Przekierowanie stdout/stderr do logs/<component>.log (append)
        log_path = self._component_log_write_path(comp)
        try:
            log_f = open(log_path, "a", encoding="utf-8", buffering=1)
            from datetime import datetime as _dt
            log_f.write(f"\n\n========== {_dt.now().isoformat()} start ==========\n")
            log_f.flush()
        except OSError:
            log_f = None
        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                cwd=str(cwd),
                stdout=log_f or subprocess.DEVNULL,
                stderr=subprocess.STDOUT if log_f else subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except OSError as e:
            if log_f:
                try:
                    log_f.close()
                except OSError:
                    pass
            messagebox.showerror(
                "Blad uruchomienia",
                f"Nie udalo sie uruchomic komponentu '{comp.name}':\n\n{e}",
            )
            return
        self._running_procs.append(proc)
        self.status_var.set(f"Uruchomiono: {comp.name} (PID {proc.pid})")
        # W tle czekaj az sie skonczy zeby wyczyscic liste + zamknac plik logu
        threading.Thread(
            target=self._watch_proc, args=(proc, comp.name, log_f), daemon=True,
        ).start()

    def _watch_proc(self, proc: subprocess.Popen, name: str, log_f: Any = None) -> None:
        rc = proc.wait()
        if log_f is not None:
            try:
                from datetime import datetime as _dt
                log_f.write(f"\n========== {_dt.now().isoformat()} exit code {rc} ==========\n")
                log_f.flush()
                log_f.close()
            except OSError:
                pass
        try:
            self._running_procs.remove(proc)
        except ValueError:
            pass
        msg = f"Zakonczono: {name} (kod {rc})"
        try:
            self.root.after(0, lambda: self.status_var.set(msg))
        except RuntimeError:
            pass

    # ---------- Inline view swap ----------
    def _show_inline(self, comp: Component) -> None:
        """Zamiast siatki kafelkow pokaz widok komponentu inline.

        Komponent musi miec `view.py` z funkcja:
            build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget
        """
        try:
            mod = importlib.import_module(comp.view_module_path)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(
                comp.name,
                f"Nie udalo sie zaladowac widoku komponentu:\n{e}",
            )
            return
        builder = getattr(mod, "build_view", None)
        if not callable(builder):
            messagebox.showerror(
                comp.name,
                f"Komponent '{comp.folder_name}' nie ma funkcji build_view(parent, on_back) w view.py.",
            )
            return

        # Przygotuj host frame dla widoku komponentu
        if self._inline_host is not None:
            try:
                self._inline_host.destroy()
            except tk.TclError:
                pass
            self._inline_host = None

        entering_from_tiles = self.tiles_view.winfo_ismapped()
        # Schowaj siatke
        self.tiles_view.pack_forget()

        if entering_from_tiles:
            self._geometry_before_inline = self.root.geometry()

        self._inline_host = ttk.Frame(self._body_container)
        self._inline_host.pack(fill="both", expand=True)

        on_back = self._next_inline_on_back if self._next_inline_on_back else self._show_tiles
        self._next_inline_on_back = None

        try:
            try:
                view = builder(
                    self._inline_host,
                    on_back,
                    on_open_component=self._open_component_by_folder,
                )
            except TypeError:
                view = builder(self._inline_host, on_back)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(comp.name, f"Blad budowy widoku:\n{e}")
            self._show_tiles()
            return

        self._current_inline_folder = comp.folder_name

        # Komponent moze sam pakowac siebie; jesli nie, wepchniemy go
        if isinstance(view, (tk.Widget, ttk.Frame)):
            try:
                view.pack(fill="both", expand=True)
            except tk.TclError:
                pass

        self._inline_view = view
        self.status_var.set(f"Otwarto: {comp.name}")
        if comp.folder_name in ("finanse", "kpir", "dnr", "dokumentysprzedazy"):
            try:
                from Komponenty._shared.finance_navigation import register_open_callback

                register_open_callback(self._open_component_by_folder)
            except ImportError:
                pass
        self.root.after_idle(lambda c=comp: self._apply_inline_window_size(c))

    def _restore_launcher_window_size(self) -> None:
        """Domyślny rozmiar okna startowego po powrocie z widoku inline."""
        self._geometry_before_inline = None
        self.root.minsize(LAUNCHER_MIN_WIDTH, LAUNCHER_MIN_HEIGHT)
        position_toplevel_screen_center(self.root, LAUNCHER_WIDTH, LAUNCHER_HEIGHT)

    def _apply_inline_window_size(self, comp: Component) -> None:
        """Powieksza okno pod widok inline, jesli komponent podaje inline_width/height w component.json."""
        try:
            w = int(comp.extras.get("inline_width") or 0)
            h = int(comp.extras.get("inline_height") or 0)
        except (TypeError, ValueError):
            return
        if w <= 0 or h <= 0:
            return
        try:
            min_w = int(comp.extras.get("inline_min_width") or w)
            min_h = int(comp.extras.get("inline_min_height") or h)
        except (TypeError, ValueError):
            min_w, min_h = w, h
        self.root.update_idletasks()
        req_w = max(w, self.root.winfo_reqwidth(), min_w)
        req_h = max(h, self.root.winfo_reqheight(), min_h)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        req_w = min(req_w, max(LAUNCHER_MIN_WIDTH, sw - 40))
        req_h = min(req_h, max(LAUNCHER_MIN_HEIGHT, sh - 80))
        self.root.minsize(min(LAUNCHER_MIN_WIDTH, req_w), min(LAUNCHER_MIN_HEIGHT, req_h))
        position_toplevel_screen_center(self.root, req_w, req_h)

    def _component_by_folder(self, folder_name: str) -> Component | None:
        pool = self._all_components or discover_components(self.components_dir, include_hidden=True)
        return next((c for c in pool if c.folder_name == folder_name), None)

    def _return_to_finanse_hub(self) -> None:
        comp = self._component_by_folder("finanse")
        if comp is None:
            self._show_tiles()
            return
        self._next_inline_on_back = None
        self._show_inline(comp)

    def _open_component_by_folder(self, folder_name: str) -> None:
        """Otwiera ukryty lub widoczny komponent inline (np. z huba Finanse)."""
        comp = self._component_by_folder(folder_name)
        if comp is None:
            messagebox.showwarning("Księgowość", f"Nie znaleziono komponentu: {folder_name}")
            return
        if comp.mode != "inline":
            self._launch(comp)
            return
        parent = self._current_inline_folder
        if parent == "finanse" and folder_name != "finanse":
            self._next_inline_on_back = self._return_to_finanse_hub
        self._show_inline(comp)

    def _ensure_tiles_wheel_binding(self) -> None:
        """Przywraca scroll siatki kafelkow (inline komponenty nie moga robic unbind_all)."""
        try:
            self.root.bind_all("<MouseWheel>", self._on_canvas_mousewheel)
            self._bind_launcher_shortcuts()
        except tk.TclError:
            pass

    def _show_tiles(self) -> None:
        """Wraca do siatki kafelkow z widoku inline."""
        if self._inline_host is not None:
            try:
                self._inline_host.destroy()
            except tk.TclError:
                pass
            self._inline_host = None
        self._inline_view = None
        self._current_inline_folder = None
        self._next_inline_on_back = None
        self._restore_launcher_window_size()
        if not self.tiles_view.winfo_ismapped():
            self.tiles_view.pack(fill="both", expand=True)
        self._ensure_tiles_wheel_binding()
        self.root.after_idle(self._focus_tiles_canvas)
        self.status_var.set("")

    # ---------- Misc ----------
    def _open_components_dir(self) -> None:
        path = self.components_dir
        if not path.exists():
            messagebox.showwarning(
                "Brak folderu",
                f"Folder Komponenty nie istnieje:\n{path}",
            )
            return
        # Otwiera w Explorerze (Windows) / Finderze (macOS) / xdg-open (Linux)
        try:
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])  # noqa: S607
            else:
                subprocess.Popen(["xdg-open", str(path)])  # noqa: S607
        except OSError:
            webbrowser.open(path.as_uri())

    def _auto_rescan(self) -> None:
        # Co 3 sekundy sprawdzaj czy pojawil sie nowy komponent.
        try:
            self._refresh_components()
        finally:
            self.root.after(3000, self._auto_rescan)

    # ---------- Reminders ----------
    def _check_monthly_plan_reminder(self) -> None:
        """1-szy dzien miesiaca: pokaz przypomnienie o wygenerowaniu planu marketingowego.

        Stan zapisujemy w `Komponenty/zadania/data/reminders.json` pod kluczem
        'monthly_plan' (wartosc = 'YYYY-MM' miesiaca, w ktorym przypomnienie zostalo
        juz pokazane). Dzieki temu nie pojawia sie 2x tego samego dnia ani nie
        wraca, jesli uzytkownik zignoruje i otworzy launcher znow.
        """
        today = date.today()
        if today.day != 1:
            return
        try:
            from Komponenty.zadania import storage as tasks_storage
        except ImportError:
            return
        try:
            reminders = tasks_storage.load_reminders()
        except Exception:  # noqa: BLE001
            return
        current_key = today.strftime("%Y-%m")
        if reminders.get("monthly_plan") == current_key:
            return  # juz pokazane w tym miesiacu

        # Polskie nazwy miesiecy (zeby nie polegac na lokalu OS-a)
        miesiace = {
            1: "styczen", 2: "luty", 3: "marzec", 4: "kwiecien", 5: "maj", 6: "czerwiec",
            7: "lipiec", 8: "sierpien", 9: "wrzesien", 10: "pazdziernik",
            11: "listopad", 12: "grudzien",
        }
        nazwa_msc = miesiace.get(today.month, str(today.month))
        msg = (
            f"Pierwszy dzien nowego miesiaca ({nazwa_msc} {today.year}).\n\n"
            "Czas wygenerowac plan marketingowy na kolejne 30 dni:\n"
            "  • nowe sygnaly z Shopify (produkty, autorzy, kolekcje),\n"
            "  • nadchodzace swieta i wydarzenia,\n"
            "  • 18-20 zadan rozsianych po kanalach social/blog/newsletter.\n\n"
            "Otworzyc Generator zadan (komponent 'Zadania') teraz?"
        )
        try:
            answer = messagebox.askyesno(
                "Plan marketingowy na nowy miesiac",
                msg,
                parent=self.root,
            )
        except tk.TclError:
            return
        # Zapisz fakt pokazania - niezaleznie od odpowiedzi (nie przypominamy 2x dziennie)
        try:
            tasks_storage.mark_reminder_shown("monthly_plan", current_key)
        except Exception:  # noqa: BLE001
            pass
        if answer:
            self._open_zadania_generator()

    def _open_zadania_generator(self) -> None:
        """Otwiera komponent 'zadania' inline + uruchamia jego generator LLM."""
        comp = next((c for c in self._all_components if c.folder_name == "zadania"), None)
        if comp is None:
            messagebox.showwarning(
                "Brak komponentu",
                "Nie znaleziono komponentu 'zadania'. Sprawdz folder Komponenty/.",
                parent=self.root,
            )
            return
        # Pokaz inline view zadan
        self._show_inline(comp)
        # Po krotkim czasie odpal okno generatora w nowym oknie
        try:
            from Komponenty.zadania.generator_zadan import open_tasks_generator
        except ImportError as e:
            messagebox.showerror("Brak komponentu", str(e), parent=self.root)
            return
        self.root.after(500, lambda: open_tasks_generator(self.root, on_saved=lambda _n: None))

    # ---------- Monthly reminder (plan marketingowy) ----------
    def _check_monthly_reminder(self) -> None:
        """Pierwszego dnia kazdego miesiaca (albo w 1-5 dnia jesli dzis pierwsze uruchomienie
        w tym miesiacu) proponujemy wygenerowanie nowego planu marketingowego.

        Zapisujemy w `Komponenty/zadania/data/reminders.json` klucz 'monthly_plan'
        z wartoscia 'YYYY-MM' - zeby nie pokazywac wiecej niz raz w miesiacu.
        """
        from datetime import date

        try:
            # Leniwy import - jesli komponent zadania jeszcze niezaimportowany, zrobmy to teraz
            from Komponenty.zadania import storage as z_storage
        except ImportError:
            return

        today = date.today()
        current_month_key = f"{today.year:04d}-{today.month:02d}"

        # Pokazujemy tylko w 1-5 dniu miesiaca, i tylko raz na miesiac
        if today.day > 5:
            return

        reminders = z_storage.load_reminders()
        last_shown = str(reminders.get("monthly_plan") or "")
        if last_shown == current_month_key:
            return  # juz pokazane w tym miesiacu

        # Pokaz dialog - pod nim oznacz ze pokazalismy (nawet jesli user anuluje)
        z_storage.mark_reminder_shown("monthly_plan", current_month_key)

        open_now = messagebox.askyesno(
            "Nowy miesiac - plan marketingowy",
            f"Jest {today.isoformat()} - czas na plan marketingowy na ten miesiac!\n\n"
            "Generator zadan pobierze sygnaly z Shopify (nowe produkty, kolekcje, autorzy), "
            "kalendarz swiat per rynek i zbuduje prompt do LLM na ~15-20 zadan.\n\n"
            "Otworzyc Generator Zadan teraz?",
        )
        if open_now:
            self._open_monthly_generator()

    def _open_monthly_generator(self) -> None:
        """Otwiera generator zadan marketingowych (komponent 'zadania')."""
        try:
            from Komponenty.zadania.generator_zadan import open_tasks_generator
        except ImportError as e:
            messagebox.showerror(
                "Brak komponentu",
                f"Nie mozna otworzyc Generatora zadan:\n{e}",
            )
            return
        open_tasks_generator(self.root)

    # ---------- Auto backup ----------
    def _run_daily_backup(self) -> None:
        """Odpalamy raz dziennie auto-backup (idempotentne - pomijane jesli juz byl)."""

        def _worker() -> None:
            try:
                from Komponenty._shared import backup
                result = backup.run_daily_backup_if_needed(logger=lambda m: None)
            except Exception as exc:  # noqa: BLE001
                try:
                    self.root.after(0, lambda: self.status_var.set(
                        f"Backup: blad ({exc})"
                    ))
                except RuntimeError:
                    pass
                return
            if result is not None:
                try:
                    self.root.after(0, lambda: self.status_var.set(
                        f"Backup: utworzono {result.name}"
                    ))
                except RuntimeError:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    # ---------- Cure completion notifications ----------
    def _check_cure_done_notifications(self) -> None:
        """Raz na minute sprawdza czy ktoras ramka wlasnie skonczyla utwardzanie.

        Gdy znajdzie - wysyla Windows toast. Zapisuje w sync_state ID zamowien,
        dla ktorych juz pokazano powiadomienie, zeby nie spamowac.
        """

        def _worker() -> None:
            try:
                import json as _json
                from datetime import datetime as _dt
                from datetime import timedelta as _td
                from Komponenty._shared.notifications import notify
            except ImportError:
                return
            orders_file = self.components_dir.parent / "Komponenty" / "produkcja" / "dane" / "zamowienia.json"
            if not orders_file.is_file():
                return
            try:
                db = _json.loads(orders_file.read_text(encoding="utf-8"))
            except (OSError, _json.JSONDecodeError):
                return
            notified_file = self.components_dir.parent / "Komponenty" / "produkcja" / "dane" / "notified.json"
            try:
                notified = _json.loads(notified_file.read_text(encoding="utf-8")) if notified_file.is_file() else {}
            except _json.JSONDecodeError:
                notified = {}
            notified_cure = set(notified.get("cure_done", []))
            changed = False
            now = _dt.now()
            for o in db.get("orders", []):
                if int(o.get("ramka_step") or 0) < 4:
                    continue
                raw = o.get("data_pomalowania")
                if not raw:
                    continue
                try:
                    start = _dt.fromisoformat(str(raw))
                except ValueError:
                    continue
                end = start + _td(hours=72)
                # Pokazujemy powiadomienie gdy minelo end + 0-60s (pierwszy tick po skonczeniu)
                if now < end:
                    continue
                elapsed_since_end = (now - end).total_seconds()
                if elapsed_since_end > 3600:
                    # Zbyt dawno skonczone - pewnie uzytkownik juz wiedzial, pomijamy
                    notified_cure.add(o.get("id"))
                    changed = True
                    continue
                oid = o.get("id")
                if oid in notified_cure:
                    continue
                # Toast!
                title = "Ramka utwardzona"
                msg = (f"{oid}: {o.get('tytul_obrazu') or '(bez tytulu)'} "
                       f"- mozesz sklada elementy.")
                notify(title, msg)
                notified_cure.add(oid)
                changed = True
            if changed:
                try:
                    notified_file.parent.mkdir(parents=True, exist_ok=True)
                    notified["cure_done"] = sorted(x for x in notified_cure if x)
                    notified_file.write_text(
                        _json.dumps(notified, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                except OSError:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
        try:
            self.root.after(60_000, self._check_cure_done_notifications)
        except RuntimeError:
            pass

    # ---------- Shopify orders polling ----------
    def _poll_orders_from_shopify(self) -> None:
        """Co 5 minut probujemy ciagnac nowe zamowienia z Shopify."""

        def _worker() -> None:
            try:
                from Komponenty.produkcja import orders_sync
            except ImportError:
                return
            try:
                added = orders_sync.sync_orders(logger=lambda m: None)
            except Exception as exc:  # noqa: BLE001
                try:
                    self.root.after(0, lambda: self.status_var.set(
                        f"Produkcja: blad synchronizacji ({exc})"
                    ))
                except RuntimeError:
                    pass
                return
            if added:
                first_client = added[0].get("client") or "(bez nazwy)"
                first_no = added[0].get("shopify_order_no") or "?"
                msg = (
                    f"Produkcja: {len(added)} nowe zamowienie(a) z Shopify "
                    f"(pierwsze: {first_no} / {first_client})"
                )
                try:
                    self.root.after(0, lambda: self.status_var.set(msg))
                    from Komponenty._shared.toast import show_toast
                    self.root.after(0, lambda: show_toast(
                        self.root, msg, duration_ms=3000,
                    ))
                except (RuntimeError, ImportError):
                    pass
                # Dodatkowo - systemowy toast Windows (zeby uzytkownik zobaczyl
                # nawet gdy GicleeApp nie jest aktywnym oknem)
                try:
                    from Komponenty._shared.notifications import notify
                    notify(
                        f"Nowe zamowienie: {first_no}",
                        f"{first_client} - dodano {len(added)} pozycji.",
                    )
                except ImportError:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
        # Zaplanuj nastepny sync za 5 minut
        try:
            self.root.after(5 * 60 * 1000, self._poll_orders_from_shopify)
        except RuntimeError:
            pass

    def _poll_accounting_orders(self) -> None:
        """Co 5 minut — nowe opłacone zamówienia bez dokumentu (panel księgowy)."""

        def _worker() -> None:
            try:
                from Komponenty.dokumentysprzedazy.orders_sync import sync_accounting_orders
                from Komponenty._shared.finance_navigation import set_nav
                from Komponenty._shared.notifications import notify
            except ImportError:
                return
            try:
                new_rows = sync_accounting_orders(days_back=30)
            except Exception as exc:  # noqa: BLE001
                try:
                    self.root.after(0, lambda: self.status_var.set(
                        f"Księgowość: błąd sync Shopify ({exc})"
                    ))
                except RuntimeError:
                    pass
                return
            if not new_rows:
                return
            first = new_rows[0]
            name = first.get("shopify_order_name") or "?"
            client = first.get("customer_name") or ""
            msg = f"{len(new_rows)} nowe zamówienie(a) — pierwsze: {name}"
            if client:
                msg += f" ({client})"
            try:
                self.root.after(0, lambda: self.status_var.set(f"Księgowość: {msg}"))
                from Komponenty._shared.toast import show_toast
                self.root.after(0, lambda: show_toast(
                    self.root, f"Księgowość: {msg}", duration_ms=4000,
                ))
            except (RuntimeError, ImportError):
                pass
            try:
                notify(f"Nowe zamówienie: {name}", msg)
            except ImportError:
                pass
            try:
                oid = str(first.get("shopify_order_id") or "")
                if oid:
                    set_nav("dokumentysprzedazy", "orders", oid)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
        try:
            self.root.after(5 * 60 * 1000, self._poll_accounting_orders)
        except RuntimeError:
            pass

    # ---------- Cykl social-media publisher ----------
    def _poll_cykl_publisher(self) -> None:
        """Co 60s sprawdza kolejke cyklu i publikuje posty ktorych nadszedl czas.

        Dziala TYLKO gdy w config.json auto_publish=True. Inaczej zwraca natychmiast.
        """

        def _worker() -> None:
            try:
                from Komponenty.socialmedia.cykl import meta_publisher as cmp
            except ImportError:
                return
            try:
                results = cmp.publish_due_items(logger=lambda m: None)
            except Exception as exc:  # noqa: BLE001
                try:
                    self.root.after(0, lambda: self.status_var.set(
                        f"Cykl: blad publishera ({exc})"
                    ))
                except RuntimeError:
                    pass
                return
            if results:
                succ = sum(1 for _, r in results for v in r.values() if v.startswith("done@"))
                err = sum(1 for _, r in results for v in r.values() if v.startswith("error"))
                msg = f"Cykl: opublikowano {len(results)} pozycji ({succ} OK, {err} blad)"
                try:
                    self.root.after(0, lambda: self.status_var.set(msg))
                    from Komponenty._shared.notifications import notify
                    notify("Cykl social-media", msg)
                except (RuntimeError, ImportError):
                    pass

        threading.Thread(target=_worker, daemon=True).start()
        try:
            self.root.after(60_000, self._poll_cykl_publisher)
        except RuntimeError:
            pass

    def _check_cykl_weekly_reminder(self) -> None:
        """Po starcie: sprawdz czy zostalo <=2 dni wygenerowanej tresci dla cyklu.

        Jesli tak - pokaz toast / messagebox. Nie irytujemy za czesto - info tylko raz
        na uruchomienie launchera (stan w pamieci procesu).
        """
        if getattr(self, "_cykl_reminder_shown", False):
            return
        try:
            from Komponenty.socialmedia.cykl import scheduler as cs
            from Komponenty.socialmedia.cykl import storage as cst
        except ImportError:
            return
        try:
            items = cst.load_queue()
        except Exception:  # noqa: BLE001
            return
        if not items:
            return
        days_left = cs.days_of_content_left(items)
        gen_until = cs.generated_until(items)
        if not gen_until:
            return
        if days_left > 2:
            return
        self._cykl_reminder_shown = True
        msg = (
            f"Cykl social-media: tresc wygenerowana tylko do {gen_until} "
            f"(zostalo {days_left} dni).\n\n"
            "Otworz Marketing -> Social Media -> Cykl i kliknij "
            "'Generuj tresc tygodnia' aby zaktualizowac."
        )
        try:
            from Komponenty._shared.notifications import notify
            notify("Cykl - czas wygenerowac tresc", msg)
        except ImportError:
            pass
        try:
            self.status_var.set(f"Cykl: zostalo tylko {days_left} dni tresci!")
        except tk.TclError:
            pass

    # ---------- Help ----------
    def _show_token_setup(self) -> None:
        """Checklista OAuth / tokenów (CHECKLIST_SETUP.md w katalogu cursor-api)."""
        path = get_bundle_root() / "CHECKLIST_SETUP.md"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            messagebox.showerror(
                "Token setup",
                f"Nie mozna odczytac checklisty:\n{path}\n\n{e}",
            )
            return
        try:
            from Komponenty._shared.help_dialog import show_help
        except ImportError:
            messagebox.showinfo("Token setup", text[:8000])
            return
        show_help(self.root, title="Token setup (Shopify + Meta)", text=text)

    def _show_session_status(self) -> None:
        from .session_status import format_session_status_text

        text = format_session_status_text()
        try:
            from Komponenty._shared.help_dialog import show_help

            show_help(self.root, title="Stan sesji / NBP / konfiguracja Partners", text=text)
        except ImportError:
            messagebox.showinfo("Stan sesji", text)

    def _show_theme_dev(self) -> None:
        try:
            from Komponenty._shared.theme_dev_gui import open_theme_dev_preview

            open_theme_dev_preview(
                self.root,
                status_var=self.status_var,
                app_title=APP_TITLE,
            )
        except ImportError as exc:
            messagebox.showerror("Theme dev", f"Nie udalo sie zaladowac modulu:\n{exc}")

    def _close_theme_dev_ports(self) -> None:
        try:
            from Komponenty.stronaglowna import home_features as home_features_mod
            from Komponenty.stronaglowna.service import theme_dev_port_open
            from Komponenty._shared.toast import show_toast
        except ImportError as exc:
            messagebox.showerror("Zamknij porty", f"Nie udalo sie zaladowac modulu:\n{exc}")
            return

        lines: list[str] = []
        home_features_mod.restart_theme_dev_port(on_line=lines.append)
        if lines:
            msg = lines[0]
        elif theme_dev_port_open():
            msg = "Port 9292 nadal zajęty — zamknij proces ręcznie."
        else:
            msg = "Port 9292 zwolniony (theme dev zatrzymany)."
        self.status_var.set(msg)
        show_toast(self.root, msg)

    def _show_activity_log(self) -> None:
        try:
            from Komponenty._shared.activity_log_ui import open_activity_log_dialog

            open_activity_log_dialog(self.root, title="Dziennik akcji")
        except ImportError as exc:
            messagebox.showerror("Dziennik akcji", f"Nie udalo sie zaladowac modulu:\n{exc}")

    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
        except ImportError:
            messagebox.showinfo("Instrukcja", _GICLEE_HELP)
            return
        show_help(self.root, title="Instrukcja - GicleeApp", text=_GICLEE_HELP)


_GICLEE_HELP = """# GicleeApp - Launcher komponentow

GicleeApp to glowne okno startowe twoich narzedzi. Z poziomu kafelkow
uruchamiasz pojedyncze aplikacje (komponenty) - kazda dziala w **wlasnym
procesie**, wiec ewentualny crash jednego komponentu NIE polozy launchera.

## Jak uruchomic komponent
1. Kliknij dowolne miejsce na kafelku (cala karta jest klikalna).
2. Albo kliknij niebieski/zielony/pomaranczowy przycisk **Uruchom** w prawym dolnym rogu.
3. Komponent otworzy sie w nowym oknie. Mozesz miec wiele komponentow otwartych jednoczesnie.

## Skroty klawiszowe (siatka kafelkow)
- **i** — uruchom **Integracja z GPT** (`integracjagpt`). Dziala tylko na glownej siatce
  (nie w widoku inline ani w otwartym dialogu). Bez Ctrl/Alt/Win.

## Toolbar w prawym gornym rogu
- **Token setup** - checklista OAuth Shopify + Meta (`CHECKLIST_SETUP.md`).
- **Stan sesji** - podglad `.shopify_session.json`, cache kursow NBP, mtime / git dla `shopify.app.toml`.
- **Theme dev…** - lokalny podglad motywu Shopify (`shopify theme dev` → http://127.0.0.1:9292).
- **Zamknij porty** - zatrzymuje theme dev i zwalnia port 9292 (np. zawieszony proces).
- **Dziennik akcji** - ostatnie wpisy z komponentow (np. batch w dodajobraz).
- **Opcje** - układ kafelków: sekcja (nagłówek), widoczność, kolejność w sekcji. Zapis lokalny w `giclee_app/data/launcher_layout.json`.
- **Instrukcja** - to okno.
- **Odswiez** - rescanuje folder `Komponenty/` szukajac nowych aplikacji (i tak robi to co 3s automatycznie).
- **Otworz folder Komponenty** - pokazuje folder w Eksploratorze. Tu trafiaja wszystkie komponenty.

## Dodawanie nowego komponentu
1. Utworz nowy folder w `cursor-api/Komponenty/<nazwa>/`.
2. Dodaj plik `__main__.py` (uruchamiany przez `python -m Komponenty.<nazwa>`).
3. Opcjonalnie utworz `component.json` z metadanymi:
   ```
   {
     "name": "Twoj komponent",
     "description": "Krotki opis (1-2 linie)",
     "icon": "🎨",
     "color": "#1e88e5",
     "order": 40
   }
   ```
4. Kafelek pojawi sie w GicleeApp w ciagu 3 sekund (auto-rescan).

## Sekcje glownego widoku
Komponenty pogrupowane sa w sekcje (kazda z naglowkiem). Kliknij naglowek
lub strzalke, zeby zwinac / rozwinac sekcje — latwiej nawigowac przy wielu kafelkach.

### Administracja produktu
- **Dodaj obraz** (`dodajobraz`) - tworzenie produktow w Shopify na podstawie zdjecia.
- **Aktualizuj opis** (`aktualizujopis`) - podmiana akapitow opisu z JSON LLM (lista produktow, 7 jezykow).
- **Zmien ceny** (`zmienceny`) - masowa aktualizacja cen wariantow + markup per rynek (Rynki).
- **Wybor szablonu produktu** (`wyborszablonu`) - lista produktow z przypisanym szablonem wariantow; przypisanie, zmiana nazwy, nowy/kopia.
- **Zmien tytuly** (`zmietytuly`) - generator promptu do zmiany tytulow produktu (Cursor).
- **Nazwij obraz** (`nazwijobraz`) - automatyczna zmiana nazw plikow na "Autor - Tytul".
- **Pobierz obraz** (`pobierzobraz`) - pobieranie pelnych obrazow IIIF (np. National Gallery).
- **Squoosh WebP** (`squoosh`) - batch konwersja do WebP.
- **Optymalizacja druku** (`print_optimize`) - Gemini + korekcja kolorow pod druk; zbieranie par Whitewall i kalibracja vs ww70.
- **Mock-up** (`mockup`) - obraz w ramce A4 -> galeria produktu (mockup) w Shopify.
- **Informacje o plikach** (`infoplikow`) - podglad grafik produktu w Shopify (plik CDN, alt, rola preview/Full/mockup).
- **Przed/Po** (`przedpo`) - upload grafiki «przed obróbką» (metafield); «po» = obraz Full z galerii; sekcja PDP v2.

### Administracja strony
- **Wzorzec szablonu** (`wzorzecszablonu`) - przypisanie szablonu motywu (template_suffix) do produktow; lista z repo + Shopify.
- **Strona produktu** (`stronaproduktu`) - podzial opisu na mini strony PDP v3 (metafield story_pages) + ustawienia efektow.
- **Karuzela** (`karuzela`) - sekcja «Wybrane dziela»: Karuzela1/2, wyglad V1/V2/V3, cytaty per kolekcja.
- **Tlo do Bio** (`tldobio`) - tlo sekcji biografii autora per kolekcja (upload + metafield Shopify).
- **Strona glowna** (`stronaglowna`) - landing page: hero, intro, suwaki przed/po, teksty sekcji (index.json).

### Zamowienia
- **Obrazy** (`obrazy`) - szybki dostep do folderow z reprodukcjami i obrazami klientow.
- **Produkcja** (`produkcja`) - status zamowien (wydruk + ramka + utwardzanie + wysylka).
- **Kalkulator kosztow** (`kalkulacja`) - koszty produkcji ramek (materialy, marze, drewno, import z .xlsm).

### Finanse
- **Księgowość — panel** (`finanse`) — jeden ekran: limit kwartalny DNR, próg VAT 240k, przepływ sprzedaży, compliance, checklist miesiąca z linkami do zamówień/faktur. Skróty do Dokumentów, KPiR i DNR (moduły ukryte na siatce, otwierane z panelu).
- **Import DNR (zaległe)** — w Zamknięciu miesiąca: domknięcie braków (faktura wystawiona, brak wpisu DNR); bez hurtowych szkiców.
- **DNR — cofnięcie przekroczenia** — gdy pierwsze przekroczenie limitu było błędne (np. przed zwrotem), w DNR → Kreator migracji: „Cofnij zapisane przekroczenie”.
- **Dokumenty sprzedaży** (`dokumentysprzedazy`) — faktury bez VAT; szkic bez daty wpływu (uzupełniasz przy wystawieniu po wpłacie).
- **JDG — KPiR** (`kpir`) — Księga Przychodów i Rozchodów; przy czynnym VAT kwota z faktury netto.
- **Działalność nierejestrowana** (`dnr`) — ewidencja DNR; import tylko z faktur (nie bezpośrednio Shopify).

### Marketing
- **Blog** (`blog`) - generator tresci, **import z HTML**, generator tematow, lista propozycji tematow, obecne posty (Shopify, 7 jezykow).
- **Social Media** (`socialmedia`) - generator postow (6 platform: IG Feed/Stories/Reels, FB, TikTok, Pinterest) i planer postow (PL+EN).
- **Zadania** (`zadania`) - organizer marketingowy: sygnaly z Shopify + kalendarz swiat + LLM -> plan miesiaca.
- **Ceny w marketingu** (`cenyMarketing`) - analiza pricingu na rynkach.

### Narzedzia pomocnicze
- **Planer** (`planer`) - dzienny planer zadan z priorytetami i kolorami.
- **Notatnik** (`notatnik`) - osobiste notatki i instrukcje (Shopify CLI, szablony, etc.).
- **Giclee Art Sklep** (`sklep`) - skrot do strony sklepu w przegladarce.

Komponenty nie wpisane do zadnej sekcji wpadna do dodatkowej sekcji "Inne" na dole.

## Wskazowki
- Kazdy komponent ma swoj wlasny przycisk **Instrukcja** - tam znajdziesz szczegoly obslugi.
- Status na dole pokazuje ostatnio uruchomiony komponent i jego PID.
- Zamkniecie GicleeApp NIE zamyka uruchomionych komponentow - dzialaja jako osobne procesy.
- Jesli uruchamiasz **GicleeApp.exe** (PyInstaller): sam launcher to .exe, ale
  komponenty nadal potrzebuja **Pythona w PATH** (`python` lub `py -3`), albo
  zmiennej `GICLEE_PYTHON` wskazujacej na `python.exe`. Bez tego kafelki
  nie wystartuja (pokaze sie komunikat).
"""


def main() -> None:
    if _LAUNCHER_AUTH_ENABLED:
        # Auth: pierwszy start = ustawienie hasla, potem logowanie przy kazdym uruchomieniu.
        try:
            from Komponenty._shared import auth
            if not auth.prompt_setup_or_login(None):
                return
        except ImportError:
            pass

    try:
        from tkinterdnd2 import TkinterDnD  # type: ignore

        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    root.withdraw()

    def _show_main() -> None:
        GicleeApp(root)
        root.deiconify()

    from .splash_screen import run_splash_then

    run_splash_then(root, _show_main)
    root.mainloop()


if __name__ == "__main__":
    main()
