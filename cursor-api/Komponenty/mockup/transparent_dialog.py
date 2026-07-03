"""Okno: wersje przezroczyste mockupow per produkt."""

from __future__ import annotations

import io
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.activity_log import append_activity
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.description_update import load_product_catalog_rows, product_catalog_sort_key
from Komponenty.dodajobraz.parser import MOCKUP_DISPLAY_ORIGINAL, MOCKUP_DISPLAY_TRANSPARENT

from PIL import Image, ImageTk

from .transparent import (
    ProductMockupImage,
    delete_product_mockup,
    download_image_bytes,
    find_mockup_pair,
    list_product_mockups,
    load_mockup_display_prefs,
    save_mockup_display_pref,
    upload_transparent_mockup_file,
)

_DISPLAY_CHOICES = (
    ("Oryginalny", MOCKUP_DISPLAY_ORIGINAL),
    ("Przezroczysty", MOCKUP_DISPLAY_TRANSPARENT),
)

_TRANSPARENT_FILE_HINT = (
    "Plik przezroczysty: ramka + grafika (WEBP/PNG z alfa). "
    "Bez bialego passe-partout — obwodka jest tylko w wersji oryginalnej CZB."
)


class TransparentMockupsDialog:
    def __init__(self, parent: tk.Misc, *, enqueue_log: Callable[[str], None] | None = None) -> None:
        self.parent = parent
        self._enqueue_log = enqueue_log
        self._products: list[dict[str, Any]] = []
        self._filtered_products: list[dict[str, Any]] = []
        self._mockups: list[ProductMockupImage] = []
        self._display_prefs: dict[str, str] = {}
        self._selected_product: dict[str, Any] | None = None
        self._selected_mockup: ProductMockupImage | None = None
        self._preview_photo: tk.PhotoImage | None = None
        self._preview_job: str | None = None

        self.win = tk.Toplevel(parent)
        self.win.title("Przezroczyste mockupy")
        position_toplevel_screen_center(self.win, 1080, 720)
        self.win.minsize(900, 560)

        self.filter_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Laduje liste produktow...")
        self.product_count_var = tk.StringVar(value="")
        self.mockup_status_var = tk.StringVar(value="Wybierz produkt z listy.")
        self.display_var = tk.StringVar(value=_DISPLAY_CHOICES[0][0])

        self._build_ui()
        self.filter_var.trace_add("write", lambda *_: self._refresh_product_tree())
        self._load_products()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self.win)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Filtr:").pack(side="left")
        ttk.Entry(top, textvariable=self.filter_var, width=36).pack(side="left", padx=(6, 8))
        ttk.Label(top, textvariable=self.product_count_var, foreground="#0a6").pack(side="left")
        ttk.Label(top, textvariable=self.status_var, foreground="#666").pack(side="right")

        paned = ttk.Panedwindow(self.win, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, **pad)

        left = ttk.LabelFrame(paned, text="Produkty", padding=6)
        paned.add(left, weight=3)

        prod_cols = ("title", "handle")
        self.product_tree = ttk.Treeview(
            left, columns=prod_cols, show="headings", height=14, selectmode="browse"
        )
        self.product_tree.heading("title", text="Produkt")
        self.product_tree.heading("handle", text="Handle")
        self.product_tree.column("title", width=420, stretch=True)
        self.product_tree.column("handle", width=180, stretch=False)
        psb = ttk.Scrollbar(left, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=psb.set)
        self.product_tree.pack(side="left", fill="both", expand=True)
        psb.pack(side="right", fill="y")
        self.product_tree.bind("<<TreeviewSelect>>", self._on_product_select)

        right = ttk.Frame(paned)
        paned.add(right, weight=4)

        mockup_frame = ttk.LabelFrame(right, text="Mockupy produktu", padding=6)
        mockup_frame.pack(fill="both", expand=True)

        mock_cols = ("variant", "kind", "alt")
        self.mockup_tree = ttk.Treeview(
            mockup_frame, columns=mock_cols, show="headings", height=8, selectmode="extended"
        )
        self.mockup_tree.heading("variant", text="Wariant")
        self.mockup_tree.heading("kind", text="Typ")
        self.mockup_tree.heading("alt", text="Alt")
        self.mockup_tree.column("variant", width=70, stretch=False)
        self.mockup_tree.column("kind", width=110, stretch=False)
        self.mockup_tree.column("alt", width=360, stretch=True)
        msb = ttk.Scrollbar(mockup_frame, orient="vertical", command=self.mockup_tree.yview)
        self.mockup_tree.configure(yscrollcommand=msb.set)
        self.mockup_tree.pack(side="left", fill="both", expand=True)
        msb.pack(side="right", fill="y")
        self.mockup_tree.bind("<<TreeviewSelect>>", self._on_mockup_select)

        detail = ttk.LabelFrame(right, text="Podglad i ustawienia", padding=8)
        detail.pack(fill="both", expand=True, pady=(8, 0))

        ttk.Label(
            detail,
            text=_TRANSPARENT_FILE_HINT,
            wraplength=480,
            justify="left",
            foreground="#555",
        ).pack(anchor="w", fill="x", pady=(0, 6))

        ttk.Label(detail, textvariable=self.mockup_status_var, wraplength=480, justify="left").pack(
            anchor="w", fill="x"
        )

        self.preview_canvas = tk.Canvas(
            detail, bg="#eceff1", highlightthickness=1, highlightbackground="#cfd8dc", height=220
        )
        self.preview_canvas.pack(fill="both", expand=True, pady=(8, 8))

        row = ttk.Frame(detail)
        row.pack(fill="x")
        ttk.Label(row, text="Wyswietlaj na stronie:").pack(side="left")
        self.display_combo = ttk.Combobox(
            row,
            textvariable=self.display_var,
            values=[label for label, _ in _DISPLAY_CHOICES],
            state="readonly",
            width=18,
        )
        self.display_combo.pack(side="left", padx=(8, 0))
        self.display_combo.bind("<<ComboboxSelected>>", self._on_display_changed)

        btn_row = ttk.Frame(detail)
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(
            btn_row, text="Dodaj wersje przezroczysta...", command=self._add_transparent_from_disk
        ).pack(side="left")
        ttk.Button(btn_row, text="Usun zaznaczone mockupy", command=self._delete_selected_mockups).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(btn_row, text="Otworz w Shopify", command=self._open_admin).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Odswiez", command=self._reload_selected_product).pack(side="right")
        ttk.Button(btn_row, text="Zamknij", command=self.win.destroy).pack(side="right", padx=(0, 8))

    def _log(self, msg: str) -> None:
        if self._enqueue_log:
            self._enqueue_log(msg)

    def _product_iid(self, row: dict[str, Any]) -> str:
        return str(row.get("product_id") or "")

    def _mockup_iid(self, mockup: ProductMockupImage) -> str:
        return str(mockup.image_id)

    def _load_products(self) -> None:
        def worker() -> None:
            try:
                rows = load_product_catalog_rows(
                    logger=self._log,
                    on_progress=lambda msg: self.win.after(
                        0, lambda m=msg: self.status_var.set(m)
                    ),
                )
            except Exception as exc:
                self.win.after(0, lambda: self._products_failed(str(exc)))
                return
            self.win.after(0, lambda: self._products_loaded(rows))

        threading.Thread(target=worker, daemon=True).start()

    def _products_failed(self, err: str) -> None:
        self.status_var.set("Blad pobierania produktow.")
        messagebox.showerror("Przezroczyste mockupy", err, parent=self.win)

    def _products_loaded(self, rows: list[dict[str, Any]]) -> None:
        self._products = rows
        self._refresh_product_tree()
        self.status_var.set("Gotowe. Wybierz produkt.")

    def _refresh_product_tree(self) -> None:
        needle = (self.filter_var.get() or "").strip().lower()
        if needle:
            filtered = [
                r
                for r in self._products
                if needle in (r.get("product_title") or "").lower()
                or needle in (r.get("artist") or "").lower()
                or needle in (r.get("painting_title") or "").lower()
                or needle in (r.get("handle") or "").lower()
            ]
        else:
            filtered = list(self._products)
        filtered.sort(key=product_catalog_sort_key)
        self._filtered_products = filtered

        self.product_tree.delete(*self.product_tree.get_children())
        for row in filtered:
            self.product_tree.insert(
                "",
                "end",
                iid=self._product_iid(row),
                values=(row.get("product_title") or "", row.get("handle") or ""),
            )
        self.product_count_var.set(f"Produkty: {len(filtered)}/{len(self._products)}")

    def _selected_product_row(self) -> dict[str, Any] | None:
        sel = self.product_tree.selection()
        if not sel:
            return None
        pid = sel[0]
        for row in self._filtered_products:
            if self._product_iid(row) == pid:
                return row
        return None

    def _on_product_select(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        row = self._selected_product_row()
        if not row:
            return
        self._selected_product = row
        self._load_product_mockups(int(row["product_id"]))

    def _load_product_mockups(self, product_id: int) -> None:
        self.mockup_status_var.set("Laduje mockupy produktu...")
        self.mockup_tree.delete(*self.mockup_tree.get_children())
        self._mockups = []
        self._selected_mockup = None
        self._clear_preview()

        def worker() -> None:
            try:
                shop, token = sc.load_session()
                images = sc.list_product_images(shop, token, product_id)
                mockups = list_product_mockups(images)
                prefs = load_mockup_display_prefs(shop, token, product_id)
            except Exception as exc:
                self.win.after(0, lambda: self._mockups_failed(str(exc)))
                return
            self.win.after(0, lambda: self._mockups_loaded(mockups, prefs))

        threading.Thread(target=worker, daemon=True).start()

    def _mockups_failed(self, err: str) -> None:
        self.mockup_status_var.set(f"Blad: {err}")
        messagebox.showerror("Przezroczyste mockupy", err, parent=self.win)

    def _mockups_loaded(self, mockups: list[ProductMockupImage], prefs: dict[str, str]) -> None:
        self._mockups = mockups
        self._display_prefs = prefs
        self.mockup_tree.delete(*self.mockup_tree.get_children())
        if not mockups:
            self.mockup_status_var.set("Brak mockupow w galerii tego produktu.")
            return
        for m in mockups:
            kind = "przezroczysty" if m.is_transparent else "oryginalny"
            self.mockup_tree.insert(
                "",
                "end",
                iid=self._mockup_iid(m),
                values=(m.variant or "—", kind, m.alt or "(brak alt)"),
            )
        self.mockup_status_var.set(f"Mockupy: {len(mockups)}. Zaznacz pozycje, aby zobaczyc podglad.")

    def _selected_mockup_rows(self) -> list[ProductMockupImage]:
        sel = self.mockup_tree.selection()
        if not sel:
            return []
        by_id = {self._mockup_iid(m): m for m in self._mockups}
        return [by_id[iid] for iid in sel if iid in by_id]

    def _selected_mockup_row(self) -> ProductMockupImage | None:
        rows = self._selected_mockup_rows()
        return rows[0] if rows else None

    def _on_mockup_select(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        if self._preview_job:
            try:
                self.win.after_cancel(self._preview_job)
            except tk.TclError:
                pass
        self._preview_job = self.win.after(80, self._refresh_mockup_detail)

    def _display_label_for_variant(self, variant: str) -> str:
        pref = self._display_prefs.get((variant or "").upper(), MOCKUP_DISPLAY_ORIGINAL)
        for label, val in _DISPLAY_CHOICES:
            if val == pref:
                return label
        return _DISPLAY_CHOICES[0][0]

    def _refresh_mockup_detail(self) -> None:
        self._preview_job = None
        mockup = self._selected_mockup_row()
        self._selected_mockup = mockup
        if mockup is None:
            self.mockup_status_var.set("Zaznacz mockup na liscie.")
            self._clear_preview()
            return

        _original, transparent = find_mockup_pair(self._mockups, source=mockup)
        variant = (mockup.variant or "DEFAULT").upper()
        self.display_var.set(self._display_label_for_variant(mockup.variant))

        parts = [f"Wariant: {mockup.variant or '—'}"]
        parts.append("Ma wersje przezroczysta" if transparent else "Brak wersji przezroczystej")
        parts.append(f"Wyswietlanie: {self._display_prefs.get(variant, MOCKUP_DISPLAY_ORIGINAL)}")
        self.mockup_status_var.set(" | ".join(parts))

        preview_src = mockup.src
        pref = self._display_prefs.get(variant, MOCKUP_DISPLAY_ORIGINAL)
        if pref == MOCKUP_DISPLAY_TRANSPARENT and transparent:
            preview_src = transparent.src
        elif not mockup.is_transparent and _original:
            preview_src = _original.src
        self._load_preview(preview_src)

    def _clear_preview(self) -> None:
        self.preview_canvas.delete("all")
        self._preview_photo = None

    def _load_preview(self, url: str) -> None:
        self._clear_preview()
        if not url:
            return
        self.preview_canvas.create_text(
            10, 10, anchor="nw", text="Laduje podglad...", fill="#78909c", font=("Segoe UI", 10)
        )

        def worker() -> None:
            try:
                data = download_image_bytes(url)
                with Image.open(io.BytesIO(data)) as im:
                    thumb = im.copy()
                    thumb.thumbnail((460, 200), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(thumb)

                def ui() -> None:
                    if not self.win.winfo_exists():
                        return
                    self._preview_photo = photo
                    self.preview_canvas.delete("all")
                    cw = max(self.preview_canvas.winfo_width(), 320)
                    ch = max(self.preview_canvas.winfo_height(), 180)
                    self.preview_canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center")

                self.win.after(0, ui)
            except Exception as exc:
                self.win.after(
                    0,
                    lambda: self.mockup_status_var.set(f"Podglad niedostepny: {exc}"),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _display_value_from_label(self, label: str) -> str:
        for lbl, val in _DISPLAY_CHOICES:
            if lbl == label:
                return val
        return MOCKUP_DISPLAY_ORIGINAL

    def _on_display_changed(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        product = self._selected_product
        mockup = self._selected_mockup_row()
        if not product or not mockup:
            return
        variant = mockup.variant
        if not variant:
            messagebox.showinfo(
                "Przezroczyste mockupy",
                "Nie mozna ustalic wariantu mockupu (CZB/CZCZ).",
                parent=self.win,
            )
            return
        display = self._display_value_from_label(self.display_var.get())
        if display == MOCKUP_DISPLAY_TRANSPARENT:
            _orig, transparent = find_mockup_pair(self._mockups, source=mockup)
            if not transparent:
                messagebox.showwarning(
                    "Przezroczyste mockupy",
                    "Najpierw dodaj wersje przezroczysta dla tego mockupu.",
                    parent=self.win,
                )
                self.display_var.set(_DISPLAY_CHOICES[0][0])
                return

        pid = int(product["product_id"])

        def worker() -> None:
            try:
                shop, token = sc.load_session()
                prefs = save_mockup_display_pref(
                    shop,
                    token,
                    pid,
                    variant=variant,
                    display=display,
                    existing=self._display_prefs,
                    logger=self._log,
                )
            except Exception as exc:
                self.win.after(
                    0,
                    lambda: messagebox.showerror("Przezroczyste mockupy", str(exc), parent=self.win),
                )
                return
            self.win.after(0, lambda: self._display_saved(prefs, display))

        threading.Thread(target=worker, daemon=True).start()

    def _display_saved(self, prefs: dict[str, str], display: str) -> None:
        self._display_prefs = prefs
        append_activity(
            "mockup",
            f"Wyswietlanie mockupu: {display}",
            detail=(self._selected_product or {}).get("product_title", ""),
        )
        self._refresh_mockup_detail()

    def _add_transparent_from_disk(self) -> None:
        product = self._selected_product
        mockup = self._selected_mockup_row()
        if not product:
            messagebox.showinfo("Przezroczyste mockupy", "Wybierz produkt.", parent=self.win)
            return
        if not mockup:
            messagebox.showinfo("Przezroczyste mockupy", "Zaznacz mockup.", parent=self.win)
            return
        if mockup.is_transparent:
            messagebox.showinfo(
                "Przezroczyste mockupy",
                "Zaznacz oryginalny mockup — na jego podstawie dodamy wersje przezroczysta.",
                parent=self.win,
            )
            return

        _original, transparent = find_mockup_pair(self._mockups, source=mockup)
        replace_existing = False
        if transparent:
            if not messagebox.askyesno(
                "Przezroczyste mockupy",
                "Wersja przezroczysta tego wariantu juz istnieje.\n\n"
                "Zastapic istniejacy plik nowym z dysku?",
                parent=self.win,
            ):
                return
            replace_existing = True

        path_str = filedialog.askopenfilename(
            parent=self.win,
            title="Wybierz plik — przezroczysty mockup",
            filetypes=[
                ("Obrazy", "*.webp *.png *.jpg *.jpeg *.tif *.tiff *.bmp"),
                ("Wszystkie", "*.*"),
            ],
        )
        if not path_str:
            return

        pid = int(product["product_id"])
        file_path = Path(path_str)
        self.mockup_status_var.set(f"Wysylam: {file_path.name}...")

        def worker() -> None:
            try:
                res = upload_transparent_mockup_file(
                    product_id=pid,
                    source=mockup,
                    file_path=file_path,
                    replace_existing=replace_existing,
                    display_prefs=self._display_prefs,
                    logger=self._log,
                )
            except Exception as exc:
                self.win.after(
                    0,
                    lambda: messagebox.showerror("Przezroczyste mockupy", str(exc), parent=self.win),
                )
                return
            self.win.after(0, lambda: self._upload_done(res))

        threading.Thread(target=worker, daemon=True).start()

    def _upload_done(self, res: dict[str, Any]) -> None:
        if res.get("skipped"):
            messagebox.showinfo(
                "Przezroczyste mockupy",
                res.get("reason") or "Pominieto.",
                parent=self.win,
            )
            return
        prefs = res.get("display_prefs")
        if isinstance(prefs, dict):
            self._display_prefs = prefs
        append_activity(
            "mockup",
            "Dodano przezroczysty mockup z dysku",
            detail=(self._selected_product or {}).get("product_title", ""),
        )
        messagebox.showinfo(
            "Przezroczyste mockupy",
            "Wersja przezroczysta dodana do galerii produktu.",
            parent=self.win,
        )
        if self._selected_product:
            self._load_product_mockups(int(self._selected_product["product_id"]))

    def _delete_selected_mockups(self) -> None:
        product = self._selected_product
        mockups = self._selected_mockup_rows()
        if not product:
            messagebox.showinfo("Przezroczyste mockupy", "Wybierz produkt.", parent=self.win)
            return
        if not mockups:
            messagebox.showinfo(
                "Przezroczyste mockupy",
                "Zaznacz co najmniej jeden mockup do usuniecia.",
                parent=self.win,
            )
            return

        labels = "\n".join(f"• {(m.alt or m.src)[:80]}" for m in mockups[:8])
        extra = f"\n… i {len(mockups) - 8} wiecej" if len(mockups) > 8 else ""
        if not messagebox.askyesno(
            "Przezroczyste mockupy",
            f"Trwale usunac {len(mockups)} mockup(ow) z galerii Shopify?\n\n{labels}{extra}",
            parent=self.win,
        ):
            return

        pid = int(product["product_id"])
        self.mockup_status_var.set("Usuwam mockupy...")

        def worker() -> None:
            ok = err = 0
            prefs = dict(self._display_prefs)
            try:
                shop, token = sc.load_session()
                for mockup in mockups:
                    try:
                        prefs = delete_product_mockup(
                            shop,
                            token,
                            pid,
                            mockup,
                            display_prefs=prefs,
                            logger=self._log,
                        )
                        ok += 1
                    except Exception as exc:
                        err += 1
                        self._log(f"[mockup] BLAD usuwania id={mockup.image_id}: {exc}")
            except Exception as exc:
                self.win.after(
                    0,
                    lambda: messagebox.showerror("Przezroczyste mockupy", str(exc), parent=self.win),
                )
                return
            self.win.after(0, lambda: self._delete_done(ok, err, prefs))

        threading.Thread(target=worker, daemon=True).start()

    def _delete_done(self, ok: int, err: int, prefs: dict[str, str]) -> None:
        self._display_prefs = prefs
        if ok:
            append_activity(
                "mockup",
                f"Usunieto mockupow: {ok}",
                detail=(self._selected_product or {}).get("product_title", ""),
            )
        messagebox.showinfo(
            "Przezroczyste mockupy",
            f"Usunieto: {ok}\nBledy: {err}",
            parent=self.win,
        )
        if self._selected_product:
            self._load_product_mockups(int(self._selected_product["product_id"]))

    def _reload_selected_product(self) -> None:
        row = self._selected_product_row()
        if not row:
            messagebox.showinfo("Przezroczyste mockupy", "Wybierz produkt.", parent=self.win)
            return
        self._load_product_mockups(int(row["product_id"]))

    def _open_admin(self) -> None:
        row = self._selected_product_row()
        if not row:
            messagebox.showinfo("Przezroczyste mockupy", "Wybierz produkt.", parent=self.win)
            return
        url = row.get("admin_url") or ""
        if url:
            webbrowser.open(url)


def open_transparent_mockups_dialog(
    parent: tk.Misc, *, enqueue_log: Callable[[str], None] | None = None
) -> None:
    TransparentMockupsDialog(parent, enqueue_log=enqueue_log)
