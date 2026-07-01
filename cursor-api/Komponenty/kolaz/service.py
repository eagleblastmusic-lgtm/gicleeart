"""Shopify + eksport kolaży."""

from __future__ import annotations

import re
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.tldobio.service import upload_bio_background

from .compositor import CollageImage, CollageSettings, ExportFormat, render_collage, save_collage

_COMPONENT_DIR = Path(__file__).resolve().parent
_EXPORT_DIR = _COMPONENT_DIR / "data" / "exports"
_ALLOWED_LOCAL = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}

Progress = Callable[[str], None]


def exports_dir() -> Path:
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return _EXPORT_DIR


def is_local_image(path: Path) -> bool:
    return path.suffix.lower() in _ALLOWED_LOCAL


def slugify_filename(text: str) -> str:
    s = (text or "kolaz").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:80] or "kolaz"


def fetch_collections(
    *,
    on_progress: Progress | None = None,
) -> list[dict[str, Any]]:
    from Komponenty.tldobio.service import fetch_collection_list

    return fetch_collection_list(on_progress=on_progress)


def fetch_collection_product_images(
    collection_id: int,
    *,
    limit: int = 24,
    on_progress: Progress | None = None,
) -> list[CollageImage]:
    shop, token = sc.load_session()
    if on_progress:
        on_progress("Pobieram produkty kolekcji…")
    data = sc.rest_get(
        shop,
        token,
        f"collections/{int(collection_id)}/products.json",
        limit=min(250, max(1, limit)),
        fields="id,title,images",
    )
    out: list[CollageImage] = []
    seen: set[str] = set()
    for product in (data or {}).get("products") or []:
        title = str(product.get("title") or "").strip()
        for img in product.get("images") or []:
            src = str(img.get("src") or "").split("?")[0].strip()
            if not src or src in seen:
                continue
            seen.add(src)
            out.append(CollageImage(title=title or src.rsplit("/", 1)[-1], url=src, selected=True))
            if len(out) >= limit:
                return out
    return out


def load_local_images(paths: list[Path]) -> list[CollageImage]:
    out: list[CollageImage] = []
    for p in paths:
        path = Path(p)
        if not path.is_file() or not is_local_image(path):
            continue
        out.append(CollageImage(title=path.stem, path=path, selected=True))
    return out


def default_export_path(
    *,
    handle_or_name: str,
    fmt: ExportFormat,
) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    ext = {"jpeg": "jpg", "webp": "webp", "png": "png"}[fmt]
    name = f"{slugify_filename(handle_or_name)}-{stamp}.{ext}"
    return exports_dir() / name


def build_collage(
    images: list[CollageImage],
    settings: CollageSettings,
) -> Any:
    return render_collage(images, settings)


def export_collage(
    image: Any,
    path: Path | None,
    *,
    fmt: ExportFormat = "jpeg",
    quality: int = 88,
    basename: str = "kolaz",
) -> Path:
    dest = path or default_export_path(handle_or_name=basename, fmt=fmt)
    q = quality
    return save_collage(image, dest, fmt=fmt, quality=q)


def upload_collage_as_bio_background(
    image_path: Path,
    collection_id: int,
    handle: str,
    title: str,
) -> dict[str, Any]:
    return upload_bio_background(
        int(collection_id),
        str(handle),
        str(title),
        Path(image_path),
    )
