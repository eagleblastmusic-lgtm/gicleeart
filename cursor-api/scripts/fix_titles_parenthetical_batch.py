"""Batch: poprawka tytulow z gołym «lub» u produktow ze skryptow fix_*_titles.py."""
from __future__ import annotations

import importlib.util
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
    get_translated_fields,
    normalize_title_alternatives,
    title_needs_lub_paren_fix,
)
from Komponenty.dodajobraz.html_template import (
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
)

_LANG_KEYS = {"pl": "pl", "en": "en", "de": "de", "fr": "fr", "es": "es", "nl": "nl", "it": "it"}


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


def _normalize_field(value: str, lang_key: str) -> str:
    return normalize_title_alternatives(value, lang_key)


def _apply_body_title_fixes(body_html: str, lang_key: str) -> tuple[str, bool]:
    labels = BODY_LABELS_I18N[lang_key]

    updated = body_html
    changed = False

    display = extract_display_title_from_body_html(body_html)
    new_display = _normalize_field(display, lang_key if lang_key != "orig" else "orig")
    if new_display != display:
        updated = _set_display_title(updated, new_display)
        changed = True

    for field_key in ("tytul", "tytul_orig"):
        label = labels[field_key]
        pat = re.compile(
            r"(<strong>\s*" + re.escape(label) + r"\s*:\s*</strong>\s*)([^<]*)",
            re.IGNORECASE,
        )
        m = pat.search(updated or "")
        if not m:
            continue
        old_val = m.group(2).strip()
        lk = "orig" if field_key == "tytul_orig" else lang_key
        new_val = _normalize_field(old_val, lk)
        if new_val != old_val:
            updated = _set_detail_value(updated, label, new_val)
            changed = True

    return updated, changed


def _collect_product_ids() -> list[int]:
    scripts_dir = Path(__file__).resolve().parent
    ids: set[int] = set()
    for script in sorted(scripts_dir.glob("fix_*_titles.py")):
        spec = importlib.util.spec_from_file_location(script.stem, script)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pid = int(getattr(mod, "PRODUCT_ID", 0) or 0)
        if pid:
            ids.add(pid)
    return sorted(ids)


def _artist_from_product_title(title: str) -> str:
    if " - " in title:
        return title.split(" - ", 1)[0].strip()
    return ""


def main() -> int:
    shop, token = sc.load_session()
    product_ids = _collect_product_ids()
    print(f"Produkty do sprawdzenia: {len(product_ids)}")

    touched = 0
    for product_id in product_ids:
        prod = sc.get_product(shop, token, product_id)
        if not prod.get("id"):
            print(f"POMIN id={product_id} — brak produktu")
            continue
        gid = sc.product_gid(product_id)
        artist = _artist_from_product_title(prod.get("title") or "")

        pl_body = prod.get("body_html") or ""
        pl_new, pl_changed = _apply_body_title_fixes(pl_body, "pl")
        any_changed = pl_changed

        locale_updates: dict[str, str] = {}
        for loc in SUPPORTED_LANGS:
            tr = get_translated_fields(shop, token, gid, loc)
            body = tr.get("body_html") or ""
            if not body:
                continue
            lk = _LANG_KEYS[loc]
            body_new, loc_changed = _apply_body_title_fixes(body, lk)
            if loc_changed:
                locale_updates[loc] = body_new
                any_changed = True

        if not any_changed:
            continue

        pl_display = extract_display_title_from_body_html(pl_new)
        en_body = locale_updates.get("en") or get_translated_fields(
            shop, token, gid, "en"
        ).get("body_html") or ""
        en_display = extract_display_title_from_body_html(en_body) if en_body else ""

        print(f"\n=== id={product_id} ===")
        if pl_changed:
            old_display = extract_display_title_from_body_html(pl_body)
            print(f"  PL: {old_display!r}")
            print(f"   -> {pl_display!r}")

        new_product_title = f"{artist} - {pl_display}" if artist else pl_display
        fields: dict = {"body_html": pl_new}
        if new_product_title != (prod.get("title") or ""):
            fields["title"] = new_product_title
            if artist:
                title_tag, meta_desc, handle = build_seo(
                    tytul=pl_display,
                    artysta=artist,
                    gatunek="",
                    nurt="",
                )
                fields["handle"] = handle
                sc.set_seo_metafields(
                    shop, token, product_id, title_tag=title_tag, description_tag=meta_desc
                )

        sc.update_product(shop, token, product_id, fields)
        print("  OK: PL body" + (" + title/handle" if "title" in fields else ""))

        for loc, body_new in locale_updates.items():
            sc.register_translations(
                shop,
                token,
                resource_gid=gid,
                locale=loc,
                fields={"body_html": body_new},
            )
            disp = extract_display_title_from_body_html(body_new)
            print(f"  OK: {loc} -> {disp!r}")

        if en_display:
            for img in prod.get("images") or []:
                img_id = int(img.get("id") or 0)
                if not img_id:
                    continue
                src = (img.get("src") or "").lower()
                if "(full)" in src or img.get("position") == 1:
                    alt = full_alt_text(artist, en_display)
                elif "(preview)" in src:
                    alt = preview_alt_text(artist, en_display)
                elif "(mockup)" in src:
                    alt = f"{artist} - {en_display} - (mockup)"
                else:
                    alt = f"{artist} - {en_display}"
                sc.rest_put(
                    shop,
                    token,
                    f"products/{product_id}/images/{img_id}.json",
                    {"image": {"id": img_id, "alt": alt}},
                )

        touched += 1

    print(f"\nGotowe: zaktualizowano {touched} produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
