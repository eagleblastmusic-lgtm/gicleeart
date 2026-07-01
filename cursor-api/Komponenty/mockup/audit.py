"""Skan produktow Shopify bez mockupow w galerii."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import PRODUCT_TYPE
from Komponenty.dodajobraz.parser import (
    alt_is_catalog_preview,
    alt_is_gallery_full,
    image_ref_is_mockup,
    mockup_suffixes_in_product_images,
)

from .templates import MockupSet

ProgressCallback = Callable[[int, int, str], None] | None
Logger = Callable[[str], None] | None


@dataclass(frozen=True)
class MissingMockupRow:
    product_id: int
    title: str
    artist: str
    base_title: str
    handle: str
    admin_url: str
    missing_suffixes: tuple[str, ...]
    preview_image_src: str | None


def _admin_url(shop: str, product_id: int) -> str:
    return f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{product_id}"


def parse_product_title(title: str) -> tuple[str, str] | None:
    text = (title or "").strip()
    if " - " not in text:
        return None
    artist, base_title = text.split(" - ", 1)
    artist = artist.strip()
    base_title = base_title.strip()
    if not artist or not base_title:
        return None
    return artist, base_title


def _is_mockup_image(im: dict) -> bool:
    alt = im.get("alt") or ""
    src = im.get("src") or ""
    return image_ref_is_mockup(alt) or image_ref_is_mockup(src)


def _ref_is_preview(ref: str | None) -> bool:
    if alt_is_catalog_preview(ref):
        return True
    low = (ref or "").lower()
    return "(preview)" in low or "_preview" in low or "-preview" in low


def _ref_is_full(ref: str | None) -> bool:
    if alt_is_gallery_full(ref):
        return True
    low = (ref or "").lower()
    return (
        "(full)" in low
        or "_full" in low
        or "-full" in low
        or "_wk." in low
        or "_kk." in low
        or low.endswith("_wk")
        or low.endswith("_kk")
    )


def _pick_artwork_source_src(images: list[dict]) -> str | None:
    """Zrodlo do generowania mockupu: preview, potem Full/WK/KK, na koncu pierwsze nie-mockup."""
    for im in images:
        if _is_mockup_image(im):
            continue
        src = (im.get("src") or "").strip()
        if not src:
            continue
        alt = im.get("alt") or ""
        if _ref_is_preview(alt) or _ref_is_preview(src):
            return src
    for im in images:
        if _is_mockup_image(im):
            continue
        src = (im.get("src") or "").strip()
        if not src:
            continue
        alt = im.get("alt") or ""
        if _ref_is_full(alt) or _ref_is_full(src):
            return src
    for im in images:
        if _is_mockup_image(im):
            continue
        src = (im.get("src") or "").strip()
        if src:
            return src
    return None


def _pick_preview_image_src(images: list[dict]) -> str | None:
    """Alias wsteczny — patrz `_pick_artwork_source_src`."""
    return _pick_artwork_source_src(images)


def scan_missing_mockups(
    mockup_sets: list[MockupSet],
    *,
    product_type: str | None = PRODUCT_TYPE,
    logger: Logger = None,
    on_progress: ProgressCallback = None,
) -> list[MissingMockupRow]:
    """Zwraca produkty typu Obraz bez wymaganych wariantow mockupu (CZB, CZCZ, ...)."""
    if not mockup_sets:
        return []

    expected = tuple(s.name_suffix for s in mockup_sets if s.name_suffix)
    if not expected:
        return []

    shop, token = sc.load_session()
    products = sc.iter_all_products(
        shop,
        token,
        product_type=product_type,
        fields="id,title,handle,product_type",
    )
    total = len(products)
    missing_rows: list[MissingMockupRow] = []

    for idx, prod in enumerate(products, start=1):
        pid = int(prod.get("id") or 0)
        title = str(prod.get("title") or "").strip()
        handle = str(prod.get("handle") or "").strip()
        if on_progress:
            on_progress(idx, total, title or f"id={pid}")

        parsed = parse_product_title(title)
        if not parsed:
            continue
        artist, base_title = parsed

        images = sc.list_product_images(shop, token, pid)
        present = mockup_suffixes_in_product_images(images)
        missing = tuple(sfx for sfx in expected if sfx not in present)
        if not missing:
            continue

        missing_rows.append(
            MissingMockupRow(
                product_id=pid,
                title=title,
                artist=artist,
                base_title=base_title,
                handle=handle,
                admin_url=_admin_url(shop, pid),
                missing_suffixes=missing,
                preview_image_src=_pick_preview_image_src(images),
            )
        )
        if logger:
            logger(f"[audit] Brak mockupu {missing}: {title}")

    return missing_rows


def row_to_log_line(row: MissingMockupRow) -> str:
    miss = ", ".join(row.missing_suffixes)
    return f"{row.title} — brak: {miss}"
