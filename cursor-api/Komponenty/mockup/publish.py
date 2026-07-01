"""Generowanie mockupu i upload do galerii produktu Shopify."""

from __future__ import annotations

import ssl
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import add_follow_up_image
from Komponenty.dodajobraz.parser import (
    IMAGE_ROLE_MOCKUP,
    mockup_suffixes_in_product_images,
    parse_filename,
    parse_title_metadata,
)

from .audit import MissingMockupRow
from .compositor import composite_artwork
from .templates import MockupSet, MockupTemplate, template_for_orientation

Logger = Callable[[str], None] | None

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def is_image_path(path: Path) -> bool:
    return path.suffix.lower() in _IMAGE_EXTS


def mockup_output_name(
    artist: str,
    base_title: str,
    *,
    name_suffix: str = "",
    ext: str = ".webp",
) -> str:
    sfx = (name_suffix or "").strip().upper()
    if sfx:
        return f"{artist} - {base_title} - (mockup) - {sfx}{ext}"
    return f"{artist} - {base_title} - (mockup){ext}"


def mockup_plan(
    artwork_path: Path,
    mockup_set: MockupSet,
) -> tuple[MockupTemplate, str, str]:
    """Zwraca (szablon, artysta, tytul_bazowy) bez renderowania obrazu."""
    artist, base_title = parse_artwork_path(artwork_path)
    with Image.open(artwork_path) as im:
        w, h = im.size
    template = template_for_orientation(mockup_set, width=w, height=h)
    return template, artist, base_title


def preview_info_text(
    path: Path,
    template: MockupTemplate,
    artist: str,
    base_title: str,
    *,
    name_suffix: str = "",
) -> str:
    return (
        f"{path.name}\n"
        f"Szablon: {template.name} ({template.orientation})\n"
        f"Shopify: {mockup_output_name(artist, base_title, name_suffix=name_suffix)}"
    )


def parse_artwork_path(path: Path) -> tuple[str, str]:
    """Z nazwy pliku wyciaga artyste i bazowy tytul (Full/preview/mockup odlupane z tytulu)."""
    artist, raw_title = parse_filename(path)
    base_title, _fnum, _corr, image_role, _fkind = parse_title_metadata(raw_title)
    if image_role == IMAGE_ROLE_MOCKUP:
        raise ValueError(
            f"{path.name}: to juz plik (mockup) — wrzuc zrodlowy obraz (Full, preview lub bez sufiksu)."
        )
    return artist, base_title


def render_mockup(
    artwork_path: Path,
    mockup_set: MockupSet,
    *,
    logger: Logger = None,
) -> tuple[Image.Image, MockupTemplate, str, str]:
    """Sklada mockup. Zwraca (obraz RGBA, szablon, artysta, tytul_bazowy)."""
    artist, base_title = parse_artwork_path(artwork_path)

    with Image.open(artwork_path) as im:
        w, h = im.size
    template = template_for_orientation(mockup_set, width=w, height=h)
    if logger:
        logger(f"[mockup] Skladam: {artwork_path.name} -> {template.name} ({template.orientation})")
    composed = composite_artwork(template, artwork_path)
    return composed, template, artist, base_title


def _unique_output_path(folder: Path, filename: str) -> Path:
    """Unikalna sciezka w folderze (dopisek «(2)» gdy plik juz istnieje)."""
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    ext = Path(filename).suffix
    n = 2
    while True:
        candidate = folder / f"{stem} ({n}){ext}"
        if not candidate.exists():
            return candidate
        n += 1


def save_mockup_to_disk(
    artwork_path: Path,
    mockup_set: MockupSet,
    output_dir: Path,
    *,
    logger: Logger = None,
) -> Path:
    """Renderuje mockup i zapisuje WEBP w wybranym folderze. Zwraca sciezke pliku."""
    composed, _template, artist, base_title = render_mockup(
        artwork_path, mockup_set, logger=logger
    )
    out_name = mockup_output_name(artist, base_title, name_suffix=mockup_set.name_suffix)
    dest = _unique_output_path(Path(output_dir), out_name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    composed.convert("RGB").save(dest, format="WEBP", quality=90, method=4)
    if logger:
        logger(f"[mockup] Eksport na dysk: {dest}")
    return dest


def render_mockup_to_temp(
    artwork_path: Path,
    template: MockupTemplate,
    *,
    artist: str,
    base_title: str,
    name_suffix: str = "",
    composed: Image.Image | None = None,
    logger: Logger = None,
) -> Path:
    if logger:
        logger(f"[mockup] Zapisuje: {artwork_path.name} -> {template.name}")
    img = composed if composed is not None else composite_artwork(template, artwork_path)
    out_name = mockup_output_name(artist, base_title, name_suffix=name_suffix)
    tmp = Path(tempfile.gettempdir()) / "giclee_mockup" / out_name
    tmp.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(tmp, format="WEBP", quality=90, method=4)
    if logger:
        logger(f"[mockup] Zapisano tymczasowo: {tmp.name}")
    return tmp


def product_has_mockup_suffix(shop: str, token: str, product_id: int, suffix: str) -> bool:
    images = sc.list_product_images(shop, token, int(product_id))
    present = mockup_suffixes_in_product_images(images)
    return suffix.upper() in present


def _safe_temp_artwork_name(artist: str, base_title: str, ext: str) -> str:
    """Nazwa pliku tymczasowego — format «Artysta - Tytul.ext», bez znakow niedozwolonych w Windows."""
    import re

    def clean(part: str) -> str:
        part = re.sub(r'[<>:"/\\|?*]', "-", part or "")
        return re.sub(r"\s+", " ", part).strip()

    return f"{clean(artist)} - {clean(base_title)}{ext}"


def download_temp_artwork(url: str, filename: str) -> Path:
    dest = Path(tempfile.gettempdir()) / "giclee_mockup" / "sources" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "GicleeApp/1.0 (mockup)"})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=180) as resp:
        dest.write_bytes(resp.read())
    return dest


def publish_mockup_for_row(
    row: MissingMockupRow,
    mockup_set: MockupSet,
    *,
    logger: Logger = None,
) -> dict[str, Any]:
    """Generuje brakujacy mockup z obrazu (preview) w galerii produktu."""
    suffix = (mockup_set.name_suffix or "").strip().upper()
    if suffix and suffix not in row.missing_suffixes:
        return {"skipped": True, "reason": f"Wariant {suffix} juz jest lub nie wymagany"}
    if not row.preview_image_src:
        raise ValueError(
            f"{row.title}: brak obrazu zrodlowego (preview lub Full) w galerii Shopify"
        )

    shop, token = sc.load_session()
    if product_has_mockup_suffix(shop, token, row.product_id, suffix):
        return {"skipped": True, "product_id": row.product_id, "reason": "Mockup juz istnieje"}

    ext = ".jpg"
    if ".webp" in row.preview_image_src.lower():
        ext = ".webp"
    elif ".png" in row.preview_image_src.lower():
        ext = ".png"
    fname = _safe_temp_artwork_name(row.artist, row.base_title, ext)
    src_tmp = download_temp_artwork(row.preview_image_src, fname)
    try:
        return publish_mockup(
            src_tmp,
            mockup_set,
            product_id=row.product_id,
            skip_if_exists=True,
            logger=logger,
        )
    finally:
        try:
            src_tmp.unlink(missing_ok=True)
        except OSError:
            pass


def publish_mockup(
    artwork_path: Path,
    mockup_set: MockupSet,
    *,
    product_id: int | None = None,
    skip_if_exists: bool = False,
    logger: Logger = None,
) -> dict[str, Any]:
    """Tworzy mockup z obrazu i dogrywa do produktu w Shopify."""
    if skip_if_exists and product_id and mockup_set.name_suffix:
        shop, token = sc.load_session()
        if product_has_mockup_suffix(shop, token, int(product_id), mockup_set.name_suffix):
            if logger:
                logger(f"[mockup] Pomijam — juz jest {mockup_set.name_suffix} (produkt {product_id})")
            return {
                "skipped": True,
                "product_id": int(product_id),
                "reason": f"Mockup {mockup_set.name_suffix} juz w galerii",
            }

    composed, template, artist, base_title = render_mockup(
        artwork_path, mockup_set, logger=logger
    )

    tmp_path = render_mockup_to_temp(
        artwork_path,
        template,
        artist=artist,
        base_title=base_title,
        name_suffix=mockup_set.name_suffix,
        composed=composed,
        logger=logger,
    )

    try:
        if logger:
            logger(f"[shopify] Szukam produktu: {artist} - {base_title}")
        result = add_follow_up_image(
            image_path=tmp_path,
            artist=artist,
            base_title=base_title,
            follow_up_number=0,
            follow_up_kind=IMAGE_ROLE_MOCKUP,
            mockup_name_suffix=mockup_set.name_suffix,
            product_id=int(product_id) if product_id else None,
            logger=logger,
        )
        result["source_file"] = str(artwork_path)
        result["mockup_file"] = tmp_path.name
        result["template"] = template.id
        return result
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
