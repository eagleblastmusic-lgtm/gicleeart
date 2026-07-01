"""Poprawka tytulow: 6 produktow Van Gogh — pejzaze i martwa natura (batch)."""
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
        "product_id": 15611340980572,
        "label": "Krajobraz z Saint-Remy",
        "old_pl_titles": (
            "Pejzaż z Saint-Rémy",
            "Krajobraz z Saint-Rémy",
        ),
        "new_pl_title": (
            "Krajobraz z Saint-Rémy "
            "(lub Pole pszenicy za szpitalem Saint-Paul/Ogrodzone pole pszenicy w Saint-Rémy)"
        ),
        "original_title": (
            "Landschap van Saint-Rémy (of Korenveld achter het hospicium Saint-Paul)"
        ),
        "english_title": (
            "Landscape from Saint-Rémy "
            "(or Wheat Field behind Saint-Paul Hospital/Enclosed Wheat Field with Rising Sun)"
        ),
        "locale_titles": {
            "en": (
                "Landscape from Saint-Rémy "
                "(or Wheat Field behind Saint-Paul Hospital/"
                "Enclosed Wheat Field with Rising Sun)"
            ),
            "de": (
                "Landschaft aus Saint-Rémy "
                "(oder Weizenfeld hinter dem Saint-Paul Hospital)"
            ),
            "fr": (
                "Paysage de Saint-Rémy "
                "(ou Champ de blé derrière l'hospice Saint-Paul)"
            ),
            "es": (
                "Paisaje de Saint-Rémy "
                "(o Campo de trigo detrás del hospital de Saint-Paul)"
            ),
            "nl": (
                "Landschap van Saint-Rémy "
                "(of Korenveld achter het hospicium Saint-Paul)"
            ),
            "it": (
                "Paesaggio di Saint-Rémy "
                "(o Campo di grano dietro l'ospedale di Saint-Paul)"
            ),
        },
        "alt_en_title": "Landscape from Saint-Rémy",
    },
    {
        "product_id": 15611341439324,
        "label": "Gaj oliwny",
        "old_pl_titles": (
            "Olive Grove",
            "Gaj oliwny",
        ),
        "new_pl_title": (
            "Gaj oliwny z niebiem i chmurami (lub Gaj oliwny/Drzewa oliwne)"
        ),
        "original_title": "Olijfgaard met blauwe lucht en wolken (of Olijfgaard)",
        "english_title": "Olive Grove with Sky and Clouds (or Olive Trees/Olive Grove)",
        "locale_titles": {
            "en": "Olive Grove with Sky and Clouds (or Olive Trees/Olive Grove)",
            "de": "Olivenhain mit blauem Himmel und Wolken (oder Olivenhain)",
            "fr": "Oliveraie avec ciel bleu et nuages (ou Les oliviers)",
            "es": "Olivar con cielo azul y nubes (o Los olivos)",
            "nl": "Olijfgaard met blauwe lucht en wolken (of Olijfgaard)",
            "it": "Uliveto con cielo azzurro e nuvole (o Gli ulivi)",
        },
        "alt_en_title": "Olive Grove with Sky and Clouds",
    },
    {
        "product_id": 15611353596252,
        "label": "Ogrod Saint-Remy",
        "old_pl_titles": (
            "Ogród szpitala w Saint-Rémy",
            "Ogród zakładu psychiatrycznego w Saint-Rémy "
            "(często występuje też pod skróconą nazwą Ogród przytułku lub Ogród szpitala w Saint-Rémy).",
            "Ogród zakładu psychiatrycznego w Saint-Rémy",
        ),
        "new_pl_title": (
            "Ogród zakładu psychiatrycznego w Saint-Rémy "
            "(lub Ogród szpitala w Saint-Rémy/Ogród przytułku)"
        ),
        "original_title": (
            "De tuin van de inrichting in Saint-Rémy "
            "(of De tuin van de kliniek Sint-Paul)"
        ),
        "english_title": (
            "The Garden of the Asylum at Saint-Rémy (or The Asylum Garden)"
        ),
        "locale_titles": {
            "en": "The Garden of the Asylum at Saint-Rémy (or The Asylum Garden)",
            "de": (
                "Der Garten der Anstalt in Saint-Rémy "
                "(oder Anstaltsgarten in Saint-Rémy)"
            ),
            "fr": (
                "Le jardin de l'asile à Saint-Rémy "
                "(ou Le jardin de l'hospice Saint-Paul)"
            ),
            "es": (
                "El jardín del asilo en Saint-Rémy "
                "(o Jardín del hospital de San Pablo)"
            ),
            "nl": (
                "De tuin van de inrichting in Saint-Rémy "
                "(of De tuin van de kliniek Sint-Paul)"
            ),
            "it": (
                "Il giardino del manicomio a Saint-Rémy "
                "(o Il giardino dell'ospedale di Saint-Paul)"
            ),
        },
        "alt_en_title": "The Garden of the Asylum at Saint-Rémy",
    },
    {
        "product_id": 15611340194140,
        "label": "Ogrodek z parami zakochanymi",
        "old_pl_titles": (
            "Ogród z parami zakochanych: Square Saint-Pierre",
            "Ogród z parami zakochanymi: Square Saint-Pierre",
        ),
        "new_pl_title": (
            "Ogród z zakochanymi parami: Plac Świętego Piotra "
            "(lub Ogród na Montmartre z kochankami)"
        ),
        "original_title": (
            "Tuin met geliefden: Square Saint-Pierre "
            "(of Tuin in Montmartre met geliefden)"
        ),
        "english_title": (
            "Garden with Courting Couples: Square Saint-Pierre "
            "(or Garden in Montmartre with Lovers)"
        ),
        "locale_titles": {
            "en": (
                "Garden with Courting Couples: Square Saint-Pierre "
                "(or Garden in Montmartre with Lovers)"
            ),
            "de": "Garten mit verliebtem Paar: Square Saint-Pierre",
            "fr": (
                "Jardin avec couples d'amoureux: Square Saint-Pierre "
                "(ou Couple d'amoureux dans le square Saint-Pierre de Montmartre)"
            ),
            "es": "Jardín con parejas cortejando: Square Saint-Pierre",
            "nl": (
                "Tuin met geliefden: Square Saint-Pierre "
                "(of Tuin in Montmartre met geliefden)"
            ),
            "it": "Giardino con coppie di innamorati: Square Saint-Pierre",
        },
        "alt_en_title": "Garden with Courting Couples: Square Saint-Pierre",
    },
    {
        "product_id": 15611335082332,
        "label": "Ogrodzone pole z oraczem",
        "old_pl_titles": (
            "Ogrodzone pole z oraczem",
        ),
        "new_pl_title": (
            "Ogrodzone pole z oraczem "
            "(lub Oracz w ogrodzonym polu/Krajobraz z oraczem)"
        ),
        "original_title": (
            "Ommuurd veld met een ploeger (of De ploeger/En gesloten veld met ploeger)"
        ),
        "english_title": (
            "Enclosed Field with a Ploughman "
            "(or Enclosed Field with Peasant/Landscape with a Ploughman)"
        ),
        "locale_titles": {
            "en": (
                "Enclosed Field with a Ploughman "
                "(or Enclosed Field with Peasant/Landscape with a Ploughman)"
            ),
            "de": "Eingezäuntes Feld mit Pflüger (oder Der Pflüger)",
            "fr": "Champ enclos avec laboureur (ou Le laboureur)",
            "es": "Campo cercado con un arador (o El arador)",
            "nl": (
                "Ommuurd veld met een ploeger "
                "(of De ploeger/En gesloten veld met ploeger)"
            ),
            "it": "Campo recintato con aratore (o L'aratore)",
        },
        "alt_en_title": "Enclosed Field with a Ploughman",
    },
    {
        "product_id": 15611351662940,
        "label": "Martwa natura z polnymi kwiatami",
        "old_pl_titles": (
            "Martwa natura z polnymi kwiatami i różami",
        ),
        "new_pl_title": (
            "Martwa natura z polnymi kwiatami i różami "
            "(lub Martwa natura z kwiatami łąkowymi i różami)"
        ),
        "original_title": "Stilleven met weidebloemen en rozen",
        "english_title": "Still Life with Meadow Flowers and Roses",
        "locale_titles": {
            "en": "Still Life with Meadow Flowers and Roses",
            "de": "Stilleven mit Wiesenblumen und Rosen",
            "fr": "Nature morte avec fleurs des champs et roses",
            "es": "Naturaleza muerta con flores de campo y rosas",
            "nl": "Stilleven met weidebloemen en rozen",
            "it": "Natura morta con fiori di campo e rose",
        },
        "alt_en_title": "Still Life with Meadow Flowers and Roses",
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
    print("\nGotowe — 6 produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
