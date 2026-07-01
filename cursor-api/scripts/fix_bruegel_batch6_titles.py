"""Poprawka tytulow: 6 produktow Pieter Bruegel (starszy) — batch 6."""
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
from Komponenty.dodajobraz.description_update import get_translated_fields, set_title_update_mark
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


ARTIST = "Pieter Bruegel (starszy)"

PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15610441793884,
        "artist": ARTIST,
        "label": "Kazanie sw. Jana Chrzciciela",
        "old_pl_titles": ("Kazanie św. Jana Chrzciciela",),
        "new_pl_title": (
            "Kazanie św. Jana Chrzciciela "
            "(lub Kazanie świętego Jana Chrzciciela)"
        ),
        "original_title": "De prediking van Johannes de Doper",
        "english_title": (
            "The Sermon of Saint John the Baptist "
            "(or The Sermon of St. John the Baptist)"
        ),
        "locale_titles": {
            "en": (
                "The Sermon of Saint John the Baptist "
                "(or The Sermon of St. John the Baptist)"
            ),
            "de": (
                "Die Predigt Johannes des Täufers "
                "(oder Die Predigt des heiligen Johannes des Täufers)"
            ),
            "fr": (
                "La prédication de saint Jean-Baptiste "
                "(ou La prédication de Jean-Baptiste)"
            ),
            "es": (
                "La predicación de san Juan Bautista "
                "(o La predicación de Juan el Bautista)"
            ),
            "nl": (
                "De prediking van Johannes de Doper "
                "(of De prediking van de heilige Johannes de Doper)"
            ),
            "it": (
                "La predica di san Giovanni Battista "
                "(o La predicazione di san Giovanni Battista)"
            ),
        },
        "alt_en_title": "The Sermon of Saint John the Baptist",
    },
    {
        "product_id": 15610441302364,
        "artist": ARTIST,
        "label": "Mysliwi na sniegu",
        "old_pl_titles": ("Myśliwi na śniegu",),
        "new_pl_title": "Myśliwi na śniegu (lub Powrót myśliwych)",
        "original_title": "Jagers in de sneeuw",
        "english_title": (
            "The Hunters in the Snow (or Return of the Hunters)"
        ),
        "locale_titles": {
            "en": (
                "The Hunters in the Snow (or Return of the Hunters)"
            ),
            "de": "Jäger im Schnee (oder Heimkehr der Jäger)",
            "fr": "Chasseurs dans la neige (ou Le retour des chasseurs)",
            "es": "Cazadores en la nieve (o El regreso de los cazadores)",
            "nl": "Jagers in de sneeuw (of De jagers in de sneeuw)",
            "it": "Cacciatori nella neve (o Ritorno dei cacciatori)",
        },
        "alt_en_title": "The Hunters in the Snow",
    },
    {
        "product_id": 15610438123868,
        "artist": ARTIST,
        "label": "Przypowiesc o slepcach",
        "old_pl_titles": (
            "Przypowieść o ślepcach (lub Ślepcy)",
            "Przypowieść o ślepcach",
        ),
        "new_pl_title": (
            "Ślepcy (lub Ślepcy prowadzący ślepców/Przypowieść o ślepcach)"
        ),
        "original_title": "De parabel der blinden",
        "english_title": (
            "The Blind Leading the Blind (or The Parable of the Blind)"
        ),
        "locale_titles": {
            "en": (
                "The Blind Leading the Blind (or The Parable of the Blind)"
            ),
            "de": "Der Blindensturz (oder Die Parabel von den Blinden)",
            "fr": "La Parabole des aveugles (ou Les Aveugles)",
            "es": "La parábola de los ciegos (o Los ciegos)",
            "nl": "De parabel der blinden (of De blinden)",
            "it": "Parabola dei ciechi (o I ciechi)",
        },
        "alt_en_title": "The Blind Leading the Blind",
    },
    {
        "product_id": 15610433995100,
        "artist": ARTIST,
        "label": "Rzez niewiniattek",
        "old_pl_titles": ("Rzeź niewiniątek",),
        "new_pl_title": "Rzeź niewiniątek",
        "original_title": "De kindermoord te Bethlehem",
        "english_title": "The Massacre of the Innocents",
        "locale_titles": {
            "en": "The Massacre of the Innocents",
            "de": "Der Kindermord zu Bethlehem",
            "fr": "Le massacre des innocents",
            "es": "La matanza de los inocentes",
            "nl": "De kindermoord te Bethlehem",
            "it": "Strage degli innocenti (o La strage degli innocenti)",
        },
        "alt_en_title": "The Massacre of the Innocents",
    },
    {
        "product_id": 15610436354396,
        "artist": ARTIST,
        "label": "Przyslowia niderlandzkie",
        "old_pl_titles": (
            "Przysłowia niderlandzkie (lub Świat na opak/Niebieski płaszcz)",
            "Wesele chłopskie",
        ),
        "new_pl_title": (
            "Przysłowia niderlandzkie "
            "(lub Przysłowia holenderskie/Świat na opak)"
        ),
        "original_title": "Nederlandse Spreekwoorden",
        "english_title": (
            "Netherlandish Proverbs "
            "(or Dutch Proverbs/The Topsy-Turvy World)"
        ),
        "locale_titles": {
            "en": (
                "Netherlandish Proverbs "
                "(or Dutch Proverbs/The Topsy-Turvy World)"
            ),
            "de": (
                "Die niederländischen Sprichwörter (oder Die verkehrte Welt)"
            ),
            "fr": (
                "Les Proverbes flamands "
                "(ou Les Proverbes néerlandais/Le Monde à l'envers)"
            ),
            "es": (
                "Los proverbios flamencos "
                "(o Proverbios neerlandeses/El mundo al revés)"
            ),
            "nl": (
                "Nederlandse Spreekwoorden "
                "(of De blauwe huik/De verkeerde wereld)"
            ),
            "it": "Proverbi fiamminghi (o Il mondo alla rovescia)",
        },
        "alt_en_title": "Netherlandish Proverbs",
    },
    {
        "product_id": 15610439762268,
        "artist": ARTIST,
        "label": "Zniwa",
        "old_pl_titles": ("Żniwa",),
        "new_pl_title": "Żniwa",
        "original_title": "De korenoogst",
        "english_title": "The Harvesters (or The Corn Harvest)",
        "locale_titles": {
            "en": "The Harvesters (or The Corn Harvest)",
            "de": "Die Körnernte (oder Die Ernte)",
            "fr": "La moisson (ou Les moissonneurs)",
            "es": "La cosecha (o Los cosechadores)",
            "nl": "De korenoogst (of De oogst)",
            "it": "La mietitura (o I mietitori)",
        },
        "alt_en_title": "The Harvesters",
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
    set_title_update_mark(pid, marked=True)


def main() -> int:
    shop, token = sc.load_session()
    for cfg in PRODUCTS:
        _apply_product(shop, token, cfg)
    print("\nGotowe — 6 produktow Bruegel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
