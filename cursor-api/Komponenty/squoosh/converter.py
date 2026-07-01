"""Konwersja obrazow do WebP — parametry jak w Squoosh (Pillow/libwebp)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

try:
    from PIL import Image, ImageFile, ImageOps  # type: ignore

    _HAS_PIL = True
    Image.MAX_IMAGE_PIXELS = None
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    _HAS_PIL = False

Logger = Callable[[str], None]

DEFAULT_QUALITY = 80
DEFAULT_METHOD = 4  # Squoosh „Effort” 0–6 → Pillow method 0–6
WEBP_MAX_DIMENSION = 16383  # limit libwebp / WebP na bok (nie da sie go obejsc w jednym pliku .webp)

OVERSIZED_SCALE_WEBP = "scale_webp"
OVERSIZED_JPEG_FULL = "jpeg_full"

INPUT_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
    ".gif",
}


def is_image_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in INPUT_SUFFIXES


def normalize_name_suffix(name_suffix: str) -> str:
    """Fragment dodawany do stem: «Full» -> « - Full», «-KK» -> « - KK»."""
    s = (name_suffix or "").strip()
    if not s:
        return ""
    if s.startswith(" - "):
        return s
    if s.startswith("- "):
        return " - " + s[2:].strip()
    if s.startswith("-"):
        return " - " + s[1:].strip()
    if s.startswith("_"):
        return " - " + s[1:].strip()
    return f" - {s}"


def output_path_for(
    src: Path,
    out_dir: Path | None,
    *,
    suffix: str = ".webp",
    name_suffix: str = "",
) -> Path:
    base = out_dir if out_dir else src.parent
    extra = normalize_name_suffix(name_suffix)
    return base / f"{src.stem}{extra}{suffix}"


def exceeds_webp_limit(path: Path) -> bool:
    """Czy po obrocie EXIF obraz nie miesci sie w limicie WebP."""
    if not _HAS_PIL:
        return False
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        return w > WEBP_MAX_DIMENSION or h > WEBP_MAX_DIMENSION


def fit_image_for_webp(
    im: Image.Image,
    *,
    max_dim: int = WEBP_MAX_DIMENSION,
) -> tuple[Image.Image, str | None]:
    """Zmniejsza obraz, jesli ktorys bok przekracza limit WebP (zachowuje proporcje)."""
    w, h = im.size
    if w <= max_dim and h <= max_dim:
        return im, None
    scale = min(max_dim / w, max_dim / h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    return resized, f"przeskalowano {w}x{h} -> {nw}x{nh} (limit WebP {max_dim}px)"


def _flatten_on_white(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        bg.alpha_composite(rgba)
        return bg.convert("RGB")
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def convert_to_webp(
    src: Path,
    dest: Path,
    *,
    quality: int = DEFAULT_QUALITY,
    method: int = DEFAULT_METHOD,
    lossless: bool = False,
    preserve_alpha: bool = False,
    engine: str = "pillow",
    oversized_mode: str = OVERSIZED_SCALE_WEBP,
    logger: Logger | None = None,
) -> dict[str, int | str]:
    """Konwertuje jeden plik. engine: 'pillow' | 'squoosh'.

    oversized_mode:
      scale_webp — zmniejsza do limitu WebP (domyslne zachowanie WebP),
      jpeg_full — przy przekroczeniu limitu zapisuje JPEG w pelnej rozdzielczosci.
    """
    src = Path(src)
    dest = Path(dest)
    mode = (oversized_mode or OVERSIZED_SCALE_WEBP).strip().lower()
    if mode == OVERSIZED_JPEG_FULL and exceeds_webp_limit(src):
        dest_jpg = dest.with_suffix(".jpg")
        _convert_to_jpeg_pillow(
            src,
            dest_jpg,
            quality=quality,
            preserve_alpha=preserve_alpha,
            logger=logger,
        )
        src_b = src.stat().st_size
        dst_b = dest_jpg.stat().st_size
        if logger:
            pct = (1 - dst_b / src_b) * 100 if src_b else 0
            logger(
                f"[jpeg] OK {src.name} -> {dest_jpg.name} "
                f"(pelna rozdzielczosc, WebP max {WEBP_MAX_DIMENSION}px; "
                f"{src_b // 1024} KB -> {dst_b // 1024} KB, {pct:.0f}% mniej)"
            )
        return {
            "src_bytes": src_b,
            "dst_bytes": dst_b,
            "dest": str(dest_jpg),
            "format": "jpeg",
        }

    eng = (engine or "pillow").strip().lower()

    if eng == "squoosh":
        from .squoosh_cli import convert_squoosh_cli

        convert_squoosh_cli(
            src,
            dest,
            quality=quality,
            method=method,
            lossless=lossless,
            preserve_alpha=preserve_alpha,
        )
    else:
        _convert_to_webp_pillow(
            src,
            dest,
            quality=quality,
            method=method,
            lossless=lossless,
            preserve_alpha=preserve_alpha,
            logger=logger,
        )

    src_b = src.stat().st_size
    dst_b = dest.stat().st_size
    if logger:
        tag = "squoosh" if eng == "squoosh" else "pillow"
        pct = (1 - dst_b / src_b) * 100 if src_b else 0
        logger(
            f"[webp/{tag}] OK {src.name} -> {dest.name} "
            f"({src_b // 1024} KB -> {dst_b // 1024} KB, {pct:.0f}% mniej)"
        )
    return {"src_bytes": src_b, "dst_bytes": dst_b, "dest": str(dest), "format": "webp"}


def _convert_to_jpeg_pillow(
    src: Path,
    dest: Path,
    *,
    quality: int = DEFAULT_QUALITY,
    preserve_alpha: bool = False,
    logger: Logger | None = None,
) -> None:
    """JPEG w oryginalnej rozdzielczosci (bez limitu WebP)."""
    if not _HAS_PIL:
        raise RuntimeError("Brak Pillow — zainstaluj: pip install Pillow")

    dest.parent.mkdir(parents=True, exist_ok=True)
    q = max(1, min(100, int(quality)))

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if getattr(im, "is_animated", False):
            im.seek(0)
        if preserve_alpha and im.mode in ("RGBA", "LA"):
            out_im = im.convert("RGBA")
            flat = Image.new("RGBA", out_im.size, (255, 255, 255, 255))
            flat.alpha_composite(out_im)
            out_im = flat.convert("RGB")
        else:
            out_im = _flatten_on_white(im)
        size = out_im.size
        out_im.save(
            dest,
            format="JPEG",
            quality=q,
            subsampling=0,
            optimize=True,
        )
    if logger:
        logger(
            f"[jpeg] {src.name}: zapis {size[0]}x{size[1]} px "
            f"(ponad limit WebP {WEBP_MAX_DIMENSION}px)"
        )


def _convert_to_webp_pillow(
    src: Path,
    dest: Path,
    *,
    quality: int = DEFAULT_QUALITY,
    method: int = DEFAULT_METHOD,
    lossless: bool = False,
    preserve_alpha: bool = False,
    logger: Logger | None = None,
) -> None:
    """Konwersja Pillow/libwebp."""
    if not _HAS_PIL:
        raise RuntimeError("Brak Pillow — zainstaluj: pip install Pillow")

    src = Path(src)
    dest = Path(dest)
    if not src.is_file():
        raise FileNotFoundError(str(src))

    dest.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if getattr(im, "is_animated", False):
            im.seek(0)

        if lossless:
            if preserve_alpha and im.mode in ("RGBA", "LA"):
                out_im = im.convert("RGBA")
            elif preserve_alpha:
                out_im = im.convert("RGBA") if "A" in im.getbands() else im.convert("RGB")
            else:
                out_im = _flatten_on_white(im)
            save_kw = {"format": "WEBP", "lossless": True, "method": max(0, min(6, int(method)))}
        else:
            q = max(1, min(100, int(quality)))
            m = max(0, min(6, int(method)))
            if preserve_alpha:
                out_im = im.convert("RGBA") if im.mode != "RGBA" else im.copy()
                save_kw = {"format": "WEBP", "quality": q, "method": m}
            else:
                out_im = _flatten_on_white(im)
                save_kw = {"format": "WEBP", "quality": q, "method": m}

        out_im, resize_note = fit_image_for_webp(out_im)
        if resize_note and logger:
            logger(
                f"[webp/pillow] {src.name}: {resize_note} "
                f"(w ustawieniach wybierz «pelna rozdzielczosc → JPEG»)"
            )
        out_im.save(dest, **save_kw)
