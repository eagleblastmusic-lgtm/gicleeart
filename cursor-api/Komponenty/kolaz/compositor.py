"""Silnik składania kolażu (Pillow)."""

from __future__ import annotations

import io
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PIL import Image, ImageFilter

from .layouts import CollageSlot, apply_spread, compute_layout_slots

ExportFormat = Literal["jpeg", "webp", "png"]


@dataclass
class CollageImage:
    """Źródło pojedynczego kafelka."""

    title: str = ""
    path: Path | None = None
    url: str | None = None
    selected: bool = True
    pil: Image.Image | None = field(default=None, repr=False)

    def load(self) -> Image.Image:
        if self.pil is not None:
            return self.pil.convert("RGBA")
        if self.path and self.path.is_file():
            self.pil = Image.open(self.path).convert("RGBA")
            return self.pil
        if self.url:
            with urllib.request.urlopen(self.url, timeout=90) as resp:
                self.pil = Image.open(io.BytesIO(resp.read())).convert("RGBA")
            return self.pil
        raise FileNotFoundError(f"Brak obrazu: {self.title or self.path or self.url}")


@dataclass
class CollageSettings:
    width: int = 2400
    height: int = 1200
    layout: str = "museum_scatter"
    seed: int = 42
    image_count: int = 6
    bg_color: tuple[int, int, int] = (18, 16, 14)
    bg_gradient: bool = False
    bg_gradient_end: tuple[int, int, int] = (8, 8, 10)
    frame_width: int = 8
    frame_color: tuple[int, int, int, int] = (245, 242, 235, 255)
    rotation_scale: float = 1.0
    shadow: bool = True
    shadow_blur: int = 14
    shadow_alpha: int = 90
    shadow_offset: tuple[int, int] = (6, 10)
    card_scale: float = 1.0
    spread: float = 1.0
    jpeg_quality: int = 88
    webp_quality: int = 88


def _fit_cover(img: Image.Image, tw: int, th: int) -> Image.Image:
    aw, ah = img.size
    scale = max(tw / aw, th / ah)
    nw = max(1, int(round(aw * scale)))
    nh = max(1, int(round(ah * scale)))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _make_background(settings: CollageSettings) -> Image.Image:
    w, h = settings.width, settings.height
    if not settings.bg_gradient:
        return Image.new("RGB", (w, h), settings.bg_color)
    top = Image.new("RGB", (w, h), settings.bg_color)
    bottom = Image.new("RGB", (w, h), settings.bg_gradient_end)
    mask = Image.linear_gradient("L").resize((w, h))
    return Image.composite(bottom, top, mask)


def _frame_card(
    img: Image.Image,
    *,
    frame_width: int,
    frame_color: tuple[int, int, int, int],
    rotation: float,
    shadow: bool,
    shadow_blur: int,
    shadow_alpha: int,
    shadow_offset: tuple[int, int],
) -> Image.Image:
    fw = max(0, int(frame_width))
    inner = img.convert("RGBA")
    tw, th = inner.size
    framed = Image.new("RGBA", (tw + fw * 2, th + fw * 2), (0, 0, 0, 0))
    border = Image.new("RGBA", (tw + fw * 2, th + fw * 2), frame_color)
    framed.paste(border, (0, 0))
    framed.paste(inner, (fw, fw), inner)

    if abs(rotation) > 0.05:
        framed = framed.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)

    if not shadow or shadow_alpha <= 0:
        return framed

    pad = shadow_blur * 2 + max(abs(shadow_offset[0]), abs(shadow_offset[1])) + 8
    canvas = Image.new("RGBA", (framed.width + pad * 2, framed.height + pad * 2), (0, 0, 0, 0))
    shadow_layer = Image.new("RGBA", framed.size, (0, 0, 0, shadow_alpha))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
    sx = pad + max(0, shadow_offset[0])
    sy = pad + max(0, shadow_offset[1])
    canvas.paste(shadow_layer, (sx, sy), shadow_layer)
    canvas.paste(framed, (pad, pad), framed)
    return canvas


def render_collage(
    images: list[CollageImage],
    settings: CollageSettings,
    *,
    slots: list[CollageSlot] | None = None,
) -> Image.Image:
    selected = [im for im in images if im.selected]
    if not selected:
        raise ValueError("Wybierz co najmniej jeden obraz do kolażu.")

    count = max(1, min(settings.image_count, len(selected)))
    use_images = selected[:count]
    layout_slots = slots or compute_layout_slots(
        settings.layout, count, seed=settings.seed
    )
    if len(layout_slots) < count:
        layout_slots = compute_layout_slots(settings.layout, count, seed=settings.seed)

    layout_slots = apply_spread(layout_slots, settings.spread)

    canvas = _make_background(settings)
    w, h = settings.width, settings.height

    layers: list[tuple[int, Image.Image, int, int]] = []
    for idx, (src, slot) in enumerate(zip(use_images, layout_slots, strict=False)):
        art = src.load()
        tw = max(32, int(w * slot.w * settings.card_scale))
        th = max(32, int(h * slot.h * settings.card_scale))
        fitted = _fit_cover(art, tw, th)
        rot = slot.rotation * settings.rotation_scale
        card = _frame_card(
            fitted,
            frame_width=settings.frame_width,
            frame_color=settings.frame_color,
            rotation=rot,
            shadow=settings.shadow,
            shadow_blur=settings.shadow_blur,
            shadow_alpha=settings.shadow_alpha,
            shadow_offset=settings.shadow_offset,
        )
        ox = int(w * slot.x)
        oy = int(h * slot.y)
        layers.append((slot.z if slot.z else idx, card, ox, oy))

    layers.sort(key=lambda t: t[0])
    for _, card, ox, oy in layers:
        canvas.paste(card, (ox, oy), card)

    return canvas.convert("RGB")


def save_collage(
    image: Image.Image,
    path: Path,
    *,
    fmt: ExportFormat = "jpeg",
    quality: int = 88,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jpeg":
        image.save(path, "JPEG", quality=quality, optimize=True)
    elif fmt == "webp":
        image.save(path, "WEBP", quality=quality, method=4)
    else:
        image.save(path, "PNG", optimize=True)
    return path
