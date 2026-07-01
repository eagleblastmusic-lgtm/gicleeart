"""Poprawka tytulow: 13 produktow Van Gogh (batch 7)."""
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
        "product_id": 15611345895772,
        "label": "Kwitnacy sad (sliwy)",
        "old_pl_titles": ("Kwitnący sad (śliwy)", "Kwitnący sad"),
        "new_pl_title": (
            "Sad w kwiatach (śliwki) "
            "(lub Kwitnący sad (Śliwy)/Sad z kwitnącymi śliwami)"
        ),
        "original_title": (
            "De bloeiende boomgaard met pruimenbomen (of Bloeiende boomgaard)"
        ),
        "english_title": "Orchard in Blossom (Plum Trees) (or The Flowering Orchard)",
        "locale_titles": {
            "en": "Orchard in Blossom (Plum Trees) (or The Flowering Orchard)",
            "de": (
                "Blühender Obstgarten mit Pflaumenbäumen "
                "(oder Blühender Obstgarten)"
            ),
            "fr": "Verger en fleurs (Pruniers) (ou Le verger en fleurs)",
            "es": "Melocotonero en flor (o Huerto en flor (Ciruelos))",
            "nl": (
                "De bloeiende boomgaard met pruimenbomen "
                "(of Bloeiende boomgaard)"
            ),
            "it": "Frutteto in fiore (Susini) (o Il frutteto in fiore)",
        },
        "alt_en_title": "Orchard in Blossom (Plum Trees)",
    },
    {
        "product_id": 15611353432412,
        "label": "Kwitnacy sad",
        "old_pl_titles": ("Kwitnący sad",),
        "new_pl_title": (
            "Kwitnący sad (lub Sad w kwiatach/Sad w kwiatach z grabiami)"
        ),
        "original_title": "De bloeiende boomgaard (of Bloeiende boomgaard met hark)",
        "english_title": (
            "The Flowering Orchard (or Orchard in Blossom/Orchard with a Rake)"
        ),
        "locale_titles": {
            "en": (
                "The Flowering Orchard "
                "(or Orchard in Blossom/Orchard with a Rake)"
            ),
            "de": "Blühender Obstgarten (oder Der blühende Obstgarten)",
            "fr": "Le verger en fleurs (ou Verger en fleurs)",
            "es": "Huerto en flor (o El huerto en flor)",
            "nl": "De bloeiende boomgaard (of Bloeiende boomgaard met hark)",
            "it": "Frutteto in fiore (o Il frutteto in fiore)",
        },
        "alt_en_title": "The Flowering Orchard",
    },
    {
        "product_id": 15615454839132,
        "label": "Kwitnace drzewo brzoskwiniowe",
        "old_pl_titles": (
            "Kwitnąca brzoskwinia",
            "Kwitnące drzewo brzoskwiniowe "
            "(lub Kwitnące drzewo migdałowe lub Drzewo brzoskwiniowe w rozkwicie)",
            "Kwitnące drzewo brzoskwiniowe",
        ),
        "new_pl_title": (
            "Kwitnące drzewo brzoskwiniowe "
            "(lub Różowe drzewo brzoskwiniowe/Kwitnące drzewo migdałowe)"
        ),
        "original_title": (
            "Bloeiende perzikboom (of Roze perzikboom/Bloeiende amandelboom)"
        ),
        "english_title": (
            "Pink Peach Tree in Blossom (or Pink Peach Tree/Almond Tree in Blossom)"
        ),
        "locale_titles": {
            "en": (
                "Pink Peach Tree in Blossom "
                "(or Pink Peach Tree/Almond Tree in Blossom)"
            ),
            "de": (
                "Blühender Pfirsichbaum "
                "(oder Rosa Pfirsichbaum/Blühender Mandelbaum)"
            ),
            "fr": (
                "Pêcher en fleurs "
                "(ou Pêcher en fleurs (Arles)/Amandier en fleurs)"
            ),
            "es": (
                "Melocotonero en flor "
                "(o Melocotonero rosa en flor/Almendro en flor)"
            ),
            "nl": (
                "Bloeiende perzikboom "
                "(of Roze perzikboom/Bloeiende amandelboom)"
            ),
            "it": (
                "Pesco in fiore "
                "(o Pesco rosa in fiore/Albero di mandorlo in fiore)"
            ),
        },
        "alt_en_title": "Pink Peach Tree in Blossom",
    },
    {
        "product_id": 15611353235804,
        "label": "Kosciol w Auvers",
        "old_pl_titles": ("Kościół w Auvers",),
        "new_pl_title": "Kościół w Auvers",
        "original_title": "De kerk van Auvers (of De kerk te Auvers-sur-Oise)",
        "english_title": "The Church at Auvers (or The Church at Auvers-sur-Oise)",
        "locale_titles": {
            "en": "The Church at Auvers (or The Church at Auvers-sur-Oise)",
            "de": "Die Kirche von Auvers",
            "fr": "L'Église d'Auvers-sur-Oise",
            "es": "La iglesia de Auvers-sur-Oise",
            "nl": "De kerk van Auvers (of De kerk te Auvers-sur-Oise)",
            "it": "La chiesa di Auvers",
        },
        "alt_en_title": "The Church at Auvers",
    },
    {
        "product_id": 15611340521820,
        "label": "Korony cesarskie",
        "old_pl_titles": (
            "Korony cesarskie w miedzianym wazonie",
            "Korony cesarskie",
        ),
        "new_pl_title": (
            "Szachownice cesarskie w miedzianym wazonie "
            "(lub Korony cesarskie w miedzianym wazonie)"
        ),
        "original_title": "Keizerskronen in een koperen vaas",
        "english_title": (
            "Imperial Fritillaries in a Copper Vase "
            "(or Crown Imperials in a Copper Vase)"
        ),
        "locale_titles": {
            "en": (
                "Imperial Fritillaries in a Copper Vase "
                "(or Crown Imperials in a Copper Vase)"
            ),
            "de": (
                "Kaiserkronen in einer Kupfervase "
                "(oder Fritillarien in einer Kupfervase)"
            ),
            "fr": (
                "Couronnes impériales dans un vase de cuivre "
                "(ou Fritillaires dans un vase de cuivre)"
            ),
            "es": (
                "Fritilarias en un florero de cobre "
                "(o Coronaciones imperiales en un jarrón de cobre)"
            ),
            "nl": "Keizerskronen in een koperen vaas",
            "it": (
                "Fritillarie in un vaso di rame "
                "(o Fritillaria imperiale in un vaso di rame)"
            ),
        },
        "alt_en_title": "Imperial Fritillaries in a Copper Vase",
    },
    {
        "product_id": 15611356709212,
        "label": "Gwiezdzista noc",
        "old_pl_titles": ("Gwiaździsta noc", "Gwieździsta noc"),
        "new_pl_title": "Gwieździsta noc",
        "original_title": "De sterrennacht",
        "english_title": "The Starry Night",
        "locale_titles": {
            "en": "The Starry Night",
            "de": "Sternennacht (oder Die Sternennacht)",
            "fr": "La Nuit étoilée",
            "es": "La noche estrellada",
            "nl": "De sterrennacht",
            "it": "Notte stellata (o La notte stellata)",
        },
        "alt_en_title": "The Starry Night",
    },
    {
        "product_id": 15611337277788,
        "label": "Gospodarstwo ze stosami torfu",
        "old_pl_titles": (
            "Gospodarstwo ze stosami torfu",
            "Gospodarstwo ze stogami torfu",
        ),
        "new_pl_title": (
            "Zagroda ze stogami torfu "
            "(lub Gospodarstwo ze stogami torfu/Pejzaż ze stogami torfu i chatami)"
        ),
        "original_title": "Boerderij met turfhopen (of Landschap met keet en turfhopen)",
        "english_title": (
            "Farm with Stacks of Peat "
            "(or Farmhouse with Peat Stacks/Landscape with a Stack of Peat and Farmhouses)"
        ),
        "locale_titles": {
            "en": (
                "Farm with Stacks of Peat "
                "(or Farmhouse with Peat Stacks/"
                "Landscape with a Stack of Peat and Farmhouses)"
            ),
            "de": (
                "Bauernhof mit Torfhaufen "
                "(oder Landschaft mit Torfhaufen und Bauernhäusern)"
            ),
            "fr": "Ferme aux tas de tourbe (ou Ferme avec des tas de tourbe)",
            "es": "Granja con montones de turba (o Granja con pilas de turba)",
            "nl": "Boerderij met turfhopen (of Landschap met keet en turfhopen)",
            "it": "Fattoria con cataste di torba (o Casa colona con cataste di torba)",
        },
        "alt_en_title": "Farm with Stacks of Peat",
    },
    {
        "product_id": 15611339374940,
        "label": "Gospodarstwo w Nuenen",
        "old_pl_titles": ("Gospodarstwo w Nuenen", "Dom wiejski w Nuenen"),
        "new_pl_title": (
            "Wiejska chałupa w Nuenen "
            "(lub Chata i kobieta z kozą/Dom wiejski w Nuenen/Chata w Nuenen)"
        ),
        "original_title": "Boerderij in Nuenen (of Huisje en vrouw met geit/La Chaumière)",
        "english_title": "Farmhouse in Nuenen (or Cottage and Woman with Goat)",
        "locale_titles": {
            "en": "Farmhouse in Nuenen (or Cottage and Woman with Goat)",
            "de": "Bauernhaus in Nuenen (oder Bauernhaus und Frau mit Ziege)",
            "fr": (
                "Chaumière à Nuenen "
                "(ou Une chaumière/Chaumière et femme avec chèvre)"
            ),
            "es": (
                "Casa de campo en Nuenen "
                "(o Cabaña y mujer con cabra/Casa de campo con mujer y cabra)"
            ),
            "nl": "Boerderij in Nuenen (of Huisje en vrouw met geit/La Chaumière)",
            "it": "Fattoria a Nuenen (o Capanna con donna e capra)",
        },
        "alt_en_title": "Farmhouse in Nuenen",
    },
    {
        "product_id": 15611343864156,
        "label": "Drzewa oliwne",
        "old_pl_titles": ("Drzewa oliwne", "Olive Trees"),
        "new_pl_title": (
            "Gaje oliwne "
            "(lub Drzewa oliwne z błękitnym niebem/Drzewa oliwne/Gaj oliwny)"
        ),
        "original_title": "Olijfgaard (of Olijfbomen met blauwe lucht/Olijfbomen)",
        "english_title": "Olive Orchard (or Olive Trees/Olive Trees with Blue Sky)",
        "locale_titles": {
            "en": "Olive Orchard (or Olive Trees/Olive Trees with Blue Sky)",
            "de": "Olivenhain (oder Olivenbäume mit blauem Himmel/Olivenbäume)",
            "fr": (
                "Les Oliviers "
                "(ou Oliveraie avec ciel bleu/Les oliviers à Saint-Rémy)"
            ),
            "es": "El olivar (o Olivos con cielo azul/Olivos)",
            "nl": "Olijfgaard (of Olijfbomen met blauwe lucht/Olijfbomen)",
            "it": "Gli ulivi (o Uliveto con cielo blu/Alberi di ulivo)",
        },
        "alt_en_title": "Olive Trees",
    },
    {
        "product_id": 15611353792860,
        "label": "Dobry Samarytanin",
        "old_pl_titles": (
            "Dobry Samarytanin (według Delacroix) "
            "(występuje również pod tradycyjną nazwą biblijną jako Miłosierny Samarytanin).",
            "Dobry Samarytanin",
            "Miłosierny Samarytanin",
        ),
        "new_pl_title": (
            "Miłosierny Samarytanin (według Delacroix) (lub Miłosierny Samarytanin)"
        ),
        "original_title": (
            "De barmhartige Samaritaan (naar Delacroix) "
            "(of De barmhartige Samaritaan)"
        ),
        "english_title": (
            "The Good Samaritan (after Delacroix) (or The Good Samaritan)"
        ),
        "locale_titles": {
            "en": "The Good Samaritan (after Delacroix) (or The Good Samaritan)",
            "de": (
                "Der barmherzige Samariter (nach Delacroix) "
                "(oder Der barmherzige Samariter)"
            ),
            "fr": "Le Bon Samaritain (d'après Delacroix) (ou Le Bon Samaritain)",
            "es": (
                "El buen samaritano (según Delacroix) (o El buen samaritano)"
            ),
            "nl": (
                "De barmhartige Samaritaan (naar Delacroix) "
                "(of De barmhartige Samaritaan)"
            ),
            "it": "Il buon samaritano (da Delacroix) (o Il buon samaritano)",
        },
        "alt_en_title": "The Good Samaritan (after Delacroix)",
    },
    {
        "product_id": 15611346714972,
        "label": "Chlopka wiazaca snopy",
        "old_pl_titles": ("Chłopka wiążąca snopy (według Milleta)",),
        "new_pl_title": (
            "Chłopka wiążąca snopy (według Milleta) "
            "(lub Wieśniaczka wiążąca snopy/Żniwiarka)"
        ),
        "original_title": "Boerin die schoven bindt (naar Millet) (of Arenleesster)",
        "english_title": (
            "Peasant Woman Binding Sheaves (after Millet) "
            "(or Peasant Woman Binding Sheaves)"
        ),
        "locale_titles": {
            "en": (
                "Peasant Woman Binding Sheaves (after Millet) "
                "(or Peasant Woman Binding Sheaves)"
            ),
            "de": "Bäuerin beim Garbenbinden (nach Millet) (oder Die Ährenleserin)",
            "fr": "Paysanne liant des gerbes (d'après Millet) (ou La glaneuse)",
            "es": (
                "Campesina atando gavillas (según Millet) "
                "(o Campesina atando gavillas)"
            ),
            "nl": "Boerin die schoven bindt (naar Millet) (of Arenleesster)",
            "it": (
                "Contadina che lega i covoni (da Millet) "
                "(o Contadina che lega i covoni)"
            ),
        },
        "alt_en_title": "Peasant Woman Binding Sheaves (after Millet)",
    },
    {
        "product_id": 15611333280092,
        "label": "Brzeg Sekwany",
        "old_pl_titles": ("Brzeg Sekwany",),
        "new_pl_title": "Brzeg Sekwany (lub Wybrzeże Sekwany)",
        "original_title": "Oever van de Seine (of De oever van de Seine)",
        "english_title": "Bank of the Seine (or The Banks of the Seine)",
        "locale_titles": {
            "en": "Bank of the Seine (or The Banks of the Seine)",
            "de": "Das Seineufer (oder Seine-Ufer)",
            "fr": "Berges de la Seine (ou Les bords de la Seine)",
            "es": "Orillas del Sena (o Las orillas del Sena)",
            "nl": "Oever van de Seine (of De oever van de Seine)",
            "it": "Rive della Senna (o Sulle rive della Senna)",
        },
        "alt_en_title": "Bank of the Seine",
    },
    {
        "product_id": 15611333575004,
        "label": "Bielnik Scheveningen",
        "old_pl_titles": (
            "Bielnik w Scheveningen",
            "Blich w Scheveningen",
        ),
        "new_pl_title": (
            "Blich w Scheveningen (lub Pole bielenia płótna w Scheveningen)"
        ),
        "original_title": "Blekerij te Scheveningen (of Bleekveld te Scheveningen)",
        "english_title": (
            "Bleaching Ground at Scheveningen (or Bleaching Ground)"
        ),
        "locale_titles": {
            "en": "Bleaching Ground at Scheveningen (or Bleaching Ground)",
            "de": "Bleiche bei Scheveningen (oder Bleichfeld in Scheveningen)",
            "fr": (
                "Blanchisserie à Scheveningen "
                "(ou Le blanchissage à Scheveningen)"
            ),
            "es": (
                "El prado de lejía en Scheveningen "
                "(o Campo de blanqueo en Scheveningen)"
            ),
            "nl": "Blekerij te Scheveningen (of Bleekveld te Scheveningen)",
            "it": (
                "Campo di candeggio a Scheveningen "
                "(o Prato di candeggio a Scheveningen)"
            ),
        },
        "alt_en_title": "Bleaching Ground at Scheveningen",
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


def main() -> int:
    shop, token = sc.load_session()
    for cfg in PRODUCTS:
        _apply_product(shop, token, cfg)
    print("\nGotowe — 13 produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
