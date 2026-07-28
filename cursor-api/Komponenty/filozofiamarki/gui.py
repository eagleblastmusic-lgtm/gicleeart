"""GUI: Filozofia marki — aktualna animacja scrollowana i jej treści."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.theme_page_editor.bootstrap import (
    build_editor_config,
    build_page_ui,
)
from Komponenty._shared.tkdnd_safe import parse_dnd_files, register_drop_target
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES
from .video_sequence import (
    format_native_video_status,
    format_status,
    read_native_video_status,
    read_sequence_status,
    replace_native_video,
    replace_video_sequence,
)


APP_TITLE = "Filozofia marki — animacja i treści"
_COMPONENT_ID = "filozofiamarki"
_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv"}


def _config():
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Strona Filozofia marki",
        intro_body=(
            "Edytujesz animację przewijaną, portal Wrota oraz charakter odtwarzania. "
            "Źródła filmów podmienisz w panelach powyżej edytora (rozwiń akordeon)."
        ),
        template_rel="templates/page.filozofia-marki.json",
        preview_path="/pages/filozofia-marki",
        variant_id_prefix="fm",
        zones=PAGE_ZONES,
        section_effects_asset_enabled=False,
        extra_deploy_relpaths=(
            "assets/giclee-philosophy-v3-manifest.json",
            "assets/giclee-philosophy-1080-manifest.json",
            "assets/giclee-philosophy-video-720-manifest.json",
            "assets/giclee-philosophy-video-1080-manifest.json",
            "assets/giclee-philosophy-scroll-720.mp4",
            "assets/giclee-philosophy-scroll-1080.mp4",
            "assets/giclee-philosophy-video-720-poster.webp",
            "assets/giclee-philosophy-video-1080-poster.webp",
            "assets/giclee-philosophy-wrota-video-720-manifest.json",
            "assets/giclee-philosophy-wrota-video-1080-manifest.json",
            "assets/giclee-philosophy-wrota-scroll-720.mp4",
            "assets/giclee-philosophy-wrota-scroll-1080.mp4",
            "assets/giclee-philosophy-wrota-video-720-poster.webp",
            "assets/giclee-philosophy-wrota-video-1080-poster.webp",
            "assets/giclee-scroll-motion-presets.json",
            "assets/giclee-scroll-scrub-video.js",
            "assets/giclee-filozofia-quote-pin.js",
            "assets/giclee-filozofia-wrota-portal.js",
            "snippets/media.liquid",
            "blocks/_media-without-appearance.liquid",
        ),
        extra_deploy_globs=(
            "assets/giclee-philosophy-v3-frame-*.webp",
            "assets/giclee-philosophy-1080-frame-*.webp",
            "assets/giclee-philosophy-wrota-720-frame-*.webp",
            "assets/giclee-philosophy-wrota-1080-frame-*.webp",
        ),
    )


def _build_video_panel(
    host: tk.Misc,
    *,
    title: str,
    family: str,
    dialog_title: str,
    expanded: bool = False,
) -> None:
    shell = ttk.Frame(host)
    shell.pack(fill="x", padx=12, pady=(10, 0))

    open_var = tk.BooleanVar(value=expanded)
    header = ttk.Frame(shell)
    header.pack(fill="x")

    toggle_btn = ttk.Button(header, width=3)
    toggle_btn.pack(side="left")
    ttk.Label(header, text=title, font=("Segoe UI", 10, "bold")).pack(
        side="left", padx=(8, 0)
    )

    body = ttk.Frame(shell, padding=(4, 8, 4, 4))
    body.columnconfigure(0, weight=1)

    def _set_toggle_label() -> None:
        toggle_btn.configure(text="▾" if open_var.get() else "▸")

    def _apply_expanded() -> None:
        if open_var.get():
            body.pack(fill="x", after=header)
        else:
            body.pack_forget()
        _set_toggle_label()

    def _toggle() -> None:
        open_var.set(not open_var.get())
        _apply_expanded()

    toggle_btn.configure(command=_toggle)
    header.bind("<Button-1>", lambda _event: _toggle())

    ttk.Label(
        body,
        text=(
            "Wybierz film MP4, WebM, MOV lub MKV, sposób przygotowania i rozdzielczość. "
            "Klatki zachowują "
            "przezroczystość jako WebP; film jest odtwarzany natywnie jako MP4 "
            "H.264 z klatką kluczową na każdej klatce, ale bez kanału alfa. "
            "Panel pokaże wykryty FPS, kodek, alfę i aktywny fallback. "
            "Podmieniany jest tylko wybrany wariant."
        ),
        wraplength=1080,
        justify="left",
    ).grid(row=0, column=0, columnspan=3, sticky="w")

    mode_var = tk.StringVar(value="video")
    quality_var = tk.StringVar(value="1080p")
    choices = ttk.Frame(body)
    choices.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 4))
    ttk.Label(choices, text="Sposób:").pack(side="left")
    ttk.Radiobutton(
        choices,
        text="Film MP4",
        variable=mode_var,
        value="video",
    ).pack(side="left", padx=(8, 4))
    ttk.Radiobutton(
        choices,
        text="Klatki WebP",
        variable=mode_var,
        value="frames",
    ).pack(side="left", padx=(4, 16))
    ttk.Label(choices, text="Rozdzielczość:").pack(side="left")
    ttk.Combobox(
        choices,
        textvariable=quality_var,
        values=("720p", "1080p"),
        state="readonly",
        width=8,
    ).pack(side="left", padx=(8, 0))

    status_var = tk.StringVar()
    status_label = ttk.Label(
        body,
        textvariable=status_var,
        foreground="#555",
        justify="left",
    )
    status_label.grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 8))

    progress = ttk.Progressbar(body, mode="indeterminate", length=190)
    progress.grid(row=3, column=2, sticky="e", padx=(10, 0))

    def refresh_status() -> None:
        try:
            status_var.set(
                "\n".join(
                    (
                        format_status(
                            read_sequence_status(quality="720p", family=family)
                        ),
                        format_status(
                            read_sequence_status(quality="1080p", family=family)
                        ),
                        format_native_video_status(
                            read_native_video_status(quality="720p", family=family)
                        ),
                        format_native_video_status(
                            read_native_video_status(quality="1080p", family=family)
                        ),
                    )
                )
            )
        except Exception as exc:
            status_var.set(f"Nie udało się odczytać sekwencji: {exc}")

    def finish_success(result: Any) -> None:
        progress.stop()
        progress.grid_remove()
        replace_button.configure(state="normal")
        refresh_status()
        mode_label = "Film MP4" if mode_var.get() == "video" else "Klatki WebP"
        summary = (
            f"{mode_label} {result.quality}: {result.status.frame_count} klatek, "
            f"{result.status.width}×{result.status.height}, {result.status.fps} FPS"
        )
        backup_info = (
            f"\n\nKopia poprzednich sekwencji:\n{result.backup_path}"
            if result.backup_path
            else ""
        )
        messagebox.showinfo(
            APP_TITLE,
            (
                f"Gotowe ({family}):\n{summary}{backup_info}\n\n"
                "Aby opublikować wariant, użyj przycisku wdrożenia w edytorze poniżej."
            ),
            parent=host,
        )

    def finish_error(exc: Exception) -> None:
        progress.stop()
        progress.grid_remove()
        replace_button.configure(state="normal")
        refresh_status()
        messagebox.showerror(APP_TITLE, str(exc), parent=host)

    def prepare_video(path: Path) -> None:
        path = Path(path)
        if path.suffix.lower() not in _VIDEO_SUFFIXES:
            messagebox.showwarning(
                APP_TITLE,
                "Wybierz plik MP4, WebM, MOV lub MKV.",
                parent=host,
            )
            return
        if not messagebox.askyesno(
            APP_TITLE,
            (
                f"Przygotować z pliku:\n{path.name}\n\n"
                f"Rodzina: {family}\n"
                f"Tryb: {'Film MP4' if mode_var.get() == 'video' else 'Klatki WebP'}\n"
                f"Jakość: {quality_var.get()}\n\n"
                "Poprzedni wariant trafi do automatycznej kopii zapasowej."
            ),
            parent=host,
        ):
            return

        # Przy starcie prepare zawsze pokaż panel, żeby widać postęp.
        if not open_var.get():
            open_var.set(True)
            _apply_expanded()

        replace_button.configure(state="disabled")
        progress.grid()
        progress.start(12)
        selected_mode = mode_var.get()
        selected_quality = quality_var.get()
        status_var.set(
            f"Przetwarzam {path.name} — "
            f"{'film MP4' if selected_mode == 'video' else 'klatki WebP'} "
            f"{selected_quality} / 60 FPS…"
        )

        def worker() -> None:
            try:
                if selected_mode == "video":
                    result = replace_native_video(
                        path,
                        quality=selected_quality,
                        family=family,
                    )
                else:
                    result = replace_video_sequence(
                        path,
                        quality=selected_quality,
                        family=family,
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
            name=f"filozofia-video-sequence-{family}",
            daemon=True,
        ).start()

    def choose_video() -> None:
        selected = filedialog.askopenfilename(
            parent=host,
            title=dialog_title,
            filetypes=(
                ("Filmy", "*.webm *.mp4 *.mov *.mkv"),
                ("Wszystkie pliki", "*.*"),
            ),
        )
        if selected:
            prepare_video(Path(selected))

    def on_drop(event: Any) -> None:
        paths = parse_dnd_files(getattr(event, "data", "") or "")
        video = next(
            (path for path in paths if path.suffix.lower() in _VIDEO_SUFFIXES),
            None,
        )
        if video:
            prepare_video(video)
        else:
            messagebox.showwarning(
                APP_TITLE,
                "Upuść jeden plik MP4, WebM, MOV lub MKV.",
                parent=host,
            )

    replace_button = ttk.Button(
        body,
        text="Wybierz źródło i przygotuj wariant…",
        command=choose_video,
    )
    replace_button.grid(row=3, column=0, sticky="w")
    ttk.Button(body, text="Odśwież informacje", command=refresh_status).grid(
        row=3,
        column=1,
        sticky="w",
        padx=(8, 0),
    )
    progress.grid_remove()
    for target in (body, status_label):
        register_drop_target(target, on_drop=on_drop)
    refresh_status()
    _apply_expanded()


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1180, 820)
    root.minsize(880, 620)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    shell = ttk.Frame(host)
    shell.pack(fill="both", expand=True)
    _build_video_panel(
        shell,
        title="Film-scroll — źródło animacji",
        family="philosophy",
        dialog_title="Wybierz film animacji Filozofia marki",
        expanded=False,
    )
    _build_video_panel(
        shell,
        title="Film-scroll — Wrota (portal)",
        family="wrota",
        dialog_title="Wybierz film portalu Wrota",
        expanded=False,
    )
    editor = ttk.Frame(shell)
    editor.pack(fill="both", expand=True)
    build_page_ui(editor, _config(), inline=inline)


__all__ = ["APP_TITLE", "_build_ui", "main"]
