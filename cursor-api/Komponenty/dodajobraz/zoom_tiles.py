"""Generator kafelkow HD + manifest JSON pod OpenSeadragon (R2 / PDP)."""

from __future__ import annotations

import json
import math
import shutil
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

OVERVIEW_MAX_EDGE = 2400
TILE_SIZE = 1024
WEBP_QUALITY = 88

Logger = Callable[[str], None]


@dataclass
class GeneratedZoomPackage:
    """Paczka plikow w katalogu tymczasowym — po uploadzie wywolaj cleanup()."""

    root: Path
    manifest: dict[str, object]
    upload_items: list[tuple[str, Path]]  # (klucz wzgledny w R2, plik lokalny)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def generate_zoom_package(
    image_path: Path,
    *,
    logger: Logger | None = None,
) -> GeneratedZoomPackage:
    """Dzieli obraz na overview + siatke kafelkow (WEBP).

    Zwraca manifest (bez public URL) i liste plikow do wgrania.
    """
    if not _HAS_PIL:
        raise RuntimeError("Brak Pillow — zainstaluj: pip install Pillow")

    p = Path(image_path)
    if not p.is_file():
        raise FileNotFoundError(str(p))

    root = Path(tempfile.mkdtemp(prefix="giclee_zoom_"))
    tiles_dir = root / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(p) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        width, height = im.size
        cols = max(1, math.ceil(width / TILE_SIZE))
        rows = max(1, math.ceil(height / TILE_SIZE))

        _log(
            logger,
            f"[zoom] {p.name}: {width}x{height} px -> siatka {cols}x{rows} "
            f"({cols * rows} kafelkow + podglad)",
        )

        # Podglad
        overview = im.copy()
        overview.thumbnail((OVERVIEW_MAX_EDGE, OVERVIEW_MAX_EDGE), Image.LANCZOS)  # type: ignore[attr-defined]
        overview_path = root / "overview.webp"
        overview.save(overview_path, format="WEBP", quality=WEBP_QUALITY, method=6)

        upload_items: list[tuple[str, Path]] = [("overview.webp", overview_path)]

        for row in range(rows):
            for col in range(cols):
                left = col * TILE_SIZE
                upper = row * TILE_SIZE
                right = min(left + TILE_SIZE, width)
                lower = min(upper + TILE_SIZE, height)
                tile = im.crop((left, upper, right, lower))
                # OpenSeadragon zaklada stale TILE_SIZE x TILE_SIZE
                canvas = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (255, 255, 255))
                canvas.paste(tile, (0, 0))
                name = f"tiles/{col}_{row}.webp"
                out = root / name
                out.parent.mkdir(parents=True, exist_ok=True)
                canvas.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
                upload_items.append((name, out))

    manifest: dict[str, object] = {
        "v": 1,
        "width": width,
        "height": height,
        "tileSize": TILE_SIZE,
        "cols": cols,
        "rows": rows,
        "overview": "overview.webp",
        "tilesPrefix": "tiles",
        "format": "webp",
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return GeneratedZoomPackage(root=root, manifest=manifest, upload_items=upload_items)


def manifest_json(manifest: dict[str, object], *, public_base_url: str, prefix: str) -> str:
    """Manifest z pelnymi URL do zapisu w metafieldzie Shopify."""
    base = public_base_url.rstrip("/") + "/" + prefix.strip("/")
    out = dict(manifest)
    out["baseUrl"] = base
    out["overviewUrl"] = f"{base}/{manifest['overview']}"
    return json.dumps(out, ensure_ascii=False)
