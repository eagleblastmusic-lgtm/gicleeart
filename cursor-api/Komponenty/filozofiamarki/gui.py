"""GUI: Filozofia marki — aktualna animacja scrollowana i jej treści."""

from __future__ import annotations

import json
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
    BEFORE_AFTER_MAX_ITEMS,
    apply_scroll_video_selection,
    active_scroll_video_deploy_relpaths,
    active_scroll_video_frame_globs,
    clear_philosophy_scroll_bg,
    clear_quote_bg,
    format_native_video_status,
    format_parallax_layer_status,
    format_philosophy_scroll_bg_status,
    format_quote_bg_status,
    format_status,
    parallax_deploy_relpaths,
    philosophy_scroll_bg_deploy_relpaths,
    quote_bg_deploy_relpaths,
    read_native_video_status,
    read_before_after_status,
    read_parallax_layer_status,
    read_philosophy_scroll_bg_status,
    read_quote_bg_status,
    read_sequence_status,
    replace_native_video,
    replace_before_after_image,
    replace_parallax_layer,
    replace_philosophy_scroll_bg,
    replace_quote_bg,
    replace_video_sequence,
    sync_scroll_video_shopifyignore,
)


APP_TITLE = "Filozofia marki — animacja i treści"
_COMPONENT_ID = "filozofiamarki"
_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv"}
_IMAGE_SUFFIXES = {".webp", ".png", ".jpg", ".jpeg"}
_SCROLL_BG_SUFFIXES = _IMAGE_SUFFIXES | {".webm"}
_BEFORE_AFTER_TEXT_DEFAULTS = {
    "brand": "Before / After Archive",
    "scrollHint": "Scroll to explore",
    "beforeLabel": "Before",
    "afterLabel": "After",
    "dragHint": "Drag to reveal",
    "frameLabel": "Frame",
}


def _before_after_texts_from_json(raw: object) -> dict[str, Any]:
    try:
        parsed = json.loads(str(raw or "{}"))
    except (TypeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    result: dict[str, Any] = {
        key: str(parsed.get(key) or default)
        for key, default in _BEFORE_AFTER_TEXT_DEFAULTS.items()
    }
    raw_slides = parsed.get("slides")
    slides = raw_slides if isinstance(raw_slides, list) else []
    result["slides"] = []
    for index in range(BEFORE_AFTER_MAX_ITEMS):
        source = slides[index] if index < len(slides) and isinstance(slides[index], dict) else {}
        result["slides"].append(
            {
                "title": str(source.get("title") or f"Porównanie {index + 1}"),
                "location": str(source.get("location") or "Giclée Art · Reprodukcja"),
                "type": str(source.get("type") or "Przed / Po"),
            }
        )
    return result


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
    set_zone_value=None,
    get_zone_value=None,
    mark_dirty=None,
) -> int:
    """Panel sekcji «Tło paralaksy — po Wrotach»."""
    del zone, config, mark_dirty
    editor_inner.columnconfigure(0, weight=1)

    ttk.Label(
        editor_inner,
        text=(
            "Bottom = jedyna warstwa tła paralaksy. "
            "WebP kopiowany 1:1; PNG/JPG → WebP."
        ),
        wraplength=520,
        foreground="#444",
        justify="left",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
    row += 1

    raw_parallax = (
        get_zone_value("fm_bg_parallax_enabled")
        if callable(get_zone_value)
        else True
    )
    parallax_var = tk.BooleanVar(
        value=True if raw_parallax in ("", None) else bool(raw_parallax)
    )

    def persist_parallax(*_args: Any) -> None:
        if callable(set_zone_value):
            set_zone_value(
                "wrota_parallax",
                "fm_bg_parallax_enabled",
                bool(parallax_var.get()),
            )

    ttk.Checkbutton(
        editor_inner,
        text="Paralaksa tła (mysz, desktop)",
        variable=parallax_var,
        command=persist_parallax,
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
    row += 1
    ttk.Label(
        editor_inner,
        text=(
            "Subtelny ruch warstwy Bottom pod kursorem. Wyłączony na mobile "
            "i przy prefers-reduced-motion. Teksty cinematic-quote oraz "
            "galeria Przed i po działają niezależnie od tego przełącznika."
        ),
        wraplength=520,
        foreground="#555",
        justify="left",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
    row += 1
    parallax_var.trace_add("write", persist_parallax)

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
                format_parallax_layer_status(
                    read_parallax_layer_status("bottom")
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
        label = "Bottom"
        kind = "obraz"
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
        label = "Bottom"
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
        if not messagebox.askyesno(
            APP_TITLE,
            (
                f"Podmienić warstwę {label} plikiem:\n{path.name}\n\n"
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
                if path.suffix.lower() in _IMAGE_SUFFIXES
            ),
            None,
        )
        if not media:
            messagebox.showwarning(
                APP_TITLE,
                "Upuść plik WebP, PNG lub JPG.",
                parent=host,
            )
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Podmienić tło Bottom plikiem:\n{media.name}?",
            parent=host,
        ):
            return
        layer = "bottom"
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
    ttk.Button(buttons, text="Odśwież", command=refresh_status).pack(
        side="left", padx=(8, 0)
    )
    row += 1

    for target in (editor_inner, status_label, buttons):
        register_drop_target(target, on_drop=on_drop)
    refresh_status()
    return row


def _render_quote_screen_zone(
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
    """Panel tła sticky ekranu cytatu przed Wrotami."""
    del zone, config, mark_dirty
    editor_inner.columnconfigure(0, weight=1)

    ttk.Label(
        editor_inner,
        text=(
            "Tło pod cytatem i liniami (pełny sticky viewport). "
            "WebP kopiowany 1:1; PNG/JPG → WebP. Bez pliku zostaje czarne tło strony."
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

    def _opacity_pct(raw: object, default: int = 100) -> int:
        try:
            return max(0, min(100, int(raw)))
        except (TypeError, ValueError):
            return default

    def _read_opacity(field_id: str, default: int = 100) -> int:
        if not callable(get_zone_value):
            return default
        raw = get_zone_value(field_id)
        if raw in ("", None):
            return default
        return _opacity_pct(raw, default)

    text_bg_var = tk.IntVar(value=_read_opacity("fm_quote_text_bg_opacity"))
    top_above_var = tk.IntVar(
        value=_read_opacity(
            "fm_quote_divider_top_above_opacity",
            _read_opacity("fm_quote_divider_top_bg_opacity"),
        )
    )
    top_below_var = tk.IntVar(
        value=_read_opacity(
            "fm_quote_divider_top_below_opacity",
            _read_opacity("fm_quote_divider_top_bg_opacity"),
        )
    )
    bottom_above_var = tk.IntVar(
        value=_read_opacity(
            "fm_quote_divider_bottom_above_opacity",
            _read_opacity("fm_quote_divider_bottom_bg_opacity"),
        )
    )
    bottom_below_var = tk.IntVar(
        value=_read_opacity(
            "fm_quote_divider_bottom_below_opacity",
            _read_opacity("fm_quote_divider_bottom_bg_opacity"),
        )
    )
    text_bg_label = tk.StringVar(value=f"{text_bg_var.get()}%")
    top_above_label = tk.StringVar(value=f"{top_above_var.get()}%")
    top_below_label = tk.StringVar(value=f"{top_below_var.get()}%")
    bottom_above_label = tk.StringVar(value=f"{bottom_above_var.get()}%")
    bottom_below_label = tk.StringVar(value=f"{bottom_below_var.get()}%")

    opacity_frame = ttk.LabelFrame(
        editor_inner,
        text="Nieprzezroczystość czarnych pasów (0% = przezroczyste)",
        padding=8,
    )
    opacity_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    opacity_frame.columnconfigure(1, weight=1)
    row += 1

    def _add_opacity_row(
        grid_row: int,
        label: str,
        variable: tk.IntVar,
        label_var: tk.StringVar,
    ) -> None:
        ttk.Label(opacity_frame, text=label).grid(
            row=grid_row, column=0, sticky="w", padx=(0, 8), pady=(0, 6)
        )
        ttk.Scale(
            opacity_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=variable,
        ).grid(row=grid_row, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(opacity_frame, textvariable=label_var, width=5).grid(
            row=grid_row, column=2, sticky="e", padx=(8, 0), pady=(0, 6)
        )

    _add_opacity_row(0, "Tło tekstu:", text_bg_var, text_bg_label)
    _add_opacity_row(
        1, "Górny separator — nad kreską:", top_above_var, top_above_label
    )
    _add_opacity_row(
        2, "Górny separator — pod kreską:", top_below_var, top_below_label
    )
    _add_opacity_row(
        3, "Dolny separator — nad kreską:", bottom_above_var, bottom_above_label
    )
    _add_opacity_row(
        4, "Dolny separator — pod kreską:", bottom_below_var, bottom_below_label
    )

    def _persist_opacity(
        field_id: str,
        variable: tk.IntVar,
        label_var: tk.StringVar,
        *_args: Any,
    ) -> None:
        value = _opacity_pct(variable.get())
        label_var.set(f"{value}%")
        if callable(set_zone_value):
            set_zone_value("quote_screen", field_id, value)

    text_bg_var.trace_add(
        "write",
        lambda *_a: _persist_opacity(
            "fm_quote_text_bg_opacity", text_bg_var, text_bg_label
        ),
    )
    top_above_var.trace_add(
        "write",
        lambda *_a: _persist_opacity(
            "fm_quote_divider_top_above_opacity",
            top_above_var,
            top_above_label,
        ),
    )
    top_below_var.trace_add(
        "write",
        lambda *_a: _persist_opacity(
            "fm_quote_divider_top_below_opacity",
            top_below_var,
            top_below_label,
        ),
    )
    bottom_above_var.trace_add(
        "write",
        lambda *_a: _persist_opacity(
            "fm_quote_divider_bottom_above_opacity",
            bottom_above_var,
            bottom_above_label,
        ),
    )
    bottom_below_var.trace_add(
        "write",
        lambda *_a: _persist_opacity(
            "fm_quote_divider_bottom_below_opacity",
            bottom_below_var,
            bottom_below_label,
        ),
    )

    raw_quote_parallax = (
        get_zone_value("fm_quote_bg_parallax_enabled")
        if callable(get_zone_value)
        else True
    )
    quote_parallax_var = tk.BooleanVar(
        value=True if raw_quote_parallax in ("", None) else bool(raw_quote_parallax)
    )

    def persist_quote_parallax(*_args: Any) -> None:
        if callable(set_zone_value):
            set_zone_value(
                "quote_screen",
                "fm_quote_bg_parallax_enabled",
                bool(quote_parallax_var.get()),
            )

    ttk.Checkbutton(
        editor_inner,
        text="Paralaksa tła (mysz, desktop)",
        variable=quote_parallax_var,
        command=persist_quote_parallax,
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 4))
    row += 1

    ttk.Label(
        editor_inner,
        text=(
            "Subtelny ruch tła cytatu pod kursorem. Wyłączony na mobile "
            "i przy prefers-reduced-motion."
        ),
        wraplength=520,
        foreground="#555",
        justify="left",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
    row += 1

    quote_parallax_var.trace_add("write", persist_quote_parallax)

    def refresh_status() -> None:
        try:
            status_var.set(format_quote_bg_status(read_quote_bg_status()))
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

    def finish_ok(dest: Path) -> None:
        status = read_quote_bg_status()
        refresh_status()
        notify_assets_changed()
        dims = (
            f"{status.width}×{status.height}"
            if status.width and status.height
            else "rozmiar nieznany"
        )
        messagebox.showinfo(
            APP_TITLE,
            (
                f"Gotowe — tło cytatu:\n{dims}\n{dest}\n\n"
                "Aby opublikować, użyj przycisku wdrożenia."
            ),
            parent=host,
        )

    def add_background() -> None:
        selected = filedialog.askopenfilename(
            parent=host,
            title="Dodaj tło — Ekran cytatu",
            filetypes=(
                ("Obrazy", "*.webp *.png *.jpg *.jpeg"),
                ("WebP", "*.webp"),
                ("Wszystkie pliki", "*.*"),
            ),
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in _IMAGE_SUFFIXES:
            messagebox.showwarning(
                APP_TITLE,
                "Wybierz plik WebP, PNG lub JPG.",
                parent=host,
            )
            return
        if not messagebox.askyesno(
            APP_TITLE,
            (
                f"Podmienić tło cytatu plikiem:\n{path.name}\n\n"
                "Poprzedni plik w assets zostanie nadpisany."
            ),
            parent=host,
        ):
            return
        try:
            dest = replace_quote_bg(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            refresh_status()
            return
        finish_ok(dest)

    def remove_background() -> None:
        status = read_quote_bg_status()
        if not status.exists:
            messagebox.showinfo(
                APP_TITLE,
                "Brak tła cytatu do usunięcia.",
                parent=host,
            )
            return
        if not messagebox.askyesno(
            APP_TITLE,
            "Usunąć tło ekranu cytatu z assets?",
            parent=host,
        ):
            return
        try:
            clear_quote_bg()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            refresh_status()
            return
        refresh_status()
        notify_assets_changed()
        messagebox.showinfo(
            APP_TITLE,
            "Usunięto tło cytatu. Wdróż, aby zobaczyć zmianę na stronie.",
            parent=host,
        )

    def on_drop(event: Any) -> None:
        paths = parse_dnd_files(getattr(event, "data", "") or "")
        media = next(
            (
                path
                for path in paths
                if path.suffix.lower() in _IMAGE_SUFFIXES
            ),
            None,
        )
        if not media:
            messagebox.showwarning(
                APP_TITLE,
                "Upuść plik WebP, PNG lub JPG.",
                parent=host,
            )
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Podmienić tło cytatu plikiem:\n{media.name}?",
            parent=host,
        ):
            return
        try:
            dest = replace_quote_bg(media)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            refresh_status()
            return
        finish_ok(dest)

    buttons = ttk.Frame(editor_inner)
    buttons.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
    ttk.Button(buttons, text="Dodaj tło…", command=add_background).pack(side="left")
    ttk.Button(buttons, text="Usuń tło", command=remove_background).pack(
        side="left", padx=(8, 0)
    )
    ttk.Button(buttons, text="Odśwież", command=refresh_status).pack(
        side="left", padx=(8, 0)
    )
    row += 1

    for target in (editor_inner, status_label, buttons, opacity_frame):
        register_drop_target(target, on_drop=on_drop)
    refresh_status()
    return row


def _render_before_after_gallery_zone(
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
    """Panel zasobów galerii „Przed i po” osadzonej po tekstach Wrota."""
    del zone, config, mark_dirty
    editor_inner.columnconfigure(0, weight=1)

    ttk.Label(
        editor_inner,
        text=(
            "Galeria zachowuje wygląd wzorca preview.html, a zmiana kart jest "
            "powiązana ze scrollem strony i działa również przy cofaniu. Pionowy "
            "suwak działa myszką i dotykiem. Oryginały zostają zachowane, a do "
            "strony automatycznie powstaje lżejszy WebP o szerokości do 2200 px."
        ),
        wraplength=650,
        foreground="#444",
        justify="left",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
    row += 1

    current = 0
    if callable(get_zone_value):
        try:
            current = int(get_zone_value("before_after_count") or 0)
        except (TypeError, ValueError):
            current = 0
    count_var = tk.IntVar(value=max(0, min(BEFORE_AFTER_MAX_ITEMS, current)))
    raw_texts = (
        get_zone_value("before_after_texts_json")
        if callable(get_zone_value)
        else ""
    )
    text_values = _before_after_texts_from_json(raw_texts)
    raw_motion_blur = (
        get_zone_value("before_after_motion_blur")
        if callable(get_zone_value)
        else True
    )
    motion_blur_var = tk.BooleanVar(
        value=True if raw_motion_blur in ("", None) else bool(raw_motion_blur)
    )
    raw_film_grain = (
        get_zone_value("before_after_film_grain")
        if callable(get_zone_value)
        else True
    )
    film_grain_var = tk.BooleanVar(
        value=True if raw_film_grain in ("", None) else bool(raw_film_grain)
    )
    raw_bg_transparent = (
        get_zone_value("before_after_bg_transparent")
        if callable(get_zone_value)
        else True
    )
    bg_transparent_var = tk.BooleanVar(
        value=True if raw_bg_transparent in ("", None) else bool(raw_bg_transparent)
    )
    raw_preserve_prev_bg = (
        get_zone_value("before_after_preserve_prev_bg")
        if callable(get_zone_value)
        else True
    )
    preserve_prev_bg_var = tk.BooleanVar(
        value=True if raw_preserve_prev_bg in ("", None) else bool(raw_preserve_prev_bg)
    )

    def _opacity_pct(raw: object, default: int = 0) -> int:
        try:
            return max(0, min(100, int(raw)))
        except (TypeError, ValueError):
            return default

    radial_opacity_var = tk.IntVar(
        value=_opacity_pct(
            get_zone_value("before_after_bg_radial_opacity")
            if callable(get_zone_value)
            else 0
        )
    )
    linear_opacity_var = tk.IntVar(
        value=_opacity_pct(
            get_zone_value("before_after_bg_linear_opacity")
            if callable(get_zone_value)
            else 0
        )
    )
    radial_opacity_label = tk.StringVar(value=f"{radial_opacity_var.get()}%")
    linear_opacity_label = tk.StringVar(value=f"{linear_opacity_var.get()}%")

    count_row = ttk.Frame(editor_inner)
    count_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
    ttk.Label(count_row, text="Liczba obrazów w galerii:").pack(side="left")
    count_box = ttk.Spinbox(
        count_row,
        from_=0,
        to=BEFORE_AFTER_MAX_ITEMS,
        width=5,
        textvariable=count_var,
    )
    count_box.pack(side="left", padx=(8, 0))
    ttk.Label(
        count_row,
        text=f"  (0–{BEFORE_AFTER_MAX_ITEMS})",
        foreground="#666",
    ).pack(side="left")
    row += 1

    effects_row = ttk.Frame(editor_inner)
    effects_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
    ttk.Checkbutton(
        effects_row,
        text="Efekt smużenia podczas zmiany kart",
        variable=motion_blur_var,
    ).pack(side="left")
    ttk.Label(
        effects_row,
        text="  (wyłącza blur kart; nie zmienia kolorów obrazu „Przed”)",
        foreground="#666",
    ).pack(side="left")
    row += 1

    grain_row = ttk.Frame(editor_inner)
    grain_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
    ttk.Checkbutton(
        grain_row,
        text="Animowane filmowe ziarno",
        variable=film_grain_var,
    ).pack(side="left")
    ttk.Label(
        grain_row,
        text="  (warstwa szumu SVG na całym ekranie galerii)",
        foreground="#666",
    ).pack(side="left")
    row += 1

    bg_row = ttk.Frame(editor_inner)
    bg_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
    ttk.Checkbutton(
        bg_row,
        text="Przezroczystość tła",
        variable=bg_transparent_var,
    ).pack(side="left")
    ttk.Label(
        bg_row,
        text="  (wyłączone = klasyczne pełne tło; włączone = suwaki poniżej)",
        foreground="#666",
    ).pack(side="left")
    row += 1

    preserve_row = ttk.Frame(editor_inner)
    preserve_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
    ttk.Checkbutton(
        preserve_row,
        text="Zachowaj winietę i efekty tła z poprzedniego ekranu",
        variable=preserve_prev_bg_var,
    ).pack(side="left")
    ttk.Label(
        preserve_row,
        text="  (winieta Bottom + efekty tła spod napisów; paralaksa Bottom zostaje)",
        foreground="#666",
    ).pack(side="left")
    row += 1

    bg_sliders = ttk.Frame(editor_inner)
    bg_sliders.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    bg_sliders.columnconfigure(1, weight=1)
    row += 1

    ttk.Label(bg_sliders, text="Radialny blob:").grid(
        row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6)
    )
    ttk.Scale(
        bg_sliders,
        from_=0,
        to=100,
        orient="horizontal",
        variable=radial_opacity_var,
    ).grid(row=0, column=1, sticky="ew", pady=(0, 6))
    ttk.Label(bg_sliders, textvariable=radial_opacity_label, width=5).grid(
        row=0, column=2, sticky="e", padx=(8, 0), pady=(0, 6)
    )
    ttk.Label(bg_sliders, text="Liniowy gradient:").grid(
        row=1, column=0, sticky="w", padx=(0, 8)
    )
    ttk.Scale(
        bg_sliders,
        from_=0,
        to=100,
        orient="horizontal",
        variable=linear_opacity_var,
    ).grid(row=1, column=1, sticky="ew")
    ttk.Label(bg_sliders, textvariable=linear_opacity_label, width=5).grid(
        row=1, column=2, sticky="e", padx=(8, 0)
    )

    text_frame = ttk.LabelFrame(
        editor_inner,
        text="Wspólne napisy galerii",
        padding=8,
    )
    text_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    text_frame.columnconfigure(1, weight=1)
    row += 1

    global_text_vars: dict[str, tk.StringVar] = {}
    global_labels = (
        ("brand", "Nazwa archiwum"),
        ("scrollHint", "Podpowiedź przewijania"),
        ("beforeLabel", "Etykieta „Przed”"),
        ("afterLabel", "Etykieta „Po”"),
        ("dragHint", "Podpowiedź suwaka"),
        ("frameLabel", "Etykieta numeru karty"),
    )
    for text_row, (key, label) in enumerate(global_labels):
        ttk.Label(text_frame, text=label + ":").grid(
            row=text_row,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 5),
        )
        variable = tk.StringVar(value=str(text_values[key]))
        global_text_vars[key] = variable
        ttk.Entry(text_frame, textvariable=variable).grid(
            row=text_row,
            column=1,
            sticky="ew",
            pady=(0, 5),
        )

    items_frame = ttk.Frame(editor_inner)
    items_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
    items_frame.columnconfigure(0, weight=1)
    row += 1

    item_frames: list[ttk.Frame] = []
    status_vars: list[tuple[tk.StringVar, tk.StringVar]] = []
    slide_text_vars: list[dict[str, tk.StringVar]] = []

    def notify_assets_changed() -> None:
        try:
            host.winfo_toplevel().event_generate(
                "<<GicleeThemeAssetsChanged>>",
                when="tail",
            )
        except tk.TclError:
            pass

    def side_status(index: int, side: str) -> str:
        status = read_before_after_status(index, side)
        if not status.exists:
            return "brak pliku"
        dims = (
            f"{status.width}×{status.height}"
            if status.width and status.height
            else "rozmiar nieznany"
        )
        return f"{dims} · {status.size_bytes / 1024:.0f} KB"

    def refresh_item(index: int) -> None:
        before_var, after_var = status_vars[index - 1]
        before_var.set("Przed: " + side_status(index, "before"))
        after_var.set("Po: " + side_status(index, "after"))

    def choose_image(index: int, side: str) -> None:
        label = "Przed" if side == "before" else "Po"
        selected = filedialog.askopenfilename(
            parent=host,
            title=f"Galeria Przed i po — obraz {index:02d} / {label}",
            filetypes=(
                ("Obrazy", "*.webp *.png *.jpg *.jpeg"),
                ("WebP", "*.webp"),
                ("Wszystkie pliki", "*.*"),
            ),
        )
        if not selected:
            return
        try:
            dest = replace_before_after_image(
                Path(selected),
                index=index,
                side=side,
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return
        refresh_item(index)
        notify_assets_changed()
        messagebox.showinfo(
            APP_TITLE,
            (
                f"Gotowe — obraz {index:02d} / {label}:\n{dest}\n\n"
                "Zapisz wariant i wdroż, aby zobaczyć zmianę na stronie."
            ),
            parent=host,
        )

    for index in range(1, BEFORE_AFTER_MAX_ITEMS + 1):
        frame = ttk.LabelFrame(items_frame, text=f"Obraz {index:02d}", padding=8)
        frame.grid(row=index - 1, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(0, weight=1)
        before_var = tk.StringVar()
        after_var = tk.StringVar()
        status_vars.append((before_var, after_var))

        ttk.Label(frame, textvariable=before_var, foreground="#555").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            frame,
            text="Wgraj Przed…",
            command=lambda idx=index: choose_image(idx, "before"),
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(frame, textvariable=after_var, foreground="#555").grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        ttk.Button(
            frame,
            text="Wgraj Po…",
            command=lambda idx=index: choose_image(idx, "after"),
        ).grid(row=1, column=1, sticky="e", padx=(12, 0), pady=(5, 0))

        slide_source = text_values["slides"][index - 1]
        slide_vars = {
            "title": tk.StringVar(value=str(slide_source["title"])),
            "location": tk.StringVar(value=str(slide_source["location"])),
            "type": tk.StringVar(value=str(slide_source["type"])),
        }
        slide_text_vars.append(slide_vars)
        for offset, (key, label) in enumerate(
            (
                ("title", "Tytuł"),
                ("location", "Podpis / lokalizacja"),
                ("type", "Typ"),
            ),
            start=2,
        ):
            ttk.Label(frame, text=label + ":").grid(
                row=offset,
                column=0,
                sticky="w",
                pady=(5, 0),
            )
            ttk.Entry(frame, textvariable=slide_vars[key], width=42).grid(
                row=offset,
                column=1,
                sticky="ew",
                padx=(12, 0),
                pady=(5, 0),
            )
        item_frames.append(frame)
        refresh_item(index)

    def persist_texts(*_args: Any) -> None:
        payload = {
            key: variable.get()
            for key, variable in global_text_vars.items()
        }
        payload["slides"] = [
            {
                key: variable.get()
                for key, variable in variables.items()
            }
            for variables in slide_text_vars
        ]
        if callable(set_zone_value):
            set_zone_value(
                "before_after_gallery",
                "before_after_texts_json",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            )

    def persist_motion_blur(*_args: Any) -> None:
        if callable(set_zone_value):
            set_zone_value(
                "before_after_gallery",
                "before_after_motion_blur",
                bool(motion_blur_var.get()),
            )

    def persist_film_grain(*_args: Any) -> None:
        if callable(set_zone_value):
            set_zone_value(
                "before_after_gallery",
                "before_after_film_grain",
                bool(film_grain_var.get()),
            )

    def persist_bg_transparent(*_args: Any) -> None:
        if callable(set_zone_value):
            set_zone_value(
                "before_after_gallery",
                "before_after_bg_transparent",
                bool(bg_transparent_var.get()),
            )
        sync_bg_sliders()

    def persist_preserve_prev_bg(*_args: Any) -> None:
        if callable(set_zone_value):
            set_zone_value(
                "before_after_gallery",
                "before_after_preserve_prev_bg",
                bool(preserve_prev_bg_var.get()),
            )

    def persist_radial_opacity(*_args: Any) -> None:
        value = _opacity_pct(radial_opacity_var.get())
        radial_opacity_label.set(f"{value}%")
        if callable(set_zone_value):
            set_zone_value(
                "before_after_gallery",
                "before_after_bg_radial_opacity",
                value,
            )

    def persist_linear_opacity(*_args: Any) -> None:
        value = _opacity_pct(linear_opacity_var.get())
        linear_opacity_label.set(f"{value}%")
        if callable(set_zone_value):
            set_zone_value(
                "before_after_gallery",
                "before_after_bg_linear_opacity",
                value,
            )

    def sync_bg_sliders(*_args: Any) -> None:
        if bool(bg_transparent_var.get()):
            bg_sliders.grid()
        else:
            bg_sliders.grid_remove()

    def sync_count(*_args: Any) -> None:
        try:
            value = int(count_var.get())
        except (tk.TclError, ValueError):
            return
        value = max(0, min(BEFORE_AFTER_MAX_ITEMS, value))
        if callable(set_zone_value):
            set_zone_value("before_after_gallery", "before_after_count", value)
        for index, frame in enumerate(item_frames, start=1):
            if index <= value:
                frame.grid()
            else:
                frame.grid_remove()

    count_var.trace_add("write", sync_count)
    motion_blur_var.trace_add("write", persist_motion_blur)
    film_grain_var.trace_add("write", persist_film_grain)
    bg_transparent_var.trace_add("write", persist_bg_transparent)
    preserve_prev_bg_var.trace_add("write", persist_preserve_prev_bg)
    radial_opacity_var.trace_add("write", persist_radial_opacity)
    linear_opacity_var.trace_add("write", persist_linear_opacity)
    for variable in global_text_vars.values():
        variable.trace_add("write", persist_texts)
    for variables in slide_text_vars:
        for variable in variables.values():
            variable.trace_add("write", persist_texts)
    sync_bg_sliders()
    sync_count()
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
            "Tło ekranu cytatu oraz paralaksy po Wrotach — w sekcji listy po lewej."
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
            *quote_bg_deploy_relpaths(),
            "assets/giclee-fm-before-after.js",
            "assets/giclee-fm-before-after.css",
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
            "sections/section.liquid",
            "blocks/_media-without-appearance.liquid",
        ),
        extra_deploy_globs=(
            *active_scroll_video_frame_globs(),
            "assets/giclee-fm-before-after-*.webp",
            "assets/giclee-fm-quote-bg.webp",
        ),
        after_template_save=apply_scroll_video_selection,
        zone_content_builders={
            "scroll_story": _render_scroll_story_bg,
            "quote_screen": _render_quote_screen_zone,
            "wrota_parallax": _render_wrota_parallax_zone,
            "before_after_gallery": _render_before_after_gallery_zone,
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
