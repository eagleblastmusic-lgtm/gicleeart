"""GUI: Strona produktu — podział opisu na mini strony (PDP v3) + grafiki stron."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.dodajobraz.description_update import product_catalog_sort_key

from .service import (
    clear_story_config,
    load_catalog_with_story_status,
    load_effects_config,
    load_product_story,
    save_effects_config,
    save_story_config,
    upload_effects_image,
    upload_story_image,
)

APP_TITLE = "Strona produktu — mini strony opisu (PDP v3)"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
_DEFAULT_PARAGRAPHS_PER_PAGE = 2
_DETAILS_IID = "details"


def _is_image_path(path: Path) -> bool:
    return path.suffix.lower() in _IMAGE_SUFFIXES


def _default_pages(paragraph_count: int) -> list[dict[str, Any]]:
    """Domyślny podział: po 2 akapity na stronę (pokrywa wszystkie akapity)."""
    pages: list[dict[str, Any]] = []
    remaining = max(0, paragraph_count)
    while remaining > 0:
        take = min(_DEFAULT_PARAGRAPHS_PER_PAGE, remaining)
        pages.append({"paragraphs": take, "image": ""})
        remaining -= take
    if not pages:
        pages.append({"paragraphs": 1, "image": ""})
    return pages


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1360, 920)
    root.minsize(1060, 720)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Tk) -> None:
    state: dict[str, Any] = {
        "rows": [],
        "detail": None,
        "pages": [],
        "details_image": "",
        "sort_col": "artist",
        "sort_reverse": False,
    }

    # ------------------------------------------------------------------
    # Lista produktów
    # ------------------------------------------------------------------
    top = ttk.LabelFrame(host, text="Produkty (szablon PDP v3 — stronicowany opis)", padding=(10, 8))
    top.pack(fill="both", expand=True, padx=12, pady=(12, 6))

    filter_bar = ttk.Frame(top)
    filter_bar.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar(value="")
    only_missing_var = tk.BooleanVar(value=False)
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=36).pack(side="left", padx=(6, 8))
    ttk.Checkbutton(
        filter_bar,
        text="Tylko bez konfiguracji stron",
        variable=only_missing_var,
    ).pack(side="left", padx=(4, 12))
    count_var = tk.StringVar(value="(ładowanie...)")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="Pobieram produkty z Shopify...")
    ttk.Label(filter_bar, textvariable=progress_var, foreground="#444").pack(side="right")
    ttk.Button(
        filter_bar,
        text="Ustawienia efektów (PDP v3)...",
        command=lambda: _open_effects_settings(),
    ).pack(side="right", padx=(8, 12))

    table_frame = ttk.Frame(top)
    table_frame.pack(fill="both", expand=True)
    cols = ("artist", "painting_title", "handle", "story_status")
    headings = {
        "artist": "Artysta",
        "painting_title": "Tytuł obrazu",
        "handle": "Handle",
        "story_status": "Strony",
    }
    widths = {"artist": 200, "painting_title": 340, "handle": 170, "story_status": 90}
    sort_state: dict[str, bool] = {}

    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=9, selectmode="browse")

    def _update_sort_headings(*, active: str | None = None, reverse: bool = False) -> None:
        for c in cols:
            base = headings[c]
            if c == active:
                base += " \u25bc" if reverse else " \u25b2"
            tree.heading(c, text=base, command=_make_sort_handler(c))

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

    row_by_iid: dict[str, dict[str, Any]] = {}

    def _filtered_rows() -> list[dict[str, Any]]:
        q = (filter_var.get() or "").strip().lower()
        only_missing = bool(only_missing_var.get())
        rows = list(state["rows"])
        col = state["sort_col"]
        rev = state["sort_reverse"]
        if col == "painting_title":
            rows.sort(key=lambda r: (r.get("painting_title") or "").lower(), reverse=rev)
        elif col == "handle":
            rows.sort(key=lambda r: (r.get("handle") or "").lower(), reverse=rev)
        elif col == "story_status":
            rows.sort(key=lambda r: (0 if r.get("has_story") else 1, product_catalog_sort_key(r)), reverse=rev)
        else:
            rows.sort(key=product_catalog_sort_key, reverse=rev)
        out: list[dict[str, Any]] = []
        for r in rows:
            if only_missing and r.get("has_story"):
                continue
            if q:
                blob = " ".join(
                    str(r.get(k) or "")
                    for k in ("artist", "painting_title", "handle", "image_filename", "product_title")
                ).lower()
                if q not in blob:
                    continue
            out.append(r)
        return out

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        row_by_iid.clear()
        visible = _filtered_rows()
        for r in visible:
            iid = tree.insert(
                "",
                "end",
                values=(
                    r.get("artist") or "",
                    r.get("painting_title") or "",
                    r.get("handle") or "",
                    r.get("story_status") or "—",
                ),
            )
            row_by_iid[iid] = r
        count_var.set(f"{len(visible)} / {len(state['rows'])} produktów")

    filter_var.trace_add("write", lambda *_: _refresh_tree())
    only_missing_var.trace_add("write", lambda *_: _refresh_tree())

    # ------------------------------------------------------------------
    # Edytor stron
    # ------------------------------------------------------------------
    bottom = ttk.LabelFrame(host, text="Strony opisu (mini strony na PDP v3)", padding=(10, 8))
    bottom.pack(fill="both", expand=False, padx=12, pady=(0, 12))

    summary_var = tk.StringVar(
        value="Wybierz produkt z listy. Podziel akapity opisu na strony i przypisz grafiki."
    )
    ttk.Label(bottom, textvariable=summary_var, wraplength=1250).pack(anchor="w", pady=(0, 8))

    editor_row = ttk.Frame(bottom)
    editor_row.pack(fill="both", expand=True)

    # Lewa część: tabela stron + akcje
    pages_frame = ttk.Frame(editor_row)
    pages_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

    page_cols = ("page", "count", "range", "image")
    pages_tree = ttk.Treeview(
        pages_frame, columns=page_cols, show="headings", height=6, selectmode="browse"
    )
    pages_tree.heading("page", text="Strona")
    pages_tree.heading("count", text="Akapity")
    pages_tree.heading("range", text="Zakres akapitów")
    pages_tree.heading("image", text="Grafika")
    pages_tree.column("page", width=90, anchor="w", stretch=False)
    pages_tree.column("count", width=70, anchor="center", stretch=False)
    pages_tree.column("range", width=170, anchor="w", stretch=False)
    pages_tree.column("image", width=380, anchor="w", stretch=True)
    pages_tree.pack(fill="both", expand=True)

    pages_actions = ttk.Frame(pages_frame)
    pages_actions.pack(fill="x", pady=(8, 0))
    ttk.Button(pages_actions, text="Dodaj stronę", command=lambda: _add_page()).pack(side="left")
    ttk.Button(pages_actions, text="Usuń stronę", command=lambda: _remove_page()).pack(side="left", padx=(6, 0))
    ttk.Button(pages_actions, text="+ akapit", command=lambda: _bump_count(1)).pack(side="left", padx=(14, 0))
    ttk.Button(pages_actions, text="− akapit", command=lambda: _bump_count(-1)).pack(side="left", padx=(6, 0))
    ttk.Button(pages_actions, text="Wgraj grafikę strony...", command=lambda: _upload_image()).pack(
        side="left", padx=(14, 0)
    )
    ttk.Button(pages_actions, text="Usuń grafikę", command=lambda: _clear_image()).pack(side="left", padx=(6, 0))

    save_bar = ttk.Frame(pages_frame)
    save_bar.pack(fill="x", pady=(8, 0))
    ttk.Button(save_bar, text="Zapisz do Shopify", command=lambda: _save()).pack(side="left")
    ttk.Button(save_bar, text="Usuń konfigurację (auto-podział)", command=lambda: _clear_config()).pack(
        side="left", padx=(8, 0)
    )
    dirty_var = tk.StringVar(value="")
    ttk.Label(save_bar, textvariable=dirty_var, foreground="#c62828").pack(side="left", padx=(12, 0))
    ttk.Button(save_bar, text="Admin Shopify", command=lambda: _open_url("admin")).pack(side="right")
    ttk.Button(save_bar, text="Strona produktu (PL)", command=lambda: _open_url("store")).pack(
        side="right", padx=(0, 8)
    )
    detail_progress_var = tk.StringVar(value="")
    ttk.Label(save_bar, textvariable=detail_progress_var, foreground="#444").pack(side="right", padx=(0, 12))

    # Prawa część: podgląd tekstu wybranej strony
    preview_frame = ttk.LabelFrame(editor_row, text="Podgląd tekstu strony", padding=6)
    preview_frame.pack(side="left", fill="both", expand=True)
    preview_text = tk.Text(preview_frame, wrap="word", height=10, width=54, state="disabled")
    preview_text.pack(fill="both", expand=True)

    hint = ttk.Label(
        bottom,
        text=(
            "Metafield produktu: custom.story_pages (JSON). Ostatnia strona (SZCZEGÓŁY) jest dokładana "
            "automatycznie przez motyw — możesz przypisać jej osobną grafikę. Bez konfiguracji motyw "
            "dzieli akapity automatycznie, a grafiką jest zdjęcie główne produktu."
        ),
        foreground="#666",
        wraplength=1250,
        justify="left",
    )
    hint.pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------------
    # Logika edytora
    # ------------------------------------------------------------------

    def _paragraphs() -> list[str]:
        detail = state.get("detail") or {}
        return list(detail.get("paragraphs") or [])

    def _set_dirty(dirty: bool) -> None:
        state["dirty"] = dirty
        dirty_var.set("● Niezapisane zmiany — kliknij «Zapisz do Shopify»" if dirty else "")

    def _image_label(url: str) -> str:
        if not url:
            return "— (zdjęcie główne produktu)"
        return url.rsplit("/", 1)[-1].split("?")[0] or url

    def _page_ranges() -> list[tuple[int, int]]:
        """Zakres akapitów (1-based, włącznie) każdej strony."""
        out: list[tuple[int, int]] = []
        idx = 0
        total = len(_paragraphs())
        for page in state["pages"]:
            n = int(page.get("paragraphs") or 1)
            start = idx + 1
            end = min(idx + n, total)
            out.append((start, end))
            idx += n
        return out

    def _refresh_pages(*, keep_selection: bool = True) -> None:
        selected = pages_tree.selection()
        selected_iid = selected[0] if (keep_selection and selected) else None
        pages_tree.delete(*pages_tree.get_children())
        total = len(_paragraphs())
        ranges = _page_ranges()
        covered = 0
        for i, page in enumerate(state["pages"]):
            start, end = ranges[i]
            if end >= start:
                rng = f"{start}–{end} z {total}"
                covered = end
            else:
                rng = "poza zakresem!"
            pages_tree.insert(
                "",
                "end",
                iid=f"page-{i}",
                values=(f"{i + 1}", page.get("paragraphs") or 1, rng, _image_label(page.get("image") or "")),
            )
        pages_tree.insert(
            "",
            "end",
            iid=_DETAILS_IID,
            values=("SZCZEGÓŁY", "—", "panel szczegółów", _image_label(state.get("details_image") or "")),
        )
        if covered < total:
            summary_extra = f" · UWAGA: akapity {covered + 1}–{total} nieprzypisane (trafią na dodatkową stronę)."
        else:
            summary_extra = ""
        detail = state.get("detail") or {}
        if detail.get("ok"):
            summary_var.set(
                f"{detail.get('title') or ''} · akapitów: {total} · stron tekstu: {len(state['pages'])}"
                + summary_extra
            )
        if selected_iid and pages_tree.exists(selected_iid):
            pages_tree.selection_set(selected_iid)
        _refresh_preview()

    def _selected_page_index() -> int | None:
        """Indeks strony tekstu; None gdy brak wyboru lub wybrano wiersz SZCZEGÓŁY."""
        sel = pages_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if iid == _DETAILS_IID:
            return None
        try:
            return int(iid.split("-", 1)[1])
        except (IndexError, ValueError):
            return None

    def _refresh_preview() -> None:
        paras = _paragraphs()
        sel = pages_tree.selection()
        lines: list[str] = []
        if sel and sel[0] == _DETAILS_IID:
            lines = ["(Panel SZCZEGÓŁY — treść z opisu produktu, dokładana automatycznie przez motyw.)"]
        else:
            idx = _selected_page_index()
            if idx is not None and idx < len(state["pages"]):
                ranges = _page_ranges()
                start, end = ranges[idx]
                for p_no in range(start, end + 1):
                    if 1 <= p_no <= len(paras):
                        lines.append(f"[{p_no}] {paras[p_no - 1]}")
                if not lines:
                    lines = ["(Brak akapitów w zakresie tej strony.)"]
        preview_text.configure(state="normal")
        preview_text.delete("1.0", "end")
        preview_text.insert("1.0", "\n\n".join(lines))
        preview_text.configure(state="disabled")

    pages_tree.bind("<<TreeviewSelect>>", lambda *_: _refresh_preview())

    def _require_detail() -> dict[str, Any] | None:
        detail = state.get("detail")
        if not detail or not detail.get("ok"):
            messagebox.showinfo(APP_TITLE, "Najpierw wybierz produkt z listy.")
            return None
        return detail

    def _add_page() -> None:
        if not _require_detail():
            return
        state["pages"].append({"paragraphs": 1, "image": ""})
        _set_dirty(True)
        _refresh_pages()

    def _remove_page() -> None:
        if not _require_detail():
            return
        idx = _selected_page_index()
        if idx is None:
            messagebox.showinfo(APP_TITLE, "Wybierz stronę tekstu do usunięcia.")
            return
        if len(state["pages"]) <= 1:
            messagebox.showinfo(APP_TITLE, "Musi zostać przynajmniej jedna strona.")
            return
        state["pages"].pop(idx)
        _set_dirty(True)
        _refresh_pages(keep_selection=False)

    def _bump_count(delta: int) -> None:
        if not _require_detail():
            return
        idx = _selected_page_index()
        if idx is None:
            messagebox.showinfo(APP_TITLE, "Wybierz stronę tekstu.")
            return
        page = state["pages"][idx]
        page["paragraphs"] = max(1, int(page.get("paragraphs") or 1) + delta)
        _set_dirty(True)
        _refresh_pages()

    def _upload_image() -> None:
        detail = _require_detail()
        if not detail:
            return
        sel = pages_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Wybierz stronę (lub wiersz SZCZEGÓŁY).")
            return
        target_iid = sel[0]
        path_str = filedialog.askopenfilename(
            title="Grafika strony",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp"),
                ("Wszystkie", "*.*"),
            ],
        )
        if not path_str:
            return
        path = Path(path_str)
        if not _is_image_path(path):
            messagebox.showwarning(APP_TITLE, f"Nieobsługiwany format pliku:\n{path.name}")
            return
        if target_iid == _DETAILS_IID:
            label = "szczegóły"
        else:
            label = f"strona {int(target_iid.split('-', 1)[1]) + 1}"
        alt = f"{detail.get('title') or ''} ({label})".strip()
        detail_progress_var.set("Wgrywam grafikę...")

        def work() -> None:
            try:
                url = upload_story_image(path, alt=alt)
                err = None
            except Exception as exc:  # noqa: BLE001
                url, err = "", str(exc)

            def done() -> None:
                detail_progress_var.set("")
                if err:
                    messagebox.showerror(APP_TITLE, f"Błąd uploadu:\n{err}")
                    return
                if target_iid == _DETAILS_IID:
                    state["details_image"] = url
                else:
                    idx = int(target_iid.split("-", 1)[1])
                    if idx < len(state["pages"]):
                        state["pages"][idx]["image"] = url
                _set_dirty(True)
                show_toast(host, "Wgrano grafikę. Pamiętaj o «Zapisz do Shopify».", duration_ms=3000)
                _refresh_pages()

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _clear_image() -> None:
        if not _require_detail():
            return
        sel = pages_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Wybierz stronę (lub wiersz SZCZEGÓŁY).")
            return
        if sel[0] == _DETAILS_IID:
            state["details_image"] = ""
        else:
            idx = _selected_page_index()
            if idx is not None and idx < len(state["pages"]):
                state["pages"][idx]["image"] = ""
        _set_dirty(True)
        _refresh_pages()

    def _save() -> None:
        detail = _require_detail()
        if not detail:
            return
        pid = int(detail.get("product_id") or 0)
        config: dict[str, Any] = {"pages": [dict(p) for p in state["pages"]]}
        if state.get("details_image"):
            config["details_image"] = state["details_image"]
        detail_progress_var.set("Zapisuję...")

        def work() -> None:
            try:
                result = save_story_config(pid, config)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": str(exc)}

            def done() -> None:
                detail_progress_var.set("")
                if not result.get("ok"):
                    messagebox.showerror(APP_TITLE, result.get("error") or "Błąd zapisu.")
                    return
                _set_dirty(False)
                show_toast(host, "Zapisano konfigurację stron.", duration_ms=2500)
                _mark_selected_row(has_story=True, page_count=len(state["pages"]))

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _clear_config() -> None:
        detail = _require_detail()
        if not detail:
            return
        if not messagebox.askyesno(APP_TITLE, "Usunąć konfigurację stron? Motyw wróci do auto-podziału."):
            return
        pid = int(detail.get("product_id") or 0)
        detail_progress_var.set("Usuwam...")

        def work() -> None:
            try:
                result = clear_story_config(pid)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": str(exc)}

            def done() -> None:
                detail_progress_var.set("")
                if not result.get("ok"):
                    messagebox.showerror(APP_TITLE, result.get("error") or "Błąd.")
                    return
                _set_dirty(False)
                show_toast(host, "Usunięto konfigurację stron.", duration_ms=2500)
                _mark_selected_row(has_story=False, page_count=0)

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _mark_selected_row(*, has_story: bool, page_count: int) -> None:
        sel = tree.selection()
        if not sel:
            return
        row = row_by_iid.get(sel[0])
        if not row:
            return
        row["has_story"] = has_story
        row["story_status"] = f"{page_count} str." if has_story else "—"
        _refresh_tree()

    def _open_url(kind: str) -> None:
        detail = state.get("detail") or {}
        url = detail.get("admin_url") if kind == "admin" else detail.get("storefront_url")
        if url:
            webbrowser.open(url)

    # ------------------------------------------------------------------
    # Ustawienia efektów PDP v3 (metafield shop custom.pdp_v3_effects)
    # ------------------------------------------------------------------

    def _open_effects_settings() -> None:
        win = tk.Toplevel(host)
        win.title("Ustawienia efektów PDP v3 (cały sklep)")
        position_toplevel_screen_center(win, 700, 700)
        win.transient(host)
        win.grab_set()

        status_var = tk.StringVar(value="Wczytuję ustawienia z Shopify...")

        zoom_var = tk.BooleanVar(value=True)
        r2_blur_var = tk.BooleanVar(value=True)

        cbg_enabled_var = tk.BooleanVar(value=True)
        cbg_image_var = tk.StringVar(value="")
        cbg_parallax_var = tk.BooleanVar(value=True)
        cbg_blur_var = tk.BooleanVar(value=True)
        cbg_brightness_var = tk.IntVar(value=100)

        pt_enabled_var = tk.BooleanVar(value=True)
        pt_image_var = tk.StringVar(value="")
        pt_blur_var = tk.BooleanVar(value=False)
        pt_brightness_var = tk.IntVar(value=100)

        frm = ttk.Frame(win, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(
            frm,
            text="Ustawienia globalne dla wszystkich produktów na szablonie PDP v3.",
            foreground="#666",
            wraplength=650,
        ).pack(anchor="w", pady=(0, 10))

        fx_frame = ttk.LabelFrame(frm, text="Efekty scrolla i zoomu", padding=(10, 8))
        fx_frame.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(
            fx_frame,
            text="Immersive zoom R2 — przybliżenie chowa górne menu i powiększa obraz na cały ekran",
            variable=zoom_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            fx_frame,
            text="Rozmycie R2 podczas wjazdu sekcji opisu",
            variable=r2_blur_var,
        ).pack(anchor="w", pady=(4, 0))

        def _bg_image_label(url: str, empty_hint: str) -> str:
            if not url:
                return empty_hint
            return url.rsplit("/", 1)[-1].split("?")[0] or url

        def _build_bg_section(
            title: str,
            *,
            enabled_var: tk.BooleanVar,
            image_var: tk.StringVar,
            blur_var: tk.BooleanVar,
            brightness_var: tk.IntVar,
            parallax_var: tk.BooleanVar | None,
            empty_hint: str,
            alt: str,
        ) -> None:
            box = ttk.LabelFrame(frm, text=title, padding=(10, 8))
            box.pack(fill="x", pady=(0, 10))
            ttk.Checkbutton(box, text="Tło włączone", variable=enabled_var).pack(anchor="w")

            img_row = ttk.Frame(box)
            img_row.pack(fill="x", pady=(4, 0))
            img_label_var = tk.StringVar(value=empty_hint)

            def _sync_img_label(*_args: Any) -> None:
                img_label_var.set(_bg_image_label(image_var.get(), empty_hint))

            image_var.trace_add("write", _sync_img_label)
            ttk.Label(img_row, text="Grafika:").pack(side="left")
            ttk.Label(img_row, textvariable=img_label_var, foreground="#0a6").pack(
                side="left", padx=(6, 8)
            )

            def _do_upload() -> None:
                path_str = filedialog.askopenfilename(
                    parent=win,
                    title=title,
                    filetypes=[
                        ("Obrazy", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp"),
                        ("Wszystkie", "*.*"),
                    ],
                )
                if not path_str:
                    return
                path = Path(path_str)
                if not _is_image_path(path):
                    messagebox.showwarning(APP_TITLE, f"Nieobsługiwany format pliku:\n{path.name}", parent=win)
                    return
                status_var.set("Wgrywam grafikę...")

                def work() -> None:
                    try:
                        url = upload_effects_image(path, alt=alt)
                        err = None
                    except Exception as exc:  # noqa: BLE001
                        url, err = "", str(exc)

                    def done() -> None:
                        status_var.set("")
                        if err:
                            messagebox.showerror(APP_TITLE, f"Błąd uploadu:\n{err}", parent=win)
                            return
                        image_var.set(url)

                    host.after(0, done)

                threading.Thread(target=work, daemon=True).start()

            ttk.Button(img_row, text="Wgraj tło...", command=_do_upload).pack(side="right")
            ttk.Button(img_row, text="Usuń tło", command=lambda: image_var.set("")).pack(
                side="right", padx=(0, 6)
            )

            if parallax_var is not None:
                ttk.Checkbutton(box, text="Efekt parallax (ruch myszy)", variable=parallax_var).pack(
                    anchor="w", pady=(4, 0)
                )
            ttk.Checkbutton(box, text="Rozmycie tła", variable=blur_var).pack(anchor="w", pady=(4, 0))

            bright_row = ttk.Frame(box)
            bright_row.pack(fill="x", pady=(6, 0))
            ttk.Label(bright_row, text="Jasność tła:").pack(side="left")
            bright_label_var = tk.StringVar(value="100%")

            def _on_bright(value: str) -> None:
                v = int(float(value))
                brightness_var.set(v)
                bright_label_var.set(f"{v}%")

            scale = ttk.Scale(
                bright_row,
                from_=30,
                to=170,
                orient="horizontal",
                command=_on_bright,
            )
            scale.pack(side="left", fill="x", expand=True, padx=(8, 8))
            ttk.Label(bright_row, textvariable=bright_label_var, width=5).pack(side="left")

            def _sync_scale(*_args: Any) -> None:
                v = int(brightness_var.get() or 100)
                if int(float(scale.get())) != v:
                    scale.set(v)
                bright_label_var.set(f"{v}%")

            brightness_var.trace_add("write", _sync_scale)
            scale.set(int(brightness_var.get() or 100))

        _build_bg_section(
            "Tło sekcji konfiguratora (jak w karuzeli)",
            enabled_var=cbg_enabled_var,
            image_var=cbg_image_var,
            blur_var=cbg_blur_var,
            brightness_var=cbg_brightness_var,
            parallax_var=cbg_parallax_var,
            empty_hint="— (domyślnie: zdjęcie główne produktu)",
            alt="PDP v3 — tło konfiguratora",
        )
        _build_bg_section(
            "Tło «Jak powstaje Twój obraz» + «Na czym budujemy Twoje zaufanie» (jeden obraz)",
            enabled_var=pt_enabled_var,
            image_var=pt_image_var,
            blur_var=pt_blur_var,
            brightness_var=pt_brightness_var,
            parallax_var=None,
            empty_hint="— (brak — sekcje mają czarne tło)",
            alt="PDP v3 — tło proces + zaufanie",
        )

        bottom_bar = ttk.Frame(frm)
        bottom_bar.pack(fill="x", pady=(4, 0))
        ttk.Label(bottom_bar, textvariable=status_var, foreground="#444").pack(side="left")

        def _apply_effects(cfg: dict[str, Any]) -> None:
            zoom_var.set(bool(cfg.get("zoom_immersive", True)))
            r2_blur_var.set(bool(cfg.get("r2_blur", True)))
            cbg = cfg.get("config_bg") or {}
            cbg_enabled_var.set(bool(cbg.get("enabled", True)))
            cbg_image_var.set(str(cbg.get("image") or ""))
            cbg_parallax_var.set(bool(cbg.get("parallax", True)))
            cbg_blur_var.set(bool(cbg.get("blur", True)))
            cbg_brightness_var.set(int(cbg.get("brightness") or 100))
            pt = cfg.get("pt_bg") or {}
            pt_enabled_var.set(bool(pt.get("enabled", True)))
            pt_image_var.set(str(pt.get("image") or ""))
            pt_blur_var.set(bool(pt.get("blur", False)))
            pt_brightness_var.set(int(pt.get("brightness") or 100))

        def _save_effects() -> None:
            config = {
                "zoom_immersive": bool(zoom_var.get()),
                "r2_blur": bool(r2_blur_var.get()),
                "config_bg": {
                    "enabled": bool(cbg_enabled_var.get()),
                    "image": cbg_image_var.get().strip(),
                    "parallax": bool(cbg_parallax_var.get()),
                    "blur": bool(cbg_blur_var.get()),
                    "brightness": int(cbg_brightness_var.get() or 100),
                },
                "pt_bg": {
                    "enabled": bool(pt_enabled_var.get()),
                    "image": pt_image_var.get().strip(),
                    "blur": bool(pt_blur_var.get()),
                    "brightness": int(pt_brightness_var.get() or 100),
                },
            }
            status_var.set("Zapisuję do Shopify...")

            def work() -> None:
                try:
                    result = save_effects_config(config)
                except Exception as exc:  # noqa: BLE001
                    result = {"ok": False, "error": str(exc)}

                def done() -> None:
                    status_var.set("")
                    if not result.get("ok"):
                        messagebox.showerror(
                            APP_TITLE, result.get("error") or "Błąd zapisu.", parent=win
                        )
                        return
                    show_toast(host, "Zapisano ustawienia efektów PDP v3.", duration_ms=2500)
                    win.destroy()

                host.after(0, done)

            threading.Thread(target=work, daemon=True).start()

        ttk.Button(bottom_bar, text="Zapisz do Shopify", command=_save_effects).pack(side="right")
        ttk.Button(bottom_bar, text="Anuluj", command=win.destroy).pack(side="right", padx=(0, 8))

        def _load_effects() -> None:
            def work() -> None:
                try:
                    cfg = load_effects_config()
                    err = None
                except Exception as exc:  # noqa: BLE001
                    cfg, err = None, str(exc)

                def done() -> None:
                    if not win.winfo_exists():
                        return
                    status_var.set("")
                    if err:
                        messagebox.showerror(
                            APP_TITLE, f"Nie udało się wczytać ustawień:\n{err}", parent=win
                        )
                        return
                    if cfg:
                        _apply_effects(cfg)

                host.after(0, done)

            threading.Thread(target=work, daemon=True).start()

        _load_effects()

    # ------------------------------------------------------------------
    # Wybór produktu
    # ------------------------------------------------------------------

    def _apply_detail(detail: dict[str, Any]) -> None:
        state["detail"] = detail
        if not detail.get("ok"):
            summary_var.set(detail.get("error") or "Błąd.")
            state["pages"] = []
            state["details_image"] = ""
            _set_dirty(False)
            _refresh_pages(keep_selection=False)
            return
        config = detail.get("config")
        if config and config.get("pages"):
            state["pages"] = [dict(p) for p in config["pages"]]
            state["details_image"] = str(config.get("details_image") or "")
            _set_dirty(False)
        else:
            # Propozycja domyślna — jeszcze NIE zapisana w Shopify.
            state["pages"] = _default_pages(len(detail.get("paragraphs") or []))
            state["details_image"] = ""
            _set_dirty(True)
        _refresh_pages(keep_selection=False)

    def _reload_selected() -> None:
        sel = tree.selection()
        if not sel:
            return
        row = row_by_iid.get(sel[0])
        if not row:
            return
        pid = int(row.get("product_id") or 0)
        detail_progress_var.set("Ładowanie...")

        def work() -> None:
            try:
                detail = load_product_story(pid)
            except Exception as exc:  # noqa: BLE001
                detail = {"ok": False, "error": str(exc)}

            def done() -> None:
                detail_progress_var.set("")
                _apply_detail(detail)

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    tree.bind("<<TreeviewSelect>>", lambda *_: _reload_selected())

    def _load_catalog() -> None:
        progress_var.set("Pobieram produkty...")

        def work() -> None:
            try:
                rows = load_catalog_with_story_status(
                    on_progress=lambda m: host.after(0, lambda: progress_var.set(m)),
                )
                err = None
            except Exception as exc:  # noqa: BLE001
                rows = []
                err = str(exc)

            def done() -> None:
                progress_var.set("")
                if err:
                    messagebox.showerror(APP_TITLE, f"Nie udało się pobrać katalogu:\n{err}")
                    count_var.set("błąd")
                    return
                state["rows"] = rows
                _refresh_tree()
                show_toast(host, f"Załadowano {len(rows)} produktów.", duration_ms=2000)

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    _load_catalog()
