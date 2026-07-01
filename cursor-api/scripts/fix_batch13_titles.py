"""Poprawka tytulow: batch 13 — Achenbach (5), Aivazovsky (13), Bakhuizen (3)."""
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
        "product_id": 15548948152668,
        "artist": "Andreas Achenbach",
        "label": "Holownik Ostende",
        "old_pl_titles": (
            "Holownik opuszczający port w Ostendzie w pełnym świetle dnia",
        ),
        "new_pl_title": (
            "Holownik opuszczający port w Ostendzie podczas przypływu "
            "(lub Holownik opuszczający port w Ostendzie w okresie rozkwitu)"
        ),
        "original_title": "Ein Schlepper verlässt den Hafen von Ostende bei Flut",
        "english_title": (
            "A Tug Leaving the Port of Ostend at High Tide "
            "(or Towboat Leaving the Port of Ostend at High Tide)"
        ),
        "locale_titles": {
            "en": (
                "A Tug Leaving the Port of Ostend at High Tide "
                "(or Towboat Leaving the Port of Ostend at High Tide)"
            ),
            "de": "Ein Schlepper verlässt den Hafen von Ostende bei Flut",
            "fr": "Un remorqueur quittant le port d'Ostende à marée haute",
            "es": "Un remolcador saliendo del puerto de Ostende con marea alta",
            "nl": "Een sleepboot verlaat de haven van Oostende bij hoogtij",
            "it": "Un rimorchiatore che lascia il porto di Ostenda con l'alta marea",
        },
        "alt_en_title": "A Tug Leaving the Port of Ostend at High Tide",
    },
    {
        "product_id": 15548946809180,
        "artist": "Andreas Achenbach",
        "label": "Parowiec kołowy",
        "old_pl_titles": ("Parowiec kołowy na wzburzonym morzu",),
        "new_pl_title": (
            "Parowiec kołowy na wzburzonym morzu "
            "(lub Parowiec kołowy podczas sztormu)"
        ),
        "original_title": "Raddampfer in stürmischer See",
        "english_title": (
            "Paddlesteamer in Stormy Weather (or Paddle Steamer in a Stormy Sea)"
        ),
        "locale_titles": {
            "en": "Paddlesteamer in Stormy Weather (or Paddle Steamer in a Stormy Sea)",
            "de": (
                "Raddampfer in stürmischer See "
                "(oder Raddampfer in schwerer See)"
            ),
            "fr": "Bateau à vapeur à aubes dans la mer en tempête",
            "es": (
                "Vapor de paletas en el mar proceloso "
                "(o Vapor de ruedas en una tormenta)"
            ),
            "nl": (
                "Raderstoomboot op een stormachtige zee "
                "(of Raderstoomboot in stormachtig weer)"
            ),
            "it": (
                "Battello a vapore in mare in tempesta "
                "(o Piroscafo a ruote in mare mosso)"
            ),
        },
        "alt_en_title": "Paddlesteamer in Stormy Weather",
    },
    {
        "product_id": 15548932129116,
        "artist": "Andreas Achenbach",
        "label": "Plaża Scheveningen LVR",
        "old_pl_titles": ("Plaża w Scheveningen",),
        "new_pl_title": (
            "Plaża w Scheveningen (LVR-LandesMuseum Bonn) "
            "(lub Wybrzeże w Scheveningen)"
        ),
        "original_title": "Der Strand von Scheveningen (LVR-LandesMuseum Bonn)",
        "english_title": (
            "The Beach at Scheveningen (LVR-LandesMuseum Bonn) "
            "(or Beach at Scheveningen)"
        ),
        "locale_titles": {
            "en": (
                "The Beach at Scheveningen (LVR-LandesMuseum Bonn) "
                "(or Beach at Scheveningen)"
            ),
            "de": "Der Strand von Scheveningen (LVR-LandesMuseum Bonn)",
            "fr": "La plage de Scheveningen (LVR-LandesMuseum Bonn)",
            "es": "La playa de Scheveningen (LVR-LandesMuseum Bonn)",
            "nl": "Het strand van Scheveningen (LVR-LandesMuseum Bonn)",
            "it": "La spiaggia di Scheveningen (LVR-LandesMuseum Bonn)",
        },
        "alt_en_title": "The Beach at Scheveningen (LVR-LandesMuseum Bonn)",
    },
    {
        "product_id": 15548947956060,
        "artist": "Andreas Achenbach",
        "label": "Plaża Scheveningen 1893",
        "old_pl_titles": ("Plaża w Scheveningen",),
        "new_pl_title": (
            "Na plaży w Scheveningen (1893) (lub Plaża w Scheveningen (1893))"
        ),
        "original_title": "Am Strand von Scheveningen (1893)",
        "english_title": (
            "On the Beach at Scheveningen (1893) "
            "(or The Beach at Scheveningen (1893))"
        ),
        "locale_titles": {
            "en": (
                "On the Beach at Scheveningen (1893) "
                "(or The Beach at Scheveningen (1893))"
            ),
            "de": "Am Strand von Scheveningen (1893)",
            "fr": (
                "Sur la plage de Scheveningen (1893) "
                "(ou La plage de Scheveningen (1893))"
            ),
            "es": (
                "En la playa de Scheveningen (1893) "
                "(o La playa de Scheveningen (1893))"
            ),
            "nl": (
                "Op het strand van Scheveningen (1893) "
                "(of Het strand van Scheveningen (1893))"
            ),
            "it": (
                "Sulla spiaggia di Scheveningen (1893) "
                "(o La spiaggia di Scheveningen (1893))"
            ),
        },
        "alt_en_title": "On the Beach at Scheveningen (1893)",
    },
    {
        "product_id": 15548947464540,
        "artist": "Andreas Achenbach",
        "label": "Sztorm Norwegia",
        "old_pl_titles": ("Sztorm u wybrzeży Norwegii",),
        "new_pl_title": (
            "Sztorm na morzu u wybrzeży Norwegii (lub Sztorm u wybrzeży Norwegii)"
        ),
        "original_title": "Seesturm an der norwegischen Küste",
        "english_title": (
            "Sea Storm on the Norwegian Coast "
            "(or Storm at Sea off the Norwegian Coast)"
        ),
        "locale_titles": {
            "en": (
                "Sea Storm on the Norwegian Coast "
                "(or Storm at Sea off the Norwegian Coast)"
            ),
            "de": "Seesturm an der norwegischen Küste",
            "fr": "Tempête en mer sur la côte norvégienne",
            "es": "Tormenta marina en la costa noruega",
            "nl": "Zeestorm aan de Noorse kust",
            "it": "Tempesta di mare sulla costa norvegese",
        },
        "alt_en_title": "Sea Storm on the Norwegian Coast",
    },
    {
        "product_id": 15549060677980,
        "artist": "Ivan Aivazovsky",
        "label": "Biarritz",
        "old_pl_titles": ("Biarritz",),
        "new_pl_title": "Biarritz (lub Plaża w Biarritz (1889))",
        "original_title": "Биарриц",
        "english_title": "Biarritz (or The Beach at Biarritz (1889))",
        "locale_titles": {
            "en": "Biarritz (or The Beach at Biarritz (1889))",
            "de": "Biarritz (oder Der Strand von Biarritz (1889))",
            "fr": "Biarritz (ou La plage de Biarritz (1889))",
            "es": "Biarritz (o La playa de Biarritz (1889))",
            "nl": "Biarritz (of Het strand van Biarritz (1889))",
            "it": "Biarritz (o La spiaggia di Biarritz (1889))",
        },
        "alt_en_title": "Biarritz",
    },
    {
        "product_id": 15549065331036,
        "artist": "Ivan Aivazovsky",
        "label": "Burza",
        "old_pl_titles": ("Burza",),
        "new_pl_title": "Burza (1855) (lub Sztorm (1855))",
        "original_title": "Буря",
        "english_title": "Tempest (1855) (or Storm (1855))",
        "locale_titles": {
            "en": "Tempest (1855) (or Storm (1855))",
            "de": "Sturm (1855) (oder Der Sturm (1855))",
            "fr": "Tempête (1855) (ou La tempête (1855))",
            "es": "Tempestad (1855) (o Tormenta (1855))",
            "nl": "Storm (1855) (of De storm (1855))",
            "it": "Tempesta (1855) (o La tempesta (1855))",
        },
        "alt_en_title": "Tempest (1855)",
    },
    {
        "product_id": 15549067985244,
        "artist": "Ivan Aivazovsky",
        "label": "Burza na morzu",
        "old_pl_titles": ("Burza na morzu",),
        "new_pl_title": "Burza na morzu (1873) (lub Sztorm na morzu (1873))",
        "original_title": "Буря на море",
        "english_title": "Storm at Sea (1873) (or Storm on the Sea (1873))",
        "locale_titles": {
            "en": "Storm at Sea (1873) (or Storm on the Sea (1873))",
            "de": "Sturm auf dem Meer (1873) (oder Seesturm (1873))",
            "fr": "Tempête en mer (1873) (ou La tempête en mer (1873))",
            "es": "Tormenta en el mar (1873) (o Tempestad en el mar (1873))",
            "nl": "Storm op zee (1873) (of De storm op zee (1873))",
            "it": "Tempesta sul mare (1873) (o Mare in tempesta (1873))",
        },
        "alt_en_title": "Storm at Sea (1873)",
    },
    {
        "product_id": 15549063496028,
        "artist": "Ivan Aivazovsky",
        "label": "Burza nad MC",
        "old_pl_titles": ("Burza nad Morzem Czarnym",),
        "new_pl_title": (
            "Burza nad Morzem Czarnym (1893) (lub Sztorm na Morzu Czarnym (1893))"
        ),
        "original_title": "Буря на Чёрном море",
        "english_title": (
            "Storm over the Black Sea (1893) (or Storm on the Black Sea (1893))"
        ),
        "locale_titles": {
            "en": (
                "Storm over the Black Sea (1893) "
                "(or Storm on the Black Sea (1893))"
            ),
            "de": (
                "Sturm über dem Schwarzen Meer (1893) "
                "(oder Sturm auf dem Schwarzen Meer (1893))"
            ),
            "fr": (
                "Tempête sur la mer Noire (1893) "
                "(ou Orage sur la mer Noire (1893))"
            ),
            "es": (
                "Tormenta en el mar Negro (1893) "
                "(o Tempestad sobre el mar Negro (1893))"
            ),
            "nl": (
                "Storm over de Zwarte Zee (1893) "
                "(of Storm op de Zwarte Zee (1893))"
            ),
            "it": (
                "Tempesta sul Mar Nero (1893) (o Burrasca sul Mar Nero (1893))"
            ),
        },
        "alt_en_title": "Storm over the Black Sea (1893)",
    },
    {
        "product_id": 15549070279004,
        "artist": "Ivan Aivazovsky",
        "label": "Fala",
        "old_pl_titles": ("Fala",),
        "new_pl_title": "Fala (1889) (lub Między falami (1889))",
        "original_title": "Волна",
        "english_title": "The Wave (1889) (or Among the Waves (1889))",
        "locale_titles": {
            "en": "The Wave (1889) (or Among the Waves (1889))",
            "de": "Die Welle (1889) (oder Inmitten der Wellen (1889))",
            "fr": "La vague (1889) (ou Entre les vagues (1889))",
            "es": "La ola (1889) (o Entre las olas (1889))",
            "nl": "De golf (1889) (of Tussen de golven (1889))",
            "it": "L'onda (1889) (o Tra le onde (1889))",
        },
        "alt_en_title": "The Wave (1889)",
    },
    {
        "product_id": 15549061890396,
        "artist": "Ivan Aivazovsky",
        "label": "Nadchodząca burza",
        "old_pl_titles": ("Nadchodząca burza",),
        "new_pl_title": "Nadchodząca burza (lub Burza/Nadciągający sztorm)",
        "original_title": "Буря",
        "english_title": "Gathering Storm (or Approaching Storm)",
        "locale_titles": {
            "en": "Gathering Storm (or Approaching Storm)",
            "de": "Aufziehender Sturm (oder Herannahender Sturm)",
            "fr": "Tempête imminente (ou Tempête approchante)",
            "es": "Tormenta inminente (o Tormenta que se aproxima)",
            "nl": "Naderende storm (of Opkomende storm)",
            "it": "Tempesta in arrivo (o Tempesta imminente)",
        },
        "alt_en_title": "Gathering Storm",
    },
    {
        "product_id": 15549069066588,
        "artist": "Ivan Aivazovsky",
        "label": "Ocalały",
        "old_pl_titles": ("Ocalały",),
        "new_pl_title": "Ocalały (1880) (lub Rozbitek (1880))",
        "original_title": "Оставшийся в живых",
        "english_title": (
            "The Survivor (1880) (or The Survivor of the Shipwreck (1880))"
        ),
        "locale_titles": {
            "en": "The Survivor (1880) (or The Survivor of the Shipwreck (1880))",
            "de": "Der Überlebende (1880) (oder Der Schiffbrüchige (1880))",
            "fr": "Le survivant (1880) (ou Le rescapé (1880))",
            "es": "El superviviente (1880) (o El náufrago (1880))",
            "nl": "De overlevende (1880) (of De schipbreukeling (1880))",
            "it": "Il sopravvissuto (1880) (o Il naufrago (1880))",
        },
        "alt_en_title": "The Survivor (1880)",
    },
    {
        "product_id": 15549060415836,
        "artist": "Ivan Aivazovsky",
        "label": "Opuszczenie statku",
        "old_pl_titles": ("Opuszczenie statku",),
        "new_pl_title": (
            "Opuszczenie statku (1882) "
            "(lub Ratowanie się z tonącego okrętu (1882))"
        ),
        "original_title": "Покидание корабля",
        "english_title": "Abandoning Ship (1882) (or Leaving the Ship (1882))",
        "locale_titles": {
            "en": "Abandoning Ship (1882) (or Leaving the Ship (1882))",
            "de": (
                "Das Verlassen des Schiffes (1882) "
                "(oder Schiff verlassen (1882))"
            ),
            "fr": (
                "Abandon du navire (1882) "
                "(ou L'abandon du navire (1882))"
            ),
            "es": "Abandono del barco (1882) (o Abandonando el barco (1882))",
            "nl": "Het verlaten van het schip (1882) (of Schip verlaten (1882))",
            "it": (
                "Abbandono della nave (1882) "
                "(o L'abbandono della nave (1882))"
            ),
        },
        "alt_en_title": "Abandoning Ship (1882)",
    },
    {
        "product_id": 15549061103964,
        "artist": "Ivan Aivazovsky",
        "label": "Spokojne morze",
        "old_pl_titles": ("Spokojne morze wczesnym wieczorem",),
        "new_pl_title": (
            "Spokojne morze we wczesny wieczór "
            "(lub Spokojne morze wczesnym wieczorem)"
        ),
        "original_title": "Calm Early Evening Sea",
        "english_title": (
            "Calm Early Evening Sea (or Calm Sea in the Early Evening)"
        ),
        "locale_titles": {
            "en": "Calm Early Evening Sea (or Calm Sea in the Early Evening)",
            "de": (
                "Ruhige See am frühen Abend "
                "(oder Ruhiges Meer am frühen Abend)"
            ),
            "fr": (
                "Mer calme en début de soirée "
                "(ou Mer calme au début de la soirée)"
            ),
            "es": (
                "Mar tranquilo a primera hora de la tarde "
                "(o Mar calmo al atardecer)"
            ),
            "nl": (
                "Kalme zee in de vroege avond "
                "(of Rustige zee in de vroege avond)"
            ),
            "it": (
                "Mare calmo nella prima serata "
                "(o Mare calmo a prima sera)"
            ),
        },
        "alt_en_title": "Calm Early Evening Sea",
    },
    {
        "product_id": 15549062185308,
        "artist": "Ivan Aivazovsky",
        "label": "Statek wzburzone morze",
        "old_pl_titles": ("Statek na wzburzonym morzu",),
        "new_pl_title": (
            "Okręt na wzburzonym morzu "
            "(lub Statek podczas sztormu (1887))"
        ),
        "original_title": "Корабль в бурном море",
        "english_title": (
            "Ship in a Stormy Sea (1887) (or Ship on Stormy Seas (1887))"
        ),
        "locale_titles": {
            "en": "Ship in a Stormy Sea (1887) (or Ship on Stormy Seas (1887))",
            "de": (
                "Schiff in stürmischer See (1887) "
                "(oder Schiff im Sturm (1887))"
            ),
            "fr": (
                "Navire dans la mer en tempête (1887) "
                "(ou Navire dans la tempête (1887))"
            ),
            "es": (
                "Barco en un mar tormentoso (1887) "
                "(o Buque en la tempestad (1887))"
            ),
            "nl": (
                "Schip op een stormachtige zee (1887) "
                "(of Schip in de storm (1887))"
            ),
            "it": (
                "Nave in un mare tempestoso (1887) "
                "(o Nave nella tempesta (1887))"
            ),
        },
        "alt_en_title": "Ship in a Stormy Sea (1887)",
    },
    {
        "product_id": 15549062414684,
        "artist": "Ludolf Bakhuizen",
        "label": "Statki w sztormie (Bakhuizen)",
        "old_pl_titles": ("Statki w sztormie",),
        "new_pl_title": (
            "Statki podczas sztormu u skalistego wybrzeża "
            "(lub Okręty w czasie burzy na morzu przy brzegu)"
        ),
        "original_title": "Schepen in een storm voor oostelijk rotsachtige kust",
        "english_title": (
            "Ships in a Tempest off a Rocky Coast "
            "(or Ships in Distress off a Rocky Coast)"
        ),
        "locale_titles": {
            "en": (
                "Ships in a Tempest off a Rocky Coast "
                "(or Ships in Distress off a Rocky Coast)"
            ),
            "de": (
                "Schiffe im Sturm vor einer felsigen Küste "
                "(oder Schiffe in Seenot vor einer Steilküste)"
            ),
            "fr": (
                "Navires dans la tempête au large d'une côte rocheuse "
                "(ou Navires en détresse près d'une côte rocheuse)"
            ),
            "es": (
                "Barcos en una tempestad frente a una costa rocosa "
                "(o Buques en peligro cerca de una costa rocosa)"
            ),
            "nl": (
                "Schepen in een storm voor een rotsachtige kust "
                "(of Schepen in nood nabij een rotsachtige kust)"
            ),
            "it": (
                "Navi nella tempesta al largo di una costa rocciosa "
                "(o Navi in difficoltà vicino a una costa rocciosa)"
            ),
        },
        "alt_en_title": "Ships in a Tempest off a Rocky Coast",
    },
    {
        "product_id": 15549064053084,
        "artist": "Ivan Aivazovsky",
        "label": "Wzburzone morze zachód",
        "old_pl_titles": ("Wzburzone morze o zachodzie słońca",),
        "new_pl_title": (
            "Wzburzone morze o zachodzie słońca (1896) "
            "(lub Morze. Zachód słońca (1896))"
        ),
        "original_title": "Море. Закат",
        "english_title": "Stormy Sea at Sunset (1896) (or Sea. Sunset (1896))",
        "locale_titles": {
            "en": "Stormy Sea at Sunset (1896) (or Sea. Sunset (1896))",
            "de": (
                "Stürmische See im Abendrot (1896) "
                "(oder Meer. Sonnenuntergang (1896))"
            ),
            "fr": (
                "Mer agitée au coucher du soleil (1896) "
                "(ou Mer. Coucher de soleil (1896))"
            ),
            "es": "Mar proceloso al atardecer (1896) (o Mar. Ocaso (1896))",
            "nl": (
                "Stormachtige zee bij zonsondergang (1896) "
                "(of Zee. Zonsondergang (1896))"
            ),
            "it": "Mare in tempesta al tramonto (1896) (o Mare. Tramonto (1896))",
        },
        "alt_en_title": "Stormy Sea at Sunset (1896)",
    },
    {
        "product_id": 15549066641756,
        "artist": "Ivan Aivazovsky",
        "label": "Zatoka Neapolitańska",
        "old_pl_titles": ("Zatoka Neapolitańska z widokiem na Capri",),
        "new_pl_title": (
            "Zatoka Neapolitańska z widokiem na Capri (1891) "
            "(lub Zatoka Neapolitańska i Capri (1891))"
        ),
        "original_title": "The Bay of Naples with Capri",
        "english_title": (
            "The Bay of Naples with Capri (1891) "
            "(or The Gulf of Naples with Capri (1891))"
        ),
        "locale_titles": {
            "en": (
                "The Bay of Naples with Capri (1891) "
                "(or The Gulf of Naples with Capri (1891))"
            ),
            "de": (
                "Die Bucht von Neapel mit Capri (1891) "
                "(oder Der Golf von Neapel mit Capri (1891))"
            ),
            "fr": (
                "La baie de Naples avec Capri (1891) "
                "(ou Le golfe de Naples avec Capri (1891))"
            ),
            "es": (
                "La bahía de Nápoles con Capri (1891) "
                "(o El golfo de Nápoles con Capri (1891))"
            ),
            "nl": (
                "De Baai van Napels met Capri (1891) "
                "(of De Golf van Napels met Capri (1891))"
            ),
            "it": (
                "Il golfo di Napoli con Capri (1891) "
                "(o La baia di Napoli con Capri (1891))"
            ),
        },
        "alt_en_title": "The Bay of Naples with Capri (1891)",
    },
    {
        "product_id": 15549071982940,
        "artist": "Ludolf Bakhuizen",
        "label": "Fregata holenderska",
        "old_pl_titles": ("Pejzaż morski (holenderska fregata holująca szalupę)",),
        "new_pl_title": (
            "Holenderska fregata i inne statki u wybrzeża "
            "(lub Krajobraz morski z fregatą)"
        ),
        "original_title": "Hollandse driemaster en andere schepen voor de kust",
        "english_title": (
            "Dutch Frigate and Other Ships Off the Coast "
            "(or Seascape with a Dutch Frigate Towing a Skiff)"
        ),
        "locale_titles": {
            "en": (
                "Dutch Frigate and Other Ships Off the Coast "
                "(or Seascape with a Dutch Frigate Towing a Skiff)"
            ),
            "de": (
                "Marine (Niederländische Fregatte mit einem Nachen im Schlepptau) "
                "(oder Schiffe vor der Küste)"
            ),
            "fr": (
                "Frégate hollandaise et autres navires au large de la côte "
                "(ou Marine avec frégate hollandaise)"
            ),
            "es": (
                "Fragata holandesa y otros barcos frente a la costa "
                "(o Marina con fragata holandesa)"
            ),
            "nl": (
                "Hollandse driemaster en andere schepen voor de kust "
                "(of Nederlandse fregat en andere schepen voor de kust)"
            ),
            "it": (
                "Fregata olandese e altre navi al largo della costa "
                "(o Marina con fregata olandese)"
            ),
        },
        "alt_en_title": "Dutch Frigate and Other Ships Off the Coast",
    },
    {
        "product_id": 15549073129820,
        "artist": "Ludolf Bakhuizen",
        "label": "Łodzie rybackie",
        "old_pl_titles": ("Pejzaż morski z łodziami rybackimi",),
        "new_pl_title": (
            "Krajobraz morski z łodziami rybackimi (lub Łodzie rybackie na morzu)"
        ),
        "original_title": "Marine en barques de pêche",
        "english_title": "Seascape and Fishing Boats",
        "locale_titles": {
            "en": "Seascape and Fishing Boats",
            "de": "Seestück mit Fischerbooten (oder Marine mit Fischerbooten)",
            "fr": "Marine et barques de pêche (ou Marine)",
            "es": "Marina y barcas de pesca (o Marina con botes de pesca)",
            "nl": "Marine en barques de pêche (of Zeegezicht met vissersboten)",
            "it": "Marina e barche da pesca (o Paesaggio marino con barche da pesca)",
        },
        "alt_en_title": "Seascape and Fishing Boats",
    },
    {
        "product_id": 15549074473308,
        "artist": "Ludolf Bakhuizen",
        "label": "Port Amsterdam IJ",
        "old_pl_titles": ("Port w Amsterdamie widziany z IJ",),
        "new_pl_title": (
            "Widok na Amsterdam ze statkiem \"De Spiegel\" "
            "i innymi jednostkami na rzece IJ "
            "(lub Widok na Amsterdam ze statkiem \"De Spiegel\" na IJ)"
        ),
        "original_title": "Gezicht na Amsterdam met de Spiegel en andere schepen op het IJ",
        "english_title": (
            "View of Amsterdam with the Ship 'De Spiegel' and Other Vessels on the IJ "
            "(or View of Amsterdam with Ships on the IJ)"
        ),
        "locale_titles": {
            "en": (
                "View of Amsterdam with the Ship 'De Spiegel' "
                "and Other Vessels on the IJ "
                "(or View of Amsterdam with Ships on the IJ)"
            ),
            "de": (
                "Ansicht von Amsterdam mit dem Schiff 'De Spiegel' "
                "und anderen Schiffen auf dem IJ "
                "(oder Blick auf Amsterdam mit Schiffen auf dem IJ)"
            ),
            "fr": (
                "Vue d'Amsterdam avec le navire 'De Spiegel' "
                "et d'autres embarcations sur l'IJ "
                "(ou Vue d'Amsterdam avec des navires sur l'IJ)"
            ),
            "es": (
                "Vista de Ámsterdam con el barco 'De Spiegel' "
                "y otras embarcaciones en el IJ "
                "(o Vista de Ámsterdam con barcos en el IJ)"
            ),
            "nl": (
                "Gezicht na Amsterdam met de Spiegel en andere schepen op het IJ "
                "(of Gezicht op Amsterdam met schepen op het IJ)"
            ),
            "it": (
                "Veduta di Amsterdam con la nave 'De Spiegel' "
                "e altre imbarcazioni sull'IJ "
                "(o Veduta di Amsterdam con navi sull'IJ)"
            ),
        },
        "alt_en_title": "View of Amsterdam with the Ship 'De Spiegel' and Other Vessels on the IJ",
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 13).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
