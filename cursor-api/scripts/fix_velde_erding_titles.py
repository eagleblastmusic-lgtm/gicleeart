"""Poprawka tytulow: Holenderskie statki na spokojnym morzu (Willem Velde)."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.body_i18n import BODY_LABELS_I18N, SUPPORTED_LANGS
from Komponenty.dodajobraz.description_update import get_translated_fields
from Komponenty.dodajobraz.html_template import (
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
)

PRODUCT_ID = 15611428045148
ORIGINAL_TITLE = "Hollandse schepen op een kalme zee"
ENGLISH_TITLE = "Dutch Ships in a Calm Sea"
def _set_detail_value(body_html: str, label: str, value: str) -> str:
    pat = re.compile(
        r"(<strong>\s*" + re.escape(label) + r"\s*:\s*</strong>\s*)([^<]*)",
        re.IGNORECASE,
    )
    if not pat.search(body_html or ""):
        raise ValueError(f"Brak pola «{label}» w body_html.")
    return pat.sub(lambda m: m.group(1) + escape(value, quote=False), body_html, count=1)


def main() -> int:
    shop, token = sc.load_session()
    gid = sc.product_gid(PRODUCT_ID)

    prod = sc.get_product(shop, token, PRODUCT_ID)
    if not prod.get("id"):
        print(f"Brak produktu id={PRODUCT_ID}")
        return 1

    pl_body = prod.get("body_html") or ""
    pl_label = BODY_LABELS_I18N["pl"]["tytul_orig"]
    new_pl = _set_detail_value(pl_body, pl_label, ORIGINAL_TITLE)
    sc.update_product(shop, token, PRODUCT_ID, {"body_html": new_pl})
    print("OK: PL body_html — tytul oryginalny")

    for loc in SUPPORTED_LANGS:
        tr = get_translated_fields(shop, token, gid, loc)
        body = tr.get("body_html") or ""
        if not body:
            print(f"POMIN: {loc} — brak tlumaczenia body_html")
            continue
        lbl_orig = BODY_LABELS_I18N[loc]["tytul_orig"]
        lbl_title = BODY_LABELS_I18N[loc]["tytul"]
        updated = _set_detail_value(body, lbl_orig, ORIGINAL_TITLE)
        if loc == "en":
            updated = _set_detail_value(updated, lbl_title, ENGLISH_TITLE)
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

    prod2 = sc.get_product(shop, token, PRODUCT_ID)
    pl2 = prod2.get("body_html") or ""
    en2 = get_translated_fields(shop, token, gid, "en").get("body_html") or ""
    print("\nWeryfikacja:")
    print("  PL oryginalny:", extract_original_title_from_body_html(pl2))
    print("  EN tytul:", extract_display_title_from_body_html(en2))
    print("  EN oryginalny:", extract_original_title_from_body_html(en2))
    print(
        f"\nAdmin: https://admin.shopify.com/store/{shop.split('.')[0]}/products/{PRODUCT_ID}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
