"""Opcjonalny dźwięk ambient w sekcji hero (slideshow) — panel w GicleeApp."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import tkinter as tk

from .service import AUDIO_SUFFIXES, upload_hero_audio

_WIN_TITLE = "Dźwięk ambient — hero"
_AUDIO_UPLOAD_TOAST = "Audio wgrane — URL CDN ustawiony w polu poniżej."


def _audio_label_from_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    return Path(text.split("?")[0]).name or text


def hero_audio_summary_text(values: dict[str, Any]) -> str:
    if not bool(values.get("hero_audio_enable")):
        return "Wyłączony — przycisk dźwięku nie pojawi się na stronie głównej."
    url = str(values.get("hero_audio_url") or "").strip()
    if not url:
        return "Włączony, ale brak pliku audio — wgraj MP3/OGG/WAV lub wklej URL CDN."
    name = _audio_label_from_url(url)
    volume = int(values.get("hero_audio_volume") or 28)
    return f"Włączony · {name} · głośność {volume}% · odtwarzanie po kliknięciu użytkownika."


def _hero_audio_values_from_widgets(state: dict[str, Any]) -> dict[str, Any]:
    enable_w = state["widgets"].get("hero_audio_enable")
    url_w = state["widgets"].get("hero_audio_url")
    on_w = state["widgets"].get("hero_audio_label_on")
    off_w = state["widgets"].get("hero_audio_label_off")
    vol_w = state["widgets"].get("hero_audio_volume")
    try:
        volume = int(vol_w.get()) if vol_w is not None and hasattr(vol_w, "get") else 28
    except (TypeError, ValueError):
        volume = 28
    return {
        "hero_audio_enable": bool(enable_w.get()) if enable_w is not None and hasattr(enable_w, "get") else False,
        "hero_audio_url": url_w.get().strip() if url_w is not None and hasattr(url_w, "get") else "",
        "hero_audio_label_on": on_w.get().strip() if on_w is not None and hasattr(on_w, "get") else "Włącz dźwięk",
        "hero_audio_label_off": off_w.get().strip() if off_w is not None and hasattr(off_w, "get") else "Wycisz",
        "hero_audio_volume": max(0, min(100, volume)),
    }


def ensure_hero_audio_widgets(state: dict[str, Any], values: dict[str, Any]) -> None:
    if "hero_audio_enable" not in state["widgets"]:
        state["widgets"]["hero_audio_enable"] = tk.BooleanVar(value=bool(values.get("hero_audio_enable")))
    if "hero_audio_url" not in state["widgets"]:
        state["widgets"]["hero_audio_url"] = tk.StringVar(value=str(values.get("hero_audio_url") or ""))
    if "hero_audio_label_on" not in state["widgets"]:
        state["widgets"]["hero_audio_label_on"] = tk.StringVar(
            value=str(values.get("hero_audio_label_on") or "Włącz dźwięk")
        )
    if "hero_audio_label_off" not in state["widgets"]:
        state["widgets"]["hero_audio_label_off"] = tk.StringVar(
            value=str(values.get("hero_audio_label_off") or "Wycisz")
        )
    if "hero_audio_volume" not in state["widgets"]:
        raw_vol = values.get("hero_audio_volume")
        try:
            volume = int(raw_vol) if raw_vol not in (None, "") else 28
        except (TypeError, ValueError):
            volume = 28
        if volume <= 0 and raw_vol in (None, ""):
            volume = 28
        state["widgets"]["hero_audio_volume"] = tk.IntVar(value=max(0, min(100, volume)))


def _notify_audio_uploaded(show_toast: Callable[..., Any], parent: tk.Misc) -> None:
    """Pokaż toast sukcesu z prawidłowym widgetem rodzica jako pierwszym argumentem."""
    show_toast(parent, _AUDIO_UPLOAD_TOAST)


def open_hero_audio_editor_window(
    host: tk.Misc,
    *,
    state: dict[str, Any],
    values: dict[str, Any],
    mark_dirty: Callable[[], None],
    status_var: tk.StringVar,
    show_toast: Callable[..., None],
    on_close: Callable[[], None] | None = None,
) -> None:
    existing = state["widgets"].get("hero_audio_editor_win")
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                return
        except tk.TclError:
            pass

    ensure_hero_audio_widgets(state, values)
    current = _hero_audio_values_from_widgets(state)

    win = tk.Toplevel(host)
    win.title(_WIN_TITLE)
    win.transient(host)
    win.grab_set()
    win.geometry("560x420")
    win.minsize(480, 360)
    state["widgets"]["hero_audio_editor_win"] = win

    pad = ttk.Frame(win, padding=(14, 12))
    pad.pack(fill="both", expand=True)

    ttk.Label(pad, text="Opcjonalny dźwięk ambient hero", font=("", 10, "bold")).pack(anchor="w")
    ttk.Label(
        pad,
        text="Dźwięk nie startuje automatycznie — odwiedzający włącza go przyciskiem na stronie głównej.",
        wraplength=500,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 12))

    enable_var = tk.BooleanVar(value=bool(current.get("hero_audio_enable")))
    url_var = tk.StringVar(value=str(current.get("hero_audio_url") or ""))
    on_var = tk.StringVar(value=str(current.get("hero_audio_label_on") or "Włącz dźwięk"))
    off_var = tk.StringVar(value=str(current.get("hero_audio_label_off") or "Wycisz"))
    vol_var = tk.IntVar(value=int(current.get("hero_audio_volume") or 28))
    vol_label_var = tk.StringVar(value=f"{vol_var.get()}%")

    ttk.Checkbutton(pad, text="Włącz opcjonalny dźwięk hero", variable=enable_var).pack(anchor="w")

    file_frame = ttk.LabelFrame(pad, text="Plik audio", padding=(10, 8))
    file_frame.pack(fill="x", pady=(12, 0))

    url_row = ttk.Frame(file_frame)
    url_row.pack(fill="x")
    ttk.Label(url_row, text="URL CDN:", width=10).pack(side="left", anchor="n")
    url_entry = ttk.Entry(url_row, textvariable=url_var, width=52)
    url_entry.pack(side="left", fill="x", expand=True)

    def _pick_audio() -> None:
        path = filedialog.askopenfilename(
            parent=win,
            title="Wybierz plik audio",
            filetypes=[
                ("Audio", " ".join(f"*{ext}" for ext in sorted(AUDIO_SUFFIXES))),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not path:
            return

        try:
            url = upload_hero_audio(Path(path))
        except Exception as exc:
            messagebox.showerror(_WIN_TITLE, f"Nie udało się wgrać pliku:\n{exc}", parent=win)
            return

        url_var.set(url)
        enable_var.set(True)
        mark_dirty()
        status_var.set("Wgrano plik audio do Shopify Files.")

        # Toast jest tylko informacją pomocniczą. Jego ewentualny błąd nie może
        # zostać pokazany jako fałszywa awaria zakończonego już uploadu.
        try:
            _notify_audio_uploaded(show_toast, win)
        except Exception:
            pass

    btn_row = ttk.Frame(file_frame)
    btn_row.pack(anchor="w", pady=(8, 0))
    ttk.Button(btn_row, text="Wgraj plik audio…", command=_pick_audio).pack(side="left")
    ttk.Label(
        btn_row,
        text="  MP3, OGG, WAV, M4A — upload do Shopify Files",
        foreground="#777",
    ).pack(side="left")

    labels_frame = ttk.LabelFrame(pad, text="Przycisk na stronie", padding=(10, 8))
    labels_frame.pack(fill="x", pady=(12, 0))

    on_row = ttk.Frame(labels_frame)
    on_row.pack(fill="x", pady=(0, 6))
    ttk.Label(on_row, text="Włącz:", width=10).pack(side="left")
    ttk.Entry(on_row, textvariable=on_var, width=40).pack(side="left", fill="x", expand=True)

    off_row = ttk.Frame(labels_frame)
    off_row.pack(fill="x")
    ttk.Label(off_row, text="Wycisz:", width=10).pack(side="left")
    ttk.Entry(off_row, textvariable=off_var, width=40).pack(side="left", fill="x", expand=True)

    vol_frame = ttk.Frame(pad)
    vol_frame.pack(fill="x", pady=(12, 0))
    ttk.Label(vol_frame, text="Głośność ambientu:").pack(anchor="w")
    vol_controls = ttk.Frame(vol_frame)
    vol_controls.pack(fill="x", pady=(4, 0))

    def _update_vol_label(*_args: object) -> None:
        vol_label_var.set(f"{vol_var.get()}%")

    vol_scale = ttk.Scale(vol_controls, from_=0, to=100, orient="horizontal", variable=vol_var)
    vol_scale.pack(side="left", fill="x", expand=True)
    ttk.Label(vol_controls, textvariable=vol_label_var, width=5).pack(side="left", padx=(6, 0))
    vol_var.trace_add("write", _update_vol_label)

    def _apply() -> None:
        if enable_var.get() and not url_var.get().strip():
            messagebox.showwarning(
                _WIN_TITLE,
                "Włączono dźwięk, ale brak URL pliku audio. Wgraj plik lub wklej adres CDN.",
                parent=win,
            )
            return
        ensure_hero_audio_widgets(state, values)
        state["widgets"]["hero_audio_enable"].set(enable_var.get())
        state["widgets"]["hero_audio_url"].set(url_var.get().strip())
        state["widgets"]["hero_audio_label_on"].set(on_var.get().strip() or "Włącz dźwięk")
        state["widgets"]["hero_audio_label_off"].set(off_var.get().strip() or "Wycisz")
        state["widgets"]["hero_audio_volume"].set(max(0, min(100, int(vol_var.get()))))
        mark_dirty()
        if on_close:
            on_close()
        win.destroy()

    def _cancel() -> None:
        win.destroy()

    bottom = ttk.Frame(pad)
    bottom.pack(fill="x", pady=(16, 0))
    ttk.Button(bottom, text="Gotowe", command=_apply).pack(side="right")
    ttk.Button(bottom, text="Anuluj", command=_cancel).pack(side="right", padx=(0, 8))

    def _on_destroy(_evt=None) -> None:
        state["widgets"].pop("hero_audio_editor_win", None)

    win.protocol("WM_DELETE_WINDOW", _cancel)
    win.bind("<Destroy>", _on_destroy)


def add_hero_audio_launcher(
    parent: ttk.Frame,
    *,
    host: tk.Misc,
    values: dict[str, Any],
    state: dict[str, Any],
    mark_dirty: Callable[[], None],
    status_var: tk.StringVar,
    show_toast: Callable[..., None],
) -> None:
    ensure_hero_audio_widgets(state, values)

    summary_var = tk.StringVar(value=hero_audio_summary_text(values))
    state["widgets"]["hero_audio_summary"] = summary_var

    row = ttk.Frame(parent)
    row.pack(anchor="w")

    def _refresh_summary() -> None:
        summary_var.set(hero_audio_summary_text(_hero_audio_values_from_widgets(state)))

    def _open() -> None:
        open_hero_audio_editor_window(
            host,
            state=state,
            values=values,
            mark_dirty=mark_dirty,
            status_var=status_var,
            show_toast=show_toast,
            on_close=_refresh_summary,
        )

    ttk.Button(row, text="Dźwięk ambient…", command=_open).pack(side="left")
    ttk.Label(row, textvariable=summary_var, foreground="#666", wraplength=480).pack(
        side="left", padx=(10, 0)
    )
