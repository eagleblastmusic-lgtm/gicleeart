"""Podgląd Tło do Bio — ten sam compositing co CSS na storefront (desktop)."""

from __future__ import annotations

from typing import Any

from PIL import Image

from .service import (
    BIO_MENU_GRADIENT_NARROW,
    BIO_MENU_GRADIENT_NONE,
    BIO_MENU_GRADIENT_WIDE,
    BIO_MENU_GRADIENT_WIDE_BOTTOM,
    BIO_MENU_GRADIENT_WIDE_V2,
    BIO_MENU_GRADIENT_WIDE_V3,
    BIO_MENU_GRADIENT_WIDE_V3_BOTTOM,
    DEFAULT_BIO_RADIAL_MASK,
    normalize_bio_cover_scale,
    normalize_bio_menu_gradient,
    normalize_bio_overlay_pct,
    normalize_bio_pos_x,
    normalize_bio_radial_mask,
    radial_mask_exposure_alpha,
    radial_mask_inner_stop,
)

# Proporcje sekcji BIO na desktopie (~1440×600 px — gab-hero-height / typowa szerokość).
SITE_PREVIEW_WIDTH = 520
SITE_PREVIEW_HEIGHT = int(round(SITE_PREVIEW_WIDTH * 600 / 1440))

_HORIZONTAL_STOPS: tuple[tuple[float, float], ...] = (
    (0.0, 0.66),
    (0.28, 0.66),
    (0.52, 0.4),
    (0.72, 0.34),
    (1.0, 0.5),
)


def _lerp_stops(t: float, stops: tuple[tuple[float, float], ...]) -> float:
    t = max(0.0, min(1.0, t))
    if t <= stops[0][0]:
        return stops[0][1]
    for idx in range(1, len(stops)):
        x0, y0 = stops[idx - 1]
        x1, y1 = stops[idx]
        if t <= x1:
            if x1 <= x0:
                return y1
            frac = (t - x0) / (x1 - x0)
            return y0 + (y1 - y0) * frac
    return stops[-1][1]


def _overlay_vertical_alpha(ty: float) -> float:
    return 0.16 + ty * 0.40


def _overlay_horizontal_alpha(tx: float) -> float:
    return _lerp_stops(tx, _HORIZONTAL_STOPS)


def _overlay_vignette_alpha(tx: float, ty: float) -> float:
    """radial-gradient(ellipse 118% 96% at 50% 50%, …) — warstwa na wierzchu overlay."""
    ex = (tx - 0.5) / 1.18
    ey = (ty - 0.5) / 0.96
    nd = (ex * ex + ey * ey) ** 0.5
    if nd <= 0.44:
        return 0.0
    if nd >= 1.0:
        return 0.22
    return 0.22 * (nd - 0.44) / 0.56


def _source_over_alpha(bottom: float, top: float) -> float:
    return top + bottom * (1.0 - top)


def site_overlay_alpha(tx: float, ty: float) -> float:
    """Łączna alpha trzech warstw .giclee-artist-bio-bg__overlay (jak w CSS)."""
    a = _overlay_vertical_alpha(ty)
    a = _source_over_alpha(a, _overlay_horizontal_alpha(tx))
    a = _source_over_alpha(a, _overlay_vignette_alpha(tx, ty))
    return max(0.0, min(1.0, a))


def apply_site_bio_overlay(img: Image.Image, *, overlay_pct: int) -> Image.Image:
    strength = normalize_bio_overlay_pct(overlay_pct) / 100.0
    if strength <= 0:
        return img.convert("RGBA")
    w, h = img.size
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    for y in range(h):
        ty = y / max(h - 1, 1)
        for x in range(w):
            tx = x / max(w - 1, 1)
            alpha = site_overlay_alpha(tx, ty) * strength
            px[x, y] = (0, 0, 0, int(max(0.0, min(1.0, alpha)) * 255))
    return Image.alpha_composite(base, overlay)


def apply_site_bio_radial_mask(img: Image.Image, mask: dict[str, Any] | None) -> Image.Image:
    mask = normalize_bio_radial_mask(mask or DEFAULT_BIO_RADIAL_MASK)
    if not mask.get("enabled") or mask.get("exposure", 0) <= 0:
        return img
    w, h = img.size
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    cx = mask["cx"] / 100.0 * w
    cy = mask["cy"] / 100.0 * h
    rx = max(1.0, mask["rx"] / 100.0 * w)
    ry = max(1.0, mask["ry"] / 100.0 * h)
    inner_pct = radial_mask_inner_stop(mask["feather"])
    max_alpha = radial_mask_exposure_alpha(mask["exposure"])
    span = max(0.001, 100.0 - inner_pct)
    for y in range(h):
        for x in range(w):
            nd = (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) ** 0.5
            nd_pct = nd * 100.0
            if nd_pct <= inner_pct:
                alpha = 0.0
            elif nd_pct >= 100.0:
                alpha = max_alpha
            else:
                t = (nd_pct - inner_pct) / span
                alpha = max_alpha * max(0.0, min(1.0, t))
            px[x, y] = (0, 0, 0, int(alpha * 255))
    return Image.alpha_composite(base, overlay)


def _menu_gradient_alpha_wide(ty: float) -> float:
    """linear-gradient(180deg, #000 0% … transparent 100%) — pas szeroki pod menu."""
    stops: tuple[tuple[float, float], ...] = (
        (0.0, 1.0),
        (0.12, 1.0),
        (0.30, 0.94),
        (0.52, 0.72),
        (0.78, 0.28),
        (1.0, 0.0),
    )
    return _lerp_stops(ty, stops)


def _menu_gradient_alpha_wide_v2(ty: float) -> float:
    """Jak szeroki, ale bez płaskiego pasu #000 u góry — gradient od pierwszego piksela."""
    stops: tuple[tuple[float, float], ...] = (
        (0.0, 1.0),
        (0.2045, 0.94),
        (0.4545, 0.72),
        (0.75, 0.28),
        (1.0, 0.0),
    )
    return _lerp_stops(ty, stops)


def _menu_gradient_alpha_narrow(ty: float) -> float:
    """Krótszy pas — szybsze przejście do przezroczystości."""
    stops: tuple[tuple[float, float], ...] = (
        (0.0, 1.0),
        (0.22, 1.0),
        (0.58, 0.82),
        (1.0, 0.0),
    )
    return _lerp_stops(ty, stops)


def _paint_menu_gradient_band(
    px: Any,
    *,
    w: int,
    h: int,
    fade_h: int,
    alpha_fn: Any,
    top: bool,
) -> None:
    band = min(fade_h, h)
    for i in range(band):
        ty = i / max(band - 1, 1)
        alpha = max(0.0, min(1.0, alpha_fn(ty)))
        a = int(alpha * 255)
        y = i if top else h - 1 - i
        for x in range(w):
            existing = px[x, y][3]
            if a > existing:
                px[x, y] = (0, 0, 0, a)


def apply_site_menu_gradient(img: Image.Image, *, menu_gradient: str) -> Image.Image:
    mode = normalize_bio_menu_gradient(menu_gradient)
    if mode == BIO_MENU_GRADIENT_NONE:
        return img
    w, h = img.size
    bottom = mode in (BIO_MENU_GRADIENT_WIDE_BOTTOM, BIO_MENU_GRADIENT_WIDE_V3_BOTTOM)
    if mode == BIO_MENU_GRADIENT_NARROW:
        fade_h = max(1, int(round(h * (64 / 600.0))))
        alpha_fn = _menu_gradient_alpha_narrow
        bottom = False
    else:
        fade_h = max(1, int(round(min(h * 0.28, h * (108 / 600.0)))))
        if mode in (BIO_MENU_GRADIENT_WIDE_V3, BIO_MENU_GRADIENT_WIDE_V3_BOTTOM):
            fade_h = max(1, int(round(fade_h * 0.6)))
            alpha_fn = _menu_gradient_alpha_wide_v2
        elif mode == BIO_MENU_GRADIENT_WIDE_V2:
            alpha_fn = _menu_gradient_alpha_wide_v2
        else:
            alpha_fn = _menu_gradient_alpha_wide
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    _paint_menu_gradient_band(px, w=w, h=h, fade_h=fade_h, alpha_fn=alpha_fn, top=True)
    if bottom:
        _paint_menu_gradient_band(px, w=w, h=h, fade_h=fade_h, alpha_fn=alpha_fn, top=False)
    return Image.alpha_composite(base, overlay)


def cover_crop_bio_image(
    img: Image.Image,
    box_w: int,
    box_h: int,
    pos_x: int,
) -> Image.Image:
    pos_x = normalize_bio_pos_x(pos_x)
    iw, ih = img.size
    if iw <= 0 or ih <= 0:
        return img
    scale = max(box_w / iw, box_h / ih)
    nw = max(1, int(round(iw * scale)))
    nh = max(1, int(round(ih * scale)))
    scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
    max_x = max(0, nw - box_w)
    x = int(round(max_x * (pos_x / 100.0)))
    y = max(0, (nh - box_h) // 2)
    return scaled.crop((x, y, x + box_w, y + box_h))


def apply_cover_scale_bio_image(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Symulacja CSS transform: scale(1.04) + overflow hidden."""
    if img.size != (box_w, box_h):
        img = img.resize((box_w, box_h), Image.Resampling.LANCZOS)
    nw = max(1, int(round(box_w * 1.04)))
    nh = max(1, int(round(box_h * 1.04)))
    scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (nw - box_w) // 2
    y = (nh - box_h) // 2
    return scaled.crop((x, y, x + box_w, y + box_h))


def compose_site_bio_background(
    img: Image.Image,
    box_w: int,
    box_h: int,
    pos_x: int,
    *,
    overlay_pct: int,
    cover_scale: bool = False,
    radial_mask: dict[str, Any] | None = None,
    menu_gradient: str | None = None,
) -> Image.Image:
    cropped = cover_crop_bio_image(img, box_w, box_h, pos_x)
    if normalize_bio_cover_scale(cover_scale):
        cropped = apply_cover_scale_bio_image(cropped, box_w, box_h)
    composed = apply_site_bio_overlay(cropped, overlay_pct=overlay_pct)
    composed = apply_site_bio_radial_mask(composed, radial_mask)
    return apply_site_menu_gradient(
        composed,
        menu_gradient=menu_gradient or "",
    )
