"""Poprawka tytulow: Kuter pilotowy nr 3 (Henry King Taylor)."""
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

PRODUCT_ID = 15611318042972
ARTIST = "Henry King Taylor"
OLD_PL_TITLES = (
    "Kuter pilotowy nr 3 z dobijającą łodzią wiosłową i parowcem bocznokołowym w oddali",
)
OLD_EN_TITLES = (
    "Pilot Cutter No. 3 with a Rowing Boat Coming Alongside and a Paddle Steamer in the Distance",
)
NEW_PL_TITLE = "Kuter pilotowy nr 3 z podpływającą łodzią wiosłową"
ORIGINAL_TITLE = "The Dover Pilot Cutter, No 3"
ENGLISH_TITLE = (
    "Pilot cutter no. 3 with a rowing boat coming alongside "
    "and a paddlesteamer in the distance"
)


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


def main() -> int:
    shop, token = sc.load_session()
    gid = sc.product_gid(PRODUCT_ID)

    prod = sc.get_product(shop, token, PRODUCT_ID)
    if not prod.get("id"):
        print(f"Brak produktu id={PRODUCT_ID}")
        return 1

    pl_body = prod.get("body_html") or ""
    for old in OLD_PL_TITLES:
        if old in pl_body:
            pl_body = pl_body.replace(old, NEW_PL_TITLE)
    for old in OLD_EN_TITLES:
        if old in pl_body:
            pl_body = pl_body.replace(old, ORIGINAL_TITLE)
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
        lbl_orig = BODY_LABELS_I18N[loc]["tytul_orig"]
        for old in OLD_EN_TITLES:
            if old in body:
                body = body.replace(old, ORIGINAL_TITLE)
        updated = _set_detail_value(body, lbl_orig, ORIGINAL_TITLE)
        if loc == "en":
            lbl_title = BODY_LABELS_I18N[loc]["tytul"]
            for old in OLD_EN_TITLES:
                if old in updated:
                    updated = updated.replace(old, ENGLISH_TITLE)
            updated = _set_detail_value(updated, lbl_title, ENGLISH_TITLE)
            updated = _set_display_title(updated, ENGLISH_TITLE)
            print("OK: en — Title + Original title")
        else:
            print(f"OK: {loc} — original title")
        sc.register_translations(
            shop,
            token,
            resource_gid=gid,
            locale=loc,
            fields={"body_html": updated},
        )

    for img in prod.get("images") or []:
        img_id = int(img.get("id") or 0)
        if not img_id:
            continue
        src = (img.get("src") or "").lower()
        if "(full)" in src or img.get("position") == 1:
            alt = full_alt_text(ARTIST, ENGLISH_TITLE)
        elif "(preview)" in src:
            alt = preview_alt_text(ARTIST, ENGLISH_TITLE)
        elif "(mockup)" in src:
            alt = f"{ARTIST} - {ENGLISH_TITLE} - (mockup)"
        else:
            alt = f"{ARTIST} - {ENGLISH_TITLE}"
        sc.rest_put(
            shop,
            token,
            f"products/{PRODUCT_ID}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )
        print(f"OK: image {img_id} alt")

    prod2 = sc.get_product(shop, token, PRODUCT_ID)
    pl2 = prod2.get("body_html") or ""
    en2 = get_translated_fields(shop, token, gid, "en").get("body_html") or ""
    print("\nWeryfikacja:")
    print("  PL tytul:", extract_display_title_from_body_html(pl2))
    print("  PL oryginalny:", extract_original_title_from_body_html(pl2))
    print("  EN tytul:", extract_display_title_from_body_html(en2))
    print("  EN oryginalny:", extract_original_title_from_body_html(en2))
    print(
        f"\nAdmin: https://admin.shopify.com/store/{shop.split('.')[0]}/products/{PRODUCT_ID}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
