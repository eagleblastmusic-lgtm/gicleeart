"""Poprawka tytulow: 9 produktow — Gesina, Taylor, Ruysch, Rusinol, Rubens (batch 9)."""
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
        "product_id": 15611530183004,
        "artist": "Gesina ter Borch",
        "label": "Posmiertny portret Mosesa",
        "old_pl_titles": ("Pośmiertny portret Mosesa ter Borcha",),
        "new_pl_title": (
            "Portret pamiątkowy Mosesa ter Borcha "
            "(lub Portret pośmiertny Mosesa ter Borcha/Portret memoratywny Mojżesza ter Borcha)"
        ),
        "original_title": (
            "Memorieportret van Moses ter Borch (of Portret van Moses ter Borch)"
        ),
        "english_title": (
            "Memorial Portrait of Moses ter Borch "
            "(or Posthumous Portrait of Moses ter Borch)"
        ),
        "locale_titles": {
            "en": (
                "Memorial Portrait of Moses ter Borch "
                "(or Posthumous Portrait of Moses ter Borch)"
            ),
            "de": (
                "Erinnerungsporträt von Moses ter Borch "
                "(oder Gedenkporträt von Moses ter Borch)"
            ),
            "fr": (
                "Portrait commémoratif de Moses ter Borch "
                "(ou Portrait posthume de Moses ter Borch)"
            ),
            "es": (
                "Retrato conmemorativo de Moses ter Borch "
                "(o Retrato póstumo de Moses ter Borch)"
            ),
            "nl": (
                "Memorieportret van Moses ter Borch "
                "(of Portret van Moses ter Borch)"
            ),
            "it": (
                "Ritratto commemorativo di Moses ter Borch "
                "(o Ritratto postumo di Moses ter Borch)"
            ),
        },
        "alt_en_title": "Memorial Portrait of Moses ter Borch",
    },
    {
        "product_id": 15611318042972,
        "artist": "Henry King Taylor",
        "label": "Kuter pilotowy z lodzia",
        "old_pl_titles": (
            "Kuter pilotowy nr 3 z podpływającą łodzią wiosłową",
            "Kuter pilotowy nr 3 z dobijającą łodzią wiosłową i parowcem bocznokołowym w oddali",
        ),
        "new_pl_title": (
            "Kuter pilotowy nr 3 z podpływającą łodzią wiosłową i parowcem kołowym w oddali "
            "(lub Kuter pilotowy z Dover nr 3 powracający do brzegu)"
        ),
        "original_title": (
            "Pilot cutter no. 3 with a rowing boat coming alongside "
            "and a paddlesteamer in the distance "
            "(of The Dover Pilot Cutter, No 3 Heading Back Inshore, "
            "with a large merchantman hove-to out in the bay)"
        ),
        "english_title": (
            "Pilot cutter no. 3 with a rowing boat coming alongside "
            "and a paddlesteamer in the distance "
            "(or The Dover Pilot Cutter, No 3 Heading Back Inshore)"
        ),
        "locale_titles": {
            "en": (
                "Pilot cutter no. 3 with a rowing boat coming alongside "
                "and a paddlesteamer in the distance "
                "(or The Dover Pilot Cutter, No 3 Heading Back Inshore)"
            ),
            "de": (
                "Lotsenkutter Nr. 3 mit einem sich annähernden Ruderboot "
                "und einem Raddampfer in der Ferne"
            ),
            "fr": (
                "Le cutter pilote n° 3 avec un canot de rames s'approchant "
                "et un bateau à vapeur à aubes au loin"
            ),
            "es": (
                "El cúter de práctico n.º 3 con un bote de remos acercándose "
                "y un vapor de ruedas a lo lejos"
            ),
            "nl": (
                "Pilot cutter no. 3 with a rowing boat coming alongside "
                "and a paddlesteamer in the distance "
                "(of The Dover Pilot Cutter, No 3 Heading Back Inshore, "
                "with a large merchantman hove-to out in the bay)"
            ),
            "it": (
                "Il cutter pilota n. 3 con una barca a remi che si avvicina "
                "e un piroscafo a ruote in lontananza"
            ),
        },
        "alt_en_title": (
            "Pilot cutter no. 3 with a rowing boat coming alongside "
            "and a paddlesteamer in the distance"
        ),
    },
    {
        "product_id": 15611317813596,
        "artist": "Henry King Taylor",
        "label": "Kuter pilotowy inshore",
        "old_pl_titles": (
            "Kuter pilotowy nr 3 powracający do brzegu",
            "Kuter pilotowy nr 3 wracający do brzegu, z dużym statkiem handlowym dryfującym w zatoce",
        ),
        "new_pl_title": (
            "Kuter pilotowy nr 3 wracający do brzegu z dużym statkiem handlowym w zatoce "
            "(lub Kuter pilotowy z Dover nr 3 powracający do brzegu)"
        ),
        "original_title": (
            "Pilot cutter no. 3 heading back inshore, "
            "with a large merchantman hove-to out in the bay "
            "(of The Dover Pilot Cutter, No 3 Heading Back Inshore)"
        ),
        "english_title": (
            "Pilot cutter no. 3 heading back inshore, "
            "with a large merchantman hove-to out in the bay "
            "(or The Dover Pilot Cutter, No 3 Heading Back Inshore)"
        ),
        "locale_titles": {
            "en": (
                "Pilot cutter no. 3 heading back inshore, "
                "with a large merchantman hove-to out in the bay "
                "(or The Dover Pilot Cutter, No 3 Heading Back Inshore)"
            ),
            "de": (
                "Lotsenkutter Nr. 3 auf dem Weg zurück an Land, "
                "mit einem großen Handelsschiff in der Bucht"
            ),
            "fr": (
                "Le cutter pilote n° 3 regagnant la côte, "
                "avec un grand navire marchand au mouillage dans la baie"
            ),
            "es": (
                "El cúter de práctico n.º 3 regresando a la costa, "
                "con un gran buque mercante fondeado en la bahía"
            ),
            "nl": (
                "Pilot cutter no. 3 heading back inshore, "
                "with a large merchantman hove-to out in the bay "
                "(of The Dover Pilot Cutter, No 3 Heading Back Inshore)"
            ),
            "it": (
                "Il cutter pilota n. 3 che rientra verso la costa, "
                "con una grande nave mercantile alla fonda nella baia"
            ),
        },
        "alt_en_title": (
            "Pilot cutter no. 3 heading back inshore, "
            "with a large merchantman hove-to out in the bay"
        ),
    },
    {
        "product_id": 15611317485916,
        "artist": "Henry King Taylor",
        "label": "Holenderscy rybacy",
        "old_pl_titles": ("Holenderscy rybacy na morzu",),
        "new_pl_title": "Holenderscy rybacy na morzu (lub Rybacy na morzu)",
        "original_title": "Dutch Fishermen at Sea (of Fishermen at Sea)",
        "english_title": "Dutch Fishermen at Sea (or Fishermen at Sea)",
        "locale_titles": {
            "en": "Dutch Fishermen at Sea (or Fishermen at Sea)",
            "de": "Niederländische Fischer auf See (oder Fischer auf See)",
            "fr": "Pêcheurs hollandais en mer (ou Pêcheurs en mer)",
            "es": "Pescadores holandeses en el mar (o Pescadores en el mar)",
            "nl": "Dutch Fishermen at Sea (of Fishermen at Sea)",
            "it": "Pescatori olandesi in mare (o Pescatori in mare)",
        },
        "alt_en_title": "Dutch Fishermen at Sea",
    },
    {
        "product_id": 15611426406748,
        "artist": "Rachel Ruysch",
        "label": "Wazon z kwiatami",
        "old_pl_titles": ("Wazon z kwiatami",),
        "new_pl_title": (
            "Wazon z kwiatami (z Mauritshuis) "
            "(lub Bukiet kwiatów w szklanym wazonie/Martwa natura z kwiatami w szklanym wazonie)"
        ),
        "original_title": (
            "Vaas met bloemen (Mauritshuis) "
            "(of Bloemen in een glazen vaas op een marmeren blad)"
        ),
        "english_title": "Vase with Flowers (Mauritshuis) (or Flowers in a Glass Vase)",
        "locale_titles": {
            "en": "Vase with Flowers (Mauritshuis) (or Flowers in a Glass Vase)",
            "de": "Vase mit Blumen (Mauritshuis) (oder Blumen in einer Glasvase)",
            "fr": "Vase avec des fleurs (Mauritshuis) (ou Fleurs dans un vase de verre)",
            "es": "Jarrón con flores (Mauritshuis) (o Flores en un jarrón de vidrio)",
            "nl": (
                "Vaas met bloemen (Mauritshuis) "
                "(of Bloemen in een glazen vaas op een marmeren blad)"
            ),
            "it": "Vaso con fiori (Mauritshuis) (o Fiori in un vaso di vetro)",
        },
        "alt_en_title": "Vase with Flowers (Mauritshuis)",
    },
    {
        "product_id": 15611427094876,
        "artist": "Santiago Rusiñol",
        "label": "Kobieca figura",
        "old_pl_titles": ("Kobieca figura", "Female Figure"),
        "new_pl_title": "Postać kobieca (lub Sylwetka kobieca/Kobieta w czerni)",
        "original_title": "Figura femenina (of Figura de dona (París))",
        "english_title": "Female Figure (or Woman in Black)",
        "locale_titles": {
            "en": "Female Figure (or Woman in Black)",
            "de": "Weibliche Figur (oder Frau in Schwarz)",
            "fr": "Figure féminine (ou Femme en noir)",
            "es": "Figura femenina (o Mujer de negro)",
            "nl": "Figura femenina (of Figura de dona (París))",
            "it": "Figura femminile (o Donna in nero)",
        },
        "alt_en_title": "Female Figure",
    },
    {
        "product_id": 15611425980764,
        "artist": "Peter Paul Rubens",
        "label": "Raj i grzech",
        "old_pl_titles": (
            "Raj i grzech pierworodny (lub Adam i Ewa w raju)",
            "Raj i grzech pierworodny",
            "Rajski ogród z upadkiem człowieka",
        ),
        "new_pl_title": (
            "Grzech pierworodny "
            "(lub Raj ziemski z upadkiem człowieka/Ogród Eden z upadkiem człowieka)"
        ),
        "original_title": (
            "De zondeval (of Het aards paradijs met de zondeval van de mens)"
        ),
        "english_title": (
            "The Garden of Eden with the Fall of Man (or The Fall of Man)"
        ),
        "locale_titles": {
            "en": "The Garden of Eden with the Fall of Man (or The Fall of Man)",
            "de": "Der Sündenfall (oder Das Paradies mit dem Sündenfall)",
            "fr": (
                "Le Paradis terrestre avec la chute de l'homme "
                "(ou Le Péché originel)"
            ),
            "es": (
                "El jardín del Edén con la caída del hombre (o El pecado original)"
            ),
            "nl": (
                "De zondeval (of Het aards paradijs met de zondeval van de mens)"
            ),
            "it": (
                "Il peccato originale "
                "(o Il giardino dell'Eden con la caduta dell'uomo)"
            ),
        },
        "alt_en_title": "The Garden of Eden with the Fall of Man",
    },
    {
        "product_id": 15611425096028,
        "artist": "Peter Paul Rubens",
        "label": "Karitas rzymska",
        "old_pl_titles": (
            "Karitas rzymska (lub Cimon i Pero)",
            "Karitas rzymska",
        ),
        "new_pl_title": "Cymon i Pero (lub Miłosierdzie rzymskie (z Rijksmuseum))",
        "original_title": "Cimon en Pero (of De Romeinse liefdadigheid (Rijksmuseum))",
        "english_title": "Cimon and Pero (or Roman Charity (Rijksmuseum))",
        "locale_titles": {
            "en": "Cimon and Pero (or Roman Charity (Rijksmuseum))",
            "de": "Cimon und Pero (oder Die römische Caritas (Rijksmuseum))",
            "fr": "Cimon et Péro (ou La Charité romaine (Rijksmuseum))",
            "es": "Cimón y Pero (o La caridad romana (Rijksmuseum))",
            "nl": "Cimon en Pero (of De Romeinse liefdadigheid (Rijksmuseum))",
            "it": "Cimone e Pero (o Carità romana (Rijksmuseum))",
        },
        "alt_en_title": "Cimon and Pero",
    },
    {
        "product_id": 15611425456476,
        "artist": "Peter Paul Rubens",
        "label": "Daniel w jaskini lwów",
        "old_pl_titles": ("Daniel w jaskini lwów",),
        "new_pl_title": "Daniel w jaskini lwów (lub Daniel w lwiej jamie)",
        "original_title": "Daniël in de leeuwenkuil",
        "english_title": "Daniel in the Lions' Den",
        "locale_titles": {
            "en": "Daniel in the Lions' Den",
            "de": "Daniel in der Löwengrube",
            "fr": "Daniel dans la fosse aux lions",
            "es": "Daniel en el foso de los leones",
            "nl": "Daniël in de leeuwenkuil",
            "it": "Daniele nella fossa dei leoni",
        },
        "alt_en_title": "Daniel in the Lions' Den",
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
    print("\nGotowe — 9 produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
