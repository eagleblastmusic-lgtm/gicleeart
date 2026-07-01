"""Poprawka tytulow: batch 19 — Thomas Cole (11), John Constable (1), Corot (6)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz.description_update import (
    apply_product_title_fields,
    load_product_title_fields,
    set_title_update_mark,
)


class ProductTitles(TypedDict):
    product_id: int
    artist: str
    label: str
    titles: dict[str, str]


PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15611250966876,
        "artist": "Thomas Cole",
        "label": "Gorski brod",
        "titles": {
            "orig": "The Mountain Ford",
            "pl": "Górski bród",
            "en": "The Mountain Ford",
            "de": "Die Bergfurth",
            "fr": "Le gué de la montagne",
            "es": "El vado de la montaña",
            "nl": "De doorwading in de bergen",
            "it": "Il guado di montagna",
        },
    },
    {
        "product_id": 15611243069788,
        "artist": "Thomas Cole",
        "label": "L'Allegro",
        "titles": {
            "orig": "L'Allegro (of Italian Sunset)",
            "pl": "L'Allegro (lub Włoski zachód słońca)",
            "en": "L'Allegro (or Italian Sunset)",
            "de": "L'Allegro (oder Italienischer Sonnenuntergang)",
            "fr": "L'Allegro (ou Coucher de soleil italien)",
            "es": "L'Allegro (o Atardecer italiano)",
            "nl": "L'Allegro (of Italiaanse zonsondergang)",
            "it": "L'Allegro (o Tramonto italiano)",
        },
    },
    {
        "product_id": 15611242676572,
        "artist": "Thomas Cole",
        "label": "Ogrody Van Rensselaer",
        "titles": {
            "orig": "The Gardens of the Van Rensselaer Manor House",
            "pl": (
                "Ogrody posiadłości Van Rensselaera "
                "(lub Ogrody posiadłości Van Rensselaer Manor House)"
            ),
            "en": "The Gardens of the Van Rensselaer Manor House",
            "de": "Die Gärten des Van Rensselaer Herrenhauses",
            "fr": "Les jardins manoirs de Van Rensselaer",
            "es": "Los jardines de la casa señorial de Van Rensselaer",
            "nl": "De tuinen van het landhuis Van Rensselaer",
            "it": "I giardini della villa Van Rensselaer",
        },
    },
    {
        "product_id": 15611248771420,
        "artist": "Thomas Cole",
        "label": "Ogrod Eden",
        "titles": {
            "orig": "The Garden of Eden",
            "pl": "Ogród Edenu (lub Rajski ogród)",
            "en": "The Garden of Eden",
            "de": "Der Garten Eden",
            "fr": "Le Jardin d'Éden",
            "es": "El Jardín de Edén",
            "nl": "De Hof van Eden",
            "it": "Il Giardino dell'Eden",
        },
    },
    {
        "product_id": 15611251753308,
        "artist": "Thomas Cole",
        "label": "Piknik",
        "titles": {
            "orig": "The Picnic",
            "pl": "Piknik",
            "en": "The Picnic",
            "de": "Das Picknick",
            "fr": "Le Pique-nique",
            "es": "El picnic",
            "nl": "De picknick",
            "it": "Il picnic",
        },
    },
    {
        "product_id": 15611251982684,
        "artist": "Thomas Cole",
        "label": "Podroz zycia Starosc",
        "titles": {
            "orig": "The Voyage of Life: Old Age",
            "pl": (
                "Podróż życia: Starość "
                "(lub Dzieje ludzkiego życia: Starość)"
            ),
            "en": "The Voyage of Life: Old Age",
            "de": "Die Lebensreise: Das Greisenalter",
            "fr": "Le Voyage de la vie: La vieillesse",
            "es": "El viaje de la vida: La vejez",
            "nl": "De reis van het leven: De ouderdom",
            "it": "Il viaggio della vita: La vecchiaia",
        },
    },
    {
        "product_id": 15611251294556,
        "artist": "Thomas Cole",
        "label": "Przeszlosc",
        "titles": {
            "orig": "The Past",
            "pl": "Przeszłość",
            "en": "The Past",
            "de": "Die Vergangenheit",
            "fr": "Le Passé",
            "es": "El pasado",
            "nl": "Het verleden",
            "it": "Il passato",
        },
    },
    {
        "product_id": 15611243430236,
        "artist": "Thomas Cole",
        "label": "Scena Mohikanina",
        "titles": {
            "orig": (
                'Scene from "The Last of the Mohicans," '
                "Cora Kneeling at the Feet of Tamenund"
            ),
            "pl": (
                'Scena z "Ostatniego Mohikanina" – Cora klęcząca u stóp Tamenunda '
                '(lub Scena z "Ostatniego Mohikanina")'
            ),
            "en": (
                'Scene from "The Last of the Mohicans," '
                "Cora Kneeling at the Feet of Tamenund"
            ),
            "de": (
                'Szene aus "Der letzte Mohikaner", '
                "Cora kniend zu Füßen von Tamenund"
            ),
            "fr": (
                'Scène du "Dernier des Mohicans", '
                "Cora agenouillée aux pieds de Tamenund"
            ),
            "es": (
                'Escena de "El último mohicano", '
                "Cora arrodillada a los pies de Tamenund"
            ),
            "nl": (
                'Scène uit "De laatste der Mohikanen", '
                "Cora knielend aan de voeten van Tamenund"
            ),
            "it": (
                'Scena da "L\'ultimo dei Mohicani", '
                "Cora in ginocchio ai piedi di Tamenund"
            ),
        },
    },
    {
        "product_id": 15611244314972,
        "artist": "Thomas Cole",
        "label": "Sen architekta",
        "titles": {
            "orig": "The Architect's Dream",
            "pl": "Marzenie architekta (lub Sen architekta)",
            "en": "The Architect's Dream",
            "de": "Der Traum des Architekten",
            "fr": "Le Rêve de l'architecte",
            "es": "El sueño del arquitecto",
            "nl": "De droom van de architect",
            "it": "Il sogno dell'architetto",
        },
    },
    {
        "product_id": 15611252539740,
        "artist": "Thomas Cole",
        "label": "Frenchman's Bay",
        "titles": {
            "orig": (
                "View Across Frenchman's Bay from Mount Desert Island After a Squall"
            ),
            "pl": (
                "Widok na zatokę Frenchman's Bay z wyspy Mount Desert po szkwale "
                "(lub Widok przez Frenchman's Bay z Mount Desert Island po szkwale)"
            ),
            "en": (
                "View Across Frenchman's Bay from Mount Desert Island After a Squall"
            ),
            "de": (
                "Blick über die Frenchman's Bay von Mount Desert Island nach einer Böe"
            ),
            "fr": (
                "Vue à travers Frenchman's Bay depuis Mount Desert Island après un grain"
            ),
            "es": (
                "Vista a través de Frenchman's Bay desde Mount Desert Island "
                "después de un turbión"
            ),
            "nl": (
                "Gezicht over Frenchman's Bay vanaf Mount Desert Island na een bui"
            ),
            "it": (
                "Veduta attraverso Frenchman's Bay da Mount Desert Island "
                "dopo una burrasca"
            ),
        },
    },
    {
        "product_id": 15611252408668,
        "artist": "Thomas Cole",
        "label": "Oxbow",
        "titles": {
            "orig": (
                "View from Mount Holyoke, Northampton, Massachusetts, "
                "after a Thunderstorm — The Oxbow"
            ),
            "pl": (
                "Widok z góry Holyoke w Northampton w stanie Massachusetts po burzy "
                "– The Oxbow (lub Przełom rzeki Connecticut pod Northampton/"
                "Zakole rzeki (The Oxbow))"
            ),
            "en": (
                "View from Mount Holyoke, Northampton, Massachusetts, "
                "after a Thunderstorm — The Oxbow"
            ),
            "de": (
                "Ansicht vom Mount Holyoke, Northampton, Massachusetts, "
                "nach einem Gewitter – The Oxbow"
            ),
            "fr": (
                "Vue du mont Holyoke, Northampton, Massachusetts, après un orage "
                "— The Oxbow"
            ),
            "es": (
                "Vista desde el monte Holyoke, Northampton, Massachusetts, "
                "después de una tormenta — The Oxbow"
            ),
            "nl": (
                "Gezicht op Mount Holyoke, Northampton, Massachusetts, "
                "na een onweersbui — The Oxbow"
            ),
            "it": (
                "Veduta dal monte Holyoke, Northampton, Massachusetts, "
                "dopo un temporale — The Oxbow"
            ),
        },
    },
    {
        "product_id": 15611179204956,
        "artist": "John Constable",
        "label": "Wivenhoe Park",
        "titles": {
            "orig": "Wivenhoe Park, Essex",
            "pl": "Park Wivenhoe (lub Wivenhoe Park w Essex)",
            "en": "Wivenhoe Park, Essex (or Wivenhoe Park)",
            "de": "Wivenhoe Park, Essex (oder Wivenhoe Park)",
            "fr": "Le Parc de Wivenhoe (ou Wivenhoe Park)",
            "es": "Wivenhoe Park, Essex (o Parque Wivenhoe)",
            "nl": "Wivenhoe Park, Essex (of Wivenhoe Park)",
            "it": "Il parco di Wivenhoe (o Wivenhoe Park)",
        },
    },
    {
        "product_id": 15611151384924,
        "artist": "Jean-Baptiste-Camille Corot",
        "label": "Agostina",
        "titles": {
            "orig": "Agostina",
            "pl": "Agostina",
            "en": "Agostina",
            "de": "Agostina",
            "fr": "Agostina",
            "es": "Agostina",
            "nl": "Agostina",
            "it": "Agostina",
        },
    },
    {
        "product_id": 15611151778140,
        "artist": "Jean-Baptiste-Camille Corot",
        "label": "Czytajaca dziewczyna",
        "titles": {
            "orig": "La Petite Liseuse (of Jeune Fille lisant)",
            "pl": "Czytająca dziewczyna (lub Mała czytelniczka)",
            "en": "Girl Reading (or The Little Reader)",
            "de": "Lesendes Mädchen (oder Die kleine Leserin)",
            "fr": "La Petite Liseuse (ou Jeune Fille lisant)",
            "es": "Joven leyendo (o La pequeña lectora)",
            "nl": "Lezend meisje (of De kleine lezeres)",
            "it": "Giovane donna che legge (o La piccola lettrice)",
        },
    },
    {
        "product_id": 15611154891100,
        "artist": "Jean-Baptiste-Camille Corot",
        "label": "Dama w blekicie",
        "titles": {
            "orig": "La Dame en bleu",
            "pl": (
                "Kobieta w błękicie "
                "(lub Dama w błękicie/Dama w niebieskiej sukni)"
            ),
            "en": "Lady in Blue (or Woman in Blue)",
            "de": "Die Dame in Blau (oder Frau in Blau)",
            "fr": "La Dame en bleu",
            "es": "La dama de azul (o La mujer de azul)",
            "nl": "De dame in het blauw (of De vrouw in het blauw)",
            "it": "La dama in blu (o La donna in blu)",
        },
    },
    {
        "product_id": 15611152105820,
        "artist": "Jean-Baptiste-Camille Corot",
        "label": "La Cervara",
        "titles": {
            "orig": (
                "La Cervara, campagne de Rome "
                "(of Campagne de Rome, dit autrefois La Cervara)"
            ),
            "pl": (
                "La Cervara, kampania rzymska "
                "(lub Krajobraz włoski (La Cervara)/La Cervara, okolice Rzymu)"
            ),
            "en": "La Cervara, the Roman Campagna",
            "de": "La Cervara, die römische Campagna",
            "fr": (
                "La Cervara, campagne de Rome "
                "(ou La Cervara, la campagne romaine)"
            ),
            "es": "La Cervara, la campiña romana",
            "nl": "La Cervara, de Romeinse Campagna",
            "it": "La Cervara, campagna romana",
        },
    },
    {
        "product_id": 15611156529500,
        "artist": "Jean-Baptiste-Camille Corot",
        "label": "Algierka",
        "titles": {
            "orig": "Algérienne (of Jeune Algérienne couchée sur le gazon)",
            "pl": "Algierka (lub Młoda Algierka leżąca na trawie)",
            "en": (
                "Algerian Woman "
                "(or Young Algerian Woman Lying on the Grass)"
            ),
            "de": "Algerierin (oder Junge Algerierin im Gras liegend)",
            "fr": "Algérienne (ou Jeune Algérienne couchée sur le gazon)",
            "es": "Argelina (o Joven argelina tumbada en la hierba)",
            "nl": (
                "Algerijnse "
                "(of Jonge Algerijnse vrouw liggend in het gras)"
            ),
            "it": "Algerina (o Giovane algerina distesa sull'erba)",
        },
    },
    {
        "product_id": 15611149025628,
        "artist": "Jean-Baptiste-Camille Corot",
        "label": "Zamyslona dziewczyna",
        "titles": {
            "orig": "Pensive (of Jeune Fille pensive/Fillette pensive)",
            "pl": (
                "Zamyślona dziewczyna "
                "(lub Zadumana dziewczyna/Zamysłona/Zaduma)"
            ),
            "en": "A Pensive Girl (or Pensive Young Woman)",
            "de": "Nachdenkliches Mädchen (oder Ein nachdenkliches Mädchen)",
            "fr": "Pensive (ou Jeune Fille pensive/Fillette pensive)",
            "es": "Joven pensativa (o Niña pensativa)",
            "nl": "Peinzend meisje (of Een peinzend meisje)",
            "it": "Ragazza pensierosa (o Giovane donna pensierosa)",
        },
    },
)


def _apply(cfg: ProductTitles) -> None:
    pid = cfg["product_id"]
    print(f"\n=== {cfg['label']} (id={pid}) ===")
    res = apply_product_title_fields(
        product_id=pid,
        artist=cfg["artist"],
        titles=cfg["titles"],
        logger=print,
    )
    set_title_update_mark(pid, marked=True)
    print(f"  PL: {load_product_title_fields(pid).get('pl', '')}")
    print(f"  locales: {res.get('saved_locales', [])}")


def main() -> int:
    for cfg in PRODUCTS:
        _apply(cfg)
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 19).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
