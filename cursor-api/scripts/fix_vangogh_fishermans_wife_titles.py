"""Poprawka tytulow: Zona rybaka na plazy (Vincent Van Gogh)."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.body_i18n import BODY_LABELS_I18N, SUPPORTED_LANGS
from Komponenty.dodajobraz.create import build_seo, full_alt_text, preview_alt_text
from Komponenty.dodajobraz.description_update import get_translated_fields
from Komponenty.dodajobraz.html_template import (
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
)

PRODUCT_ID = 15611339669852
ARTIST = "Vincent Van Gogh"
OLD_PL_TITLES = (
    "Żona rybaka na plaży",
)
OLD_ORIGINAL_TITLES = (
    "Vissersvrouw op het strand",
)
OLD_EN_TITLES = (
    "Fisherman's Wife on the Beach",
    "Fisherman's Wife",
)
NEW_PL_TITLE = "Żona rybaka na plaży (lub Żona rybaka (lub Rybaczka na plaży))"
ORIGINAL_TITLE = "Vissersvrouw op het strand (of Vissersvrouw)"
ENGLISH_TITLE = "Fisherman's Wife on the Beach (or Fisherman's Wife)"
LOCALE_TITLES: dict[str, str] = {
    "en": ENGLISH_TITLE,
    "de": "Fischerfrau am Strand (oder Fischerfrau)",
    "fr": "Femme de pêcheur sur la plage (ou Femme de pêcheur)",
    "es": "La mujer del pescador en la playa (o La mujer del pescador)",
    "nl": ORIGINAL_TITLE,
    "it": "La moglie del pescatore sulla spiaggia (o La moglie del pescatore)",
}
ALT_EN_TITLE = "Fisherman's Wife on the Beach"


def _set_detail_value(body_html: str, label: str, value: str) -> str:
    pat = re.compile(
        r"(<strong>\s*" + re.escape(label) + r"\s*:\s*</strong>\s*)([^<]*)",
        re.IGNORECASE,
    )
    if not pat.search(body_html or ""):
        raise ValueError(f"Brak pola «{label}» w body_html.")
    return pat.sub(lambda m: m.group(1) + escape(value, quote=False), body_html, count=1)


def _set_display_title(body_html: str, title: str) -> str:
    pat = re.compile(
        r"(font-size:\s*20px[^>]*>)([^<]+)(</div>)",
        re.IGNORECASE,
    )
    if not pat.search(body_html or ""):
        raise ValueError("Brak naglowka tytulu w body_html.")
    return pat.sub(
        lambda m: m.group(1) + escape(title, quote=False) + m.group(3),
        body_html,
        count=1,
    )


def _replace_titles(body_html: str, old_titles: tuple[str, ...], new_title: str) -> str:
    out = body_html
    for old in old_titles:
        if old in out and old not in new_title:
            out = out.replace(old, new_title)
    return out


def _apply_locale_titles(body_html: str, loc: str) -> str:
    title = LOCALE_TITLES.get(loc, "")
    if not title:
        return body_html
    labels = BODY_LABELS_I18N[loc]
    updated = body_html
    updated = _set_detail_value(updated, labels["tytul_orig"], ORIGINAL_TITLE)
    updated = _set_detail_value(updated, labels["tytul"], title)
    updated = _set_display_title(updated, title)
    return updated


def main() -> int:
    shop, token = sc.load_session()
    gid = sc.product_gid(PRODUCT_ID)

    prod = sc.get_product(shop, token, PRODUCT_ID)
    if not prod.get("id"):
        print(f"Brak produktu id={PRODUCT_ID}")
        return 1

    pl_body = prod.get("body_html") or ""
    pl_body = _replace_titles(pl_body, OLD_PL_TITLES, NEW_PL_TITLE)
    pl_body = _replace_titles(pl_body, OLD_ORIGINAL_TITLES, ORIGINAL_TITLE)
    pl_body = _set_display_title(pl_body, NEW_PL_TITLE)
    pl_body = _set_detail_value(pl_body, BODY_LABELS_I18N["pl"]["tytul"], NEW_PL_TITLE)
    pl_body = _set_detail_value(pl_body, BODY_LABELS_I18N["pl"]["tytul_orig"], ORIGINAL_TITLE)

    new_product_title = f"{ARTIST} - {NEW_PL_TITLE}"
    title_tag, meta_desc, handle = build_seo(
        tytul=NEW_PL_TITLE,
        artysta=ARTIST,
        gatunek="",
        nurt="",
    )

    print(f"Nowy tytul produktu: {new_product_title}")
    print(f"Nowy handle: {handle}")

    sc.update_product(
        shop,
        token,
        PRODUCT_ID,
        {
            "title": new_product_title,
            "handle": handle,
            "body_html": pl_body,
        },
    )
    print("OK: title, handle, body_html PL")

    sc.set_seo_metafields(shop, token, PRODUCT_ID, title_tag=title_tag, description_tag=meta_desc)
    print("OK: SEO metafields")

    for loc in SUPPORTED_LANGS:
        tr = get_translated_fields(shop, token, gid, loc)
        body = tr.get("body_html") or ""
        if not body:
            print(f"POMIN: {loc} — brak tlumaczenia body_html")
            continue
        updated = _replace_titles(body, OLD_ORIGINAL_TITLES, ORIGINAL_TITLE)
        if loc == "en":
            updated = _replace_titles(updated, OLD_EN_TITLES, ENGLISH_TITLE)
        updated = _apply_locale_titles(updated, loc)
        sc.register_translations(
            shop,
            token,
            resource_gid=gid,
            locale=loc,
            fields={"body_html": updated},
        )
        print(f"OK: {loc} — title + original title")

    for img in prod.get("images") or []:
        img_id = int(img.get("id") or 0)
        if not img_id:
            continue
        src = (img.get("src") or "").lower()
        if "(full)" in src or img.get("position") == 1:
            alt = full_alt_text(ARTIST, ALT_EN_TITLE)
        elif "(preview)" in src:
            alt = preview_alt_text(ARTIST, ALT_EN_TITLE)
        elif "(mockup)" in src:
            alt = f"{ARTIST} - {ALT_EN_TITLE} - (mockup)"
        else:
            alt = f"{ARTIST} - {ALT_EN_TITLE}"
        sc.rest_put(
            shop,
            token,
            f"products/{PRODUCT_ID}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )
        print(f"OK: image {img_id} alt")

    prod2 = sc.get_product(shop, token, PRODUCT_ID)
    pl2 = prod2.get("body_html") or ""
    print("\nWeryfikacja:")
    print("  PL tytul:", extract_display_title_from_body_html(pl2))
    print("  PL oryginalny:", extract_original_title_from_body_html(pl2))
    for loc in SUPPORTED_LANGS:
        body = get_translated_fields(shop, token, gid, loc).get("body_html") or ""
        if body:
            print(
                f"  {loc.upper()} tytul:",
                extract_display_title_from_body_html(body),
            )
            print(
                f"  {loc.upper()} oryginalny:",
                extract_original_title_from_body_html(body),
            )
    print(
        f"\nAdmin: https://admin.shopify.com/store/{shop.split('.')[0]}/products/{PRODUCT_ID}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
