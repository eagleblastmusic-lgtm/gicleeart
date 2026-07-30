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
    apply_scroll_video_selection,
    active_scroll_video_deploy_relpaths,
    active_scroll_video_frame_globs,
    clear_philosophy_scroll_bg,
    format_native_video_status,
    format_parallax_layer_status,
    format_philosophy_scroll_bg_status,
    format_status,
    parallax_deploy_relpaths,
    philosophy_scroll_bg_deploy_relpaths,
    read_native_video_status,
    read_parallax_layer_status,
    read_philosophy_scroll_bg_status,
    read_sequence_status,
    replace_native_video,
    replace_parallax_layer,
    replace_philosophy_scroll_bg,
    replace_video_sequence,
    sync_scroll_video_shopifyignore,
)


APP_TITLE = "Filozofia marki — animacja i treści"
_COMPONENT_ID = "filozofiamarki"
_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv"}
_IMAGE_SUFFIXES = {".webp", ".png", ".jpg", ".jpeg"}
_MIDDLE_SUFFIXES = _IMAGE_SUFFIXES | {".webm"}


_MIDDLE_SUFFIXES = _IMAGE_SUFFIXES | {".webm"}
_SCROLL_BG_SUFFIXES = _MIDDLE_SUFFIXES


def _render_scroll_story_bg(
    editor_inner: tk.Misc,
    *,
    row: int,
    host: tk.Misc,
    zone: Any = None,
    config: Any = None,
    set_zone_value=None,
    get_zone_value=None,
    mark_dirty=None,
) -> int:
    """Przycisk «Dodaj tło» w sekcji Animacja przewijana (pierwszy Film-scroll)."""
    del config, zone
    # Ustawienia tła są zwijaną grupą tej samej strefy scroll_story.
    bg_zone_id = "scroll_story"

    ttk.Label(editor_inner, text="Tło za filmem", font=("Segoe UI", 9, "bold")).grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(4, 2)
    )
    row += 1

    status_var = tk.StringVar()
    status_label = ttk.Label(
        editor_inner,
        textvariable=status_var,
        foreground="#555",
        justify="left",
    )
    status_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
    row += 1

    def refresh_status() -> None:
        mode = ""
        if callable(get_zone_value):
            mode = str(get_zone_value("scroll_background_mode", bg_zone_id) or "")
        try:
            status = read_philosophy_scroll_bg_status(kind=mode or None)
            text = format_philosophy_scroll_bg_status(status)
            if status.exists and mode not in {"asset", "webm", "image"}:
                text += (
                    "\n  Tryb strony: Auto — po «Dodaj tło» zapisz/wdrażaj, "
                    "żeby tło weszło na stronę."
                )
            status_var.set(text)
        except Exception as exc:
            status_var.set(f"Nie udało się odczytać tła: {exc}")

    def notify_assets_changed() -> None:
        try:
            host.winfo_toplevel().event_generate(
                "<<GicleeThemeAssetsChanged>>",
                when="tail",
            )
        except tk.TclError:
            pass

    def apply_mode(mode: str) -> None:
        if callable(set_zone_value):
            set_zone_value(bg_zone_id, "scroll_background_mode", mode)
            if mode in {"asset", "webm"}:
                set_zone_value(bg_zone_id, "scroll_background_value", "")
        if callable(mark_dirty):
            mark_dirty()

    def add_background() -> None:
        selected = filedialog.askopenfilename(
            parent=host,
            title="Dodaj tło — Animacja przewijana",
            filetypes=(
                ("Obraz lub WebM + alfa", "*.webp *.png *.jpg *.jpeg *.webm"),
                ("WebM z alfą", "*.webm"),
                ("Obrazy", "*.webp *.png *.jpg *.jpeg"),
                ("Wszystkie pliki", "*.*"),
            ),
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in _SCROLL_BG_SUFFIXES:
            messagebox.showwarning(
                APP_TITLE,
                "Wybierz plik WebP, PNG, JPG albo WebM z alfą.",
                parent=host,
            )
            return
        kind_note = (
            "\n\nTło jako WebM z alfą (pętla pod filmem scrolla)."
            if path.suffix.lower() == ".webm"
            else "\n\nTło jako obraz (cover za filmem)."
        )
        if not messagebox.askyesno(
            APP_TITLE,
            (
                f"Ustawić tło pierwszego video scrolla z pliku:\n{path.name}"
                f"{kind_note}"
            ),
            parent=host,
        ):
            return
        try:
            dest, mode = replace_philosophy_scroll_bg(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            refresh_status()
            return
        apply_mode(mode)
        refresh_status()
        notify_assets_changed()
        status = read_philosophy_scroll_bg_status(kind=mode)
        dims = (
            f"{status.width}×{status.height}"
            if status.width and status.height
            else "rozmiar nieznany"
        )
        messagebox.showinfo(
            APP_TITLE,
            (
                f"Gotowe — tło ({'WebM + alfa' if mode == 'webm' else 'obraz'}):\n"
                f"{dims}\n{dest}\n\n"
                "Zapisz wariant i wdroż, żeby zobaczyć zmianę na stronie."
            ),
            parent=host,
        )

    def remove_background() -> None:
        if not messagebox.askyesno(
            APP_TITLE,
            "Usunąć tło pierwszego video scrolla i wrócić do trybu Auto?",
            parent=host,
        ):
            return
        try:
            clear_philosophy_scroll_bg()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return
        apply_mode("auto")
        refresh_status()
        notify_assets_changed()

    buttons = ttk.Frame(editor_inner)
    buttons.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
    ttk.Button(buttons, text="Dodaj tło…", command=add_background).pack(side="left")
    ttk.Button(buttons, text="Usuń tło", command=remove_background).pack(
        side="left", padx=(8, 0)
    )
    ttk.Button(buttons, text="Odśwież", command=refresh_status).pack(
        side="left", padx=(8, 0)
    )
    row += 1
    refresh_status()
    return row


def _render_wrota_parallax_zone(
    editor_inner: tk.Misc,
    *,
    row: int,
    host: tk.Misc,
    zone: Any = None,
    config: Any = None,
) -> int:
    """Panel sekcji «Tło paralaksy — po Wrotach»."""
    del zone, config
    editor_inner.columnconfigure(0, weight=1)

    ttk.Label(
        editor_inner,
        text=(
            "Bottom = obraz tła. Middle = obraz albo WebM z kanałem alfa "
            "(blend screen). WebP/WebM kopiowane 1:1; PNG/JPG → WebP."
        ),
        wraplength=520,
        foreground="#444",
        justify="left",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
    row += 1

    status_var = tk.StringVar()
    status_label = ttk.Label(
        editor_inner,
        textvariable=status_var,
        foreground="#555",
        justify="left",
    )
    status_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
    row += 1

    def refresh_status() -> None:
        try:
            status_var.set(
                "\n".join(
                    (
                        format_parallax_layer_status(
                            read_parallax_layer_status("bottom")
                        ),
                        format_parallax_layer_status(
                            read_parallax_layer_status("middle")
                        ),
                    )
                )
            )
        except Exception as exc:
            status_var.set(f"Nie udało się odczytać tła: {exc}")

    def notify_assets_changed() -> None:
        try:
            host.winfo_toplevel().event_generate(
                "<<GicleeThemeAssetsChanged>>",
                when="tail",
            )
        except tk.TclError:
            pass

    def finish_ok(layer: str, dest: Path) -> None:
        status = read_parallax_layer_status(layer)
        refresh_status()
        notify_assets_changed()
        label = "Bottom" if layer == "bottom" else "Middle"
        kind = "WebM + alfa" if status.kind == "webm" else "obraz"
        dims = (
            f"{status.width}×{status.height}"
            if status.width and status.height
            else "rozmiar nieznany"
        )
        messagebox.showinfo(
            APP_TITLE,
            (
                f"Gotowe — {label} ({kind}):\n{dims}\n{dest}\n\n"
                "Aby opublikować, użyj przycisku wdrożenia."
            ),
            parent=host,
        )

    def add_layer(layer: str) -> None:
        label = "Bottom" if layer == "bottom" else "Middle"
        if layer == "middle":
            filetypes = (
                ("Obraz lub WebM + alfa", "*.webp *.png *.jpg *.jpeg *.webm"),
                ("WebM z alfą", "*.webm"),
                ("Obrazy", "*.webp *.png *.jpg *.jpeg"),
                ("Wszystkie pliki", "*.*"),
            )
            allowed = _MIDDLE_SUFFIXES
            warn = "Wybierz plik WebP, PNG, JPG albo WebM z alfą."
        else:
            filetypes = (
                ("Obrazy", "*.webp *.png *.jpg *.jpeg"),
                ("WebP", "*.webp"),
                ("Wszystkie pliki", "*.*"),
            )
            allowed = _IMAGE_SUFFIXES
            warn = "Wybierz plik WebP, PNG lub JPG."

        selected = filedialog.askopenfilename(
            parent=host,
            title=f"Dodaj tło paralaksy — {label}",
            filetypes=filetypes,
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in allowed:
            messagebox.showwarning(APP_TITLE, warn, parent=host)
            return
        kind_note = (
            "\n\nMiddle jako WebM z alfą (pętla + screen blend)."
            if layer == "middle" and path.suffix.lower() == ".webm"
            else ""
        )
        if not messagebox.askyesno(
            APP_TITLE,
            (
                f"Podmienić warstwę {label} plikiem:\n{path.name}"
                f"{kind_note}\n\n"
                "Poprzedni plik w assets zostanie nadpisany."
            ),
            parent=host,
        ):
            return
        try:
            dest = replace_parallax_layer(path, layer=layer)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            refresh_status()
            return
        finish_ok(layer, dest)

    def on_drop(event: Any) -> None:
        paths = parse_dnd_files(getattr(event, "data", "") or "")
        media = next(
            (
                path
                for path in paths
                if path.suffix.lower() in _MIDDLE_SUFFIXES
            ),
            None,
        )
        if not media:
            messagebox.showwarning(
                APP_TITLE,
                "Upuść plik WebP, PNG, JPG albo WebM.",
                parent=host,
            )
            return
        choice = messagebox.askyesnocancel(
            APP_TITLE,
            (
                f"Upuścisz: {media.name}\n\n"
                "Tak = Bottom (tylko obraz)\n"
                "Nie = Middle (obraz lub WebM)\n"
                "Anuluj = przerwij"
            ),
            parent=host,
        )
        if choice is None:
            return
        layer = "bottom" if choice else "middle"
        if layer == "bottom" and media.suffix.lower() == ".webm":
            messagebox.showwarning(
                APP_TITLE,
                "Bottom przyjmuje tylko obraz (WebP/PNG/JPG).",
                parent=host,
            )
            return
        try:
            dest = replace_parallax_layer(media, layer=layer)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            refresh_status()
            return
        finish_ok(layer, dest)

    buttons = ttk.Frame(editor_inner)
    buttons.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
    ttk.Button(
        buttons,
        text="Dodaj tło Bottom…",
        command=lambda: add_layer("bottom"),
    ).pack(side="left")
    ttk.Button(
        buttons,
        text="Dodaj tło Middle…",
        command=lambda: add_layer("middle"),
    ).pack(side="left", padx=(8, 0))
    ttk.Button(buttons, text="Odśwież", command=refresh_status).pack(
        side="left", padx=(8, 0)
    )
    row += 1

    for target in (editor_inner, status_label, buttons):
        register_drop_target(target, on_drop=on_drop)
    refresh_status()
    return row


def _config():
    sync_scroll_video_shopifyignore()
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Strona Filozofia marki",
        intro_body=(
            "Edytujesz animację przewijaną, portal Wrota oraz charakter odtwarzania. "
            "W strefie «Scroll strony» wybierzesz Standardowy, Płynny lub Lenis "
            "i ustawisz responsywność przewijania. "
            "Źródła filmów podmienisz w panelach powyżej edytora. "
            "Tło paralaksy po Wrotach — w sekcji listy po lewej."
        ),
        template_rel="templates/page.filozofia-marki.json",
        preview_path="/pages/filozofia-marki",
        variant_id_prefix="fm",
        zones=PAGE_ZONES,
        section_effects_asset_enabled=False,
        extra_deploy_relpaths=(
            *active_scroll_video_deploy_relpaths(),
            *parallax_deploy_relpaths(),
            *philosophy_scroll_bg_deploy_relpaths(),
            "assets/giclee-scroll-motion-presets.json",
            "assets/giclee-scroll-scrub-video.js",
            "assets/giclee-filozofia-quote-pin.js",
            "assets/giclee-filozofia-wrota-portal.js",
            "assets/giclee-page-smooth-scroll.js",
            "assets/lenis.min.js",
            "assets/lenis.css",
            "sections/giclee-page-scroll-config.liquid",
            "snippets/scripts.liquid",
            "snippets/media.liquid",
            "blocks/_media-without-appearance.liquid",
        ),
        extra_deploy_globs=active_scroll_video_frame_globs(),
        after_template_save=apply_scroll_video_selection,
        zone_content_builders={
            "scroll_story": _render_scroll_story_bg,
            "wrota_parallax": _render_wrota_parallax_zone,
        },
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
            "Gotowy WebM jest kopiowany 1:1 bez ponownego kodowania i może zachować "
            "kanał alfa. MP4 jest przygotowywany jako H.264 z klatką kluczową na każdej "
            "klatce, ale bez alfy. Klatki WebP zachowują przezroczystość. "
            "Panel pokaże wykryty FPS, kodek, alfę i aktywny fallback. "
            "Podmieniany jest tylko wybrany wariant."
        ),
        wraplength=1080,
        justify="left",
    ).grid(row=0, column=0, columnspan=3, sticky="w")

    mode_var = tk.StringVar(value="mp4")
    quality_var = tk.StringVar(value="1080p")
    choices = ttk.Frame(body)
    choices.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 4))
    ttk.Label(choices, text="Sposób:").pack(side="left")
    ttk.Radiobutton(
        choices,
        text="Film MP4",
        variable=mode_var,
        value="mp4",
    ).pack(side="left", padx=(8, 4))
    ttk.Radiobutton(
        choices,
        text="Gotowy WebM — bez konwersji",
        variable=mode_var,
        value="webm",
    ).pack(side="left", padx=(4, 4))
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
                            read_native_video_status(
                                quality="720p",
                                family=family,
                                container="mp4",
                            )
                        ),
                        format_native_video_status(
                            read_native_video_status(
                                quality="1080p",
                                family=family,
                                container="mp4",
                            )
                        ),
                        format_native_video_status(
                            read_native_video_status(
                                quality="720p",
                                family=family,
                                container="webm",
                            )
                        ),
                        format_native_video_status(
                            read_native_video_status(
                                quality="1080p",
                                family=family,
                                container="webm",
                            )
                        ),
                    )
                )
            )
        except Exception as exc:
            status_var.set(f"Nie udało się odczytać sekwencji: {exc}")

    def finish_success(result: Any, prepared_mode: str | None = None) -> None:
        progress.stop()
        progress.grid_remove()
        replace_button.configure(state="normal")
        try:
            sync_scroll_video_shopifyignore()
        except Exception:
            pass
        refresh_status()
        try:
            host.winfo_toplevel().event_generate(
                "<<GicleeThemeAssetsChanged>>",
                when="tail",
            )
        except tk.TclError:
            pass
        result_mode = getattr(result, "container", None) or "frames"
        mode_label = {
            "mp4": "Film MP4",
            "webm": "Gotowy WebM",
            "frames": "Klatki WebP",
        }[result_mode]
        summary = (
            f"{mode_label} {result.quality}: {result.status.frame_count} klatek, "
            f"{result.status.width}×{result.status.height}, {result.status.fps} FPS"
        )
        backup_info = (
            f"\n\nKopia poprzednich sekwencji:\n{result.backup_path}"
            if result.backup_path
            else ""
        )
        if result_mode == "webm":
            activation_info = (
                "\n\nW edytorze ustaw: Sposób odtwarzania = Film, "
                "Format filmu = WebM oraz tę samą jakość."
            )
        elif result_mode == "frames":
            activation_info = (
                "\n\nW edytorze ustaw: Sposób odtwarzania = Klatki WebP "
                "oraz tę samą jakość."
            )
        else:
            activation_info = ""
        messagebox.showinfo(
            APP_TITLE,
            (
                f"Gotowe ({family}):\n{summary}{backup_info}{activation_info}\n\n"
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
        if mode_var.get() == "webm" and path.suffix.lower() != ".webm":
            messagebox.showwarning(
                APP_TITLE,
                "Wybrany tryb WebM wymaga pliku z rozszerzeniem .webm.",
                parent=host,
            )
            return
        selected_mode_label = {
            "mp4": "Film MP4",
            "webm": "Gotowy WebM — bez konwersji",
            "frames": "Klatki WebP",
        }[mode_var.get()]
        if not messagebox.askyesno(
            APP_TITLE,
            (
                f"Przygotować z pliku:\n{path.name}\n\n"
                f"Rodzina: {family}\n"
                f"Tryb: {selected_mode_label}\n"
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
            f"{selected_mode_label.lower()} "
            f"{selected_quality}"
            f"{' / bez konwersji' if selected_mode == 'webm' else ' / 60 FPS'}…"
        )

        def worker() -> None:
            try:
                if selected_mode in {"mp4", "webm"}:
                    result = replace_native_video(
                        path,
                        quality=selected_quality,
                        family=family,
                        container=selected_mode,
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
                    host.after(
                        0,
                        lambda value=result, mode=selected_mode: finish_success(
                            value, mode
                        ),
                    )
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
