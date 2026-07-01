"""Poprawka tytulow: 19 produktow — Jansen, Knight, Leu, Lippi, Lorrain, Michelangelo, Moret, Pissarro (batch 12)."""
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
        "product_id": 15611528380764,
        "artist": "Johann Joseph Jansen",
        "label": "Jezioro Czterech Kantonow",
        "old_pl_titles": ("Widok na Jezioro Czterech Kantonów",),
        "new_pl_title": (
            "Jezioro Czterech Kantonów z drogą Axenstrasse "
            "(lub Widok na Jezioro Czterech Kantonów z drogą Axenstrasse)"
        ),
        "original_title": "Der Vierwaldstättersee mit der Axenstraße",
        "english_title": (
            "Lake Lucerne with the Axenstrasse "
            "(or View of Lake Lucerne with the Axenstrasse)"
        ),
        "locale_titles": {
            "en": (
                "Lake Lucerne with the Axenstrasse "
                "(or View of Lake Lucerne with the Axenstrasse)"
            ),
            "de": (
                "Der Vierwaldstättersee mit der Axenstraße "
                "(oder Blick auf den Vierwaldstättersee mit der Axenstraße)"
            ),
            "fr": (
                "Le lac des Quatre-Cantons avec l'Axenstrasse "
                "(ou Vue du lac des Quatre-Cantons avec l'Axenstrasse)"
            ),
            "es": (
                "El lago de los Cuatro Cantones con la Axenstrasse "
                "(o Vista del lago de los Cuatro Cantones con la Axenstrasse)"
            ),
            "nl": (
                "Het Vierwoudstrekenmeer met de Axenstrasse "
                "(of Gezicht op het Vierwoudstrekenmeer met de Axenstrasse)"
            ),
            "it": (
                "Il lago dei Quattro Cantoni con la Axenstrasse "
                "(o Veduta del lago dei Quattro Cantoni con la Axenstrasse)"
            ),
        },
        "alt_en_title": "Lake Lucerne with the Axenstrasse",
    },
    {
        "product_id": 15611312734556,
        "artist": "Daniel Ridgway Knight",
        "label": "Corka ogrodnika",
        "old_pl_titles": ("Córka ogrodnika",),
        "new_pl_title": "Córka ogrodnika",
        "original_title": "The Gardener's Daughter",
        "english_title": "The Gardener's Daughter",
        "locale_titles": {
            "en": "The Gardener's Daughter",
            "de": "Die Tochter des Gärtners",
            "fr": "La fille du jardinier",
            "es": "La hija del jardinero",
            "nl": "De dochter van de tuinman",
            "it": "La figlia del giardiniere",
        },
        "alt_en_title": "The Gardener's Daughter",
    },
    {
        "product_id": 15611311358300,
        "artist": "Daniel Ridgway Knight",
        "label": "Palenie chrustu",
        "old_pl_titles": ("Palenie chrustu",),
        "new_pl_title": "Palenie chrustu (lub Palenie gałęzi)",
        "original_title": "Burning Brushwood",
        "english_title": "Burning Brushwood (or Burning Weeds)",
        "locale_titles": {
            "en": "Burning Brushwood (or Burning Weeds)",
            "de": "Das Verbrennen von Reisig (oder Reisigbrennen)",
            "fr": "Le brûlage de broussailles (ou Le brûlage de brindilles)",
            "es": "La quema de maleza (o Quema de rastrojos)",
            "nl": "Het verbranden van sprokkelhout (of Sprokkelhout verbranden)",
            "it": "La bruciatura delle sterpaglie (o Bruciatura di rami secchi)",
        },
        "alt_en_title": "Burning Brushwood",
    },
    {
        "product_id": 15611311489372,
        "artist": "Daniel Ridgway Knight",
        "label": "W sadzie",
        "old_pl_titles": ("W sadzie",),
        "new_pl_title": "W sadzie (lub wiosna w sadzie)",
        "original_title": "In the Orchard",
        "english_title": "In the Orchard (or Springtime in the Orchard)",
        "locale_titles": {
            "en": "In the Orchard (or Springtime in the Orchard)",
            "de": "Im Obstgarten (oder Frühling im Obstgarten)",
            "fr": "Dans le verger (ou printemps dans le verger)",
            "es": "En el huerto (o primavera en el huerto)",
            "nl": "In de boomgaard (of lente in de boomgaard)",
            "it": "Nel frutteto (o primavera nel frutteto)",
        },
        "alt_en_title": "In the Orchard",
    },
    {
        "product_id": 15611312275804,
        "artist": "Daniel Ridgway Knight",
        "label": "Zabladzila",
        "old_pl_titles": ("Zabłądziła",),
        "new_pl_title": "Zabłądziła (lub zagubiona)",
        "original_title": "Lost",
        "english_title": "Lost (or Lost Her Way)",
        "locale_titles": {
            "en": "Lost (or Lost Her Way)",
            "de": "Verirrt (oder Verlaufen)",
            "fr": "Égarée (ou perdue)",
            "es": "Perdida (o extraviada)",
            "nl": "Verdwaald",
            "it": "Smarrita (o perduta)",
        },
        "alt_en_title": "Lost",
    },
    {
        "product_id": 15611312046428,
        "artist": "Daniel Ridgway Knight",
        "label": "Zrywanie kwiatow",
        "old_pl_titles": ("Zrywanie kwiatów",),
        "new_pl_title": "Kwiaty jabłoni (lub Zrywanie kwiatów)",
        "original_title": "Apple Blossoms",
        "english_title": "Apple Blossoms (or Spring Blossoms)",
        "locale_titles": {
            "en": "Apple Blossoms (or Spring Blossoms)",
            "de": "Apfelblüten (oder Frühlingsblüten)",
            "fr": "Fleurs de pommier (ou fleurs de printemps)",
            "es": "Flores de manzano (o flores de primavera)",
            "nl": "Appelbloesem (of voorjaarsbloesem)",
            "it": "Fiori di melo (o fiori di primavera)",
        },
        "alt_en_title": "Apple Blossoms",
    },
    {
        "product_id": 15611294089564,
        "artist": "August Wilhelm Leu",
        "label": "Gorskie jezioro Gosau",
        "old_pl_titles": ("Górskie jezioro z pasmem gór w tle",),
        "new_pl_title": (
            "Jezioro Gosau z Dachsteinem "
            "(lub Widok na jezioro Gosau i Dachstein)"
        ),
        "original_title": "Der Gosausee mit dem Dachstein",
        "english_title": (
            "Lake Gosau with the Dachstein "
            "(or View of Lake Gosau and the Dachstein)"
        ),
        "locale_titles": {
            "en": (
                "Lake Gosau with the Dachstein "
                "(or View of Lake Gosau and the Dachstein)"
            ),
            "de": (
                "Der Gosausee mit dem Dachstein "
                "(oder Blick auf den Gosausee mit dem Dachstein)"
            ),
            "fr": (
                "Le lac de Gosau avec le Dachstein "
                "(ou Vue du lac de Gosau avec le Dachstein)"
            ),
            "es": (
                "El lago Gosau con el Dachstein "
                "(o Vista del lago Gosau con el Dachstein)"
            ),
            "nl": (
                "De Gosausee met de Dachstein "
                "(of Gezicht op de Gosausee met de Dachstein)"
            ),
            "it": (
                "Il lago di Gosau con il Dachstein "
                "(o Veduta del lago di Gosau con il Dachstein)"
            ),
        },
        "alt_en_title": "Lake Gosau with the Dachstein",
    },
    {
        "product_id": 15611294318940,
        "artist": "August Wilhelm Leu",
        "label": "Krajobraz gorski Gosau",
        "old_pl_titles": ("Krajobraz górski",),
        "new_pl_title": (
            "Jezioro Gosau z widokiem na Dachstein (lub Jezioro Gosau i Dachstein)"
        ),
        "original_title": "Der Gosausee mit dem Dachstein",
        "english_title": (
            "Lake Gosau with the Dachstein (or Lake Gosau and the Dachstein)"
        ),
        "locale_titles": {
            "en": (
                "Lake Gosau with the Dachstein (or Lake Gosau and the Dachstein)"
            ),
            "de": (
                "Der Gosausee mit dem Dachstein "
                "(oder Der Gosausee und der Dachstein)"
            ),
            "fr": (
                "Le lac de Gosau avec le Dachstein "
                "(ou Le lac de Gosau et le Dachstein)"
            ),
            "es": (
                "El lago Gosau con el Dachstein (o El lago Gosau y el Dachstein)"
            ),
            "nl": "De Gosausee met de Dachstein (of De Gosausee en de Dachstein)",
            "it": (
                "Il lago di Gosau con il Dachstein "
                "(o Il lago di Gosau e il Dachstein)"
            ),
        },
        "alt_en_title": "Lake Gosau with the Dachstein",
    },
    {
        "product_id": 15611294581084,
        "artist": "August Wilhelm Leu",
        "label": "Mieniace sie jezioro",
        "old_pl_titles": (
            "Mieniące się górskie jezioro z dziewczętami w łodzi",
        ),
        "new_pl_title": (
            "Mieniące się górskie jezioro z dwiema dziewczętami w łodzi "
            "(lub Mieniące się górskie jezioro z dziewczętami w łodzi)"
        ),
        "original_title": "Glastender Gebirgssee mit zwei Mädchen im Boot",
        "english_title": (
            "Shimmering Mountain Lake with Two Girls in a Boat "
            "(or Glistening Mountain Lake with Two Girls in a Boat)"
        ),
        "locale_titles": {
            "en": (
                "Shimmering Mountain Lake with Two Girls in a Boat "
                "(or Glistening Mountain Lake with Two Girls in a Boat)"
            ),
            "de": (
                "Glastender Gebirgssee mit zwei Mädchen im Boot "
                "(oder Glänzender Gebirgssee mit zwei Mädchen im Boot)"
            ),
            "fr": (
                "Lac de montagne miroitant avec deux jeunes filles dans une barque "
                "(ou Lac de montagne scintillant avec deux filles dans une barque)"
            ),
            "es": (
                "Lago de montaña resplandeciente con dos jóvenes en una barca "
                "(o Lago de montaña centelleante con dos muchachas en un bote)"
            ),
            "nl": (
                "Glinsterend bergmeer met twee meisjes in een boot "
                "(of Schitterend bergmeer met twee meisjes in een boot)"
            ),
            "it": (
                "Lago di montagna scintillante con due ragazze in barca "
                "(o Lago di montagna luccicante con due fanciulle in barca)"
            ),
        },
        "alt_en_title": "Shimmering Mountain Lake with Two Girls in a Boat",
    },
    {
        "product_id": 15611294450012,
        "artist": "August Wilhelm Leu",
        "label": "Engstlenalp",
        "old_pl_titles": ("Na Engstlenalp",),
        "new_pl_title": "Na Engstlenalp (lub Krajobraz alpejski na Engstlenalp)",
        "original_title": "Auf der Engstlenalp",
        "english_title": (
            "On the Engstlenalp (or Alpine Landscape on the Engstlenalp)"
        ),
        "locale_titles": {
            "en": "On the Engstlenalp (or Alpine Landscape on the Engstlenalp)",
            "de": "Auf der Engstlenalp (oder Almlandschaft auf der Engstlenalp)",
            "fr": "Sur l'Engstlenalp (ou paysage alpin sur l'Engstlenalp)",
            "es": "En el Engstlenalp (o paisaje alpino en el Engstlenalp)",
            "nl": "Op de Engstlenalp (of alpenlandschap op de Engstlenalp)",
            "it": "Sull'Engstlenalp (o paesaggio alpino sull'Engstlenalp)",
        },
        "alt_en_title": "On the Engstlenalp",
    },
    {
        "product_id": 15611293958492,
        "artist": "August Wilhelm Leu",
        "label": "Pejzaz fiordu",
        "old_pl_titles": ("Pejzaż fiordu z lodowcem i reniferami",),
        "new_pl_title": (
            "Norweski krajobraz z bramą lodowcową i reniferami "
            "(lub Pejzaż fiordu z lodowcem i reniferami)"
        ),
        "original_title": "Norwegische Landschaft mit Gletschertor und Rentieren",
        "english_title": (
            "Norwegian Landscape with a Glacier Cave and Reindeer "
            "(or Norwegian Landscape with Glacier and Reindeer)"
        ),
        "locale_titles": {
            "en": (
                "Norwegian Landscape with a Glacier Cave and Reindeer "
                "(or Norwegian Landscape with Glacier and Reindeer)"
            ),
            "de": (
                "Norwegische Landschaft mit Gletschertor und Rentieren "
                "(oder Norwegischer Gletscher mit Rentieren)"
            ),
            "fr": (
                "Paysage norvégien avec porte de glacier et rennes "
                "(ou Paysage de fjord avec glacier et rennes)"
            ),
            "es": (
                "Paisaje noruego con puerta de glaciar y renos "
                "(o Paisaje de fiordo con glaciar y renos)"
            ),
            "nl": (
                "Noors landschap met gletsjerpoort en rendieren "
                "(of Fjordlandschap met gletsjer en rendieren)"
            ),
            "it": (
                "Paesaggio norvegese con porta di ghiacciaio e renne "
                "(o Paesaggio di fiordo con ghiacciaio e renne)"
            ),
        },
        "alt_en_title": "Norwegian Landscape with a Glacier Cave and Reindeer",
    },
    {
        "product_id": 15611293827420,
        "artist": "August Wilhelm Leu",
        "label": "Alpy Berneckie",
        "old_pl_titles": ("Scena w Alpach Berneńskich",),
        "new_pl_title": "Scena w Alpach Berneńskich (lub Z Alp Berneńskich)",
        "original_title": "Aus den Berner Alpen",
        "english_title": "From the Bernese Alps (or Scene in the Bernese Alps)",
        "locale_titles": {
            "en": "From the Bernese Alps (or Scene in the Bernese Alps)",
            "de": "Aus den Berner Alpen (oder Motiv aus den Berner Alpen)",
            "fr": "Dans les Alpes bernoises (ou scène dans les Alpes bernoises)",
            "es": "En los Alpes berneses (o escena en los Alpes berneses)",
            "nl": "In de Berner Alpen (of scène in de Berner Alpen)",
            "it": "Nelle Alpi bernesi (o scena nelle Alpi bernesi)",
        },
        "alt_en_title": "From the Bernese Alps",
    },
    {
        "product_id": 15611312931164,
        "artist": "Filippo Lippi",
        "label": "Madonna Lippi",
        "old_pl_titles": ("Madonna z Dzieciątkiem i dwoma aniołami",),
        "new_pl_title": (
            "Madonna z Dzieciątkiem i dwoma aniołami (lub Lippina)"
        ),
        "original_title": "Madonna col Bambino e due angeli",
        "english_title": (
            "Madonna and Child with Two Angels (or The Lippina)"
        ),
        "locale_titles": {
            "en": "Madonna and Child with Two Angels (or The Lippina)",
            "de": (
                "Maria mit dem Kind und zwei Engeln "
                "(oder Madonna mit dem Kind und zwei Engeln)"
            ),
            "fr": (
                "La Vierge à l'enfant avec deux anges (ou La Lippina)"
            ),
            "es": "Virgen con el Niño y dos ángeles (o La Lippina)",
            "nl": "Madonna met Kind en twee engelen (of Lippina)",
            "it": "Madonna col Bambino e due angeli (o Lippina)",
        },
        "alt_en_title": "Madonna and Child with Two Angels",
    },
    {
        "product_id": 15611524251996,
        "artist": "Claude Lorrain",
        "label": "Odpoczynek Egipt",
        "old_pl_titles": ("Odpoczynek w czasie ucieczki do Egiptu",),
        "new_pl_title": (
            "Krajobraz z odpoczynkiem podczas ucieczki do Egiptu "
            "(lub Odpoczynek podczas ucieczki do Egiptu)"
        ),
        "original_title": "Paysage avec le repos pendant la fuite en Égypte",
        "english_title": (
            "Landscape with the Rest on the Flight into Egypt "
            "(or Rest on the Flight into Egypt)"
        ),
        "locale_titles": {
            "en": (
                "Landscape with the Rest on the Flight into Egypt "
                "(or Rest on the Flight into Egypt)"
            ),
            "de": (
                "Landschaft mit der Ruhe auf der Flucht nach Ägypten "
                "(oder Ruhe auf der Flucht nach Ägypten)"
            ),
            "fr": (
                "Paysage avec le repos pendant la fuite en Égypte "
                "(ou Le repos pendant la fuite en Égypte)"
            ),
            "es": (
                "Paisaje con el descanso en la huida a Egipto "
                "(o El descanso en la huida a Egipto)"
            ),
            "nl": (
                "Landschap met de rust op de vlucht naar Egypte "
                "(of Rust op de vlucht naar Egypte)"
            ),
            "it": (
                "Paesaggio con riposo durante la fuga in Egitto "
                "(o Riposo durante la fuga in Egitto)"
            ),
        },
        "alt_en_title": "Landscape with the Rest on the Flight into Egypt",
    },
    {
        "product_id": 15611423687004,
        "artist": "Michelangelo",
        "label": "Udreka sw Antoniego",
        "old_pl_titles": ("Udręka świętego Antoniego",),
        "new_pl_title": (
            "Udręka świętego Antoniego (lub Kuszenie świętego Antoniego)"
        ),
        "original_title": "Tormento di sant'Antonio",
        "english_title": (
            "The Torment of Saint Anthony (or The Temptation of Saint Anthony)"
        ),
        "locale_titles": {
            "en": (
                "The Torment of Saint Anthony (or The Temptation of Saint Anthony)"
            ),
            "de": (
                "Die Peinigung des heiligen Antonius "
                "(oder Die Versuchung des heiligen Antonius)"
            ),
            "fr": (
                "Le tourment de saint Antoine (ou La tentation de saint Antoine)"
            ),
            "es": (
                "El tormento de san Antonio (o La tentación de san Antonio)"
            ),
            "nl": (
                "De kwelling van de heilige Antonius "
                "(of De verzoeking van de heilige Antonius)"
            ),
            "it": "Tormento di sant'Antonio (o Tentazione di sant'Antonio)",
        },
        "alt_en_title": "The Torment of Saint Anthony",
    },
    {
        "product_id": 15611319419228,
        "artist": "Henry Moret",
        "label": "Sianokosy",
        "old_pl_titles": ("Sianokosy",),
        "new_pl_title": "Sianokosy (lub Zbiór siana)",
        "original_title": "La fenaison",
        "english_title": "Haymaking (or The Hay Harvest)",
        "locale_titles": {
            "en": "Haymaking (or The Hay Harvest)",
            "de": "Die Heuernte (oder Das Heumachen)",
            "fr": "La fenaison (ou La récolte du foin)",
            "es": "La siega del heno (o La cosecha de heno)",
            "nl": "De hooioogst (of Hooimaken)",
            "it": "La fienagione (o La raccolta del fieno)",
        },
        "alt_en_title": "Haymaking",
    },
    {
        "product_id": 15611305034076,
        "artist": "Camille Pissarro",
        "label": "Domy Bougival",
        "old_pl_titles": ("Domy w Bougival (jesień)",),
        "new_pl_title": (
            "Domy w Bougival (lub Krajobraz w Bougival/Domy w Bougival (jesień))"
        ),
        "original_title": "Maisons à Bougival",
        "english_title": (
            "Houses at Bougival "
            "(or Landscape at Bougival/Houses at Bougival (Autumn))"
        ),
        "locale_titles": {
            "en": (
                "Houses at Bougival "
                "(or Landscape at Bougival/Houses at Bougival (Autumn))"
            ),
            "de": (
                "Häuser in Bougival "
                "(oder Landschaft in Bougival/Häuser in Bougival (Herbst))"
            ),
            "fr": (
                "Maisons à Bougival "
                "(ou paysage à Bougival/maisons à Bougival (automne))"
            ),
            "es": (
                "Casas en Bougival "
                "(o paisaje en Bougival/casas en Bougival (otoño))"
            ),
            "nl": (
                "Huizen in Bougival "
                "(of landschap in Bougival/huizen in Bougival (herfst))"
            ),
            "it": (
                "Case a Bougival "
                "(o paesaggio a Bougival/case a Bougival (autunno))"
            ),
        },
        "alt_en_title": "Houses at Bougival",
    },
    {
        "product_id": 15611305197916,
        "artist": "Camille Pissarro",
        "label": "Poranne slonce Eragny",
        "old_pl_titles": ("Efekt porannego słońca, Éragny",),
        "new_pl_title": "Poranne słońce, Éragny (lub Efekt porannego słońca, Éragny)",
        "original_title": "Soleil du matin, Éragny",
        "english_title": "Morning Sun, Éragny (or Morning Sunlight, Éragny)",
        "locale_titles": {
            "en": "Morning Sun, Éragny (or Morning Sunlight, Éragny)",
            "de": "Morgensonne, Éragny (oder Effekt der Morgensonne, Éragny)",
            "fr": "Soleil du matin, Éragny (ou Effet de soleil du matin, Éragny)",
            "es": "Sol de la mañana, Éragny (o Efecto de sol de la mañana, Éragny)",
            "nl": "Ochtendzon, Éragny (of Effect van de ochtendzon, Éragny)",
            "it": "Sole del mattino, Éragny (o Effetto del sole del mattino, Éragny)",
        },
        "alt_en_title": "Morning Sun, Éragny",
    },
    {
        "product_id": 15611305951580,
        "artist": "Camille Pissarro",
        "label": "Kobieta myjaca stopy",
        "old_pl_titles": ("Kobieta myjąca stopy w strumieniu",),
        "new_pl_title": (
            "Kobieta myjąca stopy (lub kobieta myjąca stopy w strumieniu)"
        ),
        "original_title": "La laveuse de pieds",
        "english_title": (
            "Woman Washing Her Feet (or Woman Bathing Her Feet)"
        ),
        "locale_titles": {
            "en": "Woman Washing Her Feet (or Woman Bathing Her Feet)",
            "de": (
                "Frau, die sich die Füße wäscht (oder Die Fußwascherin)"
            ),
            "fr": "La laveuse de pieds (ou femme se lavant les pieds)",
            "es": "Mujer lavándose los pies (o la lavadora de pies)",
            "nl": "Vrouw die haar voeten wast (of de voetwasster)",
            "it": "Donna che si lava i piedi (o la lavatrice di piedi)",
        },
        "alt_en_title": "Woman Washing Her Feet",
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
    print("\nGotowe — 19 produktow (batch 12).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
