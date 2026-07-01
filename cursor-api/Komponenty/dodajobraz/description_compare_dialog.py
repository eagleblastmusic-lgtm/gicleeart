"""Okno «Porownywarka» — wklejanie wersji akapitu obok edycji oryginalu."""

from __future__ import annotations

import threading
import tkinter as tk
from io import BytesIO
from tkinter import messagebox, scrolledtext, ttk
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .description_update import (
    COMPARE_VERSION_SLOTS,
    compare_version_label,
    _AKAPITY_MAX,
    get_compare_bucket,
    parse_full_akapity_json,
)

try:
    from PIL import Image, ImageTk

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

_PARA_SLOTS = _AKAPITY_MAX
_VERSION_SLOTS = COMPARE_VERSION_SLOTS
_APP_TITLE = "Aktualizuj opis"
_THUMB_SIZE = (120, 90)
_PREVIEW_MAX = (960, 720)
_FETCH_HEADERS = {"User-Agent": "GicleeApp-DescriptionCompare/1.0"}


_COMPARE_WIN_MIN_W = 920
_COMPARE_WIN_MIN_H = 640
_COMPARE_TEXT_HEIGHT = 11
_COMPARE_UNDO_LIMIT = 100


def _reset_text_undo(widget: tk.Text) -> None:
    """Czysci stos cofania po przelaczeniu akapitu / wersji (nowy kontekst edycji)."""
    try:
        widget.edit_reset()
    except tk.TclError:
        pass


def _bind_text_undo_redo(widget: tk.Text) -> None:
    """Ctrl+Z / Ctrl+Y w polu tekstowym — przywraca usuniety fragment itd."""

    def _undo(_event: tk.Event) -> str:
        try:
            widget.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def _redo(_event: tk.Event) -> str:
        try:
            widget.edit_redo()
        except tk.TclError:
            pass
        return "break"

    for seq in ("<Control-z>", "<Control-Z>"):
        widget.bind(seq, _undo, add="+")
    for seq in ("<Control-y>", "<Control-Y>", "<Control-Shift-z>", "<Control-Shift-Z>"):
        widget.bind(seq, _redo, add="+")


def _fit_compare_window(win: tk.Misc) -> None:
    """Rozmiar okna wg zawartosci, z limitem ekranu — dolne przyciski zawsze widoczne."""
    win.update_idletasks()
    sw = max(800, int(win.winfo_screenwidth()))
    sh = max(600, int(win.winfo_screenheight()))
    margin = 48
    w = max(_COMPARE_WIN_MIN_W, min(int(win.winfo_reqwidth()) + 8, sw - margin))
    h = max(_COMPARE_WIN_MIN_H, min(int(win.winfo_reqheight()) + 12, sh - margin))
    position_toplevel_screen_center(win, w, h)


def open_description_compare_dialog(
    parent: tk.Misc,
    *,
    get_context: Callable[[], dict[str, Any]],
    get_paragraph_text: Callable[[int], str],
    apply_paragraph: Callable[[int, str], None],
    compare_store: dict[int, dict[str, Any]],
    persist_compare_store: Callable[[], None] | None = None,
    after_apply_all: Callable[[], None] | None = None,
    on_apply_all_paragraphs: Callable[[], None] | None = None,
    default_version_idx: int = 0,
) -> None:
    """Otwiera porownywacke akapitow.

    compare_store: product_id -> locale -> {versions: {para: [10 str]}, working: {para: str}}.
    """
    ctx = get_context()
    if not ctx.get("ok"):
        messagebox.showwarning(_APP_TITLE, ctx.get("error") or "Brak kontekstu.", parent=parent)
        return

    product_id = int(ctx["product_id"])
    locale = str(ctx["locale"])
    bucket = get_compare_bucket(compare_store, product_id=product_id, locale=locale)
    product_title = str(ctx.get("product_title") or "")
    locale_label = str(ctx.get("locale_label") or locale.upper())
    image_url = str(ctx.get("image_url") or "").strip()

    win = tk.Toplevel(parent)
    win.title("Porownywarka akapitow")
    win.minsize(_COMPARE_WIN_MIN_W, _COMPARE_WIN_MIN_H)
    win.transient(parent)

    ui: dict[str, Any] = {
        "locale": locale,
        "para_idx": max(0, min(int(ctx.get("paragraph_index", 0)), _PARA_SLOTS - 1)),
        "version_idx": max(0, min(int(default_version_idx), _VERSION_SLOTS - 1)),
        "working_by_para": {},
        "close_on_rmb": False,
    }

    header = ttk.Frame(win, padding=(12, 10))
    header.pack(fill="x")
    header_top = ttk.Frame(header)
    header_top.pack(fill="x")
    header_text = ttk.Frame(header_top)
    header_text.pack(side="left", fill="x", expand=True)
    title_var = tk.StringVar(
        value=f"{product_title} — {locale_label}" if product_title else locale_label,
    )
    ttk.Label(header_text, textvariable=title_var, font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttk.Label(
        header_text,
        text=(
            f"Wklej rozne wersje akapitu (1–6, ZO1, ZO2, G1, G2) w wybranym slocie Wersji, "
            "porownaj z oryginalem po prawej. W polach tekstu Ctrl+V = wklejanie, "
            "Ctrl+Z / Ctrl+Y = cofnij / ponow (historia edycji); "
            "poza nimi Ctrl+V = Wklej calosc; po wklejeniu calosci PPM zamyka okno."
        ),
        foreground="#555",
        wraplength=680,
    ).pack(anchor="w", pady=(4, 0))
    thumb_label = tk.Label(
        header_top,
        text="(brak obrazu)" if not image_url else "Laduje...",
        relief="groove",
        bd=1,
        bg="#fafafa",
        fg="#999",
        width=16,
        height=5,
        justify="center",
        anchor="center",
        cursor="hand2" if image_url else "arrow",
    )
    thumb_label.pack(side="right", padx=(12, 0))
    ui["thumb_photo"] = None
    ui["preview_photo"] = None
    ui["image_url"] = image_url

    bars = ttk.Frame(win, padding=(12, 0))
    bars.pack(fill="x", pady=(8, 4))

    para_bar = ttk.Frame(bars)
    para_bar.pack(fill="x", pady=(0, 6))
    ttk.Label(para_bar, text="Akapit:").pack(side="left")
    para_btns: dict[int, ttk.Button] = {}

    ver_bar = ttk.Frame(bars)
    ver_bar.pack(fill="x")
    ttk.Label(ver_bar, text="Wersja:").pack(side="left")
    ver_btns: dict[int, ttk.Button] = {}
    ttk.Button(
        ver_bar,
        text="Wklej calosc",
        command=lambda: _paste_full_from_clipboard(),
    ).pack(side="left", padx=(16, 0))

    pane = ttk.Panedwindow(win, orient="horizontal")
    pane.pack(fill="both", expand=True, padx=12, pady=(4, 8))

    left = ttk.LabelFrame(pane, text="Wersja do porownania (wklej)", padding=6)
    right = ttk.LabelFrame(pane, text="Oryginal / roboczy (edytuj)", padding=6)
    pane.add(left, weight=1)
    pane.add(right, weight=1)

    _text_undo_kw: dict[str, Any] = {
        "undo": True,
        "maxundo": _COMPARE_UNDO_LIMIT,
        "autoseparator": True,
    }
    version_text = scrolledtext.ScrolledText(
        left,
        height=_COMPARE_TEXT_HEIGHT,
        wrap="word",
        font=("Segoe UI", 10),
        **_text_undo_kw,
    )
    version_text.pack(fill="both", expand=True)

    left_btns = ttk.Frame(left)
    left_btns.pack(fill="x", pady=(6, 0))
    ttk.Button(left_btns, text="Wklej ze schowka", command=lambda: _paste_clipboard(version_text)).pack(
        side="left",
    )
    ttk.Button(
        left_btns,
        text="Kopiuj wersje do roboczego",
        command=lambda: _copy_version_to_working(),
    ).pack(side="left", padx=(8, 0))

    working_text = scrolledtext.ScrolledText(
        right,
        height=_COMPARE_TEXT_HEIGHT,
        wrap="word",
        font=("Segoe UI", 10),
        **_text_undo_kw,
    )
    working_text.pack(fill="both", expand=True)

    right_btns = ttk.Frame(right)
    right_btns.pack(fill="x", pady=(6, 0))
    ttk.Button(
        right_btns,
        text="Odswiez z opisu",
        command=lambda: _reload_working_from_main(),
    ).pack(side="left")
    ttk.Button(
        right_btns,
        text="Wklej ze schowka",
        command=lambda: _paste_clipboard(working_text),
    ).pack(side="left", padx=(8, 0))

    bottom = ttk.Frame(win, padding=(12, 0, 12, 12))
    bottom.pack(fill="x")
    ttk.Button(bottom, text="Zastosuj do opisu", command=lambda: _apply_to_main()).pack(side="right")
    ttk.Button(
        bottom,
        text="Zastosuj wszystkie akapity",
        command=lambda: _apply_all_to_main(),
    ).pack(side="right", padx=(0, 8))
    def _close() -> None:
        _save_panes()
        win.destroy()

    ttk.Button(bottom, text="Zamknij", command=_close).pack(side="right", padx=(0, 8))

    def _versions_map() -> dict[int, list[str]]:
        raw = bucket.get("versions")
        if not isinstance(raw, dict):
            bucket["versions"] = {}
            return bucket["versions"]
        return raw

    def _slot_versions(p_idx: int) -> list[str]:
        store = _versions_map()
        if p_idx not in store:
            store[p_idx] = [""] * _VERSION_SLOTS
        while len(store[p_idx]) < _VERSION_SLOTS:
            store[p_idx].append("")
        return store[p_idx]

    def _save_panes() -> None:
        p_idx = ui["para_idx"]
        v_idx = ui["version_idx"]
        _slot_versions(p_idx)[v_idx] = version_text.get("1.0", "end-1c")
        working = working_text.get("1.0", "end-1c")
        ui["working_by_para"][p_idx] = working
        working_map = bucket.get("working")
        if not isinstance(working_map, dict):
            bucket["working"] = {}
            working_map = bucket["working"]
        working_map[p_idx] = working
        if persist_compare_store:
            persist_compare_store()

    def _left_version_text(p_idx: int, v_idx: int) -> str:
        row = _slot_versions(p_idx)
        return row[v_idx] if v_idx < len(row) else ""

    def _load_panes(*, working: str | None = None) -> None:
        p_idx = ui["para_idx"]
        v_idx = ui["version_idx"]
        version_text.delete("1.0", "end")
        version_text.insert("1.0", _left_version_text(p_idx, v_idx))
        if working is None:
            if p_idx in ui["working_by_para"]:
                working = ui["working_by_para"][p_idx]
            else:
                working = get_paragraph_text(p_idx)
        working_text.delete("1.0", "end")
        working_text.insert("1.0", working)
        ui["working_by_para"][p_idx] = working
        _update_para_btns()
        _update_ver_btns()
        left.configure(
            text=f"Wersja do porownania — akapit {p_idx + 1}, {compare_version_label(v_idx)}",
        )
        right.configure(text=f"Oryginal / roboczy — akapit {p_idx + 1}")
        _reset_text_undo(version_text)
        _reset_text_undo(working_text)

    def _update_para_btns() -> None:
        idx = ui["para_idx"]
        for i, btn in para_btns.items():
            btn.state(["!pressed"] if i != idx else ["pressed"])

    def _update_ver_btns() -> None:
        idx = ui["version_idx"]
        for i, btn in ver_btns.items():
            btn.state(["!pressed"] if i != idx else ["pressed"])

    def _select_paragraph(p_idx: int) -> None:
        _save_panes()
        ui["para_idx"] = max(0, min(int(p_idx), _PARA_SLOTS - 1))
        _load_panes()

    def _select_version(v_idx: int) -> None:
        _save_panes()
        ui["version_idx"] = max(0, min(int(v_idx), _VERSION_SLOTS - 1))
        _load_panes()

    def _goto_version(v_idx: int) -> None:
        """Przelacza wersje bez zapisu lewego panelu (po masowym wklejeniu akapitow)."""
        ui["version_idx"] = max(0, min(int(v_idx), _VERSION_SLOTS - 1))
        _load_panes()

    def _apply_full_akapity(akapity: list[str]) -> None:
        _save_panes()
        v_idx = ui["version_idx"]
        for i, text in enumerate(akapity[:_PARA_SLOTS]):
            _slot_versions(i)[v_idx] = text
        n = len(akapity[:_PARA_SLOTS])
        pasted_ver = compare_version_label(v_idx)
        next_v_idx = min(v_idx + 1, _VERSION_SLOTS - 1)
        _goto_version(next_v_idx)
        if persist_compare_store:
            persist_compare_store()
        if next_v_idx != v_idx:
            toast = (
                f"Wklejono {n} akapitow do {pasted_ver} "
                f"— przejscie do {compare_version_label(next_v_idx)}"
            )
        else:
            toast = f"Wklejono {n} akapitow do {pasted_ver} (ostatni slot)"
        ui["close_on_rmb"] = True
        show_toast(win, toast, duration_ms=1600)

    def _paste_full_from_clipboard() -> None:
        try:
            raw = win.clipboard_get().strip()
        except tk.TclError:
            messagebox.showwarning(_APP_TITLE, "Schowek jest pusty.", parent=win)
            return
        if not raw:
            messagebox.showwarning(_APP_TITLE, "Schowek jest pusty.", parent=win)
            return
        try:
            akapity = parse_full_akapity_json(raw)
        except ValueError as exc:
            messagebox.showerror(_APP_TITLE, str(exc), parent=win)
            return
        _apply_full_akapity(akapity)

    def _reload_working_from_main() -> None:
        text = get_paragraph_text(ui["para_idx"])
        working_text.delete("1.0", "end")
        working_text.insert("1.0", text)
        ui["working_by_para"][ui["para_idx"]] = text
        show_toast(win, "Odswiezono z opisu glownego", duration_ms=1100)

    def _copy_version_to_working() -> None:
        text = version_text.get("1.0", "end-1c")
        working_text.delete("1.0", "end")
        working_text.insert("1.0", text)
        ui["working_by_para"][ui["para_idx"]] = text
        show_toast(win, "Skopiowano wersje do roboczego", duration_ms=1100)

    def _apply_to_main() -> None:
        _save_panes()
        text = working_text.get("1.0", "end-1c").strip()
        apply_paragraph(ui["para_idx"], text)
        show_toast(win, f"Zastosowano akapit {ui['para_idx'] + 1} w opisie", duration_ms=1300)

    def _apply_all_to_main() -> None:
        _save_panes()
        for i in range(_PARA_SLOTS):
            if i in ui["working_by_para"]:
                text = ui["working_by_para"][i]
            else:
                text = get_paragraph_text(i)
            apply_paragraph(i, (text or "").strip())
        if on_apply_all_paragraphs:
            on_apply_all_paragraphs()
        _close()
        if after_apply_all:
            parent.after(0, after_apply_all)
        else:
            show_toast(
                parent,
                f"Zastosowano wszystkie akapity (1–{_PARA_SLOTS}) w opisie",
                duration_ms=1500,
            )

    def _shopify_sized_url(url: str, *, width: int) -> str:
        if not url:
            return ""
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}width={width}"

    def _fetch_image_bytes(url: str) -> bytes:
        req = Request(url, headers=_FETCH_HEADERS)
        with urlopen(req, timeout=25) as resp:
            return resp.read()

    def _pil_from_url(url: str, max_size: tuple[int, int]) -> Any:
        if not _HAS_PIL:
            raise RuntimeError("Brak Pillow — zainstaluj: pip install Pillow")
        raw = _fetch_image_bytes(url)
        with Image.open(BytesIO(raw)) as im:
            im = im.copy()
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.thumbnail(max_size, Image.Resampling.LANCZOS)
            return im

    def _set_thumb_error(msg: str) -> None:
        if not win.winfo_exists():
            return
        thumb_label.configure(
            image="",
            text=msg,
            width=16,
            height=5,
            cursor="arrow",
        )

    def _set_thumb_photo(photo: Any) -> None:
        if not win.winfo_exists():
            return
        ui["thumb_photo"] = photo
        thumb_label.configure(image=photo, text="", width=0, height=0, cursor="hand2")

    def _load_thumbnail() -> None:
        if not image_url or not _HAS_PIL:
            if image_url and not _HAS_PIL:
                thumb_label.configure(text="Brak Pillow\n(klik = info)")
            return

        def work() -> None:
            try:
                url = _shopify_sized_url(image_url, width=max(_THUMB_SIZE) * 2)
                pil = _pil_from_url(url, _THUMB_SIZE)
                photo = ImageTk.PhotoImage(pil)
            except (OSError, URLError, RuntimeError, ValueError) as exc:
                win.after(0, lambda e=exc: _set_thumb_error(f"Miniatura:\n{e}"[:80]))
                return
            win.after(0, lambda p=photo: _set_thumb_photo(p))

        threading.Thread(target=work, daemon=True, name="compare-thumb").start()

    def _open_image_preview() -> None:
        if not image_url:
            return
        if not _HAS_PIL:
            messagebox.showinfo(
                _APP_TITLE,
                "Brak Pillow — powiekszenie nie zadziala.\nZainstaluj: pip install Pillow",
                parent=win,
            )
            return
        preview = tk.Toplevel(win)
        preview.title(f"Obraz: {product_title or 'produkt'}")
        position_toplevel_screen_center(preview, 1000, 760)
        preview.transient(win)
        preview.minsize(420, 320)
        lbl = tk.Label(preview, text="Laduje obraz...", bg="#222", fg="#bbb")
        lbl.pack(fill="both", expand=True, padx=8, pady=8)
        hint = ttk.Label(
            preview,
            text="Kliknij obraz lub nacisnij Escape, aby zamknac.",
            foreground="#666",
        )
        hint.pack(fill="x", padx=8, pady=(0, 8))

        def _close_preview() -> None:
            if preview.winfo_exists():
                preview.destroy()

        def _apply_large_photo(photo: Any) -> None:
            if not preview.winfo_exists():
                return
            ui["preview_photo"] = photo
            lbl.configure(image=photo, text="", bg="#111", cursor="hand2")
            lbl.bind("<Button-1>", lambda _e: _close_preview())

        def _show_large_error(exc: BaseException) -> None:
            if not preview.winfo_exists():
                return
            lbl.configure(text=f"Blad: {exc}", bg="#400", fg="#fcc")

        def _load_large() -> None:
            try:
                url = _shopify_sized_url(image_url, width=max(_PREVIEW_MAX) * 2)
                pil = _pil_from_url(url, _PREVIEW_MAX)
                photo = ImageTk.PhotoImage(pil)
            except (OSError, URLError, RuntimeError, ValueError) as exc:
                preview.after(0, lambda e=exc: _show_large_error(e))
                return
            preview.after(0, lambda p=photo: _apply_large_photo(p))

        preview.bind("<Escape>", lambda _e: _close_preview())
        preview.protocol("WM_DELETE_WINDOW", _close_preview)
        threading.Thread(target=_load_large, daemon=True, name="compare-preview").start()

    thumb_label.bind("<Button-1>", lambda _e: _open_image_preview())

    def _paste_clipboard(widget: scrolledtext.ScrolledText) -> None:
        try:
            data = win.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(_APP_TITLE, "Schowek jest pusty.", parent=win)
            return
        widget.delete("1.0", "end")
        widget.insert("1.0", data)

    for i in range(_PARA_SLOTS):
        btn = ttk.Button(para_bar, text=str(i + 1), width=4, command=lambda ix=i: _select_paragraph(ix))
        btn.pack(side="left", padx=2)
        para_btns[i] = btn

    for i in range(_VERSION_SLOTS):
        btn = ttk.Button(
            ver_bar,
            text=compare_version_label(i),
            width=5 if len(compare_version_label(i)) > 1 else 4,
            command=lambda ix=i: _select_version(ix),
        )
        btn.pack(side="left", padx=2)
        ver_btns[i] = btn

    saved_working = bucket.get("working") or {}
    if isinstance(saved_working, dict):
        for para_raw, text in saved_working.items():
            try:
                para_idx = int(para_raw)
            except (TypeError, ValueError):
                continue
            if isinstance(text, str) and text:
                ui["working_by_para"][para_idx] = text
    p0 = ui["para_idx"]
    if p0 not in ui["working_by_para"]:
        ui["working_by_para"][p0] = str(ctx.get("paragraph_text") or "")
    _load_panes()
    _load_thumbnail()
    version_text.bind("<FocusOut>", lambda _e: _save_panes())
    working_text.bind("<FocusOut>", lambda _e: _save_panes())
    _bind_text_undo_redo(version_text)
    _bind_text_undo_redo(working_text)

    def _collect_text_widgets(root: tk.Misc) -> set[int]:
        """Id widgetow Text (w tym wnetrze ScrolledText) — tam zostawiamy zwykle Ctrl+V."""
        found: set[int] = set()

        def walk(widget: tk.Misc) -> None:
            if widget.winfo_class() == "Text":
                found.add(id(widget))
            for child in widget.winfo_children():
                walk(child)

        walk(root)
        return found

    def _on_ctrl_v_paste_full(_event: tk.Event | None = None) -> str | None:
        focus = win.focus_get()
        if focus is not None and id(focus) in _text_widget_ids:
            return None
        _paste_full_from_clipboard()
        return "break"

    def _bind_paste_full_shortcut(widget: tk.Misc) -> None:
        if id(widget) in _text_widget_ids:
            return
        for seq in ("<Control-v>", "<Control-V>"):
            widget.bind(seq, _on_ctrl_v_paste_full, add="+")
        for child in widget.winfo_children():
            _bind_paste_full_shortcut(child)

    _text_widget_ids = _collect_text_widgets(version_text) | _collect_text_widgets(working_text)

    def _on_rmb_close_after_paste(_event: tk.Event | None = None) -> str | None:
        if ui.get("close_on_rmb"):
            _close()
            return "break"
        return None

    def _bind_rmb_close(widget: tk.Misc) -> None:
        widget.bind("<Button-3>", _on_rmb_close_after_paste, add="+")
        for child in widget.winfo_children():
            _bind_rmb_close(child)

    _bind_paste_full_shortcut(win)
    _bind_rmb_close(win)

    win.protocol("WM_DELETE_WINDOW", _close)
    win.bind("<Escape>", lambda _e: _close())
    _fit_compare_window(win)
