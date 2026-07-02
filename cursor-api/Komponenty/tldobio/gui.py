"""GUI: Tło do Bio — tło sekcji biografii per kolekcja."""

from __future__ import annotations

import io
import threading
import tkinter as tk
import webbrowser
from functools import lru_cache
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any
from urllib.request import urlopen

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from PIL import Image, ImageDraw, ImageFont, ImageTk

from .preview_render import (
    SITE_PREVIEW_HEIGHT,
    SITE_PREVIEW_WIDTH,
    compose_site_bio_background,
)
from .service import (
    ALLOWED_SUFFIXES,
    BIO_MENU_GRADIENT_NARROW,
    BIO_MENU_GRADIENT_NONE,
    BIO_MENU_GRADIENT_WIDE,
    BIO_MENU_GRADIENT_WIDE_BOTTOM,
    BIO_MENU_GRADIENT_WIDE_V2,
    BIO_MENU_GRADIENT_WIDE_V3,
    BIO_MENU_GRADIENT_WIDE_V3_BOTTOM,
    DEFAULT_BIO_COVER_SCALE,
    DEFAULT_BIO_MENU_GRADIENT,
    DEFAULT_BIO_OVERLAY_PCT,
    DEFAULT_BIO_POS_X,
    DEFAULT_BIO_RADIAL_MASK,
    clear_bio_background,
    is_allowed_image,
    load_cached_collection_rows,
    load_collections_with_backgrounds,
    normalize_bio_cover_scale,
    normalize_bio_menu_gradient,
    normalize_bio_overlay_pct,
    normalize_bio_pos_x,
    normalize_bio_radial_mask,
    radial_mask_inner_stop,
    save_bio_background_display_settings,
    upload_bio_background,
)

_MENU_GRADIENT_LABELS = {
    BIO_MENU_GRADIENT_NONE: "Bez gradientu",
    BIO_MENU_GRADIENT_NARROW: "Gradient wąski",
    BIO_MENU_GRADIENT_WIDE: "Gradient szeroki",
    BIO_MENU_GRADIENT_WIDE_BOTTOM: "Gradient szeroki + dół",
    BIO_MENU_GRADIENT_WIDE_V2: "Gradient szeroki v2",
    BIO_MENU_GRADIENT_WIDE_V3: "Gradient szeroki v3",
    BIO_MENU_GRADIENT_WIDE_V3_BOTTOM: "Gradient szeroki v3 + dół",
}

APP_TITLE = "Tło do Bio — sekcja biografii autora"
_IMAGE_SUFFIXES = ALLOWED_SUFFIXES
_PREVIEW_BG = "#1a1a1a"
_PREVIEW_BG_ACTIVE = "#2a2848"
_PREVIEW_BG_NOSEL = "#3a2a2a"
_PREVIEW_W = SITE_PREVIEW_WIDTH
_PREVIEW_H = SITE_PREVIEW_HEIGHT


@lru_cache(maxsize=1)
def _preview_fonts() -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    try:
        return (
            ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 19),
            ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 10),
        )
    except OSError:
        try:
            return (
                ImageFont.truetype("arialbd.ttf", 18),
                ImageFont.truetype("arial.ttf", 10),
            )
        except OSError:
            default = ImageFont.load_default()
            return default, default


def _draw_radial_mask_guides(
    canvas: tk.Canvas,
    mask: dict[str, Any],
    *,
    box_w: int,
    box_h: int,
) -> None:
    mask = normalize_bio_radial_mask(mask)
    if not mask.get("enabled"):
        return
    cx = mask["cx"] / 100.0 * box_w
    cy = mask["cy"] / 100.0 * box_h
    rx = mask["rx"] / 100.0 * box_w
    ry = mask["ry"] / 100.0 * box_h
    inner = radial_mask_inner_stop(mask["feather"]) / 100.0
    canvas.create_oval(
        cx - rx,
        cy - ry,
        cx + rx,
        cy + ry,
        outline="#ffffff",
        width=1,
        dash=(5, 4),
    )
    canvas.create_oval(
        cx - rx * inner,
        cy - ry * inner,
        cx + rx * inner,
        cy + ry * inner,
        outline="#ffffffaa",
        width=1,
        dash=(3, 3),
    )
    canvas.create_line(cx - 8, cy, cx + 8, cy, fill="#ffffff", width=1)
    canvas.create_line(cx, cy - 8, cx, cy + 8, fill="#ffffff", width=1)


def _wrap_text_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    *,
    max_lines: int = 5,
) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    lines: list[str] = []
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
        if len(lines) >= max_lines:
            break
    if line and len(lines) < max_lines:
        lines.append(line)
    if len(lines) == max_lines and len(words) > len(" ".join(lines).split()):
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = (last + "…") if last else "…"
    return lines


def _draw_shadow_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    *,
    fill: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> None:
    x, y = xy
    for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1)):
        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 170))
    draw.text(xy, text, font=font, fill=fill)


def _compose_bio_preview(
    img: Image.Image,
    box_w: int,
    box_h: int,
    pos_x: int,
    *,
    title: str = "",
    bio_text: str = "",
    show_text: bool = True,
    overlay_pct: int = DEFAULT_BIO_OVERLAY_PCT,
    cover_scale: bool = DEFAULT_BIO_COVER_SCALE,
    radial_mask: dict[str, Any] | None = None,
    menu_gradient: str = DEFAULT_BIO_MENU_GRADIENT,
) -> Image.Image:
    from .service import normalize_bio_overlay_pct, normalize_bio_pos_x

    composed = compose_site_bio_background(
        img,
        box_w,
        box_h,
        normalize_bio_pos_x(pos_x),
        overlay_pct=normalize_bio_overlay_pct(overlay_pct),
        cover_scale=cover_scale,
        radial_mask=radial_mask,
        menu_gradient=menu_gradient,
    )
    if not show_text:
        return composed.convert("RGB")
    draw = ImageDraw.Draw(composed)
    font_title, font_body = _preview_fonts()
    pad_x, pad_y = 16, 14
    max_text_w = box_w - pad_x * 2
    y = pad_y
    title = (title or "").strip()
    if title:
        _draw_shadow_text(draw, (pad_x, y), title, font_title)
        y += 28
    bio_text = (bio_text or "").strip()
    if bio_text:
        for line in _wrap_text_lines(draw, bio_text, font_body, max_text_w, max_lines=6):
            draw.text((pad_x, y), line, font=font_body, fill=(240, 240, 240, 235))
            y += 14
    elif not title:
        draw.text(
            (pad_x, pad_y),
            "Brak opisu kolekcji w Shopify",
            font=font_body,
            fill=(200, 200, 200, 220),
        )
    return composed.convert("RGB")


def _parse_dnd_files(data: str) -> list[Path]:
    out: list[Path] = []
    buf = ""
    in_brace = False
    for ch in data:
        if ch == "{":
            in_brace = True
            buf = ""
        elif ch == "}":
            in_brace = False
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        elif ch == " " and not in_brace:
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(Path(buf.strip()))
    return out


def main() -> None:
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1180, 960)
    root.minsize(920, 780)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Tk) -> None:
    state: dict[str, Any] = {
        "rows": [],
        "selected": None,
        "_thumb_ref": None,
        "_preview_source": None,
        "_preview_url": "",
        "_pos_saved": DEFAULT_BIO_POS_X,
        "_overlay_saved": DEFAULT_BIO_OVERLAY_PCT,
        "_overlay_pct_stash": DEFAULT_BIO_OVERLAY_PCT,
        "_cover_scale_saved": DEFAULT_BIO_COVER_SCALE,
        "_radial_saved": dict(DEFAULT_BIO_RADIAL_MASK),
        "_menu_gradient_saved": DEFAULT_BIO_MENU_GRADIENT,
        "_preview_title": "",
        "_preview_bio": "",
        "_drag_x": None,
    }

    intro = ttk.Frame(host, padding=(14, 12))
    intro.pack(fill="x")
    ttk.Label(
        intro,
        text="Wgraj tło sekcji BIO dla wybranej kolekcji autora.",
        font=("", 10, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        intro,
        text=(
            "Obraz trafia do Shopify Files; URL zapisuje się w metafield "
            "custom.bio_background_url kolekcji (storefront PUBLIC_READ). "
            "Motyw pokazuje tło na stronie kolekcji i przy przełączaniu autorów w karuzeli. "
            "Suwakiem lub przeciągnięciem podglądu dopasuj kadr poziomy. "
            "Podgląd ma proporcje sekcji BIO na desktopie i ten sam compositing overlay co strona (CSS)."
        ),
        wraplength=920,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 0))

    body = ttk.Panedwindow(host, orient="horizontal")
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    left = ttk.LabelFrame(body, text="Kolekcje", padding=(8, 8))
    right = ttk.LabelFrame(body, text="Podgląd i upload", padding=(10, 10))
    body.add(left, weight=3)
    body.add(right, weight=2)

    filter_var = tk.StringVar(value="")
    only_with_var = tk.BooleanVar(value=False)
    only_missing_var = tk.BooleanVar(value=False)
    progress_var = tk.StringVar(value="Ładowanie kolekcji z Shopify...")
    count_var = tk.StringVar(value="")
    selected_title_var = tk.StringVar(value="(wybierz kolekcję)")
    selected_handle_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="")

    filter_bar = ttk.Frame(left)
    filter_bar.pack(fill="x", pady=(0, 6))
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=28).pack(side="left", padx=(6, 8))
    ttk.Checkbutton(filter_bar, text="Tylko z tłem", variable=only_with_var).pack(side="left", padx=4)
    ttk.Checkbutton(filter_bar, text="Tylko bez tła", variable=only_missing_var).pack(side="left", padx=4)
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="right")

    table_frame = ttk.Frame(left)
    table_frame.pack(fill="both", expand=True)
    cols = ("title", "handle", "status")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16, selectmode="browse")
    tree.heading("title", text="Kolekcja")
    tree.heading("handle", text="Handle")
    tree.heading("status", text="Tło")
    tree.column("title", width=280, anchor="w", stretch=True)
    tree.column("handle", width=180, anchor="w")
    tree.column("status", width=56, anchor="center")
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    ttk.Label(left, textvariable=progress_var, foreground="#666").pack(anchor="w", pady=(6, 0))

    ttk.Label(right, textvariable=selected_title_var, font=("", 11, "bold"), wraplength=360).pack(
        anchor="w"
    )
    ttk.Label(right, textvariable=selected_handle_var, foreground="#555").pack(anchor="w", pady=(2, 8))

    drop_hint = (
        "Przeciągnij grafikę tutaj\n(JPG, PNG, WEBP)"
        if _HAS_DND
        else "Brak podglądu\n(drag-and-drop: pip install tkinterdnd2)"
    )

    preview_frame = tk.Frame(right, bg=_PREVIEW_BG, width=_PREVIEW_W, height=_PREVIEW_H)
    preview_frame.pack(fill="x", pady=(0, 4))
    preview_frame.pack_propagate(False)
    preview_canvas = tk.Canvas(
        preview_frame,
        width=_PREVIEW_W,
        height=_PREVIEW_H,
        bg=_PREVIEW_BG,
        highlightthickness=0,
        cursor="hand2",
    )
    preview_canvas.pack(fill="both", expand=True)

    pos_frame = ttk.Frame(right)
    pos_frame.pack(fill="x", pady=(0, 8))
    pos_var = tk.IntVar(value=DEFAULT_BIO_POS_X)
    pos_saved_var = tk.StringVar(value="")
    show_text_var = tk.BooleanVar(value=True)
    ttk.Label(pos_frame, text="Kadr poziomy:").pack(anchor="w")
    pos_controls = ttk.Frame(pos_frame)
    pos_controls.pack(fill="x", pady=(4, 0))
    nudge_left_btn = ttk.Button(pos_controls, text="←", width=3, state="disabled")
    nudge_left_btn.pack(side="left")
    pos_scale = ttk.Scale(
        pos_controls,
        from_=0,
        to=100,
        orient="horizontal",
        variable=pos_var,
        state="disabled",
    )
    pos_scale.pack(side="left", fill="x", expand=True, padx=6)
    nudge_right_btn = ttk.Button(pos_controls, text="→", width=3, state="disabled")
    nudge_right_btn.pack(side="left")
    pos_meta = ttk.Frame(pos_frame)
    pos_meta.pack(fill="x", pady=(4, 0))
    ttk.Label(pos_meta, textvariable=pos_saved_var, foreground="#666").pack(side="left")
    save_settings_btn = ttk.Button(pos_meta, text="Zapisz ustawienia tła", state="disabled")
    save_settings_btn.pack(side="right")
    ttk.Checkbutton(
        pos_frame,
        text="Podgląd z tekstem BIO (jak na stronie)",
        variable=show_text_var,
    ).pack(anchor="w", pady=(6, 0))

    overlay_frame = ttk.Frame(right)
    overlay_frame.pack(fill="x", pady=(0, 8))
    overlay_off_var = tk.BooleanVar(value=False)
    overlay_pct_var = tk.IntVar(value=DEFAULT_BIO_OVERLAY_PCT)
    overlay_saved_var = tk.StringVar(value="")
    ttk.Label(overlay_frame, text="Przyciemnienie (gradient):").pack(anchor="w")
    overlay_controls = ttk.Frame(overlay_frame)
    overlay_controls.pack(fill="x", pady=(4, 0))
    overlay_scale = ttk.Scale(
        overlay_controls,
        from_=0,
        to=100,
        orient="horizontal",
        variable=overlay_pct_var,
        state="disabled",
    )
    overlay_scale.pack(side="left", fill="x", expand=True)
    ttk.Label(overlay_controls, textvariable=overlay_saved_var, width=5).pack(side="left", padx=(6, 0))
    overlay_off_check = ttk.Checkbutton(
        overlay_frame,
        text="Wyłącz przyciemnienie",
        variable=overlay_off_var,
    )
    overlay_off_check.pack(anchor="w", pady=(6, 0))

    cover_scale_var = tk.BooleanVar(value=DEFAULT_BIO_COVER_SCALE)
    cover_scale_check = ttk.Checkbutton(
        overlay_frame,
        text="Lekkie powiększenie kadru (scale 1.04)",
        variable=cover_scale_var,
    )
    cover_scale_check.pack(anchor="w", pady=(6, 0))

    gradient_frame = ttk.Frame(right)
    gradient_frame.pack(fill="x", pady=(0, 8))
    menu_gradient_var = tk.StringVar(value=_MENU_GRADIENT_LABELS[DEFAULT_BIO_MENU_GRADIENT])
    ttk.Label(gradient_frame, text="Gradient u góry (pod menu):").pack(anchor="w")
    gradient_row = ttk.Frame(gradient_frame)
    gradient_row.pack(fill="x", pady=(4, 0))
    gradient_btn = ttk.Button(gradient_row, text="Gradient", state="disabled")
    gradient_btn.pack(side="left")
    ttk.Label(gradient_row, textvariable=menu_gradient_var, foreground="#666").pack(
        side="left", padx=(8, 0)
    )

    radial_frame = ttk.LabelFrame(right, text="Maska radialna (ekspozycja)", padding=(8, 6))
    radial_frame.pack(fill="x", pady=(0, 8))
    radial_enabled_var = tk.BooleanVar(value=False)
    radial_cx_var = tk.IntVar(value=DEFAULT_BIO_RADIAL_MASK["cx"])
    radial_cy_var = tk.IntVar(value=DEFAULT_BIO_RADIAL_MASK["cy"])
    radial_rx_var = tk.IntVar(value=DEFAULT_BIO_RADIAL_MASK["rx"])
    radial_ry_var = tk.IntVar(value=DEFAULT_BIO_RADIAL_MASK["ry"])
    radial_feather_var = tk.IntVar(value=DEFAULT_BIO_RADIAL_MASK["feather"])
    radial_exposure_var = tk.IntVar(value=DEFAULT_BIO_RADIAL_MASK["exposure"])
    radial_hint_var = tk.StringVar(value="Podwójne kliknięcie podglądu ustawia środek maski.")

    radial_controls: list[ttk.Scale] = []

    def _add_radial_scale(parent: ttk.Frame, label: str, var: tk.IntVar, from_: int, to: int) -> ttk.Scale:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(2, 0))
        ttk.Label(row, text=label, width=14).pack(side="left")
        scale = ttk.Scale(row, from_=from_, to=to, orient="horizontal", variable=var, state="disabled")
        scale.pack(side="left", fill="x", expand=True, padx=(4, 6))
        ttk.Label(row, textvariable=var, width=4).pack(side="left")
        radial_controls.append(scale)
        return scale

    radial_enable_check = ttk.Checkbutton(
        radial_frame,
        text="Włącz maskę radialną (obok gradientu pod tekst)",
        variable=radial_enabled_var,
    )
    radial_enable_check.pack(anchor="w")
    _add_radial_scale(radial_frame, "Środek X:", radial_cx_var, 0, 100)
    _add_radial_scale(radial_frame, "Środek Y:", radial_cy_var, 0, 100)
    _add_radial_scale(radial_frame, "Szerokość:", radial_rx_var, 10, 150)
    _add_radial_scale(radial_frame, "Wysokość:", radial_ry_var, 10, 150)
    _add_radial_scale(radial_frame, "Wtapianie:", radial_feather_var, 0, 100)
    _add_radial_scale(radial_frame, "Ekspozycja:", radial_exposure_var, 0, 100)
    ttk.Label(radial_frame, textvariable=radial_hint_var, foreground="#666", wraplength=340).pack(
        anchor="w", pady=(4, 0)
    )

    ttk.Label(right, textvariable=status_var, wraplength=360).pack(anchor="w", pady=(0, 8))

    btn_row = ttk.Frame(right)
    btn_row.pack(fill="x", pady=(4, 0))
    upload_btn = ttk.Button(btn_row, text="Wgraj tło…", state="disabled")
    upload_btn.pack(side="left", padx=(0, 6))
    remove_btn = ttk.Button(btn_row, text="Usuń tło", state="disabled")
    remove_btn.pack(side="left", padx=(0, 6))
    open_btn = ttk.Button(btn_row, text="Otwórz kolekcję", state="disabled")
    open_btn.pack(side="left")

    row_by_iid: dict[str, dict[str, Any]] = {}

    def _filtered_rows() -> list[dict[str, Any]]:
        q = (filter_var.get() or "").strip().lower()
        only_with = bool(only_with_var.get())
        only_missing = bool(only_missing_var.get())
        rows = list(state["rows"])
        out: list[dict[str, Any]] = []
        for r in rows:
            if only_with and not r.get("has_background"):
                continue
            if only_missing and r.get("has_background"):
                continue
            if q:
                blob = f"{r.get('title', '')} {r.get('handle', '')}".lower()
                if q not in blob:
                    continue
            out.append(r)
        return out

    def _refresh_tree(*, keep_handle: str | None = None) -> None:
        tree.delete(*tree.get_children())
        row_by_iid.clear()
        visible = _filtered_rows()
        count_var.set(f"{len(visible)} / {len(state['rows'])}")
        select_iid = None
        for r in visible:
            iid = tree.insert(
                "",
                "end",
                values=(r.get("title") or "", r.get("handle") or "", r.get("status") or "—"),
            )
            row_by_iid[iid] = r
            if keep_handle and r.get("handle") == keep_handle:
                select_iid = iid
        if select_iid:
            tree.selection_set(select_iid)
            tree.see(select_iid)
            _on_select()

    def _effective_overlay_pct() -> int:
        if overlay_off_var.get():
            return 0
        return normalize_bio_overlay_pct(overlay_pct_var.get())

    def _current_radial_mask() -> dict[str, Any]:
        return normalize_bio_radial_mask(
            {
                "enabled": bool(radial_enabled_var.get()),
                "cx": radial_cx_var.get(),
                "cy": radial_cy_var.get(),
                "rx": radial_rx_var.get(),
                "ry": radial_ry_var.get(),
                "feather": radial_feather_var.get(),
                "exposure": radial_exposure_var.get(),
            }
        )

    def _current_menu_gradient() -> str:
        return normalize_bio_menu_gradient(state.get("_menu_gradient_value", DEFAULT_BIO_MENU_GRADIENT))

    def _set_menu_gradient(value: str) -> None:
        normalized = normalize_bio_menu_gradient(value)
        state["_menu_gradient_value"] = normalized
        menu_gradient_var.set(_MENU_GRADIENT_LABELS.get(normalized, normalized))
        _on_pos_change()

    def _apply_menu_gradient_vars(value: str | None) -> None:
        normalized = normalize_bio_menu_gradient(value)
        state["_menu_gradient_value"] = normalized
        menu_gradient_var.set(_MENU_GRADIENT_LABELS.get(normalized, normalized))

    def _apply_radial_vars(mask: dict[str, Any] | None) -> None:
        mask = normalize_bio_radial_mask(mask)
        radial_enabled_var.set(bool(mask.get("enabled")))
        radial_cx_var.set(mask["cx"])
        radial_cy_var.set(mask["cy"])
        radial_rx_var.set(mask["rx"])
        radial_ry_var.set(mask["ry"])
        radial_feather_var.set(mask["feather"])
        radial_exposure_var.set(mask["exposure"])

    def _radial_masks_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
        return normalize_bio_radial_mask(a) == normalize_bio_radial_mask(b)

    def _set_radial_controls(enabled: bool) -> None:
        radial_state = "normal" if enabled and bool(radial_enabled_var.get()) else "disabled"
        for scale in radial_controls:
            scale.configure(state=radial_state)
        radial_enable_check.configure(state="normal" if enabled else "disabled")

    def _update_settings_label() -> None:
        pos = normalize_bio_pos_x(pos_var.get())
        saved_pos = normalize_bio_pos_x(state.get("_pos_saved", DEFAULT_BIO_POS_X))
        overlay = _effective_overlay_pct()
        saved_overlay = normalize_bio_overlay_pct(state.get("_overlay_saved", DEFAULT_BIO_OVERLAY_PCT))
        cover_scale = normalize_bio_cover_scale(cover_scale_var.get())
        saved_cover_scale = normalize_bio_cover_scale(
            state.get("_cover_scale_saved", DEFAULT_BIO_COVER_SCALE)
        )
        radial = _current_radial_mask()
        saved_radial = normalize_bio_radial_mask(state.get("_radial_saved", DEFAULT_BIO_RADIAL_MASK))
        menu_gradient = _current_menu_gradient()
        saved_menu_gradient = normalize_bio_menu_gradient(
            state.get("_menu_gradient_saved", DEFAULT_BIO_MENU_GRADIENT)
        )
        pos_dirty = pos != saved_pos
        overlay_dirty = overlay != saved_overlay
        cover_scale_dirty = cover_scale != saved_cover_scale
        radial_dirty = not _radial_masks_equal(radial, saved_radial)
        menu_gradient_dirty = menu_gradient != saved_menu_gradient
        if pos_dirty or overlay_dirty or cover_scale_dirty or radial_dirty or menu_gradient_dirty:
            pos_saved_var.set("Niezapisane zmiany ustawień tła")
        else:
            pos_saved_var.set("Ustawienia zapisane")
        if overlay <= 0:
            overlay_saved_var.set("0%")
        else:
            overlay_saved_var.set(f"{overlay}%")

    def _render_preview() -> None:
        preview_canvas.delete("all")
        src = state.get("_preview_source")
        if src is None:
            preview_canvas.configure(bg=_PREVIEW_BG, cursor="")
            preview_canvas.create_text(
                _PREVIEW_W // 2,
                _PREVIEW_H // 2,
                text=drop_hint,
                fill="#888",
                justify="center",
                width=_PREVIEW_W - 24,
            )
            return
        preview_canvas.configure(bg=_PREVIEW_BG, cursor="hand2")
        pos = normalize_bio_pos_x(pos_var.get())
        cropped = _compose_bio_preview(
            src,
            _PREVIEW_W,
            _PREVIEW_H,
            pos,
            title=str(state.get("_preview_title") or ""),
            bio_text=str(state.get("_preview_bio") or ""),
            show_text=bool(show_text_var.get()),
            overlay_pct=_effective_overlay_pct(),
            cover_scale=bool(cover_scale_var.get()),
            radial_mask=_current_radial_mask(),
            menu_gradient=_current_menu_gradient(),
        )
        photo = ImageTk.PhotoImage(cropped)
        state["_thumb_ref"] = photo
        preview_canvas.create_image(0, 0, anchor="nw", image=photo)
        _draw_radial_mask_guides(
            preview_canvas,
            _current_radial_mask(),
            box_w=_PREVIEW_W,
            box_h=_PREVIEW_H,
        )
        _update_settings_label()

    def _set_position_controls(enabled: bool) -> None:
        state_ctrl = "normal" if enabled else "disabled"
        pos_scale.configure(state=state_ctrl)
        nudge_left_btn.configure(state=state_ctrl)
        nudge_right_btn.configure(state=state_ctrl)
        overlay_scale.configure(state="disabled" if not enabled or overlay_off_var.get() else "normal")
        save_settings_btn.configure(state=state_ctrl)
        gradient_btn.configure(state=state_ctrl)
        _set_radial_controls(enabled)

    def _load_preview_from_url(
        url: str,
        *,
        pos_x: int,
        overlay_pct: int,
        cover_scale: bool = DEFAULT_BIO_COVER_SCALE,
        radial_mask: dict[str, Any] | None = None,
        menu_gradient: str = DEFAULT_BIO_MENU_GRADIENT,
    ) -> None:
        state["_preview_source"] = None
        state["_preview_url"] = url
        pos_var.set(normalize_bio_pos_x(pos_x))
        state["_pos_saved"] = normalize_bio_pos_x(pos_x)
        overlay = normalize_bio_overlay_pct(overlay_pct)
        state["_overlay_saved"] = overlay
        stash = overlay if overlay > 0 else DEFAULT_BIO_OVERLAY_PCT
        state["_overlay_pct_stash"] = stash
        overlay_pct_var.set(overlay if overlay > 0 else stash)
        overlay_off_var.set(overlay <= 0)
        scale = normalize_bio_cover_scale(cover_scale)
        state["_cover_scale_saved"] = scale
        cover_scale_var.set(scale)
        radial = normalize_bio_radial_mask(radial_mask)
        state["_radial_saved"] = radial
        _apply_radial_vars(radial)
        _apply_menu_gradient_vars(menu_gradient)
        state["_menu_gradient_saved"] = normalize_bio_menu_gradient(menu_gradient)
        try:
            with urlopen(url, timeout=20) as resp:
                raw = resp.read()
            img = Image.open(io.BytesIO(raw))
            img.load()
            if img.width > 1920:
                ratio = 1920 / img.width
                img = img.resize(
                    (1920, max(1, int(round(img.height * ratio)))),
                    Image.Resampling.LANCZOS,
                )
            state["_preview_source"] = img
            _render_preview()
        except OSError as exc:
            state["_preview_source"] = None
            preview_canvas.delete("all")
            preview_canvas.create_text(
                _PREVIEW_W // 2,
                _PREVIEW_H // 2,
                text=f"Podgląd niedostępny\n{exc}",
                fill="#888",
                justify="center",
                width=_PREVIEW_W - 24,
            )

    def _set_preview(
        url: str | None,
        *,
        pos_x: int = DEFAULT_BIO_POS_X,
        overlay_pct: int = DEFAULT_BIO_OVERLAY_PCT,
        cover_scale: bool = DEFAULT_BIO_COVER_SCALE,
        radial_mask: dict[str, Any] | None = None,
        menu_gradient: str = DEFAULT_BIO_MENU_GRADIENT,
    ) -> None:
        state["_thumb_ref"] = None
        if not url:
            state["_preview_source"] = None
            state["_preview_url"] = ""
            pos_var.set(DEFAULT_BIO_POS_X)
            state["_pos_saved"] = DEFAULT_BIO_POS_X
            overlay_pct_var.set(DEFAULT_BIO_OVERLAY_PCT)
            state["_overlay_saved"] = DEFAULT_BIO_OVERLAY_PCT
            overlay_off_var.set(False)
            cover_scale_var.set(DEFAULT_BIO_COVER_SCALE)
            state["_cover_scale_saved"] = DEFAULT_BIO_COVER_SCALE
            state["_radial_saved"] = dict(DEFAULT_BIO_RADIAL_MASK)
            _apply_radial_vars(DEFAULT_BIO_RADIAL_MASK)
            _apply_menu_gradient_vars(DEFAULT_BIO_MENU_GRADIENT)
            state["_menu_gradient_saved"] = DEFAULT_BIO_MENU_GRADIENT
            _set_position_controls(False)
            _render_preview()
            return
        _set_position_controls(True)
        _load_preview_from_url(
            url,
            pos_x=pos_x,
            overlay_pct=overlay_pct,
            cover_scale=cover_scale,
            radial_mask=radial_mask,
            menu_gradient=menu_gradient,
        )

    def _set_buttons(enabled: bool, *, has_bg: bool = False) -> None:
        upload_btn.configure(state="normal" if enabled else "disabled")
        remove_btn.configure(state="normal" if enabled and has_bg else "disabled")
        open_btn.configure(state="normal" if enabled else "disabled")
        _set_position_controls(enabled and has_bg)

    def _on_select(_evt=None) -> None:
        sel = tree.selection()
        if not sel:
            state["selected"] = None
            state["_preview_title"] = ""
            state["_preview_bio"] = ""
            selected_title_var.set("(wybierz kolekcję)")
            selected_handle_var.set("")
            status_var.set("")
            _set_preview(None)
            _set_buttons(False)
            return
        row = row_by_iid.get(sel[0])
        state["selected"] = row
        if not row:
            return
        state["_preview_title"] = str(row.get("title") or "")
        state["_preview_bio"] = str(row.get("bio_preview") or "")
        selected_title_var.set(row.get("title") or row.get("handle") or "")
        selected_handle_var.set(f"Handle: {row.get('handle') or '—'}")
        url = str(row.get("background_url") or "").strip()
        pos_x = normalize_bio_pos_x(row.get("background_pos_x"))
        overlay_pct = normalize_bio_overlay_pct(row.get("background_overlay_pct"))
        cover_scale = normalize_bio_cover_scale(row.get("background_cover_scale"))
        radial_mask = normalize_bio_radial_mask(row.get("background_radial_mask"))
        menu_gradient = normalize_bio_menu_gradient(row.get("background_menu_gradient"))
        if url:
            status_var.set("Tło przypisane do tej kolekcji.")
            _set_preview(
                url,
                pos_x=pos_x,
                overlay_pct=overlay_pct,
                cover_scale=cover_scale,
                radial_mask=radial_mask,
                menu_gradient=menu_gradient,
            )
        else:
            status_var.set("Brak tła — sekcja BIO użyje domyślnego tła z motywu.")
            _set_preview(None)
        _set_buttons(True, has_bg=bool(url))

    tree.bind("<<TreeviewSelect>>", _on_select)

    def _reload_async(*, keep_handle: str | None = None) -> None:
        cached = load_cached_collection_rows()
        if cached:
            state["rows"] = cached
            _refresh_tree(keep_handle=keep_handle)
            progress_var.set(f"Cache: {len(cached)} kolekcji — odświeżam z Shopify…")
        else:
            progress_var.set("Pobieram kolekcje i metafieldy…")

        def worker() -> None:
            try:

                def on_progress(msg: str) -> None:
                    host.after(0, lambda m=msg: progress_var.set(m))

                rows = load_collections_with_backgrounds(on_progress=on_progress)

                def done() -> None:
                    state["rows"] = rows
                    progress_var.set(f"Załadowano {len(rows)} kolekcji.")
                    _refresh_tree(keep_handle=keep_handle)

                host.after(0, done)
            except Exception as exc:
                host.after(
                    0,
                    lambda: (
                        progress_var.set("Błąd ładowania."),
                        messagebox.showerror(APP_TITLE, str(exc)),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _upload_from_path(path: Path) -> None:
        row = state.get("selected")
        if not row:
            messagebox.showinfo(APP_TITLE, "Najpierw wybierz kolekcję z listy.")
            return
        if not is_allowed_image(path):
            messagebox.showwarning(
                APP_TITLE,
                "Dozwolone formaty: JPG, JPEG, PNG, WEBP.",
            )
            return
        handle = str(row.get("handle") or "")
        pos_x = normalize_bio_pos_x(pos_var.get())
        overlay_pct = _effective_overlay_pct()
        cover_scale = normalize_bio_cover_scale(cover_scale_var.get())
        radial_mask = _current_radial_mask()
        menu_gradient = _current_menu_gradient()
        upload_btn.configure(state="disabled")
        progress_var.set(f"Upload: {path.name}…")

        def worker() -> None:
            result = upload_bio_background(
                int(row.get("id") or 0),
                handle,
                str(row.get("title") or ""),
                path,
                pos_x=pos_x,
                overlay_pct=overlay_pct,
                cover_scale=cover_scale,
                radial_mask=radial_mask,
                menu_gradient=menu_gradient,
            )

            def done() -> None:
                upload_btn.configure(state="normal")
                if not result.get("ok"):
                    progress_var.set("Błąd uploadu.")
                    messagebox.showerror(APP_TITLE, result.get("error") or "Nieznany błąd.")
                    return
                url = str(result.get("url") or "")
                saved_pos = normalize_bio_pos_x(result.get("background_pos_x", pos_x))
                saved_overlay = normalize_bio_overlay_pct(
                    result.get("background_overlay_pct", overlay_pct)
                )
                saved_cover_scale = normalize_bio_cover_scale(
                    result.get("background_cover_scale", cover_scale)
                )
                saved_radial = normalize_bio_radial_mask(
                    result.get("background_radial_mask", radial_mask)
                )
                saved_menu_gradient = normalize_bio_menu_gradient(
                    result.get("background_menu_gradient", menu_gradient)
                )
                for r in state["rows"]:
                    if r.get("handle") == handle:
                        r["background_url"] = url
                        r["background_pos_x"] = saved_pos
                        r["background_overlay_pct"] = saved_overlay
                        r["background_cover_scale"] = saved_cover_scale
                        r["background_radial_mask"] = saved_radial
                        r["background_menu_gradient"] = saved_menu_gradient
                        r["has_background"] = True
                        r["status"] = "tak"
                        break
                state["_pos_saved"] = saved_pos
                state["_overlay_saved"] = saved_overlay
                state["_cover_scale_saved"] = saved_cover_scale
                state["_radial_saved"] = saved_radial
                state["_menu_gradient_saved"] = saved_menu_gradient
                _apply_menu_gradient_vars(saved_menu_gradient)
                progress_var.set(f"Zapisano tło dla {handle}.")
                show_toast(host, "Tło BIO zapisane.")
                warn = str(result.get("warn_sharpness") or "").strip()
                if warn:
                    show_toast(host, warn, duration_ms=6500)
                if result.get("resized_for_shopify"):
                    show_toast(
                        host,
                        "Plik był większy niż limit Shopify (4472 px) — zmniejszono przed wysłaniem.",
                        duration_ms=6500,
                    )
                _refresh_tree(keep_handle=handle)

            host.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _pick_and_upload() -> None:
        path_str = filedialog.askopenfilename(
            title="Wybierz obraz tła BIO",
            filetypes=[
                ("Obrazy", "*.jpg;*.jpeg;*.png;*.webp"),
                ("Wszystkie", "*.*"),
            ],
        )
        if not path_str:
            return
        _upload_from_path(Path(path_str))

    def _on_preview_drop(event: tk.Event) -> None:  # type: ignore[type-arg]
        _reset_preview_drop_style()
        data = getattr(event, "data", "") or ""
        paths = _parse_dnd_files(data)
        images = [p for p in paths if p.is_file() and is_allowed_image(p)]
        if not images:
            messagebox.showwarning(APP_TITLE, "Upuść plik graficzny (JPG, JPEG, PNG, WEBP).")
            return
        if not state.get("selected"):
            messagebox.showinfo(APP_TITLE, "Najpierw wybierz kolekcję z listy.")
            return
        if len(images) > 1:
            show_toast(host, f"Wgrywam pierwszy z {len(images)} plików.", duration_ms=2000)
        _upload_from_path(images[0])

    def _reset_preview_drop_style() -> None:
        if state.get("_preview_source"):
            preview_canvas.configure(bg=_PREVIEW_BG, cursor="hand2")
        else:
            preview_canvas.configure(bg=_PREVIEW_BG, cursor="")

    def _on_preview_drag_enter(_event: tk.Event) -> None:  # type: ignore[type-arg]
        if state.get("selected"):
            preview_canvas.configure(bg=_PREVIEW_BG_ACTIVE, cursor="hand2")
        else:
            preview_canvas.configure(bg=_PREVIEW_BG_NOSEL, cursor="no")

    def _on_preview_drag_leave(_event: tk.Event) -> None:  # type: ignore[type-arg]
        _reset_preview_drop_style()

    def _on_pos_change(*_args: object) -> None:
        if state.get("_preview_source") is not None:
            _render_preview()

    def _nudge_pos(delta: int) -> None:
        pos_var.set(normalize_bio_pos_x(int(pos_var.get()) + delta))
        _on_pos_change()

    def _save_settings() -> None:
        row = state.get("selected")
        if not row or not row.get("has_background"):
            return
        handle = str(row.get("handle") or "")
        pos_x = normalize_bio_pos_x(pos_var.get())
        overlay_pct = _effective_overlay_pct()
        cover_scale = normalize_bio_cover_scale(cover_scale_var.get())
        radial_mask = _current_radial_mask()
        menu_gradient = _current_menu_gradient()
        save_settings_btn.configure(state="disabled")
        progress_var.set(f"Zapisuję ustawienia tła: {handle}…")

        def worker() -> None:
            result = save_bio_background_display_settings(
                int(row.get("id") or 0),
                handle,
                pos_x=pos_x,
                overlay_pct=overlay_pct,
                cover_scale=cover_scale,
                radial_mask=radial_mask,
                menu_gradient=menu_gradient,
            )

            def done() -> None:
                save_settings_btn.configure(state="normal")
                if not result.get("ok"):
                    progress_var.set("Błąd zapisu ustawień.")
                    messagebox.showerror(APP_TITLE, result.get("error") or "Nieznany błąd.")
                    return
                saved_pos = normalize_bio_pos_x(result.get("background_pos_x", pos_x))
                saved_overlay = normalize_bio_overlay_pct(
                    result.get("background_overlay_pct", overlay_pct)
                )
                saved_cover_scale = normalize_bio_cover_scale(
                    result.get("background_cover_scale", cover_scale)
                )
                saved_radial = normalize_bio_radial_mask(
                    result.get("background_radial_mask", radial_mask)
                )
                saved_menu_gradient = normalize_bio_menu_gradient(
                    result.get("background_menu_gradient", menu_gradient)
                )
                state["_pos_saved"] = saved_pos
                state["_overlay_saved"] = saved_overlay
                state["_cover_scale_saved"] = saved_cover_scale
                state["_radial_saved"] = saved_radial
                state["_menu_gradient_saved"] = saved_menu_gradient
                _apply_menu_gradient_vars(saved_menu_gradient)
                for r in state["rows"]:
                    if r.get("handle") == handle:
                        r["background_pos_x"] = saved_pos
                        r["background_overlay_pct"] = saved_overlay
                        r["background_cover_scale"] = saved_cover_scale
                        r["background_radial_mask"] = saved_radial
                        r["background_menu_gradient"] = saved_menu_gradient
                        break
                progress_var.set(f"Zapisano ustawienia tła dla {handle}.")
                show_toast(host, "Ustawienia tła zapisane.")
                _update_settings_label()

            host.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_overlay_pct_change(*_args: object) -> None:
        if not overlay_off_var.get():
            pct = normalize_bio_overlay_pct(overlay_pct_var.get())
            if pct > 0:
                state["_overlay_pct_stash"] = pct
        _on_pos_change()

    def _on_overlay_off_change() -> None:
        if overlay_off_var.get():
            stash = normalize_bio_overlay_pct(overlay_pct_var.get())
            if stash > 0:
                state["_overlay_pct_stash"] = stash
            overlay_scale.configure(state="disabled")
        else:
            overlay_scale.configure(state="normal" if state.get("selected", {}).get("has_background") else "disabled")
            overlay_pct_var.set(
                normalize_bio_overlay_pct(state.get("_overlay_pct_stash", DEFAULT_BIO_OVERLAY_PCT))
            )
        _on_pos_change()

    def _on_cover_scale_change() -> None:
        _on_pos_change()

    def _on_radial_enabled_change() -> None:
        if state.get("selected", {}).get("has_background"):
            _set_radial_controls(True)
        _on_pos_change()

    def _on_canvas_double_click(event: tk.Event) -> None:  # type: ignore[type-arg]
        if not radial_enabled_var.get() or not state.get("_preview_source"):
            return
        radial_cx_var.set(max(0, min(100, int(round(event.x / _PREVIEW_W * 100)))))
        radial_cy_var.set(max(0, min(100, int(round(event.y / _PREVIEW_H * 100)))))
        _on_pos_change()

    def _on_canvas_press(event: tk.Event) -> None:  # type: ignore[type-arg]
        if not state.get("_preview_source"):
            return
        state["_drag_x"] = event.x

    def _on_canvas_drag(event: tk.Event) -> None:  # type: ignore[type-arg]
        src = state.get("_preview_source")
        if src is None or state.get("_drag_x") is None:
            return
        dx = event.x - int(state["_drag_x"])
        state["_drag_x"] = event.x
        iw, ih = src.size
        scale = max(_PREVIEW_W / iw, _PREVIEW_H / ih)
        nw = max(1, int(round(iw * scale)))
        max_x = max(1, nw - _PREVIEW_W)
        delta_pos = -(dx / max_x) * 100.0
        pos_var.set(normalize_bio_pos_x(int(round(pos_var.get() + delta_pos))))

    def _on_canvas_release(_event: tk.Event) -> None:  # type: ignore[type-arg]
        state["_drag_x"] = None

    state["_menu_gradient_value"] = DEFAULT_BIO_MENU_GRADIENT

    gradient_menu = tk.Menu(host, tearoff=0)
    gradient_menu.add_command(
        label=_MENU_GRADIENT_LABELS[BIO_MENU_GRADIENT_NONE],
        command=lambda: _set_menu_gradient(BIO_MENU_GRADIENT_NONE),
    )
    gradient_menu.add_command(
        label=_MENU_GRADIENT_LABELS[BIO_MENU_GRADIENT_NARROW],
        command=lambda: _set_menu_gradient(BIO_MENU_GRADIENT_NARROW),
    )
    gradient_menu.add_command(
        label=_MENU_GRADIENT_LABELS[BIO_MENU_GRADIENT_WIDE],
        command=lambda: _set_menu_gradient(BIO_MENU_GRADIENT_WIDE),
    )
    gradient_menu.add_command(
        label=_MENU_GRADIENT_LABELS[BIO_MENU_GRADIENT_WIDE_BOTTOM],
        command=lambda: _set_menu_gradient(BIO_MENU_GRADIENT_WIDE_BOTTOM),
    )
    gradient_menu.add_command(
        label=_MENU_GRADIENT_LABELS[BIO_MENU_GRADIENT_WIDE_V2],
        command=lambda: _set_menu_gradient(BIO_MENU_GRADIENT_WIDE_V2),
    )
    gradient_menu.add_command(
        label=_MENU_GRADIENT_LABELS[BIO_MENU_GRADIENT_WIDE_V3],
        command=lambda: _set_menu_gradient(BIO_MENU_GRADIENT_WIDE_V3),
    )
    gradient_menu.add_command(
        label=_MENU_GRADIENT_LABELS[BIO_MENU_GRADIENT_WIDE_V3_BOTTOM],
        command=lambda: _set_menu_gradient(BIO_MENU_GRADIENT_WIDE_V3_BOTTOM),
    )

    def _open_gradient_menu() -> None:
        if not state.get("selected", {}).get("has_background"):
            return
        try:
            x = gradient_btn.winfo_rootx()
            y = gradient_btn.winfo_rooty() + gradient_btn.winfo_height()
            gradient_menu.tk_popup(x, y)
        finally:
            gradient_menu.grab_release()

    gradient_btn.configure(command=_open_gradient_menu)

    pos_var.trace_add("write", _on_pos_change)
    overlay_pct_var.trace_add("write", _on_overlay_pct_change)
    overlay_off_check.configure(command=_on_overlay_off_change)
    cover_scale_check.configure(command=_on_cover_scale_change)
    radial_enable_check.configure(command=_on_radial_enabled_change)
    for var in (
        radial_cx_var,
        radial_cy_var,
        radial_rx_var,
        radial_ry_var,
        radial_feather_var,
        radial_exposure_var,
    ):
        var.trace_add("write", _on_pos_change)
    show_text_var.trace_add("write", lambda *_a: _render_preview())
    nudge_left_btn.configure(command=lambda: _nudge_pos(-5))
    nudge_right_btn.configure(command=lambda: _nudge_pos(5))
    save_settings_btn.configure(command=_save_settings)
    preview_canvas.bind("<ButtonPress-1>", _on_canvas_press)
    preview_canvas.bind("<B1-Motion>", _on_canvas_drag)
    preview_canvas.bind("<ButtonRelease-1>", _on_canvas_release)
    preview_canvas.bind("<Double-Button-1>", _on_canvas_double_click)

    if _HAS_DND:
        for widget in (preview_frame, preview_canvas):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", _on_preview_drop)
            widget.dnd_bind("<<DragEnter>>", _on_preview_drag_enter)
            widget.dnd_bind("<<DragLeave>>", _on_preview_drag_leave)

    _render_preview()

    def _remove_bg() -> None:
        row = state.get("selected")
        if not row or not row.get("has_background"):
            return
        handle = str(row.get("handle") or "")
        title = str(row.get("title") or handle)
        if not messagebox.askyesno(APP_TITLE, f"Usunąć tło BIO dla «{title}»?"):
            return
        remove_btn.configure(state="disabled")
        progress_var.set(f"Usuwam tło: {handle}…")

        def worker() -> None:
            result = clear_bio_background(int(row.get("id") or 0), handle)

            def done() -> None:
                remove_btn.configure(state="normal")
                if not result.get("ok"):
                    progress_var.set("Błąd usuwania.")
                    messagebox.showerror(APP_TITLE, result.get("error") or "Nieznany błąd.")
                    return
                for r in state["rows"]:
                    if r.get("handle") == handle:
                        r["background_url"] = ""
                        r["has_background"] = False
                        r["status"] = "—"
                        break
                progress_var.set(f"Usunięto tło dla {handle}.")
                show_toast(host, "Tło BIO usunięte.")
                _refresh_tree(keep_handle=handle)

            host.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _open_collection() -> None:
        row = state.get("selected")
        if not row:
            return
        handle = str(row.get("handle") or "").strip()
        if not handle:
            return
        webbrowser.open(f"https://giclee-art-3.myshopify.com/collections/{handle}")

    upload_btn.configure(command=_pick_and_upload)
    remove_btn.configure(command=_remove_bg)
    open_btn.configure(command=_open_collection)

    def _on_filter_change(*_args) -> None:
        _refresh_tree(
            keep_handle=(state.get("selected") or {}).get("handle")
            if state.get("selected")
            else None
        )

    filter_var.trace_add("write", _on_filter_change)
    only_with_var.trace_add("write", _on_filter_change)
    only_missing_var.trace_add("write", _on_filter_change)

    refresh_btn = ttk.Button(left, text="Odśwież listę", command=lambda: _reload_async())
    refresh_btn.pack(anchor="e", pady=(6, 0))

    _reload_async()
