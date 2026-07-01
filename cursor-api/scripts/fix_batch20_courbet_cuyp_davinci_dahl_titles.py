"""Poprawka tytulow: batch 20 — Courbet (5), Cuyp (7), Da Vinci (7), Hans Dahl (5), Johan Dahl (2)."""
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
        "product_id": 15611221705052,
        "artist": "Gustave Courbet",
        "label": "Jelen w sniegu",
        "titles": {
            "orig": "Cerf courant dans la neige",
            "pl": "Jeleń biegnący po śniegu (lub Jeleń biegnący w śniegu)",
            "en": "Deer Running in the Snow",
            "de": "Hirsch im Schnee (oder Ein Hirsch läuft durch den Schnee)",
            "fr": "Cerf courant dans la neige",
            "es": "Ciervo corriendo en la nieve",
            "nl": "Hert rennend in de sneeuw (of Hert rennend door de sneeuw)",
            "it": "Cervo che corre nella neve",
        },
    },
    {
        "product_id": 15611221934428,
        "artist": "Gustave Courbet",
        "label": "Jo Irlandka",
        "titles": {
            "orig": "Jo, la belle Irlandaise (29.100.63) (1865–1866)",
            "pl": (
                "Jo, piękna Irlandka (29.100.63) (1865–1866) "
                "(lub Piękna irlandzka dziewczyna (29.100.63) (1865–1866))"
            ),
            "en": (
                "Jo, the Beautiful Irishwoman (29.100.63) (1865–1866) "
                "(or Jo, the Beautiful Irish Girl (29.100.63) (1865–1866))"
            ),
            "de": "Jo, die schöne Irländerin (29.100.63) (1865–1866)",
            "fr": "Jo, la belle Irlandaise (29.100.63) (1865–1866)",
            "es": "Jo, la bella irlandesa (29.100.63) (1865–1866)",
            "nl": "Jo, de schone Ierse (29.100.63) (1865–1866)",
            "it": "Jo, la bella irlandese (29.100.63) (1865–1866)",
        },
    },
    {
        "product_id": 15611223081308,
        "artist": "Gustave Courbet",
        "label": "Kobieta w falach",
        "titles": {
            "orig": "La Femme aux vagues (of La Femme dans les vagues)",
            "pl": "Kobieta w falach (lub Kobieta wśród fal)",
            "en": "The Woman in the Waves (or The Woman in the Wave)",
            "de": "Die Frau in den Wellen",
            "fr": "La Femme aux vagues (ou La Femme dans les vagues)",
            "es": "La mujer en las olas (o La mujer entre las olas)",
            "nl": "De vrouw in de golven",
            "it": "La donna tra le onde",
        },
    },
    {
        "product_id": 15611224949084,
        "artist": "Gustave Courbet",
        "label": "Kobieta z papuga",
        "titles": {
            "orig": "La Femme au perroquet",
            "pl": "Kobieta z papugą",
            "en": "Woman with a Parrot",
            "de": "Die Frau mit dem Papagei",
            "fr": "La Femme au perroquet",
            "es": "La mujer del loro (o Mujer con un loro)",
            "nl": "Vrouw met een papegaai",
            "it": "La donna con il pappagallo",
        },
    },
    {
        "product_id": 15611222557020,
        "artist": "Gustave Courbet",
        "label": "Naga kobieta z psem",
        "titles": {
            "orig": "Femme nue au chien (of Femme nue avec un chien)",
            "pl": "Akt kobiecy z psem (lub Naga kobieta z pieskiem)",
            "en": "Nude Woman with a Dog (or Nude Woman with Dog)",
            "de": "Nackte Frau mit Hund",
            "fr": "Femme nue au chien (ou Femme nue avec un chien)",
            "es": "Mujer desnuda con un perro",
            "nl": "Naakte vrouw met hond",
            "it": "Donna nuda con cane",
        },
    },
    {
        "product_id": 15611270332764,
        "artist": "Aelbert Cuyp",
        "label": "Jezdzcy odpoczywajacy",
        "titles": {
            "orig": "Rustende ruiters in een landschap",
            "pl": (
                "Odpoczynek jeźdźców w krajobrazie "
                "(lub Odpoczywający jeźdźcy w krajobrazie)"
            ),
            "en": "Horsemen Resting in a Landscape",
            "de": "Rastende Reiter in einer Landschaft",
            "fr": "Cavaliers se reposant dans un paysage",
            "es": "Jinetes descansando en un paisaje",
            "nl": "Rustende ruiters in een landschap",
            "it": "Cavalieri che si riposano in un paesaggio",
        },
    },
    {
        "product_id": 15611271545180,
        "artist": "Aelbert Cuyp",
        "label": "Moza pod Dordrecht",
        "titles": {
            "orig": "De Maas te Dordrecht (of Gezicht op de Maas bij Dordrecht)",
            "pl": (
                "Moza pod Dordrecht "
                "(lub Rzeka Moza w Dordrecht/Widok Mozy pod Dordrecht)"
            ),
            "en": "The Maas at Dordrecht (or View of the Maas at Dordrecht)",
            "de": (
                "Die Maas bei Dordrecht "
                "(oder Ansicht der Maas bei Dordrecht)"
            ),
            "fr": "La Meuse à Dordrecht (ou Vue de la Meuse à Dordrecht)",
            "es": "El Mosa en Dordrecht (o Vista del Mosa en Dordrecht)",
            "nl": "De Maas te Dordrecht (of Gezicht op de Maas bij Dordrecht)",
            "it": "La Mosa a Dordrecht (o Veduta della Mosa a Dordrecht)",
        },
    },
    {
        "product_id": 15611272397148,
        "artist": "Aelbert Cuyp",
        "label": "Mlodzi pasterze",
        "titles": {
            "orig": "Jonge herders met koeien (of Herders met koeien)",
            "pl": "Młodzi pasterze z krowami (lub Młody pastuszek z krowami)",
            "en": "Young Herdsmen with Cows (or Young Herdsman with Cows)",
            "de": "Junge Hirten mit Kühen (oder Hirten mit Kühen)",
            "fr": "Jeunes bergers avec des vaches",
            "es": "Jóvenes pastores con vacas",
            "nl": "Jonge herders met koeien (of Herders met koeien)",
            "it": "Giovani pastori con mucche",
        },
    },
    {
        "product_id": 15611270791516,
        "artist": "Aelbert Cuyp",
        "label": "Pejzaz rzeczny",
        "titles": {
            "orig": "Rivierlandschap met ruiter en vee (of Rivierlandschap met ruiters)",
            "pl": (
                "Krajobraz rzeczny z jeźdźcem i wieśniakami "
                "(lub Krajobraz rzeczny z jeźdźcami i pasterzami)"
            ),
            "en": (
                "River Landscape with Horseman and Peasants "
                "(or River Landscape with Riders)"
            ),
            "de": (
                "Flusslandschaft mit Reiter und Bauern "
                "(oder Flusslandschaft mit Reitern)"
            ),
            "fr": (
                "Paysage fluvial avec cavalier et paysans "
                "(ou Paysage de rivière avec cavaliers)"
            ),
            "es": (
                "Paisaje fluvial con jinete y campesinos "
                "(o Paisaje de río con jinetes)"
            ),
            "nl": "Rivierlandschap met ruiter en vee (of Rivierlandschap met ruiters)",
            "it": (
                "Paesaggio fluviale con cavaliere e contadini "
                "(o Paesaggio fluviale con cavalieri)"
            ),
        },
    },
    {
        "product_id": 15611270627676,
        "artist": "Aelbert Cuyp",
        "label": "Valkhof Nijmegen",
        "titles": {
            "orig": (
                "Landschap met gezicht op het Valkhof te Nijmegen "
                "(NG 2314) (c. 1655–1660)"
            ),
            "pl": (
                "Krajobraz z widokiem na Valkhof w Nijmegen "
                "(NG 2314) (c. 1655–1660) "
                "(lub Widok na pałac Valkhof w Nijmegen (NG 2314) (c. 1655–1660))"
            ),
            "en": (
                "Landscape with a View of the Valkhof, Nijmegen "
                "(NG 2314) (c. 1655–1660) "
                "(or A View of the Valkhof, Nijmegen (NG 2314) (c. 1655–1660))"
            ),
            "de": (
                "Landschaft mit Blick auf den Valkhof, Nijmegen "
                "(NG 2314) (c. 1655–1660) "
                "(oder Blick auf den Valkhof von Südwesten (NG 2314) (c. 1655–1660))"
            ),
            "fr": (
                "Paysage avec vue du Valkhof à Nimègue "
                "(NG 2314) (c. 1655–1660)"
            ),
            "es": (
                "Paisaje con una vista del Valkhof, Nimega "
                "(NG 2314) (c. 1655–1660)"
            ),
            "nl": (
                "Landschap met gezicht op het Valkhof te Nijmegen "
                "(NG 2314) (c. 1655–1660)"
            ),
            "it": (
                "Paesaggio con veduta del Valkhof a Nimega "
                "(NG 2314) (c. 1655–1660)"
            ),
        },
    },
    {
        "product_id": 15611272135004,
        "artist": "Aelbert Cuyp",
        "label": "Widok Dordrechtu",
        "titles": {
            "orig": "Gezicht op Dordrecht vanaf de Maas (of Gezicht op Dordrecht)",
            "pl": (
                "Widok Dordrechtu od strony rzeki Mozy "
                "(lub Widok Dordrechtu/Dordrecht z rzeki Mozy)"
            ),
            "en": "View of Dordrecht (or View of Dordrecht from the Maas)",
            "de": "Ansicht von Dordrecht (oder Blick auf Dordrecht von der Maas)",
            "fr": "Vue de Dordrecht (ou Vue de Dordrecht depuis la Meuse)",
            "es": "Vista de Dordrecht (o Vista de Dordrecht desde el Mosa)",
            "nl": "Gezicht op Dordrecht vanaf de Maas (of Gezicht op Dordrecht)",
            "it": "Veduta di Dordrecht (o Veduta di Dordrecht dalla Mosa)",
        },
    },
    {
        "product_id": 15611271840092,
        "artist": "Aelbert Cuyp",
        "label": "Lodz przewozowa",
        "titles": {
            "orig": (
                "Het veerboot (The Passage Boat) "
                "(of Gezicht op een veerboot met passagiers)"
            ),
            "pl": (
                "Prom pasażerski "
                "(lub Łódź pasażerska/Statki pasażerskie na rzece)"
            ),
            "en": "The Passage Boat (or A Passage Boat)",
            "de": "Das Fährboot (oder Das Passagierboot)",
            "fr": "Le bac (ou Le bateau de passage)",
            "es": "El transbordador (o El barco de pasaje)",
            "nl": (
                "Het veerboot "
                "(of Gezicht op een veerboot met passagiers)"
            ),
            "it": "Il traghetto (o Il battello di passaggio)",
        },
    },
    {
        "product_id": 15611264139612,
        "artist": "Leonardo Da Vinci",
        "label": "Dama z gronostajem",
        "titles": {
            "orig": "Dama con l'ermellino",
            "pl": "Dama z gronostajem (lub Dama z łasiczką)",
            "en": "Lady with an Ermine",
            "de": "Dame mit dem Hermelin",
            "fr": "La Dame à l'hermine",
            "es": "La dama del armiño",
            "nl": "De dame met de hermelijn",
            "it": "Dama con l'ermellino",
        },
    },
    {
        "product_id": 15611266203996,
        "artist": "Leonardo Da Vinci",
        "label": "Madonna z Dzieciatkiem",
        "titles": {
            "orig": "Madonna col Bambino (NG1300)",
            "pl": (
                "Madonna z Dzieciątkiem (NG1300) "
                "(lub Matka Boska Karmiąca (NG1300))"
            ),
            "en": (
                "The Virgin and Child (NG1300) "
                "(or Madonna and Child (NG1300))"
            ),
            "de": (
                "Maria mit dem Kind (NG1300) "
                "(oder Madonna mit dem Kind (NG1300))"
            ),
            "fr": (
                "La Vierge et l'Enfant (NG1300) "
                "(ou La Vierge allaitant (NG1300))"
            ),
            "es": (
                "La Virgen y el Niño (NG1300) "
                "(o Virgen de la leche (NG1300))"
            ),
            "nl": (
                "Maria met Kind (NG1300) "
                "(of De Maagd en het Kind (NG1300))"
            ),
            "it": (
                "Madonna col Bambino (NG1300) "
                "(o Madonna del Latte (NG1300))"
            ),
        },
    },
    {
        "product_id": 15611264631132,
        "artist": "Leonardo Da Vinci",
        "label": "Madonna z gozdzikiem",
        "titles": {
            "orig": "Madonna del Garofano",
            "pl": "Madonna z goździkiem",
            "en": "Madonna of the Carnation (or Virgin with the Carnation)",
            "de": "Madonna mit der Nelke",
            "fr": "La Vierge au oeillet (ou La Madone au oeillet)",
            "es": "La Virgen del clavel",
            "nl": "Madonna met de anjer",
            "it": "Madonna del Garofano",
        },
    },
    {
        "product_id": 15611265253724,
        "artist": "Leonardo Da Vinci",
        "label": "Mona Lisa",
        "titles": {
            "orig": (
                "Monna Lisa "
                "(of Ritratto di Lisa Gherardini, moglie di Francesco del Giocondo/"
                "La Gioconda)"
            ),
            "pl": "Mona Lisa (lub Gioconda)",
            "en": (
                "Mona Lisa "
                "(or Portrait of Lisa Gherardini, wife of Francesco del Giocondo/"
                "La Gioconda)"
            ),
            "de": "Mona Lisa (oder La Gioconda)",
            "fr": (
                "La Joconde "
                "(ou Portrait de Lisa Gherardini, épouse de Francesco del Giocondo)"
            ),
            "es": "Mona Lisa (o La Gioconda)",
            "nl": "Mona Lisa (of De Mona Lisa/La Gioconda)",
            "it": "Monna Lisa (o La Gioconda)",
        },
    },
    {
        "product_id": 15611265745244,
        "artist": "Leonardo Da Vinci",
        "label": "La Belle Ferronniere",
        "titles": {
            "orig": "Ritratto di dama (of La Belle Ferronnière)",
            "pl": (
                "La Belle Ferronnière "
                "(lub Portret damy/Piękna Ferronnière)"
            ),
            "en": (
                "La Belle Ferronnière "
                "(or Portrait of an Unknown Woman)"
            ),
            "de": (
                "La Belle Ferronnière "
                "(oder Bildnis einer unbekannten Frau)"
            ),
            "fr": (
                "La Belle Ferronnière "
                "(ou Portrait d'une femme inconnue)"
            ),
            "es": (
                "La Belle Ferronnière "
                "(o Retrato de una dama desconocida)"
            ),
            "nl": (
                "La Belle Ferronnière "
                "(of Portret van een onbekende vrouw)"
            ),
            "it": "La Belle Ferronnière (o Ritratto di dama)",
        },
    },
    {
        "product_id": 15611266892124,
        "artist": "Leonardo Da Vinci",
        "label": "Swieta Anna Samotrzecia",
        "titles": {
            "orig": "Sant'Anna, la Vergine e il Bambino con l'agnellino",
            "pl": (
                "Święta Anna Samotrzecia "
                "(lub Dziewica z Dzieciątkiem i świętą Anną)"
            ),
            "en": (
                "The Virgin and Child with Saint Anne "
                "(or The Virgin and Child with Saint Anne and a Lamb)"
            ),
            "de": (
                "Anna selbdritt "
                "(oder Maria mit dem Kind und der heiligen Anna)"
            ),
            "fr": (
                "La Vierge, l'Enfant Jésus et sainte Anne "
                "(ou Sainte Anne, la Vierge et l'Enfant Jésus)"
            ),
            "es": "Santa Ana, la Virgen y el Niño",
            "nl": "Maria met Kind en Sint-Anna (of Heilige Anna te Drieën)",
            "it": "Sant'Anna, la Vergine e il Bambino con l'agnellino",
        },
    },
    {
        "product_id": 15611313619292,
        "artist": "Hans Dahl",
        "label": "Dziewczyna nad fiordem",
        "titles": {
            "orig": "Pike ved en fjord (of Ung pike ved en fjord)",
            "pl": "Dziewczyna nad fiordem (lub Młoda dziewczyna nad fiordem)",
            "en": "Girl Beside a Fjord (or A Young Girl by a Fjord)",
            "de": "Mädchen an einem Fjord (oder Junges Mädchen am Fjord)",
            "fr": (
                "Jeune fille au bord d'un fjord "
                "(ou Fille à côté d'un fjord)"
            ),
            "es": "Joven junto a un fiordo (o Muchacha al lado de un fiordo)",
            "nl": "Meisje bij een fjord (of Jong meisje aan een fjord)",
            "it": (
                "Ragazza accanto a un fiordo "
                "(o Giovane donna vicino a un fiordo)"
            ),
        },
    },
    {
        "product_id": 15611313422684,
        "artist": "Hans Dahl",
        "label": "Fiord z zaglowka",
        "titles": {
            "orig": "Fjordparti med seilbåt (of Seilas på fjorden)",
            "pl": (
                "Fiord z łodzią żaglową "
                "(lub Rejs na fiordzie/Łódź żaglowa na fiordzie)"
            ),
            "en": "Fjord with a Sailing Boat (or Sailing on the Fjord)",
            "de": "Fjord mit Segelboot (oder Fahrt auf dem Fjord)",
            "fr": "Fjord avec voilier (ou Navigation sur le fjord)",
            "es": "Fiordo con velero (o Navegando en el fiordo)",
            "nl": "Fjord met zeilboot (of Varen op de fjord)",
            "it": "Fiordo con barca a vela (o Navigazione sul fiordo)",
        },
    },
    {
        "product_id": 15611313226076,
        "artist": "Hans Dahl",
        "label": "Mloda kobieta na lace",
        "titles": {
            "orig": "A young woman in the meadow (of Ung kvinne på engen)",
            "pl": "Młoda kobieta na łące (lub Dziewczyna na łące)",
            "en": "A Young Woman in the Meadow (or Young Woman in a Meadow)",
            "de": "Eine junge Frau auf der Wiese",
            "fr": "Une jeune femme dans la prairie",
            "es": "Una joven en el prado",
            "nl": "Een jonge vrouw in de weide",
            "it": "Una giovane donna nel prato",
        },
    },
    {
        "product_id": 15611314012508,
        "artist": "Hans Dahl",
        "label": "Norweski fiord",
        "titles": {
            "orig": "Norsk fjordlandskap (of Parti fra en norsk fjord)",
            "pl": (
                "Norweski krajobraz z fiordem "
                "(lub Widok z fiordu norweskiego/Krajobraz z fiordem)"
            ),
            "en": (
                "Norwegian Fjord Landscape "
                "(or Scene from a Norwegian Fjord)"
            ),
            "de": (
                "Norwegische Fjordlandschaft "
                "(oder Szene aus einem norwegischen Fjord)"
            ),
            "fr": (
                "Paysage de fjord norvégien "
                "(ou Scène d'un fjord norvégien)"
            ),
            "es": (
                "Paisaje de un fiordo noruego "
                "(o Escena de un fiordo noruego)"
            ),
            "nl": "Noors fjordlandschap (of Gezicht op een Noorse fjord)",
            "it": (
                "Paesaggio del fiordo norvegese "
                "(o Veduta di un fiordo norvegese)"
            ),
        },
    },
    {
        "product_id": 15611313783132,
        "artist": "Hans Dahl",
        "label": "Wiesniaczka z grabiami",
        "titles": {
            "orig": "Bondejente med rive (of Ung kvinne med rive i fjellet)",
            "pl": (
                "Wiejska dziewczyna z grabiami "
                "(lub Dziewczyna z grabiami na górskiej łące)"
            ),
            "en": (
                "Peasant Girl with a Rake "
                "(or Girl with a Rake/Young Woman with a Rake)"
            ),
            "de": (
                "Bauernmädchen mit Harke "
                "(oder Junges Mädchen mit Rechen in den Bergen)"
            ),
            "fr": (
                "Jeune paysanne au râteau "
                "(ou Jeune fille au râteau)"
            ),
            "es": (
                "Joven campesina con un rastrillo "
                "(o Muchacha con rastrillo)"
            ),
            "nl": (
                "Boerenmeisje met een hark "
                "(of Jong meisje met hark in de bergen)"
            ),
            "it": "Giovane contadina con rastrello (o Ragazza con rastrello)",
        },
    },
    {
        "product_id": 15611527332188,
        "artist": "Johan Dahl",
        "label": "Larvik",
        "titles": {
            "orig": "Larvik i måneskinn",
            "pl": (
                "Larvik w świetle księżyca "
                "(lub Larvik nocą w świetle księżyca)"
            ),
            "en": "Larvik by Moonlight",
            "de": "Larvik im Mondschein",
            "fr": "Larvik au clair de lune",
            "es": "Larvik a la luz de la luna",
            "nl": "Larvik bij maanlicht",
            "it": "Larvik al chiaro di luna",
        },
    },
    {
        "product_id": 15611527922012,
        "artist": "Johan Dahl",
        "label": "Widok z Bastei",
        "titles": {
            "orig": "Utsikt fra Bastei (of Fra Bastei)",
            "pl": "Widok z Bastei (lub Z Bastei)",
            "en": "View from Bastei",
            "de": "Blick von der Bastei (oder Ausblick von der Bastei)",
            "fr": "Vue de la Bastei",
            "es": "Vista desde el Bastei",
            "nl": "Gezicht vanaf de Bastei",
            "it": "Veduta da Bastei",
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 20).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
