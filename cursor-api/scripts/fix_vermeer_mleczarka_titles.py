"""Poprawka tytulow: Mleczarka (Johannes Vermeer)."""
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
from Komponenty.dodajobraz.description_update import (
    format_title_alternative_parenthetical,
    get_translated_fields,
)
from Komponenty.dodajobraz.html_template import (
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
)

PRODUCT_ID = 15611529101660
ARTIST = "Johannes Vermeer"
OLD_PL_TITLES = ("Mleczarka",)
NEW_PL_TITLE = format_title_alternative_parenthetical(
    "Mleczarka (lub Dziewczyna z dzbanem mleka)",
    "pl",
)
ORIGINAL_TITLE = "Het melkmeisje (of De melkmeid)"
ENGLISH_TITLE = "The Milkmaid"
LOCALE_TITLES: dict[str, str] = {
    "en": ENGLISH_TITLE,
    "de": format_title_alternative_parenthetical(
        "Dienstmädchen mit Milchkrug (oder Die Milchmagd)",
        "de",
    ),
    "fr": "La Laitière",
    "es": "La lechera",
    "nl": ORIGINAL_TITLE,
    "it": format_title_alternative_parenthetical(
        "Lattaia (o La merlettaia)",
        "it",
    ),
}


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


def _apply_locale_titles(body_html: str, loc: str) -> str:
    title = LOCALE_TITLES.get(loc, "")
    if not title:
        return body_html
    labels = BODY_LABELS_I18N[loc]
    updated = body_html
    for old_orig in ("Het melkmeisje", ORIGINAL_TITLE):
        if old_orig in updated and old_orig != ORIGINAL_TITLE:
            updated = updated.replace(old_orig, ORIGINAL_TITLE)
    updated = _set_detail_value(updated, labels["tytul_orig"], ORIGINAL_TITLE)
    updated = _set_detail_value(updated, labels["tytul"], title)
    updated = _set_display_title(updated, title)
    return updated


def _snapshot(shop: str, token: str, gid: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    prod = sc.get_product(shop, token, PRODUCT_ID)
    pl = prod.get("body_html") or ""
    out["product"] = {
        "title": (prod.get("title") or "").strip(),
        "handle": (prod.get("handle") or "").strip(),
    }
    out["pl"] = {
        "display": extract_display_title_from_body_html(pl),
        "original": extract_original_title_from_body_html(pl),
    }
    for loc in SUPPORTED_LANGS:
        body = get_translated_fields(shop, token, gid, loc).get("body_html") or ""
        if body:
            out[loc] = {
                "display": extract_display_title_from_body_html(body),
                "original": extract_original_title_from_body_html(body),
            }
    return out


def _print_changes(before: dict, after: dict) -> None:
    print("\n=== Co sie zmienilo ===")
    changed = False
    for key in ("product", "pl", *SUPPORTED_LANGS):
        b = before.get(key) or {}
        a = after.get(key) or {}
        if key == "product":
            for field in ("title", "handle"):
                if b.get(field) != a.get(field):
                    print(f"  {field}: {b.get(field)!r} -> {a.get(field)!r}")
                    changed = True
        else:
            for field in ("display", "original"):
                bk = f"PL {field}" if key == "pl" else f"{key.upper()} {field}"
                if b.get(field) != a.get(field):
                    print(f"  {bk}: {b.get(field)!r} -> {a.get(field)!r}")
                    changed = True
    if not changed:
        print("  (brak zmian — tytuly juz zgodne ze specyfikacja)")


def main() -> int:
    shop, token = sc.load_session()
    gid = sc.product_gid(PRODUCT_ID)
    before = _snapshot(shop, token, gid)

    prod = sc.get_product(shop, token, PRODUCT_ID)
    if not prod.get("id"):
        print(f"Brak produktu id={PRODUCT_ID}")
        return 1

    pl_body = prod.get("body_html") or ""
    for old in OLD_PL_TITLES:
        if old in pl_body and old != NEW_PL_TITLE and old not in NEW_PL_TITLE:
            pl_body = pl_body.replace(old, NEW_PL_TITLE)
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
    sc.set_seo_metafields(shop, token, PRODUCT_ID, title_tag=title_tag, description_tag=meta_desc)

    for loc in SUPPORTED_LANGS:
        tr = get_translated_fields(shop, token, gid, loc)
        body = tr.get("body_html") or ""
        if not body:
            continue
        updated = _apply_locale_titles(body, loc)
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

    after = _snapshot(shop, token, gid)
    _print_changes(before, after)
    print(
        f"\nAdmin: https://admin.shopify.com/store/{shop.split('.')[0]}/products/{PRODUCT_ID}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
