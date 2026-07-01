"""Poprawka tytulow: 17 produktow — Daubigny, David, Diemer, Dupre, Fantin, Hassam, Lorrain (batch 11)."""
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


PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15611274821980,
        "artist": "Charles François Daubigny",
        "label": "Stawy w Gylieu",
        "old_pl_titles": ("Stawy w Gylieu",),
        "new_pl_title": "Stawy w Gylieu (lub Staw w Gylieu)",
        "original_title": "Les étangs de Gylieu",
        "english_title": "The Ponds of Gylieu (or The Pond of Gylieu)",
        "locale_titles": {
            "en": "The Ponds of Gylieu (or The Pond of Gylieu)",
            "de": "Die Teiche von Gylieu (oder Der Teich von Gylieu)",
            "fr": "Les étangs de Gylieu (ou L'étang de Gylieu)",
            "es": "Los estanques de Gylieu (o El estanque de Gylieu)",
            "nl": "De vijvers van Gylieu (of De vijver van Gylieu)",
            "it": "Gli stagni di Gylieu (o Lo stagno di Gylieu)",
        },
        "alt_en_title": "The Ponds of Gylieu",
    },
    {
        "product_id": 15611274756444,
        "artist": "Charles François Daubigny",
        "label": "Wiosenny pejzaż",
        "old_pl_titles": ("Wiosenny pejzaż",),
        "new_pl_title": "Wiosna (lub Wiosenny pejzaż)",
        "original_title": "Le Printemps",
        "english_title": "Springtime (or Spring or Spring Landscape)",
        "locale_titles": {
            "en": "Springtime (or Spring or Spring Landscape)",
            "de": "Der Frühling (oder Frühlingslandschaft)",
            "fr": "Le printemps (ou paysage de printemps)",
            "es": "La primavera (o paisaje de primavera)",
            "nl": "De lente (of lentelandschap)",
            "it": "La primavera (o paesaggio primaverile)",
        },
        "alt_en_title": "Springtime",
    },
    {
        "product_id": 15611525103964,
        "artist": "Jacques-Louis David",
        "label": "Amor i Psyche",
        "old_pl_titles": ("Amor i Psyche",),
        "new_pl_title": "Amor i Psyche (lub Kupidyn i Psyche)",
        "original_title": "Amour et Psyché",
        "english_title": "Cupid and Psyche",
        "locale_titles": {
            "en": "Cupid and Psyche",
            "de": "Amor und Psyche",
            "fr": "Amour et Psyché",
            "es": "Amor y Psique",
            "nl": "Amor en Psyche",
            "it": "Amore e Psiche",
        },
        "alt_en_title": "Cupid and Psyche",
    },
    {
        "product_id": 15611525398876,
        "artist": "Jacques-Louis David",
        "label": "Napoleon Bernarda",
        "old_pl_titles": ("Napoleon na przełęczy Wielkiego Świętego Bernarda",),
        "new_pl_title": (
            "Napoleon na przełęczy Wielkiego Świętego Bernarda "
            "(lub Bonaparte na przełęczy Wielkiego Świętego Bernarda/"
            "Napoleon przekraczający Alpy)"
        ),
        "original_title": "Bonaparte franchissant le Grand-Saint-Bernard",
        "english_title": (
            "Napoleon Crossing the Alps "
            "(or Bonaparte Crossing the Grand Saint-Bernard "
            "or Napoleon at the Great St Bernard Pass)"
        ),
        "locale_titles": {
            "en": (
                "Napoleon Crossing the Alps "
                "(or Bonaparte Crossing the Grand Saint-Bernard "
                "or Napoleon at the Great St Bernard Pass)"
            ),
            "de": (
                "Napoleon am Großen St. Bernhard "
                "(oder Bonaparte am Großen St. Bernhard "
                "oder Napoleon überquert die Alpen)"
            ),
            "fr": (
                "Bonaparte franchissant le Grand-Saint-Bernard "
                "(ou Napoléon franchissant le col du Grand-Saint-Bernard "
                "ou Napoléon traversant les Alpes)"
            ),
            "es": (
                "Napoleón cruzando los Alpes "
                "(o Bonaparte cruzando el paso de Gran San Bernardo)"
            ),
            "nl": (
                "Napoleon trekt over de Alpen "
                "(of Bonaparte trekt over de Grote Sint-Bernhardpas)"
            ),
            "it": (
                "Napoleone valica le Alpi "
                "(o Bonaparte valica il Gran San Bernardo "
                "o Napoleone al passo del Gran San Bernardo)"
            ),
        },
        "alt_en_title": "Napoleon Crossing the Alps",
    },
    {
        "product_id": 15611525890396,
        "artist": "Jacques-Louis David",
        "label": "Napoleon Tuileries",
        "old_pl_titles": ("Napoleon w swoim gabinecie w pałacu Tuileries",),
        "new_pl_title": (
            "Napoleon w swoim gabinecie w pałacu Tuileries "
            "(lub Cesarz Napoleon w swoim gabinecie w pałacu Tuileries)"
        ),
        "original_title": "Napoléon dans son cabinet de travail",
        "english_title": (
            "The Emperor Napoleon in His Study at the Tuileries "
            "(or Napoleon in His Study)"
        ),
        "locale_titles": {
            "en": (
                "The Emperor Napoleon in His Study at the Tuileries "
                "(or Napoleon in His Study)"
            ),
            "de": (
                "Kaiser Napoleon in seinem Arbeitszimmer im Tuilerien-Palast "
                "(oder Napoleon in seinem Arbeitszimmer)"
            ),
            "fr": (
                "Napoléon dans son cabinet de travail "
                "(ou l'empereur Napoléon dans son cabinet de travail aux Tuileries)"
            ),
            "es": (
                "El emperador Napoleón en su gabinete de trabajo en las Tullerías "
                "(o Napoleón en su gabinete de trabajo)"
            ),
            "nl": (
                "Keizer Napoleon in zijn studeerkamer in de Tuilerieën "
                "(of Napoleon in zijn werkkamer)"
            ),
            "it": (
                "L'imperatore Napoleone nel suo studio alle Tuileries "
                "(o Napoleone nel suo gabinetto di lavoro)"
            ),
        },
        "alt_en_title": "The Emperor Napoleon in His Study at the Tuileries",
    },
    {
        "product_id": 15611419558236,
        "artist": "Michael Zeno Diemer",
        "label": "Fregata Rio",
        "old_pl_titles": ("Fregata u wybrzeży w pobliżu Rio de Janeiro",),
        "new_pl_title": (
            "Fregata u wybrzeży w pobliżu Rio de Janeiro "
            "(lub Fregata u wybrzeży Rio de Janeiro)"
        ),
        "original_title": "Fregatte vor der Küste von Rio de Janeiro",
        "english_title": (
            "Frigate off the Coast of Rio de Janeiro "
            "(or Frigate off the Coast Near Rio de Janeiro)"
        ),
        "locale_titles": {
            "en": (
                "Frigate off the Coast of Rio de Janeiro "
                "(or Frigate off the Coast Near Rio de Janeiro)"
            ),
            "de": (
                "Fregatte vor der Küste von Rio de Janeiro "
                "(oder Fregatte vor Rio de Janeiro)"
            ),
            "fr": (
                "Frégate au large de la côte de Rio de Janeiro "
                "(ou frégate près de Rio de Janeiro)"
            ),
            "es": (
                "Fragata frente a la costa de Río de Janeiro "
                "(o fragata cerca de Río de Janeiro)"
            ),
            "nl": (
                "Fregat voor de kust van Rio de Janeiro "
                "(of fregat nabij Rio de Janeiro)"
            ),
            "it": (
                "Fregata al largo della costa di Rio de Janeiro "
                "(o fregata nei pressi di Rio de Janeiro)"
            ),
        },
        "alt_en_title": "Frigate off the Coast of Rio de Janeiro",
    },
    {
        "product_id": 15611421098332,
        "artist": "Michael Zeno Diemer",
        "label": "Latający Holender",
        "old_pl_titles": ("Latający Holender",),
        "new_pl_title": "Latający Holender",
        "original_title": "Der fliegende Holländer",
        "english_title": "The Flying Dutchman",
        "locale_titles": {
            "en": "The Flying Dutchman",
            "de": "Der fliegende Holländer",
            "fr": "Le Hollandais volant (ou Le Vaisseau fantôme)",
            "es": "El holandés errante",
            "nl": "De vliegende Hollander",
            "it": "L'olandese volante",
        },
        "alt_en_title": "The Flying Dutchman",
    },
    {
        "product_id": 15611421655388,
        "artist": "Michael Zeno Diemer",
        "label": "Latający Holender koga",
        "old_pl_titles": (
            "Latający Holender (dwumasztowa koga z wydętymi żaglami)",
            "Latający Holender",
        ),
        "new_pl_title": "Latający Holender",
        "original_title": "Der fliegende Holländer",
        "english_title": "The Flying Dutchman",
        "locale_titles": {
            "en": "The Flying Dutchman",
            "de": "Der fliegende Holländer",
            "fr": "Le Hollandais volant (ou Le Vaisseau fantôme)",
            "es": "El holandés errante",
            "nl": "De vliegende Hollander",
            "it": "L'olandese volante",
        },
        "alt_en_title": "The Flying Dutchman",
    },
    {
        "product_id": 15611420279132,
        "artist": "Michael Zeno Diemer",
        "label": "Skaliste wybrzeże",
        "old_pl_titles": ("Skaliste wybrzeże o wczesnym poranku",),
        "new_pl_title": (
            "Skaliste wybrzeże o poranku "
            "(lub Skaliste wybrzeże o wczesnym poranku)"
        ),
        "original_title": "Felsige Küste am Morgen",
        "english_title": (
            "Rocky Coast in the Morning (or Rocky Coast in the Early Morning)"
        ),
        "locale_titles": {
            "en": (
                "Rocky Coast in the Morning (or Rocky Coast in the Early Morning)"
            ),
            "de": (
                "Felsige Küste am Morgen (oder Felsige Küste am frühen Morgen)"
            ),
            "fr": (
                "Côte rocheuse au matin (ou Côte rocheuse au petit matin)"
            ),
            "es": (
                "Costa rocosa por la mañana "
                "(o Costa rocosa a primera hora de la mañana)"
            ),
            "nl": (
                "Rotsachtige kust in de ochtend "
                "(of Rotsachtige kust in de vroege ochtend)"
            ),
            "it": (
                "Costa rocciosa al mattino (o Costa rocciosa di prima mattina)"
            ),
        },
        "alt_en_title": "Rocky Coast in the Morning",
    },
    {
        "product_id": 15611420705116,
        "artist": "Michael Zeno Diemer",
        "label": "Trójmasztowiec na morzu",
        "old_pl_titles": ("Trójmasztowiec na morzu",),
        "new_pl_title": (
            "Trójmasztowiec na pełnym morzu (lub Trójmasztowiec na wzburzonym morzu)"
        ),
        "original_title": "Dreimaster auf hoher See",
        "english_title": (
            "Three-Master on the High Seas (or Three-Master on a Rough Sea)"
        ),
        "locale_titles": {
            "en": (
                "Three-Master on the High Seas (or Three-Master on a Rough Sea)"
            ),
            "de": (
                "Dreimaster auf hoher See (oder Dreimaster auf stürmischer See)"
            ),
            "fr": (
                "Trois-mâts en haute mer (ou trois-mâts sur une mer agitée)"
            ),
            "es": (
                "Tres mástiles en alta mar (o tres mástiles en un mar agitado)"
            ),
            "nl": (
                "Driemaster op volle zee (of driemaster op een onstuimige zee)"
            ),
            "it": (
                "Veliero a tre alberi in alto mare (o tre alberi in mare agitato)"
            ),
        },
        "alt_en_title": "Three-Master on the High Seas",
    },
    {
        "product_id": 15611423162716,
        "artist": "Michael Zeno Diemer",
        "label": "Trójmasztowiec na pełnym morzu",
        "old_pl_titles": ("Trójmasztowiec na pełnym morzu",),
        "new_pl_title": (
            "Trójmasztowiec na pełnym morzu (lub Trójmasztowiec na wzburzonym morzu)"
        ),
        "original_title": "Dreimaster auf hoher See",
        "english_title": (
            "Three-Master on the High Seas (or Three-Master on a Rough Sea)"
        ),
        "locale_titles": {
            "en": (
                "Three-Master on the High Seas (or Three-Master on a Rough Sea)"
            ),
            "de": (
                "Dreimaster auf hoher See (oder Dreimaster auf bewegter See)"
            ),
            "fr": (
                "Trois-mâts en haute mer (ou Trois-mâts sur une mer agitée)"
            ),
            "es": (
                "Tres mástiles en alta mar (o Tres mástiles en un mar agitado)"
            ),
            "nl": (
                "Driemaster op volle zee (of Driemaster op een onstuimige zee)"
            ),
            "it": (
                "Veliero a tre alberi in alto mare "
                "(o Veliero a tre alberi in un mare mosso)"
            ),
        },
        "alt_en_title": "Three-Master on the High Seas",
    },
    {
        "product_id": 15611422638428,
        "artist": "Michael Zeno Diemer",
        "label": "Trójmasztowiec Messina",
        "old_pl_titles": ("Trójmasztowiec w Cieśninie Mesyńskiej",),
        "new_pl_title": "Trójmasztowiec w Cieśninie Mesyńskiej",
        "original_title": "Dreimaster in der Straße von Messina",
        "english_title": (
            "Three-Master in the Strait of Messina "
            "(or A Three-Master in the Strait of Messina)"
        ),
        "locale_titles": {
            "en": (
                "Three-Master in the Strait of Messina "
                "(or A Three-Master in the Strait of Messina)"
            ),
            "de": (
                "Dreimaster in der Straße von Messina "
                "(oder Ein Dreimaster in der Straße von Messina)"
            ),
            "fr": (
                "Trois-mâts dans le détroit de Messine "
                "(ou Un trois-mâts dans le détroit de Messine)"
            ),
            "es": (
                "Tres mástiles en el estrecho de Mesina "
                "(o Un tres mástiles en el estrecho de Mesina)"
            ),
            "nl": (
                "Driemaster in de Straat van Messina "
                "(of Een driemaster in de Straat van Messina)"
            ),
            "it": (
                "Veliero a tre alberi nello stretto di Messina "
                "(o Un tre alberi nello stretto di Messina)"
            ),
        },
        "alt_en_title": "Three-Master in the Strait of Messina",
    },
    {
        "product_id": 15611422114140,
        "artist": "Michael Zeno Diemer",
        "label": "Trójmasztowy żaglowiec",
        "old_pl_titles": ("Trójmasztowy żaglowiec",),
        "new_pl_title": (
            "Trójmasztowiec przy górzystym wybrzeżu "
            "(lub Trójmasztowy żaglowiec przy górzystym wybrzeżu)"
        ),
        "original_title": "Dreimaster vor gebirgiger Küste",
        "english_title": (
            "Three-Master off a Mountainous Coast "
            "(or Three-Masted Sailing Ship off a Mountainous Coast)"
        ),
        "locale_titles": {
            "en": (
                "Three-Master off a Mountainous Coast "
                "(or Three-Masted Sailing Ship off a Mountainous Coast)"
            ),
            "de": (
                "Dreimaster vor gebirgiger Küste "
                "(oder Dreimaster vor einer gebirgigen Küste)"
            ),
            "fr": (
                "Trois-mâts devant une côte montagneuse "
                "(ou Trois-mâts au large d'une côte montagneuse)"
            ),
            "es": (
                "Tres mástiles frente a una costa montañosa "
                "(o Velero de tres mástiles frente a una costa montañosa)"
            ),
            "nl": "Driemaster voor een bergachtige kust",
            "it": (
                "Veliero a tre alberi davanti a una costa montuosa "
                "(o Tre alberi davanti a una costa montuosa)"
            ),
        },
        "alt_en_title": "Three-Master off a Mountainous Coast",
    },
    {
        "product_id": 15611532509532,
        "artist": "Julien Dupré",
        "label": "Krnąbrna krowa",
        "old_pl_titles": ("Krnąbrna krowa",),
        "new_pl_title": "Krnąbrna krowa (lub Uparta krowa)",
        "original_title": "La vache récalcitrante",
        "english_title": "The Stubborn Cow (or The Recalcitrant Cow)",
        "locale_titles": {
            "en": "The Stubborn Cow (or The Recalcitrant Cow)",
            "de": "Die widerspenstige Kuh (oder Die eigensinnige Kuh)",
            "fr": "La vache récalcitrante (ou La vache difficile)",
            "es": "La vaca recalcitrante (o La vaca obstinada)",
            "nl": "De weerspannige koe (of De koppige koe)",
            "it": "La mucca recalcitrante (o La mucca ostinata)",
        },
        "alt_en_title": "The Stubborn Cow",
    },
    {
        "product_id": 15611315749212,
        "artist": "Henri Fantin-Latour",
        "label": "Białe róże",
        "old_pl_titles": ("Martwa natura z białymi różami",),
        "new_pl_title": "Białe róże (lub Martwa natura z białymi różami)",
        "original_title": "Roses blanches",
        "english_title": "White Roses",
        "locale_titles": {
            "en": "White Roses",
            "de": "Weiße Rosen",
            "fr": "Roses blanches",
            "es": "Rosas blancas",
            "nl": "Witte rozen",
            "it": "Rose bianche",
        },
        "alt_en_title": "White Roses",
    },
    {
        "product_id": 15611310375260,
        "artist": "Childe Hassam",
        "label": "Łąka w Concord",
        "old_pl_titles": ("Łąka w Concord",),
        "new_pl_title": "Łąka w Concord (lub Łąka, Concord)",
        "original_title": "Concord Meadow",
        "english_title": "Concord Meadow",
        "locale_titles": {
            "en": "Concord Meadow",
            "de": "Concord-Wiese (oder Wiese in Concord)",
            "fr": "Le pré de Concord (ou prairie à Concord)",
            "es": "El prado de Concord (o prado en Concord)",
            "nl": "De weide van Concord (of weide in Concord)",
            "it": "Il prato di Concord (o prato a Concord)",
        },
        "alt_en_title": "Concord Meadow",
    },
    {
        "product_id": 15611524481372,
        "artist": "Claude Lorrain",
        "label": "Trojanki",
        "old_pl_titles": ("Trojanki podpalające swoją flotę",),
        "new_pl_title": (
            "Trojanki podpalające swoją flotę "
            "(lub Trojanki podpalające swą flotę)"
        ),
        "original_title": "Les Troyennes brûlant leur flotte",
        "english_title": "The Trojan Women Setting Fire to Their Fleet",
        "locale_titles": {
            "en": "The Trojan Women Setting Fire to Their Fleet",
            "de": (
                "Die Trojanerinnen setzen ihre Flotte in Brand "
                "(oder Die trojanischen Frauen stecken ihre Flotte in Brand)"
            ),
            "fr": (
                "Les Troyennes brûlant leur flotte "
                "(ou Les femmes troyennes brûlant leur flotte)"
            ),
            "es": (
                "Las troyanas prendiendo fuego a su flota "
                "(o Las troyanas quemando su flota)"
            ),
            "nl": (
                "De Trojaanse vrouwen steken hun vloot in brand "
                "(of Trojaanse vrouwen steken hun vloot in brand)"
            ),
            "it": (
                "Le troiane incendiano la loro flotta "
                "(o Le donne troiane che incendiano la loro flotta)"
            ),
        },
        "alt_en_title": "The Trojan Women Setting Fire to Their Fleet",
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
    print("\nGotowe — 17 produktow (batch 11).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
