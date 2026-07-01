"""GUI: batch tytulow i roboczych opisow przez Gemini API."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from Komponenty._shared.gemini_client import (
    DEFAULT_BATCH_DELAY_S,
    DEFAULT_MODEL,
    GeminiAborted,
    gemini_api_key,
    gemini_api_key_hint,
    set_gemini_api_key,
)
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.dodajobraz.description_update import (
    load_product_catalog_rows,
    load_title_update_marks,
    product_catalog_sort_key,
    set_title_update_marks_batch,
    toggle_title_update_mark,
)

from .batch import BatchItemResult, prefetch_row_images, process_product_row
from .descriptions import (
    DescriptionVariantKey,
    ProductDescriptionDrafts,
    VARIANT_LABELS,
    format_akapity_compare_json,
    format_draft_display,
    merge_description_drafts,
    process_description_row,
)
from .prompts import GEMINI_CHAT_SESSION_START
from .storage import (
    load_description_drafts,
    load_title_drafts,
    save_description_drafts,
    save_title_drafts,
)

APP_TITLE = "Tytuły AI (Gemini)"
_STASH_SEP = "\n\n"


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 980, 720)
    root.minsize(760, 560)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Misc) -> None:
    shared: dict[str, object] = {
        "rows": [],
        "title_marks": set(),
        "title_drafts": load_title_drafts(),
        "description_drafts": load_description_drafts(),
    }

    top = ttk.Frame(host, padding=(12, 10))
    top.pack(fill="x")

    key_row = ttk.Frame(top)
    key_row.pack(fill="x")

    def _update_key_label() -> None:
        key_ok = bool(gemini_api_key())
        hint = gemini_api_key_hint()
        if key_ok:
            text = f"GEMINI_API_KEY: OK ({hint}, cursor-api/.env)"
            color = "#0a6"
        else:
            text = "GEMINI_API_KEY: BRAK — ustaw klucz API"
            color = "#c00"
        key_label.configure(text=text, foreground=color)

    key_label = ttk.Label(key_row, text="GEMINI_API_KEY: …")
    key_label.pack(side="left")
    ttk.Button(
        key_row,
        text="Zmien klucz API…",
        command=lambda: _show_gemini_key_dialog(host, on_saved=_update_key_label),
    ).pack(side="left", padx=(10, 0))
    _update_key_label()

    cfg = ttk.Frame(top)
    cfg.pack(fill="x", pady=(8, 0))
    ttk.Label(cfg, text="Model:").pack(side="left")
    ttk.Label(cfg, text=DEFAULT_MODEL, foreground="#0a6").pack(side="left", padx=(6, 16))
    model_var = tk.StringVar(value=DEFAULT_MODEL)
    ttk.Label(cfg, text="Przerwa miedzy obrazami (s):").pack(side="left")
    delay_var = tk.StringVar(value=str(DEFAULT_BATCH_DELAY_S))
    ttk.Entry(cfg, textvariable=delay_var, width=5).pack(side="left", padx=(6, 0))

    notebook = ttk.Notebook(host)
    notebook.pack(fill="both", expand=True, padx=0, pady=(0, 0))

    titles_tab = ttk.Frame(notebook, padding=0)
    desc_tab = ttk.Frame(notebook, padding=0)
    notebook.add(titles_tab, text="Tytuły")
    notebook.add(desc_tab, text="Opisy")

    loaders: list[Callable[[], None]] = []

    def _load_products(*, progress_set: Callable[[str], None], on_ready: Callable[[], None]) -> None:
        progress_set("Pobieram produkty...")

        def work() -> None:
            try:
                rows = load_product_catalog_rows(
                    on_progress=lambda s: host.after(0, lambda m=s: progress_set(m)),
                )
            except Exception as exc:
                host.after(0, lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=host))
                host.after(0, lambda: progress_set("Blad pobierania."))
                return

            def done() -> None:
                shared["rows"] = rows
                shared["title_marks"] = load_title_update_marks()
                progress_set(f"Gotowe — {len(rows)} produkt(ow).")
                on_ready()

            host.after(0, done)

        threading.Thread(target=work, daemon=True, name="tytulyai-load").start()

    _build_titles_tab(
        titles_tab,
        host,
        shared,
        model_var=model_var,
        delay_var=delay_var,
        register_loader=lambda fn: loaders.append(fn),
        load_products=_load_products,
    )
    _build_descriptions_tab(
        desc_tab,
        host,
        shared,
        model_var=model_var,
        delay_var=delay_var,
        register_loader=lambda fn: loaders.append(fn),
        load_products=_load_products,
    )

    for load_fn in loaders:
        load_fn()


def _build_titles_tab(
    parent: tk.Misc,
    host: tk.Misc,
    shared: dict[str, object],
    *,
    model_var: tk.StringVar,
    delay_var: tk.StringVar,
    register_loader: Callable[[Callable[[], None]], None],
    load_products: Callable[..., None],
) -> None:
    state: dict[str, object] = {
        "running": False,
    }

    list_frame = ttk.LabelFrame(
        parent,
        text="Produkty (Ctrl/Shift — wiele; generuj tytuly przez API)",
        padding=(10, 8),
    )
    list_frame.pack(fill="both", expand=True, padx=12, pady=(6, 6))

    filter_bar = ttk.Frame(list_frame)
    filter_bar.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar(value="")
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=32).pack(side="left", padx=(6, 8))
    title_status_var = tk.StringVar(value="wszystkie")
    ttk.Label(filter_bar, text="Status tytulu:").pack(side="left", padx=(4, 0))
    title_status_combo = ttk.Combobox(
        filter_bar,
        textvariable=title_status_var,
        values=("wszystkie", "zmienione", "niezmienione"),
        width=14,
        state="readonly",
    )
    title_status_combo.pack(side="left", padx=(6, 8))
    mark_btn = ttk.Button(
        filter_bar,
        text="Oznacz: tytul po aktualizacji",
        state="disabled",
    )
    mark_btn.pack(side="right", padx=(8, 0))
    count_var = tk.StringVar(value="(ladowanie...)")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="")
    ttk.Label(filter_bar, textvariable=progress_var, foreground="#444").pack(side="right")

    table_frame = ttk.Frame(list_frame)
    table_frame.pack(fill="both", expand=True)
    cols = ("surname", "firstname", "painting_title", "artist", "draft")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10, selectmode="extended")
    for c, label, w in (
        ("surname", "Nazwisko", 140),
        ("firstname", "Imie", 120),
        ("painting_title", "Tytul obrazu", 280),
        ("artist", "Artysta", 180),
        ("draft", "Tytul", 48),
    ):
        tree.heading(c, text=label)
        tree.column(c, width=w, anchor="w", stretch=(c == "painting_title"))
    tree.column("draft", anchor="center", stretch=False)
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    tree.tag_configure("title_updated", background="#e8f5e9", foreground="#1b5e20")
    tree.tag_configure("has_draft", background="#e3f2fd", foreground="#0d47a1")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    out_frame = ttk.LabelFrame(
        parent,
        text="Prompty do Cursora (robocze — zapisane lokalnie, kliknij produkt z ✓)",
        padding=(10, 6),
    )
    out_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))
    out_text = scrolledtext.ScrolledText(out_frame, height=8, wrap="word", font=("Consolas", 9))
    out_text.pack(fill="both", expand=True)

    bottom = ttk.Frame(parent, padding=(12, 8))
    bottom.pack(fill="x")
    gen_btn = ttk.Button(bottom, text="Generuj tytuly (Gemini API)", state="disabled")
    gen_btn.pack(side="right")
    copy_btn = ttk.Button(bottom, text="Kopiuj wyniki", state="disabled")
    copy_btn.pack(side="right", padx=(0, 8))
    save_btn = ttk.Button(bottom, text="Zapisz do pliku...", state="disabled")
    save_btn.pack(side="right", padx=(0, 8))
    refresh_btn = ttk.Button(bottom, text="Odswiez produkty")
    refresh_btn.pack(side="left")
    ttk.Button(
        bottom,
        text="Kopiuj prompt startowy (Gemini czat)",
        command=lambda: _copy_session_prompt(host),
    ).pack(side="left", padx=(8, 0))
    stop_btn = ttk.Button(bottom, text="Stop", state="disabled")
    stop_btn.pack(side="left", padx=(8, 0))

    stop_flag = {"stop": False}
    row_by_iid: dict[str, dict] = {}

    def _rows() -> list[dict]:
        rows = shared.get("rows")
        return rows if isinstance(rows, list) else []

    def _title_marks() -> set[int]:
        marks = shared.get("title_marks")
        return marks if isinstance(marks, set) else set()

    def _title_drafts() -> dict[int, BatchItemResult]:
        drafts = shared.get("title_drafts")
        return drafts if isinstance(drafts, dict) else {}

    def _draft_for_row(row: dict) -> BatchItemResult | None:
        pid = int(row.get("product_id") or 0)
        if not pid:
            return None
        return _title_drafts().get(pid)

    def _store_title_draft(result: BatchItemResult) -> None:
        drafts = _title_drafts()
        if result.product_id:
            drafts[result.product_id] = result
            shared["title_drafts"] = drafts
            save_title_drafts(drafts)

    def _selected_rows() -> list[dict]:
        out: list[dict] = []
        for iid in tree.selection():
            row = row_by_iid.get(iid)
            if row:
                out.append(row)
        return out

    def _selected_product_ids() -> list[int]:
        out: list[int] = []
        for row in _selected_rows():
            try:
                pid = int(row.get("product_id") or 0)
            except (TypeError, ValueError):
                continue
            if pid:
                out.append(pid)
        return out

    def _sync_local_title_marks(pids: list[int], *, marked: bool) -> None:
        marks = _title_marks()
        for pid in pids:
            if marked:
                marks.add(pid)
            else:
                marks.discard(pid)
        shared["title_marks"] = marks

    def _update_mark_btn() -> None:
        pids = _selected_product_ids()
        n = len(pids)
        if n == 0 or state["running"]:
            mark_btn.configure(state="disabled", text="Oznacz: tytul po aktualizacji")
            return
        marks = _title_marks()
        marked_count = sum(1 for pid in pids if pid in marks)
        if n == 1:
            if marked_count:
                mark_btn.configure(state="normal", text="Odznacz «tytul po aktualizacji»")
            else:
                mark_btn.configure(state="normal", text="Oznacz: tytul po aktualizacji")
        elif marked_count == n:
            mark_btn.configure(state="normal", text=f"Odznacz zaznaczone ({n})")
        else:
            mark_btn.configure(state="normal", text=f"Oznacz zaznaczone ({n})")

    def _set_title_marks(*, marked: bool) -> None:
        pids = _selected_product_ids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=host)
            return
        set_title_update_marks_batch(pids, marked=marked)
        _sync_local_title_marks(pids, marked=marked)
        _refresh_tree()
        _update_mark_btn()
        verb = "Oznaczono" if marked else "Odznaczono"
        suffix = f" ({len(pids)})" if len(pids) > 1 else ""
        show_toast(host, f"{verb}: tytul po aktualizacji{suffix}", duration_ms=1200)

    def _toggle_title_mark() -> None:
        pids = _selected_product_ids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=host)
            return
        if len(pids) == 1:
            marked = toggle_title_update_mark(pids[0])
            _sync_local_title_marks(pids, marked=marked)
        else:
            marks = _title_marks()
            all_marked = all(pid in marks for pid in pids)
            marked = not all_marked
            set_title_update_marks_batch(pids, marked=marked)
            _sync_local_title_marks(pids, marked=marked)
        _refresh_tree()
        _update_mark_btn()
        action = "Oznaczono" if marked else "Odznaczono"
        suffix = f" ({len(pids)})" if len(pids) > 1 else ""
        show_toast(host, f"{action}: tytul po aktualizacji{suffix}", duration_ms=1200)

    def _on_tree_context_menu(event: tk.Event) -> None:
        item = tree.identify_row(event.y)
        if item:
            if item not in tree.selection():
                tree.selection_set(item)
            tree.focus(item)
            tree.see(item)
            _on_tree_select()
        rows = _selected_rows()
        if not rows:
            return
        n = len(rows)
        menu = tk.Menu(host, tearoff=0)
        menu.add_command(
            label="Oznacz: tytul po aktualizacji" if n == 1 else f"Oznacz zaznaczone ({n})",
            command=lambda: _set_title_marks(marked=True),
        )
        menu.add_command(
            label="Odznacz «tytul po aktualizacji»" if n == 1 else f"Odznacz zaznaczone ({n})",
            command=lambda: _set_title_marks(marked=False),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    mark_btn.configure(command=_toggle_title_mark)

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        row_by_iid.clear()
        q = filter_var.get().strip().lower()
        status_filter = title_status_var.get().strip().lower()
        visible: list[dict] = []
        marks = _title_marks()
        drafts = _title_drafts()
        draft_count = sum(1 for d in drafts.values() if d.cursor_prompt)
        marked_total = 0
        unmarked_total = 0
        for row in _rows():
            pid = int(row.get("product_id") or 0)
            is_marked = pid in marks
            if is_marked:
                marked_total += 1
            else:
                unmarked_total += 1
            if status_filter == "zmienione" and not is_marked:
                continue
            if status_filter == "niezmienione" and is_marked:
                continue
            blob = " ".join(
                str(row.get(k) or "") for k in ("surname", "firstname", "artist", "painting_title")
            ).lower()
            if q and q not in blob:
                continue
            visible.append(row)
        visible.sort(key=product_catalog_sort_key)
        for row in visible:
            pid = int(row.get("product_id") or 0)
            tags: tuple[str, ...] = ()
            if pid in marks:
                tags = ("title_updated",)
            draft = drafts.get(pid)
            has_draft = bool(draft and draft.cursor_prompt)
            if has_draft:
                tags = tags + ("has_draft",)
            iid = tree.insert(
                "",
                "end",
                values=(
                    row.get("surname", ""),
                    row.get("firstname", ""),
                    row.get("painting_title", ""),
                    row.get("artist", ""),
                    "✓" if has_draft else "",
                ),
                tags=tags,
            )
            row_by_iid[iid] = row
        count_text = f"{len(visible)} / {len(_rows())} produkt(ow)"
        count_text += f"  |  zmienione: {marked_total}, do zmiany: {unmarked_total}"
        count_text += f"  |  robocze tytuly: {draft_count}"
        count_var.set(count_text)
        gen_btn.configure(state="normal" if visible and not state["running"] else "disabled")
        _update_mark_btn()

    def _show_drafts_in_output(rows: list[dict] | None = None) -> None:
        selected = rows if rows is not None else _selected_rows()
        drafts = _title_drafts()
        prompts: list[str] = []
        errors: list[str] = []
        warnings: list[str] = []
        for row in selected:
            pid = int(row.get("product_id") or 0)
            item = drafts.get(pid)
            if not item:
                continue
            if item.cursor_prompt:
                prompts.append(item.cursor_prompt)
            if item.warning:
                warnings.append(f"{item.painting_title}: {item.warning}")
            if item.error:
                errors.append(f"{item.painting_title}: {item.error}")
        out_text.delete("1.0", "end")
        if prompts:
            out_text.insert("1.0", _STASH_SEP.join(prompts))
        if warnings:
            out_text.insert(
                "end",
                ("\n\n--- KOLIZJE TYTULOW (sprawdz przed wdrozeniem) ---\n" if prompts else "")
                + "\n".join(warnings),
            )
        if errors:
            out_text.insert("end", ("\n\n--- BLEDY ---\n" if prompts or warnings else "") + "\n".join(errors))
        has_out = bool(prompts or errors or warnings)
        copy_btn.configure(state="normal" if has_out else "disabled")
        save_btn.configure(state="normal" if has_out else "disabled")

    def _on_tree_select(_event: tk.Event | None = None) -> None:
        gen_btn.configure(
            state="normal" if _selected_rows() and not state["running"] else "disabled",
        )
        _update_mark_btn()
        _show_drafts_in_output()

    def _append_results(results: list[BatchItemResult]) -> None:
        prompts = [r.cursor_prompt for r in results if r.cursor_prompt]
        errors = [f"{r.painting_title}: {r.error}" for r in results if r.error]
        warnings = [f"{r.painting_title}: {r.warning}" for r in results if r.warning]
        out_text.delete("1.0", "end")
        if prompts:
            out_text.insert("1.0", _STASH_SEP.join(prompts))
        if warnings:
            out_text.insert(
                "end",
                ("\n\n--- KOLIZJE TYTULOW (sprawdz przed wdrozeniem) ---\n" if prompts else "")
                + "\n".join(warnings),
            )
        if errors:
            out_text.insert("end", ("\n\n--- BLEDY ---\n" if prompts or warnings else "") + "\n".join(errors))
        has_out = bool(prompts or errors or warnings)
        copy_btn.configure(state="normal" if has_out else "disabled")
        save_btn.configure(state="normal" if has_out else "disabled")

    def _on_products_loaded() -> None:
        refresh_btn.configure(state="normal")
        _refresh_tree()

    def _load_products_click() -> None:
        refresh_btn.configure(state="disabled")
        gen_btn.configure(state="disabled")
        load_products(progress_set=progress_var.set, on_ready=_on_products_loaded)

    def _run_batch() -> None:
        rows = _selected_rows()
        if not rows:
            messagebox.showinfo(APP_TITLE, "Zaznacz co najmniej jeden produkt.", parent=host)
            return
        if not gemini_api_key():
            messagebox.showerror(
                APP_TITLE,
                "Dodaj GEMINI_API_KEY do cursor-api/.env\n"
                "(https://aistudio.google.com/apikey)",
                parent=host,
            )
            return
        try:
            delay_s = max(0.0, float(delay_var.get().replace(",", ".")))
        except ValueError:
            messagebox.showerror(APP_TITLE, "Nieprawidlowa przerwa (sekundy).", parent=host)
            return

        model = model_var.get().strip() or DEFAULT_MODEL
        stop_flag["stop"] = False
        state["running"] = True
        gen_btn.configure(state="disabled")
        refresh_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        out_text.delete("1.0", "end")

        def work() -> None:
            import time

            results: list[BatchItemResult] = []
            total = len(rows)

            def _prefetch_progress(done: int, count: int) -> None:
                host.after(
                    0,
                    lambda d=done, c=count: progress_var.set(f"Pobieram miniatury ({d}/{c})..."),
                )

            prefetch = prefetch_row_images(rows, on_progress=_prefetch_progress)

            for idx, row in enumerate(rows, start=1):
                if stop_flag["stop"]:
                    break
                title = str(row.get("painting_title") or "?")
                pf = prefetch.get(id(row))
                if pf and pf.error:
                    results.append(
                        BatchItemResult(
                            product_id=int(row.get("product_id") or 0),
                            artist=str(row.get("artist") or ""),
                            painting_title=title,
                            model_used="",
                            raw_response="",
                            cursor_prompt="",
                            error=pf.error,
                        ),
                    )
                    _store_title_draft(results[-1])
                    host.after(0, lambda r=list(results): _append_results(r))
                    host.after(0, _refresh_tree)
                    continue

                host.after(
                    0,
                    lambda i=idx, t=total, n=title: progress_var.set(f"Gemini ({i}/{t}): {n[:50]}..."),
                )
                img_bytes = pf.image_bytes if pf else None
                mime = pf.mime_type if pf else "image/jpeg"

                def _status(msg: str, *, _idx=idx, _total=total, _title=title) -> None:
                    host.after(
                        0,
                        lambda m=msg, i=_idx, t=_total, n=_title: progress_var.set(
                            f"Gemini ({i}/{t}): {n[:35]}... — {m}",
                        ),
                    )

                try:
                    result = process_product_row(
                        row,
                        model=model,
                        image_bytes=img_bytes,
                        mime_type=mime,
                        catalog_rows=_rows(),
                        on_status=_status,
                        should_abort=lambda: stop_flag["stop"],
                    )
                except GeminiAborted:
                    break
                results.append(result)
                _store_title_draft(result)
                host.after(0, lambda r=list(results): _append_results(r))
                host.after(0, _refresh_tree)
                if idx < total and delay_s > 0 and not stop_flag["stop"]:
                    time.sleep(delay_s)

            def done() -> None:
                state["running"] = False
                stop_btn.configure(state="disabled")
                refresh_btn.configure(state="normal")
                _refresh_tree()
                ok = sum(1 for r in results if r.cursor_prompt)
                err = sum(1 for r in results if r.error)
                progress_var.set(f"Koniec: {ok} OK, {err} bledow.")
                show_toast(host, f"Gemini: {ok} prompt(ow), {err} bled(ow)", duration_ms=2200)

            host.after(0, done)

        threading.Thread(target=work, daemon=True, name="tytulyai-batch").start()

    def _copy_results() -> None:
        payload = out_text.get("1.0", "end").strip()
        if not payload:
            return
        host.clipboard_clear()
        host.clipboard_append(payload)
        host.update()
        show_toast(host, "Skopiowano wyniki do schowka", duration_ms=1600)

    def _save_results() -> None:
        payload = out_text.get("1.0", "end").strip()
        if not payload:
            return
        path = filedialog.asksaveasfilename(
            title="Zapisz prompty",
            defaultextension=".txt",
            filetypes=[("Tekst", "*.txt"), ("Wszystkie", "*.*")],
            parent=host,
        )
        if not path:
            return
        Path(path).write_text(payload, encoding="utf-8")
        show_toast(host, "Zapisano plik", duration_ms=1400)

    def _stop() -> None:
        stop_flag["stop"] = True
        progress_var.set("Stop — koncze po biezacym oczekiwaniu 429/503...")

    filter_var.trace_add("write", lambda *_: _refresh_tree())
    title_status_var.trace_add("write", lambda *_: _refresh_tree())
    title_status_combo.bind("<<ComboboxSelected>>", lambda _e: _refresh_tree())
    refresh_btn.configure(command=_load_products_click)
    gen_btn.configure(command=_run_batch)
    copy_btn.configure(command=_copy_results)
    save_btn.configure(command=_save_results)
    stop_btn.configure(command=_stop)
    tree.bind("<<TreeviewSelect>>", _on_tree_select)
    tree.bind("<Button-3>", _on_tree_context_menu)
    host.bind("<Escape>", lambda _e: _stop() if state["running"] else None)

    register_loader(_load_products_click)


def _build_descriptions_tab(
    parent: tk.Misc,
    host: tk.Misc,
    shared: dict[str, object],
    *,
    model_var: tk.StringVar,
    delay_var: tk.StringVar,
    register_loader: Callable[[Callable[[], None]], None],
    load_products: Callable[..., None],
) -> None:
    state: dict[str, object] = {"running": False}

    list_frame = ttk.LabelFrame(
        parent,
        text="Produkty (Ctrl/Shift — wiele; generuj roboczy opis przez Gemini API)",
        padding=(10, 8),
    )
    list_frame.pack(fill="both", expand=True, padx=12, pady=(6, 6))

    filter_bar = ttk.Frame(list_frame)
    filter_bar.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar(value="")
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=32).pack(side="left", padx=(6, 8))
    count_var = tk.StringVar(value="(ladowanie...)")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="")
    ttk.Label(filter_bar, textvariable=progress_var, foreground="#444").pack(side="right")

    table_frame = ttk.Frame(list_frame)
    table_frame.pack(fill="both", expand=True)
    cols = ("surname", "firstname", "painting_title", "artist", "draft")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8, selectmode="extended")
    for c, label, w in (
        ("surname", "Nazwisko", 120),
        ("firstname", "Imie", 100),
        ("painting_title", "Tytul obrazu", 260),
        ("artist", "Artysta", 160),
        ("draft", "v1/v2", 52),
    ):
        tree.heading(c, text=label)
        tree.column(c, width=w, anchor="w", stretch=(c == "painting_title"))
    tree.column("draft", anchor="center", stretch=False)
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    tree.tag_configure("has_draft", background="#e3f2fd", foreground="#0d47a1")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    draft_frame = ttk.LabelFrame(
        parent,
        text="Roboczy opis (zapis lokalny — nie trafia do Shopify)",
        padding=(10, 6),
    )
    draft_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))
    draft_meta = tk.StringVar(value="Zaznacz produkt z listy albo wygeneruj opis.")
    ttk.Label(draft_frame, textvariable=draft_meta, foreground="#444", wraplength=900).pack(
        anchor="w", pady=(0, 4),
    )
    version_row = ttk.Frame(draft_frame)
    version_row.pack(fill="x", pady=(0, 6))
    ttk.Label(version_row, text="Wariant:").pack(side="left")
    description_version_var = tk.StringVar(value="v1")
    for vkey, vlabel in VARIANT_LABELS.items():
        ttk.Radiobutton(
            version_row,
            text=vlabel,
            variable=description_version_var,
            value=vkey,
        ).pack(side="left", padx=(10, 0))
    draft_text = scrolledtext.ScrolledText(draft_frame, height=10, wrap="word", font=("Segoe UI", 10))
    draft_text.pack(fill="both", expand=True)

    bottom = ttk.Frame(parent, padding=(12, 8))
    bottom.pack(fill="x")
    gen_btn = ttk.Button(bottom, text="Generuj opisy v1 + v2 (Gemini API)", state="disabled")
    gen_btn.pack(side="right")
    copy_btn = ttk.Button(bottom, text="Kopiuj opis", state="disabled")
    copy_btn.pack(side="right", padx=(0, 8))
    copy_json_btn = ttk.Button(bottom, text="Kopiuj JSON (porownywarka)", state="disabled")
    copy_json_btn.pack(side="right", padx=(0, 8))
    refresh_btn = ttk.Button(bottom, text="Odswiez produkty")
    refresh_btn.pack(side="left")
    stop_btn = ttk.Button(bottom, text="Stop", state="disabled")
    stop_btn.pack(side="left", padx=(8, 0))

    stop_flag = {"stop": False}
    row_by_iid: dict[str, dict] = {}

    def _rows() -> list[dict]:
        rows = shared.get("rows")
        return rows if isinstance(rows, list) else []

    def _drafts() -> dict[int, ProductDescriptionDrafts]:
        drafts = shared.get("description_drafts")
        return drafts if isinstance(drafts, dict) else {}

    def _draft_for_row(row: dict) -> ProductDescriptionDrafts | None:
        pid = int(row.get("product_id") or 0)
        if not pid:
            return None
        return _drafts().get(pid)

    def _active_variant_key() -> DescriptionVariantKey:
        return "v2" if description_version_var.get() == "v2" else "v1"

    def _draft_status_label(draft: ProductDescriptionDrafts | None) -> str:
        if not draft:
            return "—"
        v1 = "✓" if draft.v1.ok else "—"
        v2 = "✓" if draft.v2.ok else "—"
        return f"{v1}/{v2}"

    def _can_copy_compare_json(variant) -> bool:
        if not variant or not variant.ok:
            return False
        return sum(1 for a in variant.akapity if (a or "").strip()) >= 3

    def _show_draft_in_preview(
        draft: ProductDescriptionDrafts | None,
        *,
        row: dict | None = None,
    ) -> None:
        key = _active_variant_key()
        variant_label = VARIANT_LABELS[key]
        variant = draft.variant(key) if draft else None
        draft_text.configure(state="normal")
        draft_text.delete("1.0", "end")
        if variant and variant.ok:
            draft_text.insert("1.0", format_draft_display(variant.akapity))
            meta = f"{draft.artist} — {draft.painting_title}  |  {variant_label}"
            if variant.model_used:
                meta += f"  |  model: {variant.model_used}"
            if variant.generated_at:
                meta += f"  |  {variant.generated_at}"
            draft_meta.set(meta)
            copy_btn.configure(state="normal")
            copy_json_btn.configure(
                state="normal" if _can_copy_compare_json(variant) else "disabled",
            )
        elif variant and variant.error:
            draft_text.insert("1.0", f"Blad generowania ({variant_label}):\n{variant.error}")
            if variant.raw_response:
                draft_text.insert("end", f"\n\n--- surowa odpowiedz ---\n{variant.raw_response[:4000]}")
            title = (row or {}).get("painting_title") or (draft.painting_title if draft else "")
            artist = (row or {}).get("artist") or (draft.artist if draft else "")
            draft_meta.set(f"{artist} — {title}  |  {variant_label}  |  blad")
            copy_btn.configure(state="disabled")
            copy_json_btn.configure(state="disabled")
        else:
            if row and draft:
                other_key: DescriptionVariantKey = "v2" if key == "v1" else "v1"
                other = draft.variant(other_key)
                if other.ok:
                    draft_meta.set(
                        f"{row.get('artist', '')} — {row.get('painting_title', '')}  |  "
                        f"brak {variant_label} (przelacz na {VARIANT_LABELS[other_key]})",
                    )
                else:
                    draft_meta.set(
                        f"{row.get('artist', '')} — {row.get('painting_title', '')}  |  "
                        f"brak roboczego opisu ({variant_label})",
                    )
            elif row:
                draft_meta.set(
                    f"{row.get('artist', '')} — {row.get('painting_title', '')}  |  brak roboczego opisu",
                )
            else:
                draft_meta.set("Zaznacz produkt z listy albo wygeneruj opis.")
            copy_btn.configure(state="disabled")
            copy_json_btn.configure(state="disabled")

    def _selected_rows() -> list[dict]:
        out: list[dict] = []
        for iid in tree.selection():
            row = row_by_iid.get(iid)
            if row:
                out.append(row)
        return out

    def _on_version_changed() -> None:
        rows = _selected_rows()
        if len(rows) == 1:
            _show_draft_in_preview(_draft_for_row(rows[0]), row=rows[0])

    description_version_var.trace_add("write", lambda *_: _on_version_changed())

    def _refresh_tree(*, keep_selection: bool = True) -> None:
        selected_pids = {
            int(row_by_iid[iid].get("product_id") or 0)
            for iid in tree.selection()
            if iid in row_by_iid
        }
        tree.delete(*tree.get_children())
        row_by_iid.clear()
        q = filter_var.get().strip().lower()
        visible: list[dict] = []
        drafts = _drafts()
        draft_count = 0
        for row in _rows():
            pid = int(row.get("product_id") or 0)
            if pid in drafts and drafts[pid].ok:
                draft_count += 1
            blob = " ".join(
                str(row.get(k) or "") for k in ("surname", "firstname", "artist", "painting_title")
            ).lower()
            if q and q not in blob:
                continue
            visible.append(row)
        visible.sort(key=product_catalog_sort_key)
        reselect: list[str] = []
        for row in visible:
            pid = int(row.get("product_id") or 0)
            draft = drafts.get(pid)
            has = bool(draft and draft.ok)
            tags = ("has_draft",) if has else ()
            iid = tree.insert(
                "",
                "end",
                values=(
                    row.get("surname", ""),
                    row.get("firstname", ""),
                    row.get("painting_title", ""),
                    row.get("artist", ""),
                    _draft_status_label(draft),
                ),
                tags=tags,
            )
            row_by_iid[iid] = row
            if keep_selection and pid in selected_pids:
                reselect.append(iid)
        if reselect:
            tree.selection_set(reselect)
            tree.focus(reselect[0])
        count_var.set(
            f"{len(visible)} / {len(_rows())} produkt(ow)  |  robocze opisy: {draft_count}",
        )
        gen_btn.configure(state="normal" if visible and not state["running"] else "disabled")

    def _on_tree_select(_event: tk.Event | None = None) -> None:
        rows = _selected_rows()
        gen_btn.configure(state="normal" if rows and not state["running"] else "disabled")
        if len(rows) == 1:
            row = rows[0]
            _show_draft_in_preview(_draft_for_row(row), row=row)
        elif not rows:
            _show_draft_in_preview(None)

    def _open_draft_dialog(draft: ProductDescriptionDrafts) -> None:
        win = tk.Toplevel(host)
        win.title(f"Roboczy opis — {draft.painting_title}")
        win.transient(host)
        position_toplevel_screen_center(win, 760, 580)
        win.minsize(520, 400)

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)
        meta = f"{draft.artist} — {draft.painting_title}"
        ttk.Label(frame, text=meta, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        dlg_version = tk.StringVar(value=description_version_var.get())
        vrow = ttk.Frame(frame)
        vrow.pack(fill="x", pady=(0, 8))
        ttk.Label(vrow, text="Wariant:").pack(side="left")
        for vkey, vlabel in VARIANT_LABELS.items():
            ttk.Radiobutton(vrow, text=vlabel, variable=dlg_version, value=vkey).pack(
                side="left", padx=(10, 0),
            )

        meta_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=meta_var, foreground="#555").pack(anchor="w", pady=(0, 4))
        txt = scrolledtext.ScrolledText(frame, wrap="word", font=("Segoe UI", 10))
        txt.pack(fill="both", expand=True)

        def _refresh_dialog() -> None:
            key: DescriptionVariantKey = "v2" if dlg_version.get() == "v2" else "v1"
            variant = draft.variant(key)
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            if variant.ok:
                txt.insert("1.0", format_draft_display(variant.akapity))
                sub = VARIANT_LABELS[key]
                if variant.model_used:
                    sub += f"  |  {variant.model_used}"
                meta_var.set(sub)
            elif variant.error:
                txt.insert("1.0", variant.error)
                meta_var.set(f"{VARIANT_LABELS[key]} — blad")
            else:
                meta_var.set(f"Brak wariantu {VARIANT_LABELS[key]}")
            txt.configure(state="disabled")
            copy_btn.configure(state="normal" if variant.ok else "disabled")
            copy_json_btn.configure(
                state="normal" if _can_copy_compare_json(variant) else "disabled",
            )

        dlg_version.trace_add("write", lambda *_: _refresh_dialog())

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=(10, 0))

        def _copy() -> None:
            key: DescriptionVariantKey = "v2" if dlg_version.get() == "v2" else "v1"
            variant = draft.variant(key)
            payload = format_draft_display(variant.akapity) if variant.ok else variant.error
            if not payload.strip():
                return
            win.clipboard_clear()
            win.clipboard_append(payload)
            win.update()
            show_toast(win, "Skopiowano opis", duration_ms=1400)

        def _copy_json() -> None:
            key: DescriptionVariantKey = "v2" if dlg_version.get() == "v2" else "v1"
            variant = draft.variant(key)
            if not _can_copy_compare_json(variant):
                messagebox.showwarning(
                    APP_TITLE,
                    "Brak co najmniej 3 akapitow do JSON porownywarki.",
                    parent=win,
                )
                return
            try:
                payload = format_akapity_compare_json(variant.akapity)
            except ValueError as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=win)
                return
            win.clipboard_clear()
            win.clipboard_append(payload)
            win.update()
            show_toast(win, "Skopiowano JSON do porownywarki", duration_ms=1500)

        copy_btn = ttk.Button(btn_row, text="Kopiuj opis", command=_copy, state="disabled")
        copy_btn.pack(side="right")
        copy_json_btn = ttk.Button(
            btn_row,
            text="Kopiuj JSON (porownywarka)",
            command=_copy_json,
            state="disabled",
        )
        copy_json_btn.pack(side="right", padx=(0, 8))
        ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right", padx=(0, 8))
        _refresh_dialog()
        win.bind("<Escape>", lambda _e: win.destroy())

    def _on_tree_double_click(event: tk.Event) -> None:
        item = tree.identify_row(event.y)
        if not item:
            return
        row = row_by_iid.get(item)
        if not row:
            return
        draft = _draft_for_row(row)
        if draft and (draft.v1.ok or draft.v2.ok or draft.v1.error or draft.v2.error):
            _open_draft_dialog(draft)
        else:
            messagebox.showinfo(
                APP_TITLE,
                "Brak roboczego opisu dla tego produktu.\n"
                "Zaznacz go i kliknij «Generuj opis (Gemini API)».",
                parent=host,
            )
        return "break"

    def _store_draft(result: ProductDescriptionDrafts) -> None:
        drafts = _drafts()
        if result.product_id:
            existing = drafts.get(result.product_id)
            if existing:
                result = merge_description_drafts(existing, result)
            drafts[result.product_id] = result
        shared["description_drafts"] = drafts
        save_description_drafts(drafts)

    def _on_products_loaded() -> None:
        refresh_btn.configure(state="normal")
        _refresh_tree()

    def _load_products_click() -> None:
        refresh_btn.configure(state="disabled")
        gen_btn.configure(state="disabled")
        load_products(progress_set=progress_var.set, on_ready=_on_products_loaded)

    def _run_batch() -> None:
        rows = _selected_rows()
        if not rows:
            messagebox.showinfo(APP_TITLE, "Zaznacz co najmniej jeden produkt.", parent=host)
            return
        if not gemini_api_key():
            messagebox.showerror(
                APP_TITLE,
                "Dodaj GEMINI_API_KEY do cursor-api/.env\n"
                "(https://aistudio.google.com/apikey)",
                parent=host,
            )
            return
        try:
            delay_s = max(0.0, float(delay_var.get().replace(",", ".")))
        except ValueError:
            messagebox.showerror(APP_TITLE, "Nieprawidlowa przerwa (sekundy).", parent=host)
            return

        model = model_var.get().strip() or DEFAULT_MODEL
        stop_flag["stop"] = False
        state["running"] = True
        gen_btn.configure(state="disabled")
        refresh_btn.configure(state="disabled")
        stop_btn.configure(state="normal")

        def work() -> None:
            import time

            total = len(rows)

            def _prefetch_progress(done: int, count: int) -> None:
                host.after(
                    0,
                    lambda d=done, c=count: progress_var.set(f"Pobieram miniatury ({d}/{c})..."),
                )

            prefetch = prefetch_row_images(rows, on_progress=_prefetch_progress)

            for idx, row in enumerate(rows, start=1):
                if stop_flag["stop"]:
                    break
                title = str(row.get("painting_title") or "?")
                pf = prefetch.get(id(row))
                pid = int(row.get("product_id") or 0)

                if pf and pf.error:
                    result = ProductDescriptionDrafts(
                        product_id=pid,
                        artist=str(row.get("artist") or ""),
                        painting_title=title,
                    )
                    result.v1.error = pf.error
                    result.v2.error = pf.error
                    _store_draft(result)
                    host.after(0, lambda r=result: _show_draft_in_preview(r, row=row))
                    host.after(0, _refresh_tree)
                    continue

                host.after(
                    0,
                    lambda i=idx, t=total, n=title: progress_var.set(
                        f"Opis Gemini ({i}/{t}): {n[:45]}...",
                    ),
                )
                img_bytes = pf.image_bytes if pf else None
                mime = pf.mime_type if pf else "image/jpeg"

                def _show_retry_state(
                    attempt_no: int,
                    *,
                    _row: dict = row,
                    _pid: int = pid,
                ) -> None:
                    draft_text.configure(state="normal")
                    draft_text.delete("1.0", "end")
                    draft_text.insert(
                        "1.0",
                        (
                            "Gemini API — ponawiam po bledzie 503/429...\n\n"
                            f"Proba nr {attempt_no}. Nie zamykaj okna — aplikacja czeka "
                            "i wysyla zapytanie ponownie automatycznie."
                        ),
                    )
                    title_s = str(_row.get("painting_title") or "?")
                    draft_meta.set(
                        f"{_row.get('artist', '')} — {title_s}  |  ponawiam ({attempt_no})",
                    )

                def _status(msg: str, *, _idx=idx, _total=total, _title=title) -> None:
                    def _ui(m: str = msg, i=_idx, t=_total, n=_title) -> None:
                        progress_var.set(f"Opis Gemini ({i}/{t}): {n[:30]}... — {m}")
                        if any(
                            x in m
                            for x in ("503", "429", "czekam", "ponowie", "proba")
                        ):
                            attempt_no = 1
                            for token in m.replace(",", " ").split():
                                if token.isdigit():
                                    attempt_no = max(attempt_no, int(token))
                            _show_retry_state(attempt_no)

                    host.after(0, _ui)

                def _start_generating(*, _row: dict = row) -> None:
                    draft_text.configure(state="normal")
                    draft_text.delete("1.0", "end")
                    draft_text.insert(
                        "1.0",
                        "Generowanie opisow v1 + v2 przez Gemini API...\n"
                        "Przy bledzie 503 aplikacja czeka i ponawia do skutku.",
                    )
                    title_s = str(_row.get("painting_title") or "?")
                    draft_meta.set(
                        f"{_row.get('artist', '')} — {title_s}  |  generuje...",
                    )

                if len(_selected_rows()) == 1:
                    host.after(0, _start_generating)
                try:
                    result = process_description_row(
                        row,
                        model=model,
                        image_bytes=img_bytes,
                        mime_type=mime,
                        on_status=_status,
                        should_abort=lambda: stop_flag["stop"],
                        existing=_drafts().get(pid),
                    )
                except GeminiAborted:
                    break
                _store_draft(result)

                def _ui_update(r: ProductDescriptionDrafts = result, rw: dict = row) -> None:
                    _refresh_tree()
                    if len(_selected_rows()) == 1:
                        sel = _selected_rows()
                        if sel and int(sel[0].get("product_id") or 0) == r.product_id:
                            _show_draft_in_preview(r, row=rw)

                host.after(0, _ui_update)
                if idx < total and delay_s > 0 and not stop_flag["stop"]:
                    time.sleep(delay_s)

            def done() -> None:
                state["running"] = False
                stop_btn.configure(state="disabled")
                refresh_btn.configure(state="normal")
                _refresh_tree()
                drafts = _drafts()
                ok_v1 = sum(1 for r in drafts.values() if r.v1.ok)
                ok_v2 = sum(1 for r in drafts.values() if r.v2.ok)
                err = sum(1 for r in drafts.values() if r.v1.error or r.v2.error)
                progress_var.set(f"Koniec batcha: v1={ok_v1}, v2={ok_v2}, bledy={err}.")
                show_toast(host, f"Gemini opisy: v1={ok_v1}, v2={ok_v2}", duration_ms=2200)

            host.after(0, done)

        threading.Thread(target=work, daemon=True, name="tytulyai-desc-batch").start()

    def _copy_draft() -> None:
        payload = draft_text.get("1.0", "end-1c").strip()
        if not payload:
            return
        host.clipboard_clear()
        host.clipboard_append(payload)
        host.update()
        show_toast(host, "Skopiowano opis do schowka", duration_ms=1600)

    def _copy_draft_json() -> None:
        rows = _selected_rows()
        if len(rows) != 1:
            return
        draft = _draft_for_row(rows[0])
        if not draft:
            return
        variant = draft.variant(_active_variant_key())
        if not _can_copy_compare_json(variant):
            messagebox.showwarning(
                APP_TITLE,
                "Brak co najmniej 3 akapitow do JSON porownywarki.",
                parent=host,
            )
            return
        try:
            payload = format_akapity_compare_json(variant.akapity)
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return
        host.clipboard_clear()
        host.clipboard_append(payload)
        host.update()
        show_toast(host, "Skopiowano JSON do porownywarki akapitow", duration_ms=1600)

    def _stop() -> None:
        stop_flag["stop"] = True
        progress_var.set("Stop — koncze po biezacym oczekiwaniu 429/503...")

    filter_var.trace_add("write", lambda *_: _refresh_tree())
    refresh_btn.configure(command=_load_products_click)
    gen_btn.configure(command=_run_batch)
    copy_btn.configure(command=_copy_draft)
    copy_json_btn.configure(command=_copy_draft_json)
    stop_btn.configure(command=_stop)
    tree.bind("<<TreeviewSelect>>", _on_tree_select)
    tree.bind("<Double-1>", _on_tree_double_click)
    host.bind("<Escape>", lambda _e: _stop() if state["running"] else None)

    register_loader(_load_products_click)


def _show_gemini_key_dialog(parent: tk.Misc, *, on_saved: Callable[[], None] | None = None) -> None:
    win = tk.Toplevel(parent)
    win.title("Gemini API — klucz")
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)
    position_toplevel_screen_center(win, 520, 280)

    frame = ttk.Frame(win, padding=14)
    frame.pack(fill="both", expand=True)

    ttk.Label(
        frame,
        text="Klucz Google Gemini (GEMINI_API_KEY)",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")

    current = gemini_api_key()
    if current:
        ttk.Label(
            frame,
            text=f"Aktualny klucz: {gemini_api_key_hint()}",
            foreground="#666",
        ).pack(anchor="w", pady=(4, 0))

    ttk.Label(
        frame,
        text=(
            "Wklej klucz z Google AI Studio. Zostanie zapisany w cursor-api/.env "
            "(nadpisuje istniejaca wartosc GEMINI_API_KEY)."
        ),
        wraplength=460,
        justify="left",
    ).pack(fill="x", pady=(8, 6))

    link_row = ttk.Frame(frame)
    link_row.pack(fill="x", pady=(0, 8))
    ttk.Label(link_row, text="Pobierz klucz: ").pack(side="left")
    link = tk.Label(
        link_row,
        text="https://aistudio.google.com/apikey",
        fg="#06a",
        cursor="hand2",
        font=("Segoe UI", 9, "underline"),
    )
    link.pack(side="left")
    link.bind(
        "<Button-1>",
        lambda _e: webbrowser.open("https://aistudio.google.com/apikey"),
    )

    ttk.Label(frame, text="Nowy GEMINI_API_KEY:").pack(anchor="w")
    key_var = tk.StringVar(value=current)
    entry = ttk.Entry(frame, textvariable=key_var, width=58, show="*")
    entry.pack(fill="x", pady=(2, 4))
    show_var = tk.IntVar(value=0)

    def _toggle_show() -> None:
        entry.configure(show="" if show_var.get() else "*")

    ttk.Checkbutton(
        frame, text="Pokaz znaki", variable=show_var, command=_toggle_show,
    ).pack(anchor="w")

    status_var = tk.StringVar(value="")
    ttk.Label(frame, textvariable=status_var, foreground="#a60", wraplength=460).pack(
        fill="x", pady=(4, 0),
    )

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x", pady=(12, 0))

    def _close() -> None:
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    def _save() -> None:
        new_key = key_var.get().strip()
        if len(new_key) < 20:
            status_var.set("Klucz wyglada na za krotki. Sprawdz i sprobuj ponownie.")
            return
        try:
            env_path = set_gemini_api_key(new_key)
        except (OSError, ValueError) as exc:
            status_var.set(str(exc))
            return
        if on_saved:
            on_saved()
        show_toast(
            parent,
            f"Zapisano GEMINI_API_KEY ({env_path.name})",
            duration_ms=2200,
        )
        _close()

    ttk.Button(btn_row, text="Anuluj", command=_close).pack(side="right")
    ttk.Button(btn_row, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))
    entry.focus_set()
    entry.selection_range(0, "end")
    win.bind("<Return>", lambda _e: _save())
    win.bind("<Escape>", lambda _e: _close())


def _copy_session_prompt(host: tk.Misc) -> None:
    try:
        host.clipboard_clear()
        host.clipboard_append(GEMINI_CHAT_SESSION_START)
        host.update()
    except tk.TclError as exc:
        messagebox.showerror(APP_TITLE, str(exc), parent=host)
        return
    show_toast(
        host,
        "Prompt startowy skopiowany — wklej w nowym czacie Gemini",
        duration_ms=2200,
    )