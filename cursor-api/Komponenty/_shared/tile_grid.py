"""Mini-launcher uzywany przez komponenty inline (Obrazy, Finanse, ...).

Tworzy widok z paskiem [<- Powrot] [Tytul] [... Ustawienia] + siatka kafelkow,
ktorych klikniecie wywoluje callback (np. otworzenie folderu / pliku / toast).

Persystencja "settings": JSON w `Komponenty/<komponent>/settings.json`.
Domyslne wartosci pochodza z definicji TileSpec.target_path; uzytkownik moze
nadpisac w dialogu ustawien.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center


@dataclass
class TileSpec:
    key: str                            # stable klucz settings (np. "reprodukcje")
    label: str                          # napis na kafelku
    color: str = "#1e88e5"              # akcent
    icon: str = ""                      # emoji
    target_path: str = ""               # default sciezka (folder/plik) - dla path tile
    target_kind: str = "path"           # "path" (otworz w explorerze/aplikacji) | "callable" | "url"
    callback: Callable[[tk.Misc, "TileSpec"], None] | None = None  # dla kind=callable
    description: str = ""               # podtytul pod nazwa
    settings_label: str = ""            # opis pola w dialogu ustawien (default = label)
    settings_kind: str = "folder"       # "folder" | "file" | "any"
    extras: dict = field(default_factory=dict)


_TILE_W = 280
_TILE_H = 150
_TILES_PER_ROW = 3
_TILE_PAD = 12


def open_path_in_os(path: str) -> tuple[bool, str]:
    """Otwiera folder/plik w domyslnej aplikacji systemu. Zwraca (ok, info)."""
    if not path:
        return False, "Sciezka jest pusta. Otworz Ustawienia i wskaz lokalizacje."
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"Sciezka nie istnieje:\n{p}"
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])  # noqa: S607
        else:
            subprocess.Popen(["xdg-open", str(p)])  # noqa: S607
    except OSError as e:
        return False, f"Blad otwierania: {e}"
    return True, str(p)


def load_settings(component_dir: Path) -> dict[str, Any]:
    p = component_dir / "settings.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(component_dir: Path, data: dict[str, Any]) -> None:
    p = component_dir / "settings.json"
    try:
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


class InlineTileView:
    """Mini-launcher renderowany w danym `parent` frame.

    Po `mount(parent)` zwraca utworzony tk.Frame. `unmount()` go niszczy.
    """

    def __init__(
        self,
        *,
        title: str,
        tiles: list[TileSpec],
        component_dir: Path,
        on_back: Callable[[], None],
        subtitle: str = "",
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.tiles = tiles
        self.component_dir = component_dir
        self.on_back = on_back
        self.settings = load_settings(component_dir)
        self.frame: tk.Frame | None = None

    # ---------- mount ----------
    def mount(self, parent: tk.Misc) -> tk.Frame:
        outer = tk.Frame(parent, bg="#f4f4f7")
        self.frame = outer

        # Toolbar: [Powrot] [Tytul] [Ustawienia]
        toolbar = tk.Frame(outer, bg="#f4f4f7")
        toolbar.pack(fill="x", padx=14, pady=(12, 4))
        ttk.Button(toolbar, text="< Powrot", command=self.on_back).pack(side="left")
        tk.Label(
            toolbar, text=self.title, bg="#f4f4f7",
            font=("Segoe UI", 18, "bold"), fg="#222",
        ).pack(side="left", padx=(14, 0))
        if self.subtitle:
            tk.Label(
                toolbar, text=self.subtitle, bg="#f4f4f7", fg="#666",
                font=("Segoe UI", 10),
            ).pack(side="left", padx=(10, 0), pady=(8, 0))
        ttk.Button(toolbar, text="Ustawienia", command=self._open_settings).pack(side="right")

        # Siatka kafelkow
        body = tk.Frame(outer, bg="#f4f4f7")
        body.pack(fill="both", expand=True, padx=14, pady=10)
        for i in range(_TILES_PER_ROW):
            body.columnconfigure(i, weight=1, uniform="tg")

        for idx, t in enumerate(self.tiles):
            r, c = divmod(idx, _TILES_PER_ROW)
            tile = self._build_tile(body, t)
            tile.grid(row=r, column=c, padx=_TILE_PAD, pady=_TILE_PAD, sticky="")

        return outer

    def unmount(self) -> None:
        if self.frame is not None:
            try:
                self.frame.destroy()
            except tk.TclError:
                pass
            self.frame = None

    # ---------- tile rendering (skopiowane z launcher.py - taki sam look & feel) ----------
    def _build_tile(self, parent: tk.Misc, t: TileSpec) -> tk.Frame:
        BG_NORMAL = "#ffffff"
        BG_HOVER = "#f0f2f7"
        outer = tk.Frame(
            parent, bg=BG_NORMAL, bd=0,
            highlightthickness=1,
            highlightbackground="#dcdce2",
            highlightcolor="#dcdce2",
            width=_TILE_W, height=_TILE_H,
        )
        outer.pack_propagate(False)

        accent = tk.Frame(outer, bg=t.color, width=6)
        accent.pack(side="left", fill="y")
        body = tk.Frame(outer, bg=BG_NORMAL)
        body.pack(side="left", fill="both", expand=True, padx=14, pady=10)

        title_row = tk.Frame(body, bg=BG_NORMAL)
        title_row.pack(fill="x")
        if t.icon:
            tk.Label(title_row, text=t.icon, bg=BG_NORMAL,
                     font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 6))
        tk.Label(title_row, text=t.label, bg=BG_NORMAL,
                 font=("Segoe UI", 12, "bold"), fg="#222",
                 anchor="w").pack(side="left", fill="x", expand=True)

        if t.description:
            tk.Label(body, text=t.description, bg=BG_NORMAL,
                     font=("Segoe UI", 9), fg="#555",
                     wraplength=_TILE_W - 50, justify="left",
                     anchor="w").pack(fill="x", pady=(4, 0))

        # Hover (tylko bg) + klik na calym kafelku
        bg_widgets: list[tk.Widget] = []

        def _collect(w: tk.Widget) -> None:
            if w is accent:
                return
            bg_widgets.append(w)
            for ch in w.winfo_children():
                _collect(ch)

        _collect(outer)

        def _set_hover(active: bool) -> None:
            new_bg = BG_HOVER if active else BG_NORMAL
            for w in bg_widgets:
                try:
                    w.configure(bg=new_bg)
                except tk.TclError:
                    pass

        def _on_enter(_e: object) -> None:
            _set_hover(True)

        def _on_leave(_e: object) -> None:
            try:
                px, py = outer.winfo_pointerxy()
                ox, oy = outer.winfo_rootx(), outer.winfo_rooty()
                ow, oh = outer.winfo_width(), outer.winfo_height()
            except tk.TclError:
                return
            if ox <= px < ox + ow and oy <= py < oy + oh:
                return
            _set_hover(False)

        def _on_click(_e: object, spec: TileSpec = t) -> None:
            self._activate(spec)

        def _bind(w: tk.Widget) -> None:
            w.bind("<Enter>", _on_enter, add="+")
            w.bind("<Leave>", _on_leave, add="+")
            w.bind("<Button-1>", _on_click, add="+")
            try:
                w.configure(cursor="hand2")
            except tk.TclError:
                pass
            for ch in w.winfo_children():
                _bind(ch)

        _bind(outer)
        return outer

    # ---------- aktywacja kafelka ----------
    def _activate(self, t: TileSpec) -> None:
        if t.target_kind == "callable" and t.callback:
            try:
                t.callback(self.frame, t)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror(self.title, f"Blad: {e}")
            return
        if t.target_kind == "url":
            target = self.settings.get(t.key, t.target_path)
            import webbrowser
            if not target:
                messagebox.showwarning(self.title, "Brak URL. Otworz Ustawienia.")
                return
            webbrowser.open(target)
            return
        # path
        target = self.settings.get(t.key) or t.target_path
        ok, info = open_path_in_os(target)
        if not ok:
            messagebox.showwarning(t.label, info)
        else:
            show_toast(self.frame, f"Otwarto: {Path(info).name or info}", duration_ms=1200)

    # ---------- ustawienia ----------
    def _open_settings(self) -> None:
        dlg = tk.Toplevel(self.frame)
        dlg.title(f"Ustawienia - {self.title}")
        dlg.transient(self.frame.winfo_toplevel())
        position_toplevel_screen_center(dlg, 760, 420)
        dlg.minsize(600, 320)

        ttk.Label(
            dlg, text="Sciezki kafelkow",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))
        ttk.Label(
            dlg, text="Podaj sciezki, ktore maja sie otwierac po kliknieciu w kafelek.",
            foreground="#666",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        body = ttk.Frame(dlg, padding=(14, 4))
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        entries: dict[str, tk.StringVar] = {}
        row = 0
        for t in self.tiles:
            if t.target_kind == "callable":
                continue  # niekonfigurowalny
            ttk.Label(body, text=t.settings_label or t.label).grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=4,
            )
            var = tk.StringVar(value=self.settings.get(t.key, t.target_path))
            entries[t.key] = var
            entry = ttk.Entry(body, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", pady=4)

            # Przycisk wyboru folderu/pliku zaleznie od target_kind
            kind = t.target_kind
            settings_kind = t.settings_kind

            def _make_picker(v: tk.StringVar = var, k: str = kind, sk: str = settings_kind) -> Callable[[], None]:
                def _pick() -> None:
                    initial = v.get() or os.getcwd()
                    if k == "url":
                        return  # nie ma file dialogu dla URL
                    if sk == "file":
                        path = filedialog.askopenfilename(initialdir=initial)
                    elif sk == "folder":
                        path = filedialog.askdirectory(initialdir=initial)
                    else:
                        path = filedialog.askopenfilename(initialdir=initial)
                    if path:
                        v.set(path)
                return _pick

            if kind != "url":
                ttk.Button(body, text="...", width=4, command=_make_picker()).grid(
                    row=row, column=2, padx=(6, 0),
                )
            row += 1

        btns = ttk.Frame(dlg, padding=(14, 8))
        btns.pack(fill="x")

        def _save() -> None:
            for k, v in entries.items():
                self.settings[k] = v.get().strip()
            save_settings(self.component_dir, self.settings)
            show_toast(self.frame, "Zapisano ustawienia", duration_ms=1100)
            dlg.destroy()

        ttk.Button(btns, text="Zapisz", command=_save).pack(side="right")
        ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right", padx=(0, 6))
