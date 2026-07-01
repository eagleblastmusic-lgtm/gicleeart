"""GUI: Przed/Po — lista produktów + upload grafiki «przed obróbką»."""

from __future__ import annotations

import io
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any
from urllib.request import urlopen

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.dodajobraz.description_update import product_catalog_sort_key
from PIL import Image, ImageTk

from .service import (
    clear_before_image,
    load_catalog_with_before_status,
    load_product_before_after,
    upload_before_image,
)

APP_TITLE = "Przed/Po — porównanie obróbki"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
_BEFORE_DROP_BG = "#1a1a1a"
_BEFORE_DROP_BG_ACTIVE = "#2a2848"


def _is_image_path(path: Path) -> bool:
    return path.suffix.lower() in _IMAGE_SUFFIXES


def _parse_dnd_files(data: str) -> list[Path]:
    out: list[Path] = []
    buf = ""
    in_brace = False
    for ch in data:
        if ch == "{":
            in_brace = True
            buf = ""
        elif ch == "}":
            in_brace = False
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        elif ch == " " and not in_brace:
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(Path(buf.strip()))
    return out


def main() -> None:
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1320, 880)
    root.minsize(1020, 680)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Tk) -> None:
    state: dict[str, Any] = {
        "rows": [],
        "selected_row": None,
        "detail": None,
        "sort_col": "artist",
        "sort_reverse": False,
        "_thumb_refs": [],
    }

    top = ttk.LabelFrame(host, text="Produkty (szablon PDP v2 — porównanie przed/po)", padding=(10, 8))
    top.pack(fill="both", expand=True, padx=12, pady=(12, 6))

    filter_bar = ttk.Frame(top)
    filter_bar.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar(value="")
    only_missing_var = tk.BooleanVar(value=False)
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=36).pack(side="left", padx=(6, 8))
    ttk.Checkbutton(
        filter_bar,
        text="Tylko bez grafiki «przed»",
        variable=only_missing_var,
    ).pack(side="left", padx=(4, 12))
    count_var = tk.StringVar(value="(ładowanie...)")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="Pobieram produkty z Shopify...")
    ttk.Label(filter_bar, textvariable=progress_var, foreground="#444").pack(side="right")

    table_frame = ttk.Frame(top)
    table_frame.pack(fill="both", expand=True)
    cols = ("artist", "painting_title", "handle", "before_status", "after_hint")
    headings = {
        "artist": "Artysta",
        "painting_title": "Tytuł obrazu",
        "handle": "Handle",
        "before_status": "Przed",
        "after_hint": "Po (Full)",
    }
    widths = {
        "artist": 190,
        "painting_title": 300,
        "handle": 150,
        "before_status": 72,
        "after_hint": 220,
    }
    sort_state: dict[str, bool] = {}

    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10, selectmode="browse")

    def _update_sort_headings(*, active: str | None = None, reverse: bool = False) -> None:
        arrow_up = " \u25b2"
        arrow_down = " \u25bc"
        for c in cols:
            base = headings[c]
            if c == active:
                base += arrow_down if reverse else arrow_up
            cmd = _make_sort_handler(c) if c in ("artist", "painting_title", "handle", "before_status") else ""
            tree.heading(c, text=base, command=cmd)

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
        elif col == "before_status":
            rows.sort(key=lambda r: (0 if r.get("has_before") else 1, product_catalog_sort_key(r)), reverse=rev)
        else:
            rows.sort(key=product_catalog_sort_key, reverse=rev)
        out: list[dict[str, Any]] = []
        for r in rows:
            if only_missing and r.get("has_before"):
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
                    r.get("before_status") or "—",
                    "Full w galerii (po wyborze)",
                ),
            )
            row_by_iid[iid] = r
        count_var.set(f"{len(visible)} / {len(state['rows'])} produktów")

    filter_var.trace_add("write", lambda *_: _refresh_tree())
    only_missing_var.trace_add("write", lambda *_: _refresh_tree())

    bottom = ttk.LabelFrame(host, text="Grafiki porównania", padding=(10, 8))
    bottom.pack(fill="both", expand=False, padx=12, pady=(0, 12))

    summary_var = tk.StringVar(value="Wybierz produkt z listy. «Po obróbce» = obraz Full z galerii (już w sklepie).")
    ttk.Label(bottom, textvariable=summary_var, wraplength=1200).pack(anchor="w", pady=(0, 8))

    action_bar = ttk.Frame(bottom)
    action_bar.pack(fill="x", pady=(0, 8))
    ttk.Button(action_bar, text="Wgraj grafikę «przed»...", command=lambda: _upload_before()).pack(side="left")
    ttk.Button(action_bar, text="Usuń grafikę «przed»", command=lambda: _clear_before()).pack(side="left", padx=(8, 0))
    ttk.Button(action_bar, text="Odśwież", command=lambda: _reload_selected()).pack(side="left", padx=(8, 0))
    ttk.Button(action_bar, text="Admin Shopify", command=lambda: _open_url("admin")).pack(side="right")
    ttk.Button(action_bar, text="Strona produktu (PL)", command=lambda: _open_url("store")).pack(side="right", padx=(0, 8))
    detail_progress_var = tk.StringVar(value="")
    ttk.Label(action_bar, textvariable=detail_progress_var, foreground="#444").pack(side="right", padx=(0, 12))

    preview_row = ttk.Frame(bottom)
    preview_row.pack(fill="x")

    before_frame = ttk.LabelFrame(preview_row, text="Przed obróbką (przeciągnij plik tutaj)", padding=8)
    before_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
    before_drop_hint = (
        "Przeciągnij obraz tutaj\n(lub użyj przycisku «Wgraj»)\n\n"
        if _HAS_DND
        else "Brak grafiki «przed»\n\n"
    )
    before_canvas = tk.Label(
        before_frame,
        text=before_drop_hint + "—",
        anchor="center",
        background=_BEFORE_DROP_BG,
        foreground="#ccc",
        font=("Segoe UI", 10),
    )
    before_canvas.pack(fill="both", expand=True, ipadx=120, ipady=80)

    after_frame = ttk.LabelFrame(preview_row, text="Po obróbce (obraz Full z galerii)", padding=8)
    after_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))
    after_canvas = tk.Label(after_frame, text="—", anchor="center", background="#1a1a1a", foreground="#ccc")
    after_canvas.pack(fill="both", expand=True, ipadx=120, ipady=80)

    hint = ttk.Label(
        bottom,
        text=(
            "Metafield produktu: custom.before_retouch_url. "
            "Sekcja «Porównanie przed/po» na szablonie szablon-produktu-v2 pojawi się, "
            "gdy jest grafika «przed» i obraz Full w galerii."
            + ("" if _HAS_DND else " (Drag-and-drop: pip install tkinterdnd2)")
        ),
        foreground="#666",
        wraplength=1200,
        justify="left",
    )
    hint.pack(anchor="w", pady=(8, 0))

    def _before_drop_placeholder(*, has_image: bool = False) -> str:
        if has_image:
            return ""
        if _HAS_DND:
            return "Przeciągnij obraz tutaj\n(lub użyj przycisku «Wgraj»)\n\nBrak grafiki «przed»"
        return "Brak grafiki «przed»"

    def _selected_row() -> dict[str, Any] | None:
        sel = tree.selection()
        if not sel:
            return None
        return row_by_iid.get(sel[0])

    def _open_url(kind: str) -> None:
        detail = state.get("detail") or {}
        url = detail.get("admin_url") if kind == "admin" else detail.get("storefront_url")
        if url:
            webbrowser.open(url)

    def _set_preview(label: tk.Label, url: str | None, *, placeholder: str, is_before: bool = False) -> None:
        if label is before_canvas:
            state["_thumb_refs"].clear()
        if not url:
            text = placeholder
            if is_before and not url:
                text = _before_drop_placeholder(has_image=False) if placeholder == "Brak grafiki «przed»" else placeholder
            label.configure(image="", text=text)
            return
        try:
            with urlopen(url, timeout=30) as resp:
                raw = resp.read()
            img = Image.open(io.BytesIO(raw))
            img.thumbnail((420, 320), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            state["_thumb_refs"].append(photo)
            label.configure(image=photo, text="")
        except OSError as exc:
            label.configure(image="", text=f"Podgląd niedostępny\n{exc}")

    def _apply_detail(detail: dict[str, Any]) -> None:
        state["detail"] = detail
        if not detail.get("ok"):
            summary_var.set(detail.get("error") or "Błąd.")
            _set_preview(before_canvas, None, placeholder="—")
            _set_preview(after_canvas, None, placeholder="—")
            return
        title = detail.get("title") or ""
        parts = [title]
        if detail.get("has_before"):
            parts.append("«przed»: tak")
        else:
            parts.append("«przed»: brak")
        after = detail.get("after") or {}
        if detail.get("has_after"):
            parts.append(f"«po» (Full): {after.get('filename') or 'tak'}")
        else:
            parts.append("«po» (Full): brak — dodaj obraz Full w galerii")
        summary_var.set(" · ".join(parts))
        _set_preview(before_canvas, detail.get("before_url"), placeholder="Brak grafiki «przed»", is_before=True)
        _set_preview(after_canvas, (after or {}).get("src"), placeholder="Brak obrazu Full")

    def _reload_selected(*, refresh_list: bool = False) -> None:
        row = _selected_row()
        if not row:
            messagebox.showinfo(APP_TITLE, "Wybierz produkt z listy.")
            return
        pid = int(row.get("product_id") or 0)
        detail_progress_var.set("Ładowanie...")

        def work() -> None:
            try:
                detail = load_product_before_after(pid)
            except Exception as exc:  # noqa: BLE001
                detail = {"ok": False, "error": str(exc)}

            def done() -> None:
                detail_progress_var.set("")
                _apply_detail(detail)
                if refresh_list and detail.get("ok"):
                    row["has_before"] = bool(detail.get("has_before"))
                    row["before_url"] = detail.get("before_url") or ""
                    row["before_status"] = "tak" if row["has_before"] else "—"
                    _refresh_tree()

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _upload_before_from_path(path: Path) -> None:
        row = _selected_row()
        if not row:
            messagebox.showinfo(APP_TITLE, "Najpierw wybierz produkt z listy, potem upuść plik.")
            return
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, f"Plik nie istnieje:\n{path}")
            return
        if not _is_image_path(path):
            messagebox.showwarning(
                APP_TITLE,
                f"Nieobsługiwany format pliku:\n{path.name}\n\n"
                f"Dozwolone: {', '.join(sorted(_IMAGE_SUFFIXES))}",
            )
            return
        pid = int(row.get("product_id") or 0)
        alt = f"{row.get('artist') or ''} - {row.get('painting_title') or ''} (przed obróbką)".strip(" -")
        detail_progress_var.set("Wgrywam...")

        def work() -> None:
            try:
                result = upload_before_image(pid, path, alt=alt)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": str(exc)}

            def done() -> None:
                detail_progress_var.set("")
                if not result.get("ok"):
                    messagebox.showerror(APP_TITLE, result.get("error") or "Błąd uploadu.")
                    return
                show_toast(host, "Zapisano grafikę «przed».", duration_ms=2500)
                _reload_selected(refresh_list=True)

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _upload_before() -> None:
        row = _selected_row()
        if not row:
            messagebox.showinfo(APP_TITLE, "Wybierz produkt z listy.")
            return
        path = filedialog.askopenfilename(
            title="Grafika «przed obróbką»",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp"),
                ("Wszystkie", "*.*"),
            ],
        )
        if not path:
            return
        _upload_before_from_path(Path(path))

    def _on_before_drop(event: tk.Event) -> None:  # type: ignore[type-arg]
        data = getattr(event, "data", "") or ""
        paths = _parse_dnd_files(data)
        images = [p for p in paths if p.is_file() and _is_image_path(p)]
        if not images:
            messagebox.showwarning(APP_TITLE, "Upuść plik graficzny (JPG, PNG, WebP, TIFF…).")
            return
        if len(images) > 1:
            show_toast(host, f"Wgrywam pierwszy z {len(images)} plików.", duration_ms=2000)
        _upload_before_from_path(images[0])

    def _on_before_drag_enter(_event: tk.Event) -> None:  # type: ignore[type-arg]
        if _selected_row():
            before_canvas.configure(background=_BEFORE_DROP_BG_ACTIVE, cursor="hand2")
        else:
            before_canvas.configure(background="#3a2a2a", cursor="no")

    def _on_before_drag_leave(_event: tk.Event) -> None:  # type: ignore[type-arg]
        before_canvas.configure(background=_BEFORE_DROP_BG, cursor="")

    if _HAS_DND:
        before_canvas.drop_target_register(DND_FILES)
        before_canvas.dnd_bind("<<Drop>>", _on_before_drop)
        before_canvas.dnd_bind("<<DragEnter>>", _on_before_drag_enter)
        before_canvas.dnd_bind("<<DragLeave>>", _on_before_drag_leave)

    def _clear_before() -> None:
        row = _selected_row()
        if not row:
            messagebox.showinfo(APP_TITLE, "Wybierz produkt z listy.")
            return
        if not messagebox.askyesno(APP_TITLE, "Usunąć grafikę «przed» dla tego produktu?"):
            return
        pid = int(row.get("product_id") or 0)
        detail_progress_var.set("Usuwam...")

        def work() -> None:
            try:
                result = clear_before_image(pid)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": str(exc)}

            def done() -> None:
                detail_progress_var.set("")
                if not result.get("ok"):
                    messagebox.showerror(APP_TITLE, result.get("error") or "Błąd.")
                    return
                show_toast(host, "Usunięto grafikę «przed».", duration_ms=2500)
                _reload_selected(refresh_list=True)

            host.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _on_select(_evt: object) -> None:
        _reload_selected()

    tree.bind("<<TreeviewSelect>>", _on_select)

    def _load_catalog() -> None:
        progress_var.set("Pobieram produkty...")

        def work() -> None:
            try:
                rows = load_catalog_with_before_status(
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
