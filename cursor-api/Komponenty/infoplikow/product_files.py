"""Pobieranie i klasyfikacja grafik produktu ze sklepu Shopify."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

from Komponenty._shared.storefront_urls import product_storefront_url
from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.parser import (
    IMAGE_ROLE_FULL,
    IMAGE_ROLE_MOCKUP,
    IMAGE_ROLE_PREVIEW,
    alt_is_catalog_preview,
    alt_is_mockup,
    image_ref_is_mockup,
)

_IMG_SRC_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)


def filename_from_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    tail = raw.rsplit("/", 1)[-1]
    tail = tail.split("?", 1)[0]
    return unquote(tail)


def classify_image_role(*, alt: str, src: str) -> str:
    """Rola grafiki wg altu i nazwy pliku CDN (preview / Full / mockup / inne)."""
    alt_l = (alt or "").lower()
    fn = filename_from_url(src).lower()
    if alt_is_catalog_preview(alt) or "(preview)" in alt_l or "(preview)" in fn:
        return IMAGE_ROLE_PREVIEW
    if alt_is_mockup(alt) or image_ref_is_mockup(src) or image_ref_is_mockup(alt):
        return IMAGE_ROLE_MOCKUP
    if "full" in alt_l or re.search(r"(?:^|[-_. ])full(?:[-_. ]|$)", fn):
        return IMAGE_ROLE_FULL
    return "inne"


def gallery_visible_label(role: str) -> str:
    if role == IMAGE_ROLE_PREVIEW:
        return "nie (ukryte)"
    return "tak"


def load_product_file_info(shop: str, token: str, product_id: int) -> dict[str, Any]:
    """Pelne informacje o grafikach jednego produktu."""
    prod = sc.get_product(shop, token, int(product_id))
    if not prod:
        return {"ok": False, "error": f"Nie znaleziono produktu {product_id}."}

    pid = int(prod.get("id") or product_id)
    handle = (prod.get("handle") or "").strip()
    title = (prod.get("title") or "").strip()
    featured = prod.get("image") or {}
    featured_id = int(featured.get("id") or 0) or None

    variants_by_id: dict[int, str] = {}
    for var in prod.get("variants") or []:
        try:
            vid = int(var.get("id") or 0)
        except (TypeError, ValueError):
            continue
        if not vid:
            continue
        label = (var.get("title") or "").strip() or f"#{vid}"
        variants_by_id[vid] = label

    images = sc.list_product_images(shop, token, pid)
    rows: list[dict[str, Any]] = []
    for im in sorted(images, key=lambda x: int(x.get("position") or 0)):
        img_id = int(im.get("id") or 0)
        src = (im.get("src") or "").strip()
        alt = (im.get("alt") or "").strip()
        role = classify_image_role(alt=alt, src=src)
        variant_ids = [int(v) for v in (im.get("variant_ids") or []) if v]
        variant_labels = [variants_by_id.get(v, f"#{v}") for v in variant_ids]
        rows.append(
            {
                "image_id": img_id,
                "position": int(im.get("position") or 0),
                "filename": filename_from_url(src),
                "alt": alt,
                "role": role,
                "gallery_visible": gallery_visible_label(role),
                "featured": "tak" if featured_id and img_id == featured_id else "",
                "width": im.get("width") or "",
                "height": im.get("height") or "",
                "variant_labels": ", ".join(variant_labels) if variant_labels else "",
                "src": src,
            }
        )

    body_html = (prod.get("body_html") or "").strip()
    body_images: list[dict[str, str]] = []
    for match in _IMG_SRC_RE.finditer(body_html):
        src = (match.group(1) or "").strip()
        if not src:
            continue
        body_images.append(
            {
                "filename": filename_from_url(src),
                "src": src,
                "context": "opis produktu (body_html)",
            }
        )

    return {
        "ok": True,
        "product_id": pid,
        "title": title,
        "handle": handle,
        "admin_url": (
            f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{pid}"
        ),
        "storefront_url": product_storefront_url(handle),
        "featured_image_id": featured_id,
        "featured_filename": filename_from_url((featured.get("src") or "").strip()),
        "image_count": len(rows),
        "gallery_images": rows,
        "body_html_images": body_images,
    }
