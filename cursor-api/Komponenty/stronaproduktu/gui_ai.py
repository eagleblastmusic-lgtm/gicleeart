"""Nakładka GUI: istniejący edytor PDP v3 + inteligentne kadry Gemini."""

from __future__ import annotations

import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Iterable

from Komponenty._shared.gemini_client import (
    DEFAULT_BATCH_DELAY_S,
    gemini_api_key,
    gemini_api_key_hint,
    set_gemini_api_key,
)
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import (
    attach_onscreen_guard,
    clamp_toplevel_onscreen,
    position_toplevel_screen_center,
)

from . import gui as legacy_gui
from .ai_crops import (
    CropSession,
    SmartCropError,
    cleanup_crop_session,
    generate_crop_session,
    paragraph_counts_from_config,
    resolve_product_story_context,
    save_selected_crops,
)

APP_TITLE = legacy_gui.APP_TITLE
GEMINI_API_KEY_URL = "https://aistudio.google.com/apikey"
MAX_AI_BATCH = 20


def _walk_widgets(widget: tk.Misc) -> Iterable[tk.Misc]:
    for child in widget.winfo_children():
        yield child
        yield from _walk_widgets(child)


def _tree_columns(tree: ttk.Treeview) -> tuple[str, ...]:
    raw = tree.cget("columns")
    if isinstance(raw, str):
        try:
            return tuple(tree.tk.splitlist(raw))
        except tk.TclError:
            return tuple(raw.split())
    return tuple(raw)


def _find_tree(host: tk.Misc, columns: tuple[str, ...]) -> ttk.Treeview | None:
    for widget in _walk_widgets(host):
        if isinstance(widget, ttk.Treeview) and _tree_columns(widget) == columns:
            return widget
    return None


def _find_button(host: tk.Misc, text: str) -> ttk.Button | None:
    for widget in _walk_widgets(host):
        if isinstance(widget, ttk.Button) and str(widget.cget("text")) == text:
            return widget
    return None


def _has_unsaved_changes(host: tk.Misc) -> bool:
    for widget in _walk_widgets(host):
        if not isinstance(widget, ttk.Label):
            continue
        var_name = str(widget.cget("textvariable") or "")
        if not var_name:
            continue
        try:
            value = str(host.getvar(var_name) or "")
        except tk.TclError:
            continue
        if "Niezapisane zmiany" in value:
            return True
    return False


def _selected_handles(product_tree: ttk.Treeview) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for iid in product_tree.selection():
        values = product_tree.item(iid, "values") or ()
        handle = str(values[2] if len(values) > 2 else "").strip()
        if handle and handle not in seen:
            seen.add(handle)
            out.append(handle)
    return out


def _mark_product_images_complete(product_tree: ttk.Treeview, handle: str) -> None:
    """Zielone oznaczenie wiersza po zapisie pełnego zestawu grafik AI."""
    target = (handle or "").strip()
    if not target:
        return
    for iid in product_tree.get_children(""):
        values = list(product_tree.item(iid, "values") or ())
        if len(values) < 3 or str(values[2]).strip() != target:
            continue
        status = str(values[3] if len(values) > 3 else "").strip()
        if status.endswith("str.") and "✓" not in status:
            values[3] = f"{status} ✓"
        elif "str." in status and "✓" not in status:
            values[3] = status.replace(" str.", " str. ✓", 1)
        try:
            product_tree.item(iid, values=values, tags=("images_complete",))
        except tk.TclError:
            pass
        break


def _page_counts(pages_tree: ttk.Treeview) -> list[int]:
    out: list[int] = []
    for iid in pages_tree.get_children(""):
        if str(iid) == "details":
            continue
        values = pages_tree.item(iid, "values") or ()
        if len(values) < 2:
            continue
        try:
            out.append(max(1, int(values[1])))
        except (TypeError, ValueError):
            continue
    return out


def _load_photo(path: Path | None, image_url: str, *, max_size: tuple[int, int]) -> Any:
    try:
        from PIL import Image, ImageTk
        from Komponenty._shared.clipboard_image import fetch_image_bytes, shopify_sized_image_url
        from io import BytesIO
    except ImportError as exc:
        raise RuntimeError("Podgląd wymaga Pillow: pip install Pillow") from exc

    if path and path.is_file():
        source: Any = path
    else:
        raw = fetch_image_bytes(shopify_sized_image_url(image_url, width=1600))
        source = BytesIO(raw)
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)


def _show_gemini_key_dialog(parent: tk.Misc, *, on_saved: Callable[[], None] | None = None) -> None:
    """Okno z polem do wklejenia GEMINI_API_KEY (zapis do cursor-api/.env)."""
    win = tk.Toplevel(parent)
    win.title("Gemini API — klucz")
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)
    position_toplevel_screen_center(win, 520, 300)

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
    else:
        ttk.Label(
            frame,
            text="Brak klucza — wklej poniżej, żeby włączyć AI — dobierz kadry…",
            foreground="#a60",
        ).pack(anchor="w", pady=(4, 0))

    ttk.Label(
        frame,
        text=(
            "Wklej klucz z Google AI Studio. Zostanie zapisany w cursor-api/.env "
            "(nadpisuje istniejącą wartość GEMINI_API_KEY)."
        ),
        wraplength=460,
        justify="left",
    ).pack(fill="x", pady=(8, 6))

    link_row = ttk.Frame(frame)
    link_row.pack(fill="x", pady=(0, 8))
    ttk.Label(link_row, text="Pobierz klucz: ").pack(side="left")
    link = tk.Label(
        link_row,
        text=GEMINI_API_KEY_URL,
        fg="#06a",
        cursor="hand2",
        font=("Segoe UI", 9, "underline"),
    )
    link.pack(side="left")
    link.bind("<Button-1>", lambda _e: webbrowser.open(GEMINI_API_KEY_URL))

    ttk.Label(frame, text="Wklej GEMINI_API_KEY:").pack(anchor="w")
    key_var = tk.StringVar(value=current)
    entry = ttk.Entry(frame, textvariable=key_var, width=58, show="*")
    entry.pack(fill="x", pady=(2, 4))
    show_var = tk.IntVar(value=0)

    def _toggle_show() -> None:
        entry.configure(show="" if show_var.get() else "*")

    ttk.Checkbutton(
        frame,
        text="Pokaż znaki",
        variable=show_var,
        command=_toggle_show,
    ).pack(anchor="w")

    status_var = tk.StringVar(value="")
    ttk.Label(frame, textvariable=status_var, foreground="#a60", wraplength=460).pack(
        fill="x",
        pady=(4, 0),
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
            status_var.set("Klucz wygląda na za krótki. Sprawdź i spróbuj ponownie.")
            return
        try:
            env_path = set_gemini_api_key(new_key)
        except (OSError, ValueError) as exc:
            status_var.set(str(exc))
            return
        if on_saved:
            on_saved()
        show_toast(parent, f"Zapisano GEMINI_API_KEY ({env_path.name})", duration_ms=2200)
        _close()

    ttk.Button(btn_row, text="Anuluj", command=_close).pack(side="right")
    ttk.Button(btn_row, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))
    entry.focus_set()
    entry.selection_range(0, "end")
    win.bind("<Return>", lambda _e: _save())
    win.bind("<Escape>", lambda _e: _close())


def _open_crop_window(
    host: tk.Misc,
    *,
    product_tree: ttk.Treeview,
    pages_tree: ttk.Treeview,
) -> None:
    handles = _selected_handles(product_tree)
    if not handles:
        messagebox.showinfo(APP_TITLE, "Najpierw wybierz produkt z listy.")
        return
    truncated = False
    if len(handles) > MAX_AI_BATCH:
        handles = handles[:MAX_AI_BATCH]
        truncated = True
    single_counts = _page_counts(pages_tree) if len(handles) == 1 else []
    if len(handles) == 1 and not single_counts:
        messagebox.showinfo(APP_TITLE, "Wybrany produkt nie ma stron tekstu do analizy.")
        return
    if _has_unsaved_changes(host):
        messagebox.showinfo(
            APP_TITLE,
            "Najpierw kliknij «Zapisz do Shopify». AI pracuje na zapisanym podziale stron, "
            "dzięki czemu nie utraci istniejących grafik.",
        )
        return
    if not gemini_api_key():
        _show_gemini_key_dialog(
            host,
            on_saved=lambda: _open_crop_window(
                host,
                product_tree=product_tree,
                pages_tree=pages_tree,
            ),
        )
        return
    if truncated:
        messagebox.showinfo(
            APP_TITLE,
            f"Zaznaczono więcej niż {MAX_AI_BATCH} produktów — sesja obejmuje pierwsze {MAX_AI_BATCH}.",
        )

    batch_mode = len(handles) > 1
    win = tk.Toplevel(host)
    win.title(
        "AI — kadry mini-stron (sesja zbiorcza)"
        if batch_mode
        else "AI — kadry mini-stron z głównego obrazu"
    )
    position_toplevel_screen_center(win, 1180, 760)
    win.minsize(980, 640)
    win.transient(host)
    win.grab_set()
    # Po minimizacji Windows często chowa okno na -32000 — pilnuj powrotu na ekran.
    attach_onscreen_guard(win, fallback_width=1180, fallback_height=760)
    try:
        root = host.winfo_toplevel()
        attach_onscreen_guard(root, fallback_width=1360, fallback_height=920)
    except tk.TclError:
        pass
    # Okno modalne: okresowo sprawdzaj, czy nie „uciekło” poza ekran.
    def _watchdog(remaining: int = 120) -> None:
        if state.get("closed") or remaining <= 0:
            return
        try:
            if not win.winfo_exists():
                return
            clamp_toplevel_onscreen(win, fallback_width=1180, fallback_height=760)
            clamp_toplevel_onscreen(host.winfo_toplevel(), fallback_width=1360, fallback_height=920)
            win.after(2000, lambda: _watchdog(remaining - 1))
        except tk.TclError:
            return
    win.after(2000, lambda: _watchdog())

    state: dict[str, Any] = {
        "session": None,
        "current_item": None,
        "enabled": set(),
        "closed": False,
        "busy": False,
        "reviewing": False,
        "waiting": False,
        "generating": True,
        "items": [
            {"handle": h, "status": "pending", "session": None, "error": None}
            for h in handles
        ],
        "saved": 0,
        "skipped": 0,
        "failed": 0,
        "saves_in_flight": 0,
        "batch": batch_mode,
        "bg_note": "Start...",
    }
    abort_event = threading.Event()

    outer = ttk.Frame(win, padding=14)
    outer.pack(fill="both", expand=True)
    title_var = tk.StringVar(
        value=(
            f"Sesja zbiorcza: {len(handles)} produktów — przegląd równolegle z Gemini"
            if batch_mode
            else "Analizuję obraz i teksty mini-stron..."
        )
    )
    status_var = tk.StringVar(value="Start...")
    ttk.Label(outer, textvariable=title_var, font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(outer, textvariable=status_var, foreground="#555", wraplength=1120).pack(
        anchor="w", pady=(4, 10)
    )
    progress = ttk.Progressbar(outer, mode="indeterminate")
    progress.pack(fill="x")
    progress.start(12)
    content = ttk.Frame(outer)
    content.pack(fill="both", expand=True, pady=(12, 0))
    footer = ttk.Frame(outer)
    footer.pack(fill="x", pady=(12, 0))
    ttk.Button(footer, text="Anuluj", command=lambda: _close()).pack(side="right")

    def ui(callback: Callable[[], None]) -> None:
        try:
            if win.winfo_exists():
                win.after(0, callback)
        except tk.TclError:
            return

    def set_status(message: str) -> None:
        # Aktualizuj pasek tła; nie nadpisuj statusu podczas aktywnego przeglądu.
        def apply() -> None:
            state["bg_note"] = message
            if state.get("waiting") or not state.get("reviewing"):
                status_var.set(_progress_line(message))
            elif state.get("reviewing") and state.get("session") is not None:
                session = state["session"]
                status_var.set(
                    f"Model: {session.model_used} · "
                    f"{session.source_size[0]}×{session.source_size[1]} px. "
                    f"{_progress_line('')}"
                )

        ui(apply)

    def _progress_counts() -> tuple[int, int, int, int, int, int]:
        items = state["items"]
        pending = sum(1 for i in items if i["status"] == "pending")
        ready = sum(1 for i in items if i["status"] == "ready")
        saving = int(state.get("saves_in_flight") or 0)
        saved = int(state.get("saved") or 0)
        skipped = int(state.get("skipped") or 0)
        failed = int(state.get("failed") or 0)
        return pending, ready, saving, saved, skipped, failed

    def _progress_line(extra: str = "") -> str:
        pending, ready, saving, saved, skipped, failed = _progress_counts()
        total = len(state["items"])
        doneish = saved + skipped + failed
        base = (
            f"Gotowe: {ready} · Gemini: {pending}/{total} · zapis w tle: {saving} · "
            f"zapisano {saved}, pominięto {skipped}, błędy {failed} ({doneish}/{total})"
        )
        extra = (extra or "").strip()
        if extra and (state.get("waiting") or not state.get("reviewing")):
            return f"{base} — {extra}"
        if extra and state.get("reviewing"):
            return f"{base} · tło: {extra}"
        return base

    def _cleanup_all_sessions() -> None:
        for item in state.get("items") or []:
            cleanup_crop_session(item.get("session"))
            item["session"] = None
        cleanup_crop_session(state.get("session"))
        state["session"] = None
        state["current_item"] = None

    def _close() -> None:
        if state["closed"]:
            return
        state["closed"] = True
        abort_event.set()
        _cleanup_all_sessions()
        try:
            win.destroy()
        except tk.TclError:
            pass

    win.protocol("WM_DELETE_WINDOW", _close)

    def _finish_session(*, show_all_failed: bool = False) -> None:
        saved = int(state.get("saved") or 0)
        skipped = int(state.get("skipped") or 0)
        failed = int(state.get("failed") or 0)
        if show_all_failed and state["batch"] and saved == 0 and skipped == 0 and failed > 0:
            errs = [
                f"{i['handle']}: {i['error']}"
                for i in state["items"]
                if i.get("status") == "error" and i.get("error")
            ]
            messagebox.showerror(
                APP_TITLE,
                "Nie udało się przygotować kadrów dla zaznaczonych produktów:\n"
                + "\n".join(errs[:8]),
                parent=win,
            )
        state["closed"] = True
        abort_event.set()
        _cleanup_all_sessions()
        try:
            win.destroy()
        except tk.TclError:
            pass
        if state["batch"]:
            show_toast(
                host,
                f"Sesja AI: zapisano {saved}, pominięto {skipped}, błędy {failed}.",
                duration_ms=4500,
            )
        elif saved:
            show_toast(host, "Kadry AI zapisano w mini-stronach PDP v3.", duration_ms=3500)
        try:
            product_tree.event_generate("<<TreeviewSelect>>")
        except tk.TclError:
            pass

    def _show_waiting_ui(*, for_saves: bool = False) -> None:
        state["reviewing"] = False
        state["waiting"] = True
        state["session"] = None
        state["current_item"] = None
        state["busy"] = False
        for child in content.winfo_children():
            child.destroy()
        for child in footer.winfo_children():
            child.destroy()
        if not progress.winfo_ismapped():
            progress.pack(fill="x", before=content)
        progress.start(12)
        if for_saves:
            title_var.set("Zapisuję zatwierdzone kadry w tle…")
            tip = (
                "Przegląd zakończony. Trwa jeszcze upload/zapis do Shopify — "
                "poczekaj chwilę, okno zamknie się samo."
            )
        else:
            title_var.set("Czekam na kolejne wyniki Gemini…")
            tip = (
                "Możesz poczekać — gdy pojawi się kolejna odpowiedź, "
                "podgląd otworzy się automatycznie. Generowanie pozostałych trwa w tle."
            )
        status_var.set(_progress_line(str(state.get("bg_note") or "")))
        ttk.Label(content, text=tip, wraplength=900, foreground="#444").pack(anchor="w", pady=20)
        ttk.Button(footer, text="Zakończ sesję", command=_close).pack(side="right")

    def _try_present_next() -> None:
        if state["closed"] or state.get("reviewing"):
            return
        for item in state["items"]:
            if item.get("status") == "ready" and item.get("session") is not None:
                build_preview(item)
                return
        pending = any(i.get("status") == "pending" for i in state["items"])
        if pending or state.get("generating"):
            _show_waiting_ui(for_saves=False)
            return
        if int(state.get("saves_in_flight") or 0) > 0:
            _show_waiting_ui(for_saves=True)
            return
        # Nic więcej do przeglądu ani zapisu.
        only_errors = (
            int(state.get("saved") or 0) == 0
            and int(state.get("skipped") or 0) == 0
            and int(state.get("failed") or 0) > 0
        )
        if not state["batch"] and only_errors:
            err = next(
                (i.get("error") for i in state["items"] if i.get("status") == "error"),
                "Nieznany błąd",
            )
            messagebox.showerror(APP_TITLE, f"Nie udało się przygotować kadrów:\n{err}", parent=win)
            _finish_session()
            return
        _finish_session(show_all_failed=only_errors)

    def _on_item_generated(index: int, session: CropSession | None, error: str | None) -> None:
        def apply() -> None:
            if state["closed"]:
                cleanup_crop_session(session)
                return
            item = state["items"][index]
            if error or session is None:
                item["status"] = "error"
                item["error"] = error or "Nie udało się przygotować kadrów."
                item["session"] = None
                state["failed"] = int(state.get("failed") or 0) + 1
                cleanup_crop_session(session)
            else:
                item["status"] = "ready"
                item["session"] = session
                item["error"] = None
            if not state.get("reviewing"):
                _try_present_next()
            else:
                status_var.set(
                    (
                        f"Model: {state['session'].model_used} · "
                        f"{state['session'].source_size[0]}×{state['session'].source_size[1]} px. "
                        if state.get("session") is not None
                        else ""
                    )
                    + _progress_line(str(state.get("bg_note") or ""))
                )

        ui(apply)

    def build_preview(item: dict[str, Any]) -> None:
        session = item.get("session")
        if state["closed"] or session is None:
            cleanup_crop_session(session)
            return
        state["waiting"] = False
        state["reviewing"] = True
        state["current_item"] = item
        state["session"] = session
        state["busy"] = False
        progress.stop()
        progress.pack_forget()
        for child in content.winfo_children():
            child.destroy()
        for child in footer.winfo_children():
            child.destroy()

        items = state["items"]
        pos = next((i + 1 for i, it in enumerate(items) if it is item), 1)
        batch_prefix = f"[{pos}/{len(items)}] " if state["batch"] else ""
        title_var.set(f"{batch_prefix}{session.title} — propozycje kadrów")
        status_var.set(
            f"Model: {session.model_used} · źródło: {session.source_size[0]}×{session.source_size[1]} px. "
            f"{_progress_line('')}"
        )

        enabled: set[int] = {
            p.page_index for p in session.proposals if not p.existing_image
        }
        state["enabled"] = enabled

        paned = ttk.Panedwindow(content, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned, padding=(0, 0, 10, 0))
        right = ttk.LabelFrame(paned, text="Podgląd wybranego kadru", padding=10)
        paned.add(left, weight=2)
        paned.add(right, weight=3)

        columns = ("use", "page", "subject", "confidence", "current")
        tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        labels = {
            "use": "Użyj",
            "page": "Strona",
            "subject": "Dopasowany motyw",
            "confidence": "Pewność",
            "current": "Obecna grafika",
        }
        widths = {"use": 55, "page": 65, "subject": 245, "confidence": 75, "current": 130}
        for col in columns:
            tree.heading(col, text=labels[col])
            tree.column(col, width=widths[col], anchor="w", stretch=(col == "subject"))
        tree.pack(fill="both", expand=True)

        preview_label = ttk.Label(right, anchor="center")
        preview_label.pack(fill="both", expand=True)
        subject_var = tk.StringVar(value="")
        reason_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=subject_var, font=("Segoe UI", 11, "bold"), wraplength=600).pack(
            anchor="w", pady=(10, 2)
        )
        ttk.Label(right, textvariable=reason_var, foreground="#555", wraplength=600).pack(anchor="w")
        text_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=text_var, foreground="#666", wraplength=600).pack(
            anchor="w", pady=(8, 0)
        )
        preview_label._photo_ref = None  # type: ignore[attr-defined]

        def row_values(proposal: Any) -> tuple[str, str, str, str, str]:
            variant = proposal.variants[proposal.selected_variant]
            current = "własna" if proposal.existing_image else "główny obraz"
            confidence = "—" if variant.is_full_view else f"{variant.confidence * 100:.0f}%"
            return (
                "✓" if proposal.page_index in enabled else "—",
                str(proposal.page_index + 1),
                variant.matched_subject,
                confidence,
                current,
            )

        for proposal in session.proposals:
            tree.insert("", "end", iid=f"page-{proposal.page_index}", values=row_values(proposal))

        def selected_proposal() -> Any | None:
            sel = tree.selection()
            if not sel:
                return None
            try:
                index = int(str(sel[0]).split("-", 1)[1])
            except (IndexError, ValueError):
                return None
            return session.proposals[index] if 0 <= index < len(session.proposals) else None

        def refresh_row(proposal: Any) -> None:
            tree.item(f"page-{proposal.page_index}", values=row_values(proposal))
            refresh_preview()

        def refresh_preview(*_args: Any) -> None:
            proposal = selected_proposal()
            if proposal is None:
                return
            variant = proposal.variants[proposal.selected_variant]
            try:
                photo = _load_photo(
                    variant.local_path,
                    session.image_url,
                    max_size=(650, 430),
                )
            except Exception as exc:  # noqa: BLE001
                preview_label.configure(image="", text=f"Nie udało się wyświetlić podglądu:\n{exc}")
                preview_label._photo_ref = None  # type: ignore[attr-defined]
            else:
                preview_label.configure(image=photo, text="")
                preview_label._photo_ref = photo  # type: ignore[attr-defined]
            subject_var.set(
                f"Strona {proposal.page_index + 1}: {variant.matched_subject}"
                + (" · pełny obraz" if variant.is_full_view else "")
            )
            reason_var.set(variant.reason)
            snippet = " ".join(proposal.page_text.split())
            text_var.set((snippet[:360] + "…") if len(snippet) > 360 else snippet)

        def toggle_selected() -> None:
            proposal = selected_proposal()
            if proposal is None:
                return
            if proposal.page_index in enabled:
                enabled.remove(proposal.page_index)
            else:
                enabled.add(proposal.page_index)
            refresh_row(proposal)

        def next_variant() -> None:
            proposal = selected_proposal()
            if proposal is None or len(proposal.variants) <= 1:
                return
            proposal.selected_variant = (proposal.selected_variant + 1) % len(proposal.variants)
            refresh_row(proposal)

        tree.bind("<<TreeviewSelect>>", refresh_preview)
        tree.bind("<Double-1>", lambda *_: toggle_selected())
        if session.proposals:
            tree.selection_set("page-0")
            refresh_preview()

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Włącz / wyłącz", command=toggle_selected).pack(side="left")
        ttk.Button(actions, text="Następny wariant", command=next_variant).pack(side="left", padx=(8, 0))

        def release_current(*, mark: str, cleanup: bool = True) -> None:
            if cleanup:
                cleanup_crop_session(session)
            item["session"] = None
            item["status"] = mark
            state["session"] = None
            state["current_item"] = None
            state["reviewing"] = False
            if mark == "skipped":
                state["skipped"] = int(state.get("skipped") or 0) + 1

        def skip_product() -> None:
            release_current(mark="skipped", cleanup=True)
            if state["batch"]:
                _try_present_next()
            else:
                _finish_session()

        def apply() -> None:
            selections = {
                proposal.page_index: proposal.selected_variant
                for proposal in session.proposals
                if proposal.page_index in enabled
            }
            if not selections:
                messagebox.showinfo(APP_TITLE, "Nie zaznaczono żadnej strony.", parent=win)
                return
            replacements = sum(
                1 for p in session.proposals if p.page_index in selections and p.existing_image
            )
            warning = (
                f"\n\nZostanie zastąpionych istniejących grafik: {replacements}."
                if replacements
                else ""
            )
            if not messagebox.askyesno(
                APP_TITLE,
                f"Wgrać i zapisać grafiki dla {len(selections)} stron?{warning}",
                parent=win,
            ):
                return

            save_session = session
            save_item = item
            save_handle = str(session.handle or item.get("handle") or "")
            # Od razu oddaj UI — zapis leci w tle (sesji nie sprzątamy aż po uploadzie).
            release_current(mark="saving", cleanup=False)
            state["saves_in_flight"] = int(state.get("saves_in_flight") or 0) + 1
            state["bg_note"] = f"Zapisuję {save_handle} w tle…"
            set_status(str(state["bg_note"]))

            def work_save() -> None:
                try:
                    result = save_selected_crops(
                        save_session,
                        selections,
                        on_status=lambda m: set_status(f"{save_handle}: {m}"),
                    )
                    error = None
                except Exception as exc:  # noqa: BLE001
                    result, error = None, str(exc)
                finally:
                    cleanup_crop_session(save_session)

                def done_save() -> None:
                    state["saves_in_flight"] = max(
                        0, int(state.get("saves_in_flight") or 0) - 1
                    )
                    if error or not (result or {}).get("ok"):
                        save_item["status"] = "error"
                        save_item["error"] = str(
                            error or (result or {}).get("error") or "Błąd zapisu"
                        )
                        state["failed"] = int(state.get("failed") or 0) + 1
                        toast_host = host if state["closed"] else win
                        try:
                            show_toast(
                                toast_host,
                                f"Błąd zapisu {save_handle}: {save_item['error'][:120]}",
                                duration_ms=4500,
                            )
                        except tk.TclError:
                            pass
                    else:
                        save_item["status"] = "done"
                        state["saved"] = int(state.get("saved") or 0) + 1
                        try:
                            _mark_product_images_complete(product_tree, save_handle)
                        except tk.TclError:
                            pass
                        if not state["closed"]:
                            try:
                                show_toast(win, f"Zapisano: {save_handle}", duration_ms=2000)
                            except tk.TclError:
                                pass
                    if state["closed"]:
                        return
                    if not state.get("reviewing"):
                        _try_present_next()
                    else:
                        status_var.set(_progress_line(str(state.get("bg_note") or "")))

                ui(done_save)

            threading.Thread(target=work_save, daemon=True).start()
            # Natychmiast kolejna karta (batch) albo ekran oczekiwania na zapis (single).
            _try_present_next()

        apply_button = ttk.Button(footer, text="Zatwierdź i zapisz do Shopify", command=apply)
        apply_button.pack(side="right")
        if state["batch"]:
            ttk.Button(footer, text="Pomiń produkt", command=skip_product).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Zakończ sesję" if state["batch"] else "Anuluj", command=_close).pack(
            side="right", padx=(0, 8)
        )
        ttk.Label(
            footer,
            text=(
                "Zatwierdź → od razu następna karta, zapis Shopify w tle. Dwuklik = użyj strony."
                if state["batch"]
                else "Dwuklik w wiersz przełącza użycie. Istniejące grafiki są domyślnie wyłączone."
            ),
            foreground="#666",
        ).pack(side="left")

    def work_generate() -> None:
        for index, handle in enumerate(handles):
            if abort_event.is_set():
                break
            set_status(f"[{index + 1}/{len(handles)}] {handle}: przygotowuję...")
            if index > 0:
                set_status(
                    f"[{index + 1}/{len(handles)}] przerwa {DEFAULT_BATCH_DELAY_S:.0f}s (RPM)…"
                )
                waited = 0.0
                while waited < DEFAULT_BATCH_DELAY_S:
                    if abort_event.is_set():
                        break
                    step = min(0.25, DEFAULT_BATCH_DELAY_S - waited)
                    time.sleep(step)
                    waited += step
                if abort_event.is_set():
                    break
            session: CropSession | None = None
            error: str | None = None
            try:
                if len(handles) == 1:
                    counts = single_counts
                else:
                    context = resolve_product_story_context(handle)
                    counts = paragraph_counts_from_config(
                        context.config, len(context.paragraphs)
                    )
                    if not counts:
                        raise SmartCropError("Brak stron do analizy (zapisany podział w Shopify).")
                session = generate_crop_session(
                    handle=handle,
                    paragraph_counts=counts,
                    on_status=set_status,
                    should_abort=abort_event.is_set,
                )
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                session = None
            _on_item_generated(index, session, error)

        def done_generate() -> None:
            if state["closed"]:
                return
            state["generating"] = False
            state["bg_note"] = "Generowanie w tle zakończone."
            if not state.get("reviewing"):
                _try_present_next()
            else:
                status_var.set(_progress_line(str(state.get("bg_note") or "")))

        ui(done_generate)

    threading.Thread(target=work_generate, daemon=True).start()


def _attach_ai_controls(host: tk.Misc) -> None:
    if getattr(host, "_giclee_ai_crops_attached", False):
        return
    product_tree = _find_tree(host, ("artist", "painting_title", "handle", "story_status"))
    pages_tree = _find_tree(host, ("page", "count", "range", "image"))
    upload_button = _find_button(host, "Wgraj grafikę strony...")
    if product_tree is None or pages_tree is None or upload_button is None:
        return
    setattr(host, "_giclee_ai_crops_attached", True)
    actions = upload_button.master
    ttk.Button(
        actions,
        text="AI — dobierz kadry...",
        command=lambda: _open_crop_window(
            host,
            product_tree=product_tree,
            pages_tree=pages_tree,
        ),
    ).pack(side="left", padx=(14, 0))
    ttk.Button(
        actions,
        text="Gemini API…",
        command=lambda: _show_gemini_key_dialog(host),
    ).pack(side="left", padx=(8, 0))


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    legacy_gui._build_ui(host, inline=inline)
    host.after_idle(lambda: _attach_ai_controls(host))


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1360, 920)
    root.minsize(1060, 720)
    _build_ui(root)
    root.mainloop()
