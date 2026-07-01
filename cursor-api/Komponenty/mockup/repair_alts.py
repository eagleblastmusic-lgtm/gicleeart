"""Naprawa altow zdjec mockup w Shopify (gdy plik CDN ma mockup, a alt stracił «(mockup)»)."""

from __future__ import annotations

from collections.abc import Callable

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import PRODUCT_TYPE
from Komponenty.dodajobraz.parser import (
    alt_is_mockup,
    image_ref_is_mockup,
    mockup_alt_text,
    mockup_suffixes_in_image_refs,
    parse_title_metadata,
)

from .audit import parse_product_title

Logger = Callable[[str], None] | None


def _en_title_from_alt(alt: str) -> tuple[str, str]:
    """Z altu «Artysta - Tytul (Full)» zwraca (artysta, tytul_en)."""
    text = (alt or "").strip()
    if " - " not in text:
        return "", text
    artist, raw = text.split(" - ", 1)
    base, *_ = parse_title_metadata(raw)
    return artist.strip(), (base or raw).strip()


def repair_mockup_alts_for_product(
    shop: str,
    token: str,
    product_id: int,
    *,
    artist: str | None = None,
    logger: Logger = None,
    dry_run: bool = False,
) -> int:
    """Przywraca alt «Artysta - Tytul - (mockup) - CZB/CZCZ» wg URL pliku. Zwraca liczbe poprawek."""
    if not artist:
        prod = sc.get_product(shop, token, int(product_id))
        parsed = parse_product_title(str(prod.get("title") or ""))
        if parsed:
            artist = parsed[0]

    images = sc.list_product_images(shop, token, int(product_id))
    fixed = 0
    for im in images:
        img_id = int(im.get("id") or 0)
        if not img_id:
            continue
        alt = (im.get("alt") or "").strip()
        src = im.get("src") or ""
        if not image_ref_is_mockup(src) and not image_ref_is_mockup(alt):
            continue

        suffixes = mockup_suffixes_in_image_refs([alt, src])
        sfx = "CZCZ" if "CZCZ" in suffixes else ("CZB" if "CZB" in suffixes else "")

        alt_artist, en_title = _en_title_from_alt(alt)
        use_artist = (artist or alt_artist or "").strip()
        if not use_artist or not en_title:
            if logger:
                logger(f"[mockup alt] Pomijam image {img_id} — brak artysty/tytulu w alcie.")
            continue

        new_alt = mockup_alt_text(use_artist, en_title, name_suffix=sfx)
        if alt == new_alt or (alt_is_mockup(alt) and sfx and sfx in alt.upper()):
            continue

        if logger:
            logger(f"[mockup alt] pid={product_id} image={img_id}: naprawiam alt mockupu ({sfx or '?'})")

        if not dry_run:
            sc.rest_put(
                shop,
                token,
                f"products/{product_id}/images/{img_id}.json",
                {"image": {"id": img_id, "alt": new_alt}},
            )
        fixed += 1
    return fixed


def repair_all_mockup_alts(
    *,
    product_type: str | None = PRODUCT_TYPE,
    logger: Logger = None,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Naprawia alt mockupow we wszystkich produktach typu Obraz. Zwraca (produkty, zdjecia)."""
    shop, token = sc.load_session()
    products_fixed = 0
    images_fixed = 0
    for prod in sc.iter_all_products(shop, token, product_type=product_type, fields="id,title"):
        parsed = parse_product_title(str(prod.get("title") or ""))
        if not parsed:
            continue
        pid = int(prod.get("id") or 0)
        if not pid:
            continue
        artist, _ = parsed
        n = repair_mockup_alts_for_product(
            shop, token, pid, artist=artist, logger=logger, dry_run=dry_run,
        )
        if n:
            products_fixed += 1
            images_fixed += n
    return products_fixed, images_fixed
