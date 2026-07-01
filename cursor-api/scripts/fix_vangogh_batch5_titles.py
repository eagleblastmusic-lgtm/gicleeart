"""Poprawka tytulow: 5 produktow Van Gogh (batch)."""
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
        "product_id": 15611352645980,
        "label": "Sloneczniki",
        "old_pl_titles": ("Słoneczniki",),
        "new_pl_title": "Słoneczniki (lub Wazon z piętnastoma słonecznikami)",
        "original_title": "Zonnebloemen (of Vaas met vijftien zonnebloemen)",
        "english_title": "Sunflowers (or Vase with Fifteen Sunflowers)",
        "locale_titles": {
            "en": "Sunflowers (or Vase with Fifteen Sunflowers)",
            "de": "Sonnenblumen (oder Vase mit fünfzehn Sonnenblumen)",
            "fr": "Tournesols (ou Vase avec quinze tournesols)",
            "es": "Los girasoles (o Jarrón con quince girasoles)",
            "nl": "Zonnebloemen (of Vaas met vijftien zonnebloemen)",
            "it": "Girasoli (o Vaso con quindici girasoli)",
        },
        "alt_en_title": "Sunflowers",
    },
    {
        "product_id": 15611354775900,
        "label": "Roze drzewo brzoskwiniowe",
        "old_pl_titles": (
            "Różowe drzewo brzoskwiniowe (Souvenir de Mauve)",
            "Różowe drzewo brzoskwiniowe",
        ),
        "new_pl_title": "Różowe drzewo brzoskwiniowe (lub Różowa brzoskwinia)",
        "original_title": "De roze perzikboom (of Roze perzikboom)",
        "english_title": "The Pink Peach Tree (or Peach Tree in Blossom)",
        "locale_titles": {
            "en": "The Pink Peach Tree (or Peach Tree in Blossom)",
            "de": "Der rosa Pfirsichbaum (oder Blühender Pfirsichbaum)",
            "fr": "Le pêcher rose (ou Pêcher en fleurs)",
            "es": "El melocotonero rosa (o Melocotonero en flor)",
            "nl": "De roze perzikboom (of Roze perzikboom)",
            "it": "Il pesco rosa (o Pesco in fiore)",
        },
        "alt_en_title": "The Pink Peach Tree",
    },
    {
        "product_id": 15611348091228,
        "label": "Roze i piwonie",
        "old_pl_titles": (
            "Róże i piwonie",
        ),
        "new_pl_title": (
            "Róże i piwonie (lub Czara z piwoniami i różami/Wazon z różami i piwoniami)"
        ),
        "original_title": "Rozen en pioenrozen (of Kom met pioenrozen en rozen)",
        "english_title": "Roses and Peonies (or Bowl with Peonies and Roses)",
        "locale_titles": {
            "en": "Roses and Peonies (or Bowl with Peonies and Roses)",
            "de": "Rosen und Pfingstrosen",
            "fr": "Roses et pivoines",
            "es": "Rosas y peonías",
            "nl": "Rozen en pioenrozen (of Kom met pioenrozen en rozen)",
            "it": "Rose e peonie",
        },
        "alt_en_title": "Roses and Peonies",
    },
    {
        "product_id": 15611347730780,
        "label": "Roses",
        "old_pl_titles": (
            "Roses",
            "Róże",
            "Wazon z różami",
        ),
        "new_pl_title": "Wazon z różami (lub Róże)",
        "original_title": "Vaas met rozen (of Rozen)",
        "english_title": "Vase with Roses (or Roses)",
        "locale_titles": {
            "en": "Vase with Roses (or Roses)",
            "de": "Vase mit Rosen (oder Rosen)",
            "fr": "Vase avec roses (ou Les roses)",
            "es": "Jarrón con rosas (o Rosas)",
            "nl": "Vaas met rozen (of Rozen)",
            "it": "Vaso con rose (o Rose)",
        },
        "alt_en_title": "Vase with Roses",
    },
    {
        "product_id": 15611347370332,
        "label": "Portret Josepha Roulina",
        "old_pl_titles": (
            "Portret Josepha Roulina",
            "Portret Joseph Roulina",
        ),
        "new_pl_title": (
            "Portret listonosza Józefa Roulina na tle kwiatów "
            "(lub Listonosz Joseph Roulin (wersja nowojorska))"
        ),
        "original_title": (
            "Portrait de Joseph Roulin (fond fleuri) "
            "(of Le Facteur Joseph Roulin (MoMA))"
        ),
        "english_title": (
            "Portrait of Joseph Roulin (with Floral Background) "
            "(of The Postman Joseph Roulin (MoMA))"
        ),
        "locale_titles": {
            "en": (
                "Portrait of Joseph Roulin (with Floral Background) "
                "(of The Postman Joseph Roulin (MoMA))"
            ),
            "de": "Porträt des Postboten Joseph Roulin vor blumigen Hintergrund",
            "es": "Retrato de Joseph Roulin con fondo floral",
            "nl": "Portret van Joseph Roulin met bloemenachtergrond",
            "it": "Ritratto di Joseph Roulin con sfondo floreale",
        },
        "alt_en_title": "Portrait of Joseph Roulin (with Floral Background)",
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
    print("\nGotowe — 5 produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
