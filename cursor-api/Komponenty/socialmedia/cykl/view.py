"""Glowny inline widok komponentu Cykl.

Struktura:

    Toolbar (gora):
      < Powrot | Generuj tresc tygodnia | Odswiez z Shopify | Przesun kolejke
      +/-1 dzien | Lista kontrolna | Otworz folder obrazow | Ustawienia Meta API
      | Instrukcja

    Treeview kolejki (srodek):
      Data | Godz | Slot | Artysta | Tytul | FB PL | FB EN | IG PL | IG EN
      | Tresc | Status

    Status bar (dol):
      Kolejka: X pending / Y done | Tresc do: DD.MM | Kolejny artysta

PPM menu na pozycji:
  Edytuj... | Publikuj teraz | Wyslij recznie | Przesun +1/-1 dzien | Gora/Dol
  | Pomin | Usun

Dwuklik -> Edytuj.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.tree_sort import attach_sortable_headings

from . import (
    content_gen,
    edit_dialog,
    help_text,
    images as img_mod,
    meta_config,
    meta_publisher,
    platforms_cykl as _cp,
    queue_builder,
    scheduler,
    storage,
)

_BG = "#f4f4f7"


# ---------------------------------------------------------------------------
# Entry point - wywolywany z Komponenty/socialmedia/view.py
# ---------------------------------------------------------------------------

def build_cykl_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    v = CykleView(parent, on_back)
    return v.frame


# ---------------------------------------------------------------------------
# Model: kolumny treeview
# ---------------------------------------------------------------------------

_COLS = (
    "date", "time", "slot", "artist", "title",
    "fb_pl", "fb_en", "ig_pl", "ig_en",
    "caption", "status",
)

_COL_HEADERS = {
    "date": "Data",
    "time": "Godz",
    "slot": "Slot",
    "artist": "Artysta",
    "title": "Tytul",
    "fb_pl": "FB PL",
    "fb_en": "FB EN",
    "ig_pl": "IG PL",
    "ig_en": "IG EN",
    "caption": "Tresc (preview)",
    "status": "Status",
}

_COL_WIDTHS = {
    "date": 88, "time": 54, "slot": 80,
    "artist": 130, "title": 170,
    "fb_pl": 50, "fb_en": 50, "ig_pl": 50, "ig_en": 50,
    "caption": 220, "status": 80,
}


class CykleView:
    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        self.parent = parent
        self.on_back = on_back
        self.frame = tk.Frame(parent, bg=_BG)

        self._build_toolbar()
        self._build_tree()
        self._build_status_bar()
        self._refresh_from_disk()

    # ---------- Toolbar ----------
    def _build_toolbar(self) -> None:
        top = tk.Frame(self.frame, bg=_BG)
        top.pack(fill="x", padx=12, pady=(10, 4))

        ttk.Button(top, text="< Powrot", command=self.on_back).pack(side="left")
        tk.Label(
            top, text="Cykl - Obraz na rano, popoludnie i wieczor",
            bg=_BG, font=("Segoe UI", 14, "bold"),
        ).pack(side="left", padx=(12, 0))

        ttk.Button(top, text="Instrukcja", command=self._show_help).pack(side="right")
        ttk.Button(top, text="Ustawienia Meta API",
                   command=self._open_meta_config).pack(side="right", padx=(0, 6))

        # Druga linia toolbaru
        toolbar = tk.Frame(self.frame, bg=_BG)
        toolbar.pack(fill="x", padx=12, pady=(0, 6))

        ttk.Button(toolbar, text="Odswiez z Shopify",
                   command=self._refresh_from_shopify).pack(side="left")
        ttk.Button(toolbar, text="Generuj tresc tygodnia",
                   command=self._open_content_generator).pack(side="left", padx=(6, 0))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Button(toolbar, text="+1 dzien WSZYSTKIE",
                   command=lambda: self._shift_all(1)).pack(side="left")
        ttk.Button(toolbar, text="-1 dzien WSZYSTKIE",
                   command=lambda: self._shift_all(-1)).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Rozpocznij od artysty...",
                   command=self._start_from_artist).pack(side="left", padx=(6, 0))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Button(toolbar, text="Lista kontrolna",
                   command=self._show_checklist).pack(side="left")
        ttk.Button(toolbar, text="Otworz folder obrazow",
                   command=self._open_images_folder).pack(side="left", padx=(6, 0))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Button(toolbar, text="Wyczysc kolejke",
                   command=self._clear_queue).pack(side="left")

    # ---------- Tree + side panel ----------
    def _build_tree(self) -> None:
        mid = tk.Frame(self.frame, bg=_BG)
        mid.pack(fill="both", expand=True, padx=12, pady=(4, 4))

        # Horizontal split: Treeview po lewej, panel zdjec po prawej.
        paned = ttk.PanedWindow(mid, orient="horizontal")
        paned.pack(fill="both", expand=True)

        tree_frame = ttk.Frame(paned)
        paned.add(tree_frame, weight=3)

        self._side_panel_frame = ttk.Frame(paned, padding=(6, 4))
        paned.add(self._side_panel_frame, weight=1)

        self.tree = ttk.Treeview(
            tree_frame, columns=_COLS, show="headings", height=20,
            selectmode="extended",
        )
        for col in _COLS:
            self.tree.heading(col, text=_COL_HEADERS[col])
            anchor = "center" if col in ("time", "slot", "fb_pl", "fb_en", "ig_pl", "ig_en") else "w"
            self.tree.column(col, width=_COL_WIDTHS[col], anchor=anchor, stretch=(col == "caption"))

        sb_v = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        sb_h = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Tagi statusow
        self.tree.tag_configure("overdue", background="#ffe0e0")
        self.tree.tag_configure("done", foreground="#388e3c")
        self.tree.tag_configure("skipped", foreground="#888")
        self.tree.tag_configure("error", background="#fff4d6")
        self.tree.tag_configure("missing_img", foreground="#d84315")

        # Sort
        attach_sortable_headings(
            self.tree,
            columns={
                "date": ("Data", "date"),
                "time": ("Godz", "text"),
                "slot": ("Slot", "text"),
                "artist": ("Artysta", "text"),
                "title": ("Tytul", "text"),
                "fb_pl": ("FB PL", "text"),
                "fb_en": ("FB EN", "text"),
                "ig_pl": ("IG PL", "text"),
                "ig_en": ("IG EN", "text"),
                "caption": ("Tresc", "text"),
                "status": ("Status", "text"),
            },
        )

        # Context menu + dwuklik
        self.tree.bind("<Double-Button-1>", lambda e: self._edit_selected())
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Drag-select (painter-style): klik + przeciagniecie kursorem
        # zaznacza wszystkie wiersze pomiedzy startem a biezaca pozycja.
        # Standardowy extended mode obsluguje Ctrl+click / Shift+click;
        # tutaj dokladamy intuicyjne malowanie przeciagnieciem.
        self._drag_anchor: str | None = None

        def _on_press(evt: tk.Event) -> None:
            row = self.tree.identify_row(evt.y)
            if not row:
                self._drag_anchor = None
                return
            # Bez modyfikatorow - reset do pojedynczego wiersza
            state = int(getattr(evt, "state", 0) or 0)
            ctrl = bool(state & 0x0004)
            shift = bool(state & 0x0001)
            if not (ctrl or shift):
                self.tree.selection_set(row)
            self._drag_anchor = row

        def _on_drag(evt: tk.Event) -> None:
            if not self._drag_anchor:
                return
            row = self.tree.identify_row(evt.y)
            if not row:
                return
            children = list(self.tree.get_children())
            try:
                a = children.index(self._drag_anchor)
                b = children.index(row)
            except ValueError:
                return
            lo, hi = (a, b) if a <= b else (b, a)
            self.tree.selection_set(children[lo:hi + 1])

        self.tree.bind("<Button-1>", _on_press, add="+")
        self.tree.bind("<B1-Motion>", _on_drag, add="+")

        # Selection -> update side panelu zdjec
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._refresh_side_panel())

        # Inicjalny render side panelu (placeholder)
        self._side_widgets: dict | None = None
        self._side_item_id: str | None = None
        self._refresh_side_panel()

    # ---------- Side panel: szybki upload zdjec ----------
    def _refresh_side_panel(self) -> None:
        """Buduje/aktualizuje panel zdjec po prawej na podstawie zaznaczenia."""
        for child in self._side_panel_frame.winfo_children():
            child.destroy()
        self._side_widgets = None

        sel = self.tree.selection()
        if not sel:
            self._side_item_id = None
            ttk.Label(
                self._side_panel_frame,
                text="(zaznacz 1 pozycje aby edytowac zdjecia)",
                foreground="#888",
                wraplength=240, justify="center",
            ).pack(expand=True, pady=40)
            return
        if len(sel) > 1:
            self._side_item_id = None
            ttk.Label(
                self._side_panel_frame,
                text=f"({len(sel)} pozycji zaznaczonych - panel dostepny tylko dla 1)",
                foreground="#888",
                wraplength=240, justify="center",
            ).pack(expand=True, pady=40)
            return

        item_id = sel[0]
        item = storage.get_item(item_id)
        if item is None:
            self._side_item_id = None
            ttk.Label(self._side_panel_frame, text="(pozycja nie istnieje)").pack()
            return
        self._side_item_id = item_id

        # Header z tytulem
        hdr = ttk.Frame(self._side_panel_frame)
        hdr.pack(fill="x", pady=(0, 6))
        ttk.Label(
            hdr, text=item.artist, font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            hdr, text=item.painting_title_pl,
            foreground="#555", wraplength=240, justify="left",
        ).pack(anchor="w")

        # Przycisk "Sync z folderu" - odtwarza zestaw z Obrazy/
        def _sync() -> None:
            it2 = storage.get_item(item_id)
            if it2 is None:
                return
            # Wyczysc recznie zeby sync_item_images nadpisal
            it2.image_fb_main = ""
            it2.image_fb_zooms = []
            it2.image_fb_mockup = ""
            it2.image_ig_main = ""
            it2.image_ig_zooms = []
            it2.image_ig_mockup = ""
            img_mod.sync_item_images(it2)
            self._invalidate_cdn(it2)
            storage.update_item(item_id, **{
                f: getattr(it2, f) for f in (
                    "image_fb_main", "image_fb_zooms", "image_fb_mockup",
                    "image_ig_main", "image_ig_zooms", "image_ig_mockup",
                    "cdn_fb_main", "cdn_fb_zooms", "cdn_fb_mockup",
                    "cdn_ig_main", "cdn_ig_zooms", "cdn_ig_mockup",
                )
            })
            self._refresh_side_panel()
            show_toast(self.frame.winfo_toplevel(), "Zsynchronizowano z folderu")

        ttk.Button(hdr, text="Sync z folderu", command=_sync).pack(anchor="w", pady=(4, 0))

        # 2 kolumny: FB | IG
        cols = ttk.Frame(self._side_panel_frame)
        cols.pack(fill="both", expand=True, pady=(4, 0))
        cols.columnconfigure(0, weight=1, uniform="side")
        cols.columnconfigure(1, weight=1, uniform="side")

        widgets: dict = {}
        fb = ttk.LabelFrame(cols, text="Facebook", padding=6)
        fb.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        self._build_side_platform(fb, item_id, "fb", widgets)

        ig = ttk.LabelFrame(cols, text="Instagram", padding=6)
        ig.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        self._build_side_platform(ig, item_id, "ig", widgets)

        self._side_widgets = widgets

    def _build_side_platform(
        self, parent: ttk.LabelFrame, item_id: str, platform: str, widgets: dict,
    ) -> None:
        """Buduje kolumne side panelu: main + zoomy + mockup dla FB lub IG."""
        item = storage.get_item(item_id)
        if item is None:
            return

        # --- Main ---
        ttk.Label(parent, text="Main:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        main_val = getattr(item, f"image_{platform}_main", "") or ""
        main_var = tk.StringVar(value=_short_name(main_val))
        main_lbl = ttk.Label(parent, textvariable=main_var, foreground="#1976d2", wraplength=160)
        main_lbl.pack(anchor="w")
        main_row = ttk.Frame(parent)
        main_row.pack(fill="x", pady=(2, 6))

        def _set_main() -> None:
            p = filedialog.askopenfilename(
                parent=self.frame.winfo_toplevel(),
                title=f"{platform.upper()} main",
                filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp")],
            )
            if not p:
                return
            it2 = storage.get_item(item_id)
            if it2 is None:
                return
            try:
                rel = img_mod.copy_into(
                    Path(p), it2.artist_handle, it2.painting_handle, role="main",
                )
            except (FileNotFoundError, ValueError) as e:
                messagebox.showerror("Main", str(e))
                return
            setattr(it2, f"image_{platform}_main", rel)
            setattr(it2, f"cdn_{platform}_main", "")
            storage.update_item(item_id, **{
                f"image_{platform}_main": rel,
                f"cdn_{platform}_main": "",
            })
            main_var.set(_short_name(rel))
            show_toast(self.frame.winfo_toplevel(), f"{platform.upper()} main: {Path(p).name}")

        def _clear_main() -> None:
            storage.update_item(item_id, **{
                f"image_{platform}_main": "",
                f"cdn_{platform}_main": "",
            })
            main_var.set("(brak)")

        ttk.Button(main_row, text="Wybierz", command=_set_main, width=9).pack(side="left")
        ttk.Button(main_row, text="X", command=_clear_main, width=2).pack(side="left", padx=(4, 0))
        if not main_val:
            main_var.set("(brak)")

        # --- Zoomy ---
        ttk.Label(parent, text="Zoomy:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        zoom_box = tk.Listbox(parent, height=5, font=("Consolas", 8), exportselection=False)
        for z in getattr(item, f"image_{platform}_zooms") or []:
            zoom_box.insert("end", _short_name(z))
        zoom_box.pack(fill="x")
        zoom_row = ttk.Frame(parent)
        zoom_row.pack(fill="x", pady=(2, 6))

        def _zoom_rel_paths() -> list[str]:
            it2 = storage.get_item(item_id)
            return list(getattr(it2, f"image_{platform}_zooms") or []) if it2 else []

        def _add_zoom() -> None:
            paths = filedialog.askopenfilenames(
                parent=self.frame.winfo_toplevel(),
                title=f"{platform.upper()} zoomy",
                filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp")],
            )
            if not paths:
                return
            it2 = storage.get_item(item_id)
            if it2 is None:
                return
            zooms = list(getattr(it2, f"image_{platform}_zooms") or [])
            added = 0
            for p in paths:
                try:
                    rel = img_mod.copy_into(
                        Path(p), it2.artist_handle, it2.painting_handle, role="zoom",
                    )
                except (FileNotFoundError, ValueError) as e:
                    messagebox.showerror("Zoom", str(e))
                    continue
                zooms.append(rel)
                zoom_box.insert("end", _short_name(rel))
                added += 1
            if added:
                storage.update_item(item_id, **{
                    f"image_{platform}_zooms": zooms,
                    f"cdn_{platform}_zooms": [],
                })
                show_toast(self.frame.winfo_toplevel(),
                           f"Dodano {added} zoomow do {platform.upper()}")

        def _remove_zoom() -> None:
            sel = list(zoom_box.curselection())
            if not sel:
                return
            it2 = storage.get_item(item_id)
            if it2 is None:
                return
            zooms = list(getattr(it2, f"image_{platform}_zooms") or [])
            for i in sorted(sel, reverse=True):
                if 0 <= i < len(zooms):
                    del zooms[i]
                zoom_box.delete(i)
            storage.update_item(item_id, **{
                f"image_{platform}_zooms": zooms,
                f"cdn_{platform}_zooms": [],
            })

        ttk.Button(zoom_row, text="+", command=_add_zoom, width=3).pack(side="left")
        ttk.Button(zoom_row, text="-", command=_remove_zoom, width=3).pack(side="left", padx=(2, 0))

        # --- Mockup ---
        ttk.Label(parent, text="Mockup:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        mockup_val = getattr(item, f"image_{platform}_mockup", "") or ""
        mockup_var = tk.StringVar(value=_short_name(mockup_val) if mockup_val else "(brak)")
        ttk.Label(parent, textvariable=mockup_var, foreground="#1976d2", wraplength=160).pack(anchor="w")
        mockup_row = ttk.Frame(parent)
        mockup_row.pack(fill="x", pady=(2, 0))

        def _set_mockup() -> None:
            p = filedialog.askopenfilename(
                parent=self.frame.winfo_toplevel(),
                title=f"{platform.upper()} mockup",
                filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp")],
            )
            if not p:
                return
            it2 = storage.get_item(item_id)
            if it2 is None:
                return
            try:
                rel = img_mod.copy_into(
                    Path(p), it2.artist_handle, it2.painting_handle, role="mockup",
                )
            except (FileNotFoundError, ValueError) as e:
                messagebox.showerror("Mockup", str(e))
                return
            storage.update_item(item_id, **{
                f"image_{platform}_mockup": rel,
                f"cdn_{platform}_mockup": "",
            })
            mockup_var.set(_short_name(rel))
            show_toast(self.frame.winfo_toplevel(), f"{platform.upper()} mockup: {Path(p).name}")

        def _clear_mockup() -> None:
            storage.update_item(item_id, **{
                f"image_{platform}_mockup": "",
                f"cdn_{platform}_mockup": "",
            })
            mockup_var.set("(brak)")

        ttk.Button(mockup_row, text="Wybierz", command=_set_mockup, width=9).pack(side="left")
        ttk.Button(mockup_row, text="X", command=_clear_mockup, width=2).pack(side="left", padx=(4, 0))

    @staticmethod
    def _invalidate_cdn(item: storage.CykleItem) -> None:
        item.cdn_fb_main = ""
        item.cdn_fb_zooms = []
        item.cdn_fb_mockup = ""
        item.cdn_ig_main = ""
        item.cdn_ig_zooms = []
        item.cdn_ig_mockup = ""

    # ---------- Status bar ----------
    def _build_status_bar(self) -> None:
        self.status = tk.Frame(self.frame, bg=_BG)
        self.status.pack(fill="x", padx=12, pady=(4, 10))

        self.status_left = tk.StringVar(value="")
        tk.Label(self.status, textvariable=self.status_left, bg=_BG, fg="#555").pack(side="left")

        self.status_gen = tk.StringVar(value="")
        self.status_gen_lbl = tk.Label(
            self.status, textvariable=self.status_gen, bg=_BG, fg="#e65100",
            font=("Segoe UI", 9, "bold"),
        )
        self.status_gen_lbl.pack(side="left", padx=(16, 0))

        self.status_next = tk.StringVar(value="")
        tk.Label(self.status, textvariable=self.status_next, bg=_BG, fg="#555").pack(side="right")

    # ---------- Render ----------
    def _refresh_from_disk(self) -> None:
        items = storage.load_queue()
        # Syncuj obrazy z dysku dla kazdego pending/ready
        for it in items:
            if it.status in ("pending", "ready"):
                img_mod.sync_item_images(it)
        storage.save_queue(items)

        # Wyczysc tree
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        now = datetime.now()
        pending = 0
        done = 0
        skipped = 0
        errored = 0

        for it in items:
            tags = []
            if it.status == "done":
                done += 1
                tags.append("done")
            elif it.status == "skipped":
                skipped += 1
                tags.append("skipped")
            elif it.status == "error":
                errored += 1
                tags.append("error")
            else:
                pending += 1
                # Overdue?
                if it.scheduled_at:
                    try:
                        if datetime.fromisoformat(it.scheduled_at) < now:
                            tags.append("overdue")
                    except ValueError:
                        pass
                # Missing images?
                imset = img_mod.list_images_for(it.artist_handle, it.painting_handle)
                if not (imset.has_main() or it.product_image_url):
                    tags.append("missing_img")

            date_str, time_str = _split_iso(it.scheduled_at)
            slot_label = _cp.SLOT_LABEL_PL.get(it.slot, it.slot or "")

            caption_preview = _preview(it.caption_pl or it.caption_fb_pl or it.caption_ig_pl)

            self.tree.insert(
                "", "end", iid=it.id,
                values=(
                    date_str, time_str, slot_label,
                    it.artist, it.painting_title_pl,
                    _channel_badge(it, "fb_pl"),
                    _channel_badge(it, "fb_en"),
                    _channel_badge(it, "ig_pl"),
                    _channel_badge(it, "ig_en"),
                    caption_preview,
                    _status_label(it.status),
                ),
                tags=tuple(tags),
            )

        # Status bar
        total = len(items)
        self.status_left.set(
            f"Kolejka: {total} pozycji ({pending} pending, {done} done, "
            f"{skipped} skipped, {errored} error)"
        )
        gen_until = scheduler.generated_until(items)
        days_left = scheduler.days_of_content_left(items)
        if gen_until:
            if days_left <= 2:
                self.status_gen.set(
                    f"Tresc wygenerowana do: {_fmt_date(gen_until)} "
                    f"- CZAS GENEROWAC KOLEJNY TYDZIEN (zostalo {days_left} dni)"
                )
            else:
                self.status_gen.set(
                    f"Tresc wygenerowana do: {_fmt_date(gen_until)} ({days_left} dni)"
                )
        else:
            self.status_gen.set("Tresc jeszcze nie wygenerowana - kliknij 'Generuj tresc tygodnia'")

        # Next artist info
        next_art = _next_artist_in_queue(items)
        self.status_next.set(next_art)

        # Odswiez side panel (selection moze byc pusta/nieaktualna)
        if hasattr(self, "_side_panel_frame"):
            self._refresh_side_panel()

    # ---------- Actions: refresh z Shopify ----------
    def _refresh_from_shopify(self) -> None:
        items = storage.load_queue()
        if items:
            # Juz jest kolejka - robimy delta detection zamiast full rebuild
            if not messagebox.askyesno(
                "Odswiezenie",
                "Kolejka istnieje. Chcesz:\n\n"
                "TAK = Wykryc nowych artystow/obrazy (delta) i wcisnac ich w kolejke.\n"
                "NIE = Pelny REBUILD (kasuje aktualny harmonogram!).\n\n"
                "Wybierz TAK jesli dodales artystow/obrazy i chcesz zaktualizowac kolejke.",
            ):
                if not messagebox.askyesno(
                    "Pelny rebuild",
                    "UWAGA: pelny rebuild nadpisze caly harmonogram i TRESC.\n"
                    "Kontynuowac?",
                ):
                    return
                self._run_full_rebuild()
                return
            self._run_delta_detect_and_apply()
            return
        # Brak kolejki - pelny build
        self._run_full_rebuild()

    def _run_full_rebuild(self) -> None:
        progress = _ProgressDialog(self.frame.winfo_toplevel(), "Budowanie kolejki z Shopify...")

        def _worker() -> None:
            try:
                items = queue_builder.build_queue_from_shopify(logger=progress.log)
                progress.log(f"Zbudowano {len(items)} pozycji. Przypisywanie slotow...")
                scheduler.assign_slots(items)
                storage.save_queue(items)
                progress.log("Gotowe.")
            except Exception as e:  # noqa: BLE001
                progress.log(f"BLAD: {e}")
                self.frame.after(0, lambda: messagebox.showerror(
                    "Odswiezenie", f"Blad: {e}", parent=self.frame.winfo_toplevel(),
                ))
                return
            self.frame.after(0, self._refresh_from_disk)
            self.frame.after(0, progress.close_after_delay)

        threading.Thread(target=_worker, daemon=True).start()

    def _run_delta_detect_and_apply(self) -> None:
        progress = _ProgressDialog(self.frame.winfo_toplevel(), "Wykrywanie zmian w Shopify...")

        def _worker() -> None:
            try:
                deltas = queue_builder.detect_deltas(logger=progress.log)
                progress.log(deltas.summary_text)
                if not (deltas.new_artists or deltas.new_paintings):
                    self.frame.after(0, progress.close_after_delay)
                    return
                items = storage.load_queue()
                added = queue_builder.apply_deltas(items, deltas)
                progress.log(f"Dodano {added} pozycji. Przeliczanie slotow...")
                scheduler.reassign_from_now(items)
                storage.save_queue(items)
                progress.log("Gotowe.")
            except Exception as e:  # noqa: BLE001
                progress.log(f"BLAD: {e}")
                self.frame.after(0, lambda: messagebox.showerror(
                    "Odswiezenie", f"Blad: {e}", parent=self.frame.winfo_toplevel(),
                ))
                return
            self.frame.after(0, self._refresh_from_disk)
            self.frame.after(0, progress.close_after_delay)

        threading.Thread(target=_worker, daemon=True).start()

    # ---------- Actions: przesuniecia ----------
    def _shift_all(self, delta: int) -> None:
        items = storage.load_queue()
        moved = scheduler.shift_all_pending(items, delta)
        storage.save_queue(items)
        self._refresh_from_disk()
        show_toast(self.frame.winfo_toplevel(), f"Przesunieto {moved} pozycji o {delta:+d} dzien")

    def _shift_selected(self, delta: int) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        items = storage.load_queue()
        item_id = sel[0]
        if scheduler.shift_single(items, item_id, delta):
            storage.save_queue(items)
            self._refresh_from_disk()

    def _move_selected(self, direction: int) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        items = storage.load_queue()
        if scheduler.reorder_move(items, sel[0], direction):
            scheduler.reassign_from_now(items)
            storage.save_queue(items)
            self._refresh_from_disk()

    # ---------- Actions: edycja / publikacja ----------
    def _edit_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        edit_dialog.open_edit_dialog(
            self.frame.winfo_toplevel(), sel[0],
            on_saved=self._refresh_from_disk,
        )

    def _skip_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        storage.update_item(sel[0], status="skipped")
        self._refresh_from_disk()

    def _delete_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        count = len(sel)
        msg = (
            f"Usunac {count} zaznaczonych pozycji z kolejki?\n\n"
            "Mozna je odzyskac tylko przez pelny rebuild."
            if count > 1
            else "Usunac pozycje z kolejki? (Mozna ja odzyskac tylko przez pelny rebuild)."
        )
        if not messagebox.askyesno("Usun z kolejki", msg):
            return
        # Batch delete - jeden save_queue zamiast N
        items = storage.load_queue()
        sel_set = set(sel)
        filtered = [it for it in items if it.id not in sel_set]
        storage.save_queue(filtered)
        self._refresh_from_disk()
        show_toast(self.frame.winfo_toplevel(), f"Usunieto {count} pozycji")

    def _skip_multi(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        items = storage.load_queue()
        sel_set = set(sel)
        for it in items:
            if it.id in sel_set:
                it.status = "skipped"
        storage.save_queue(items)
        self._refresh_from_disk()

    def _start_from_artist(self) -> None:
        """Dialog wyboru artysty + rotacja kolejki tak, zeby on byl pierwszy."""
        items = storage.load_queue()
        pending = [it for it in items if it.status in ("pending", "ready")]
        if not pending:
            messagebox.showinfo(
                "Rozpocznij od artysty",
                "Kolejka jest pusta lub wszystkie pozycje sa done/skipped.",
            )
            return

        # Lista unikalnych artystow w kolejnosci pojawienia (pending)
        ordered_unique: list[str] = []
        seen: set[str] = set()
        for it in pending:
            if it.artist and it.artist not in seen:
                seen.add(it.artist)
                ordered_unique.append(it.artist)

        if len(ordered_unique) < 2:
            messagebox.showinfo(
                "Rozpocznij od artysty",
                "W kolejce jest tylko jeden artysta - nie ma co rotowac.",
            )
            return

        dlg = tk.Toplevel(self.frame.winfo_toplevel())
        dlg.title("Rozpocznij od artysty")
        dlg.geometry("520x260")
        try:
            dlg.transient(self.frame.winfo_toplevel())
        except tk.TclError:
            pass

        outer = ttk.Frame(dlg, padding=(16, 14))
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text=(
                "Wybierz artyste, od ktorego ma sie rozpoczac kolejka.\n\n"
                "Artysci alfabetycznie PRZED wybranym zostana przesunieci na koniec\n"
                "kolejki (nic sie nie straci - tylko zmiana kolejnosci).\n\n"
                "Po rotacji sloty czasowe sa przeliczane od dzisiaj."
            ),
            foreground="#444",
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        row = ttk.Frame(outer)
        row.pack(fill="x", pady=(0, 12))
        ttk.Label(row, text="Artysta:").pack(side="left", padx=(0, 8))

        artist_var = tk.StringVar(value=ordered_unique[0])
        combo = ttk.Combobox(
            row, textvariable=artist_var,
            values=ordered_unique, state="readonly", width=36,
        )
        combo.pack(side="left", fill="x", expand=True)

        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(8, 0))

        def _apply() -> None:
            chosen = artist_var.get().strip()
            if not chosen:
                dlg.destroy()
                return
            items2 = storage.load_queue()
            moved = scheduler.rotate_to_artist(items2, chosen)
            if moved == 0:
                messagebox.showinfo(
                    "Rozpocznij od artysty",
                    f"Artysta '{chosen}' jest juz pierwszy w kolejce.",
                    parent=dlg,
                )
                dlg.destroy()
                return
            scheduler.reassign_from_now(items2)
            storage.save_queue(items2)
            self._refresh_from_disk()
            show_toast(
                self.frame.winfo_toplevel(),
                f"Kolejka rozpoczyna sie od '{chosen}' - przesunieto {moved} pozycji na koniec",
            )
            dlg.destroy()

        ttk.Button(btns, text="Zastosuj", command=_apply).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right")

    def _clear_queue(self) -> None:
        items = storage.load_queue()
        if not items:
            messagebox.showinfo("Wyczysc kolejke", "Kolejka jest juz pusta.")
            return
        if not messagebox.askyesno(
            "Wyczysc kolejke",
            f"Usunac WSZYSTKIE {len(items)} pozycji z kolejki?\n\n"
            "To kasuje cala kolejke (takze posty ktore juz sa opublikowane zniknia z listy).\n"
            "Opublikowane posty w Meta/Shopify zostaja - tutaj usuwamy tylko lokalna kolejke.\n\n"
            "Kolejke mozna odbudowac: 'Odswiez z Shopify' -> pelny rebuild.",
        ):
            return
        # Druga potwierdzenie - to nieodwracalna operacja
        if not messagebox.askyesno(
            "Ostateczne potwierdzenie",
            "Na pewno? Wszystkie wygenerowane tresci tez przepadna.",
        ):
            return
        storage.save_queue([])
        # Resetujemy tez generation_state.artists_snapshot zeby pelny rebuild zaczal od zera
        state = storage.load_generation_state()
        state.pop("artists_snapshot", None)
        state.pop("artists_hash", None)
        state.pop("paintings_hash", None)
        storage.save_generation_state(state)
        self._refresh_from_disk()
        show_toast(self.frame.winfo_toplevel(), "Kolejka wyczyszczona")

    def _publish_now_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = storage.get_item(sel[0])
        if item is None:
            return
        if not messagebox.askyesno(
            "Publikacja",
            f"Opublikowac teraz:\n\n{item.artist} - {item.painting_title_pl}\n\n"
            "na wszystkich aktywnych kanalach? (wymaga skonfigurowanych tokenow Meta API)",
        ):
            return

        progress = _ProgressDialog(self.frame.winfo_toplevel(), "Publikuje...")

        def _worker() -> None:
            try:
                items = storage.load_queue()
                target = next((it for it in items if it.id == item.id), None)
                if target is None:
                    return
                results = meta_publisher.publish_item(target, logger=progress.log)
                storage.save_queue(items)
                progress.log("--- WYNIKI ---")
                for ch, res in results.items():
                    progress.log(f"  {ch}: {res}")
            except Exception as e:  # noqa: BLE001
                progress.log(f"BLAD: {e}")
                return
            self.frame.after(0, self._refresh_from_disk)
            self.frame.after(0, progress.close_after_delay)

        threading.Thread(target=_worker, daemon=True).start()

    def _manual_send_selected(self) -> None:
        """Kopiuje caption do schowka, otwiera folder obrazow + 4 URL-e stron."""
        sel = self.tree.selection()
        if not sel:
            return
        item = storage.get_item(sel[0])
        if item is None:
            return
        toplvl = self.frame.winfo_toplevel()

        # Buduj ladny blok z 4 captions
        parts = [
            f"=== {item.artist} - {item.painting_title_pl} ===",
            "",
            "--- Facebook PL ---",
            item.caption_fb_pl or item.caption_pl or "(brak tresci)",
            "",
            "--- Facebook EN ---",
            item.caption_fb_en or item.caption_en or "(brak tresci)",
            "",
            "--- Instagram PL (z hashtagami) ---",
            (item.caption_ig_pl or item.caption_pl or "(brak)") + "\n\n" + " ".join(item.hashtags_pl),
            "",
            "--- Instagram EN (z hashtagami) ---",
            (item.caption_ig_en or item.caption_en or "(brak)") + "\n\n" + " ".join(item.hashtags_en),
        ]
        blob = "\n".join(parts)
        toplvl.clipboard_clear()
        toplvl.clipboard_append(blob)
        toplvl.update()

        # Otworz folder obrazow dla tej pozycji
        folder = img_mod.painting_dir_abs(item.artist_handle, item.painting_handle)
        if folder.is_dir():
            self._open_path(folder)

        show_toast(toplvl, "Skopiowano wszystkie 4 captions do schowka")
        # Otworz strony
        for ch in _cp.all_channels():
            webbrowser.open(ch.page_url)

    def _copy_caption(self, lang: str) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = storage.get_item(sel[0])
        if item is None:
            return
        text = item.caption_pl if lang == "pl" else item.caption_en
        if not text:
            text = item.caption_fb_pl if lang == "pl" else item.caption_fb_en
        toplvl = self.frame.winfo_toplevel()
        toplvl.clipboard_clear()
        toplvl.clipboard_append(text or "")
        toplvl.update()
        show_toast(toplvl, f"Skopiowano caption ({lang.upper()})")

    # ---------- Context menu ----------
    def _show_context_menu(self, event: tk.Event) -> None:
        row = self.tree.identify_row(event.y)
        # Gdy kliknieto w juz zaznaczona grupe - zachowaj zaznaczenie.
        # Gdy kliknieto poza zaznaczeniem (albo na pojedynczym wierszu) - ustaw
        # tylko ten wiersz.
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        sel = self.tree.selection()
        if not sel:
            return
        multi = len(sel) > 1

        m = tk.Menu(self.frame.winfo_toplevel(), tearoff=0)
        if multi:
            m.add_command(label=f"[{len(sel)} pozycji zaznaczonych]", state="disabled")
            m.add_separator()
            m.add_command(label=f"Pomin zaznaczone ({len(sel)})", command=self._skip_multi)
            m.add_command(label=f"Usun zaznaczone ({len(sel)})",
                          command=self._delete_selected)
            m.add_separator()
            m.add_command(label="(Edycja / Publikacja dostepne tylko przy 1 pozycji)",
                          state="disabled")
        else:
            m.add_command(label="Edytuj...", command=self._edit_selected)
            m.add_command(label="Publikuj teraz", command=self._publish_now_selected)
            m.add_command(label="Wyslij w trybie manualnym", command=self._manual_send_selected)
            m.add_separator()
            m.add_command(label="Przesun +1 dzien (ta pozycja)",
                          command=lambda: self._shift_selected(1))
            m.add_command(label="Przesun -1 dzien (ta pozycja)",
                          command=lambda: self._shift_selected(-1))
            m.add_command(label="Gora (w liscie)", command=lambda: self._move_selected(-1))
            m.add_command(label="Dol (w liscie)", command=lambda: self._move_selected(1))
            m.add_separator()
            copy_menu = tk.Menu(m, tearoff=0)
            copy_menu.add_command(label="PL", command=lambda: self._copy_caption("pl"))
            copy_menu.add_command(label="EN", command=lambda: self._copy_caption("en"))
            m.add_cascade(label="Kopiuj caption", menu=copy_menu)
            m.add_separator()
            m.add_command(label="Pomin", command=self._skip_selected)
            m.add_command(label="Usun z kolejki", command=self._delete_selected)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    # ---------- Content generator ----------
    def _open_content_generator(self) -> None:
        items = storage.load_queue()
        pending = [it for it in items if it.status in ("pending", "ready") and not it.manual_override]
        if not pending:
            messagebox.showinfo("Generator tresci", "Brak pozycji do wygenerowania.")
            return
        try:
            prompt = content_gen.build_week_prompt(items)
        except ValueError as e:
            messagebox.showinfo("Generator tresci", str(e))
            return

        _open_generator_dialog(
            self.frame.winfo_toplevel(),
            prompt=prompt,
            expected_ids=[
                it.id for it in items
                if it.status in ("pending", "ready") and not it.manual_override
            ][: content_gen.DEFAULT_BATCH_SIZE],
            on_applied=self._refresh_from_disk,
        )

    # ---------- Checklist ----------
    def _show_checklist(self) -> None:
        items = storage.load_queue()
        reports = img_mod.missing_report(items)
        if not reports:
            messagebox.showinfo("Lista kontrolna", "Kolejka jest pusta.")
            return

        dlg = tk.Toplevel(self.frame.winfo_toplevel())
        dlg.title("Lista kontrolna zdjec")
        dlg.geometry("940x620")

        top = ttk.Frame(dlg, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(
            top, text="Lista kontrolna braku zdjec",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")
        only_missing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Tylko braki", variable=only_missing_var,
                        command=lambda: _fill(only_missing_var.get())).pack(side="right")

        tree_frame = ttk.Frame(dlg)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        cols = ("date", "artist", "title", "main", "zooms", "mockup", "missing")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=20)
        headers = {
            "date": "Data", "artist": "Artysta", "title": "Tytul",
            "main": "main", "zooms": "zoomy", "mockup": "MOCKUP",
            "missing": "Brakuje",
        }
        widths = {
            "date": 90, "artist": 140, "title": 180,
            "main": 50, "zooms": 60, "mockup": 60, "missing": 180,
        }
        for c in cols:
            tree.heading(c, text=headers[c])
            tree.column(c, width=widths[c], anchor=("center" if c in ("main", "zooms", "mockup") else "w"))
        sb_v = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb_v.set)
        tree.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        tree.tag_configure("missing", background="#fff4d6")
        tree.tag_configure("ok", foreground="#388e3c")

        def _fill(only_missing: bool) -> None:
            for iid in tree.get_children():
                tree.delete(iid)
            for r in reports:
                missing = r.missing_labels()
                if only_missing and not missing:
                    continue
                date_part, _ = _split_iso(r.scheduled_at)
                tag = "missing" if missing else "ok"
                tree.insert("", "end", iid=r.item_id, values=(
                    date_part,
                    r.artist,
                    r.title_pl,
                    "YES" if r.has_main else "NO",
                    str(r.zooms_count),
                    "YES" if r.has_mockup else "NO",
                    ", ".join(missing) if missing else "(OK)",
                ), tags=(tag,))

        _fill(True)

        def _on_dbl(_e: object) -> None:
            sel = tree.selection()
            if not sel:
                return
            edit_dialog.open_edit_dialog(dlg, sel[0], on_saved=lambda: _fill(only_missing_var.get()))

        tree.bind("<Double-Button-1>", _on_dbl)

        btns = ttk.Frame(dlg)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Otworz folder obrazow",
                   command=self._open_images_folder).pack(side="left")
        ttk.Button(btns, text="Zamknij", command=dlg.destroy).pack(side="right")

    # ---------- Misc ----------
    def _open_meta_config(self) -> None:
        meta_config.open_meta_config_dialog(self.frame.winfo_toplevel(),
                                            on_saved=self._refresh_from_disk)

    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
            show_help(self.frame.winfo_toplevel(),
                      title="Cykl - Instrukcja", text=help_text.HELP_TEXT)
        except ImportError:
            messagebox.showinfo("Instrukcja", help_text.HELP_TEXT[:4000])

    def _open_images_folder(self) -> None:
        self._open_path(img_mod.open_images_folder())

    @staticmethod
    def _open_path(p) -> None:
        try:
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(p))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])  # noqa: S607
            else:
                subprocess.Popen(["xdg-open", str(p)])  # noqa: S607
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Dialog generatora tresci (Opus prompt + paste + parse)
# ---------------------------------------------------------------------------

def _open_generator_dialog(
    parent: tk.Misc,
    *,
    prompt: str,
    expected_ids: list[str],
    on_applied: Callable[[], None],
) -> tk.Toplevel:
    dlg = tk.Toplevel(parent)
    dlg.title("Cykl - Generator tresci na tydzien (Opus)")
    dlg.geometry("1080x860")
    dlg.minsize(900, 640)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    outer = ttk.Frame(dlg, padding=(10, 8))
    outer.pack(fill="both", expand=True)

    ttk.Label(
        outer,
        text=(
            "Krok 1: skopiuj prompt (przycisk ponizej lub Ctrl+A, Ctrl+C), "
            "wklej w chat Cursor z modelem Claude Opus, otrzymaj odpowiedz.\n"
            "Krok 2: skopiuj odpowiedz, wklej w dolne pole i kliknij 'Zastosuj'."
        ),
        foreground="#555",
        justify="left",
    ).pack(anchor="w", pady=(0, 6))

    nb = ttk.Notebook(outer)
    nb.pack(fill="both", expand=True)

    # Tab 1: Prompt
    prompt_tab = ttk.Frame(nb, padding=(6, 6))
    nb.add(prompt_tab, text="1. Prompt")
    prompt_text = tk.Text(prompt_tab, wrap="word", font=("Consolas", 9))
    prompt_text.insert("1.0", prompt)
    prompt_text.pack(fill="both", expand=True)

    def _copy_prompt() -> None:
        dlg.clipboard_clear()
        dlg.clipboard_append(prompt_text.get("1.0", "end-1c"))
        dlg.update()
        show_toast(dlg, "Prompt skopiowany do schowka")

    ttk.Button(prompt_tab, text="Kopiuj prompt do schowka", command=_copy_prompt).pack(
        anchor="w", pady=(6, 0)
    )

    # Tab 2: Odpowiedz
    resp_tab = ttk.Frame(nb, padding=(6, 6))
    nb.add(resp_tab, text="2. Odpowiedz")
    resp_text = tk.Text(resp_tab, wrap="word", font=("Consolas", 9))
    resp_text.pack(fill="both", expand=True)

    btns = ttk.Frame(resp_tab)
    btns.pack(fill="x", pady=(6, 0))

    def _paste_from_clipboard() -> None:
        try:
            content = dlg.clipboard_get()
        except tk.TclError:
            content = ""
        if content:
            resp_text.delete("1.0", "end")
            resp_text.insert("1.0", content)

    def _apply_response() -> None:
        raw = resp_text.get("1.0", "end-1c")
        try:
            content_map = content_gen.parse_week_response(raw, expected_ids)
        except ValueError as e:
            messagebox.showerror("Parser", str(e), parent=dlg)
            return
        items = storage.load_queue()
        count = content_gen.apply_to_queue(items, content_map)
        storage.save_queue(items)
        messagebox.showinfo("Gotowe", f"Zastosowano tresc do {count} pozycji.", parent=dlg)
        try:
            on_applied()
        except Exception:  # noqa: BLE001
            pass
        dlg.destroy()

    ttk.Button(btns, text="Wklej ze schowka", command=_paste_from_clipboard).pack(side="left")
    ttk.Button(btns, text="Zastosuj", command=_apply_response).pack(side="right")
    ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right", padx=(0, 6))

    return dlg


# ---------------------------------------------------------------------------
# ProgressDialog - okienko z logiem dla dlugich operacji (Shopify fetch, publish)
# ---------------------------------------------------------------------------

class _ProgressDialog:
    def __init__(self, parent: tk.Misc, title: str) -> None:
        self.dlg = tk.Toplevel(parent)
        self.dlg.title(title)
        self.dlg.geometry("640x380")
        try:
            self.dlg.transient(parent)
        except tk.TclError:
            pass
        self.text = tk.Text(self.dlg, wrap="word", font=("Consolas", 9),
                            bg="#1e1e1e", fg="#d4d4d4")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.text.configure(state="disabled")

    def log(self, msg: str) -> None:
        def _apply() -> None:
            try:
                self.text.configure(state="normal")
                self.text.insert("end", msg + "\n")
                self.text.see("end")
                self.text.configure(state="disabled")
            except tk.TclError:
                pass
        try:
            self.dlg.after(0, _apply)
        except tk.TclError:
            pass

    def close_after_delay(self, ms: int = 1500) -> None:
        try:
            self.dlg.after(ms, self.dlg.destroy)
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_iso(iso: str) -> tuple[str, str]:
    if not iso:
        return "", ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return "", ""
    return dt.date().isoformat(), dt.strftime("%H:%M")


def _fmt_date(iso: str) -> str:
    if not iso:
        return "?"
    try:
        dt = datetime.fromisoformat(iso + "T00:00:00") if len(iso) == 10 else datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return dt.strftime("%d.%m.%Y")


def _short_name(rel_path: str, max_len: int = 22) -> str:
    """Zwraca skrocona nazwe pliku (bez folderow) do wyswietlenia w wask side panelu."""
    if not rel_path:
        return "(brak)"
    name = rel_path.rsplit("/", 1)[-1]
    if len(name) <= max_len:
        return name
    # Skroc srodek: "dluga_naz...g.jpg"
    head = name[: max_len - 7]
    tail = name[-6:]
    return f"{head}...{tail}"


def _preview(text: str, max_len: int = 70) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "..."


def _channel_badge(item: storage.CykleItem, channel_code: str) -> str:
    if channel_code not in item.channels_enabled:
        return "-"
    status = getattr(item, f"published_{channel_code}", "")
    if status.startswith("done@"):
        return "OK"
    if status.startswith("error"):
        return "ERR"
    return "."


def _status_label(status: str) -> str:
    return {
        "pending": "Pending",
        "ready": "Ready",
        "publishing": "Publikacja",
        "done": "Done",
        "skipped": "Skipped",
        "error": "Blad",
    }.get(status, status)


def _next_artist_in_queue(items) -> str:
    """Zwraca skrot 'Aktualnie: X (3/7) -> nastepny Y'."""
    for it in items:
        if it.status in ("pending", "ready"):
            nxt = f" -> {it.next_artist}" if (it.is_last_of_artist and it.next_artist) else ""
            return f"Aktualnie: {it.artist} ({it.artist_position}/{it.artist_total}){nxt}"
    return ""
