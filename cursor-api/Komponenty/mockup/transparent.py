"""Wersje przezroczyste mockupow w galerii produktu + metafield wyboru wersji."""

from __future__ import annotations

import json
import ssl
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.parser import (
    MOCKUP_DISPLAY_ORIGINAL,
    MOCKUP_DISPLAY_TRANSPARENT,
    alt_is_mockup_transparent,
    image_ref_is_mockup,
    mockup_transparent_alt_text,
    mockup_variant_from_ref,
    parse_filename,
    parse_title_metadata,
)

from .publish import is_image_path

MOCKUP_DISPLAY_NAMESPACE = "custom"
MOCKUP_DISPLAY_KEY = "mockup_display"

Logger = Callable[[str], None] | None


@dataclass(frozen=True)
class ProductMockupImage:
    image_id: int
    position: int
    alt: str
    src: str
    variant: str
    is_transparent: bool
    width: int
    height: int


def _log(logger: Logger, msg: str) -> None:
    if logger:
        logger(msg)


def download_image_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GicleeApp/1.0 (mockup-transparent)"})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=180) as resp:
        return resp.read()


def list_product_mockups(images: list[dict[str, Any]]) -> list[ProductMockupImage]:
    out: list[ProductMockupImage] = []
    for im in sorted(images, key=lambda x: int(x.get("position") or 0)):
        alt = (im.get("alt") or "").strip()
        src = (im.get("src") or "").strip()
        if not image_ref_is_mockup(alt) and not image_ref_is_mockup(src):
            continue
        img_id = int(im.get("id") or 0)
        if not img_id:
            continue
        variant = mockup_variant_from_ref(alt) or mockup_variant_from_ref(src)
        out.append(
            ProductMockupImage(
                image_id=img_id,
                position=int(im.get("position") or 0),
                alt=alt,
                src=src,
                variant=variant,
                is_transparent=alt_is_mockup_transparent(alt) or alt_is_mockup_transparent(src),
                width=int(im.get("width") or 0),
                height=int(im.get("height") or 0),
            )
        )
    return out


def find_mockup_pair(
    mockups: list[ProductMockupImage],
    *,
    source: ProductMockupImage,
) -> tuple[ProductMockupImage | None, ProductMockupImage | None]:
    """Zwraca (oryginal, przezroczysty) dla tego samego wariantu mockupu."""
    variant = source.variant
    original: ProductMockupImage | None = None
    transparent: ProductMockupImage | None = None
    for m in mockups:
        if variant and m.variant != variant:
            continue
        if m.is_transparent:
            transparent = m
        else:
            original = m
    if not variant:
        if source.is_transparent:
            transparent = source
        else:
            original = source
    return original, transparent


def load_mockup_display_prefs(
    shop: str,
    token: str,
    product_id: int,
) -> dict[str, str]:
    mf = sc.find_metafield(shop, token, product_id, namespace=MOCKUP_DISPLAY_NAMESPACE, key=MOCKUP_DISPLAY_KEY)
    raw = (mf or {}).get("value") or ""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for key, val in data.items():
        k = str(key or "").strip().upper()
        v = str(val or "").strip().lower()
        if not k:
            continue
        if v == MOCKUP_DISPLAY_TRANSPARENT:
            out[k] = MOCKUP_DISPLAY_TRANSPARENT
        else:
            out[k] = MOCKUP_DISPLAY_ORIGINAL
    return out


def save_mockup_display_pref(
    shop: str,
    token: str,
    product_id: int,
    *,
    variant: str,
    display: str,
    existing: dict[str, str] | None = None,
    logger: Logger = None,
) -> dict[str, str]:
    prefs = dict(existing or load_mockup_display_prefs(shop, token, product_id))
    vkey = (variant or "").strip().upper() or "DEFAULT"
    display_norm = (
        MOCKUP_DISPLAY_TRANSPARENT
        if (display or "").strip().lower() == MOCKUP_DISPLAY_TRANSPARENT
        else MOCKUP_DISPLAY_ORIGINAL
    )
    prefs[vkey] = display_norm
    payload = json.dumps(prefs, ensure_ascii=False, separators=(",", ":"))
    sc.upsert_metafield(
        shop,
        token,
        product_id,
        namespace=MOCKUP_DISPLAY_NAMESPACE,
        key=MOCKUP_DISPLAY_KEY,
        value=payload,
        ftype="json",
    )
    _log(logger, f"[mockup] Zapisano wyswietlanie {vkey}={display_norm} (produkt {product_id})")
    return prefs


def _parse_artist_title_from_mockup_ref(ref: str) -> tuple[str, str]:
    artist, raw_title = parse_filename(ref)
    base_title, _fnum, _corr, _role, _fkind = parse_title_metadata(raw_title)
    return artist, base_title


def upload_transparent_mockup_file(
    *,
    product_id: int,
    source: ProductMockupImage,
    file_path: Path,
    replace_existing: bool = False,
    display_prefs: dict[str, str] | None = None,
    logger: Logger = None,
) -> dict[str, Any]:
    """Dogrywa recznie wybrany plik jako przezroczysta wersje mockupu."""
    if source.is_transparent:
        raise ValueError("Zaznacz oryginalny mockup (nie wersje przezroczysta).")
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku: {path}")
    if not is_image_path(path):
        raise ValueError(f"Nieobslugiwany format pliku: {path.suffix}")

    shop, token = sc.load_session()
    images = sc.list_product_images(shop, token, int(product_id))
    mockups = list_product_mockups(images)
    _original, transparent = find_mockup_pair(mockups, source=source)

    prefs = dict(display_prefs or load_mockup_display_prefs(shop, token, product_id))
    if transparent and not replace_existing:
        return {
            "skipped": True,
            "product_id": int(product_id),
            "reason": f"Wersja przezroczysta ({source.variant or 'mockup'}) juz istnieje",
        }

    if transparent and replace_existing:
        prefs = delete_product_mockup(
            shop,
            token,
            product_id,
            transparent,
            display_prefs=prefs,
            logger=logger,
        )

    artist, base_title = _parse_artist_title_from_mockup_ref(source.alt or source.src)
    alt = mockup_transparent_alt_text(artist, base_title, name_suffix=source.variant)
    _log(logger, f"[mockup] Dogrywam przezroczysty mockup z dysku: {path.name} -> {alt}")
    img = sc.upload_image(shop, token, int(product_id), path, alt=alt, logger=logger)
    return {
        "product_id": int(product_id),
        "image_id": img.get("id"),
        "alt": alt,
        "variant": source.variant,
        "source_file": str(path),
        "mode": "mockup_transparent_upload",
        "display_prefs": prefs,
    }


def delete_product_mockup(
    shop: str,
    token: str,
    product_id: int,
    mockup: ProductMockupImage,
    *,
    display_prefs: dict[str, str] | None = None,
    logger: Logger = None,
) -> dict[str, str]:
    """Usuwa zdjecie mockupu z galerii produktu."""
    sc.delete_product_image(shop, token, int(product_id), int(mockup.image_id))
    _log(logger, f"[mockup] Usunieto mockup id={mockup.image_id} (produkt {product_id})")

    prefs = dict(display_prefs or {})
    variant = (mockup.variant or "").strip().upper()
    if variant and mockup.is_transparent and prefs.get(variant) == MOCKUP_DISPLAY_TRANSPARENT:
        prefs = save_mockup_display_pref(
            shop,
            token,
            product_id,
            variant=variant,
            display=MOCKUP_DISPLAY_ORIGINAL,
            existing=prefs,
            logger=logger,
        )
    return prefs
