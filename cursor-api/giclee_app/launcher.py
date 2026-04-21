"""GicleeApp - launcher z kafelkami komponentow.

Uruchamia kazdy komponent jako osobny proces (`python -m Komponenty.<nazwa>`),
zeby ewentualne crashe nie ubily launchera, a Tkinter mial swoj wlasny root
w kazdym z procesow.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from . import __version__
from .component_loader import Component, discover_components, find_components_dir
from .runtime import get_bundle_root, get_component_cwd, resolve_python_interpreter

APP_TITLE = "GicleeApp - launcher komponentow"

# Logi subprocess-ow komponentow (stdout/stderr przekierowany tutaj)
_LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

_TILES_PER_ROW = 3
_TILE_W = 280
_TILE_H = 170
_TILE_PAD_X = 6   # poziomy odstep miedzy kafelkami w wierszu
_TILE_PAD_Y = 6   # pionowy odstep wewnatrz sekcji
_SECTION_GAP_TOP = 4    # gora pierwszej sekcji
_SECTION_GAP_BETWEEN = 12  # odstep miedzy kolejnymi sekcjami

# Glowny widok pogrupowany w sekcje. Klucz to nazwa sekcji wyswietlana
# nad rzadem kafelkow; wartosci to nazwy folderow komponentow w
# kolejnosci, w jakiej maja sie pokazac (NIE wg pola "order" z
# component.json - tu liczy sie kolejnosc na liscie ponizej).
_SECTIONS: list[tuple[str, list[str]]] = [
    ("Administracja produktu", ["dodajobraz", "nazwijobraz", "pobierzobraz"]),
    ("Zamowienia",             ["obrazy", "produkcja", "finanse"]),
    ("Marketing",              ["blog", "socialmedia", "zadania", "cenyMarketing"]),
    ("Narzedzia pomocnicze",   ["planer", "notatnik", "sklep"]),
]
_SECTION_OTHER = "Inne"


class GicleeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"{APP_TITLE} · v{__version__}")
        # Rozmiar okna dobrany pod 3 sekcje x 3 kafelki w rzedzie
        # (3 * (170 + 24) + 3 * naglowek_sekcji + paddingi + status bar).
        self.root.geometry("920x780")
        self.root.minsize(840, 640)

        self.components_dir: Path = find_components_dir()
        self.components: list[Component] = []
        self._running_procs: list[subprocess.Popen] = []  # noqa: PLR0402
        # Aktualnie zamontowany widok inline (None = pokazujemy siatke kafelkow)
        self._inline_view: Any = None

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

        # Scroll mysza
        def _on_mousewheel(evt: tk.Event) -> None:
            delta = -1 * (evt.delta // 120) if evt.delta else 0
            if delta:
                self.canvas.yview_scroll(delta, "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Status bar
        status = ttk.Frame(self.root, padding=(12, 4))
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.status_var, foreground="#777").pack(side="left")
        ttk.Label(
            status,
            text=f"wersja {__version__}  ·  Komponenty: {self.components_dir}",
            foreground="#aaa",
        ).pack(side="right")

    # ---------- Discover + rendering ----------
    def _refresh_components(self) -> None:
        new_list = discover_components(self.components_dir)
        # Sprawdz czy sa zmiany (zeby nie odrysowywac niepotrzebnie)
        old_keys = [(c.folder_name, c.name, c.description, c.color, c.order) for c in self.components]
        new_keys = [(c.folder_name, c.name, c.description, c.color, c.order) for c in new_list]
        if new_keys == old_keys:
            return
        self.components = new_list
        self._render_tiles()
        if not self.components:
            self.status_var.set(f"Brak komponentow w {self.components_dir}")
        else:
            self.status_var.set(f"Znaleziono komponentow: {len(self.components)}")

    def _render_tiles(self) -> None:
        for child in list(self.tiles_frame.winfo_children()):
            child.destroy()

        if not self.components:
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

        # Pogrupuj komponenty wg _SECTIONS, zachowujac kolejnosc z listy.
        by_folder = {c.folder_name: c for c in self.components}
        sections: list[tuple[str, list[Component]]] = []
        used: set[str] = set()
        for section_title, folder_order in _SECTIONS:
            comps_in_section: list[Component] = []
            for fld in folder_order:
                comp = by_folder.get(fld)
                if comp is not None:
                    comps_in_section.append(comp)
                    used.add(fld)
            if comps_in_section:
                sections.append((section_title, comps_in_section))

        # Komponenty nie zmapowane - trafia do sekcji "Inne" na koncu (nie ginie nic nowego).
        leftover = [c for c in self.components if c.folder_name not in used]
        if leftover:
            sections.append((_SECTION_OTHER, leftover))

        # Renderowanie sekcja po sekcji.
        row_cursor = 0
        for sec_idx, (section_title, comps) in enumerate(sections):
            # Naglowek sekcji
            header = tk.Label(
                self.tiles_frame,
                text=section_title,
                bg="#f4f4f7",
                fg="#222",
                font=("Segoe UI", 13, "bold"),
                anchor="w",
                padx=4,
            )
            header.grid(
                row=row_cursor,
                column=0,
                columnspan=_TILES_PER_ROW,
                sticky="ew",
                padx=_TILE_PAD_X,
                pady=(
                    _SECTION_GAP_TOP if sec_idx == 0 else _SECTION_GAP_BETWEEN,
                    1,
                ),
            )
            row_cursor += 1

            # Cienka kreska pod naglowkiem sekcji
            sep = tk.Frame(self.tiles_frame, height=1, bg="#dcdce2")
            sep.grid(
                row=row_cursor,
                column=0,
                columnspan=_TILES_PER_ROW,
                sticky="ew",
                padx=_TILE_PAD_X,
                pady=(0, 2),
            )
            row_cursor += 1

            # Kafelki sekcji
            for i, comp in enumerate(comps):
                sub_row, col = divmod(i, _TILES_PER_ROW)
                tile = self._build_tile(self.tiles_frame, comp)
                tile.grid(
                    row=row_cursor + sub_row,
                    column=col,
                    padx=_TILE_PAD_X,
                    pady=_TILE_PAD_Y,
                    sticky="",  # bez rozciagania - kafelki maja staly rozmiar
                )
            row_cursor += (len(comps) + _TILES_PER_ROW - 1) // _TILES_PER_ROW

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
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
        return _LOGS_DIR / f"{comp.folder_name}.log"

    def _show_component_log(self, comp: Component) -> None:
        path = self._component_log_path(comp)
        win = tk.Toplevel(self.root)
        win.title(f"Log: {comp.name}")
        win.geometry("900x560")
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
        path = self._component_log_path(comp)
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

        def _on_enter(_evt: object) -> None:
            _set_hover(True)

        def _on_leave(_evt: object) -> None:
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
        log_path = self._component_log_path(comp)
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

        # Schowaj siatke
        self.tiles_view.pack_forget()

        self._inline_host = ttk.Frame(self._body_container)
        self._inline_host.pack(fill="both", expand=True)

        try:
            view = builder(self._inline_host, self._show_tiles)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(comp.name, f"Blad budowy widoku:\n{e}")
            self._show_tiles()
            return

        # Komponent moze sam pakowac siebie; jesli nie, wepchniemy go
        if isinstance(view, (tk.Widget, ttk.Frame)):
            try:
                view.pack(fill="both", expand=True)
            except tk.TclError:
                pass

        self._inline_view = view
        self.status_var.set(f"Otwarto: {comp.name}")

    def _show_tiles(self) -> None:
        """Wraca do siatki kafelkow z widoku inline."""
        if self._inline_host is not None:
            try:
                self._inline_host.destroy()
            except tk.TclError:
                pass
            self._inline_host = None
        self._inline_view = None
        if not self.tiles_view.winfo_ismapped():
            self.tiles_view.pack(fill="both", expand=True)
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
        comp = next((c for c in self.components if c.folder_name == "zadania"), None)
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

## Toolbar w prawym gornym rogu
- **Token setup** - checklista OAuth Shopify + Meta (`CHECKLIST_SETUP.md`).
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
Komponenty pogrupowane sa w trzy sekcje (kazda z naglowkiem):

### Administracja produktu
- **Dodaj obraz** (`dodajobraz`) - tworzenie produktow w Shopify na podstawie zdjecia.
- **Nazwij obraz** (`nazwijobraz`) - automatyczna zmiana nazw plikow na "Autor - Tytul".
- **Pobierz obraz** (`pobierzobraz`) - pobieranie pelnych obrazow IIIF (np. National Gallery).

### Zamowienia
- **Obrazy** (`obrazy`) - szybki dostep do folderow z reprodukcjami i obrazami klientow.
- **Produkcja** (`produkcja`) - status zamowien (wydruk + ramka + utwardzanie + wysylka).
- **Finanse** (`finanse`) - wyliczenia i ksiegowosc.

### Marketing
- **Blog** (`blog`) - generator tresci + generator tematow + podglad postow z bloga Shopify (7 jezykow).
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
    # Auth: przy pierwszym uruchomieniu prosi o ustawienie hasla, potem za
    # kazdym razem loguje uzytkownika. Jesli nie wybierze - apka sie nie otworzy.
    try:
        from Komponenty._shared import auth
        if not auth.prompt_setup_or_login(None):
            # User anulowal albo 3x bledne haslo -> apka zamykana.
            return
    except ImportError:
        # Fallback - brak modulu auth to pozwalamy dzialac bez ochrony
        pass

    root = tk.Tk()
    GicleeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
