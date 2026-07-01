"""Przygotowanie pliku do uploadu Shopify (limit 20 megapikseli)."""

from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from PIL import Image, ImageFile, ImageOps  # type: ignore

    _HAS_PIL = True
    Image.MAX_IMAGE_PIXELS = None
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    _HAS_PIL = False

# Shopify Admin API: max 20 megapikseli (szer. x wys.).
SHOPIFY_MAX_PIXELS = 20_000_000
# Margines pod zaokraglenia przy skalowaniu.
SHOPIFY_SAFE_MAX_PIXELS = 19_500_000

Logger = Callable[[str], None]


@dataclass
class ResolvedUpload:
    path: Path
    filename: str
    _temp_path: Path | None = None
    resized: bool = False

    def cleanup(self) -> None:
        if self._temp_path is not None:
            try:
                self._temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _target_size(w: int, h: int, max_pixels: int) -> tuple[int, int]:
    px = w * h
    if px <= max_pixels:
        return w, h
    scale = (max_pixels / px) ** 0.5
    return max(1, int(w * scale)), max(1, int(h * scale))


def resolve_shopify_upload(
    image_path: Path,
    *,
    logger: Logger | None = None,
) -> ResolvedUpload:
    """Zwraca sciezke do wyslania; tworzy tymczasowy JPEG gdy trzeba zmniejszyc."""
    p = Path(image_path)
    if not p.is_file():
        raise FileNotFoundError(str(p))

    if not _HAS_PIL:
        return ResolvedUpload(path=p, filename=p.name)

    with Image.open(p) as im:  # type: ignore[attr-defined]
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        if w * h <= SHOPIFY_SAFE_MAX_PIXELS:
            return ResolvedUpload(path=p, filename=p.name)

        tw, th = _target_size(w, h, SHOPIFY_SAFE_MAX_PIXELS)
        if logger:
            mp_before = (w * h) / 1_000_000
            mp_after = (tw * th) / 1_000_000
            logger(
                f"[obraz] Zmniejszam {p.name}: {w}x{h} ({mp_before:.1f} MP) "
                f"-> {tw}x{th} ({mp_after:.1f} MP) — limit Shopify 20 MP"
            )
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        resized = im.resize((tw, th), Image.LANCZOS)  # type: ignore[attr-defined]
        buf = io.BytesIO()
        out_name = p.with_suffix(".jpg").name
        resized.save(buf, format="JPEG", quality=90, optimize=True, progressive=True)
        tmp = tempfile.NamedTemporaryFile(
            prefix="dodajobraz_shopify_",
            suffix=".jpg",
            delete=False,
        )
        tmp.write(buf.getvalue())
        tmp.close()
        temp_path = Path(tmp.name)
        return ResolvedUpload(
            path=temp_path,
            filename=out_name,
            _temp_path=temp_path,
            resized=True,
        )
