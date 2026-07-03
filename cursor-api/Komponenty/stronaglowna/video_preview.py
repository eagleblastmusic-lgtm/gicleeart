"""Podgląd filmu z Shopify Files (hero, kolaż, picker)."""

from __future__ import annotations

import os
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import webbrowser

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .service import fetch_shopify_file_bytes, resolve_shopify_file_download_url, shopify_ref_label


def preview_shopify_video(
    parent: tk.Misc,
    ref: str,
    *,
    title: str = "Podgląd filmu",
) -> None:
    """Odtwarza film z Shopify Files — najpierw URL w przeglądarce, potem plik tymczasowy."""
    text = (ref or "").strip()
    if not text.startswith("shopify://") and not text.startswith("gid://"):
        messagebox.showinfo(title, "Brak pliku wideo do podglądu.", parent=parent)
        return

    label = shopify_ref_label(text)
    status = tk.StringVar(value=f"Ładowanie: {label}…")
    win = tk.Toplevel(parent)
    win.title(title)
    position_toplevel_screen_center(win, 420, 120)
    win.transient(parent.winfo_toplevel())
    ttk.Label(win, textvariable=status, padding=16, wraplength=380).pack(fill="both", expand=True)

    def _open_url(url: str) -> None:
        webbrowser.open(url)
        status.set(f"Otwarto podgląd: {label}")
        win.after(600, win.destroy)

    def _open_temp(data: bytes, suffix: str) -> None:
        fd, path = tempfile.mkstemp(suffix=suffix or ".mp4", prefix="giclee_video_preview_")
        os.close(fd)
        try:
            Path(path).write_bytes(data)
            if os.name == "nt":
                os.startfile(path)  # noqa: S606
            else:
                webbrowser.open(Path(path).as_uri())
            status.set(f"Odtwarzam: {label}")
            win.after(600, win.destroy)
        except OSError as exc:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
            status.set("Błąd odtwarzania.")
            messagebox.showerror(title, str(exc), parent=win)

    def worker() -> None:
        url = resolve_shopify_file_download_url(text)
        if url:
            win.after(0, lambda: _open_url(url))
            return
        data = fetch_shopify_file_bytes(text)
        if not data:
            win.after(
                0,
                lambda: (
                    status.set("Nie udało się pobrać filmu."),
                    messagebox.showerror(title, f"Nie udało się pobrać:\n{label}", parent=win),
                    win.destroy(),
                ),
            )
            return
        suffix = Path(label).suffix or ".mp4"
        win.after(0, lambda: _open_temp(data, suffix))

    threading.Thread(target=worker, daemon=True, name="stronaglowna-video-preview").start()
