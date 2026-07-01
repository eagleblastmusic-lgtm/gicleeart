"""Poprawka tytulow: batch 23 — Jansen, Knight, Leu, Lippi, Lorrain, Michelangelo, Moret, Pissarro, Potter, Ribera, Richards, Rubens, Rusinol, Ruysch, Taylor, ter Borch (35)."""
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
        "product_id": 15611528380764,
        "artist": "Johann Joseph Jansen",
        "label": "Jezioro Czterech Kantonow",
        "titles": {
            "orig": "Blick auf den Vierwaldstättersee (1900)",
            "pl": (
                "Widok na Jezioro Czterech Kantonów "
                "(lub Jezioro Czterech Kantonów (1900))"
            ),
            "en": "View of Lake Lucerne (or Lake Lucerne (1900))",
            "de": "Blick auf den Vierwaldstättersee (1900)",
            "fr": "Vue du lac des Quatre-Cantons (1900)",
            "es": (
                "Vista del lago de Lucerna "
                "(o El lago de los Cuatro Cantones (1900))"
            ),
            "nl": "Gezicht op het Vierwoudstedenmeer (1900)",
            "it": (
                "Veduta del lago di Lucerna "
                "(o Lago dei Quattro Cantoni (1900))"
            ),
        },
    },
    {
        "product_id": 15611312734556,
        "artist": "Daniel Ridgway Knight",
        "label": "Corka ogrodnika",
        "titles": {
            "orig": "The Gardener's Daughter",
            "pl": "Córka ogrodnika",
            "en": "The Gardener's Daughter",
            "de": "Die Tochter des Gärtners",
            "fr": "La fille du jardinier",
            "es": "La hija del jardinero",
            "nl": "De dochter van de tuinman",
            "it": "La figlia del giardiniere",
        },
    },
    {
        "product_id": 15611312046428,
        "artist": "Daniel Ridgway Knight",
        "label": "Picking Blossoms",
        "titles": {
            "orig": "Picking Blossoms",
            "pl": "Zbieranie kwiatów (lub Dziewczyna zbierająca kwiaty)",
            "en": "Picking Blossoms",
            "de": "Die Blütenlese (oder Mädchen beim Blütenpflücken)",
            "fr": (
                "La cueillette des fleurs "
                "(ou Jeune femme cueillant des fleurs)"
            ),
            "es": "Recogiendo flores (o Joven recogiendo flores)",
            "nl": "Bloesems plukken (of Meisje dat bloesems plukt)",
            "it": (
                "La raccolta dei fiori "
                "(o Giovane donna che raccoglie fiori)"
            ),
        },
    },
    {
        "product_id": 15611311358300,
        "artist": "Daniel Ridgway Knight",
        "label": "Palenie chrustu",
        "titles": {
            "orig": "Burning Brush",
            "pl": "Palenie chrustu (lub Palenie zarośli)",
            "en": "Burning Brush",
            "de": "Das Verbrennen von Gestrüpp (oder Reisigfeuer)",
            "fr": (
                "Brûlage de broussailles "
                "(ou Le brûlage des branches)"
            ),
            "es": "Quema de rastrojos (o La quema de maleza)",
            "nl": (
                "Struikgewas verbranden "
                "(of Het verbranden van rijshout)"
            ),
            "it": "Bruciare le sterpaglie (o Fuoco de sterpi)",
        },
    },
    {
        "product_id": 15611311489372,
        "artist": "Daniel Ridgway Knight",
        "label": "W sadzie",
        "titles": {
            "orig": "In the Orchard",
            "pl": "W sadzie",
            "en": "In the Orchard",
            "de": "Im Obstgarten (oder In der Obstplantage)",
            "fr": "Dans le verger",
            "es": "En el huerto (o En el jardín de frutales)",
            "nl": "In de boomgaard",
            "it": "Nel frutteto",
        },
    },
    {
        "product_id": 15611312275804,
        "artist": "Daniel Ridgway Knight",
        "label": "Zagubiona",
        "titles": {
            "orig": "She has lost her way (of Frosty Morning)",
            "pl": (
                "Zagubiona "
                "(lub Mroźny poranek/Młoda kobieta z koszykiem na śniegu)"
            ),
            "en": "She has lost her way (or Frosty Morning)",
            "de": "Sie hat sich verirrt (oder Frostiger Morgen)",
            "fr": (
                "Elle a perdu son chemin "
                "(ou Jeune femme au panier marchant dans la neige/"
                "Matinée givrée)"
            ),
            "es": "Se ha perdido (o Mañana helada)",
            "nl": "Ze is de weg kwijt (of Vorstachtige ochtend)",
            "it": "Si è smarrita (o Mattina gelida)",
        },
    },
    {
        "product_id": 15611294089564,
        "artist": "August Wilhelm Leu",
        "label": "Gebirgssee 1873",
        "titles": {
            "orig": "Gebirgssee mit Gebirgsmassiv im Hintergrund (1873)",
            "pl": (
                "Jezioro górskie z masywem górskim w tle "
                "(lub Jezioro górskie (1873))"
            ),
            "en": (
                "Mountain lake with a mountain range in the background (1873)"
            ),
            "de": "Gebirgssee mit Gebirgsmassiv im Hintergrund (1873)",
            "fr": (
                "Lac de montagne avec massif montagneux "
                "en arrière-plan (1873)"
            ),
            "es": (
                "Lago de montaña con macizo montañoso al fondo (1873)"
            ),
            "nl": "Bergmeer met bergmassa op de achtergrond (1873)",
            "it": (
                "Lago di montagna con massiccio montuoso "
                "sullo sfondo (1873)"
            ),
        },
    },
    {
        "product_id": 15611294318940,
        "artist": "August Wilhelm Leu",
        "label": "Konigssee 1866",
        "titles": {
            "orig": "Der Königssee mit dem Watzmann (1866)",
            "pl": (
                "Jezioro Königssee z widokiem na Watzmann "
                "(lub Jezioro Königssee i Watzmann (1866))"
            ),
            "en": (
                "Königssee with Watzmann mountain "
                "(or A View of the Watzmann Mountain and Lake Königssee (1866))"
            ),
            "de": "Der Königssee mit dem Watzmann (1866)",
            "fr": "Le lac Königssee avec le mont Watzmann (1866)",
            "es": "El lago Königssee con el monte Watzmann (1866)",
            "nl": "De Königssee met de Watzmann (1866)",
            "it": "Il lago Königssee con il monte Watzmann (1866)",
        },
    },
    {
        "product_id": 15611294581084,
        "artist": "August Wilhelm Leu",
        "label": "Shimmering lake",
        "titles": {
            "orig": (
                "Schimmernder Hochgebirgssee mit Mädchen im Kahn "
                "(of Schimmernder Gebirgssee mit zwei Mädchen im Ruderboot (1863))"
            ),
            "pl": "Migoczące jezioro górskie z dziewczętami w łodzi (1863)",
            "en": "Shimmering Mountain Lake with Girls in a Boat (1863)",
            "de": (
                "Schimmernder Hochgebirgssee mit Mädchen im Kahn "
                "(oder Schimmernder Gebirgssee mit zwei Mädchen im Ruderboot (1863))"
            ),
            "fr": (
                "Lac de montagne miroitant avec deux jeunes filles "
                "en barque (1863)"
            ),
            "es": (
                "Lago de montaña resplandeciente con muchachas "
                "en un bote (1863)"
            ),
            "nl": "Glinsterend bergmeer met meisjes in een boot (1863)",
            "it": (
                "Lago di montagna scintillante con fanciulle in barca (1863)"
            ),
        },
    },
    {
        "product_id": 15611294450012,
        "artist": "August Wilhelm Leu",
        "label": "Engstlenalm",
        "titles": {
            "orig": "Auf der Engstlenalm (Kanton Bern) (1865)",
            "pl": (
                "Na hali Engstlenalm (Kanton Bern) "
                "(lub Pasterze na hali Engstlenalm (1865))"
            ),
            "en": (
                "On the Engstlenalm (Canton of Bern) "
                "(or Alpine Pasture at Engstlenalm (1865))"
            ),
            "de": "Auf der Engstlenalm (Kanton Bern) (1865)",
            "fr": "Sur l'alpage d'Engstlenalm (Canton de Berne) (1865)",
            "es": "En el Engstlenalm (Cantón de Berna) (1865)",
            "nl": "Op de Engstlenalm (Kanton Bern) (1865)",
            "it": "Sull'alpeggio di Engstlenalm (Cantone di Berna) (1865)",
        },
    },
    {
        "product_id": 15611293958492,
        "artist": "August Wilhelm Leu",
        "label": "Norwegia fjord",
        "titles": {
            "orig": (
                "Norwegische Fjordlandschaft mit Gletscher und Rentieren (1890)"
            ),
            "pl": (
                "Norweski krajobraz fiordowy z lodowcem i reniferami "
                "(lub Krajobraz z lodowcem i reniferami (1890))"
            ),
            "en": (
                "Norwegian Fjord Landscape with Glacier and Reindeer (1890)"
            ),
            "de": (
                "Norwegische Fjordlandschaft mit Gletscher und Rentieren (1890)"
            ),
            "fr": (
                "Paysage de fjord norvégien avec glacier et rennes (1890)"
            ),
            "es": "Paisaje de fiordo noruego con glaciar y renos (1890)",
            "nl": (
                "Noors fjordlandschap met gletsjer en rendieren (1890)"
            ),
            "it": (
                "Paesaggio di un fiordo norvegese con ghiacciaio e renne (1890)"
            ),
        },
    },
    {
        "product_id": 15611293827420,
        "artist": "August Wilhelm Leu",
        "label": "Berner Alpen",
        "titles": {
            "orig": "Partie aus den Berner Alpen (1853)",
            "pl": (
                "Widok z Alp Berneńskich "
                "(lub Krajobraz w Alpach Berneńskich (1853))"
            ),
            "en": (
                "A Scene in the Bern Alps "
                "(or Part from the Bernese Alps (1853))"
            ),
            "de": "Partie aus den Berner Alpen (1853)",
            "fr": "Vue des Alpes bernoises (1853)",
            "es": "Paisaje de los Alpes berneses (1853)",
            "nl": "Gezicht op de Berner Alpen (1853)",
            "it": "Veduta delle Alpi bernesi (1853)",
        },
    },
    {
        "product_id": 15611312931164,
        "artist": "Filippo Lippi",
        "label": "Madonna Lippina",
        "titles": {
            "orig": "Madonna col Bambino e due angeli",
            "pl": (
                "Madonna z Dzieciątkiem i dwoma aniołami "
                "(lub Madonna z dwoma aniołami)"
            ),
            "en": (
                "Madonna and Child with Two Angels "
                "(or Madonna with Child and Two Angels)"
            ),
            "de": "Maria mit dem Kind und zwei Engeln",
            "fr": "La Vierge à l'Enfant avec deux anges",
            "es": "Virgen con el Niño y dos ángeles",
            "nl": "Madonna met Kind en twee engelen",
            "it": "Madonna col Bambino e due angeli",
        },
    },
    {
        "product_id": 15611524251996,
        "artist": "Claude Lorrain",
        "label": "Ucieczka do Egiptu",
        "titles": {
            "orig": (
                "Paysage avec le repos pendant la fuite en Égypte "
                "(of Le Repos pendant la fuite en Égypte)"
            ),
            "pl": (
                "Krajobraz z odpoczynkiem podczas ucieczki do Egiptu "
                "(lub Odpoczynek podczas ucieczki do Egiptu)"
            ),
            "en": (
                "Rest on the Flight into Egypt "
                "(or Landscape with the Rest on the Flight into Egypt)"
            ),
            "de": (
                "Landschaft mit der Ruhe auf der Flucht nach Ägypten "
                "(oder Ruhe auf der Flucht nach Ägypten)"
            ),
            "fr": (
                "Paysage avec le repos pendant la fuite en Égypte "
                "(ou Le Repos pendant la fuite en Égypte)"
            ),
            "es": (
                "Descanso en la huida a Egipto "
                "(o Paisaje con el descanso en la huida a Egipto)"
            ),
            "nl": (
                "Landschap met de rust op de vlucht naar Egypte "
                "(of Rust op de vlucht naar Egypte)"
            ),
            "it": (
                "Riposo durante la fuga in Egitto "
                "(o Paesaggio con il riposo durante la fuga in Egitto)"
            ),
        },
    },
    {
        "product_id": 15611524481372,
        "artist": "Claude Lorrain",
        "label": "Trojanki",
        "titles": {
            "orig": "Les Troyennes mettant le feu à leur flotte",
            "pl": (
                "Trojanki podpalające swoją flotę "
                "(lub Trojanki palące swoją flotę)"
            ),
            "en": (
                "The Trojan Women Set Fire to their Fleet "
                "(or The Trojan Women Setting Fire to Their Fleet)"
            ),
            "de": "Trojanische Frauen setzen ihre Flotte in Brand",
            "fr": "Les Troyennes mettant le feu à leur flotte",
            "es": "Las troyanas prendiendo fuego a su flota",
            "nl": "De Trojaanse vrouwen steken hun vloot in brand",
            "it": "Le donne troiane danno fuoco alla loro flotta",
        },
    },
    {
        "product_id": 15611423687004,
        "artist": "Michelangelo",
        "label": "Sw Antoni",
        "titles": {
            "orig": "Tormento di sant'Antonio",
            "pl": (
                "Kuszony przez demony święty Antoni "
                "(lub Kuszenie świętego Antoniego/Katusze świętego Antoniego)"
            ),
            "en": (
                "The Torment of Saint Anthony "
                "(or The Temptation of Saint Anthony)"
            ),
            "de": "Die Marter des heiligen Antonius",
            "fr": "Le Tourment de saint Antoine",
            "es": "El tormento de San Antonio",
            "nl": "De kwelling van de heilige Antonius",
            "it": "Tormento di sant'Antonio",
        },
    },
    {
        "product_id": 15611319419228,
        "artist": "Henry Moret",
        "label": "Sianokosy Moret",
        "titles": {
            "orig": "Fanaison ou La récolte du foin (1898)",
            "pl": "Sianokosy (lub Zbiór siana (1898))",
            "en": "Hay Harvest (or Haymaking) (1898)",
            "de": "Heuernte (1898)",
            "fr": "Fanaison ou La récolte du foin (1898)",
            "es": "Cosecha de heno (o La recogida del heno) (1898)",
            "nl": "Hooioogst (1898)",
            "it": "Raccolta del fieno (1898)",
        },
    },
    {
        "product_id": 15611305034076,
        "artist": "Camille Pissarro",
        "label": "Bougival",
        "titles": {
            "orig": (
                "Maisons à Bougival, automne "
                "(of Paysage à Louveciennes (automne))"
            ),
            "pl": (
                "Domy w Bougival (Jesień) "
                "(lub Krajobraz w Louveciennes (Jesień))"
            ),
            "en": (
                "Houses at Bougival (Autumn) "
                "(or Landscape at Louveciennes (Autumn))"
            ),
            "de": (
                "Häuser in Bougival (Herbst) "
                "(oder Landschaft bei Louveciennes (Herbst))"
            ),
            "fr": (
                "Maisons à Bougival, automne "
                "(ou Paysage à Louveciennes (automne))"
            ),
            "es": (
                "Casas en Bougival (Otoño) "
                "(o Paisaje en Louveciennes (Otoño))"
            ),
            "nl": (
                "Huizen te Bougival (Herfst) "
                "(of Landschap bij Louveciennes (Herfst))"
            ),
            "it": (
                "Case a Bougival (Autunno) "
                "(o Paesaggio a Louveciennes (Autunno))"
            ),
        },
    },
    {
        "product_id": 15611305951580,
        "artist": "Camille Pissarro",
        "label": "Kobieta myje stopy",
        "titles": {
            "orig": (
                "Femme se lavant les pieds dans un ruisseau "
                "(of Le Bain de pieds (1894))"
            ),
            "pl": "Kobieta myjąca stopy w potoku (lub Kąpiel stóp (1894))",
            "en": (
                "Woman Washing Her Feet in a Brook "
                "(or Woman Bathing Her Feet (1894))"
            ),
            "de": (
                "Frau, sich die Füße in einem Bach waschend "
                "(oder Das Fußbad (1894))"
            ),
            "fr": (
                "Femme se lavant les pieds dans un ruisseau "
                "(ou Le Bain de pieds (1894))"
            ),
            "es": (
                "Mujer lavándose los pies en un arroyo "
                "(o El baño de pies (1894))"
            ),
            "nl": (
                "Vrouw die haar voeten wast in een beek "
                "(of Het voetbad (1894))"
            ),
            "it": (
                "Donna che si lava i piedi in un ruscello "
                "(o Il bagno ai piedi (1894))"
            ),
        },
    },
    {
        "product_id": 15611305197916,
        "artist": "Camille Pissarro",
        "label": "Eragny",
        "titles": {
            "orig": "Effet de soleil du matin, Éragny (1899)",
            "pl": (
                "Efekt porannego słońca, Éragny "
                "(lub Poranne słońce w Éragny (1899))"
            ),
            "en": (
                "Morning Sunlight Effect, Éragny "
                "(or Morning, Sunlight Effect, Éragny (1899))"
            ),
            "de": (
                "Morgensonnenlandschaft, Éragny "
                "(oder Effekt des morgendlichen Sonnenlichts, Éragny (1899))"
            ),
            "fr": "Effet de soleil du matin, Éragny (1899)",
            "es": (
                "Efecto de la luz del sol de la mañana, Éragny (1899)"
            ),
            "nl": "Effect van ochtendzon, Éragny (1899)",
            "it": (
                "Effetto della luce del sole mattutino, Éragny (1899)"
            ),
        },
    },
    {
        "product_id": 15611305460060,
        "artist": "Camille Pissarro",
        "label": "Sluza Pontoise",
        "titles": {
            "orig": "L'Écluse à Pontoise",
            "pl": "Śluza w Pontoise",
            "en": "The Lock at Pontoise",
            "de": "Die Schleuse in Pontoise",
            "fr": "L'Écluse à Pontoise",
            "es": "La esclusa de Pontoise",
            "nl": "De sluis bij Pontoise",
            "it": "La chiusa a Pontoise",
        },
    },
    {
        "product_id": 15611424702812,
        "artist": "Paulus Potter",
        "label": "Byk",
        "titles": {
            "orig": "De jonge stier",
            "pl": "Młody byk (lub Byk)",
            "en": "The Young Bull (or The Bull)",
            "de": "Der junge Stier",
            "fr": "Le Jeune Taureau",
            "es": "El toro joven (o El toro)",
            "nl": "De jonge stier",
            "it": "Il giovane toro",
        },
    },
    {
        "product_id": 15611424211292,
        "artist": "Paulus Potter",
        "label": "Krowy w wodzie",
        "titles": {
            "orig": "Het spiegelende koetje (of De spiegelende koe)",
            "pl": (
                "Krowy odbijające się w wodzie "
                "(lub Odbijająca się krowa/Bydło u wodopoju)"
            ),
            "en": "Cows Reflected in the Water (or The Reflected Cow)",
            "de": "Kühe im Wasser spiegelnd (oder Die spiegelnde Kuh)",
            "fr": (
                "Vaches se reflétant dans l'eau "
                "(ou La vache qui se miroite)"
            ),
            "es": "Vacas reflejadas en el agua (o La vaca reflejada)",
            "nl": "Het spiegelende koetje (of De spiegelende koe)",
            "it": "Mucche riflesse nell'acqua (o La mucca riflessa)",
        },
    },
    {
        "product_id": 15611533033820,
        "artist": "Jusepe Ribera",
        "label": "Swieta Rodzina Ribera",
        "titles": {
            "orig": "Sagrada Familia con santa Ana y santa Catalina de Alejandría",
            "pl": (
                "Święta Rodzina ze świętą Anną i świętą Katarzyną Aleksandryjską "
                "(lub Mistyczne zaślubiny świętej Katarzyny)"
            ),
            "en": (
                "The Holy Family with Saints Anne and Catherine of Alexandria "
                "(or The Mystic Marriage of Saint Catherine)"
            ),
            "de": (
                "Die Heilige Familie mit den heiligen Anna "
                "und Katharina von Alexandrien"
            ),
            "fr": (
                "La Sainte Famille avec sainte Anne "
                "et sainte Catherine d'Alexandrie"
            ),
            "es": (
                "Sagrada Familia con santa Ana y santa Catalina de Alejandría"
            ),
            "nl": (
                "De Heilige Familie met de heilige Anna "
                "en de heilige Catharina van Alexandrië"
            ),
            "it": (
                "Sacra Famiglia con sant'Anna e santa Caterina d'Alessandria"
            ),
        },
    },
    {
        "product_id": 15611428897116,
        "artist": "William Trost Richards",
        "label": "Skaliste wybrzeze Richards",
        "titles": {
            "orig": "A Rocky Coast",
            "pl": "Skaliste wybrzeże (lub Skalisty brzeg)",
            "en": "A Rocky Coast",
            "de": "Eine felsige Küste",
            "fr": "Une côte rocheuse",
            "es": "Una costa rocosa",
            "nl": "Een rotsachtige kust",
            "it": "Una costa rocciosa",
        },
    },
    {
        "product_id": 15611429355868,
        "artist": "William Trost Richards",
        "label": "Donegal",
        "titles": {
            "orig": "Donegal Bay",
            "pl": "Zatoka Donegal",
            "en": "Donegal Bay",
            "de": "Die Bucht von Donegal (oder Donegal-Bucht)",
            "fr": "La baie de Donegal",
            "es": "La bahía de Donegal",
            "nl": "De baai van Donegal",
            "it": "La baia di Donegal",
        },
    },
    {
        "product_id": 15611425096028,
        "artist": "Peter Paul Rubens",
        "label": "Cimon i Pero",
        "titles": {
            "orig": "Cimon en Pero (of Romeinse liefdadigheid)",
            "pl": (
                "Cymon i Pero "
                "(lub Caritas Romana/Miłosierdzie rzymskie)"
            ),
            "en": "Cimon and Pero (or Roman Charity)",
            "de": "Cimon und Pero (oder Römische Caritas)",
            "fr": "Cimon et Péro (ou La Charité romaine)",
            "es": "Cimón y Pero (o Caridad romana)",
            "nl": "Cimon en Pero (of Romeinse liefdadigheid)",
            "it": "Cimone e Pero (o Carità Romana)",
        },
    },
    {
        "product_id": 15611425456476,
        "artist": "Peter Paul Rubens",
        "label": "Daniel",
        "titles": {
            "orig": "Daniel in de leeuwenkuil",
            "pl": "Daniel w jaskini lwów (lub Daniel w lwiej jamie)",
            "en": "Daniel in the Lions' Den",
            "de": "Daniel in der Löwengrube",
            "fr": "Daniel dans la fosse aux lions",
            "es": "Daniel en el foso de los leones",
            "nl": "Daniel in de leeuwenkuil",
            "it": "Daniele nella fossa dei leoni",
        },
    },
    {
        "product_id": 15611425980764,
        "artist": "Peter Paul Rubens",
        "label": "Grzech pierworodny",
        "titles": {
            "orig": (
                "De zondeval (of Het Paradijs met de zondeval van de mens)"
            ),
            "pl": (
                "Ogród Eden z upadkiem człowieka "
                "(lub Raj i grzech pierworodny/Grzech pierworodny w Raju)"
            ),
            "en": (
                "The Garden of Eden with the Fall of Man "
                "(or The Fall of Man)"
            ),
            "de": "Das Paradies mit dem Sündenfall",
            "fr": "Le Paradis terrestre avec la chute de l'homme",
            "es": (
                "El jardín del Edén con la caída del hombre "
                "(o El Paraíso y la caída del hombre)"
            ),
            "nl": (
                "De zondeval (of Het Paradijs met de zondeval van de mens)"
            ),
            "it": "Il paradiso terrestre con la caduta dell'uomo",
        },
    },
    {
        "product_id": 15611427094876,
        "artist": "Santiago Rusiñol",
        "label": "Postac kobieca",
        "titles": {
            "orig": "Figura femenina (of Retrat de noia)",
            "pl": (
                "Postać kobieca "
                "(lub Portret dziewczyny/Dziewczyna w czerni profilu)"
            ),
            "en": "Female Figure (or Portrait of a Girl)",
            "de": "Weibliche Figur (oder Porträt eines Mädchens)",
            "fr": "Figure féminine (ou Portrait de jeune fille)",
            "es": "Figura femenina (o Retrato de muchacha)",
            "nl": "Vrouwenfiguur (of Portret van een meisje)",
            "it": "Figura femminile (o Ritratto di ragazza)",
        },
    },
    {
        "product_id": 15611426406748,
        "artist": "Rachel Ruysch",
        "label": "Wazon z kwiatami",
        "titles": {
            "orig": "Vaas met bloemen (of Bloemen in een glazen vaas)",
            "pl": (
                "Wazon z kwiatami "
                "(lub Bukiet kwiatów w szklanym wazie/Kwiaty w szklanym wazonie)"
            ),
            "en": "Vase with Flowers (or Flowers in a Glass Vase)",
            "de": "Vasen mit Blumen (oder Blumenstrauß in einer Glasvase)",
            "fr": "Vase de fleurs (ou Fleurs dans un vase de verre)",
            "es": "Jarrón con flores (o Flores en un jarrón de vidrio)",
            "nl": "Vaas met bloemen (of Bloemen in een glazen vaas)",
            "it": "Vaso con fiori (o Fiori in un vaso di vetro)",
        },
    },
    {
        "product_id": 15611317485916,
        "artist": "Henry King Taylor",
        "label": "Rybacy",
        "titles": {
            "orig": "Fishermen at Sea",
            "pl": "Rybacy na morzu",
            "en": "Fishermen at Sea",
            "de": "Fischer auf See",
            "fr": "Pêcheurs en mer",
            "es": "Pescadores en el mar",
            "nl": "Vissers op zee",
            "it": "Pescatori in mare",
        },
    },
    {
        "product_id": 15611318042972,
        "artist": "Henry King Taylor",
        "label": "Pilot cutter rowing",
        "titles": {
            "orig": (
                "Pilot cutter no. 3 with a rowing boat coming alongside "
                "and a paddlesteamer in the distance (1858)"
            ),
            "pl": (
                "Kuter pilotowy nr 3 z podpływającą łodzią wiosłową "
                "i parowcem kołowym w oddali (1858)"
            ),
            "en": (
                "Pilot cutter no. 3 with a rowing boat coming alongside "
                "and a paddlesteamer in the distance (1858)"
            ),
            "de": (
                "Lotsenkutter Nr. 3 mit einem herannahenden Ruderboot "
                "und einem Raddampfer in der Ferne (1858)"
            ),
            "fr": (
                "Bateau-pilote n° 3 avec une barque à rames accostant "
                "et un bateau à aubes au loin (1858)"
            ),
            "es": (
                "Cúter de prácticos n.º 3 con un bote de remos acercándose "
                "y un vapor de paletas a lo lejos (1858)"
            ),
            "nl": (
                "Loodsboot nr. 3 met een naderende roeiboot "
                "en een radersstoomboot in de verte (1858)"
            ),
            "it": (
                "Pilotina n. 3 con una barca a remi che si avvicina "
                "e un piroscafo a ruote in lontananza (1858)"
            ),
        },
    },
    {
        "product_id": 15611530183004,
        "artist": "Gesina ter Borch",
        "label": "Moses ter Borch",
        "titles": {
            "orig": "Memorial portret van Moses ter Borch (1645-1667)",
            "pl": (
                "Portret pośmiertny Mosesa ter Borcha "
                "(lub Portret pamięci Mosesa ter Borcha)"
            ),
            "en": "Memorial Portrait of Moses ter Borch",
            "de": "Gedächtnisbildnis des Moses ter Borch",
            "fr": "Portrait commémoratif de Moses ter Borch",
            "es": "Retrato conmemorativo de Moses ter Borch",
            "nl": "Memorial portret van Moses ter Borch (1645-1667)",
            "it": "Ritratto commemorativo di Moses ter Borch",
        },
    },
    {
        "product_id": 15611317813596,
        "artist": "Henry King Taylor",
        "label": "Pilot cutter Dover",
        "titles": {
            "orig": (
                "Pilot Cutter No. 3 off Dover "
                "(with paddlesteamer in the distance)"
            ),
            "pl": (
                "Kuter pilotowy nr 3 "
                "(lub Kuter pilotowy nr 3 u wybrzeży Dover "
                "(wersja z parowcem w tle))"
            ),
            "en": (
                "Pilot Cutter No. 3 off Dover "
                "(with paddlesteamer in the distance)"
            ),
            "de": (
                "Lotsenkutter Nr. 3 vor Dover "
                "(mit Raddampfer im Hintergrund)"
            ),
            "fr": (
                "Bateau-pilote n° 3 au large de Douvres "
                "(avec bateau à aubes au loin)"
            ),
            "es": (
                "Cúter de prácticos n.º 3 frente a Dover "
                "(con vapor de paletas al fondo)"
            ),
            "nl": (
                "Loodsboot nr. 3 voor de kust van Dover "
                "(met radersstoomboot in de verte)"
            ),
            "it": (
                "Pilotina n. 3 al largo di Dover "
                "(con piroscafo a ruote in lontananza)"
            ),
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 23).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
