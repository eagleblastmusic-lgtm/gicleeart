"""GUI: kreator promptu «Zmien tytuly» — lista produktow, potem tytuly."""

from __future__ import annotations

import os
import re
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from Komponenty._shared.clipboard_image import (
    copy_image_url_to_clipboard,
    image_url_extension,
    save_image_url_to_file,
)
from Komponenty._shared.toast import show_toast
from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.description_update import (
    TITLE_UPDATED_LABEL,
    TITLE_EDIT_FIELD_LABELS,
    TITLE_EDIT_LANG_KEYS,
    apply_product_title_fields,
    build_title_change_prompt,
    load_product_catalog_rows,
    load_product_title_fields,
    load_title_update_marks,
    parse_title_change_fields,
    parse_title_change_product_ref,
    product_catalog_sort_key,
    set_title_update_mark,
    set_title_update_marks_batch,
    toggle_title_update_mark,
)
from Komponenty.tytulyai.prompts import GEMINI_CHAT_SESSION_START, TITLE_CHAT_PROMPT_PRESETS

APP_TITLE = "Zmień tytuły"
_STASH_SEPARATOR = "\n\n"
_WIN_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _win_alive(win: tk.Misc | None) -> bool:
    if win is None:
        return False
    try:
        return bool(win.winfo_exists())
    except tk.TclError:
        return False


def _safe_configure(widget: tk.Misc | None, **kwargs) -> None:
    if widget is None:
        return
    try:
        if widget.winfo_exists():
            widget.configure(**kwargs)
    except tk.TclError:
        return


def _safe_download_stem(row: dict) -> str:
    artist = str(row.get("artist") or "").strip()
    title = str(row.get("painting_title") or "").strip()
    if artist and title:
        base = f"{artist} - {title}"
    else:
        fn = str(row.get("image_filename") or "").strip()
        base = Path(fn).stem if fn else f"product-{row.get('product_id') or 'obraz'}"
    base = _WIN_INVALID_FILENAME.sub("-", base).strip(" .")
    if len(base) > 180:
        base = base[:180].rstrip(" .")
    return base or "obraz"


def _unique_download_path(folder: Path, stem: str, ext: str) -> Path:
    candidate = folder / f"{stem}{ext}"
    if not candidate.exists():
        return candidate
    i = 2
    while True:
        candidate = folder / f"{stem} ({i}){ext}"
        if not candidate.exists():
            return candidate
        i += 1


def _resolve_row_image_url(row: dict) -> str:
    image_url = (row.get("image_src") or "").strip()
    if image_url:
        return image_url
    pid = int(row.get("product_id") or 0)
    if not pid:
        return ""
    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, pid)
    img = prod.get("image") or {}
    image_url = (img.get("src") or "").strip()
    if image_url:
        return image_url
    for im in prod.get("images") or []:
        src = (im.get("src") or "").strip()
        if src:
            return src
    return ""


def _open_folder(path: Path) -> None:
    if not path.is_dir():
        return
    if os.name == "nt":
        os.startfile(str(path))  # noqa: S606
    else:
        import subprocess

        subprocess.run(["xdg-open", str(path)], check=False)


def _wizard_state(host: tk.Misc) -> dict[str, object]:
    if not hasattr(host, "_zmietytuly_wizard"):
        host._zmietytuly_wizard = {}
    return host._zmietytuly_wizard


def _copy_prompt_to_clipboard(parent: tk.Misc, prompt: str) -> None:
    try:
        parent.clipboard_clear()
        parent.clipboard_append(prompt)
        parent.update()
    except tk.TclError as exc:
        messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=parent)
        raise


def _open_prompt_list_dialog(
    parent: tk.Misc,
    *,
    clipboard_root: tk.Misc,
) -> None:
    """Okno z presetami promptow startowych Gemini (kopiuj do schowka)."""
    win = tk.Toplevel(parent)
    win.title(f"{APP_TITLE} — lista promptow")
    win.transient(parent)
    win.grab_set()
    position_toplevel_screen_center(win, 820, 620)
    win.minsize(640, 480)

    ttk.Label(
        win,
        text=(
            "Wybierz prompt startowy do nowej rozmowy w Gemini. "
            "Kliknij dwukrotnie lub uzyj «Kopiuj», potem wklej w czacie przed pierwszym zdjeciem."
        ),
        wraplength=760,
        padding=(12, 12, 12, 8),
    ).pack(fill="x")

    body = ttk.Panedwindow(win, orient="horizontal")
    body.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    list_frame = ttk.Frame(body, padding=(0, 0, 6, 0))
    body.add(list_frame, weight=1)
    lb = tk.Listbox(list_frame, selectmode="browse", activestyle="dotbox", exportselection=False)
    lb.pack(fill="both", expand=True)
    for label, _text in TITLE_CHAT_PROMPT_PRESETS:
        lb.insert("end", label)

    preview_frame = ttk.Frame(body)
    body.add(preview_frame, weight=3)
    preview = scrolledtext.ScrolledText(
        preview_frame, wrap="word", font=("Consolas", 9), state="disabled",
    )
    preview.pack(fill="both", expand=True)

    def _show_preview(index: int) -> None:
        if index < 0 or index >= len(TITLE_CHAT_PROMPT_PRESETS):
            return
        _label, text = TITLE_CHAT_PROMPT_PRESETS[index]
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        preview.insert("1.0", text)
        preview.configure(state="disabled")

    def _selected_index() -> int:
        sel = lb.curselection()
        return int(sel[0]) if sel else -1

    def _copy_selected() -> None:
        idx = _selected_index()
        if idx < 0:
            messagebox.showinfo(APP_TITLE, "Wybierz prompt z listy.", parent=win)
            return
        _label, text = TITLE_CHAT_PROMPT_PRESETS[idx]
        try:
            _copy_prompt_to_clipboard(parent, text)
        except tk.TclError:
            return
        show_toast(
            clipboard_root,
            f"Skopiowano: {_label}",
            duration_ms=2200,
        )

    def _on_select(_event: tk.Event | None = None) -> None:
        _show_preview(_selected_index())

    lb.bind("<<ListboxSelect>>", _on_select)
    lb.bind("<Double-Button-1>", lambda _e: _copy_selected())
    if TITLE_CHAT_PROMPT_PRESETS:
        lb.selection_set(0)
        lb.activate(0)
        _show_preview(0)

    btns = ttk.Frame(win, padding=(12, 0, 12, 12))
    btns.pack(fill="x")
    ttk.Button(btns, text="Kopiuj", command=_copy_selected).pack(side="left")
    ttk.Button(btns, text="Zamknij", command=win.destroy).pack(side="right")
    win.bind("<Escape>", lambda _e: win.destroy())


def _set_wizard_title(host: tk.Misc, step: int, *, total: int = 2) -> None:
    if isinstance(host, (tk.Tk, tk.Toplevel)):
        host.title(f"{APP_TITLE} — krok {step}/{total}")


def _clear_host(host: tk.Misc) -> None:
    for child in host.winfo_children():
        child.destroy()


def _stash_items(ws: dict[str, object]) -> list[str]:
    raw = ws.get("stash")
    if not isinstance(raw, list):
        raw = []
        ws["stash"] = raw
    return raw


def _stash_joined(ws: dict[str, object]) -> str:
    return _STASH_SEPARATOR.join(_stash_items(ws))


def _refresh_stash_text(stash_text: scrolledtext.ScrolledText, ws: dict[str, object]) -> None:
    stash_text.configure(state="normal")
    stash_text.delete("1.0", "end")
    stash_text.insert("1.0", _stash_joined(ws))
    stash_text.configure(state="disabled")


def _build_stash_panel(
    host: tk.Misc,
    *,
    clipboard_root: tk.Misc,
    ws: dict[str, object],
) -> scrolledtext.ScrolledText:
    frame = ttk.LabelFrame(host, text="Schowek", padding=(10, 6))
    frame.pack(fill="x", padx=12, pady=(0, 8))

    hint = ttk.Label(
        frame,
        text=(
            "Po kroku 2 prompty trafiaja tutaj. Zbierz kilka produktow, "
            "potem «Kopiuj schowek» i wklej w Cursor."
        ),
        wraplength=900,
        foreground="#444",
    )
    hint.pack(anchor="w", pady=(0, 4))

    stash_text = scrolledtext.ScrolledText(
        frame, height=5, wrap="word", font=("Consolas", 9), state="disabled",
    )
    stash_text.pack(fill="x", expand=False, pady=(0, 6))
    _refresh_stash_text(stash_text, ws)

    btns = ttk.Frame(frame)
    btns.pack(fill="x")

    def _copy_stash() -> None:
        payload = _stash_joined(ws).strip()
        if not payload:
            messagebox.showinfo(APP_TITLE, "Schowek jest pusty.", parent=host)
            return
        try:
            _copy_prompt_to_clipboard(host, payload)
        except tk.TclError:
            return
        show_toast(
            clipboard_root,
            f"Skopiowano {len(_stash_items(ws))} prompt(ow) ze schowka",
            duration_ms=1800,
        )

    def _clear_stash() -> None:
        if not _stash_items(ws):
            return
        if not messagebox.askyesno(
            APP_TITLE,
            "Wyczyscic caly schowek?",
            parent=host,
        ):
            return
        _stash_items(ws).clear()
        _refresh_stash_text(stash_text, ws)

    count_var = tk.StringVar(value=f"{len(_stash_items(ws))} prompt(ow)")
    ttk.Label(btns, textvariable=count_var, foreground="#0a6").pack(side="left")

    def _update_count() -> None:
        count_var.set(f"{len(_stash_items(ws))} prompt(ow)")

    stash_text._zmietytuly_update_count = _update_count  # type: ignore[attr-defined]
    ttk.Button(btns, text="Kopiuj schowek", command=_copy_stash).pack(side="right")
    ttk.Button(btns, text="Wyczysc", command=_clear_stash).pack(side="right", padx=(0, 8))
    return stash_text


def _stash_append(
    ws: dict[str, object],
    prompt: str,
    stash_text: scrolledtext.ScrolledText | None,
) -> None:
    text = (prompt or "").strip()
    if not text:
        return
    items = _stash_items(ws)
    if items and items[-1] == text:
        return
    items.append(text)
    if stash_text is not None:
        _refresh_stash_text(stash_text, ws)
        update_count = getattr(stash_text, "_zmietytuly_update_count", None)
        if callable(update_count):
            update_count()


def _show_step2(
    host: tk.Misc,
    *,
    clipboard_root: tk.Misc,
    painting_title: str,
    artist_name: str,
    product_id: int = 0,
    on_back: Callable[[], None] | None = None,
    on_finish: Callable[[], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
) -> None:
    _clear_host(host)
    _set_wizard_title(host, 2)
    ws = _wizard_state(host)
    if isinstance(host, (tk.Tk, tk.Toplevel)):
        position_toplevel_screen_center(host, 820, 620)
        host.minsize(600, 480)

    ttk.Label(
        host,
        text=(
            "Wklej nowe tytuly (np. z LLM) — po wklejeniu prompt trafia automatycznie do schowka:\n"
            "Tytul oryginalny / niderlandzki (NL): ...\n"
            "Tytul polski: ...  Tytul angielski: ...\n"
            "Tytuly w pozostalych jezykach: Tytul niemiecki (DE): ... itd."
        ),
        wraplength=700,
    ).pack(anchor="w", padx=12, pady=(12, 6))

    ttk.Label(
        host,
        text=f"Produkt: {painting_title} — {artist_name}",
        wraplength=700,
        foreground="#444",
    ).pack(anchor="w", padx=12, pady=(0, 6))

    titles_frame = ttk.Frame(host, padding=(12, 0))
    titles_frame.pack(fill="both", expand=True)
    titles_text = scrolledtext.ScrolledText(
        titles_frame, height=10, wrap="word", font=("Consolas", 10),
    )
    titles_text.pack(fill="both", expand=True)

    stash_widget = _build_stash_panel(host, clipboard_root=clipboard_root, ws=ws)

    titles_btns = ttk.Frame(host, padding=(12, 8))
    titles_btns.pack(fill="x")

    def _auto_stash_from_field(*, return_to_list: bool) -> bool:
        raw = titles_text.get("1.0", "end").strip()
        if not raw:
            return False
        try:
            fields = parse_title_change_fields(raw)
            prompt = build_title_change_prompt(
                painting_title=painting_title,
                artist=artist_name,
                titles=fields,
            )
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return False
        _stash_append(ws, prompt, stash_widget)
        if product_id:
            set_title_update_mark(product_id, marked=True)
        show_toast(clipboard_root, "Prompt dodany do schowka", duration_ms=1600)
        if return_to_list and on_finish:
            on_finish()
        return True

    def _paste_titles_clipboard() -> None:
        try:
            data = clipboard_root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(APP_TITLE, "Schowek jest pusty.", parent=host)
            return
        titles_text.delete("1.0", "end")
        titles_text.insert("1.0", data)
        _auto_stash_from_field(return_to_list=True)

    def _on_text_paste(_event: tk.Event | None = None) -> None:
        host.after_idle(lambda: _auto_stash_from_field(return_to_list=True))

    def _back() -> None:
        raw = titles_text.get("1.0", "end").strip()
        if raw:
            if not _auto_stash_from_field(return_to_list=False):
                return
        if on_back:
            on_back()

    def _cancel() -> None:
        if on_cancel:
            on_cancel()

    if on_back:
        ttk.Button(titles_btns, text="Wstecz", command=_back).pack(side="left")
    ttk.Button(
        titles_btns, text="Wklej ze schowka", command=_paste_titles_clipboard,
    ).pack(side="left", padx=(8, 0) if on_back else (0, 0))
    ttk.Button(titles_btns, text="Zamknij", command=_cancel).pack(side="right")
    host.bind("<Escape>", lambda _e: _cancel())
    titles_text.bind("<<Paste>>", _on_text_paste)
    titles_text.focus_set()


def _show_manual_ref(
    host: tk.Misc,
    *,
    clipboard_root: tk.Misc,
    on_back: Callable[[], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
    painting: str = "",
    artist: str = "",
) -> None:
    _clear_host(host)
    if isinstance(host, (tk.Tk, tk.Toplevel)):
        host.title(f"{APP_TITLE} — wpisz recznie")
        position_toplevel_screen_center(host, 720, 360)
        host.minsize(520, 280)

    ttk.Label(
        host,
        text=(
            "Wklej identyfikacje produktu (dwie linie):\n"
            "1) tytul obrazu\n2) artysta"
        ),
        wraplength=660,
    ).pack(anchor="w", padx=12, pady=(12, 6))

    ref_frame = ttk.Frame(host, padding=(12, 0))
    ref_frame.pack(fill="both", expand=True)
    ref_text = scrolledtext.ScrolledText(ref_frame, height=8, wrap="word", font=("Consolas", 10))
    ref_text.pack(fill="both", expand=True)
    if painting.strip() and artist.strip():
        ref_text.insert("1.0", f"{painting.strip()}\n{artist.strip()}")

    ref_btns = ttk.Frame(host, padding=(12, 8))
    ref_btns.pack(fill="x")

    def _next_step() -> None:
        raw = ref_text.get("1.0", "end").strip()
        try:
            painting_title, artist_name = parse_title_change_product_ref(raw)
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return
        _show_step2(
            host,
            clipboard_root=clipboard_root,
            painting_title=painting_title,
            artist_name=artist_name,
            on_back=lambda: _show_manual_ref(
                host,
                clipboard_root=clipboard_root,
                on_back=on_back,
                on_cancel=on_cancel,
                painting=painting_title,
                artist=artist_name,
            ),
            on_cancel=on_cancel,
        )

    def _paste_ref_clipboard() -> None:
        try:
            data = clipboard_root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(APP_TITLE, "Schowek jest pusty.", parent=host)
            return
        ref_text.delete("1.0", "end")
        ref_text.insert("1.0", data)
        _next_step()

    def _cancel() -> None:
        if on_cancel:
            on_cancel()

    if on_back:
        ttk.Button(ref_btns, text="Wstecz", command=on_back).pack(side="left")
    ttk.Button(
        ref_btns, text="Wklej ze schowka", command=_paste_ref_clipboard,
    ).pack(side="left", padx=(8, 0) if on_back else (0, 0))
    ttk.Button(ref_btns, text="Dalej", command=_next_step).pack(side="right")
    ttk.Button(ref_btns, text="Zamknij", command=_cancel).pack(side="right", padx=(0, 8))
    host.bind("<Escape>", lambda _e: _cancel())
    ref_text.focus_set()


def _open_title_editor_dialog(
    parent: tk.Misc,
    *,
    row: dict,
    on_saved: Callable[[dict[str, str]], None] | None = None,
) -> None:
    """Okno edycji tytulow obrazu we wszystkich jezykach (PPM z listy produktow)."""
    product_id = int(row.get("product_id") or 0)
    artist = str(row.get("artist") or "").strip()
    painting_title = str(row.get("painting_title") or "").strip()
    if not product_id:
        messagebox.showerror(APP_TITLE, "Brak ID produktu.", parent=parent)
        return
    if not artist:
        messagebox.showerror(APP_TITLE, "Brak artysty w danych produktu.", parent=parent)
        return

    win = tk.Toplevel(parent)
    win.title(f"{APP_TITLE} — edycja tytulow")
    win.transient(parent)
    win.grab_set()
    position_toplevel_screen_center(win, 760, 620)
    win.minsize(560, 480)

    header = ttk.Label(
        win,
        text=f"{painting_title}\n{artist}",
        wraplength=700,
        justify="left",
    )
    header.pack(anchor="w", padx=12, pady=(12, 4))

    status_var = tk.StringVar(value="Pobieram tytuly ze sklepu...")
    ttk.Label(win, textvariable=status_var, foreground="#444").pack(
        anchor="w", padx=12, pady=(0, 8),
    )

    form_outer = ttk.Frame(win)
    form_outer.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    canvas = tk.Canvas(form_outer, highlightthickness=0)
    vsb = ttk.Scrollbar(form_outer, orient="vertical", command=canvas.yview)
    form = ttk.Frame(canvas)
    form.bind(
        "<Configure>",
        lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    form_window = canvas.create_window((0, 0), window=form, anchor="nw")

    def _resize_form(_event: tk.Event) -> None:
        canvas.itemconfigure(form_window, width=canvas.winfo_width())

    canvas.bind("<Configure>", _resize_form)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    bind_mousewheel_to_canvas(canvas, win)

    entries: dict[str, tk.Entry] = {}
    title_vars: dict[str, tk.StringVar] = {}
    for key in TITLE_EDIT_LANG_KEYS:
        row_frame = ttk.Frame(form)
        row_frame.pack(fill="x", pady=(0, 8))
        label = TITLE_EDIT_FIELD_LABELS.get(key, key)
        ttk.Label(row_frame, text=f"{label}:", width=28, anchor="w").pack(
            side="left", anchor="n", padx=(0, 8),
        )
        var = tk.StringVar()
        title_vars[key] = var
        ent = ttk.Entry(row_frame, textvariable=var, width=72, state="readonly")
        ent.pack(side="left", fill="x", expand=True)
        entries[key] = ent

    if painting_title:
        title_vars["pl"].set(painting_title)

    btns = ttk.Frame(win, padding=(12, 8))
    btns.pack(fill="x")
    save_btn = ttk.Button(btns, text="Zapisz do Shopify", state="disabled")
    save_btn.pack(side="right")
    copy_btn = ttk.Button(btns, text="Kopiuj prompt", state="disabled")
    copy_btn.pack(side="right", padx=(0, 8))

    ui_closed = [False]
    pending_after_ids: list[str] = []

    def _invalidate_ui() -> None:
        ui_closed[0] = True
        for aid in pending_after_ids:
            try:
                win.after_cancel(aid)
            except (tk.TclError, ValueError):
                pass
        pending_after_ids.clear()

    def _close_dialog() -> None:
        _invalidate_ui()
        if _win_alive(win):
            win.destroy()

    def _schedule_ui(callback: Callable[[], None]) -> None:
        if ui_closed[0] or not _win_alive(win):
            return

        def wrapper() -> None:
            if ui_closed[0] or not _win_alive(win):
                return
            callback()

        pending_after_ids.append(win.after(0, wrapper))

    ttk.Button(btns, text="Zamknij", command=_close_dialog).pack(side="left")

    def _collect_titles() -> dict[str, str]:
        return {key: title_vars[key].get().strip() for key in TITLE_EDIT_LANG_KEYS}

    def _copy_prompt() -> None:
        titles = _collect_titles()
        if not titles.get("pl"):
            messagebox.showwarning(APP_TITLE, "Uzupelnij tytul polski.", parent=win)
            return
        try:
            prompt = build_title_change_prompt(
                painting_title=titles.get("pl") or painting_title,
                artist=artist,
                titles=titles,
            )
            _copy_prompt_to_clipboard(win, prompt)
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=win)
            return
        show_toast(win, "Prompt skopiowany do schowka", duration_ms=1600)

    def _enable_form() -> None:
        if not _win_alive(win):
            return
        for ent in entries.values():
            _safe_configure(ent, state="normal")
        _safe_configure(save_btn, state="normal")
        _safe_configure(copy_btn, state="normal")

    def _set_form_values(titles: dict[str, str]) -> None:
        if not _win_alive(win):
            return
        for key in TITLE_EDIT_LANG_KEYS:
            title_vars[key].set(titles.get(key) or "")

    def _save() -> None:
        titles = _collect_titles()
        if not titles.get("pl"):
            messagebox.showwarning(APP_TITLE, "Tytul polski jest wymagany.", parent=win)
            return
        if not titles.get("orig"):
            messagebox.showwarning(APP_TITLE, "Tytul oryginalny jest wymagany.", parent=win)
            return
        _safe_configure(save_btn, state="disabled")
        _safe_configure(copy_btn, state="disabled")
        if _win_alive(win):
            status_var.set("Zapisuje w Shopify...")

        def work() -> None:
            try:
                apply_product_title_fields(
                    product_id=product_id,
                    artist=artist,
                    titles=titles,
                )
                set_title_update_mark(product_id, marked=True)
            except Exception as exc:
                _schedule_ui(
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=win),
                )
                _schedule_ui(lambda e=exc: status_var.set(f"Blad: {e}"))
                _schedule_ui(_enable_form)
                return

            def done() -> None:
                if not _win_alive(win):
                    return
                status_var.set("Zapisano.")
                show_toast(win, "Tytuly zapisane w sklepie", duration_ms=1800)
                if on_saved:
                    on_saved(titles)
                _close_dialog()

            _schedule_ui(done)

        threading.Thread(target=work, daemon=True, name="zmietytuly-save-titles").start()

    copy_btn.configure(command=_copy_prompt)
    save_btn.configure(command=_save)
    win.protocol("WM_DELETE_WINDOW", _close_dialog)
    win.bind("<Escape>", lambda _e: _close_dialog())

    def _load() -> None:
        try:
            titles = load_product_title_fields(product_id)
        except Exception as exc:
            _schedule_ui(
                lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=win),
            )
            _schedule_ui(lambda e=exc: status_var.set(f"Blad pobierania: {e}"))
            _schedule_ui(_enable_form)
            return

        def populate() -> None:
            if ui_closed[0] or not _win_alive(win):
                return
            _set_form_values(titles)
            status_var.set("Edytuj tytuly i zapisz lub skopiuj prompt do Cursora.")
            _enable_form()

        _schedule_ui(populate)

    threading.Thread(target=_load, daemon=True, name="zmietytuly-load-titles").start()


def _show_product_list(
    host: tk.Misc,
    *,
    clipboard_root: tk.Misc,
    on_cancel: Callable[[], None] | None = None,
    selected_product_id: int | None = None,
) -> None:
    _clear_host(host)
    _set_wizard_title(host, 1)
    ws = _wizard_state(host)
    if isinstance(host, (tk.Tk, tk.Toplevel)):
        position_toplevel_screen_center(host, 980, 680)
        host.minsize(760, 520)

    if selected_product_id is not None:
        ws["selected_product_id"] = selected_product_id

    state: dict[str, object] = {
        "rows": list(ws.get("rows") or []),
        "row_by_iid": {},
        "sort_col": ws.get("sort_col") or "surname",
        "sort_reverse": bool(ws.get("sort_reverse")),
        "selected_product_id": ws.get("selected_product_id"),
        "title_marks": load_title_update_marks(),
    }
    sort_state: dict[str, bool] = dict(ws.get("sort_state") or {})
    filter_mode_var = tk.StringVar(value=str(ws.get("title_filter_mode") or "all"))

    top = ttk.LabelFrame(
        host,
        text="Produkty ze sklepu (Ctrl+klik lub Shift+klik — wiele zaznaczen)",
        padding=(10, 8),
    )
    top.pack(fill="both", expand=True, padx=12, pady=(12, 6))

    filter_bar = ttk.Frame(top)
    filter_bar.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar(value=str(ws.get("filter") or ""))
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=32).pack(side="left", padx=(6, 8))
    count_var = tk.StringVar(value="(ladowanie...)")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="Pobieram produkty z Shopify...")
    ttk.Label(filter_bar, textvariable=progress_var, foreground="#444").pack(side="right")

    mark_btn = ttk.Button(
        filter_bar,
        text="Oznacz: tytul po aktualizacji",
        state="disabled",
    )
    mark_btn.pack(side="right", padx=(8, 0))

    filter_btns_frame = ttk.Frame(top)
    filter_btns_frame.pack(fill="x", pady=(0, 4))
    ttk.Label(filter_btns_frame, text="Pokaz:").pack(side="left")
    filter_btns: dict[str, ttk.Button] = {}

    table_frame = ttk.Frame(top)
    table_frame.pack(fill="both", expand=True)
    cols = ("title_status", "surname", "firstname", "painting_title", "handle", "image_filename")
    headings = {
        "title_status": "Tytul",
        "surname": "Nazwisko",
        "firstname": "Imie",
        "painting_title": "Tytul obrazu",
        "handle": "Handle",
        "image_filename": "Plik glownej grafiki",
    }
    widths = {
        "title_status": 130,
        "surname": 150,
        "firstname": 130,
        "painting_title": 280,
        "handle": 150,
        "image_filename": 220,
    }

    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=14, selectmode="extended")

    def _update_sort_headings(*, active: str | None = None, reverse: bool = False) -> None:
        arrow_up = " \u25b2"
        arrow_down = " \u25bc"
        for c in cols:
            base = headings[c]
            if c == active:
                base += arrow_down if reverse else arrow_up
            if c in ("title_status", "surname", "firstname", "painting_title"):
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

    active_sort = str(state.get("sort_col") or "surname")
    active_reverse = bool(state.get("sort_reverse"))
    _update_sort_headings(active=active_sort, reverse=active_reverse)
    for c in cols:
        tree.column(c, width=widths[c], anchor="w", stretch=(c == "painting_title"))
    tree.tag_configure("title_updated", background="#e8f5e9", foreground="#1b5e20")
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    def _set_list_filter(mode: str) -> None:
        filter_mode_var.set(mode)
        for m, btn in filter_btns.items():
            btn.state(["pressed"] if m == mode else ["!pressed"])
        _refresh_tree()

    for label, mode in (
        ("Wszystkie", "all"),
        ("Po aktualizacji", "updated"),
        ("Bez oznaczenia", "not_updated"),
    ):
        btn = ttk.Button(
            filter_btns_frame,
            text=label,
            width=18,
            command=lambda m=mode: _set_list_filter(m),
        )
        btn.pack(side="left", padx=(4, 0))
        filter_btns[mode] = btn
    initial_filter = str(filter_mode_var.get() or "all")
    if initial_filter not in filter_btns:
        initial_filter = "all"
    filter_mode_var.set(initial_filter)
    filter_btns[initial_filter].state(["pressed"])

    _build_stash_panel(host, clipboard_root=clipboard_root, ws=ws)

    bottom = ttk.Frame(host, padding=(12, 8))
    bottom.pack(fill="x")
    next_btn = ttk.Button(bottom, text="Dalej", state="disabled")
    next_btn.pack(side="right")
    ttk.Button(bottom, text="Zamknij", command=lambda: on_cancel and on_cancel()).pack(
        side="right", padx=(0, 8),
    )
    refresh_btn = ttk.Button(bottom, text="Odswiez liste produktow")
    refresh_btn.pack(side="left")
    download_btn = ttk.Button(bottom, text="Pobierz grafiki zaznaczonych", state="disabled")
    download_btn.pack(side="left", padx=(8, 0))

    def _copy_gemini_session_prompt() -> None:
        try:
            host.clipboard_clear()
            host.clipboard_append(GEMINI_CHAT_SESSION_START)
            host.update()
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return
        show_toast(
            clipboard_root,
            "Prompt startowy Gemini — wklej w nowym czacie przed zdjeciami",
            duration_ms=2200,
        )

    ttk.Button(
        bottom,
        text="Prompt startowy Gemini",
        command=_copy_gemini_session_prompt,
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        bottom,
        text="Lista promptow",
        command=lambda: _open_prompt_list_dialog(host, clipboard_root=clipboard_root),
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        bottom,
        text="Wpisz recznie",
        command=lambda: _show_manual_ref(
            host,
            clipboard_root=clipboard_root,
            on_back=lambda: _show_product_list(
                host, clipboard_root=clipboard_root, on_cancel=on_cancel,
            ),
            on_cancel=on_cancel,
        ),
    ).pack(side="left", padx=(8, 0))

    def _selected_row() -> dict | None:
        sel = tree.selection()
        if not sel:
            return None
        return state["row_by_iid"].get(sel[0])

    def _selected_rows() -> list[dict]:
        rows: list[dict] = []
        for iid in tree.selection():
            row = state["row_by_iid"].get(iid)
            if row:
                rows.append(row)
        return rows

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
        marks = state["title_marks"]
        if not isinstance(marks, set):
            marks = set()
            state["title_marks"] = marks
        for pid in pids:
            if marked:
                marks.add(pid)
            else:
                marks.discard(pid)

    def _update_mark_btn() -> None:
        rows = _selected_rows()
        pids = _selected_product_ids()
        n = len(pids)
        if n == 0:
            mark_btn.configure(state="disabled", text="Oznacz: tytul po aktualizacji")
            return
        marks = state["title_marks"]
        if not isinstance(marks, set):
            marks = set()
        marked_count = sum(1 for pid in pids if pid in marks)
        if n == 1:
            if marked_count:
                mark_btn.configure(
                    state="normal",
                    text="Odznacz «tytul po aktualizacji»",
                )
            else:
                mark_btn.configure(
                    state="normal",
                    text="Oznacz: tytul po aktualizacji",
                )
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

    def _toggle_title_mark(*, product_id: int | None = None) -> None:
        if product_id is not None:
            pids = [int(product_id)]
        else:
            pids = _selected_product_ids()
        if not pids:
            messagebox.showwarning(APP_TITLE, "Wybierz produkt(y) z listy.", parent=host)
            return
        if len(pids) == 1:
            marked = toggle_title_update_mark(pids[0])
            _sync_local_title_marks(pids, marked=marked)
        else:
            marks = state["title_marks"]
            if not isinstance(marks, set):
                marks = set()
            all_marked = all(pid in marks for pid in pids)
            marked = not all_marked
            set_title_update_marks_batch(pids, marked=marked)
            _sync_local_title_marks(pids, marked=marked)
        _refresh_tree()
        _update_mark_btn()
        action = "Oznaczono" if marked else "Odznaczono"
        suffix = f" ({len(pids)})" if len(pids) > 1 else ""
        show_toast(host, f"{action}: tytul po aktualizacji{suffix}", duration_ms=1200)

    mark_btn.configure(command=lambda: _toggle_title_mark())

    def _row_sort_key(row: dict) -> tuple:
        col = str(state.get("sort_col") or "surname")
        marks = state["title_marks"]
        if not isinstance(marks, set):
            marks = set()
        pid = int(row.get("product_id") or 0)
        is_marked = pid in marks
        status = TITLE_UPDATED_LABEL if is_marked else ""
        if col == "title_status":
            return (
                status.lower(),
                str(row.get("surname") or "").lower(),
                str(row.get("firstname") or "").lower(),
                str(row.get("painting_title") or "").lower(),
            )
        val = str(row.get(col) or "").lower()
        if col == "surname":
            return product_catalog_sort_key(row)
        if col == "firstname":
            return (
                val,
                str(row.get("surname") or "").lower(),
                (row.get("painting_title") or "").lower(),
            )
        if col == "painting_title":
            return (
                val,
                str(row.get("surname") or "").lower(),
                str(row.get("firstname") or "").lower(),
            )
        return (val, str(row.get("surname") or "").lower())

    def _persist_list_state() -> None:
        ws["rows"] = list(state.get("rows") or [])
        ws["sort_col"] = state.get("sort_col")
        ws["sort_reverse"] = state.get("sort_reverse")
        ws["sort_state"] = dict(sort_state)
        ws["filter"] = filter_var.get()
        ws["title_filter_mode"] = filter_mode_var.get()
        ws["selected_product_id"] = state.get("selected_product_id")

    def _refresh_tree() -> None:
        marks = state["title_marks"]
        if not isinstance(marks, set):
            marks = load_title_update_marks()
            state["title_marks"] = marks
        filter_mode = filter_mode_var.get()
        selected_pid: int | None = None
        raw_pid = state.get("selected_product_id")
        if raw_pid is not None:
            try:
                selected_pid = int(raw_pid) or None
            except (TypeError, ValueError):
                selected_pid = None
        if selected_pid is None:
            sel = tree.selection()
            if sel:
                old_row = state["row_by_iid"].get(sel[0])
                if old_row:
                    selected_pid = int(old_row.get("product_id") or 0) or None

        tree.delete(*tree.get_children())
        state["row_by_iid"] = {}
        q = filter_var.get().strip().lower()
        visible_rows: list[dict] = []
        marked_total = 0
        unmarked_total = 0
        for row in state["rows"]:
            pid = int(row.get("product_id") or 0)
            is_marked = pid in marks
            if is_marked:
                marked_total += 1
            else:
                unmarked_total += 1
            if filter_mode == "updated" and not is_marked:
                continue
            if filter_mode == "not_updated" and is_marked:
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

        selected_iid = None

        for row in visible_rows:
            pid = int(row.get("product_id") or 0)
            is_marked = pid in marks
            status = TITLE_UPDATED_LABEL if is_marked else ""
            tags = ("title_updated",) if is_marked else ()
            iid = tree.insert(
                "",
                "end",
                values=(
                    status,
                    row.get("surname", ""),
                    row.get("firstname", ""),
                    row.get("painting_title", ""),
                    row.get("handle", ""),
                    row.get("image_filename", ""),
                ),
                tags=tags,
            )
            state["row_by_iid"][iid] = row
            if selected_pid is not None and pid == selected_pid:
                selected_iid = iid

        if selected_iid and tree.exists(selected_iid):
            tree.selection_set(selected_iid)
            tree.focus(selected_iid)
            tree.see(selected_iid)
            state["selected_product_id"] = selected_pid

        count_var.set(
            f"{len(visible_rows)} / {len(state['rows'])} produkt(ow)"
            + f"  |  Po aktualizacji: {marked_total}, do zmiany: {unmarked_total}"
        )
        _persist_list_state()
        _update_mark_btn()

    def _go_to_titles_from_row(row: dict | None) -> None:
        if not row:
            messagebox.showinfo(APP_TITLE, "Zaznacz produkt na liscie.", parent=host)
            return
        painting_title = str(row.get("painting_title") or "").strip()
        artist_name = str(row.get("artist") or "").strip()
        if not painting_title or not artist_name:
            messagebox.showerror(
                APP_TITLE,
                "Brak tytulu obrazu lub artysty w danych produktu.",
                parent=host,
            )
            return
        pid = int(row.get("product_id") or 0)
        state["selected_product_id"] = pid or None
        _persist_list_state()

        def _return_to_list() -> None:
            _show_product_list(
                host,
                clipboard_root=clipboard_root,
                on_cancel=on_cancel,
                selected_product_id=pid or None,
            )

        _show_step2(
            host,
            clipboard_root=clipboard_root,
            painting_title=painting_title,
            artist_name=artist_name,
            product_id=pid,
            on_back=_return_to_list,
            on_finish=_return_to_list,
            on_cancel=on_cancel,
        )

    def _on_tree_select(_event: tk.Event | None = None) -> None:
        rows = _selected_rows()
        if len(rows) == 1:
            try:
                state["selected_product_id"] = int(rows[0].get("product_id") or 0) or None
            except (TypeError, ValueError):
                state["selected_product_id"] = None
            _persist_list_state()
        next_btn.configure(state="normal" if len(rows) == 1 else "disabled")
        download_btn.configure(state="normal" if rows else "disabled")
        _update_mark_btn()

    def _on_tree_double_click(event: tk.Event) -> str:
        item = tree.identify_row(event.y)
        if not item:
            return ""
        tree.selection_set(item)
        tree.focus(item)
        tree.see(item)
        _go_to_titles_from_row(state["row_by_iid"].get(item))
        return "break"

    def _copy_selected_image() -> None:
        row = _selected_row()
        if not row:
            messagebox.showinfo(APP_TITLE, "Zaznacz produkt na liscie.", parent=host)
            return
        image_url = (row.get("image_src") or "").strip()
        pid = int(row.get("product_id") or 0)

        def work() -> None:
            nonlocal image_url
            try:
                if not image_url:
                    image_url = _resolve_row_image_url(row)
                if not image_url:
                    raise ValueError("Brak grafiki glownej dla tego produktu.")
                copy_image_url_to_clipboard(image_url)
            except Exception as exc:
                host.after(
                    0,
                    lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=host),
                )
                return
            host.after(
                0,
                lambda: show_toast(host, "Grafika skopiowana do schowka", duration_ms=1600),
            )

        threading.Thread(target=work, daemon=True, name="zmietytuly-copy-image").start()

    def _download_selected_images() -> None:
        rows = _selected_rows()
        if not rows:
            messagebox.showinfo(APP_TITLE, "Zaznacz co najmniej jeden produkt.", parent=host)
            return
        dest_dir = filedialog.askdirectory(
            title="Zapisz grafiki zaznaczonych produktow",
            parent=host,
        )
        if not dest_dir:
            return
        folder = Path(dest_dir)
        total = len(rows)
        download_btn.configure(state="disabled")
        refresh_btn.configure(state="disabled")
        next_btn.configure(state="disabled")
        progress_var.set(f"Pobieram grafiki (0/{total})...")

        def work() -> None:
            saved: list[Path] = []
            errors: list[str] = []
            used_stems: set[str] = set()
            for idx, row in enumerate(rows, start=1):
                label = str(row.get("painting_title") or row.get("product_id") or "?")
                host.after(
                    0,
                    lambda i=idx, n=total: progress_var.set(f"Pobieram grafiki ({i}/{n})..."),
                )
                try:
                    image_url = _resolve_row_image_url(row)
                    if not image_url:
                        raise ValueError("Brak grafiki glownej.")
                    ext = image_url_extension(image_url)
                    stem = _safe_download_stem(row)
                    while stem in used_stems:
                        stem = f"{stem} ({idx})"
                    used_stems.add(stem)
                    dest = _unique_download_path(folder, stem, ext)
                    save_image_url_to_file(image_url, dest)
                    saved.append(dest)
                except Exception as exc:
                    errors.append(f"{label}: {exc}")

            def done() -> None:
                _on_tree_select()
                refresh_btn.configure(state="normal")
                if saved:
                    progress_var.set(
                        f"Zapisano {len(saved)} grafik w: {folder}",
                    )
                else:
                    progress_var.set("Nie zapisano zadnej grafiki.")
                if errors:
                    preview = "\n".join(errors[:8])
                    if len(errors) > 8:
                        preview += f"\n... i {len(errors) - 8} wiecej"
                    messagebox.showwarning(
                        APP_TITLE,
                        f"Zapisano {len(saved)} z {total} grafik.\n\nBledy:\n{preview}",
                        parent=host,
                    )
                elif saved:
                    show_toast(
                        host,
                        f"Zapisano {len(saved)} grafik — otwieram folder",
                        duration_ms=2200,
                    )
                    _open_folder(folder)
                else:
                    messagebox.showerror(
                        APP_TITLE,
                        "Nie udalo sie pobrac zadnej grafiki.",
                        parent=host,
                    )

            host.after(0, done)

        threading.Thread(
            target=work, daemon=True, name="zmietytuly-download-images",
        ).start()

    def _edit_titles_languages() -> None:
        row = _selected_row()
        if not row:
            messagebox.showinfo(APP_TITLE, "Zaznacz jeden produkt na liscie.", parent=host)
            return

        def _on_saved(titles: dict[str, str]) -> None:
            new_pl = (titles.get("pl") or "").strip()
            if new_pl:
                row["painting_title"] = new_pl
            pid = int(row.get("product_id") or 0)
            marks = state["title_marks"]
            if isinstance(marks, set) and pid:
                marks.add(pid)
            _refresh_tree()

        _open_title_editor_dialog(host, row=row, on_saved=_on_saved)

    def _on_tree_context_menu(event: tk.Event) -> None:
        item = tree.identify_row(event.y)
        if item:
            if item not in tree.selection():
                tree.selection_set(item)
            tree.focus(item)
            tree.see(item)
            _on_tree_select()
        rows = _selected_rows()
        menu = tk.Menu(host, tearoff=0)
        if len(rows) == 1:
            menu.add_command(
                label="Edytuj tytuly w jezykach...",
                command=_edit_titles_languages,
            )
            menu.add_separator()
        if rows:
            if len(rows) == 1:
                menu.add_command(label="Kopiuj grafike", command=_copy_selected_image)
            label = (
                "Pobierz grafike zaznaczonej"
                if len(rows) == 1
                else f"Pobierz grafiki zaznaczonych ({len(rows)})"
            )
            menu.add_command(label=label, command=_download_selected_images)
            menu.add_separator()
            n = len(rows)
            menu.add_command(
                label=(
                    "Oznacz: tytul po aktualizacji"
                    if n == 1
                    else f"Oznacz zaznaczone ({n})"
                ),
                command=lambda: _set_title_marks(marked=True),
            )
            menu.add_command(
                label=(
                    "Odznacz «tytul po aktualizacji»"
                    if n == 1
                    else f"Odznacz zaznaczone ({n})"
                ),
                command=lambda: _set_title_marks(marked=False),
            )
        if menu.index("end") is None:
            return
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _load_products() -> None:
        progress_var.set("Pobieram produkty...")
        refresh_btn.configure(state="disabled")
        next_btn.configure(state="disabled")

        def work() -> None:
            try:
                rows = load_product_catalog_rows(
                    on_progress=lambda s: host.after(0, lambda m=s: progress_var.set(m)),
                )
            except Exception as exc:
                host.after(0, lambda e=exc: messagebox.showerror(APP_TITLE, str(e), parent=host))
                host.after(0, lambda: progress_var.set("Blad pobierania."))
                host.after(0, lambda: refresh_btn.configure(state="normal"))
                return

            def done() -> None:
                state["rows"] = rows
                state["title_marks"] = load_title_update_marks()
                _refresh_tree()
                progress_var.set(f"Gotowe — {len(rows)} produkt(ow).")
                refresh_btn.configure(state="normal")
                _on_tree_select()

            host.after(0, done)

        threading.Thread(target=work, daemon=True, name="zmietytuly-load-products").start()

    filter_var.trace_add("write", lambda *_: _refresh_tree())
    next_btn.configure(command=lambda: _go_to_titles_from_row(_selected_row()))
    download_btn.configure(command=_download_selected_images)
    refresh_btn.configure(command=_load_products)
    tree.bind("<<TreeviewSelect>>", _on_tree_select)
    tree.bind("<Double-1>", _on_tree_double_click, add="+")
    tree.bind("<Double-Button-1>", _on_tree_double_click, add="+")
    tree.bind("<Button-3>", _on_tree_context_menu)
    host.bind("<Escape>", lambda _e: on_cancel and on_cancel())

    if state["rows"]:
        _refresh_tree()
        progress_var.set(f"Gotowe — {len(state['rows'])} produkt(ow).")
        _on_tree_select()
    else:
        _load_products()


def open_title_change_wizard(
    parent: tk.Misc,
    *,
    painting: str = "",
    artist: str = "",
) -> None:
    """Otwiera kreator w osobnym oknie (np. z innego komponentu)."""
    win = tk.Toplevel(parent)
    win.transient(parent)
    win.grab_set()
    if painting.strip() and artist.strip():
        _show_step2(
            win,
            clipboard_root=parent,
            painting_title=painting.strip(),
            artist_name=artist.strip(),
            on_cancel=win.destroy,
        )
    else:
        _show_product_list(win, clipboard_root=parent, on_cancel=win.destroy)


def main() -> None:
    root = tk.Tk()
    _show_product_list(root, clipboard_root=root, on_cancel=root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
