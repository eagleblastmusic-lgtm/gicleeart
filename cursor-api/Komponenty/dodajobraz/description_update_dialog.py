"""Okno «Aktualizuj opis» — podmiana akapitow z tablicy JSON LLM."""

from __future__ import annotations

import re
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, scrolledtext, ttk
from typing import Any, Callable

from Komponenty._shared.clipboard_image import copy_image_url_to_clipboard
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import shopify_client as sc
from .description_update import (
    DESCRIPTION_RESUME_FLAG_LABEL,
    DESCRIPTION_UPDATED_LABEL,
    CHECKMARK_TREE_LABEL,
    RESUME_FLAG_TREE_LABEL,
    count_unmarked_products_with_compare_versions,
    format_compare_versions_unmarked_note,
    format_description_pl_pending_progress,
    format_description_update_progress,
    format_do_tlumaczenia_progress,
    LOCALE_LABELS,
    UpdateMode,
    apply_current_paragraphs_batch,
    apply_current_paragraphs_update,
    apply_description_update,
    build_translation_prompt,
    build_translation_prompt_all,
    build_giga_translation_prompt,
    build_locales_from_translation_batch,
    build_current_translations_json,
    load_all_locale_paragraphs,
    compute_locale_preview,
    compare_default_version_for_provider,
    compare_llm_provider_index,
    compare_provider_from_index,
    COMPARE_LLM_LABELS,
    get_translated_fields,
    load_current_paragraphs,
    load_compare_versions,
    load_description_auto_copy_prompt,
    load_description_compare_llm,
    load_description_do_tlumaczenia_marks,
    load_description_bez_16_marks,
    load_description_gpt_translation_marks,
    load_description_from_image_marks,
    load_description_pl_pending_marks,
    load_description_resume_flag,
    load_description_sonnet_translation_marks,
    load_description_update_marks,
    load_product_catalog_rows,
    product_catalog_sort_key,
    product_has_filled_compare_versions,
    save_compare_versions,
    save_description_auto_copy_prompt,
    save_description_compare_llm,
    set_description_gpt_translation_marks_batch,
    set_description_from_image_marks_batch,
    set_description_do_tlumaczenia_marks_batch,
    set_description_bez_16_marks_batch,
    set_description_sonnet_translation_marks_batch,
    match_json_entry_for_product,
    parse_paragraph_translations_batch,
    parse_paragraph_translations_json,
    parse_giga_translations_json,
    toggle_description_resume_flag,
    toggle_description_update_mark,
    update_description_marks_after_save,
)
from .html_template import (
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
)
from .parser import parse_filename
from .description_compare_dialog import open_description_compare_dialog
from .prompt_builder import (
    TRANSLATION_LANGS,
    build_image_description_prompt,
    build_image_description_prompt_v2,
    build_new_description_prompt,
    parse_batch_response_json,
)

APP_TITLE = "Dodaj obraz"

_LOCALES = ("pl", "en", "de", "fr", "es", "nl", "it")
_LOADING_TEXT = "Ladowanie..."


def _open_gemini_image_prompt_helper(
    parent: tk.Misc,
    *,
    prompt: str,
    image_url: str,
    variant_label: str,
) -> None:
    """Gemini przy Ctrl+V bierze tylko obraz, gdy w schowku jest tekst+bitmapa — krok po kroku."""
    win = tk.Toplevel(parent)
    win.title(f"{variant_label} → Gemini")
    win.transient(parent)
    position_toplevel_screen_center(win, 520, 340)
    win.minsize(440, 280)

    frame = ttk.Frame(win, padding=12)
    frame.pack(fill="both", expand=True)

    ttk.Label(
        frame,
        text=variant_label,
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        frame,
        text=(
            "Gemini nie wkleja tekstu i obrazu jednym Ctrl+V (bierze tylko grafike).\n\n"
            "1. Grafika bedzie w schowku — wklej ja w pole czatu Gemini (Ctrl+V lub ikona +).\n"
            "2. Kliknij «Kopiuj prompt», potem wklej tekst w Gemini (Ctrl+V)."
        ),
        wraplength=480,
        justify="left",
        foreground="#444",
    ).pack(anchor="w", pady=(8, 10))

    preview = scrolledtext.ScrolledText(frame, height=6, wrap="word", font=("Segoe UI", 9))
    preview.pack(fill="both", expand=True)
    preview.insert("1.0", prompt)
    preview.configure(state="disabled")

    status_var = tk.StringVar(value="Pobieram grafike...")
    ttk.Label(frame, textvariable=status_var, foreground="#0a6", wraplength=480).pack(
        anchor="w", pady=(8, 0),
    )

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x", pady=(10, 0))

    def _copy_prompt() -> None:
        try:
            win.clipboard_clear()
            win.clipboard_append(prompt)
            win.update()
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=win)
            return
        status_var.set("Prompt w schowku — wklej w Gemini (Ctrl+V).")
        show_toast(win, "Prompt w schowku", duration_ms=1200)

    def _copy_image(*, auto: bool = False) -> None:
        status_var.set("Pobieram grafike...")
        copy_img_btn.configure(state="disabled")

        def work() -> None:
            try:
                copy_image_url_to_clipboard(image_url)
            except Exception as exc:
                win.after(
                    0,
                    lambda e=exc: (
                        status_var.set(str(e)),
                        copy_img_btn.configure(state="normal"),
                        messagebox.showerror(APP_TITLE, str(e), parent=win),
                    ),
                )
                return

            def done() -> None:
                status_var.set("Grafika w schowku — wklej w Gemini (Ctrl+V).")
                copy_img_btn.configure(state="normal")
                if not auto:
                    show_toast(win, "Grafika w schowku", duration_ms=1400)

            win.after(0, done)

        threading.Thread(target=work, daemon=True, name="gemini-helper-copy-image").start()

    copy_prompt_btn = ttk.Button(btn_row, text="Kopiuj prompt (krok 2)", command=_copy_prompt)
    copy_prompt_btn.pack(side="left")
    copy_img_btn = ttk.Button(btn_row, text="Kopiuj grafike ponownie", command=_copy_image)
    copy_img_btn.pack(side="left", padx=(8, 0))
    ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right")

    win.bind("<Escape>", lambda _e: win.destroy())
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.after(100, lambda: _copy_image(auto=True))


def open_description_update_dialog(
    parent: tk.Misc,
    *,
    enqueue_log: Callable[[str], None],
    set_status: Callable[[str], None],
    standalone: bool = False,
) -> tk.Misc:
    if standalone and isinstance(parent, tk.Tk):
        dlg = parent
    else:
        dlg = tk.Toplevel(parent)
        dlg.transient(parent)
    dlg.title("Aktualizuj opis")
    position_toplevel_screen_center(dlg, 1320, 820)
    dlg.minsize(960, 620)

    state: dict[str, Any] = {
        "rows": [],
        "row_by_iid": {},
        "selected_product": None,
        "full_product": None,
        "llm_item": None,
        "llm_items": [],
        "previews": {},
        "edited_paragraphs": {},
        "baseline_paragraphs": {},
        "draft_old_paragraphs": {},
        "locale": "pl",
        "edit_paragraph_idx": 0,
        "mode": tk.StringVar(value="replace_all"),
        "paragraph_index": tk.IntVar(value=1),
        "compare_versions": load_compare_versions(),
        "compare_open_pid": None,
        "updated_marks": load_description_update_marks(),
        "pl_pending_marks": load_description_pl_pending_marks(),
        "gpt_marks": load_description_gpt_translation_marks(),
        "sonnet_marks": load_description_sonnet_translation_marks(),
        "from_image_marks": load_description_from_image_marks(),
        "do_tlum_marks": load_description_do_tlumaczenia_marks(),
        "bez_16_marks": load_description_bez_16_marks(),
        "resume_flag_pid": load_description_resume_flag(),
        "sort_col": "artist",
        "sort_reverse": False,
    }

    # --- gora: lista produktow ---
    top = ttk.LabelFrame(
        dlg,
        text="Produkty (Ctrl+klik lub Shift+klik — wiele zaznaczen)",
        padding=(10, 8),
    )
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

    filter_active: set[str] = set()
    filter_btns_frame = ttk.Frame(top)
    filter_btns_frame.pack(fill="x", pady=(0, 4))
    ttk.Label(filter_btns_frame, text="Pokaz:").pack(side="left")
    filter_btns: dict[str, ttk.Button] = {}

    mark_btn = ttk.Button(
        filter_bar,
        text="Oznacz: opis po aktualizacji",
        command=lambda: _toggle_updated_mark(),
        state="disabled",
    )
    mark_btn.pack(side="right", padx=(8, 0))
    do_tlum_mark_btn = ttk.Button(
        filter_bar,
        text="do tlum.",
        command=lambda: _toggle_do_tlum_mark_btn(),
        state="disabled",
    )
    do_tlum_mark_btn.pack(side="right", padx=(8, 0))
    sonn_mark_btn = ttk.Button(
        filter_bar,
        text="tlum. SONN",
        command=lambda: _toggle_sonnet_mark_btn(),
        state="disabled",
    )
    sonn_mark_btn.pack(side="right", padx=(8, 0))
    gpt_mark_btn = ttk.Button(
        filter_bar,
        text="tlum. GPT",
        command=lambda: _toggle_gpt_mark_btn(),
        state="disabled",
    )
    gpt_mark_btn.pack(side="right", padx=(8, 0))
    from_image_mark_btn = ttk.Button(
        filter_bar,
        text="z obrazu",
        command=lambda: _toggle_from_image_mark_btn(),
        state="disabled",
    )
    from_image_mark_btn.pack(side="right", padx=(8, 0))
    bez_16_mark_btn = ttk.Button(
        filter_bar,
        text="Bez 1-6",
        command=lambda: _toggle_bez_16_mark_btn(),
        state="disabled",
    )
    bez_16_mark_btn.pack(side="right", padx=(8, 0))
    flag_btn = ttk.Button(
        filter_bar,
        text="Ustaw flage: tu skonczylem",
        command=lambda: _toggle_resume_flag(),
        state="disabled",
    )
    flag_btn.pack(side="right", padx=(8, 0))

    table_frame = ttk.Frame(top)
    table_frame.pack(fill="both", expand=True)
    cols = (
        "flag",
        "desc_status",
        "compare_status",
        "do_tlum",
        "tlum_gpt",
        "tlum_sonn",
        "z_obrazu",
        "bez_16",
        "artist",
        "painting_title",
        "handle",
        "image_filename",
    )
    headings = {
        "flag": "Flaga",
        "desc_status": "Akt.",
        "compare_status": "Wers.",
        "do_tlum": "Do tlum.",
        "tlum_gpt": "tlum. GPT",
        "tlum_sonn": "tlum. SONN",
        "z_obrazu": "z obrazu",
        "bez_16": "Bez 1-6",
        "artist": "Artysta",
        "painting_title": "Tytul obrazu",
        "handle": "Handle",
        "image_filename": "Plik glownej grafiki",
    }
    widths = {
        "flag": 44,
        "desc_status": 40,
        "compare_status": 40,
        "do_tlum": 40,
        "tlum_gpt": 72,
        "tlum_sonn": 76,
        "z_obrazu": 64,
        "bez_16": 56,
        "artist": 168,
        "painting_title": 260,
        "handle": 140,
        "image_filename": 220,
    }
    sort_state: dict[str, bool] = {}

    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10, selectmode="extended")

    def _update_sort_headings(*, active: str | None = None, reverse: bool = False) -> None:
        arrow_up = " \u25b2"
        arrow_down = " \u25bc"
        for c in cols:
            base = headings[c]
            if c == active:
                base += arrow_down if reverse else arrow_up
            if c in ("desc_status", "compare_status", "do_tlum", "tlum_gpt", "tlum_sonn", "z_obrazu", "bez_16", "artist"):
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
        anchor = "center" if c in ("flag", "desc_status", "compare_status", "do_tlum", "tlum_gpt", "tlum_sonn", "z_obrazu", "bez_16") else "w"
        tree.column(c, width=widths[c], anchor=anchor, stretch=(c == "painting_title"))
    tree.tag_configure("updated", background="#e8f5e9", foreground="#1b5e20")
    tree.tag_configure("pl_pending", background="#e1bee7", foreground="#4a148c")
    tree.tag_configure("resume_flag", background="#fff8e1", foreground="#e65100")
    tree.tag_configure("updated_resume", background="#e8f5e9", foreground="#e65100")
    tree.tag_configure("pl_pending_resume", background="#e1bee7", foreground="#e65100")
    tree.tag_configure("compare_unmarked", background="#e3f2fd", foreground="#0d47a1")
    tree.tag_configure("compare_resume", background="#e3f2fd", foreground="#e65100")
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    filter_var.trace_add("write", lambda *_: _refresh_tree())

    def _sync_filter_btns() -> None:
        for m, btn in filter_btns.items():
            if m == "all":
                btn.state(["pressed"] if not filter_active else ["!pressed"])
            else:
                btn.state(["pressed"] if m in filter_active else ["!pressed"])

    def _row_matches_filters(
        *,
        is_marked: bool,
        is_pl_pending: bool,
        is_from_image: bool,
        has_do_tlum: bool,
    ) -> bool:
        if not filter_active:
            return True
        if "updated" in filter_active and not is_marked:
            return False
        if "not_updated" in filter_active and (is_marked or is_pl_pending):
            return False
        if "without_update" in filter_active and is_marked:
            return False
        if "from_image" in filter_active and not is_from_image:
            return False
        if "not_from_image" in filter_active and is_from_image:
            return False
        if "do_tlumaczenia" in filter_active and not has_do_tlum:
            return False
        return True

    def _toggle_list_filter(mode: str) -> None:
        if mode == "all":
            filter_active.clear()
        elif mode in filter_active:
            filter_active.discard(mode)
        else:
            filter_active.add(mode)
        _sync_filter_btns()
        _refresh_tree()

    for label, mode in (
        ("Wszystkie", "all"),
        ("Po aktualizacji", "updated"),
        ("Bez oznaczenia", "not_updated"),
        ("bez aktualizacji", "without_update"),
        ("do tlumaczenia", "do_tlumaczenia"),
        ("z obrazu ✓", "from_image"),
        ("bez z obrazu", "not_from_image"),
    ):
        btn = ttk.Button(
            filter_btns_frame,
            text=label,
            width=16,
            command=lambda m=mode: _toggle_list_filter(m),
        )
        btn.pack(side="left", padx=(4, 0))
        filter_btns[mode] = btn
    _sync_filter_btns()

    auto_copy_var = tk.IntVar(value=1 if load_description_auto_copy_prompt() else 0)
    auto_copy_frame = ttk.Frame(filter_btns_frame)
    auto_copy_frame.pack(side="right")
    auto_copy_label_var = tk.StringVar()

    def _auto_copy_prompt_enabled() -> bool:
        return bool(auto_copy_var.get())

    def _update_auto_copy_label() -> None:
        auto_copy_label_var.set("Wlaczone" if _auto_copy_prompt_enabled() else "Wylaczone")

    def _set_auto_copy(idx: int) -> None:
        snapped = max(0, min(int(idx), 1))
        auto_copy_var.set(snapped)
        _update_auto_copy_label()
        save_description_auto_copy_prompt(bool(snapped))

    def _on_auto_copy_scale(val: str) -> None:
        _set_auto_copy(int(round(float(val))))

    ttk.Label(auto_copy_frame, text="Auto prompt:").pack(side="left")
    auto_copy_scale = ttk.Scale(
        auto_copy_frame,
        from_=0,
        to=1,
        orient="horizontal",
        variable=auto_copy_var,
        length=72,
        command=_on_auto_copy_scale,
    )
    auto_copy_scale.pack(side="left", padx=(6, 4))
    auto_copy_scale.bind("<ButtonRelease-1>", lambda _e: _set_auto_copy(auto_copy_var.get()))
    for i, name in enumerate(("Wyl", "Wl")):
        ttk.Button(
            auto_copy_frame,
            text=name,
            width=4,
            command=lambda ix=i: _set_auto_copy(ix),
        ).pack(side="left", padx=1)
    ttk.Label(
        auto_copy_frame,
        textvariable=auto_copy_label_var,
        foreground="#555",
        font=("Segoe UI", 8),
    ).pack(side="left", padx=(6, 0))
    _update_auto_copy_label()

    # --- srodek: tryb + JSON ---
    mid = ttk.Frame(dlg, padding=(12, 0))
    mid.pack(fill="x")

    mode_frame = ttk.LabelFrame(mid, text="Tryb aktualizacji", padding=(10, 8))
    mode_frame.pack(side="left", fill="y", padx=(0, 10))
    ttk.Radiobutton(
        mode_frame, text="Podmien wszystko", variable=state["mode"], value="replace_all",
        command=lambda: _on_mode_changed(),
    ).pack(anchor="w")
    ttk.Radiobutton(
        mode_frame, text="Podmien wybrany akapit", variable=state["mode"],
        value="replace_paragraph", command=lambda: _on_mode_changed(),
    ).pack(anchor="w")
    ttk.Label(
        mode_frame,
        text="(numer akapitu wybierz\nponizej w podgladzie)",
        foreground="#666",
        font=("Segoe UI", 8),
    ).pack(anchor="w", padx=(18, 0))
    ttk.Radiobutton(
        mode_frame, text="Dodaj jeszcze jeden akapit", variable=state["mode"],
        value="add_paragraph", command=lambda: _on_mode_changed(),
    ).pack(anchor="w", pady=(6, 0))

    json_frame = ttk.LabelFrame(mid, text="Tablica JSON z LLM", padding=(10, 8))
    json_frame.pack(side="left", fill="both", expand=True)
    json_text = scrolledtext.ScrolledText(json_frame, height=8, wrap="word", font=("Consolas", 10))
    json_text.pack(fill="both", expand=True)
    json_btns = ttk.Frame(json_frame)
    json_btns.pack(fill="x", pady=(6, 0))
    analyze_btn = ttk.Button(json_btns, text="Analizuj JSON", command=lambda: _analyze_json())
    analyze_btn.pack(side="left")
    match_var = tk.StringVar(value="")
    ttk.Label(json_btns, textvariable=match_var, foreground="#1565c0", wraplength=520).pack(
        side="left", padx=(12, 0)
    )

    # --- dol: podglad ---
    preview_frame = ttk.LabelFrame(dlg, text="Podglad zmian", padding=(10, 8))
    preview_frame.pack(fill="both", expand=True, padx=12, pady=(6, 6))

    lang_bar = ttk.Frame(preview_frame)
    lang_bar.pack(fill="x", pady=(0, 8))
    ttk.Label(lang_bar, text="Wersja jezykowa:").pack(side="left")
    lang_btns: dict[str, ttk.Button] = {}

    preview_note = tk.StringVar(value="Kliknij produkt na liscie — wczytam obecny opis z Shopify.")
    ttk.Label(preview_frame, textvariable=preview_note, foreground="#444", wraplength=1100).pack(
        anchor="w", pady=(0, 6)
    )

    para_edit_bar = ttk.Frame(preview_frame)
    para_edit_bar.pack(fill="x", pady=(0, 8))
    para_row1 = ttk.Frame(para_edit_bar)
    para_row1.pack(fill="x")
    para_row2 = ttk.Frame(para_edit_bar)
    para_row2.pack(fill="x", pady=(6, 0))
    ttk.Label(para_row1, text="Edytuj akapit:").pack(side="left")
    para_edit_btns: dict[int, ttk.Button] = {}
    new_description_prompt_btn = ttk.Button(
        para_row1,
        text="Prompt do nowego opisu",
        command=lambda: _copy_new_description_prompt(),
    )
    image_description_prompt_btn = ttk.Button(
        para_row1,
        text="Opis z obrazu",
        command=lambda: _copy_image_description_prompt(),
    )
    image_description_prompt_v2_btn = ttk.Button(
        para_row1,
        text="Opis z obrazu v2",
        command=lambda: _copy_image_description_prompt(v2=True),
    )
    compare_btn = ttk.Button(
        para_row1,
        text="Porownywarka",
        command=lambda: _open_compare_dialog(),
    )
    llm_frame = ttk.Frame(para_row1)
    translation_prompt_btn = ttk.Button(
        para_row2,
        text="Prompt tlumaczenia",
        command=lambda: _copy_translation_prompt(),
    )
    paste_translations_btn = ttk.Button(
        para_row2,
        text="Wklej tlumaczenia do akapitu",
        command=lambda: _open_paste_translations_dialog(),
    )
    copy_translations_json_btn = ttk.Button(
        para_row2,
        text="JSON obecnych tlumaczen",
        command=lambda: _copy_current_translations_json(),
    )
    giga_translation_btn = ttk.Button(
        para_row2,
        text="GIGA TLUMACZENIE",
        command=lambda: _copy_giga_translation_prompt(),
        state="disabled",
    )
    giga_paste_btn = ttk.Button(
        para_row2,
        text="Wklej GIGA TLUMACZENIE",
        command=lambda: _open_paste_giga_translations_dialog(),
        state="disabled",
    )
    llm_idx_var = tk.IntVar(value=compare_llm_provider_index(load_description_compare_llm()))
    llm_label_var = tk.StringVar()

    def _llm_provider() -> str:
        return compare_provider_from_index(llm_idx_var.get())

    def _update_llm_scale_label() -> None:
        provider = _llm_provider()
        ver = compare_default_version_for_provider(provider) + 1
        llm_label_var.set(f"{COMPARE_LLM_LABELS[provider]} → wersja {ver}")

    def _on_llm_scale(val: str) -> None:
        snapped = int(round(float(val)))
        if llm_idx_var.get() != snapped:
            llm_idx_var.set(snapped)
        _update_llm_scale_label()
        save_description_compare_llm(_llm_provider())

    def _set_llm_index(idx: int) -> None:
        snapped = max(0, min(int(idx), 2))
        llm_idx_var.set(snapped)
        _update_llm_scale_label()
        save_description_compare_llm(_llm_provider())

    llm_inner = ttk.Frame(llm_frame)
    llm_inner.pack(side="left")
    ttk.Label(llm_inner, text="Model:").pack(side="left")
    llm_scale = ttk.Scale(
        llm_inner,
        from_=0,
        to=2,
        orient="horizontal",
        variable=llm_idx_var,
        length=132,
        command=_on_llm_scale,
    )
    llm_scale.pack(side="left", padx=(6, 4))
    llm_scale.bind("<ButtonRelease-1>", lambda _e: _set_llm_index(llm_idx_var.get()))
    llm_ticks = ttk.Frame(llm_inner)
    llm_ticks.pack(side="left")
    for i, name in enumerate(("Sonnet", "Gemini", "GPT")):
        ttk.Button(
            llm_ticks,
            text=name,
            width=7,
            command=lambda ix=i: _set_llm_index(ix),
        ).pack(side="left", padx=1)
    ttk.Label(
        llm_frame,
        textvariable=llm_label_var,
        foreground="#555",
        font=("Segoe UI", 8),
    ).pack(side="left", padx=(8, 0))
    _update_llm_scale_label()
    preview_pane = ttk.Panedwindow(preview_frame, orient="horizontal")
    preview_pane.pack(fill="both", expand=True)

    old_frame = ttk.LabelFrame(preview_pane, text="Obecny opis (akapity)", padding=4)
    new_frame = ttk.LabelFrame(preview_pane, text="Po zmianie (mozna edytowac)", padding=4)
    preview_pane.add(old_frame, weight=1)
    preview_pane.add(new_frame, weight=1)

    old_header = ttk.Frame(old_frame)
    old_header.pack(fill="x", pady=(0, 4))
    save_old_btn = ttk.Button(
        old_header,
        text="Zapisz obecny opis",
        command=lambda: _save_current_description(),
        state="disabled",
    )
    save_old_btn.pack(side="right", padx=(4, 0))
    save_all_old_btn = ttk.Button(
        old_header,
        text="Zapisz kazda wersje jezykowa",
        command=lambda: _save_all_current_descriptions(),
        state="disabled",
    )
    save_all_old_btn.pack(side="right")

    old_text = scrolledtext.ScrolledText(old_frame, height=14, wrap="word", font=("Segoe UI", 10))
    old_text.pack(fill="both", expand=True)

    new_text = scrolledtext.ScrolledText(new_frame, height=14, wrap="word", font=("Segoe UI", 10))
    new_text.pack(fill="both", expand=True)

    bottom = ttk.Frame(dlg, padding=(12, 0, 12, 12))
    bottom.pack(fill="x")
    apply_btn = ttk.Button(bottom, text="Zastosuj w Shopify", command=lambda: _apply(), state="disabled")
    apply_btn.pack(side="right")
    ttk.Button(
        bottom, text="Otworz w Shopify",
        command=lambda: _open_admin(),
    ).pack(side="right", padx=(0, 8))
    ttk.Button(bottom, text="Zamknij", command=dlg.destroy).pack(side="right", padx=(0, 8))
    refresh_btn = ttk.Button(bottom, text="Odswiez liste produktow", command=lambda: _load_products())
    refresh_btn.pack(side="left")

    def _parse_edited_paragraphs(text: str) -> list[str]:
        parts: list[str] = []
        for chunk in text.split("--- Akapit"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "]" in chunk[:20] or "---" in chunk[:20]:
                lines = chunk.split("\n", 1)
                body = lines[1].strip() if len(lines) > 1 else ""
            else:
                body = chunk
            if body:
                parts.append(body)
        return parts[:4]

    def _set_preview_text(widget: scrolledtext.ScrolledText, text: str, *, readonly: bool) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled" if readonly else "normal")

    def _paragraphs_equal(a: list[str], b: list[str]) -> bool:
        if len(a) != len(b):
            return False
        return all(_norm_paragraph(x) == _norm_paragraph(y) for x, y in zip(a, b))

    def _norm_paragraph(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip().lower())

    def _old_paragraphs_list() -> list[str]:
        locale = state.get("locale") or "pl"
        if locale in state["draft_old_paragraphs"]:
            return list(state["draft_old_paragraphs"][locale])
        baseline = state["baseline_paragraphs"].get(locale)
        return list(baseline) if baseline else []

    def _new_paragraphs_list() -> list[str]:
        locale = state.get("locale") or "pl"
        if locale in state["edited_paragraphs"]:
            return list(state["edited_paragraphs"][locale])
        prev = state["previews"].get(locale)
        if prev:
            return list(prev.get("new_paragraphs") or [])
        return []

    def _commit_old_paragraph_field() -> None:
        locale = state.get("locale")
        if not locale:
            return
        text = old_text.get("1.0", "end").strip()
        if text in ("", _LOADING_TEXT):
            return
        paras = _old_paragraphs_list()
        idx = state["edit_paragraph_idx"]
        while len(paras) <= idx:
            paras.append("")
        paras[idx] = text
        state["draft_old_paragraphs"][locale] = paras[:4]

    def _commit_new_paragraph_field() -> None:
        if not state.get("llm_item"):
            return
        locale = state.get("locale")
        if not locale:
            return
        paras = _new_paragraphs_list()
        idx = state["edit_paragraph_idx"]
        text = new_text.get("1.0", "end").strip()
        while len(paras) <= idx:
            paras.append("")
        paras[idx] = text
        state["edited_paragraphs"][locale] = paras[:4]

    def _visible_old_paragraph_text() -> str:
        idx = state["edit_paragraph_idx"]
        paras = _old_paragraphs_list()
        if idx < len(paras):
            text = (paras[idx] or "").strip()
            if text and text != _LOADING_TEXT:
                return text
        text = old_text.get("1.0", "end").strip()
        if text in ("", _LOADING_TEXT):
            return ""
        return text

    def _current_paragraph_text() -> str:
        _commit_old_paragraph_field()
        return _visible_old_paragraph_text()

    def _selected_product_row() -> dict[str, Any] | None:
        return state.get("selected_product") or _selected_row()

    def _discard_spurious_draft(locale: str) -> None:
        draft = state["draft_old_paragraphs"].get(locale)
        if not draft:
            return
        if any((p or "").strip() == _LOADING_TEXT for p in draft):
            state["draft_old_paragraphs"].pop(locale, None)

    def _update_prompt_btns() -> None:
        locale = state.get("locale")
        product = _selected_product_row()
        has_product = bool(product)
        has_paragraph = any(
            (p or "").strip() and (p or "").strip() != _LOADING_TEXT
            for p in _old_paragraphs_list()
        ) or bool(_visible_old_paragraph_text())

        if has_product:
            if not new_description_prompt_btn.winfo_ismapped():
                new_description_prompt_btn.pack(side="left", padx=(16, 0))
            new_description_prompt_btn.configure(state="normal")
            if not image_description_prompt_btn.winfo_ismapped():
                image_description_prompt_btn.pack(side="left", padx=(8, 0))
            image_description_prompt_btn.configure(state="normal")
            if not image_description_prompt_v2_btn.winfo_ismapped():
                image_description_prompt_v2_btn.pack(side="left", padx=(8, 0))
            image_description_prompt_v2_btn.configure(state="normal")
        else:
            if new_description_prompt_btn.winfo_ismapped():
                new_description_prompt_btn.pack_forget()
            if image_description_prompt_btn.winfo_ismapped():
                image_description_prompt_btn.pack_forget()
            if image_description_prompt_v2_btn.winfo_ismapped():
                image_description_prompt_v2_btn.pack_forget()

        if has_product and locale:
            if not translation_prompt_btn.winfo_ismapped():
                translation_prompt_btn.pack(side="left", padx=(0, 8))
            translation_prompt_btn.configure(
                state="normal" if has_paragraph else "disabled",
            )
        elif translation_prompt_btn.winfo_ismapped():
            translation_prompt_btn.pack_forget()

        if has_product and state.get("full_product"):
            if not paste_translations_btn.winfo_ismapped():
                paste_translations_btn.pack(side="left", padx=(0, 8))
            paste_translations_btn.configure(state="normal")
            if not copy_translations_json_btn.winfo_ismapped():
                copy_translations_json_btn.pack(side="left", padx=(0, 8))
            copy_translations_json_btn.configure(state="normal")
        elif paste_translations_btn.winfo_ismapped():
            paste_translations_btn.pack_forget()
            copy_translations_json_btn.pack_forget()

        n_selected = len(_selected_rows())
        giga_pad = (0, 8) if translation_prompt_btn.winfo_ismapped() else (0, 0)
        if not giga_translation_btn.winfo_ismapped():
            giga_translation_btn.pack(side="left", padx=giga_pad)
            giga_paste_btn.pack(side="left", padx=(0, 8))
        if n_selected >= 2:
            giga_translation_btn.configure(
                state="normal",
                text=f"GIGA TLUMACZENIE ({n_selected})",
            )
            giga_paste_btn.configure(
                state="normal",
                text=f"Wklej GIGA TLUMACZENIE ({n_selected})",
            )
        else:
            giga_translation_btn.configure(
                state="disabled",
                text="GIGA TLUMACZENIE",
            )
            giga_paste_btn.configure(
                state="disabled",
                text="Wklej GIGA TLUMACZENIE",
            )

        if has_product and state.get("full_product"):
            if not compare_btn.winfo_ismapped():
                compare_btn.pack(side="left", padx=(8, 0))
            compare_btn.configure(state="normal")
            if not llm_frame.winfo_ismapped():
                llm_frame.pack(side="left", padx=(12, 0))
        else:
            if compare_btn.winfo_ismapped():
                compare_btn.pack_forget()
            if llm_frame.winfo_ismapped():
                llm_frame.pack_forget()

    def _paragraph_text_at(idx: int) -> str:
        locale = state.get("locale") or "pl"
        paras = _old_paragraphs_list()
        if idx < len(paras):
            text = (paras[idx] or "").strip()
            if text and text != _LOADING_TEXT:
                return text
        if idx == state["edit_paragraph_idx"]:
            return _visible_old_paragraph_text()
        return ""

    def _product_image_url(row: dict[str, Any] | None) -> str:
        if not row:
            return ""
        if _full_product_matches_row(row):
            full = state.get("full_product") or {}
            img = full.get("image") or {}
            src = (img.get("src") or "").strip()
            if src:
                return src
            for im in full.get("images") or []:
                src = (im.get("src") or "").strip()
                if src:
                    return src
        return (row.get("image_src") or "").strip()

    def _compare_context() -> dict[str, Any]:
        product = _selected_product_row()
        if not product or not state.get("full_product"):
            return {"ok": False, "error": "Wybierz produkt i poczekaj na wczytanie opisu."}
        _commit_old_paragraph_field()
        locale = state.get("locale") or "pl"
        idx = state["edit_paragraph_idx"]
        image_url = _product_image_url(product)
        return {
            "ok": True,
            "product_id": int(product.get("product_id") or product.get("id") or 0),
            "locale": locale,
            "locale_label": LOCALE_LABELS.get(locale, locale),
            "paragraph_index": idx,
            "paragraph_text": _paragraph_text_at(idx),
            "product_title": (product.get("painting_title") or product.get("product_title") or ""),
            "image_url": image_url,
        }

    def _apply_compare_paragraph(para_idx: int, text: str) -> None:
        locale = state.get("locale") or "pl"
        idx = max(0, min(int(para_idx), 3))
        paras = list(_old_paragraphs_list())
        while len(paras) <= idx:
            paras.append("")
        paras[idx] = text
        state["draft_old_paragraphs"][locale] = paras[:4]
        state["edit_paragraph_idx"] = idx
        state["paragraph_index"].set(idx + 1)
        _show_paragraph_editors()
        _update_save_old_btn()

    def _open_compare_dialog() -> None:
        def _persist_compare_and_refresh() -> None:
            save_compare_versions(state["compare_versions"])
            _refresh_tree()

        open_description_compare_dialog(
            dlg,
            get_context=_compare_context,
            get_paragraph_text=_paragraph_text_at,
            apply_paragraph=_apply_compare_paragraph,
            compare_store=state["compare_versions"],
            persist_compare_store=_persist_compare_and_refresh,
            on_apply_all_paragraphs=None,
            after_apply_all=lambda: _save_all_current_descriptions(skip_confirm=True),
            default_version_idx=compare_default_version_for_provider(_llm_provider()),
        )

    def _full_product_matches_row(product: dict[str, Any] | None) -> bool:
        full = state.get("full_product")
        if not product or not full:
            return False
        try:
            pid = int(product.get("product_id") or product.get("id") or 0)
            fid = int(full.get("id") or 0)
        except (TypeError, ValueError):
            return False
        return bool(pid) and pid == fid

    def _try_open_compare_for_pid(pid: int) -> bool:
        if state.get("compare_open_pid") != pid:
            return False
        product = _selected_row()
        if not product or int(product.get("product_id") or 0) != pid:
            return False
        if not _full_product_matches_row(product):
            return False
        state["compare_open_pid"] = None
        _open_compare_dialog()
        return True

    def _schedule_compare_open_for_row(row: dict[str, Any]) -> None:
        pid = int(row.get("product_id") or 0)
        if not pid:
            return
        state["compare_open_pid"] = pid
        state["selected_product"] = row

        def _deferred_open(attempt: int = 0) -> None:
            if _try_open_compare_for_pid(pid):
                return
            if state.get("compare_open_pid") != pid:
                return
            if attempt < 80:
                dlg.after(150, lambda: _deferred_open(attempt + 1))

        dlg.after(50, _deferred_open)

    def _copy_prompt_to_clipboard(prompt: str, *, parent: tk.Misc) -> None:
        try:
            parent.clipboard_clear()
            parent.clipboard_append(prompt)
            parent.update()
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=parent)
            raise

    def _baseline_for_locale(loc: str) -> list[str] | None:
        """Akapity z Shopify (cache), bez draftu — do porownan i wklejania tlumaczen."""
        if loc in state["baseline_paragraphs"]:
            return list(state["baseline_paragraphs"][loc])
        product = _selected_product_row()
        full = state.get("full_product")
        if not product or not full:
            return None
        shop, token = sc.load_session()
        paragraphs = load_current_paragraphs(
            product_id=int(product["product_id"]),
            full_product=full,
            locale=loc,
            shop=shop,
            token=token,
        )
        state["baseline_paragraphs"][loc] = list(paragraphs)
        return list(paragraphs)

    def _ensure_baseline_paragraphs(loc: str) -> list[str]:
        if loc in state["draft_old_paragraphs"]:
            return list(state["draft_old_paragraphs"][loc])
        baseline = _baseline_for_locale(loc)
        return list(baseline) if baseline is not None else []

    def _apply_paragraph_translations(translations: dict[str, str]) -> dict[str, list[str]]:
        _stash_locale_edits()
        idx = state["edit_paragraph_idx"]
        pl_paras = _baseline_for_locale("pl") or _ensure_baseline_paragraphs("pl")
        target_len = max(len(pl_paras), idx + 1, 3)
        to_save: dict[str, list[str]] = {}
        applied: list[str] = []
        for lang in TRANSLATION_LANGS:
            text = translations[lang]
            baseline = _baseline_for_locale(lang) or []
            if len(baseline) < target_len:
                pl_seed = _baseline_for_locale("pl") or []
                if len(pl_seed) >= target_len:
                    baseline = [""] * target_len
                else:
                    baseline = list(baseline)
            paras = list(baseline)
            while len(paras) < target_len:
                paras.append("")
            paras[idx] = text
            paras = paras[:4]
            state["draft_old_paragraphs"][lang] = paras
            to_save[lang] = paras
            applied.append(lang)
        _show_paragraph_editors()
        _update_save_old_btn()
        labels = ", ".join(LOCALE_LABELS.get(l, l) for l in applied)
        preview_note.set(
            f"Wklejono tlumaczenia akapitu {idx + 1} dla: {labels}. Zapisuje wersje jezykowe..."
        )
        show_toast(dlg, f"Tlumaczenia akapitu {idx + 1} wklejone", duration_ms=1600)
        return to_save

    def _apply_all_paragraph_translations(items: list[dict[str, str]]) -> dict[str, list[str]]:
        _stash_locale_edits()
        pl_paras = _baseline_for_locale("pl") or _ensure_baseline_paragraphs("pl")
        pl_count = max(len(pl_paras), len(items), 3)
        target_len = min(4, pl_count)
        to_save: dict[str, list[str]] = {}
        for lang in TRANSLATION_LANGS:
            baseline = _baseline_for_locale(lang) or []
            paras = list(baseline)
            while len(paras) < target_len:
                paras.append("")
            for para_idx, translations in enumerate(items):
                paras[para_idx] = translations[lang]
            paras = paras[:4]
            state["draft_old_paragraphs"][lang] = paras
            to_save[lang] = paras
        _show_paragraph_editors()
        _update_save_old_btn()
        labels = ", ".join(LOCALE_LABELS.get(l, l) for l in TRANSLATION_LANGS)
        note = (
            f"Wklejono tlumaczenia akapitow 1–{len(items)} dla: {labels}. "
            f"Zapisuje wersje jezykowe..."
        )
        if len(pl_paras) > len(items):
            note += (
                f" Uwaga: polski opis ma {len(pl_paras)} akapitow, "
                f"a JSON tylko {len(items)} — akapit(y) "
                f"{', '.join(str(i) for i in range(len(items) + 1, len(pl_paras) + 1))} "
                f"nie zostaly uzupelnione."
            )
        preview_note.set(note)
        show_toast(
            dlg,
            f"Tlumaczenia akapitow 1–{len(items)} wklejone",
            duration_ms=1600,
        )
        return to_save

    def _sync_marks_from_disk(pid: int | None = None) -> None:
        state["updated_marks"] = load_description_update_marks()
        state["pl_pending_marks"] = load_description_pl_pending_marks()
        state["gpt_marks"] = load_description_gpt_translation_marks()
        state["sonnet_marks"] = load_description_sonnet_translation_marks()
        state["from_image_marks"] = load_description_from_image_marks()
        state["do_tlum_marks"] = load_description_do_tlumaczenia_marks()
        state["bez_16_marks"] = load_description_bez_16_marks()
        preserve: set[int] | None = None
        if pid:
            preserve = {int(pid)}
        else:
            preserve = _selected_pids() or None
        _refresh_tree(preserve_pids=preserve)

    def _mark_product_after_save(
        product_id: int,
        *,
        saved_locales: list[str],
        translations_pushed: bool = False,
        translations_pasted: bool = False,
    ) -> None:
        pid = int(product_id)
        if not pid:
            return
        update_description_marks_after_save(
            pid,
            saved_locales=saved_locales,
            translations_pushed=translations_pushed,
            translations_pasted=translations_pasted,
        )
        _sync_marks_from_disk(pid)

    def _save_locales_paragraphs(
        product: dict[str, Any],
        locales_paragraphs: dict[str, list[str]],
        *,
        skip_confirm: bool = False,
        translations_pasted: bool = False,
    ) -> None:
        if not product:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        if not locales_paragraphs:
            if not skip_confirm:
                messagebox.showinfo(
                    APP_TITLE,
                    "Brak zmian w wersjach jezykowych do zapisania.",
                    parent=dlg,
                )
            return

        try:
            pid = int(product["product_id"])
        except (TypeError, ValueError):
            return
        if not pid:
            return

        labels = [LOCALE_LABELS.get(loc, loc) for loc in locales_paragraphs]
        if not skip_confirm and not messagebox.askyesno(
            APP_TITLE,
            f"Zapisac obecny opis dla {len(locales_paragraphs)} wersji jezykowych:\n"
            f"{', '.join(labels)}\n\n"
            f"Produkt: {product.get('product_title')}?",
            parent=dlg,
        ):
            return

        save_old_btn.configure(state="disabled")
        save_all_old_btn.configure(state="disabled")
        set_status("Zapisuje wersje jezykowe w Shopify...")

        def work() -> None:
            try:
                res = apply_current_paragraphs_batch(
                    product_id=pid,
                    locales_paragraphs=locales_paragraphs,
                    logger=enqueue_log,
                )
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                dlg.after(0, lambda: _update_save_old_btn())
                dlg.after(0, lambda: set_status("Blad zapisu wersji jezykowych."))
                return

            def done() -> None:
                saved = res.get("saved_locales") or []
                errs = res.get("errors") or []
                if saved:
                    _mark_product_after_save(
                        pid,
                        saved_locales=saved,
                        translations_pasted=translations_pasted,
                    )
                enqueue_log(
                    f"[opis] Zapisano recznie id={res['product_id']} "
                    f"— jezyki: {', '.join(saved)}."
                )
                set_status("Wersje jezykowe zapisane.")
                msg = (
                    f"Zapisano {len(saved)} wersji: "
                    f"{', '.join(LOCALE_LABELS.get(l, l) for l in saved)}.\n{res['admin_url']}"
                )
                if errs:
                    msg += "\n\nBledy:\n" + "\n".join(
                        f"- {LOCALE_LABELS.get(e['locale'], e['locale'])}: {e['error']}"
                        for e in errs
                    )
                if skip_confirm and saved and not errs:
                    show_toast(dlg, f"Zapisano {len(saved)} wersji jezykowych", duration_ms=1600)
                else:
                    messagebox.showinfo(APP_TITLE, msg, parent=dlg)
                for loc in saved:
                    state["draft_old_paragraphs"].pop(loc, None)
                    refreshed = _baseline_for_locale(loc)
                    if refreshed is not None:
                        state["baseline_paragraphs"][loc] = list(
                            locales_paragraphs.get(loc, refreshed)
                        )

                def after_save() -> None:
                    _display_current_description()
                    if state.get("llm_item"):
                        _rebuild_preview()

                _fetch_full_product(product, after_save)
                _update_save_old_btn()

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _open_paste_translations_dialog() -> None:
        product = _selected_product_row()
        if not product:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        if not state.get("full_product"):
            messagebox.showwarning(
                APP_TITLE,
                "Poczekaj na wczytanie opisu z Shopify.",
                parent=dlg,
            )
            return
        idx = state["edit_paragraph_idx"] + 1
        sub = tk.Toplevel(dlg)
        sub.title("Wklej tlumaczenia akapitu")
        position_toplevel_screen_center(sub, 760, 520)
        sub.minsize(560, 360)
        sub.transient(dlg)
        sub.grab_set()

        ttk.Label(
            sub,
            text=(
                f"Wklej JSON z tlumaczeniami (klucze: en, de, fr, es, nl, it).\n"
                f"Jeden obiekt {{...}} — akapit {idx}; kilka obiektow — akapity 1–4 naraz;\n"
                f"albo jeden obiekt {{akapit_1: {{...}}, akapit_2: {{...}}, ...}}.\n"
                "Dopuszczalne: same bloki JSON pod soba albo sekcje **Akapit N** + ```json ... ```."
            ),
            wraplength=700,
        ).pack(anchor="w", padx=12, pady=(12, 6))

        text_frame = ttk.Frame(sub, padding=(12, 0))
        text_frame.pack(fill="both", expand=True)
        paste_text = scrolledtext.ScrolledText(text_frame, height=16, wrap="word", font=("Consolas", 10))
        paste_text.pack(fill="both", expand=True)

        btn_row = ttk.Frame(sub, padding=(12, 8))
        btn_row.pack(fill="x")

        def _paste_clipboard() -> None:
            try:
                data = dlg.clipboard_get()
            except tk.TclError:
                messagebox.showwarning(APP_TITLE, "Schowek jest pusty.", parent=sub)
                return
            paste_text.delete("1.0", "end")
            paste_text.insert("1.0", data)

        def _apply() -> None:
            raw = paste_text.get("1.0", "end").strip()
            try:
                batch = parse_paragraph_translations_batch(raw)
            except ValueError as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=sub)
                return
            sub.destroy()
            if len(batch) == 1:
                to_save = _apply_paragraph_translations(batch[0])
            else:
                to_save = _apply_all_paragraph_translations(batch)
            _save_locales_paragraphs(
                product,
                to_save,
                skip_confirm=True,
                translations_pasted=True,
            )

        ttk.Button(btn_row, text="Wklej ze schowka", command=_paste_clipboard).pack(side="left")
        ttk.Button(btn_row, text="Zastosuj", command=_apply).pack(side="right")
        ttk.Button(btn_row, text="Anuluj", command=sub.destroy).pack(side="right", padx=(0, 8))
        sub.bind("<Escape>", lambda _e: sub.destroy())
        paste_text.focus_set()

    def _resolve_new_description_titles() -> dict[str, str] | None:
        product = _selected_product_row()
        if not product:
            return None
        artist = (product.get("artist") or "").strip()
        if not artist:
            return None

        title_pl = (product.get("painting_title") or product.get("product_title") or "").strip()
        title_en = ""
        title_original = ""

        llm_item = state.get("llm_item")
        if llm_item:
            title_original = (llm_item.get("tytul_orginalny") or "").strip()
            title_pl = (llm_item.get("tytul_polski") or title_pl).strip()
            en_block = (llm_item.get("tlumaczenia") or {}).get("en") or {}
            if isinstance(en_block, dict):
                title_en = (en_block.get("tytul_polski") or "").strip()

        full = state.get("full_product")
        if full:
            body_pl = full.get("body_html") or ""
            if not title_original:
                title_original = extract_original_title_from_body_html(body_pl)
            if not title_pl:
                title_pl = extract_display_title_from_body_html(body_pl)

            if not title_en:
                try:
                    shop, token = sc.load_session()
                    gid = sc.product_gid(int(product["product_id"]))
                    tr_en = get_translated_fields(shop, token, gid, "en")
                    body_en = tr_en.get("body_html") or ""
                    title_en = extract_display_title_from_body_html(body_en)
                except Exception:
                    pass

        if not title_en:
            fn = (product.get("image_filename") or "").strip()
            if fn:
                fn = fn.rsplit("/", 1)[-1].split("?", 1)[0]
                try:
                    _a, t_fn = parse_filename(fn)
                    if (t_fn or "").strip():
                        title_en = t_fn.strip()
                except ValueError:
                    pass

        if not title_pl and not title_en and not title_original:
            return None

        return {
            "artist": artist,
            "title_pl": title_pl,
            "title_en": title_en,
            "title_original": title_original,
        }

    def _copy_new_description_prompt(*, silent: bool = False) -> bool:
        ctx = _resolve_new_description_titles()
        if not ctx:
            if not silent:
                messagebox.showwarning(
                    APP_TITLE,
                    "Wybierz produkt z listy (potrzebny artysta i tytul).",
                    parent=dlg,
                )
            return False
        prompt = build_new_description_prompt(
            artist=ctx["artist"],
            title_pl=ctx["title_pl"],
            title_en=ctx["title_en"],
            title_original=ctx["title_original"],
        )
        try:
            dlg.clipboard_clear()
            dlg.clipboard_append(prompt)
            dlg.update()
        except tk.TclError as exc:
            if not silent:
                messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=dlg)
            return False
        parts = [p for p in (ctx["title_en"], ctx["title_original"]) if p]
        suffix = f" ({', '.join(parts[:2])})" if parts else ""
        show_toast(dlg, f"Prompt do nowego opisu skopiowany{suffix}", duration_ms=1600)
        return True

    def _display_title_for_image_prompt(ctx: dict[str, str]) -> str:
        for key in ("title_pl", "title_en", "title_original"):
            t = (ctx.get(key) or "").strip()
            if t:
                return t
        return ""

    def _copy_image_description_prompt(*, v2: bool = False) -> None:
        ctx = _resolve_new_description_titles()
        if not ctx:
            messagebox.showwarning(
                APP_TITLE,
                "Wybierz produkt z listy (potrzebny artysta i tytul).",
                parent=dlg,
            )
            return
        title = _display_title_for_image_prompt(ctx)
        if not title:
            messagebox.showwarning(
                APP_TITLE,
                "Brak tytulu dla zaznaczonego produktu.",
                parent=dlg,
            )
            return
        if v2:
            prompt = build_image_description_prompt_v2(artist=ctx["artist"], title=title)
            variant_label = "Opis z obrazu v2"
            thread_name = "copy-image-description-prompt-v2"
        else:
            prompt = build_image_description_prompt(artist=ctx["artist"], title=title)
            variant_label = "Opis z obrazu"
            thread_name = "copy-image-description-prompt"
        row = _selected_product_row()
        if not row:
            return
        image_url = _product_image_url(row)
        pid = int(row.get("product_id") or 0)

        def _show_helper(url: str) -> None:
            _open_gemini_image_prompt_helper(
                dlg,
                prompt=prompt,
                image_url=url,
                variant_label=variant_label,
            )

        if image_url:
            _show_helper(image_url)
            return

        def work() -> None:
            nonlocal image_url
            try:
                if pid:
                    shop, token = sc.load_session()
                    prod = sc.get_product(shop, token, pid)
                    img = prod.get("image") or {}
                    image_url = (img.get("src") or "").strip()
                    if not image_url:
                        for im in prod.get("images") or []:
                            src = (im.get("src") or "").strip()
                            if src:
                                image_url = src
                                break
                if not image_url:
                    raise ValueError("Brak grafiki glownej dla tego produktu.")
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                return
            dlg.after(0, lambda u=image_url: _show_helper(u))

        threading.Thread(target=work, daemon=True, name=thread_name).start()

    def _copy_translation_prompt() -> None:
        choice = messagebox.askyesnocancel(
            APP_TITLE,
            "Prompt tlumaczenia dla:\n\n"
            "TAK — wszystkich akapitow (biezaca wersja jezykowa)\n"
            "NIE — tylko zaznaczonego akapitu\n"
            "ANULUJ — przerwij",
            parent=dlg,
        )
        if choice is None:
            return
        _commit_old_paragraph_field()
        locale = state.get("locale") or "pl"
        if choice:
            paras = [p.strip() for p in _old_paragraphs_list() if (p or "").strip()]
            if not paras:
                messagebox.showwarning(
                    APP_TITLE,
                    "Brak akapitow w biezacej wersji jezykowej.",
                    parent=dlg,
                )
                return
            try:
                prompt = build_translation_prompt_all(paras)
            except ValueError as exc:
                messagebox.showwarning(APP_TITLE, str(exc), parent=dlg)
                return
            toast_suffix = f"wszystkie ({len(paras)} akapitow)"
        else:
            text = _visible_old_paragraph_text()
            if not text:
                messagebox.showwarning(
                    APP_TITLE,
                    "Wybrany akapit jest pusty — nie ma czego tlumaczyc.",
                    parent=dlg,
                )
                return
            prompt = build_translation_prompt(text)
            toast_suffix = f"akapit {state['edit_paragraph_idx'] + 1}"
        try:
            dlg.clipboard_clear()
            dlg.clipboard_append(prompt)
            dlg.update()
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=dlg)
            return
        show_toast(
            dlg,
            f"Prompt skopiowany ({LOCALE_LABELS.get(locale, locale)}, {toast_suffix})",
            duration_ms=1400,
        )

    def _copy_current_translations_json() -> None:
        product = _selected_product_row()
        if not product:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        full = state.get("full_product")
        if not full:
            messagebox.showwarning(
                APP_TITLE,
                "Poczekaj na wczytanie opisu z Shopify.",
                parent=dlg,
            )
            return
        copy_translations_json_btn.configure(state="disabled")
        set_status("Pobieram tlumaczenia ze Shopify...")

        def work() -> None:
            try:
                shop, token = sc.load_session()
                pid = int(product["product_id"])
                paragraphs_by_locale = load_all_locale_paragraphs(
                    product_id=pid,
                    full_product=full,
                    shop=shop,
                    token=token,
                )
                payload = build_current_translations_json(
                    artist=(product.get("artist") or "").strip(),
                    title=(
                        product.get("painting_title")
                        or product.get("product_title")
                        or ""
                    ).strip(),
                    paragraphs_by_locale=paragraphs_by_locale,
                )
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                dlg.after(0, lambda: set_status("Blad eksportu tlumaczen."))
                dlg.after(0, lambda: copy_translations_json_btn.configure(state="normal"))
                return

            def done() -> None:
                try:
                    dlg.clipboard_clear()
                    dlg.clipboard_append(payload)
                    dlg.update()
                except tk.TclError as exc:
                    messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=dlg)
                    copy_translations_json_btn.configure(state="normal")
                    return
                pl_count = len(paragraphs_by_locale.get("pl") or [])
                show_toast(
                    dlg,
                    f"JSON tlumaczen skopiowany ({pl_count} akapitow)",
                    duration_ms=1600,
                )
                set_status("JSON obecnych tlumaczen w schowku.")
                copy_translations_json_btn.configure(state="normal")

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _copy_giga_translation_prompt() -> None:
        rows = _selected_rows()
        if len(rows) < 2:
            messagebox.showwarning(
                APP_TITLE,
                "Zaznacz co najmniej 2 produkty (Ctrl+klik / Shift+klik).",
                parent=dlg,
            )
            return
        giga_translation_btn.configure(state="disabled")
        set_status(f"Pobieram opisy PL dla {len(rows)} produktow...")

        def work() -> None:
            try:
                shop, token = sc.load_session()
                items: list[dict[str, Any]] = []
                for row in rows:
                    pid = int(row["product_id"])
                    full = sc.get_product(shop, token, pid)
                    if not full:
                        raise ValueError(f"Nie znaleziono produktu id={pid}.")
                    paragraphs = load_current_paragraphs(
                        product_id=pid,
                        full_product=full,
                        locale="pl",
                        shop=shop,
                        token=token,
                    )
                    items.append(
                        {
                            "artist": row.get("artist") or "",
                            "title": row.get("painting_title")
                            or row.get("product_title")
                            or "",
                            "paragraphs": paragraphs,
                        }
                    )
                prompt = build_giga_translation_prompt(items)
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                dlg.after(0, lambda: set_status("Blad GIGA tlumaczenia."))
                dlg.after(0, _update_prompt_btns)
                return

            def done() -> None:
                try:
                    dlg.clipboard_clear()
                    dlg.clipboard_append(prompt)
                    dlg.update()
                except tk.TclError as exc:
                    messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=dlg)
                    _update_prompt_btns()
                    return
                show_toast(
                    dlg,
                    f"GIGA prompt skopiowany ({len(rows)} produktow)",
                    duration_ms=1800,
                )
                set_status(f"GIGA prompt: {len(rows)} produktow w schowku.")
                _update_prompt_btns()

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _open_paste_giga_translations_dialog() -> None:
        rows = _selected_rows()
        if len(rows) < 2:
            messagebox.showwarning(
                APP_TITLE,
                "Zaznacz co najmniej 2 produkty (ta sama kolejnosc co przy GIGA prompt).",
                parent=dlg,
            )
            return
        n = len(rows)
        sub = tk.Toplevel(dlg)
        sub.title("Wklej GIGA tlumaczenia")
        position_toplevel_screen_center(sub, 820, 560)
        sub.minsize(600, 400)
        sub.transient(dlg)
        sub.grab_set()

        ttk.Label(
            sub,
            text=(
                f"Wklej JSON z tlumaczeniami dla {n} zaznaczonych produktow.\n"
                f"Format: {{produkt_1: {{akapit_1: {{en, de, fr, es, nl, it}}, ...}}, "
                f"produkt_2: {{...}}, ... produkt_{n}: {{...}}}}.\n"
                "Kolejnosc produkt_1..N musi odpowiadac zaznaczeniu na liscie (od gory)."
            ),
            wraplength=760,
        ).pack(anchor="w", padx=12, pady=(12, 6))

        text_frame = ttk.Frame(sub, padding=(12, 0))
        text_frame.pack(fill="both", expand=True)
        paste_text = scrolledtext.ScrolledText(
            text_frame, height=18, wrap="word", font=("Consolas", 10)
        )
        paste_text.pack(fill="both", expand=True)

        btn_row = ttk.Frame(sub, padding=(12, 8))
        btn_row.pack(fill="x")

        def _paste_clipboard() -> None:
            try:
                data = dlg.clipboard_get()
            except tk.TclError:
                messagebox.showwarning(APP_TITLE, "Schowek jest pusty.", parent=sub)
                return
            paste_text.delete("1.0", "end")
            paste_text.insert("1.0", data)

        def _apply() -> None:
            raw = paste_text.get("1.0", "end").strip()
            try:
                parsed = parse_giga_translations_json(raw)
            except ValueError as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=sub)
                return
            expected = set(range(1, n + 1))
            got = set(parsed.keys())
            missing = sorted(expected - got)
            extra = sorted(got - expected)
            if missing or extra:
                parts: list[str] = []
                if missing:
                    parts.append(f"brakuje produkt_{missing[0]}" + (
                        f"…{missing[-1]}" if len(missing) > 1 else ""
                    ))
                if extra:
                    parts.append(f"nadmiarowe klucze produkt_{extra[0]}" + (
                        f"…{extra[-1]}" if len(extra) > 1 else ""
                    ))
                messagebox.showerror(
                    APP_TITLE,
                    f"JSON nie pasuje do {n} zaznaczonych produktow: "
                    + "; ".join(parts),
                    parent=sub,
                )
                return
            sub.destroy()
            giga_translation_btn.configure(state="disabled")
            giga_paste_btn.configure(state="disabled")
            set_status(f"Zapisuje GIGA tlumaczenia ({n} produktow)...")

            def work() -> None:
                shop, token = sc.load_session()
                saved_pids: list[int] = []
                errors: list[str] = []
                for i, row in enumerate(rows, 1):
                    pid = int(row["product_id"])
                    title = row.get("painting_title") or row.get("product_title") or str(pid)
                    try:
                        full = sc.get_product(shop, token, pid)
                        if not full:
                            raise ValueError(f"Nie znaleziono produktu id={pid}.")
                        baseline_by_locale: dict[str, list[str]] = {"pl": []}
                        baseline_by_locale["pl"] = load_current_paragraphs(
                            product_id=pid,
                            full_product=full,
                            locale="pl",
                            shop=shop,
                            token=token,
                        )
                        for lang in TRANSLATION_LANGS:
                            baseline_by_locale[lang] = load_current_paragraphs(
                                product_id=pid,
                                full_product=full,
                                locale=lang,
                                shop=shop,
                                token=token,
                            )
                        locales_paragraphs = build_locales_from_translation_batch(
                            baseline_by_locale=baseline_by_locale,
                            translation_batch=parsed[i],
                        )
                        res = apply_current_paragraphs_batch(
                            product_id=pid,
                            locales_paragraphs=locales_paragraphs,
                            logger=enqueue_log,
                        )
                        saved = res.get("saved_locales") or []
                        errs = res.get("errors") or []
                        if saved:
                            saved_pids.append(pid)
                            dlg.after(
                                0,
                                lambda p=pid, s=saved: _mark_product_after_save(
                                    p,
                                    saved_locales=s,
                                    translations_pasted=True,
                                ),
                            )
                        for e in errs:
                            loc = e.get("locale", "?")
                            errors.append(
                                f"{title} ({LOCALE_LABELS.get(loc, loc)}): {e.get('error')}"
                            )
                    except Exception as exc:
                        errors.append(f"{title}: {exc}")

                def done() -> None:
                    _sync_marks_from_disk()
                    if saved_pids:
                        show_toast(
                            dlg,
                            f"GIGA: zapisano {len(saved_pids)}/{n} produktow",
                            duration_ms=2200,
                        )
                    msg = f"Zapisano tlumaczenia dla {len(saved_pids)} z {n} produktow."
                    if errors:
                        msg += "\n\nBledy:\n" + "\n".join(f"- {e}" for e in errors[:12])
                        if len(errors) > 12:
                            msg += f"\n… i {len(errors) - 12} wiecej (patrz log)."
                    set_status(msg.split("\n")[0])
                    if errors or len(saved_pids) < n:
                        messagebox.showwarning(APP_TITLE, msg, parent=dlg)
                    else:
                        messagebox.showinfo(APP_TITLE, msg, parent=dlg)
                    row_after = _selected_row()
                    if row_after and int(row_after.get("product_id") or 0) in saved_pids:
                        _fetch_full_product(row_after, _display_current_description)
                    _update_prompt_btns()

                dlg.after(0, done)

            threading.Thread(target=work, daemon=True).start()

        ttk.Button(btn_row, text="Wklej ze schowka", command=_paste_clipboard).pack(side="left")
        ttk.Button(btn_row, text="Zastosuj", command=_apply).pack(side="right")
        ttk.Button(btn_row, text="Anuluj", command=sub.destroy).pack(side="right", padx=(0, 8))
        sub.bind("<Escape>", lambda _e: sub.destroy())
        paste_text.focus_set()

    def _update_para_edit_btns() -> None:
        if not para_edit_btns:
            return
        idx = state["edit_paragraph_idx"]
        old_paras = _old_paragraphs_list()
        pl_paras = (
            state["draft_old_paragraphs"].get("pl")
            or state["baseline_paragraphs"].get("pl")
            or []
        )
        n = min(4, max(len(old_paras), len(pl_paras), 3))
        prev = state["previews"].get(state.get("locale") or "pl")
        changed = set(prev.get("changed_indices") or []) if prev else set()
        baseline = state["baseline_paragraphs"].get(state.get("locale") or "pl", [])
        draft = state["draft_old_paragraphs"].get(state.get("locale") or "pl", baseline)

        for i, btn in para_edit_btns.items():
            suffix = ""
            if i in changed:
                suffix = " *"
            elif (
                draft
                and baseline
                and i < len(draft)
                and i < len(baseline)
                and _norm_paragraph(draft[i]) != _norm_paragraph(baseline[i])
            ):
                suffix = " !"
            btn.configure(text=f"{i + 1}{suffix}")
            btn.state(["disabled"] if i >= n else ["!disabled"])
            btn.state(["!pressed"] if i != idx else ["pressed"])
        _update_prompt_btns()

    def _show_paragraph_editors() -> None:
        idx = state["edit_paragraph_idx"]
        old_paras = _old_paragraphs_list()
        old_body = old_paras[idx] if idx < len(old_paras) else ""
        _set_preview_text(old_text, old_body, readonly=False)
        old_frame.configure(text=f"Obecny opis — akapit {idx + 1}")

        if state.get("llm_item"):
            new_paras = _new_paragraphs_list()
            new_body = new_paras[idx] if idx < len(new_paras) else ""
            _set_preview_text(new_text, new_body, readonly=False)
            prev = state["previews"].get(state.get("locale") or "pl")
            changed = set(prev.get("changed_indices") or []) if prev else set()
            ch = " [ZMIANA]" if idx in changed else ""
            new_frame.configure(text=f"Po zmianie — akapit {idx + 1}{ch}")
        else:
            _set_preview_text(
                new_text,
                "(po analizie JSON — prawa kolumna pokaze wersje po zmianie)",
                readonly=True,
            )
            new_frame.configure(text="Po zmianie (mozna edytowac)")

        _update_para_edit_btns()
        _update_save_old_btn()
        _update_prompt_btns()

    def _select_edit_paragraph(idx: int) -> None:
        _commit_old_paragraph_field()
        _commit_new_paragraph_field()
        state["edit_paragraph_idx"] = max(0, min(int(idx), 3))
        state["paragraph_index"].set(state["edit_paragraph_idx"] + 1)
        _show_paragraph_editors()
        if (
            state.get("llm_item")
            and state.get("full_product")
            and state["mode"].get() == "replace_paragraph"
        ):
            _rebuild_preview()

    def _set_old_paragraphs_list(paragraphs: list[str]) -> None:
        locale = state.get("locale") or "pl"
        state["draft_old_paragraphs"][locale] = list(paragraphs)[:4]
        _show_paragraph_editors()

    def _set_new_paragraphs_list(paragraphs: list[str]) -> None:
        locale = state.get("locale") or "pl"
        state["edited_paragraphs"][locale] = list(paragraphs)[:4]
        if state.get("llm_item"):
            _show_paragraph_editors()

    def _stash_locale_edits() -> None:
        _commit_old_paragraph_field()
        _commit_new_paragraph_field()

    def _dirty_old_locales() -> dict[str, list[str]]:
        _stash_locale_edits()
        out: dict[str, list[str]] = {}
        for loc, draft in state["draft_old_paragraphs"].items():
            baseline = _baseline_for_locale(loc)
            if baseline is None:
                continue
            if not _paragraphs_equal(draft, baseline) and len(draft) >= 3:
                out[loc] = draft
        return out

    def _update_save_old_btn() -> None:
        locale = state.get("locale") or "pl"
        baseline = state["baseline_paragraphs"].get(locale)
        if baseline is None or not state.get("full_product"):
            save_old_btn.configure(state="disabled")
            save_all_old_btn.configure(state="disabled")
            return
        try:
            current = _old_paragraphs_list()
        except Exception:
            save_old_btn.configure(state="disabled")
            save_all_old_btn.configure(state="disabled")
            return
        dirty = not _paragraphs_equal(current, baseline)
        save_old_btn.configure(state="normal" if dirty else "disabled")
        any_dirty = bool(_dirty_old_locales())
        save_all_old_btn.configure(state="normal" if any_dirty else "disabled")

    def _on_old_text_changed(_event: tk.Event | None = None) -> None:
        _commit_old_paragraph_field()
        _update_save_old_btn()
        _update_para_edit_btns()
        _update_prompt_btns()

    old_text.bind("<KeyRelease>", _on_old_text_changed)

    def _on_new_text_changed(_event: tk.Event | None = None) -> None:
        _commit_new_paragraph_field()
        _update_para_edit_btns()

    new_text.bind("<KeyRelease>", _on_new_text_changed)

    def _set_old_text_content(paragraphs: list[str], *, changed: set[int] | None = None) -> None:
        _set_old_paragraphs_list(paragraphs)

    def _mode() -> UpdateMode:
        v = state["mode"].get()
        if v in ("replace_all", "replace_paragraph", "add_paragraph"):
            return v  # type: ignore[return-value]
        return "replace_all"

    def _paragraph_idx() -> int:
        try:
            return max(0, int(state["paragraph_index"].get()) - 1)
        except (TypeError, ValueError):
            return 0

    def _on_mode_changed() -> None:
        if state.get("llm_item") and state.get("full_product"):
            _rebuild_preview()

    def _selected_row() -> dict[str, Any] | None:
        sel = tree.selection()
        if not sel:
            return None
        return state["row_by_iid"].get(sel[0])

    def _selected_rows() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for iid in tree.selection():
            row = state["row_by_iid"].get(iid)
            if row:
                rows.append(row)
        return rows

    def _selected_pids() -> list[int]:
        pids: list[int] = []
        for row in _selected_rows():
            try:
                pid = int(row.get("product_id") or 0)
            except (TypeError, ValueError):
                continue
            if pid > 0:
                pids.append(pid)
        return pids

    def _column_name_at(event: tk.Event) -> str | None:
        if tree.identify_region(event.x, event.y) != "cell":
            return None
        col_id = tree.identify_column(event.x)
        try:
            col_idx = int(str(col_id).lstrip("#")) - 1
        except (TypeError, ValueError):
            return None
        if col_idx < 0 or col_idx >= len(cols):
            return None
        return cols[col_idx]

    def _set_do_tlum_marks(pids: list[int], *, marked: bool) -> None:
        if not pids:
            return
        set_description_do_tlumaczenia_marks_batch(pids, marked=marked)
        marks = state["do_tlum_marks"]
        if marked:
            marks.update(pids)
        else:
            marks -= set(pids)
        _refresh_tree(preserve_pids=set(pids))
        action = "Oznaczono" if marked else "Odznaczono"
        show_toast(dlg, f"{action}: do tlumaczenia ({len(pids)})", duration_ms=1200)

    def _toggle_do_tlum_marks(pids: list[int]) -> None:
        if not pids:
            return
        marks = state["do_tlum_marks"]
        marked = not all(pid in marks for pid in pids)
        _set_do_tlum_marks(pids, marked=marked)

    def _set_from_image_marks(pids: list[int], *, marked: bool) -> None:
        if not pids:
            return
        set_description_from_image_marks_batch(pids, marked=marked)
        marks = state["from_image_marks"]
        if marked:
            marks.update(pids)
        else:
            marks -= set(pids)
        _refresh_tree(preserve_pids=set(pids))
        _update_llm_mark_btns()
        action = "Oznaczono" if marked else "Odznaczono"
        show_toast(dlg, f"{action}: z obrazu ({len(pids)})", duration_ms=1200)

    def _toggle_from_image_marks(pids: list[int]) -> None:
        if not pids:
            return
        marks = state["from_image_marks"]
        marked = not all(pid in marks for pid in pids)
        _set_from_image_marks(pids, marked=marked)

    def _toggle_from_image_mark_btn() -> None:
        pids = _selected_pids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=dlg)
            return
        _toggle_from_image_marks(pids)

    def _set_bez_16_marks(pids: list[int], *, marked: bool) -> None:
        if not pids:
            return
        set_description_bez_16_marks_batch(pids, marked=marked)
        marks = state["bez_16_marks"]
        if marked:
            marks.update(pids)
        else:
            marks -= set(pids)
        _refresh_tree(preserve_pids=set(pids))
        _update_llm_mark_btns()
        action = "Oznaczono" if marked else "Odznaczono"
        show_toast(dlg, f"{action}: Bez 1-6 ({len(pids)})", duration_ms=1200)

    def _toggle_bez_16_marks(pids: list[int]) -> None:
        if not pids:
            return
        marks = state["bez_16_marks"]
        marked = not all(pid in marks for pid in pids)
        _set_bez_16_marks(pids, marked=marked)

    def _toggle_bez_16_mark_btn() -> None:
        pids = _selected_pids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=dlg)
            return
        _toggle_bez_16_marks(pids)

    def _set_gpt_marks(pids: list[int], *, marked: bool) -> None:
        if not pids:
            return
        set_description_gpt_translation_marks_batch(pids, marked=marked)
        marks = state["gpt_marks"]
        if marked:
            marks.update(pids)
        else:
            marks -= set(pids)
        _refresh_tree(preserve_pids=set(pids))
        _update_llm_mark_btns()
        action = "Oznaczono" if marked else "Odznaczono"
        show_toast(dlg, f"{action}: tlum. GPT ({len(pids)})", duration_ms=1200)

    def _set_sonnet_marks(pids: list[int], *, marked: bool) -> None:
        if not pids:
            return
        set_description_sonnet_translation_marks_batch(pids, marked=marked)
        marks = state["sonnet_marks"]
        if marked:
            marks.update(pids)
        else:
            marks -= set(pids)
        _refresh_tree(preserve_pids=set(pids))
        _update_llm_mark_btns()
        action = "Oznaczono" if marked else "Odznaczono"
        show_toast(dlg, f"{action}: tlum. SONN ({len(pids)})", duration_ms=1200)

    def _toggle_gpt_marks(pids: list[int]) -> None:
        if not pids:
            return
        marks = state["gpt_marks"]
        marked = not all(pid in marks for pid in pids)
        _set_gpt_marks(pids, marked=marked)

    def _toggle_sonnet_marks(pids: list[int]) -> None:
        if not pids:
            return
        marks = state["sonnet_marks"]
        marked = not all(pid in marks for pid in pids)
        _set_sonnet_marks(pids, marked=marked)

    def _toggle_do_tlum_mark_btn() -> None:
        pids = _selected_pids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=dlg)
            return
        _toggle_do_tlum_marks(pids)

    def _toggle_gpt_mark_btn() -> None:
        pids = _selected_pids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=dlg)
            return
        _toggle_gpt_marks(pids)

    def _toggle_sonnet_mark_btn() -> None:
        pids = _selected_pids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=dlg)
            return
        _toggle_sonnet_marks(pids)

    def _update_llm_mark_btns() -> None:
        pids = _selected_pids()
        n = len(pids)
        if n <= 0:
            do_tlum_mark_btn.configure(state="disabled", text="do tlum.")
            gpt_mark_btn.configure(state="disabled", text="tlum. GPT")
            sonn_mark_btn.configure(state="disabled", text="tlum. SONN")
            from_image_mark_btn.configure(state="disabled", text="z obrazu")
            bez_16_mark_btn.configure(state="disabled", text="Bez 1-6")
            return
        do_tlum_marks = state["do_tlum_marks"]
        gpt_marks = state["gpt_marks"]
        sonn_marks = state["sonnet_marks"]
        from_image_marks = state["from_image_marks"]
        bez_16_marks = state["bez_16_marks"]
        if all(pid in do_tlum_marks for pid in pids):
            do_tlum_mark_btn.configure(state="normal", text=f"Odznacz do tlum. ({n})")
        else:
            do_tlum_mark_btn.configure(state="normal", text=f"Oznacz do tlum. ({n})")
        if all(pid in gpt_marks for pid in pids):
            gpt_mark_btn.configure(state="normal", text=f"Odznacz GPT ({n})")
        else:
            gpt_mark_btn.configure(state="normal", text=f"Oznacz GPT ({n})")
        if all(pid in sonn_marks for pid in pids):
            sonn_mark_btn.configure(state="normal", text=f"Odznacz SONN ({n})")
        else:
            sonn_mark_btn.configure(state="normal", text=f"Oznacz SONN ({n})")
        if all(pid in from_image_marks for pid in pids):
            from_image_mark_btn.configure(state="normal", text=f"Odznacz z obrazu ({n})")
        else:
            from_image_mark_btn.configure(state="normal", text=f"Oznacz z obrazu ({n})")
        if all(pid in bez_16_marks for pid in pids):
            bez_16_mark_btn.configure(state="normal", text=f"Odznacz Bez 1-6 ({n})")
        else:
            bez_16_mark_btn.configure(state="normal", text=f"Oznacz Bez 1-6 ({n})")

    def _update_mark_btn() -> None:
        row = _selected_row()
        if not row:
            mark_btn.configure(state="disabled", text="Oznacz: opis po aktualizacji")
            flag_btn.configure(state="disabled", text="Ustaw flage: tu skonczylem")
            _update_llm_mark_btns()
            return
        pid = int(row["product_id"])
        if pid in state["updated_marks"]:
            mark_btn.configure(
                state="normal",
                text="Odznacz «opis po aktualizacji»",
            )
        else:
            mark_btn.configure(
                state="normal",
                text="Oznacz: opis po aktualizacji",
            )
        resume_pid = state.get("resume_flag_pid")
        if resume_pid == pid:
            flag_btn.configure(state="normal", text="Usun flage pozycji")
        else:
            flag_btn.configure(state="normal", text="Ustaw flage: tu skonczylem")
        _update_llm_mark_btns()
        _update_prompt_btns()

    def _toggle_updated_mark(*, product_id: int | None = None) -> None:
        row = _selected_row()
        pid = product_id if product_id is not None else (int(row["product_id"]) if row else 0)
        if not pid:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        marked = toggle_description_update_mark(pid)
        if marked:
            state["updated_marks"].add(pid)
            state["pl_pending_marks"].discard(pid)
        else:
            state["updated_marks"].discard(pid)
        _refresh_tree(preserve_pids={pid})
        _update_mark_btn()
        action = "Oznaczono" if marked else "Odznaczono"
        show_toast(dlg, f"{action}: opis po aktualizacji", duration_ms=1200)

    def _toggle_resume_flag(*, product_id: int | None = None) -> None:
        row = _selected_row()
        pid = product_id if product_id is not None else (int(row["product_id"]) if row else 0)
        if not pid:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        flagged = toggle_description_resume_flag(pid)
        state["resume_flag_pid"] = load_description_resume_flag()
        _refresh_tree(preserve_pids={pid})
        _update_mark_btn()
        if flagged:
            show_toast(dlg, f"Flaga: {DESCRIPTION_RESUME_FLAG_LABEL}", duration_ms=1400)
        else:
            show_toast(dlg, "Usunieto flage pozycji", duration_ms=1200)

    def _row_sort_key(row: dict[str, Any]) -> tuple[str, ...]:
        pid = int(row.get("product_id") or 0)
        is_marked = pid in state["updated_marks"]
        status = CHECKMARK_TREE_LABEL if is_marked else ""
        has_variant = product_has_filled_compare_versions(state["compare_versions"], pid)
        variant_status = CHECKMARK_TREE_LABEL if has_variant else ""
        gpt_status = CHECKMARK_TREE_LABEL if pid in state["gpt_marks"] else ""
        sonn_status = CHECKMARK_TREE_LABEL if pid in state["sonnet_marks"] else ""
        from_image_status = CHECKMARK_TREE_LABEL if pid in state["from_image_marks"] else ""
        bez_16_status = CHECKMARK_TREE_LABEL if pid in state["bez_16_marks"] else ""
        do_tlum_status = CHECKMARK_TREE_LABEL if pid in state["do_tlum_marks"] else ""
        surname = (row.get("surname") or "").strip().lower()
        firstname = (row.get("firstname") or "").strip().lower()
        artist = (row.get("artist") or "").strip().lower()
        painting = (row.get("painting_title") or "").strip().lower()
        handle = (row.get("handle") or "").strip().lower()
        col = state.get("sort_col") or "artist"
        if col == "desc_status":
            return (status.lower(), surname, firstname, painting, handle)
        if col == "compare_status":
            return (variant_status.lower(), surname, firstname, painting, handle)
        if col == "do_tlum":
            return (do_tlum_status.lower(), surname, firstname, painting, handle)
        if col == "tlum_gpt":
            return (gpt_status.lower(), surname, firstname, painting, handle)
        if col == "tlum_sonn":
            return (sonn_status.lower(), surname, firstname, painting, handle)
        if col == "z_obrazu":
            return (from_image_status.lower(), surname, firstname, painting, handle)
        if col == "bez_16":
            return (bez_16_status.lower(), surname, firstname, painting, handle)
        if col == "artist":
            return (*product_catalog_sort_key(row), handle)
        return (artist, painting, handle)

    def _refresh_tree(
        *,
        preserve_selection: int | None = None,
        preserve_pids: set[int] | None = None,
    ) -> None:
        keep_pids: set[int] = set(preserve_pids or ())
        if preserve_selection is not None:
            keep_pids.add(int(preserve_selection))
        if not keep_pids:
            keep_pids = set(_selected_pids())

        tree.delete(*tree.get_children())
        state["row_by_iid"].clear()
        q = filter_var.get().strip().lower()
        shown = 0
        marked_total = 0
        pl_pending_total = 0
        do_tlum_total = 0
        selected_iids: list[str] = []
        visible_rows: list[dict[str, Any]] = []

        for row in state["rows"]:
            pid = int(row.get("product_id") or 0)
            is_marked = pid in state["updated_marks"]
            is_pl_pending = pid in state["pl_pending_marks"]
            is_from_image = pid in state["from_image_marks"]
            has_do_tlum = pid in state["do_tlum_marks"]
            if is_marked:
                marked_total += 1
            if is_pl_pending:
                pl_pending_total += 1
            if has_do_tlum:
                do_tlum_total += 1
            if not _row_matches_filters(
                is_marked=is_marked,
                is_pl_pending=is_pl_pending,
                is_from_image=is_from_image,
                has_do_tlum=has_do_tlum,
            ):
                continue
            blob = " ".join(
                [
                    str(row.get("surname") or ""),
                    str(row.get("firstname") or ""),
                    str(row.get("artist") or ""),
                    str(row.get("painting_title") or ""),
                    str(row.get("handle") or ""),
                    str(row.get("image_filename") or ""),
                ]
            ).lower()
            if q and q not in blob:
                continue
            visible_rows.append(row)

        visible_rows.sort(key=_row_sort_key, reverse=bool(state.get("sort_reverse")))

        resume_pid = state.get("resume_flag_pid")
        try:
            resume_pid = int(resume_pid) if resume_pid else None
        except (TypeError, ValueError):
            resume_pid = None

        for row in visible_rows:
            pid = int(row.get("product_id") or 0)
            is_marked = pid in state["updated_marks"]
            is_pl_pending = pid in state["pl_pending_marks"]
            is_flagged = resume_pid is not None and pid == resume_pid
            has_compare = (
                not is_marked
                and not is_pl_pending
                and product_has_filled_compare_versions(state["compare_versions"], pid)
            )
            status = CHECKMARK_TREE_LABEL if is_marked else ""
            has_variant = product_has_filled_compare_versions(state["compare_versions"], pid)
            variant_cell = CHECKMARK_TREE_LABEL if has_variant else ""
            gpt_cell = CHECKMARK_TREE_LABEL if pid in state["gpt_marks"] else ""
            sonn_cell = CHECKMARK_TREE_LABEL if pid in state["sonnet_marks"] else ""
            from_image_cell = CHECKMARK_TREE_LABEL if pid in state["from_image_marks"] else ""
            bez_16_cell = CHECKMARK_TREE_LABEL if pid in state["bez_16_marks"] else ""
            do_tlum_cell = CHECKMARK_TREE_LABEL if pid in state["do_tlum_marks"] else ""
            flag_cell = RESUME_FLAG_TREE_LABEL if is_flagged else ""
            if is_marked and is_flagged:
                tags = ("updated_resume",)
            elif is_marked:
                tags = ("updated",)
            elif is_pl_pending and is_flagged:
                tags = ("pl_pending_resume",)
            elif is_pl_pending:
                tags = ("pl_pending",)
            elif has_compare and is_flagged:
                tags = ("compare_resume",)
            elif has_compare:
                tags = ("compare_unmarked",)
            elif is_flagged:
                tags = ("resume_flag",)
            else:
                tags = ()
            iid = tree.insert(
                "",
                "end",
                values=(
                    flag_cell,
                    status,
                    variant_cell,
                    do_tlum_cell,
                    gpt_cell,
                    sonn_cell,
                    from_image_cell,
                    bez_16_cell,
                    row.get("artist", ""),
                    row.get("painting_title", ""),
                    row.get("handle", ""),
                    row.get("image_filename", ""),
                ),
                tags=tags,
            )
            state["row_by_iid"][iid] = row
            shown += 1
            if pid in keep_pids:
                selected_iids.append(iid)

        if not selected_iids and resume_pid is not None:
            for iid, row in state["row_by_iid"].items():
                if int(row.get("product_id") or 0) == resume_pid:
                    selected_iids = [iid]
                    break

        if selected_iids:
            existing = [iid for iid in selected_iids if tree.exists(iid)]
            if existing:
                tree.selection_set(existing)
                tree.see(existing[0])

        flag_note = ""
        if resume_pid is not None:
            flag_note = f"  |  Flaga: pid {resume_pid}"
        total_rows = len(state["rows"])
        progress_note = (
            f"  |  {format_description_update_progress(marked=marked_total, total=total_rows)}"
            if total_rows
            else ""
        )
        pl_pending_note = (
            f"  |  {format_description_pl_pending_progress(marked=pl_pending_total, total=total_rows)}"
            if total_rows and pl_pending_total
            else ""
        )
        do_tlum_note = (
            f"  |  {format_do_tlumaczenia_progress(marked=do_tlum_total, total=total_rows)}"
            if total_rows and do_tlum_total
            else ""
        )
        compare_unmarked = count_unmarked_products_with_compare_versions(
            state["rows"],
            state["compare_versions"],
            state["updated_marks"],
        )
        compare_note = (
            f"  |  {format_compare_versions_unmarked_note(count=compare_unmarked, total=total_rows)}"
            if total_rows
            else ""
        )
        state["_count_meta"] = {
            "shown": shown,
            "total_rows": total_rows,
            "progress_note": progress_note,
            "pl_pending_note": pl_pending_note,
            "do_tlum_note": do_tlum_note,
            "compare_note": compare_note,
            "flag_note": flag_note,
        }
        _sync_count_label()
        _update_mark_btn()

    def _sync_count_label() -> None:
        meta = state.get("_count_meta") or {}
        shown = int(meta.get("shown") or 0)
        total_rows = int(meta.get("total_rows") or 0)
        n_selected = len(_selected_pids())
        selected_note = f"  |  zaznaczono: {n_selected}" if n_selected else ""
        count_var.set(
            f"{shown} / {total_rows} produkt(ow)"
            + str(meta.get("progress_note") or "")
            + str(meta.get("pl_pending_note") or "")
            + str(meta.get("do_tlum_note") or "")
            + str(meta.get("compare_note") or "")
            + str(meta.get("flag_note") or "")
            + selected_note
        )

    def _mark_selected_after_save(
        *,
        saved_locales: list[str],
        translations_pushed: bool = False,
        translations_pasted: bool = False,
    ) -> None:
        product = _selected_product_row()
        if not product:
            return
        try:
            pid = int(product["product_id"])
        except (TypeError, ValueError):
            return
        if not pid:
            return
        _mark_product_after_save(
            pid,
            saved_locales=saved_locales,
            translations_pushed=translations_pushed,
            translations_pasted=translations_pasted,
        )

    def _load_products() -> None:
        progress_var.set("Pobieram produkty...")
        refresh_btn.configure(state="disabled")

        def work() -> None:
            try:
                rows = load_product_catalog_rows(
                    logger=enqueue_log,
                    on_progress=lambda s: dlg.after(0, lambda m=s: progress_var.set(m)),
                )
            except Exception as exc:
                dlg.after(0, lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg))
                dlg.after(0, lambda: progress_var.set("Blad pobierania."))
                dlg.after(0, lambda: refresh_btn.configure(state="normal"))
                return

            def done() -> None:
                state["rows"] = rows
                state["updated_marks"] = load_description_update_marks()
                state["pl_pending_marks"] = load_description_pl_pending_marks()
                state["gpt_marks"] = load_description_gpt_translation_marks()
                state["sonnet_marks"] = load_description_sonnet_translation_marks()
                state["do_tlum_marks"] = load_description_do_tlumaczenia_marks()
                state["bez_16_marks"] = load_description_bez_16_marks()
                _refresh_tree()
                progress_var.set(f"Gotowe — {len(rows)} produkt(ow).")
                refresh_btn.configure(state="normal")
                set_status(f"Aktualizuj opis: {len(rows)} produktow.")

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _display_current_description() -> None:
        """Pokazuje akapity z Shopify bez JSON (lewa kolumna)."""
        product = state["selected_product"]
        full = state["full_product"]
        if not product or not full:
            return
        locale = state["locale"]
        try:
            shop, token = sc.load_session()
            paragraphs = load_current_paragraphs(
                product_id=int(product["product_id"]),
                full_product=full,
                locale=locale,
                shop=shop,
                token=token,
            )
        except Exception as exc:
            preview_note.set(f"Blad odczytu opisu: {exc}")
            _set_preview_text(old_text, "", readonly=False)
            save_old_btn.configure(state="disabled")
            save_all_old_btn.configure(state="disabled")
            return

        title = (product.get("painting_title") or product.get("product_title") or "").strip()
        state["baseline_paragraphs"][locale] = list(paragraphs)
        _discard_spurious_draft(locale)
        draft = state["draft_old_paragraphs"].get(locale)
        display = draft if draft is not None else paragraphs
        if paragraphs:
            _set_old_text_content(display)
            preview_note.set(
                f"{LOCALE_LABELS.get(locale, locale)} — {title}: "
                f"{len(paragraphs)} akapit(ow) w Shopify. Mozesz edytowac lewa kolumne "
                f"lub wkleic JSON, aby zobaczyc podglad zmian."
            )
        else:
            _set_old_text_content([])
            preview_note.set(f"{LOCALE_LABELS.get(locale, locale)} — {title}: brak akapitow w opisie.")

        if not state.get("llm_item"):
            _set_preview_text(
                new_text,
                "(po analizie JSON — prawa kolumna pokaze wersje po zmianie)",
                readonly=True,
            )
            apply_btn.configure(state="disabled")

    def _on_tree_select(_event: tk.Event | None = None) -> None:
        row = _selected_row()
        prev_row = state.get("selected_product")
        prev_pid = int(prev_row.get("product_id") or 0) if prev_row else 0
        new_pid = int(row.get("product_id") or 0) if row else 0
        state["selected_product"] = row
        if not row:
            state["compare_open_pid"] = None
            state["full_product"] = None
            _set_preview_text(old_text, "", readonly=False)
            _set_preview_text(new_text, "", readonly=True)
            preview_note.set("Kliknij produkt na liscie — wczytam obecny opis z Shopify.")
            apply_btn.configure(state="disabled")
            save_old_btn.configure(state="disabled")
            save_all_old_btn.configure(state="disabled")
            state["baseline_paragraphs"] = {}
            state["draft_old_paragraphs"] = {}
            state["edit_paragraph_idx"] = 0
            state["paragraph_index"].set(1)
            _update_para_edit_btns()
            _update_prompt_btns()
            _update_mark_btn()
            _sync_count_label()
            return

        if new_pid != prev_pid and _auto_copy_prompt_enabled():
            _copy_new_description_prompt(silent=True)

        if _full_product_matches_row(row):
            _update_mark_btn()
            _update_prompt_btns()
            _sync_count_label()
            return

        if new_pid != prev_pid:
            state["compare_open_pid"] = None
        state["full_product"] = None
        preview_note.set("Pobieram opis z Shopify...")
        _set_preview_text(old_text, _LOADING_TEXT, readonly=False)
        _set_preview_text(
            new_text,
            "(po analizie JSON — prawa kolumna pokaze wersje po zmianie)",
            readonly=True,
        )
        apply_btn.configure(state="disabled")
        save_old_btn.configure(state="disabled")
        save_all_old_btn.configure(state="disabled")
        match_var.set("")
        state["baseline_paragraphs"] = {}
        state["draft_old_paragraphs"] = {}
        state["edit_paragraph_idx"] = 0
        state["paragraph_index"].set(1)
        _update_prompt_btns()
        _update_mark_btn()
        _sync_count_label()

        def after_load() -> None:
            _display_current_description()
            if json_text.get("1.0", "end").strip():
                _analyze_json(quiet=True)
            row_after = _selected_row()
            if row_after:
                _try_open_compare_for_pid(int(row_after.get("product_id") or 0))

        _fetch_full_product(row, after_load)

    def _on_tree_double_click(event: tk.Event) -> str:
        item = tree.identify_row(event.y)
        if not item:
            return ""
        row = state["row_by_iid"].get(item)
        if not row:
            return ""
        tree.selection_set(item)
        tree.focus(item)
        tree.see(item)
        _schedule_compare_open_for_row(row)
        return "break"

    def _copy_selected_image() -> None:
        row = _selected_row()
        if not row:
            messagebox.showinfo(APP_TITLE, "Zaznacz produkt na liscie.", parent=dlg)
            return
        image_url = _product_image_url(row)
        pid = int(row.get("product_id") or 0)

        def work() -> None:
            nonlocal image_url
            try:
                if not image_url and pid:
                    shop, token = sc.load_session()
                    prod = sc.get_product(shop, token, pid)
                    img = prod.get("image") or {}
                    image_url = (img.get("src") or "").strip()
                    if not image_url:
                        for im in prod.get("images") or []:
                            src = (im.get("src") or "").strip()
                            if src:
                                image_url = src
                                break
                if not image_url:
                    raise ValueError("Brak grafiki glownej dla tego produktu.")
                copy_image_url_to_clipboard(image_url)
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                return
            dlg.after(
                0,
                lambda: show_toast(dlg, "Grafika skopiowana do schowka", duration_ms=1600),
            )

        threading.Thread(target=work, daemon=True, name="copy-product-image").start()

    def _on_tree_context_menu(event: tk.Event) -> None:
        item = tree.identify_row(event.y)
        if item:
            if item not in tree.selection():
                tree.selection_set(item)
            tree.focus(item)
            tree.see(item)
            _on_tree_select()
        rows = _selected_rows()
        menu = tk.Menu(dlg, tearoff=0)
        if rows:
            pid = int(rows[0].get("product_id") or 0)
            menu.add_command(label="Kopiuj grafike", command=_copy_selected_image)
            if pid and pid == state.get("resume_flag_pid"):
                menu.add_command(
                    label="Usun flage pozycji",
                    command=lambda p=pid: _toggle_resume_flag(product_id=p),
                )
            else:
                menu.add_command(
                    label="Ustaw flage: tu skonczylem",
                    command=lambda p=pid: _toggle_resume_flag(product_id=pid),
                )
            menu.add_separator()
            n = len(rows)
            menu.add_command(
                label=(
                    "Oznacz: opis po aktualizacji"
                    if n == 1
                    else f"Oznacz opis — zaznaczone ({n})"
                ),
                command=lambda: _toggle_updated_mark(),
            )
            menu.add_command(
                label=(
                    "Oznacz tlum. GPT"
                    if n == 1
                    else f"Oznacz tlum. GPT ({n})"
                ),
                command=lambda: _set_gpt_marks(_selected_pids(), marked=True),
            )
            menu.add_command(
                label=(
                    "Odznacz tlum. GPT"
                    if n == 1
                    else f"Odznacz tlum. GPT ({n})"
                ),
                command=lambda: _set_gpt_marks(_selected_pids(), marked=False),
            )
            menu.add_command(
                label=(
                    "Oznacz tlum. SONN"
                    if n == 1
                    else f"Oznacz tlum. SONN ({n})"
                ),
                command=lambda: _set_sonnet_marks(_selected_pids(), marked=True),
            )
            menu.add_command(
                label=(
                    "Odznacz tlum. SONN"
                    if n == 1
                    else f"Odznacz tlum. SONN ({n})"
                ),
                command=lambda: _set_sonnet_marks(_selected_pids(), marked=False),
            )
            menu.add_command(
                label=(
                    "Oznacz z obrazu"
                    if n == 1
                    else f"Oznacz z obrazu ({n})"
                ),
                command=lambda: _set_from_image_marks(_selected_pids(), marked=True),
            )
            menu.add_command(
                label=(
                    "Odznacz z obrazu"
                    if n == 1
                    else f"Odznacz z obrazu ({n})"
                ),
                command=lambda: _set_from_image_marks(_selected_pids(), marked=False),
            )
            menu.add_command(
                label=(
                    "Oznacz Bez 1-6"
                    if n == 1
                    else f"Oznacz Bez 1-6 ({n})"
                ),
                command=lambda: _set_bez_16_marks(_selected_pids(), marked=True),
            )
            menu.add_command(
                label=(
                    "Odznacz Bez 1-6"
                    if n == 1
                    else f"Odznacz Bez 1-6 ({n})"
                ),
                command=lambda: _set_bez_16_marks(_selected_pids(), marked=False),
            )
            menu.add_separator()
            menu.add_command(
                label=(
                    "Oznacz do tlumaczenia"
                    if n == 1
                    else f"Oznacz do tlumaczenia ({n})"
                ),
                command=lambda: _set_do_tlum_marks(_selected_pids(), marked=True),
            )
            menu.add_command(
                label=(
                    "Odznacz do tlumaczenia"
                    if n == 1
                    else f"Odznacz do tlumaczenia ({n})"
                ),
                command=lambda: _set_do_tlum_marks(_selected_pids(), marked=False),
            )
        if menu.index("end") is None:
            return
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_tree_cell_release(event: tk.Event) -> None:
        col_name = _column_name_at(event)
        if col_name not in ("do_tlum", "tlum_gpt", "tlum_sonn", "z_obrazu", "bez_16"):
            return
        item = tree.identify_row(event.y)
        if not item:
            return
        if item not in tree.selection():
            tree.selection_set(item)
        pids = _selected_pids()
        if not pids:
            return
        if col_name == "do_tlum":
            _toggle_do_tlum_marks(pids)
        elif col_name == "tlum_gpt":
            _toggle_gpt_marks(pids)
        elif col_name == "tlum_sonn":
            _toggle_sonnet_marks(pids)
        elif col_name == "z_obrazu":
            _toggle_from_image_marks(pids)
        elif col_name == "bez_16":
            _toggle_bez_16_marks(pids)

    def _on_tree_ctrl_c(_event: tk.Event | None = None) -> str:
        if not _selected_row():
            return ""
        _copy_new_description_prompt()
        return "break"

    tree.bind("<<TreeviewSelect>>", _on_tree_select)
    tree.bind("<Double-1>", _on_tree_double_click, add="+")
    tree.bind("<Double-Button-1>", _on_tree_double_click, add="+")
    tree.bind("<Button-3>", _on_tree_context_menu)
    tree.bind("<ButtonRelease-1>", _on_tree_cell_release, add="+")
    for _seq in ("<Control-c>", "<Control-C>"):
        tree.bind(_seq, _on_tree_ctrl_c)

    def _format_paragraphs(paragraphs: list[str], changed: set[int] | None = None) -> str:
        lines: list[str] = []
        for i, p in enumerate(paragraphs):
            marker = " [ZMIANA]" if changed and i in changed else ""
            lines.append(f"--- Akapit {i + 1}{marker} ---\n{p}\n")
        return "\n".join(lines) if lines else "(brak akapitow)"

    def _rebuild_preview() -> None:
        product = state["selected_product"]
        llm_item = state["llm_item"]
        full = state["full_product"]
        if not product or not llm_item or not full:
            apply_btn.configure(state="disabled")
            return
        locale = state["locale"]
        try:
            shop, token = sc.load_session()
            prev = compute_locale_preview(
                product=product,
                full_product=full,
                llm_item=llm_item,
                mode=_mode(),
                paragraph_index=_paragraph_idx(),
                locale=locale,
                shop=shop,
                token=token,
            )
        except Exception as exc:
            preview_note.set(f"Blad podgladu: {exc}")
            apply_btn.configure(state="disabled")
            return

        state["previews"][locale] = prev
        new_p = list(prev.get("new_paragraphs") or [])
        if locale in state["edited_paragraphs"]:
            cur_list = state["edited_paragraphs"][locale]
            if _mode() != "replace_all" and len(cur_list) == len(new_p):
                merged = list(new_p)
                idx = state["edit_paragraph_idx"]
                if idx < len(cur_list) and (cur_list[idx] or "").strip():
                    merged[idx] = cur_list[idx]
                new_p = merged
        state["edited_paragraphs"][locale] = list(new_p)
        _show_paragraph_editors()

        changed = set(prev.get("changed_indices") or [])
        if changed:
            preview_note.set(
                f"{LOCALE_LABELS.get(locale, locale)}: zmienia sie akapit(y) "
                f"{', '.join(str(i + 1) for i in sorted(changed))} "
                f"(lacznie {len(new_p)} akapitow)."
            )
        else:
            preview_note.set(
                f"{LOCALE_LABELS.get(locale, locale)}: brak roznicy w akapitach "
                f"(tryb: {state['mode'].get()})."
            )
        apply_btn.configure(state="normal" if changed or _mode() == "add_paragraph" else "normal")

    def _switch_locale(loc: str) -> None:
        _stash_locale_edits()
        state["locale"] = loc
        for code, btn in lang_btns.items():
            btn.state(["!pressed"] if code != loc else ["pressed"])
        if state.get("llm_item") and state.get("full_product"):
            _rebuild_preview()
        elif state.get("full_product"):
            _display_current_description()
        _update_prompt_btns()

    for code in _LOCALES:
        btn = ttk.Button(
            lang_bar,
            text=code.upper(),
            width=4,
            command=lambda c=code: _switch_locale(c),
        )
        btn.pack(side="left", padx=2)
        lang_btns[code] = btn

    for i in range(4):
        btn = ttk.Button(
            para_row1,
            text=str(i + 1),
            width=5,
            command=lambda ix=i: _select_edit_paragraph(ix),
        )
        btn.pack(side="left", padx=2)
        para_edit_btns[i] = btn

    def _save_current_description() -> None:
        product = state["selected_product"]
        if not product:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        locale = state["locale"]
        _commit_old_paragraph_field()
        paragraphs = _old_paragraphs_list()
        if len(paragraphs) < 3:
            messagebox.showwarning(
                APP_TITLE,
                "Opis musi miec co najmniej 3 akapity.",
                parent=dlg,
            )
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Zapisac obecny opis ({LOCALE_LABELS.get(locale, locale)}) dla:\n"
            f"{product.get('product_title')}?",
            parent=dlg,
        ):
            return

        save_old_btn.configure(state="disabled")
        save_all_old_btn.configure(state="disabled")
        set_status("Zapisuje obecny opis w Shopify...")

        def work() -> None:
            try:
                res = apply_current_paragraphs_update(
                    product_id=int(product["product_id"]),
                    locale=locale,
                    paragraphs=paragraphs,
                    logger=enqueue_log,
                )
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                dlg.after(0, lambda: _update_save_old_btn())
                dlg.after(0, lambda: set_status("Blad zapisu obecnego opisu."))
                return

            def done() -> None:
                _mark_selected_after_save(saved_locales=[res["locale"]])
                enqueue_log(
                    f"[opis] Zapisano recznie id={res['product_id']} "
                    f"({res['locale']}, {res['paragraph_count']} akapitow)."
                )
                set_status("Obecny opis zapisany.")
                messagebox.showinfo(
                    APP_TITLE,
                    f"Zapisano obecny opis ({res['paragraph_count']} akapitow).\n{res['admin_url']}",
                    parent=dlg,
                )
                state["draft_old_paragraphs"].pop(locale, None)

                def after_save() -> None:
                    _display_current_description()
                    if state.get("llm_item"):
                        _rebuild_preview()

                _fetch_full_product(product, after_save)

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _save_all_current_descriptions(
        *,
        skip_confirm: bool = False,
        translations_pasted: bool = False,
    ) -> None:
        product = _selected_product_row()
        if not product:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        _save_locales_paragraphs(
            product,
            _dirty_old_locales(),
            skip_confirm=skip_confirm,
            translations_pasted=translations_pasted,
        )

    def _fetch_full_product(product: dict[str, Any], callback: Callable[[], None]) -> None:
        pid = int(product["product_id"])

        def work() -> None:
            try:
                shop, token = sc.load_session()
                full = sc.get_product(shop, token, pid)
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                return

            def done() -> None:
                state["full_product"] = full
                callback()

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _analyze_json(*, quiet: bool = False) -> None:
        product = _selected_row()
        if not product:
            if not quiet:
                messagebox.showwarning(APP_TITLE, "Wybierz produkt z listy.", parent=dlg)
            return
        raw = json_text.get("1.0", "end").strip()
        if not raw:
            if not quiet:
                messagebox.showwarning(APP_TITLE, "Wklej tablice JSON.", parent=dlg)
            return
        try:
            items = parse_batch_response_json(raw)
        except ValueError as exc:
            if not quiet:
                messagebox.showerror(APP_TITLE, f"JSON:\n{exc}", parent=dlg)
            match_var.set(f"Blad JSON: {exc}")
            state["llm_item"] = None
            apply_btn.configure(state="disabled")
            if state.get("full_product"):
                _display_current_description()
            return

        state["llm_items"] = items
        hit = match_json_entry_for_product(product, items)
        if not hit:
            match_var.set("Brak dopasowania — sprawdz pole 'plik' w JSON.")
            state["llm_item"] = None
            apply_btn.configure(state="disabled")
            if state.get("full_product"):
                _display_current_description()
            if not quiet:
                messagebox.showwarning(
                    APP_TITLE,
                    "Nie znaleziono wpisu JSON dla tego produktu.\n"
                    "Upewnij sie, ze pole 'plik' odpowiada nazwie glownej grafiki "
                    "lub tytulowi obrazu.",
                    parent=dlg,
                )
            return

        state["llm_item"] = hit
        state["edited_paragraphs"] = {}
        state["previews"] = {}
        state["edit_paragraph_idx"] = 0
        state["paragraph_index"].set(1)
        plik = (hit.get("plik") or "").strip()
        match_var.set(f"Dopasowano: {plik or '(plik)'}")
        state["selected_product"] = product

        def after_load() -> None:
            _rebuild_preview()

        if state.get("full_product"):
            after_load()
        else:
            _fetch_full_product(product, after_load)

    def _apply() -> None:
        product = state["selected_product"]
        llm_item = state["llm_item"]
        if not product or not llm_item:
            messagebox.showwarning(APP_TITLE, "Brak produktu lub JSON.", parent=dlg)
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Zapisac opis dla:\n{product.get('product_title')}\n\n"
            f"Tryb: {state['mode'].get()}?",
            parent=dlg,
        ):
            return

        locales_override: dict[str, list[str]] = {}
        _commit_new_paragraph_field()
        for loc in _LOCALES:
            if loc in state["edited_paragraphs"]:
                paras = state["edited_paragraphs"][loc]
                if len(paras) >= 3:
                    locales_override[loc] = paras
        cur = state["locale"]
        cur_list = state["edited_paragraphs"].get(cur) or _new_paragraphs_list()
        if cur_list and len(cur_list) >= 3:
            locales_override[cur] = cur_list

        apply_btn.configure(state="disabled")
        set_status("Zapisuje opis w Shopify...")

        def work() -> None:
            try:
                res = apply_description_update(
                    product_id=int(product["product_id"]),
                    product=product,
                    llm_item=llm_item,
                    mode=_mode(),
                    paragraph_index=_paragraph_idx(),
                    locales=locales_override or None,
                    logger=enqueue_log,
                )
            except Exception as exc:
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=dlg),
                )
                dlg.after(0, lambda: apply_btn.configure(state="normal"))
                dlg.after(0, lambda: set_status("Blad zapisu opisu."))
                return

            def done() -> None:
                _mark_selected_after_save(
                    saved_locales=res.get("saved_locales") or ["pl"],
                    translations_pushed=bool(res.get("translations_pushed")),
                )
                enqueue_log(
                    f"[opis] OK id={res['product_id']} — {res['paragraph_count']} akapitow "
                    f"({res['mode']})."
                )
                set_status("Opis zaktualizowany.")
                messagebox.showinfo(
                    APP_TITLE,
                    f"Zapisano opis ({res['paragraph_count']} akapitow).\n{res['admin_url']}",
                    parent=dlg,
                )
                apply_btn.configure(state="normal")

                def after_save() -> None:
                    _display_current_description()
                    if state.get("llm_item"):
                        _rebuild_preview()

                _fetch_full_product(product, after_save)

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _open_admin() -> None:
        row = _selected_row()
        if row and row.get("admin_url"):
            webbrowser.open(row["admin_url"])

    _on_mode_changed()
    _switch_locale("pl")
    _update_prompt_btns()
    _load_products()
    return dlg
