"""Poprawka tytulow: 5 produktow — Richards, Ribera, Potter (batch 10)."""
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
from Komponenty.dodajobraz.html_template import extract_display_title_from_body_html


class ProductTitles(TypedDict):
    product_id: int
    artist: str
    label: str
    old_pl_titles: tuple[str, ...]
    new_pl_title: str
    original_title: str
    english_title: str
    locale_titles: dict[str, str]
    alt_en_title: str


PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15611429355868,
        "artist": "William Trost Richards",
        "label": "Zatoka Donegal",
        "old_pl_titles": ("Zatoka Donegal",),
        "new_pl_title": "Zatoka Donegal (lub Klify Donegal)",
        "original_title": "Donegal Bay (of Cliffs of Donegal)",
        "english_title": "Donegal Bay (or Cliffs of Donegal)",
        "locale_titles": {
            "en": "Donegal Bay (or Cliffs of Donegal)",
            "de": "Die Bucht von Donegal (oder Klippen von Donegal)",
            "fr": "La baie de Donegal (ou Falaises de Donegal)",
            "es": "La bahía de Donegal (o Acantilados de Donegal)",
            "nl": "Donegal Bay (of Cliffs of Donegal)",
            "it": "La baia di Donegal (o Scogliere di Donegal)",
        },
        "alt_en_title": "Donegal Bay",
    },
    {
        "product_id": 15611428897116,
        "artist": "William Trost Richards",
        "label": "Skaliste wybrzeze",
        "old_pl_titles": ("Skaliste wybrzeże",),
        "new_pl_title": (
            "Skaliste wybrzeże "
            "(lub Skaliste wybrzeże (z Metropolitan Museum of Art))"
        ),
        "original_title": "A Rocky Coast (of A Rocky Coast (Metropolitan Museum of Art))",
        "english_title": "A Rocky Coast (or A Rocky Coast (Metropolitan Museum of Art))",
        "locale_titles": {
            "en": "A Rocky Coast (or A Rocky Coast (Metropolitan Museum of Art))",
            "de": "Eine felsige Küste (oder Felsige Küste)",
            "fr": "Une côte rocheuse (ou Côte rocheuse)",
            "es": "Una costa rocosa (o Costa rocosa)",
            "nl": "A Rocky Coast (of A Rocky Coast (Metropolitan Museum of Art))",
            "it": "Una costa rocciosa (o Costa rocciosa)",
        },
        "alt_en_title": "A Rocky Coast",
    },
    {
        "product_id": 15611533033820,
        "artist": "Jusepe Ribera",
        "label": "Swieta Rodzina Ribera",
        "old_pl_titles": (
            "Święta Rodzina ze świętą Anną i świętą Katarzyną Aleksandryjską",
            "Święta Rodzina ze świętymi Anną i Katarzyną Aleksandryjską",
        ),
        "new_pl_title": (
            "Święta Rodzina ze świętymi Anną i Katarzyną Aleksandryjską "
            "(lub Mistyczne zaślubiny świętej Katarzyny/"
            "Święta Rodzina ze św. Anną i Katarzyną Aleksandryjską (z Metropolitan Museum of Art))"
        ),
        "original_title": (
            "La Sagrada Familia con Santa Ana y Santa Catalina de Alejandría "
            "(of Los desposorios místicos de Santa Catalina de Alejandría "
            "con la Sagrada Familia)"
        ),
        "english_title": (
            "The Holy Family with Saints Anne and Catherine of Alexandria "
            "(or Mystical Marriage of Saint Catherine of Alexandria)"
        ),
        "locale_titles": {
            "en": (
                "The Holy Family with Saints Anne and Catherine of Alexandria "
                "(or Mystical Marriage of Saint Catherine of Alexandria)"
            ),
            "de": (
                "Die Heilige Familie mit den Heiligen Anna und Katharina von Alexandrien "
                "(oder Mystische Hochzeit der Heiligen Katharina von Alexandrien)"
            ),
            "fr": (
                "La Sainte Famille avec sainte Anne et sainte Catherine d'Alexandrie "
                "(ou Mariage mystique de sainte Catherine)"
            ),
            "es": (
                "La Sagrada Familia con santa Ana y santa Catalina de Alejandría "
                "(o Los desposorios místicos de santa Catalina de Alejandría "
                "con la Sagrada Familia)"
            ),
            "nl": (
                "La Sagrada Familia con Santa Ana y Santa Catalina de Alejandría "
                "(of Los desposorios místicos de Santa Catalina de Alejandría "
                "con la Sagrada Familia)"
            ),
            "it": (
                "Sacra Famiglia con i santi Anna e Caterina d'Alessandria "
                "(o Sposalizio mistico di santa Caterina d'Alessandria)"
            ),
        },
        "alt_en_title": (
            "The Holy Family with Saints Anne and Catherine of Alexandria"
        ),
    },
    {
        "product_id": 15611424211292,
        "artist": "Paulus Potter",
        "label": "Krowy odbijajace",
        "old_pl_titles": ("Krowy odbijające się w wodzie",),
        "new_pl_title": (
            "Krowy odbijające się w wodzie "
            "(lub Bydło odbijające się w wodzie/Pejzaż z krowami pijącymi wodę)"
        ),
        "original_title": "Koeien weerspiegeld in het water",
        "english_title": (
            "Cows Reflected in the Water (or Cattle Reflecting in the Water)"
        ),
        "locale_titles": {
            "en": (
                "Cows Reflected in the Water (or Cattle Reflecting in the Water)"
            ),
            "de": "Kühe im Wasser gespiegelt",
            "fr": (
                "Vaches se reflétant dans l'eau "
                "(ou Vaches au pâturage près d'une mare)"
            ),
            "es": "Vacas reflejadas en el agua",
            "nl": "Koeien weerspiegeld in het water",
            "it": "Mucche riflesse nell'acqua",
        },
        "alt_en_title": "Cows Reflected in the Water",
    },
    {
        "product_id": 15611424702812,
        "artist": "Paulus Potter",
        "label": "Byk",
        "old_pl_titles": ("Byk",),
        "new_pl_title": "Byk (lub Młody byk)",
        "original_title": "De stier (of De jonge stier)",
        "english_title": "The Bull (or The Young Bull)",
        "locale_titles": {
            "en": "The Bull (or The Young Bull)",
            "de": "Der Stier (oder Der junge Stier)",
            "fr": "Le Taureau (ou Le Jeune Taureau)",
            "es": "El toro (o El toro joven)",
            "nl": "De stier (of De jonge stier)",
            "it": "Il toro (o Il giovane toro)",
        },
        "alt_en_title": "The Bull",
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
    artist = cfg["artist"]
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

    new_product_title = f"{artist} - {cfg['new_pl_title']}"
    title_tag, meta_desc, handle = build_seo(
        tytul=cfg["new_pl_title"],
        artysta=artist,
        gatunek="",
        nurt="",
    )
    print(f"  tytul: {new_product_title}")

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
            alt = full_alt_text(artist, alt_en)
        elif "(preview)" in src:
            alt = preview_alt_text(artist, alt_en)
        elif "(mockup)" in src:
            alt = f"{artist} - {alt_en} - (mockup)"
        else:
            alt = f"{artist} - {alt_en}"
        sc.rest_put(
            shop,
            token,
            f"products/{pid}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )

    pl2 = sc.get_product(shop, token, pid).get("body_html") or ""
    print(f"  PL: {extract_display_title_from_body_html(pl2)}")


def main() -> int:
    shop, token = sc.load_session()
    for cfg in PRODUCTS:
        _apply_product(shop, token, cfg)
    print("\nGotowe — 5 produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
