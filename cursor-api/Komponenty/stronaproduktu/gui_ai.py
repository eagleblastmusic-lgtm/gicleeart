"""Nakładka GUI: istniejący edytor PDP v3 + inteligentne kadry Gemini."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Iterable

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import gui as legacy_gui
from .ai_crops import (
    CropSession,
    cleanup_crop_session,
    generate_crop_session,
    save_selected_crops,
)

APP_TITLE = legacy_gui.APP_TITLE


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


def _selected_handle(product_tree: ttk.Treeview) -> str:
    selected = product_tree.selection()
    if not selected:
        return ""
    values = product_tree.item(selected[0], "values") or ()
    return str(values[2] if len(values) > 2 else "").strip()


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


def _open_crop_window(
    host: tk.Misc,
    *,
    product_tree: ttk.Treeview,
    pages_tree: ttk.Treeview,
) -> None:
    handle = _selected_handle(product_tree)
    if not handle:
        messagebox.showinfo(APP_TITLE, "Najpierw wybierz produkt z listy.")
        return
    counts = _page_counts(pages_tree)
    if not counts:
        messagebox.showinfo(APP_TITLE, "Wybrany produkt nie ma stron tekstu do analizy.")
        return
    if _has_unsaved_changes(host):
        messagebox.showinfo(
            APP_TITLE,
            "Najpierw kliknij «Zapisz do Shopify». AI pracuje na zapisanym podziale stron, "
            "dzięki czemu nie utraci istniejących grafik.",
        )
        return

    win = tk.Toplevel(host)
    win.title("AI — kadry mini-stron z głównego obrazu")
    position_toplevel_screen_center(win, 1180, 760)
    win.minsize(980, 640)
    win.transient(host)
    win.grab_set()

    state: dict[str, Any] = {
        "session": None,
        "enabled": set(),
        "closed": False,
        "busy": True,
    }
    abort_event = threading.Event()

    outer = ttk.Frame(win, padding=14)
    outer.pack(fill="both", expand=True)
    title_var = tk.StringVar(value="Analizuję obraz i teksty mini-stron...")
    status_var = tk.StringVar(value="Pobieram dane produktu...")
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
    cancel_button = ttk.Button(footer, text="Anuluj", command=lambda: _close())
    cancel_button.pack(side="right")

    def ui(callback: Callable[[], None]) -> None:
        try:
            if win.winfo_exists():
                win.after(0, callback)
        except tk.TclError:
            return

    def set_status(message: str) -> None:
        ui(lambda: status_var.set(message))

    def _close() -> None:
        if state["closed"]:
            return
        state["closed"] = True
        abort_event.set()
        cleanup_crop_session(state.get("session"))
        try:
            win.destroy()
        except tk.TclError:
            pass

    win.protocol("WM_DELETE_WINDOW", _close)

    def build_preview(session: CropSession) -> None:
        if state["closed"]:
            cleanup_crop_session(session)
            return
        state["session"] = session
        state["busy"] = False
        progress.stop()
        progress.pack_forget()
        for child in content.winfo_children():
            child.destroy()
        for child in footer.winfo_children():
            child.destroy()

        title_var.set(f"{session.title} — propozycje kadrów")
        status_var.set(
            f"Model: {session.model_used} · źródło: {session.source_size[0]}×{session.source_size[1]} px. "
            "Strona 1 używa pełnego obrazu bez duplikowania pliku."
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
            state["busy"] = True
            for widget in (tree, apply_button):
                try:
                    widget.configure(state="disabled")
                except tk.TclError:
                    pass
            progress.pack(fill="x", before=content)
            progress.start(12)
            status_var.set("Wgrywam zatwierdzone kadry do Shopify Files...")

            def work_save() -> None:
                try:
                    result = save_selected_crops(session, selections, on_status=set_status)
                    error = None
                except Exception as exc:  # noqa: BLE001
                    result, error = None, str(exc)

                def done_save() -> None:
                    if state["closed"]:
                        return
                    progress.stop()
                    if error or not (result or {}).get("ok"):
                        state["busy"] = False
                        progress.pack_forget()
                        messagebox.showerror(
                            APP_TITLE,
                            f"Nie udało się zapisać kadrów:\n{error or (result or {}).get('error')}",
                            parent=win,
                        )
                        try:
                            tree.configure(state="normal")
                            apply_button.configure(state="normal")
                        except tk.TclError:
                            pass
                        return
                    cleanup_crop_session(session)
                    state["session"] = None
                    state["closed"] = True
                    win.destroy()
                    show_toast(host, "Kadry AI zapisano w mini-stronach PDP v3.", duration_ms=3500)
                    try:
                        product_tree.event_generate("<<TreeviewSelect>>")
                    except tk.TclError:
                        pass

                ui(done_save)

            threading.Thread(target=work_save, daemon=True).start()

        apply_button = ttk.Button(footer, text="Zatwierdź i zapisz do Shopify", command=apply)
        apply_button.pack(side="right")
        ttk.Button(footer, text="Anuluj", command=_close).pack(side="right", padx=(0, 8))
        ttk.Label(
            footer,
            text="Dwuklik w wiersz przełącza użycie. Istniejące grafiki są domyślnie wyłączone.",
            foreground="#666",
        ).pack(side="left")

    def work_generate() -> None:
        try:
            session = generate_crop_session(
                handle=handle,
                paragraph_counts=counts,
                on_status=set_status,
                should_abort=abort_event.is_set,
            )
            error = None
        except Exception as exc:  # noqa: BLE001
            session, error = None, str(exc)

        def done_generate() -> None:
            if state["closed"]:
                cleanup_crop_session(session)
                return
            if error or session is None:
                progress.stop()
                progress.pack_forget()
                state["busy"] = False
                status_var.set("")
                messagebox.showerror(APP_TITLE, f"Nie udało się przygotować kadrów:\n{error}", parent=win)
                _close()
                return
            build_preview(session)

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
    ttk.Button(
        upload_button.master,
        text="AI — dobierz kadry...",
        command=lambda: _open_crop_window(
            host,
            product_tree=product_tree,
            pages_tree=pages_tree,
        ),
    ).pack(side="left", padx=(14, 0))


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
