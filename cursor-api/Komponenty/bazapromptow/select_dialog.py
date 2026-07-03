"""Okno wyboru artysty i obrazu + kopiowanie promptu z grafika."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, scrolledtext, ttk

from Komponenty._shared.clipboard_image import copy_image_url_to_clipboard
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .catalog import (
    apply_prompt_placeholders,
    painting_display,
    painting_label,
    paintings_for_artist,
    row_image_url,
    unique_artists,
)
from .storage import PromptEntry

APP_TITLE = "Baza Promptow"


def open_copy_helper_dialog(
    parent: tk.Misc,
    *,
    prompt: str,
    image_url: str,
    label: str,
    artist: str,
    title: str,
) -> None:
    """Prompt w schowku + osobny krok na grafike (Gemini bierze tylko obraz przy Ctrl+V)."""
    win = tk.Toplevel(parent)
    win.title(f"{label} → schowek")
    win.transient(parent)
    position_toplevel_screen_center(win, 540, 360)
    win.minsize(460, 300)

    frame = ttk.Frame(win, padding=12)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=label, font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttk.Label(
        frame,
        text=f"{artist} — {title}",
        foreground="#444",
    ).pack(anchor="w", pady=(2, 0))
    ttk.Label(
        frame,
        text=(
            "Prompt jest juz w schowku — wklej go w czacie (Ctrl+V).\n"
            "Potem kliknij «Kopiuj grafike» i wklej obraz osobno."
        ),
        wraplength=500,
        justify="left",
        foreground="#555",
    ).pack(anchor="w", pady=(8, 8))

    preview = scrolledtext.ScrolledText(frame, height=7, wrap="word", font=("Segoe UI", 9))
    preview.pack(fill="both", expand=True)
    preview.insert("1.0", prompt)
    preview.configure(state="disabled")

    status_var = tk.StringVar(value="Prompt w schowku.")
    ttk.Label(frame, textvariable=status_var, foreground="#0a6", wraplength=500).pack(
        anchor="w", pady=(8, 0),
    )

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x", pady=(10, 0))

    def _copy_prompt_again() -> None:
        try:
            win.clipboard_clear()
            win.clipboard_append(prompt)
            win.update()
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=win)
            return
        status_var.set("Prompt ponownie w schowku.")
        show_toast(win, "Prompt w schowku", duration_ms=1200)

    def _copy_image() -> None:
        if not image_url:
            messagebox.showwarning(APP_TITLE, "Brak grafiki dla tego produktu.", parent=win)
            return
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
                status_var.set("Grafika w schowku — wklej w czacie (Ctrl+V).")
                copy_img_btn.configure(state="normal")
                show_toast(win, "Grafika w schowku", duration_ms=1600)

            win.after(0, done)

        threading.Thread(target=work, daemon=True, name="bazapromptow-copy-img").start()

    ttk.Button(btn_row, text="Kopiuj prompt ponownie", command=_copy_prompt_again).pack(side="left")
    copy_img_btn = ttk.Button(btn_row, text="Kopiuj grafike", command=_copy_image)
    copy_img_btn.pack(side="left", padx=(8, 0))
    ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right")


def open_product_select_dialog(
    parent: tk.Misc,
    *,
    entry: PromptEntry,
    catalog_rows: list[dict],
    on_status: Callable[[str], None] | None = None,
) -> None:
    """Lista rozwijana: artysta → obraz → kopiuj prompt z podstawionymi placeholderami."""
    if not catalog_rows:
        messagebox.showwarning(
            APP_TITLE,
            "Katalog produktow jest pusty.\n"
            "Kliknij «Odswiez katalog» i sprobuj ponownie.",
            parent=parent,
        )
        return

    artists = unique_artists(catalog_rows)
    if not artists:
        messagebox.showwarning(APP_TITLE, "Brak artystow w katalogu.", parent=parent)
        return

    win = tk.Toplevel(parent)
    win.title(f"{entry.label} — wybierz obraz")
    win.transient(parent)
    win.grab_set()
    position_toplevel_screen_center(win, 620, 480)
    win.minsize(520, 400)

    body = ttk.Frame(win, padding=12)
    body.pack(fill="both", expand=True)

    ttk.Label(
        body,
        text=f"Prompt: {entry.label}",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        body,
        text="Wybierz artyste i obraz. Placeholdery [autor] i [tytuł] zostana podmienione.",
        foreground="#555",
        wraplength=560,
    ).pack(anchor="w", pady=(4, 12))

    artist_var = tk.StringVar(value=artists[0])
    ttk.Label(body, text="Artysta:").pack(anchor="w")
    artist_cb = ttk.Combobox(
        body,
        textvariable=artist_var,
        values=artists,
        state="readonly",
        font=("Segoe UI", 10),
    )
    artist_cb.pack(fill="x", pady=(2, 10))

    painting_var = tk.StringVar()
    ttk.Label(body, text="Obraz:").pack(anchor="w")
    painting_cb = ttk.Combobox(
        body,
        textvariable=painting_var,
        state="readonly",
        font=("Segoe UI", 10),
    )
    painting_cb.pack(fill="x", pady=(2, 10))

    preview_frame = ttk.LabelFrame(body, text="Podglad promptu", padding=6)
    preview_frame.pack(fill="both", expand=True, pady=(0, 10))
    preview = scrolledtext.ScrolledText(
        preview_frame, height=8, wrap="word", font=("Consolas", 9), state="disabled",
    )
    preview.pack(fill="both", expand=True)

    row_by_label: dict[str, dict] = {}

    def _refresh_paintings(*_args: object) -> None:
        nonlocal row_by_label
        artist = artist_var.get().strip()
        rows = paintings_for_artist(catalog_rows, artist)
        labels = [painting_display(r) for r in rows]
        row_by_label = {painting_display(r): r for r in rows}
        painting_cb.configure(values=labels)
        if labels:
            painting_var.set(labels[0])
        else:
            painting_var.set("")
        _update_preview()

    def _selected_row() -> dict | None:
        label = painting_var.get().strip()
        return row_by_label.get(label)

    def _update_preview() -> None:
        row = _selected_row()
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        if row:
            artist = str(row.get("artist") or "").strip()
            title = painting_label(row)
            text = apply_prompt_placeholders(entry.text, artist=artist, title=title)
            preview.insert("1.0", text)
        preview.configure(state="disabled")

    def _copy_and_close() -> None:
        row = _selected_row()
        if not row:
            messagebox.showwarning(APP_TITLE, "Wybierz obraz z listy.", parent=win)
            return
        artist = str(row.get("artist") or "").strip()
        title = painting_label(row)
        prompt = apply_prompt_placeholders(entry.text, artist=artist, title=title)
        image_url = row_image_url(row)
        try:
            win.clipboard_clear()
            win.clipboard_append(prompt)
            win.update()
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=win)
            return
        win.destroy()
        if on_status:
            on_status(f"Skopiowano: {entry.label} ({artist} — {title})")
        show_toast(parent, f"Prompt: {title[:40]}", duration_ms=1800)
        open_copy_helper_dialog(
            parent,
            prompt=prompt,
            image_url=image_url,
            label=entry.label,
            artist=artist,
            title=title,
        )

    artist_cb.bind("<<ComboboxSelected>>", _refresh_paintings)
    painting_cb.bind("<<ComboboxSelected>>", lambda *_: _update_preview())

    btns = ttk.Frame(body)
    btns.pack(fill="x")
    ttk.Button(btns, text="Anuluj", command=win.destroy).pack(side="right")
    ttk.Button(btns, text="Kopiuj prompt", command=_copy_and_close).pack(side="right", padx=(0, 8))

    _refresh_paintings()
    artist_cb.focus_set()
    win.bind("<Escape>", lambda _e: win.destroy())
