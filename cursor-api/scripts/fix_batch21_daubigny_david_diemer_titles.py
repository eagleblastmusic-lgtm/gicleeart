"""Poprawka tytulow: Daubigny (2), David (3), Diemer Fregata (6 produktow)."""
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
        "product_id": 15611274821980,
        "artist": "Charles François Daubigny",
        "label": "Staw w Gylieu",
        "titles": {
            "orig": "L'Étang de Gylieu (of Les Étangs de Gylieu)",
            "pl": "Staw w Gylieu (lub Stawy w Gylieu)",
            "en": "The Pond at Gylieu (or The Ponds of Gylieu)",
            "de": "Der Teich von Gylieu (oder Die Teiche von Gylieu)",
            "fr": "L'Étang de Gylieu (ou Les Étangs de Gylieu)",
            "es": "El estanque de Gylieu (o Los estanques de Gylieu)",
            "nl": "De vijver van Gylieu (of De vijvers van Gylieu)",
            "it": "Lo stagno di Gylieu (o Gli stagni di Gylieu)",
        },
    },
    {
        "product_id": 15611274756444,
        "artist": "Charles François Daubigny",
        "label": "Wiosna",
        "titles": {
            "orig": "Le printemps",
            "pl": "Wiosna (lub Wiosenny krajobraz)",
            "en": "Springtime (or Spring Landscape)",
            "de": "Der Frühling (oder Frühlingslandschaft)",
            "fr": "Le printemps",
            "es": "La primavera (o Paisaje de primavera)",
            "nl": "De lente (of Lente-landschap)",
            "it": "La primavera (o Paesaggio primaverile)",
        },
    },
    {
        "product_id": 15611525103964,
        "artist": "Jacques-Louis David",
        "label": "Amor i Psyche",
        "titles": {
            "orig": "L'Amour et Psyché",
            "pl": "Amor i Psyche (lub Kupidyn i Psyche)",
            "en": "Cupid and Psyche (or Love and Psyche)",
            "de": "Amor und Psyche",
            "fr": "L'Amour et Psyché",
            "es": "Amor y Psique",
            "nl": "Amor en Psyche",
            "it": "Amore e Psiche",
        },
    },
    {
        "product_id": 15611525398876,
        "artist": "Jacques-Louis David",
        "label": "Napoleon Bernarda",
        "titles": {
            "orig": (
                "Bonaparte franchissant le Grand-Saint-Bernard "
                "(of Napoléon traversant les Alpes)"
            ),
            "pl": (
                "Napoleon przekraczający Przełęcz Świętego Bernarda "
                "(lub Napoleon przekraczający Alpy/Bonaparte na Przełęczy "
                "Świętego Bernarda)"
            ),
            "en": "Napoleon Crossing the Alps (or Bonaparte Crossing the Alps)",
            "de": (
                "Napoleon am Großen St. Bernhard "
                "(oder Bonaparte beim Übergang über den Großen St. Bernhard)"
            ),
            "fr": (
                "Bonaparte franchissant le Grand-Saint-Bernard "
                "(ou Napoléon traversant les Alpes)"
            ),
            "es": (
                "Napoleón cruzando los Alpes "
                "(o Bonaparte cruzando los Alpes)"
            ),
            "nl": (
                "Napoleon trekt over de Alpen "
                "(of Bonaparte trekt over de Grote Sint-Bernhardpas)"
            ),
            "it": (
                "Napoleone valica le Alpi "
                "(o Bonaparte valica il Gran San Bernardo)"
            ),
        },
    },
    {
        "product_id": 15611525890396,
        "artist": "Jacques-Louis David",
        "label": "Napoleon Tuileries",
        "titles": {
            "orig": (
                "L'Empereur Napoléon dans son cabinet de travail aux Tuileries "
                "(of Napoléon dans son cabinet de travail)"
            ),
            "pl": (
                "Napoleon w swoim gabinecie "
                "(lub Napoleon w gabinecie osobistym w Tuileries/"
                "Cesarz Napoleon w swoim gabinecie w Tuileries)"
            ),
            "en": (
                "The Emperor Napoleon in His Study at the Tuileries "
                "(or Napoleon in His Study)"
            ),
            "de": (
                "Kaiser Napoleon in seinem Arbeitszimmer im Tuilerien-Palast "
                "(oder Napoleon in seinem Arbeitszimmer)"
            ),
            "fr": (
                "L'Empereur Napoléon dans son cabinet de travail aux Tuileries "
                "(ou Napoléon dans son cabinet de travail)"
            ),
            "es": (
                "El emperador Napoleón en su estudio en las Tullerías "
                "(o Napoleón en su gabinete de trabajo)"
            ),
            "nl": (
                "Keizer Napoleon in zijn werkkamer in de Tuilerieën "
                "(of Napoleon in zijn studeerkamer)"
            ),
            "it": (
                "L'imperatore Napoleone nel suo studio alle Tuileries "
                "(o Napoleone nel suo studio)"
            ),
        },
    },
    {
        "product_id": 15611419558236,
        "artist": "Michael Zeno Diemer",
        "label": "Fregata Rio",
        "titles": {
            "orig": (
                "Eine Fregatte vor der Küste bei Rio de Janeiro "
                "(of Fregatte vor Rio de Janeiro)"
            ),
            "pl": (
                "Fregata u wybrzeży Rio de Janeiro "
                "(lub Fregata przed Rio de Janeiro)"
            ),
            "en": (
                "A Frigate off the Coast Near Rio de Janeiro "
                "(or Frigate off Rio de Janeiro)"
            ),
            "de": (
                "Eine Fregatte vor der Küste bei Rio de Janeiro "
                "(oder Fregatte vor Rio de Janeiro)"
            ),
            "fr": "Une frégate au large de Rio de Janeiro",
            "es": "Una fragata frente a la costa de Río de Janeiro",
            "nl": "Een fregat voor de kust van Rio de Janeiro",
            "it": "Una fregata al largo della costa di Rio de Janeiro",
        },
    },
)


def main() -> int:
    for cfg in PRODUCTS:
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
