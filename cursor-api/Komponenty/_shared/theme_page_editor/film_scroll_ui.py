"""Kontrolki źródła dla dynamicznej sekcji Film-scroll."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from Komponenty.filozofiamarki.video_sequence import (
    list_native_video_assets,
    replace_native_video,
)

from .film_scroll import SHARED_ASSET_FAMILY


_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv"}


def build_film_scroll_source_controls(
    editor_inner: tk.Misc,
    *,
    row: int,
    host: tk.Misc,
    zone_id: str,
    app_title: str,
    get_zone_value: Callable[[str], Any],
    set_zone_value: Callable[[str, str, Any], None],
    refresh_editor: Callable[[], None],
) -> int:
    """Dodaj przycisk importu. Wybór trafia do pola konkretnej instancji."""

    frame = ttk.Frame(editor_inner)
    frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    frame.columnconfigure(1, weight=1)
    status_var = tk.StringVar(value="")
    progress = ttk.Progressbar(frame, mode="indeterminate", length=140)

    def finish_error(exc: Exception) -> None:
        progress.stop()
        progress.grid_remove()
        prepare_button.configure(state="normal")
        status_var.set("")
        messagebox.showerror(app_title, str(exc), parent=host)

    def finish_success(result: Any) -> None:
        progress.stop()
        progress.grid_remove()
        prepare_button.configure(state="normal")
        library_path = getattr(result, "library_video_path", None)
        selected = None
        if library_path is not None:
            for item in list_native_video_assets(
                family=SHARED_ASSET_FAMILY,
                container=result.container,
                quality=result.quality,
            ):
                if item.video == Path(library_path).name:
                    selected = item
                    break
        if selected is None:
            finish_error(
                RuntimeError("Film przygotowano, ale nie odnaleziono go w bibliotece.")
            )
            return
        set_zone_value(zone_id, "scroll_video_source", selected.source_spec)
        set_zone_value(zone_id, "scroll_video_engine", "video")
        set_zone_value(zone_id, "scroll_video_container", result.container)
        set_zone_value(zone_id, "scroll_video_quality", result.quality)
        set_zone_value(zone_id, "_enabled", True)
        status_var.set(
            f"Gotowe: {selected.width}×{selected.height}, "
            f"{selected.fps} FPS, {result.container.upper()}."
        )
        try:
            host.winfo_toplevel().event_generate(
                "<<GicleeThemeAssetsChanged>>",
                when="tail",
            )
        except tk.TclError:
            pass
        refresh_editor()

    def prepare() -> None:
        engine = str(get_zone_value("scroll_video_engine") or "video")
        if engine != "video":
            messagebox.showinfo(
                app_title,
                "Przycisk przygotowuje natywny film MP4/WebM. "
                "Najpierw wybierz «Film — MP4 lub WebM».",
                parent=host,
            )
            return
        container = str(get_zone_value("scroll_video_container") or "webm")
        quality = str(get_zone_value("scroll_video_quality") or "1080p")
        selected = filedialog.askopenfilename(
            parent=host,
            title="Przygotuj film dla Scroll Film",
            filetypes=(
                ("Filmy", "*.webm *.mp4 *.mov *.mkv"),
                ("Wszystkie pliki", "*.*"),
            ),
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in _VIDEO_SUFFIXES:
            messagebox.showwarning(
                app_title,
                "Wybierz plik MP4, WebM, MOV albo MKV.",
                parent=host,
            )
            return
        if container == "webm" and path.suffix.lower() != ".webm":
            messagebox.showwarning(
                app_title,
                "Format WebM wymaga gotowego pliku .webm. "
                "Wybierz MP4, jeżeli plik ma zostać przekonwertowany.",
                parent=host,
            )
            return
        if not messagebox.askyesno(
            app_title,
            f"Przygotować {path.name} jako {container.upper()} {quality}?",
            parent=host,
        ):
            return
        prepare_button.configure(state="disabled")
        progress.grid(row=0, column=2, padx=(8, 0))
        progress.start(12)
        status_var.set(f"Przygotowuję {path.name}…")

        def worker() -> None:
            try:
                result = replace_native_video(
                    path,
                    quality=quality,
                    family=SHARED_ASSET_FAMILY,
                    container=container,
                )
            except Exception as exc:
                try:
                    host.after(0, lambda err=exc: finish_error(err))
                except tk.TclError:
                    return
            else:
                try:
                    host.after(0, lambda value=result: finish_success(value))
                except tk.TclError:
                    return

        threading.Thread(
            target=worker,
            name="giclee-film-scroll-prepare",
            daemon=True,
        ).start()

    prepare_button = ttk.Button(
        frame,
        text="Przygotuj nowy film…",
        command=prepare,
    )
    prepare_button.grid(row=0, column=0, sticky="w")
    ttk.Label(frame, textvariable=status_var, foreground="#555").grid(
        row=0,
        column=1,
        sticky="w",
        padx=(10, 0),
    )
    progress.grid_remove()
    return row + 1


__all__ = ["build_film_scroll_source_controls"]
