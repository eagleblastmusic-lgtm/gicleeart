"""Okno importu posta z pliku HTML (podglad AI / GicleeApp)."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import html_import, preview, publish

_LANG_LABELS = {
    "pl": "Polski",
    "en": "Angielski",
    "de": "Niemiecki",
    "fr": "Francuski",
    "es": "Hiszpanski",
    "nl": "Holenderski",
    "it": "Wloski",
}


def open_html_import(parent: tk.Misc) -> tk.Toplevel:
    """Otwiera dialog: wybierz plik HTML -> podglad -> wyslij na Shopify."""
    dlg = tk.Toplevel(parent)
    dlg.title("Blog - Import z pliku HTML")
    position_toplevel_screen_center(dlg, 900, 620)
    dlg.minsize(760, 520)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    state: dict[str, Any] = {
        "parsed": None,
        "file_path": "",
        "sending": False,
    }

    root = ttk.Frame(dlg, padding=(10, 8))
    root.pack(fill="both", expand=True)

    file_frame = ttk.LabelFrame(root, text="1. Plik HTML z podgladu (AI / Generator tresci)", padding=8)
    file_frame.pack(fill="x", pady=(0, 6))
    file_frame.columnconfigure(1, weight=1)

    file_var = tk.StringVar(value="")
    ttk.Label(file_frame, text="Plik:").grid(row=0, column=0, sticky="w", padx=(0, 6))
    file_entry = ttk.Entry(file_frame, textvariable=file_var, state="readonly")
    file_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))

    def _pick_and_load() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz plik HTML posta",
            filetypes=[("HTML", "*.html *.htm"), ("Wszystkie", "*.*")],
            parent=dlg,
        )
        if not path:
            return
        try:
            parsed = html_import.parse_preview_html_file(path)
        except ValueError as e:
            messagebox.showerror("Blad importu", str(e), parent=dlg)
            return
        state["parsed"] = parsed
        state["file_path"] = path
        file_var.set(path)
        _apply_parsed(parsed)
        show_toast(dlg, f"Wczytano: {Path(path).name}", duration_ms=1200)

    ttk.Button(file_frame, text="Wybierz plik...", command=_pick_and_load).grid(row=0, column=2)

    meta_frame = ttk.LabelFrame(root, text="2. Metadane publikacji", padding=8)
    meta_frame.pack(fill="x", pady=6)
    meta_frame.columnconfigure(1, weight=1)

    topic_label = ttk.Label(meta_frame, text="(wczytaj plik HTML)", foreground="#888")
    topic_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

    ttk.Label(meta_frame, text="Obrazek (URL lub plik):").grid(row=1, column=0, sticky="w", padx=(0, 6))
    image_var = tk.StringVar(value="")
    ttk.Entry(meta_frame, textvariable=image_var).grid(row=1, column=1, sticky="ew", pady=2)

    def _pick_image() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz obrazek",
            filetypes=[("Obrazki", "*.jpg *.jpeg *.png *.webp *.gif"), ("Wszystkie", "*.*")],
            parent=dlg,
        )
        if path:
            image_var.set(path)

    img_row = ttk.Frame(meta_frame)
    img_row.grid(row=1, column=2, padx=(6, 0))
    ttk.Button(img_row, text="...", width=3, command=_pick_image).pack(side="left")

    ttk.Label(meta_frame, text="Autor:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=2)
    author_var = tk.StringVar(value="GicleeArt")
    ttk.Entry(meta_frame, textvariable=author_var, width=24).grid(row=2, column=1, sticky="w", pady=2)

    lang_frame = ttk.LabelFrame(root, text="3. Jezyki do publikacji", padding=8)
    lang_frame.pack(fill="x", pady=6)

    lang_vars: dict[str, tk.BooleanVar] = {}
    langs_row = ttk.Frame(lang_frame)
    langs_row.pack(fill="x")
    for code, label in _LANG_LABELS.items():
        v = tk.BooleanVar(value=False)
        lang_vars[code] = v
        ttk.Checkbutton(langs_row, text=label, variable=v).pack(side="left", padx=(10, 0))

    action_row = ttk.Frame(root)
    action_row.pack(fill="x", pady=(8, 0))
    status_label = ttk.Label(action_row, text="", foreground="#888")
    status_label.pack(side="left")

    send_btn = ttk.Button(action_row, text="Wyslij na bloga", command=lambda: None)
    send_btn.pack(side="right")
    ttk.Button(action_row, text="Zamknij", command=dlg.destroy).pack(side="right", padx=(0, 6))
    ttk.Button(
        action_row, text="Podglad w przegladarce",
        command=lambda: _open_preview(dlg, state, status_label),
    ).pack(side="right", padx=(0, 6))

    def _apply_parsed(parsed: dict[str, Any]) -> None:
        langs = parsed.get("languages") or {}
        topic = parsed.get("topic") or ""
        pl_title = (langs.get("pl") or {}).get("title") or ""
        found = [code for code in lang_vars if code in langs and (langs.get(code) or {}).get("title")]
        topic_label.configure(
            text=f'Temat: "{topic or pl_title}" | jezyki w pliku: {", ".join(found) or "(brak)"}',
            foreground="#222",
        )
        for code, v in lang_vars.items():
            v.set(code in found)
        hint = str(parsed.get("image_hint") or "").strip()
        if hint.startswith("http://") or hint.startswith("https://"):
            image_var.set(hint)
        status_label.configure(
            text=f'Gotowe: PL "{pl_title[:50]}"',
            foreground="#1b5e20",
        )

    def _open_preview(dlg_: tk.Toplevel, st: dict[str, Any], lbl: ttk.Label) -> None:
        data = st.get("parsed")
        if not data:
            messagebox.showwarning("Brak danych", "Najpierw wczytaj plik HTML.", parent=dlg_)
            return
        try:
            path = preview.open_preview_in_browser(data)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Blad podgladu", str(e), parent=dlg_)
            return
        show_toast(dlg_, f"Otwarto: {path.name}", duration_ms=1200)

    def _send() -> None:
        if state.get("sending"):
            return
        data = state.get("parsed")
        if not data:
            messagebox.showwarning("Brak danych", "Najpierw wczytaj plik HTML.", parent=dlg)
            return

        langs = data.get("languages") or {}
        pl = langs.get("pl") or {}
        selected_locales = [
            code for code, v in lang_vars.items()
            if code != "pl" and v.get() and code in langs
        ]

        if not messagebox.askyesno(
            "Wyslac post?",
            f"Zostanie opublikowany post:\n\n"
            f"PL: {pl.get('title')}\n"
            f"Tlumaczenia: {', '.join(selected_locales) if selected_locales else '(tylko PL)'}\n\n"
            f"Plik: {Path(state.get('file_path') or '').name or '(?)'}\n\n"
            f"Kontynuowac?",
            parent=dlg,
        ):
            return

        state["sending"] = True
        send_btn.configure(state="disabled", text="Wysylam...")
        status_label.configure(text="Wysylam na Shopify...", foreground="#555")

        image_url = image_var.get().strip()
        author = author_var.get().strip() or "GicleeArt"

        def _worker() -> None:
            try:
                result = publish.publish_parsed_article(
                    data,
                    image_url=image_url,
                    author=author,
                    selected_locales=selected_locales,
                )
                article_id = result["article_id"]
                article = result["article"]
                translation_errors = result["translation_errors"]
                admin_url = result["admin_url"]
                summary = (
                    f"Post opublikowany!\n\n"
                    f"ID: {article_id}\nTytul: {article.get('title')}\n"
                    f"Tlumaczenia: {len(selected_locales) - len(translation_errors)}/{len(selected_locales)}\n\n"
                    f"Admin: {admin_url}"
                )
                if translation_errors:
                    summary += "\n\nBledy tlumaczen:\n" + "\n".join(translation_errors)

                def _ok() -> None:
                    status_label.configure(text=f"ID {article_id} - opublikowano", foreground="#1b5e20")
                    messagebox.showinfo("Sukces", summary, parent=dlg)

                dlg.after(0, _ok)
            except Exception as e:  # noqa: BLE001
                err = str(e)

                def _err() -> None:
                    status_label.configure(text=err[:80], foreground="#c62828")
                    messagebox.showerror("Blad wysylki", err, parent=dlg)

                dlg.after(0, _err)
            finally:
                def _reset() -> None:
                    state["sending"] = False
                    send_btn.configure(state="normal", text="Wyslij na bloga")

                dlg.after(0, _reset)

        threading.Thread(target=_worker, daemon=True).start()

    send_btn.configure(command=_send)
    dlg.bind("<Escape>", lambda _e: dlg.destroy())

    return dlg
