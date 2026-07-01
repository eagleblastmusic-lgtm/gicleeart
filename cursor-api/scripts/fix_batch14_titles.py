"""Poprawka tytulow: batch 14 — Bierstadt (2), Botticelli (8)."""
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
from Komponenty.dodajobraz.description_update import (
    get_translated_fields,
    set_title_update_mark,
)
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
        "product_id": 15549059924316,
        "artist": "Albert Bierstadt",
        "label": "Gory Skaliste, Szczyt Landera",
        "old_pl_titles": ("Góry Skaliste, Szczyt Landera",),
        "new_pl_title": "Góry Skaliste, Szczyt Landera",
        "original_title": "The Rocky Mountains, Lander's Peak",
        "english_title": "The Rocky Mountains, Lander's Peak",
        "locale_titles": {
            "en": "The Rocky Mountains, Lander's Peak",
            "de": "Die Rocky Mountains, Lander's Peak",
            "fr": "Les Montagnes Rocheuses, Lander's Peak",
            "es": "Las Montañas Rocosas, el pico Lander",
            "nl": "The Rocky Mountains, Lander's Peak",
            "it": "Le Montagne Rocciose, Lander's Peak",
        },
        "alt_en_title": "The Rocky Mountains, Lander's Peak",
    },
    {
        "product_id": 15549059629404,
        "artist": "Albert Bierstadt",
        "label": "Matterhorn",
        "old_pl_titles": ("Matterhorn",),
        "new_pl_title": (
            "Matterhorn (lub Widok na Matterhorn/Potok górski na tle Matterhornu)"
        ),
        "original_title": "The Matterhorn",
        "english_title": "The Matterhorn",
        "locale_titles": {
            "en": "The Matterhorn",
            "de": "Das Matterhorn",
            "fr": "Le Cervin (ou Le mont Cervin)",
            "es": "El Cervino (o El monte Cervino)",
            "nl": "De Matterhorn",
            "it": "Il Cervino (o Monte Cervino)",
        },
        "alt_en_title": "The Matterhorn",
    },
    {
        "product_id": 15611547812188,
        "artist": "Sandro Botticelli",
        "label": "Madonna z Dzieciatkiem",
        "old_pl_titles": ("Madonna z Dzieciątkiem",),
        "new_pl_title": "Madonna z Dzieciątkiem (lub Dziewica i Dziecko)",
        "original_title": "Madonna col Bambino",
        "english_title": "The Virgin and Child (or Madonna and Child)",
        "locale_titles": {
            "en": "The Virgin and Child (or Madonna and Child)",
            "de": "Maria mit dem Kind (oder Madonna mit Kind)",
            "fr": "La Vierge et l'Enfant (ou Madone à l'Enfant)",
            "es": "La Virgen y el Niño (o Virgen con el Niño)",
            "nl": "Madonna met Kind (of De Maagd en het Kind)",
            "it": "Madonna col Bambino (o Vergine con il Bambino)",
        },
        "alt_en_title": "The Virgin and Child",
    },
    {
        "product_id": 15611547844956,
        "artist": "Sandro Botticelli",
        "label": "Madonna w niszy",
        "old_pl_titles": ("Madonna z Dzieciątkiem w niszy",),
        "new_pl_title": "Madonna z Dzieciątkiem w niszy",
        "original_title": "Madonna col Bambino in una nicchia",
        "english_title": (
            "The Virgin and Child in a Niche (or Madonna and Child in a Niche)"
        ),
        "locale_titles": {
            "en": (
                "The Virgin and Child in a Niche (or Madonna and Child in a Niche)"
            ),
            "de": (
                "Madonna mit Kind in einer Nische "
                "(oder Maria mit dem Kind in einer Nische)"
            ),
            "fr": (
                "La Vierge et l'Enfant dans une niche "
                "(ou Madone à l'Enfant dans une niche)"
            ),
            "es": (
                "La Virgen y el Niño en un nicho "
                "(o Virgen con el Niño en un nicho)"
            ),
            "nl": (
                "Madonna met Kind in een nis "
                "(of De Maagd en het Kind in een nis)"
            ),
            "it": (
                "Madonna col Bambino in una nicchia "
                "(o Vergine col Bambino in una nicchia)"
            ),
        },
        "alt_en_title": "The Virgin and Child in a Niche",
    },
    {
        "product_id": 15611547779420,
        "artist": "Sandro Botticelli",
        "label": "Madonna korona cierniowa",
        "old_pl_titles": (
            "Madonna z Dzieciątkiem, koroną cierniową i trzema gwoździami",
        ),
        "new_pl_title": (
            "Madonna z Dzieciątkiem z koroną cierniową i trzema gwoździami "
            "(lub Dziewica z Dzieciątkiem)"
        ),
        "original_title": (
            "Madonna col Bambino con la corona di spine e tre chiodi"
        ),
        "english_title": (
            "The Virgin and Child with the Crown of Thorns and Three Nails "
            "(or Madonna and Child)"
        ),
        "locale_titles": {
            "en": (
                "The Virgin and Child with the Crown of Thorns and Three Nails "
                "(or Madonna and Child)"
            ),
            "de": (
                "Maria mit dem Kind mit der Dornenkrone und drei Nägeln "
                "(oder Madonna und Kind)"
            ),
            "fr": (
                "La Vierge et l'Enfant avec la couronne d'épines et les trois clous "
                "(ou Vierge à l'Enfant)"
            ),
            "es": (
                "La Virgen y el Niño con la corona de espinas y tres clavos "
                "(o Virgen con el Niño)"
            ),
            "nl": (
                "Madonna met Kind met de doornenkroon en drie spijkers "
                "(of De Maagd en het Kind)"
            ),
            "it": (
                "Madonna col Bambino con la corona di spine e tre chiodi "
                "(o Vergine col Bambino con la corona di spine e tre chiodi)"
            ),
        },
        "alt_en_title": (
            "The Virgin and Child with the Crown of Thorns and Three Nails"
        ),
    },
    {
        "product_id": 15611547418972,
        "artist": "Sandro Botticelli",
        "label": "Madonna z ksiega",
        "old_pl_titles": (
            "Madonna z księgą (Maria z Dzieciątkiem)",
            "Madonna z księgą",
        ),
        "new_pl_title": "Madonna z księgą (lub Madonna del Libro)",
        "original_title": "Madonna del Libro",
        "english_title": "Madonna of the Book (or Virgin and Child with a Book)",
        "locale_titles": {
            "en": "Madonna of the Book (or Virgin and Child with a Book)",
            "de": "Madonna mit dem Buch (oder Maria mit dem Buch)",
            "fr": "La Madone du livre (ou La Vierge au livre)",
            "es": "Virgen del libro (o Virgen con el Niño leyendo)",
            "nl": "Madonna van het boek (of De Maagd van het boek)",
            "it": "Madonna del Libro (o Madonna col Bambino e un libro)",
        },
        "alt_en_title": "Madonna of the Book",
    },
    {
        "product_id": 15611547451740,
        "artist": "Sandro Botticelli",
        "label": "Mystic Crucifixion",
        "old_pl_titles": ("Mystic Crucifixion",),
        "new_pl_title": "Ukrzyżowanie mistyczne (lub Mistyczne Ukrzyżowanie)",
        "original_title": "Crocifissione mistica",
        "english_title": "Mystic Crucifixion (or Mystical Crucifixion)",
        "locale_titles": {
            "en": "Mystic Crucifixion (or Mystical Crucifixion)",
            "de": "Mystische Kreuzigung",
            "fr": "Crucifixion mystique",
            "es": "Crucifixión mística",
            "nl": "Mystieke kruisiging",
            "it": "Crocifissione mistica",
        },
        "alt_en_title": "Mystic Crucifixion",
    },
    {
        "product_id": 15611547746652,
        "artist": "Sandro Botticelli",
        "label": "Narodziny Wenus",
        "old_pl_titles": ("Narodziny Wenus",),
        "new_pl_title": "Narodziny Wenus",
        "original_title": "Nascita di Venere",
        "english_title": "The Birth of Venus",
        "locale_titles": {
            "en": "The Birth of Venus",
            "de": "Die Geburt der Venus",
            "fr": "La Naissance de Vénus",
            "es": "El nacimiento de Venus",
            "nl": "De Geboorte van Venus",
            "it": "Nascita di Venere",
        },
        "alt_en_title": "The Birth of Venus",
    },
    {
        "product_id": 15611548008796,
        "artist": "Sandro Botticelli",
        "label": "Pallas i Centaur",
        "old_pl_titles": ("Pallas i Centaur",),
        "new_pl_title": "Pallas i centaur (lub Atena i centaur)",
        "original_title": "Pallade e il centauro",
        "english_title": "Pallas and the Centaur",
        "locale_titles": {
            "en": "Pallas and the Centaur",
            "de": "Pallas und der Zentaur",
            "fr": "Pallas et le Centaure",
            "es": "Palas y el Centauro",
            "nl": "Pallas en de Centaur",
            "it": "Pallade e il centauro",
        },
        "alt_en_title": "Pallas and the Centaur",
    },
    {
        "product_id": 15611547713884,
        "artist": "Sandro Botticelli",
        "label": "Portret mlodej kobiety",
        "old_pl_titles": ("Portret młodej kobiety",),
        "new_pl_title": (
            "Portret młodej kobiety (lub Portret Simonetty Vespucci)"
        ),
        "original_title": "Ritratto di giovane donna",
        "english_title": (
            "Portrait of a Young Woman (or Portrait of Simonetta Vespucci)"
        ),
        "locale_titles": {
            "en": "Portrait of a Young Woman (or Portrait of Simonetta Vespucci)",
            "de": (
                "Bildnis einer jungen Frau (oder Porträt der Simonetta Vespucci)"
            ),
            "fr": (
                "Portrait de jeune femme (ou Portrait de Simonetta Vespucci)"
            ),
            "es": (
                "Retrato de una joven (o Retrato de Simonetta Vespucci)"
            ),
            "nl": (
                "Portret van een jonge vrouw (of Portret van Simonetta Vespucci)"
            ),
            "it": (
                "Ritratto di giovane donna (o Ritratto di Simonetta Vespucci)"
            ),
        },
        "alt_en_title": "Portrait of a Young Woman",
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 14).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
