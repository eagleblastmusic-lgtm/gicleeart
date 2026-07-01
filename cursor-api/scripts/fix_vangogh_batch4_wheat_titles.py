"""Poprawka tytulow: 4 produkty Van Gogh — pola pszenicy i podszycie (batch)."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path
from typing import TypedDict

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

ARTIST = "Vincent Van Gogh"


class ProductTitles(TypedDict):
    product_id: int
    label: str
    old_pl_titles: tuple[str, ...]
    new_pl_title: str
    original_title: str
    english_title: str
    locale_titles: dict[str, str]
    alt_en_title: str


PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15611359494492,
        "label": "Pole pszenicy z krukami",
        "old_pl_titles": ("Pole pszenicy z krukami",),
        "new_pl_title": "Pole pszenicy z krukami (lub Pole pszenicy z wronami)",
        "original_title": "Korenveld met kraaien",
        "english_title": "Wheatfield with Crows (or Wheat Field with Crows)",
        "locale_titles": {
            "en": "Wheatfield with Crows (or Wheat Field with Crows)",
            "de": "Weizenfeld mit Krähen",
            "fr": "Champ de blé aux corbeaux",
            "es": "Trigal con cuervos (o Campo de trigo con cuervos)",
            "nl": "Korenveld met kraaien",
            "it": "Campo di grano con corvi",
        },
        "alt_en_title": "Wheatfield with Crows",
    },
    {
        "product_id": 15611358871900,
        "label": "Pole pszenicy z chabrami",
        "old_pl_titles": ("Pole pszenicy z chabrami",),
        "new_pl_title": "Pole pszenicy z chabrami (lub Pole pszenicy z bławatkami)",
        "original_title": "Champ de blé aux bleuets",
        "english_title": "Wheat Field with Cornflowers (or Wheatfield with Cornflowers)",
        "locale_titles": {
            "en": "Wheat Field with Cornflowers (or Wheatfield with Cornflowers)",
            "de": "Weizenfeld mit Kornblumen",
            "es": "Campo de trigo con acianos",
            "nl": "Korenveld met korebloemen",
            "it": "Campo di grano con fiordalisi",
        },
        "alt_en_title": "Wheat Field with Cornflowers",
    },
    {
        "product_id": 15611358609756,
        "label": "Pola pszenicy ze zniwiarzem",
        "old_pl_titles": (
            "Pola pszenicy ze żniwiarzem, Auvers",
            "Pola pszenicy ze żniwiarzem",
        ),
        "new_pl_title": (
            "Pola pszenicy ze żniwiarzem i stogami "
            "(lub Pola pszenicy ze żniwiarzem)"
        ),
        "original_title": (
            "Champs de blé avec moissonneur et meules (of Les moissonneurs)"
        ),
        "english_title": "Wheat Fields with Reaper (or Wheat Fields with Sheaves)",
        "locale_titles": {
            "en": "Wheat Fields with Reaper (or Wheat Fields with Sheaves)",
            "de": "Weizenfelder mit Schnitter und Korngarben",
            "es": "Campos de trigo con segador y almiares",
            "nl": "Korenvelden met maaier en korenmijten",
            "it": "Campi di grano con mietitore e covoni",
        },
        "alt_en_title": "Wheat Fields with Reaper",
    },
    {
        "product_id": 15611358216540,
        "label": "Podszycie lesne z dwojgiem ludzi",
        "old_pl_titles": (
            "Podszycie leśne z dwojgiem ludzi",
            "Poszycie leśne z dwiema postaciami",
        ),
        "new_pl_title": (
            "Podszycie leśne z dwojgiem ludzi "
            "(lub Podszyt z dwiema postaciami/Dwoje ludzi w lesie)"
        ),
        "original_title": "Kreupelhout met twee figuren (of Onderhout met twee figuren)",
        "english_title": (
            "Undergrowth with Two Figures "
            "(or Undergrowth with Two Figures in Landscape)"
        ),
        "locale_titles": {
            "en": (
                "Undergrowth with Two Figures "
                "(or Undergrowth with Two Figures in Landscape)"
            ),
            "de": "Unterholz mit zwei Figuren (oder Unterholz mit Liebespaar)",
            "fr": "Sous-bois avec deux figures (ou Sous-bois avec deux personnages)",
            "es": "Sotobosque con dos figuras (o Maleza con dos figuras)",
            "nl": "Kreupelhout met twee figuren (of Onderhout met twee figuren)",
            "it": "Sottobosco con due figure",
        },
        "alt_en_title": "Undergrowth with Two Figures",
    },
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


def _replace_titles(body_html: str, old_titles: tuple[str, ...], new_title: str) -> str:
    out = body_html
    for old in old_titles:
        if old in out and old not in new_title:
            out = out.replace(old, new_title)
    return out


def _apply_locale_titles(
    body_html: str,
    loc: str,
    *,
    original_title: str,
    locale_titles: dict[str, str],
) -> str:
    title = locale_titles.get(loc, "")
    if not title:
        return body_html
    labels = BODY_LABELS_I18N[loc]
    updated = body_html
    updated = _set_detail_value(updated, labels["tytul_orig"], original_title)
    updated = _set_detail_value(updated, labels["tytul"], title)
    updated = _set_display_title(updated, title)
    return updated


def _apply_product(shop: str, token: str, cfg: ProductTitles) -> None:
    pid = cfg["product_id"]
    gid = sc.product_gid(pid)
    print(f"\n=== {cfg['label']} (id={pid}) ===")

    prod = sc.get_product(shop, token, pid)
    if not prod.get("id"):
        raise RuntimeError(f"Brak produktu id={pid}")

    pl_body = prod.get("body_html") or ""
    pl_body = _replace_titles(pl_body, cfg["old_pl_titles"], cfg["new_pl_title"])
    pl_body = _set_display_title(pl_body, cfg["new_pl_title"])
    pl_body = _set_detail_value(
        pl_body, BODY_LABELS_I18N["pl"]["tytul"], cfg["new_pl_title"],
    )
    pl_body = _set_detail_value(
        pl_body, BODY_LABELS_I18N["pl"]["tytul_orig"], cfg["original_title"],
    )

    new_product_title = f"{ARTIST} - {cfg['new_pl_title']}"
    title_tag, meta_desc, handle = build_seo(
        tytul=cfg["new_pl_title"],
        artysta=ARTIST,
        gatunek="",
        nurt="",
    )
    print(f"  tytul: {new_product_title}")
    print(f"  handle: {handle}")

    sc.update_product(
        shop,
        token,
        pid,
        {"title": new_product_title, "handle": handle, "body_html": pl_body},
    )
    sc.set_seo_metafields(shop, token, pid, title_tag=title_tag, description_tag=meta_desc)

    for loc in SUPPORTED_LANGS:
        tr = get_translated_fields(shop, token, gid, loc)
        body = tr.get("body_html") or ""
        if not body:
            print(f"  POMIN: {loc}")
            continue
        updated = _apply_locale_titles(
            body,
            loc,
            original_title=cfg["original_title"],
            locale_titles=cfg["locale_titles"],
        )
        sc.register_translations(
            shop, token, resource_gid=gid, locale=loc, fields={"body_html": updated},
        )

    alt_en = cfg["alt_en_title"]
    for img in prod.get("images") or []:
        img_id = int(img.get("id") or 0)
        if not img_id:
            continue
        src = (img.get("src") or "").lower()
        if "(full)" in src or img.get("position") == 1:
            alt = full_alt_text(ARTIST, alt_en)
        elif "(preview)" in src:
            alt = preview_alt_text(ARTIST, alt_en)
        elif "(mockup)" in src:
            alt = f"{ARTIST} - {alt_en} - (mockup)"
        else:
            alt = f"{ARTIST} - {alt_en}"
        sc.rest_put(
            shop,
            token,
            f"products/{pid}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )

    pl2 = sc.get_product(shop, token, pid).get("body_html") or ""
    print(f"  PL: {extract_display_title_from_body_html(pl2)}")
    print(f"  orig: {extract_original_title_from_body_html(pl2)}")


def main() -> int:
    shop, token = sc.load_session()
    for cfg in PRODUCTS:
        _apply_product(shop, token, cfg)
    print("\nGotowe — 4 produkty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
