"""GUI: Informacje o plikach — lista produktow + szczegoly grafik w Shopify."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Any

from Komponenty._shared.clipboard_image import copy_image_url_to_clipboard
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.dodajobraz.description_update import (
    load_product_catalog_rows,
    product_catalog_sort_key,
)

from .product_files import load_product_file_info

APP_TITLE = "Informacje o plikach"


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1280, 860)
    root.minsize(980, 640)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Tk) -> None:
    state: dict[str, Any] = {
        "rows": [],
        "selected_row": None,
        "file_info": None,
        "sort_col": "artist",
        "sort_reverse": False,
    }

    # --- gora: lista produktow ---
    top = ttk.LabelFrame(host, text="Produkty (wybierz jeden)", padding=(10, 8))
    top.pack(fill="both", expand=True, padx=12, pady=(12, 6))

    filter_bar = ttk.Frame(top)
    filter_bar.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar(value="")
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=42).pack(side="left", padx=(6, 8))
    count_var = tk.StringVar(value="(ladowanie...)")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="Pobieram produkty z Shopify...")
    ttk.Label(filter_bar, textvariable=progress_var, foreground="#444").pack(side="right")

    table_frame = ttk.Frame(top)
    table_frame.pack(fill="both", expand=True)
    cols = ("artist", "painting_title", "handle", "image_filename")
    headings = {
        "artist": "Artysta",
        "painting_title": "Tytul obrazu",
        "handle": "Handle",
        "image_filename": "Plik glownej grafiki",
    }
    widths = {
        "artist": 200,
        "painting_title": 320,
        "handle": 160,
        "image_filename": 280,
    }
    sort_state: dict[str, bool] = {}

    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=9, selectmode="browse")

    def _update_sort_headings(*, active: str | None = None, reverse: bool = False) -> None:
        arrow_up = " \u25b2"
        arrow_down = " \u25bc"
        for c in cols:
            base = headings[c]
            if c == active:
                base += arrow_down if reverse else arrow_up
            if c == "artist":
                tree.heading(c, text=base, command=_make_sort_handler(c))
            else:
                tree.heading(c, text=base)

    def _make_sort_handler(col: str):
        def handler() -> None:
            reverse = sort_state.get(col, False)
            state["sort_col"] = col
            state["sort_reverse"] = reverse
            sort_state.clear()
            sort_state[col] = not reverse
            _update_sort_headings(active=col, reverse=reverse)
            _refresh_tree()

        return handler

    _update_sort_headings(active="artist", reverse=False)
    for c in cols:
        tree.column(c, width=widths[c], anchor="w", stretch=(c == "painting_title"))
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    filter_var.trace_add("write", lambda *_: _refresh_tree())

    # --- dol: szczegoly grafik ---
    bottom = ttk.LabelFrame(host, text="Grafiki w sklepie (galeria produktu)", padding=(10, 8))
    bottom.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    info_bar = ttk.Frame(bottom)
    info_bar.pack(fill="x", pady=(0, 6))
    summary_var = tk.StringVar(value="Wybierz produkt z listy powyzej.")
    ttk.Label(info_bar, textvariable=summary_var, wraplength=1100).pack(side="left", fill="x", expand=True)
    detail_progress_var = tk.StringVar(value="")
    ttk.Label(info_bar, textvariable=detail_progress_var, foreground="#444").pack(side="right")

    link_bar = ttk.Frame(bottom)
    link_bar.pack(fill="x", pady=(0, 6))
    ttk.Button(link_bar, text="Admin Shopify", command=lambda: _open_url("admin")).pack(side="left", padx=(0, 6))
    ttk.Button(link_bar, text="Strona produktu (PL)", command=lambda: _open_url("storefront")).pack(side="left")
    ttk.Button(link_bar, text="Odswiez", command=lambda: _reload_selected()).pack(side="right")

    img_frame = ttk.Frame(bottom)
    img_frame.pack(fill="both", expand=True)
    img_cols = (
        "position",
        "filename",
        "alt",
        "role",
        "gallery_visible",
        "featured",
        "dimensions",
        "variants",
    )
    img_headings = {
        "position": "Poz.",
        "filename": "Plik CDN",
        "alt": "Alt (nazwa na stronie)",
        "role": "Rola",
        "gallery_visible": "Galeria PDP",
        "featured": "Glowne",
        "dimensions": "Wymiary",
        "variants": "Warianty",
    }
    img_widths = {
        "position": 44,
        "filename": 260,
        "alt": 300,
        "role": 72,
        "gallery_visible": 88,
        "featured": 56,
        "dimensions": 88,
        "variants": 140,
    }
    img_tree = ttk.Treeview(img_frame, columns=img_cols, show="headings", height=8, selectmode="browse")
    for c in img_cols:
        img_tree.heading(c, text=img_headings[c])
        img_tree.column(c, width=img_widths[c], anchor="w", stretch=(c in ("filename", "alt")))
    img_vsb = ttk.Scrollbar(img_frame, orient="vertical", command=img_tree.yview)
    img_tree.configure(yscrollcommand=img_vsb.set)
    img_tree.grid(row=0, column=0, sticky="nsew")
    img_vsb.grid(row=0, column=1, sticky="ns")
    img_frame.rowconfigure(0, weight=1)
    img_frame.columnconfigure(0, weight=1)

    body_label = ttk.Label(bottom, text="Obrazy osadzone w opisie (body_html):", foreground="#444")
    body_label.pack(anchor="w", pady=(8, 2))
    body_var = tk.StringVar(value="—")
    ttk.Label(bottom, textvariable=body_var, wraplength=1100, justify="left").pack(anchor="w")

    img_row_by_iid: dict[str, dict[str, Any]] = {}

    def _filtered_rows() -> list[dict[str, Any]]:
        q = (filter_var.get() or "").strip().lower()
        rows = list(state["rows"])
        col = state["sort_col"]
        rev = state["sort_reverse"]
        if col == "painting_title":
            rows.sort(key=lambda r: (r.get("painting_title") or "").lower(), reverse=rev)
        elif col == "handle":
            rows.sort(key=lambda r: (r.get("handle") or "").lower(), reverse=rev)
        elif col == "image_filename":
            rows.sort(key=lambda r: (r.get("image_filename") or "").lower(), reverse=rev)
        else:
            rows.sort(key=product_catalog_sort_key, reverse=rev)
        if not q:
            return rows
        out: list[dict[str, Any]] = []
        for r in rows:
            blob = " ".join(
                str(r.get(k) or "")
                for k in ("artist", "painting_title", "handle", "image_filename", "product_title")
            ).lower()
            if q in blob:
                out.append(r)
        return out

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        visible = _filtered_rows()
        for row in visible:
            iid = str(row.get("product_id") or "")
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("artist", ""),
                    row.get("painting_title", ""),
                    row.get("handle", ""),
                    row.get("image_filename", ""),
                ),
            )
        total = len(state["rows"])
        count_var.set(f"{len(visible)}/{total} produktow")

    def _clear_image_panel(msg: str = "Wybierz produkt z listy powyzej.") -> None:
        img_tree.delete(*img_tree.get_children())
        img_row_by_iid.clear()
        state["file_info"] = None
        summary_var.set(msg)
        body_var.set("—")

    def _show_file_info(info: dict[str, Any]) -> None:
        state["file_info"] = info
        img_tree.delete(*img_tree.get_children())
        img_row_by_iid.clear()
        if not info.get("ok"):
            summary_var.set(info.get("error") or "Blad pobierania grafik.")
            body_var.set("—")
            return

        summary_var.set(
            f"{info.get('title', '')}  |  handle: {info.get('handle', '')}  |  "
            f"grafik w galerii: {info.get('image_count', 0)}  |  "
            f"glowne: {info.get('featured_filename') or '—'}"
        )

        for row in info.get("gallery_images") or []:
            w, h = row.get("width"), row.get("height")
            dims = f"{w}×{h}" if w and h else ""
            iid = str(row.get("image_id") or "")
            img_row_by_iid[iid] = row
            img_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("position", ""),
                    row.get("filename", ""),
                    row.get("alt", ""),
                    row.get("role", ""),
                    row.get("gallery_visible", ""),
                    row.get("featured", ""),
                    dims,
                    row.get("variant_labels", ""),
                ),
            )

        body_imgs = info.get("body_html_images") or []
        if body_imgs:
            parts = [f"{b.get('filename', '')} ({b.get('context', '')})" for b in body_imgs]
            body_var.set("\n".join(parts))
        else:
            body_var.set("Brak tagow <img> w opisie produktu.")

    def _load_products_bg() -> None:
        try:
            rows = load_product_catalog_rows(
                on_progress=lambda msg: host.after(0, lambda m=msg: progress_var.set(m)),
            )
            host.after(0, lambda: _on_products_loaded(rows))
        except Exception as exc:
            host.after(0, lambda: _on_products_error(str(exc)))

    def _on_products_loaded(rows: list[dict[str, Any]]) -> None:
        state["rows"] = rows
        progress_var.set("")
        _refresh_tree()
        if rows:
            count_var.set(f"{len(rows)}/{len(rows)} produktow")
        else:
            count_var.set("0 produktow")

    def _on_products_error(msg: str) -> None:
        progress_var.set("")
        count_var.set("blad")
        messagebox.showerror(APP_TITLE, f"Nie udalo sie pobrac produktow:\n{msg}", parent=host)

    def _load_details_bg(product_id: int) -> None:
        try:
            from Komponenty.dodajobraz import shopify_client as sc

            shop, token = sc.load_session()
            info = load_product_file_info(shop, token, product_id)
            host.after(0, lambda: _on_details_loaded(info))
        except Exception as exc:
            host.after(0, lambda: _on_details_error(str(exc)))

    def _on_details_loaded(info: dict[str, Any]) -> None:
        detail_progress_var.set("")
        _show_file_info(info)

    def _on_details_error(msg: str) -> None:
        detail_progress_var.set("")
        _clear_image_panel(f"Blad: {msg}")
        messagebox.showerror(APP_TITLE, f"Nie udalo sie pobrac grafik:\n{msg}", parent=host)

    def _on_product_select(_event: tk.Event | None = None) -> None:
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        row = next((r for r in state["rows"] if str(r.get("product_id")) == iid), None)
        state["selected_row"] = row
        if not row:
            return
        pid = int(row.get("product_id") or 0)
        if not pid:
            return
        detail_progress_var.set("Pobieram grafiki produktu...")
        threading.Thread(target=_load_details_bg, args=(pid,), daemon=True).start()

    def _reload_selected() -> None:
        row = state.get("selected_row")
        if not row:
            messagebox.showinfo(APP_TITLE, "Najpierw wybierz produkt z listy.", parent=host)
            return
        pid = int(row.get("product_id") or 0)
        if pid:
            detail_progress_var.set("Pobieram grafiki produktu...")
            threading.Thread(target=_load_details_bg, args=(pid,), daemon=True).start()

    def _open_url(kind: str) -> None:
        info = state.get("file_info") or {}
        row = state.get("selected_row") or {}
        if kind == "admin":
            url = info.get("admin_url") or row.get("admin_url") or ""
        else:
            url = info.get("storefront_url") or ""
        if not url:
            messagebox.showinfo(APP_TITLE, "Brak URL — wybierz produkt.", parent=host)
            return
        webbrowser.open(url)

    def _selected_image_row() -> dict[str, Any] | None:
        sel = img_tree.selection()
        if not sel:
            return None
        return img_row_by_iid.get(sel[0])

    def _copy_image_url() -> None:
        row = _selected_image_row()
        if not row:
            return
        src = (row.get("src") or "").strip()
        if not src:
            return
        host.clipboard_clear()
        host.clipboard_append(src)
        host.update()
        show_toast(host, "Skopiowano URL grafiki.")

    def _copy_image_alt() -> None:
        row = _selected_image_row()
        if not row:
            return
        alt = (row.get("alt") or "").strip()
        host.clipboard_clear()
        host.clipboard_append(alt)
        host.update()
        show_toast(host, "Skopiowano alt.")

    def _copy_image_bitmap() -> None:
        row = _selected_image_row()
        if not row:
            return
        src = (row.get("src") or "").strip()
        if not src:
            return
        try:
            copy_image_url_to_clipboard(host, src)
            show_toast(host, "Skopiowano miniaturke do schowka.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=host)

    def _open_image_url() -> None:
        row = _selected_image_row()
        if not row:
            return
        src = (row.get("src") or "").strip()
        if src:
            webbrowser.open(src)

    img_menu = tk.Menu(host, tearoff=0)
    img_menu.add_command(label="Otworz URL grafiki", command=_open_image_url)
    img_menu.add_command(label="Kopiuj URL", command=_copy_image_url)
    img_menu.add_command(label="Kopiuj alt", command=_copy_image_alt)
    img_menu.add_command(label="Kopiuj miniaturke", command=_copy_image_bitmap)

    def _img_context_menu(event: tk.Event) -> None:
        iid = img_tree.identify_row(event.y)
        if iid:
            img_tree.selection_set(iid)
            img_menu.tk_popup(event.x_root, event.y_root)

    tree.bind("<<TreeviewSelect>>", _on_product_select)
    img_tree.bind("<Button-3>", _img_context_menu)
    img_tree.bind("<Double-Button-1>", lambda _e: _open_image_url())

    threading.Thread(target=_load_products_bg, daemon=True).start()
