"""Poprawka tytulow: batch 15 — Lorenzo Butti (1), Antonio Canal (12)."""
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
        "product_id": 15611419165020,
        "artist": "Lorenzo Butti",
        "label": "Pejzaż morski scirocco",
        "titles": {
            "orig": "Seestück mit Scirocco",
            "pl": (
                "Pejzaż morski z wiatrem scirocco "
                "(lub Krajobraz morski ze scirocco)"
            ),
            "en": "Seascape with Scirocco (or Sea Piece with Scirocco)",
            "de": "Seestück mit Scirocco",
            "fr": "Marine au sirocco (ou Paysage de mer avec sirocco)",
            "es": "Marina con siroco (o Paisaje marino con siroco)",
            "nl": "Zeegezicht met scirocco (of Marine met scirocco)",
            "it": "Marina con scirocco (o Paesaggio marino con scirocco)",
        },
    },
    {
        "product_id": 15611055178076,
        "artist": "Antonio Canal",
        "label": "Canal Grande Balbi Rialto",
        "titles": {
            "orig": "Il Canal Grande da Palazzo Balbi a Rialto",
            "pl": (
                "Kanał Grande od Palazzo Balbi w stronę Rialto "
                "(lub Kanał Grande w pobliżu mostu Rialto w Wenecji/"
                "Widok na Grand Canal z Palazzo Balbi w kierunku mostu Rialto)"
            ),
            "en": (
                "The Grand Canal near the Rialto Bridge, Venice "
                "(or The Grand Canal from Palazzo Balbi to Rialto)"
            ),
            "de": (
                "Der Canal Grande vom Palazzo Balbi nach Rialto "
                "(oder Der Canal Grande nahe der Rialtobrücke, Venedig)"
            ),
            "fr": (
                "Le Grand Canal du Palazzo Balbi au Rialto "
                "(ou Le Grand Canal près du pont du Rialto, Venise)"
            ),
            "es": (
                "El Gran Canal desde el Palazzo Balbi hacia el Rialto "
                "(o El Gran Canal cerca del puente de Rialto, Venecia)"
            ),
            "nl": (
                "Het Canal Grande van Palazzo Balbi naar Rialto "
                "(of Het Canal Grande vlakbij de Rialtobrug, Venetië)"
            ),
            "it": (
                "Il Canal Grande da Palazzo Balbi a Rialto "
                "(o Il Canal Grande dalle prossimità del ponte di Rialto)"
            ),
        },
    },
    {
        "product_id": 15611053080924,
        "artist": "Antonio Canal",
        "label": "Canal Grande Flangini",
        "titles": {
            "orig": "Il Canal Grande da Palazzo Flangini a Campo San Marcuola",
            "pl": (
                "Kanał Grande od Palazzo Flangini do Campo San Marcuola "
                "(lub Widok na Grand Canal od Palazzo Flangini "
                "w stronę Campo San Marcuola)"
            ),
            "en": (
                "The Grand Canal in Venice from Palazzo Flangini "
                "to Campo San Marcuola "
                "(or Venice: The Grand Canal from the Palazzo Flangini "
                "to San Marcuola)"
            ),
            "de": (
                "Der Canal Grande vom Palazzo Flangini zum Campo San Marcuola "
                "(oder Das Canal Grande in Venedig vom Palazzo Flangini "
                "zum Campo San Marcuola)"
            ),
            "fr": (
                "Le Grand Canal à Venise du palazzo Flangini "
                "vers le campo San Marcuola "
                "(ou Le Grand Canal du Palazzo Flangini au Campo San Marcuola)"
            ),
            "es": (
                "El Gran Canal en Venecia desde el Palazzo Flangini "
                "hasta el Campo San Marcuola "
                "(o El Gran Canal desde el Palacio Flangini "
                "hasta la iglesia de San Marcuola)"
            ),
            "nl": (
                "Het Canal Grande in Venetië van Palazzo Flangini "
                "naar Campo San Marcuola "
                "(of Gezicht op het Canal Grande van Palazzo Flangini "
                "naar Campo San Marcuola)"
            ),
            "it": (
                "Il Canal Grande da Palazzo Flangini a Campo San Marcuola "
                "(o Veduta del Canal Grande da Palazzo Flangini "
                "a Campo San Marcuola)"
            ),
        },
    },
    {
        "product_id": 15610497630556,
        "artist": "Antonio Canal",
        "label": "Capriccio Rialto",
        "titles": {
            "orig": (
                "Capriccio con il ponte di Rialto "
                "e la chiesa di San Giorgio Maggiore"
            ),
            "pl": (
                "Kaprys z mostem Rialto i kościołem San Giorgio Maggiore "
                "(lub Widok fantastyczny z mostem Rialto "
                "i kościołem San Giorgio Maggiore)"
            ),
            "en": (
                "Capriccio: The Rialto Bridge and the Church "
                "of San Giorgio Maggiore "
                "(or Capriccio with the Rialto Bridge and the Church "
                "of San Giorgio Maggiore)"
            ),
            "de": (
                "Capriccio mit der Rialtobrücke und der Kirche "
                "San Giorgio Maggiore "
                "(oder Capriccio mit der Rialtobrücke und San Giorgio Maggiore)"
            ),
            "fr": (
                "Capriccio avec le pont du Rialto et l'église "
                "San Giorgio Maggiore "
                "(ou Caprice architectural avec le pont du Rialto "
                "et l'église San Giorgio Maggiore)"
            ),
            "es": (
                "Capricho con el puente de Rialto y la iglesia "
                "de San Giorgio Maggiore "
                "(o Capricho con el puente de Rialto y San Giorgio Maggiore)"
            ),
            "nl": (
                "Capriccio met de Rialtobrug en de kerk van San Giorgio Maggiore "
                "(of Capriccio met de Rialtobrug en San Giorgio Maggiore)"
            ),
            "it": (
                "Capriccio con il ponte di Rialto "
                "e la chiesa di San Giorgio Maggiore"
            ),
        },
    },
    {
        "product_id": 15610497663324,
        "artist": "Antonio Canal",
        "label": "Drezno Elba",
        "titles": {
            "orig": "Dresda dalla riva destra dell'Elba sotto il ponte di Augusto",
            "pl": (
                "Drezno z prawego brzegu Łaby poniżej mostu Augusta "
                "(lub Widok Drezna z prawego brzegu Łaby poniżej mostu Augusta/"
                "Widok Drezna z prawego brzegu Łaby pod mostem Augusta)"
            ),
            "en": (
                "Dresden from the Right Bank of the Elbe Below the Augustus Bridge "
                "(or Dresden seen from the Right Bank of the Elbe, "
                "beneath the Augustus Bridge)"
            ),
            "de": (
                "Dresden vom rechten Elbufer unterhalb der Augustusbrücke "
                "(oder Blick auf Dresden vom rechten Elbufer "
                "unterhalb der Augustusbrücke)"
            ),
            "fr": (
                "Dresde de la rive droite de l'Elbe en dessous du pont Auguste "
                "(ou Vue de Dresde de la rive droite de l'Elbe, "
                "en dessous du pont Auguste)"
            ),
            "es": (
                "Dresde desde la orilla derecha del Elba bajo el puente de Augusto "
                "(o Vista de Dresde desde la orilla derecha del Elba, "
                "bajo el puente de Augusto)"
            ),
            "nl": (
                "Dresden vanaf de rechteroever van de Elbe onder de Augustusbrücke "
                "(of Gezicht na Dresden vanaf de rechteroever van de Elbe "
                "onder de Augustusbrücke)"
            ),
            "it": (
                "Dresda dalla riva destra dell'Elba sotto il ponte di Augusto "
                "(o Veduta di Dresda dalla riva destra dell'Elba "
                "sotto il ponte di Augusto)"
            ),
        },
    },
    {
        "product_id": 15611061076316,
        "artist": "Antonio Canal",
        "label": "Molo Biblioteca",
        "titles": {
            "orig": "Il Molo con la Libreria e l'ingresso al Canal Grande",
            "pl": (
                "Molo z Biblioteką i wejściem do Kanału Grande "
                "(lub Molo w Wenecji z Biblioteką i kościołem Santa Maria della Salute/"
                "Nadbrzeże weneckie w pobliżu mennicy)"
            ),
            "en": (
                "The Molo with the Library and the Entrance to the Grand Canal "
                "(or The Pier near the Mint with the Column of San Teodoro)"
            ),
            "de": (
                "Das Molo mit der Bibliothek und der Einfahrt in den Canal Grande "
                "(oder Die Kaimauer nahe der Münze mit der Säule des San Teodoro)"
            ),
            "fr": (
                "Le Molo avec la bibliothèque et l'entrée du Grand Canal "
                "(ou Le quai près de la Monnaie avec la colonne de San Teodoro)"
            ),
            "es": (
                "El Molo con la Biblioteca y la entrada al Gran Canal "
                "(o El muelle cerca de la Ceca con la columna de San Teodoro)"
            ),
            "nl": (
                "De Molo met de Bibliotheek en de ingang van het Canal Grande "
                "(of De kade bij de Munt met de kolom van San Teodoro)"
            ),
            "it": (
                "Il Molo con la Libreria e l'ingresso al Canal Grande "
                "(o Il Molo presso la Zecca con la colonna di San Teodoro)"
            ),
        },
    },
    {
        "product_id": 15611059110236,
        "artist": "Antonio Canal",
        "label": "Molo Schiavoni",
        "titles": {
            "orig": "Il Molo verso Riva degli Schiavoni con il Palazzo Ducale",
            "pl": (
                "Molo w stronę Riva degli Schiavoni z Pałacem Dożów "
                "(lub Riva degli Schiavoni z Pałacem Dożów/"
                "Widok na Molo z Pałacem Dożów)"
            ),
            "en": (
                "The Molo looking East "
                "(or The Molo towards Riva degli Schiavoni with the Doge's Palace/"
                "Venice: The Molo from the Bacino di San Marco)"
            ),
            "de": (
                "Das Molo mit dem Dogenpalast gegen die Riva degli Schiavoni "
                "(oder Das Molo mit Blick nach Osten)"
            ),
            "fr": (
                "Le Molo vu du bassin de Saint-Marc "
                "(ou Le Molo vers la Riva degli Schiavoni "
                "avec le Palais des Doges)"
            ),
            "es": (
                "El Molo hacia Riva degli Schiavoni con el Palacio Ducal "
                "(o El Molo mirando al este)"
            ),
            "nl": (
                "De Molo naar de Riva degli Schiavoni met het Dogepaleis "
                "(of De Molo gezien naar het oosten)"
            ),
            "it": (
                "Il Molo verso Riva degli Schiavoni con il Palazzo Ducale "
                "(o Il Molo guardando verso est)"
            ),
        },
    },
    {
        "product_id": 15610497958236,
        "artist": "Antonio Canal",
        "label": "Piazza San Marco Venice",
        "titles": {
            "orig": (
                "Piazza San Marco verso la Procuratie Nuove "
                "e l'edificio di San Geminiano"
            ),
            "pl": (
                "Plac Świętego Marka w Wenecji "
                "(lub Plac św. Marka w stronę kościoła San Geminiano/"
                "Widok Placu św. Marka w kierunku zachodnim)"
            ),
            "en": (
                "Piazza San Marco, Venice "
                "(or Piazza San Marco looking West towards San Geminiano/"
                "Piazza San Marco towards the Procuratie Nuove "
                "and the Church of San Geminiano)"
            ),
            "de": (
                "Der Markusplatz in Venedig "
                "(oder Der Markusplatz nach Westen gegen San Geminiano)"
            ),
            "fr": (
                "La place Saint-Marc, Venise "
                "(ou La place Saint-Marc vers l'église San Geminiano)"
            ),
            "es": (
                "La plaza de San Marcos, Venecia "
                "(o La plaza de San Marcos mirando hacia el oeste "
                "y la iglesia de San Geminiano)"
            ),
            "nl": (
                "Het San Marcoplein, Venetië "
                "(of Het San Marcoplein in westelijke richting naar San Geminiano)"
            ),
            "it": (
                "Piazza San Marco, Venezia "
                "(o Piazza San Marco verso le Procuratie Nuove "
                "e la chiesa di San Geminiano)"
            ),
        },
    },
    {
        "product_id": 15610497696092,
        "artist": "Antonio Canal",
        "label": "Piazza Procuratie kampanila",
        "titles": {
            "orig": "Piazza San Marco verso le Procuratie Nuove",
            "pl": (
                "Plac św. Marka w stronę Procuratie Nuove "
                "(lub Plac Świętego Marka w Wenecji z widokiem na Procuratie Nuove/"
                "Widok Placu św. Marka w kierunku zachodnim z dzwonnicą)"
            ),
            "en": (
                "Piazza San Marco looking West towards the Procuratie Nuove "
                "(or Piazza San Marco, Venice)"
            ),
            "de": (
                "Der Markusplatz nach Westen gegen die Procuratie Nuove "
                "(oder Der Markusplatz in Venedig)"
            ),
            "fr": (
                "La place Saint-Marc vers les Procuratie Nuove "
                "(ou La place Saint-Marc, Venise)"
            ),
            "es": (
                "La plaza de San Marcos mirando hacia el oeste y las Procuratie Nuove "
                "(o La plaza de San Marcos, Venecia)"
            ),
            "nl": (
                "Het San Marcoplein in westelijke richting naar de Procuratie Nuove "
                "(of Het San Marcoplein, Venetië)"
            ),
            "it": (
                "Piazza San Marco verso le Procuratie Nuove "
                "(o Piazza San Marco, Venezia)"
            ),
        },
    },
    {
        "product_id": 15610497892700,
        "artist": "Antonio Canal",
        "label": "Piazza sud ovest",
        "titles": {
            "orig": "Piazza San Marco verso sud e ovest",
            "pl": (
                "Plac św. Marka w stronę południową i zachodnią "
                "(lub Widok Placu św. Marka w kierunku południowo-zachodnim/"
                "Plac Świętego Marka w Wenecji)"
            ),
            "en": (
                "Piazza San Marco Looking South and West "
                "(or Piazza San Marco, Venice)"
            ),
            "de": (
                "Der Markusplatz mit Blick nach Süden und Westen "
                "(oder Der Markusplatz in Venedig)"
            ),
            "fr": (
                "La place Saint-Marc, regardant vers le sud et l'ouest "
                "(ou La place Saint-Marc, Venise)"
            ),
            "es": (
                "La plaza de San Marcos mirando hacia el sur y el oeste "
                "(o La plaza de San Marcos, Venecia)"
            ),
            "nl": (
                "Het San Marcoplein in zuidelijke en westelijke richting "
                "(of Het San Marcoplein, Venetië)"
            ),
            "it": (
                "Piazza San Marco verso sud e ovest (o Piazza San Marco, Venezia)"
            ),
        },
    },
    {
        "product_id": 15611057078620,
        "artist": "Antonio Canal",
        "label": "Plac sw Marka Wenecja",
        "titles": {
            "orig": "Piazza San Marco verso la Basilica",
            "pl": (
                "Plac Świętego Marka w Wenecji "
                "(lub Plac św. Marka w stronę Bazyliki/"
                "Plac św. Marka w kierunku wschodnim)"
            ),
            "en": (
                "The Piazza San Marco in Venice "
                "(or Piazza San Marco Looking East along the Central Line)"
            ),
            "de": (
                "Der Markusplatz in Venedig "
                "(oder Der Markusplatz gegen Osten mit der Basilika)"
            ),
            "fr": (
                "La place Saint-Marc, Venise "
                "(ou La place Saint-Marc vers la basilique)"
            ),
            "es": (
                "La plaza de San Marcos en Venecia "
                "(o La plaza de San Marcos mirando hacia el este)"
            ),
            "nl": (
                "Het San Marcoplein, Venetië "
                "(of Het San Marcoplein in oostelijke richting naar de basiliek)"
            ),
            "it": (
                "Piazza San Marco, Venezia "
                "(o Piazza San Marco verso la Basilica e il Palazzo Ducale)"
            ),
        },
    },
    {
        "product_id": 15611049214300,
        "artist": "Antonio Canal",
        "label": "Powrot Bucintoro",
        "titles": {
            "orig": "Il ritorno del Bucintoro al Molo nel giorno dell'Ascensione",
            "pl": (
                "Powrót Bucentaura do portu przy Pałacu Dożów "
                "(lub Bucintoro na Molo w dzień Wniebowstąpienia/"
                "Bucentaur na Molo w dzień Wniebowstąpienia)"
            ),
            "en": (
                "The Bucintoro Returning to the Molo on Ascension Day "
                "(or The Bucintoro at the Molo on Ascension Day)"
            ),
            "de": (
                "Die Rückkehr des Bucintoro zum Molo am Himmelfahrtstag "
                "(oder Der Bucintoro am Molo am Himmelfahrtstag)"
            ),
            "fr": (
                "Le retour du Bucentaure au Molo le jour de l'Ascension "
                "(ou Le Bucentaure au Molo le jour de l'Ascension)"
            ),
            "es": (
                "El regreso del Bucentauro al Molo el día de la Ascensión "
                "(o El Bucentauro en el Molo el día de la Ascensión)"
            ),
            "nl": (
                "De terugkeer van de Bucintoro naar de Molo op Hemelvaartsdag "
                "(of De Bucintoro bij de Molo op Hemelvaartsdag)"
            ),
            "it": (
                "Il ritorno del Bucintoro al Molo nel giorno dell'Ascensione "
                "(o Il Bucintoro al Molo nel giorno dell'Ascensione)"
            ),
        },
    },
    {
        "product_id": 15611047346524,
        "artist": "Antonio Canal",
        "label": "Bucintoro E1924",
        "titles": {
            "orig": (
                "Il Bucintoro al molo nel giorno dell'Ascensione "
                "(E1924-3-48) (c. 1745)"
            ),
            "pl": (
                "Bucintoro na Molo w dzień Wniebowstąpienia (E1924-3-48) (ok. 1745) "
                "(lub Bucentaur na Molo w dzień Wniebowstąpienia (E1924-3-48) (ok. 1745)/"
                "Powrót Bucentaura do Molo w Dzień Wniebowstąpienia "
                "(E1924-3-48) (ok. 1745))"
            ),
            "en": (
                "The Bucintoro at the Molo on Ascension Day (E1924-3-48) (c. 1745) "
                "(or The Return of the Bucintoro to the Molo on Ascension Day "
                "(E1924-3-48) (c. 1745))"
            ),
            "de": (
                "Der Bucintoro am Molo am Himmelfahrtstag (E1924-3-48) (ca. 1745) "
                "(oder Die Rückkehr des Bucintoro zum Molo am Himmelfahrtstag "
                "(E1924-3-48) (ca. 1745))"
            ),
            "fr": (
                "Le Bucentaure au Molo le jour de l'Ascension (E1924-3-48) (vers 1745) "
                "(ou Le retour du Bucentaure au Molo le jour de l'Ascension "
                "(E1924-3-48) (vers 1745))"
            ),
            "es": (
                "El Bucentauro en el Molo el día de la Ascensión (E1924-3-48) (c. 1745) "
                "(o El regreso del Bucentauro al Molo el día de la Ascensión "
                "(E1924-3-48) (c. 1745))"
            ),
            "nl": (
                "De Bucintoro bij de Molo op Hemelvaartsdag (E1924-3-48) (ca. 1745) "
                "(of De terugkeer van de Bucintoro naar de Molo op Hemelvaartsdag "
                "(E1924-3-48) (ca. 1745))"
            ),
            "it": (
                "Il Bucintoro al molo nel giorno dell'Ascensione "
                "(E1924-3-48) (ca. 1745) "
                "(o Il ritorno del Bucintoro al molo nel giorno dell'Ascensione "
                "(E1924-3-48) (ca. 1745))"
            ),
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
    pl = load_product_title_fields(pid)
    print(f"  PL: {pl.get('pl', '')}")
    print(f"  locales: {res.get('saved_locales', [])}")


def main() -> int:
    for cfg in PRODUCTS:
        _apply(cfg)
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 15).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
