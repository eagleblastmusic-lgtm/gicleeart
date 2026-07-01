"""Poprawka tytulow: batch 22 — Diemer (5), Dupre (4), Fantin (6), Gierymski (4), Gude (3), Hassam (6), Hogarth, Hulk (2), Peeters."""
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
        "product_id": 15611420279132,
        "artist": "Michael Zeno Diemer",
        "label": "Skaliste wybrzeze",
        "titles": {
            "orig": "Felsige Meeresküste im frühen Morgenlicht",
            "pl": (
                "Skaliste wybrzeże wczesnym rankiem "
                "(lub Skaliste wybrzeże morskie w porannym świetle/Skaliste wybrzeże)"
            ),
            "en": (
                "A Rocky Coastal Landscape at Early Morning "
                "(or Rocky Sea Coast in Early Morning Light)"
            ),
            "de": "Felsige Meeresküste im frühen Morgenlicht",
            "fr": (
                "Paysage côtier rocheux au petit matin "
                "(ou Côte marine rocheuse dans la lumière du matin)"
            ),
            "es": (
                "Paisaje costero rocoso temprano en la mañana "
                "(o Costa marina rocosa a la luz de la mañana)"
            ),
            "nl": (
                "Rotsachtig kustlandschap in de vroege ochtend "
                "(of Rotsachtige zeekust in het vroege ochtendlicht)"
            ),
            "it": (
                "Paesaggio costiero roccioso la mattina presto "
                "(o Costa marina rocciosa nella luce del mattino)"
            ),
        },
    },
    {
        "product_id": 15611420705116,
        "artist": "Michael Zeno Diemer",
        "label": "Trojmasztowiec bez rozmiaru",
        "titles": {
            "orig": "Dreimaster auf hoher See (of Dreimaster auf See)",
            "pl": "Trójmasztowiec na pełnym morzu (lub Trójmasztowiec na morzu)",
            "en": "Three-Master on the High Seas (or A Three-Master at Sea)",
            "de": "Dreimaster auf hoher See (oder Dreimaster auf See)",
            "fr": "Trois-mâts en haute mer (ou Un trois-mâts en mer)",
            "es": "Tres mástiles en alta mar (o Un tres mástiles en el mar)",
            "nl": "Driemaster op volle zee (of Een driemaster op zee)",
            "it": "Veliero a tre alberi in alto mare (o Un tre alberi in mare)",
        },
    },
    {
        "product_id": 15611423162716,
        "artist": "Michael Zeno Diemer",
        "label": "Trojmasztowiec 60x80",
        "titles": {
            "orig": "Dreimaster auf hoher See (60x80)",
            "pl": (
                "Trójmasztowiec na pełnym morzu (60x80) "
                "(lub Trójmasztowiec na wzburzonym morzu)"
            ),
            "en": (
                "Three-Master on the High Seas (60x80) "
                "(or Three-Master in Choppy Seas)"
            ),
            "de": (
                "Dreimaster auf hoher See (60x80) "
                "(oder Dreimaster in bewegter See)"
            ),
            "fr": (
                "Trois-mâts en haute mer (60x80) "
                "(ou Trois-mâts par mer agitée)"
            ),
            "es": (
                "Tres mástiles en alta mar (60x80) "
                "(o Tres mástiles en mar gruesa)"
            ),
            "nl": (
                "Driemaster op volle zee (60x80) "
                "(of Driemaster op woelige zee)"
            ),
            "it": (
                "Veliero a tre alberi in alto mare (60x80) "
                "(o Tre alberi in mare mosso)"
            ),
        },
    },
    {
        "product_id": 15611422114140,
        "artist": "Michael Zeno Diemer",
        "label": "Trojmasztowiec Kalabria",
        "titles": {
            "orig": (
                "Dreimaster vor der kalabrischen Küste "
                "(of Dreimaster an der kalabrischen Küste)"
            ),
            "pl": (
                "Trójmasztowiec u wybrzeży Kalabrii "
                "(lub Trójmasztowiec przed kalabryjskim wybrzeżem)"
            ),
            "en": (
                "A Three Master off the Coast of Calabria "
                "(or Three-master off the Calabrian coast)"
            ),
            "de": (
                "Dreimaster vor der kalabrischen Küste "
                "(oder Dreimaster an der kalabrischen Küste)"
            ),
            "fr": "Trois-mâts au large de la côte calabraise",
            "es": "Tres mástiles frente a la costa de Calabria",
            "nl": "Driemaster voor de kust van Calabrië",
            "it": "Veliero a tre alberi al largo della costa calabrese",
        },
    },
    {
        "product_id": 15611422638428,
        "artist": "Michael Zeno Diemer",
        "label": "Messina",
        "titles": {
            "orig": "Dreimaster in der Strasse von Messina",
            "pl": "Trójmasztowiec w Cieśninie Mesyńskiej",
            "en": "Three-Master in the Strait of Messina",
            "de": "Dreimaster in der Strasse von Messina",
            "fr": "Trois-mâts dans le détroit de Messine",
            "es": "Tres mástiles en el estrecho de Mesina",
            "nl": "Driemaster in de Straat van Messina",
            "it": "Veliero a tre alberi nello Stretto di Messina",
        },
    },
    {
        "product_id": 15611532509532,
        "artist": "Julien Dupré",
        "label": "Uparta krowa",
        "titles": {
            "orig": "La Vache récalcitrante (of La Vache obstinée)",
            "pl": "Uparta krowa (lub Nieposłuszna krowa)",
            "en": "The Stubborn Cow (or The Recalcitrant Cow)",
            "de": "Die widerspenstige Kuh",
            "fr": "La Vache récalcitrante (ou La Vache obstinée)",
            "es": "La vaca recalcitrante (o La vaca obstinada)",
            "nl": "De weerbarstige koe",
            "it": "La mucca recalcitrante (o La mucca ostinata)",
        },
    },
    {
        "product_id": 15611531788636,
        "artist": "Julien Dupré",
        "label": "Sianokosy",
        "titles": {
            "orig": "Fenaison (of La Récolte des foins)",
            "pl": "Sianokosy (lub Zbiór siana/Żniwa sianokosów)",
            "en": "The Hay Harvester (or The Hay Harvest/Haymaking)",
            "de": "Heuernte (oder Die Heuernte)",
            "fr": "Fenaison (ou La Récolte des foins)",
            "es": "La recogida del heno (o La cosecha de heno)",
            "nl": "De hooioogst (of Hooien)",
            "it": "La raccolta del fieno",
        },
    },
    {
        "product_id": 15611531231580,
        "artist": "Julien Dupré",
        "label": "Zniwiarka",
        "titles": {
            "orig": "La Faneuse (of Fenaison)",
            "pl": "Kobieta zbierająca siano (lub Sianokosy/Żniwiarka)",
            "en": "The Harvester (or The Haymaker)",
            "de": "Die Heuernterin (oder Die Heuwenderin)",
            "fr": "La Faneuse (ou Fenaison)",
            "es": "La segadora (o La cosechadora de heno)",
            "nl": "De hooister (of De oogstster)",
            "it": "La mietitrice (o La fienaiola)",
        },
    },
    {
        "product_id": 15611530707292,
        "artist": "Julien Dupré",
        "label": "Zycie na wsi",
        "titles": {
            "orig": "La Vie à la campagne (of Retour du troupeau)",
            "pl": "Życie na wsi (lub Powrót stada)",
            "en": "Country Life (or The Herd's Return/Returning from the Pasture)",
            "de": "Landleben (oder Rückkehr der Herde)",
            "fr": "La Vie à la campagne (ou Retour du troupeau)",
            "es": "La vida en el campo (o El regreso del rebaño)",
            "nl": "Landleven (of De terugkeer van de kudde)",
            "it": "Vita in campagna (o Il ritorno del gregge)",
        },
    },
    {
        "product_id": 15611315749212,
        "artist": "Henri Fantin-Latour",
        "label": "Biale roze",
        "titles": {
            "orig": "Roses blanches",
            "pl": "Białe róże",
            "en": "White Roses",
            "de": "Weiße Rosen",
            "fr": "Roses blanches",
            "es": "Rosas blancas",
            "nl": "Witte rozen",
            "it": "Rose bianche",
        },
    },
    {
        "product_id": 15611315913052,
        "artist": "Henri Fantin-Latour",
        "label": "Martwa natura",
        "titles": {
            "orig": "Nature morte aux fleurs et fruits (of Fleurs et fruits)",
            "pl": "Martwa natura z kwiatami i owocami (lub Kwiaty i owoce)",
            "en": "Still Life with Flowers and Fruit (or Flowers and Fruit)",
            "de": (
                "Stilleben mit Blumen und Früchten "
                "(oder Blumen und Früchte)"
            ),
            "fr": "Nature morte aux fleurs et fruits (ou Fleurs et fruits)",
            "es": (
                "Naturaleza muerta con flores y frutas "
                "(o Flores y frutas)"
            ),
            "nl": "Stilleven met bloemen en vruchten (of Bloemen en fruit)",
            "it": "Natura morta con fiori e frutta (o Fiori e frutta)",
        },
    },
    {
        "product_id": 15611315290460,
        "artist": "Henri Fantin-Latour",
        "label": "Owoce i kwiaty",
        "titles": {
            "orig": "Fruits et fleurs (B.M. 514) (1866)",
            "pl": (
                "Owoce i kwiaty (B.M. 514) (1866) "
                "(lub Martwa natura z kwiatami i owocami)"
            ),
            "en": (
                "Fruit and Flowers (B.M. 514) (1866) "
                "(or Fruits and Flowers)"
            ),
            "de": (
                "Früchte und Blumen (B.M. 514) (1866) "
                "(oder Obst und Blumen)"
            ),
            "fr": "Fruits et fleurs (B.M. 514) (1866)",
            "es": (
                "Frutas y flores (B.M. 514) (1866) "
                "(o Naturaleza muerta con flores y frutas)"
            ),
            "nl": (
                "Fruit en bloemen (B.M. 514) (1866) "
                "(of Stilleven met bloemen en vruchten)"
            ),
            "it": (
                "Frutta e fiori (B.M. 514) (1866) "
                "(o Natura morta con fiori e frutta)"
            ),
        },
    },
    {
        "product_id": 15611315487068,
        "artist": "Henri Fantin-Latour",
        "label": "Roze i lilie",
        "titles": {
            "orig": "Roses et lis (of Roses et lys)",
            "pl": "Róże i lilie",
            "en": "Roses and Lilies",
            "de": "Rosen und Lilien",
            "fr": "Roses et lis (ou Roses et lys)",
            "es": "Rosas y lirios",
            "nl": "Rozen en lelies",
            "it": "Rose e gigli",
        },
    },
    {
        "product_id": 15611315618140,
        "artist": "Henri Fantin-Latour",
        "label": "Roze w wazonie",
        "titles": {
            "orig": "Roses dans un vase (of Roses dans un vase de verre)",
            "pl": "Róże w wazonie (lub Róże w szklanym wazonie)",
            "en": "Roses in a Vase (or Roses in a Glass Vase)",
            "de": "Rosen in einer Vase (oder Rosen in einer Glasvase)",
            "fr": "Roses dans un vase (ou Roses dans un vase de verre)",
            "es": "Rosas en un jarrón (o Rosas en un jarrón de vidrio)",
            "nl": "Rozen in een vaas (of Rozen in een glazen vaas)",
            "it": "Rose in un vaso (o Rose in un vaso di vetro)",
        },
    },
    {
        "product_id": 15611317223772,
        "artist": "Henri Fantin-Latour",
        "label": "Zinnias",
        "titles": {
            "orig": "Zinnias (of Bouquet de zinnias)",
            "pl": "Cynie (lub Bukiet cynii)",
            "en": "Zinnias (or Bouquet of Zinnias)",
            "de": "Zinnien (oder Zinnienstrauß)",
            "fr": "Zinnias (ou Bouquet de zinnias)",
            "es": "Zinias (o Jarrón con zinias)",
            "nl": "Zinnia's (of Boeket zinnia's)",
            "it": "Zinnie (o Bouquet di zinnie)",
        },
    },
    {
        "product_id": 15611291500892,
        "artist": "Aleksander Gierymski",
        "label": "Chlop z Bronowic",
        "titles": {
            "orig": "Chłop z Bronowic (of Portret chłopa z Bronowic)",
            "pl": "Chłop z Bronowic (lub Portret chłopa z Bronowic)",
            "en": (
                "Peasant from Bronowice "
                "(or Portrait of a Peasant from Bronowice)"
            ),
            "de": (
                "Bauer aus Bronowice "
                "(oder Porträt eines Bauern aus Bronowice)"
            ),
            "fr": (
                "Paysan de Bronowice "
                "(ou Portrait d'un paysan de Bronowice)"
            ),
            "es": (
                "Campesino de Bronowice "
                "(o Retrato de un campesino de Bronowice)"
            ),
            "nl": (
                "Boer uit Bronowice "
                "(of Portret van een boer uit Bronowice)"
            ),
            "it": (
                "Contadino di Bronowice "
                "(o Ritratto di un contadino di Bronowice)"
            ),
        },
    },
    {
        "product_id": 15611291795804,
        "artist": "Aleksander Gierymski",
        "label": "Dziewczyna z Bronowic",
        "titles": {
            "orig": "Dziewczyna z Bronowic (of Portret dziewczyny z Bronowic)",
            "pl": "Dziewczyna z Bronowic (lub Portret dziewczyny z Bronowic)",
            "en": (
                "Girl from Bronowice "
                "(or Portrait of a Girl from Bronowice)"
            ),
            "de": (
                "Mädchen aus Bronowice "
                "(oder Porträt eines Mädchens aus Bronowice)"
            ),
            "fr": (
                "Jeune fille de Bronowice "
                "(ou Portrait d'une jeune fille de Bronowice)"
            ),
            "es": (
                "Muchacha de Bronowice "
                "(o Retrato de una joven de Bronowice)"
            ),
            "nl": (
                "Meisje uit Bronowice "
                "(of Portret van een meisje uit Bronowice)"
            ),
            "it": (
                "Ragazza di Bronowice "
                "(o Ritratto di una ragazza di Bronowice)"
            ),
        },
    },
    {
        "product_id": 15611292090716,
        "artist": "Aleksander Gierymski",
        "label": "Powisle",
        "titles": {
            "orig": "Powiśle (of Wybrzeże Wisły)",
            "pl": "Powiśle (lub Wybrzeże Wisły)",
            "en": "Powiśle (or Riverbank of the Vistula)",
            "de": "Powiśle (oder Das Weichselufer)",
            "fr": "Powiśle (ou La Rive de la Vistule)",
            "es": "Powiśle (o La orilla del Vístula)",
            "nl": "Powiśle (of De oever van de Wisła)",
            "it": "Powiśle (o La riva della Vistola)",
        },
    },
    {
        "product_id": 15611292287324,
        "artist": "Aleksander Gierymski",
        "label": "Pomarańczarka",
        "titles": {
            "orig": "Żydówka z pomarańczami (of Pomarańczarka)",
            "pl": "Żydówka z pomarańczami (lub Pomarańczarka)",
            "en": "Jewess with Oranges (or Orange Seller)",
            "de": "Jüdin mit Orangen (oder Die Apfelsinenverkäuferin)",
            "fr": "Juive aux oranges (ou La Marchande d'oranges)",
            "es": "Judía con naranjas (o La vendedora de naranjas)",
            "nl": "Jodin met sinaasappels (of De sinaasappelverkoopster)",
            "it": "Ebrea con arance (o La venditrice di arance)",
        },
    },
    {
        "product_id": 15611314340188,
        "artist": "Hans Gude",
        "label": "Balestrand",
        "titles": {
            "orig": "Balestrand (of Fra Balestrand)",
            "pl": "Balestrand (lub Widok z Balestrand)",
            "en": "Balestrand (or From Balestrand)",
            "de": "Balestrand (oder Ansicht von Balestrand)",
            "fr": "Balestrand (ou Vue de Balestrand)",
            "es": "Balestrand (o Vista de Balestrand)",
            "nl": "Balestrand (of Gezicht op Balestrand)",
            "it": "Balestrand (o Veduta di Balestrand)",
        },
    },
    {
        "product_id": 15611315093852,
        "artist": "Hans Gude",
        "label": "Fiord Oslo",
        "titles": {
            "orig": "Fra Kristianiafjorden (of Innseilingen til Kristiania)",
            "pl": (
                "Z Fiordu Oslo "
                "(lub Wpływając do fiordu Oslo/Z fiordu Kristiania)"
            ),
            "en": "From the Inlet of Oslo (or Entering the Oslo Fjord)",
            "de": (
                "Aus dem Christianiafjord "
                "(oder Einfahrt in den Christianiafjord)"
            ),
            "fr": (
                "Du fjord d'Oslo "
                "(ou L'entrée du fjord de Kristiania)"
            ),
            "es": (
                "Del fiordo de Oslo "
                "(o Entrada al fiordo de Cristianía)"
            ),
            "nl": (
                "Van de Oslofjord "
                "(of Binnenvaren van de Kristianiafjord)"
            ),
            "it": (
                "Dal fiordo di Oslo "
                "(o Ingresso nel fiordo di Kristiania)"
            ),
        },
    },
    {
        "product_id": 15611314733404,
        "artist": "Hans Gude",
        "label": "Swieza bryza",
        "titles": {
            "orig": "Frisk bris på den norske kyst (of Frisk bris)",
            "pl": (
                "Świeży wiatr u wybrzeży Norwegii "
                "(lub Świeża bryza na norweskim wybrzeżu)"
            ),
            "en": "Fresh Breeze on the Norwegian Coast (or Fresh Breeze)",
            "de": (
                "Frische Brise an der norwegischen Küste "
                "(oder Frische Brise)"
            ),
            "fr": (
                "Brise fraîche sur la côte norvégienne "
                "(ou Brise fraîche)"
            ),
            "es": (
                "Brisa fresca en la costa noruega (o Brisa fresca)"
            ),
            "nl": "Frisse bries op de Noorse kust (of Frisse bries)",
            "it": (
                "Brezza fresca sulla costa norvegese (o Brezza fresca)"
            ),
        },
    },
    {
        "product_id": 15611309818204,
        "artist": "Childe Hassam",
        "label": "Deszczowy Boston",
        "titles": {
            "orig": "Rainy Day, Boston",
            "pl": "Deszczowy dzień w Bostonie (lub Deszczowy dzień, Boston)",
            "en": "Rainy Day, Boston",
            "de": "Regnerischer Tag, Boston",
            "fr": "Jour de pluie, Boston",
            "es": "Día lluvioso, Boston",
            "nl": "Regenachtige dag, Boston",
            "it": "Giorno di pioggia, Boston",
        },
    },
    {
        "product_id": 15611310735708,
        "artist": "Childe Hassam",
        "label": "Lorelei",
        "titles": {
            "orig": "The Lorelei",
            "pl": "Lorelei",
            "en": "The Lorelei",
            "de": "Die Lorelei",
            "fr": "La Lorelei",
            "es": "Lorelei",
            "nl": "Lorelei",
            "it": "Lorelei",
        },
    },
    {
        "product_id": 15611309195612,
        "artist": "Childe Hassam",
        "label": "East Hampton",
        "titles": {
            "orig": "Beach at East Hampton (of Dunes at East Hampton)",
            "pl": "Plaża w East Hampton (lub Wydmy w East Hampton)",
            "en": "Beach at East Hampton (or Dunes at East Hampton)",
            "de": "Strand von East Hampton (oder Dünen in East Hampton)",
            "fr": "Plage à East Hampton (ou Dunes à East Hampton)",
            "es": "Playa en East Hampton (o Dunas en East Hampton)",
            "nl": "Strand te East Hampton (of Duinen bij East Hampton)",
            "it": "Spiaggia a East Hampton (o Dune a East Hampton)",
        },
    },
    {
        "product_id": 15611310965084,
        "artist": "Childe Hassam",
        "label": "Appledore",
        "titles": {
            "orig": "The South Ledges, Appledore",
            "pl": (
                "Południowe skały, Appledore "
                "(lub Południowe półki skalne na wyspie Appledore)"
            ),
            "en": "The South Ledges, Appledore",
            "de": "Die südlichen Felskanten, Appledore",
            "fr": "Les récifs du sud, Appledore",
            "es": "Los arrecifes del sur, Appledore",
            "nl": "De zuidelijke rotsen, Appledore",
            "it": "Le scogliere del sud, Appledore",
        },
    },
    {
        "product_id": 15611307524444,
        "artist": "Childe Hassam",
        "label": "U kwiaciarki",
        "titles": {
            "orig": "At the Florist (of The Florist)",
            "pl": "U kwiaciarki (lub U kwiaciarza)",
            "en": "At the Florist (or The Florist)",
            "de": "Beim Blumenhändler",
            "fr": "Chez le fleuriste",
            "es": "En la floristería (o En lo del florista)",
            "nl": "Bij de bloemist",
            "it": "Dal fioraio",
        },
    },
    {
        "product_id": 15611310375260,
        "artist": "Childe Hassam",
        "label": "Laka Concord",
        "titles": {
            "orig": "The Concord Meadow",
            "pl": "Łąka w Concord",
            "en": "The Concord Meadow",
            "de": "Die Wiese in Concord",
            "fr": "La prairie de Concord",
            "es": "Prado en Concord",
            "nl": "De weide in Concord",
            "it": "Il prato di Concord",
        },
    },
    {
        "product_id": 15611428503900,
        "artist": "William Hogarth",
        "label": "Miss Mary Edwards",
        "titles": {
            "orig": "Miss Mary Edwards",
            "pl": (
                "Portret Miss Mary Edwards "
                "(lub Portret panny Mary Edwards)"
            ),
            "en": "Miss Mary Edwards",
            "de": "Miss Mary Edwards",
            "fr": "Miss Mary Edwards",
            "es": "Miss Mary Edwards",
            "nl": "Miss Mary Edwards",
            "it": "Miss Mary Edwards",
        },
    },
    {
        "product_id": 15611291042140,
        "artist": "Abraham Hulk",
        "label": "Wyjscie w morze",
        "titles": {
            "orig": "Uitvarende vissersschepen (of Op zee hinaus)",
            "pl": "Wyjście w morze (lub Statki na wzburzonym morzu)",
            "en": (
                "Heading out to Sea "
                "(or Outward Bound/Ships in a Choppy Sea)"
            ),
            "de": "Auf See hinaus (oder Auslaufende Fischerboote)",
            "fr": (
                "Départ en mer "
                "(ou Bateaux de pêche en mer agitée)"
            ),
            "es": (
                "Haciéndose a la mar "
                "(o Barcos de pesca en el mar picado)"
            ),
            "nl": "Uitvarende vissersschepen (of Op zee hinaus)",
            "it": "Uscita in mare (o Imbarcazioni in un mare mosso)",
        },
    },
    {
        "product_id": 15611291238748,
        "artist": "Abraham Hulk",
        "label": "Zachod slonca",
        "titles": {
            "orig": "Shipping at sunset",
            "pl": (
                "Flotylla o zachodzie słońca "
                "(lub Statki o zachodzie słońca/Żaglowce o zachodzie słońca)"
            ),
            "en": "Shipping at sunset",
            "de": (
                "Schiffe im Abendrot "
                "(oder Schiffe bei Sonnenuntergang)"
            ),
            "fr": "Navires au coucher du soleil",
            "es": "Barcos al atardecer",
            "nl": "Schepen bij zonsondergang",
            "it": "Navi al tramonto",
        },
    },
    {
        "product_id": 15611526873436,
        "artist": "Jan Peeters I",
        "label": "Galeony",
        "titles": {
            "orig": (
                "Spaans en Engels galjoen in de storm "
                "(of Spaans galjoen vergaat in een storm bij een kustfort)"
            ),
            "pl": (
                "Hiszpańskie i angielskie galeony podczas sztormu "
                "(lub Katastrofa galeonów w czasie burzy na skalistym wybrzeżu)"
            ),
            "en": (
                "Spanish and English Galleons Foundering in Stormy Waters "
                "(or A Spanish Galleon Wrecked in a Storm)"
            ),
            "de": (
                "Großes Seestück "
                "(oder Spanische und englische Galeonen im Sturm "
                "vor einer Steilküste)"
            ),
            "fr": "Galions espagnol et anglais sombrant dans la tempête",
            "es": (
                "Galeones españoles e ingleses naufragando en una tormenta"
            ),
            "nl": (
                "Spaans en Engels galjoen in de storm "
                "(of Spaans galjoen vergaat in een storm bij een kustfort)"
            ),
            "it": (
                "Galeoni spagnoli e inglesi che naufragano in una tempesta"
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 22).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
