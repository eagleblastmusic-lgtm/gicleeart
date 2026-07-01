"""Usuwa koncowa kropke z tytulow w SZCZEGOLACH (PL + tlumaczenia) i naglowku EN."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.body_i18n import BODY_LABELS_I18N, SUPPORTED_LANGS
from Komponenty.dodajobraz.create import full_alt_text, preview_alt_text
from Komponenty.dodajobraz.description_update import get_translated_fields
from Komponenty.dodajobraz.html_template import (
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
)

ARTIST = "Vincent Van Gogh"

# product_id -> {en_display?, orig_all?}
FIXES: dict[int, dict[str, str]] = {
    15611353792860: {
        "en_display": "The Good Samaritan (after Delacroix)",
    },
    15611353596252: {
        "orig_all": "De tuin van de inrichting in Saint-Rémy",
    },
}


def _strip_period(s: str) -> str:
    return (s or "").strip().rstrip(".")


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


def _replace_trailing_period_in_body(body: str, old: str, new: str) -> str:
    if old == new or not old:
        return body
    return body.replace(old, new)


def main() -> int:
    shop, token = sc.load_session()

    for product_id, spec in FIXES.items():
        gid = sc.product_gid(product_id)
        prod = sc.get_product(shop, token, product_id)
        if not prod.get("id"):
            print(f"Brak produktu id={product_id}")
            return 1

        pl_body = prod.get("body_html") or ""
        orig_new = spec.get("orig_all")
        if orig_new:
            old_orig = extract_original_title_from_body_html(pl_body)
            if old_orig and _strip_period(old_orig) == orig_new:
                pl_body = _replace_trailing_period_in_body(pl_body, old_orig, orig_new)
                pl_body = _set_detail_value(
                    pl_body, BODY_LABELS_I18N["pl"]["tytul_orig"], orig_new,
                )
                sc.update_product(shop, token, product_id, {"body_html": pl_body})
                print(f"OK: {product_id} PL orig -> {orig_new!r}")

        en_new = spec.get("en_display")
        if en_new:
            tr_en = get_translated_fields(shop, token, gid, "en")
            en_body = tr_en.get("body_html") or ""
            if en_body:
                old_en = extract_display_title_from_body_html(en_body)
                if old_en and _strip_period(old_en) == en_new:
                    en_body = _replace_trailing_period_in_body(en_body, old_en, en_new)
                    en_body = _set_detail_value(
                        en_body, BODY_LABELS_I18N["en"]["tytul"], en_new,
                    )
                    en_body = _set_display_title(en_body, en_new)
                    sc.register_translations(
                        shop,
                        token,
                        resource_gid=gid,
                        locale="en",
                        fields={"body_html": en_body},
                    )
                    print(f"OK: {product_id} EN display -> {en_new!r}")

                    for img in prod.get("images") or []:
                        img_id = int(img.get("id") or 0)
                        if not img_id:
                            continue
                        src = (img.get("src") or "").lower()
                        if "(full)" in src or img.get("position") == 1:
                            alt = full_alt_text(ARTIST, en_new)
                        elif "(preview)" in src:
                            alt = preview_alt_text(ARTIST, en_new)
                        elif "(mockup)" in src:
                            alt = f"{ARTIST} - {en_new} - (mockup)"
                        else:
                            alt = f"{ARTIST} - {en_new}"
                        sc.rest_put(
                            shop,
                            token,
                            f"products/{product_id}/images/{img_id}.json",
                            {"image": {"id": img_id, "alt": alt}},
                        )
                    print(f"OK: {product_id} image alts")

        if orig_new:
            for loc in SUPPORTED_LANGS:
                tr = get_translated_fields(shop, token, gid, loc)
                body = tr.get("body_html") or ""
                if not body:
                    continue
                old = extract_original_title_from_body_html(body)
                if not old or _strip_period(old) != orig_new:
                    continue
                updated = _replace_trailing_period_in_body(body, old, orig_new)
                updated = _set_detail_value(
                    updated, BODY_LABELS_I18N[loc]["tytul_orig"], orig_new,
                )
                sc.register_translations(
                    shop,
                    token,
                    resource_gid=gid,
                    locale=loc,
                    fields={"body_html": updated},
                )
                print(f"OK: {product_id} {loc} orig -> {orig_new!r}")

        pl2 = sc.get_product(shop, token, product_id).get("body_html") or ""
        en2 = get_translated_fields(shop, token, gid, "en").get("body_html") or ""
        print(f"  Weryfikacja {product_id}:")
        print("    PL orig:", repr(extract_original_title_from_body_html(pl2)))
        print("    EN:", repr(extract_display_title_from_body_html(en2)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
