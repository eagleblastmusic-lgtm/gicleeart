"""Tlumaczenia szablonu body_html (sekcja 'SZCZEGOLY') na 6 jezykow obcych.

Sklada sie z dwoch warstw:

  1. ETYKIETY i NAGLOWEK (`BODY_LABELS_I18N`) - statyczny slownik (zero LLM,
     deterministycznie). Naglowek ('SZCZEGOLY') i etykiety pol (Tytul,
     Autor, Data powstania, ...) sa identyczne na kazdym produkcie.

  2. WARTOSCI FAKTOGRAFICZNE (`COMMON_VALUE_TRANSLATIONS`) - statyczny slownik
     najczestszych wartosci PL ('Olej na plotnie', 'Pejzaz marynistyczny',
     'XIX wiek', 'Romantyzm', ...) -> tlumaczenia. Uzywany jako FALLBACK
     gdy LLM nie poda przetlumaczonej wartosci dla danego pola.

  Pierwszenstwo (z create.push_product_translations):
     wartosc z bloku tlumaczen LLM (`tlumaczenia.<lang>.data_powstania` itd.)
        -> jesli brak: COMMON_VALUE_TRANSLATIONS (z obsluga separatorow ',', '/', ' / ')
        -> jesli brak: oryginal PL (lepszy niz pusto).
"""
from __future__ import annotations

import re

SUPPORTED_LANGS: tuple[str, ...] = ("en", "de", "fr", "es", "nl", "it")


# ---------------------------------------------------------------------------
# 1. NAGLOWEK + ETYKIETY POL (statyczny slownik per locale)
# ---------------------------------------------------------------------------

BODY_LABELS_I18N: dict[str, dict[str, str]] = {
    "pl": {
        "header": "SZCZEGÓŁY",
        "tytul": "Tytuł",
        "tytul_orig": "Tytuł oryginalny",
        "autor": "Autor",
        "data_powstania": "Data powstania",
        "miejsce_powstania": "Miejsce powstania",
        "typ": "Typ",
        "typ_value": "Obraz",
        "technika": "Technika",
        "gatunek": "Gatunek",
        "nurt": "Nurt",
        "forma": "Forma",
    },
    "en": {
        "header": "DETAILS",
        "tytul": "Title",
        "tytul_orig": "Original title",
        "autor": "Artist",
        "data_powstania": "Date",
        "miejsce_powstania": "Place of origin",
        "typ": "Type",
        "typ_value": "Painting",
        "technika": "Technique",
        "gatunek": "Genre",
        "nurt": "Style",
        "forma": "Form",
    },
    "de": {
        "header": "DETAILS",
        "tytul": "Titel",
        "tytul_orig": "Originaltitel",
        "autor": "Künstler",
        "data_powstania": "Entstehungszeit",
        "miejsce_powstania": "Entstehungsort",
        "typ": "Typ",
        "typ_value": "Gemälde",
        "technika": "Technik",
        "gatunek": "Genre",
        "nurt": "Stilrichtung",
        "forma": "Form",
    },
    "fr": {
        "header": "DÉTAILS",
        "tytul": "Titre",
        "tytul_orig": "Titre original",
        "autor": "Artiste",
        "data_powstania": "Date",
        "miejsce_powstania": "Lieu de création",
        "typ": "Type",
        "typ_value": "Tableau",
        "technika": "Technique",
        "gatunek": "Genre",
        "nurt": "Mouvement",
        "forma": "Forme",
    },
    "es": {
        "header": "DETALLES",
        "tytul": "Título",
        "tytul_orig": "Título original",
        "autor": "Autor",
        "data_powstania": "Fecha",
        "miejsce_powstania": "Lugar de creación",
        "typ": "Tipo",
        "typ_value": "Pintura",
        "technika": "Técnica",
        "gatunek": "Género",
        "nurt": "Movimiento",
        "forma": "Forma",
    },
    "nl": {
        "header": "DETAILS",
        "tytul": "Titel",
        "tytul_orig": "Originele titel",
        "autor": "Kunstenaar",
        "data_powstania": "Datering",
        "miejsce_powstania": "Plaats van ontstaan",
        "typ": "Type",
        "typ_value": "Schilderij",
        "technika": "Techniek",
        "gatunek": "Genre",
        "nurt": "Stroming",
        "forma": "Vorm",
    },
    "it": {
        "header": "DETTAGLI",
        "tytul": "Titolo",
        "tytul_orig": "Titolo originale",
        "autor": "Artista",
        "data_powstania": "Data",
        "miejsce_powstania": "Luogo di origine",
        "typ": "Tipo",
        "typ_value": "Dipinto",
        "technika": "Tecnica",
        "gatunek": "Genere",
        "nurt": "Movimento",
        "forma": "Forma",
    },
}


def body_labels(lang: str) -> dict[str, str]:
    """Zwraca dict etykiet dla danego locale (pl/en/de/fr/es/nl/it).

    Dla nieznanego locale zwraca polskie etykiety (graceful fallback).
    """
    return BODY_LABELS_I18N.get((lang or "").strip().lower(), BODY_LABELS_I18N["pl"])


# ---------------------------------------------------------------------------
# 2. SLOWNIK CZESTYCH WARTOSCI FAKTOGRAFICZNYCH (PL -> 6 jezykow)
# ---------------------------------------------------------------------------
# Klucze w slowniku TRZYMAMY w polskiej formie z poprawna pisownia (z polskimi
# diakrytykami). Lookup jest case-insensitive i tolerancyjny na trim.
# ---------------------------------------------------------------------------

COMMON_VALUE_TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- TECHNIKI MALARSKIE ---
    "Olej na płótnie": {
        "en": "Oil on canvas", "de": "Öl auf Leinwand", "fr": "Huile sur toile",
        "es": "Óleo sobre lienzo", "nl": "Olieverf op doek", "it": "Olio su tela",
    },
    "Olej na desce": {
        "en": "Oil on panel", "de": "Öl auf Holz", "fr": "Huile sur bois",
        "es": "Óleo sobre tabla", "nl": "Olieverf op paneel", "it": "Olio su tavola",
    },
    "Olej na tekturze": {
        "en": "Oil on cardboard", "de": "Öl auf Karton", "fr": "Huile sur carton",
        "es": "Óleo sobre cartón", "nl": "Olieverf op karton", "it": "Olio su cartone",
    },
    "Akwarela": {
        "en": "Watercolor", "de": "Aquarell", "fr": "Aquarelle",
        "es": "Acuarela", "nl": "Aquarel", "it": "Acquerello",
    },
    "Tempera": {
        "en": "Tempera", "de": "Tempera", "fr": "Tempera",
        "es": "Temple", "nl": "Tempera", "it": "Tempera",
    },
    "Pastel": {
        "en": "Pastel", "de": "Pastell", "fr": "Pastel",
        "es": "Pastel", "nl": "Pastel", "it": "Pastello",
    },
    "Gwasz": {
        "en": "Gouache", "de": "Gouache", "fr": "Gouache",
        "es": "Aguada", "nl": "Gouache", "it": "Guazzo",
    },
    "Tusz": {
        "en": "Ink", "de": "Tinte", "fr": "Encre",
        "es": "Tinta", "nl": "Inkt", "it": "Inchiostro",
    },
    "Akryl": {
        "en": "Acrylic", "de": "Acryl", "fr": "Acrylique",
        "es": "Acrílico", "nl": "Acryl", "it": "Acrilico",
    },
    "Akryl na płótnie": {
        "en": "Acrylic on canvas", "de": "Acryl auf Leinwand", "fr": "Acrylique sur toile",
        "es": "Acrílico sobre lienzo", "nl": "Acryl op doek", "it": "Acrilico su tela",
    },
    # --- GATUNKI MALARSKIE ---
    "Pejzaż": {
        "en": "Landscape", "de": "Landschaft", "fr": "Paysage",
        "es": "Paisaje", "nl": "Landschap", "it": "Paesaggio",
    },
    "Pejzaż marynistyczny": {
        "en": "Marine landscape", "de": "Seestück", "fr": "Paysage marin",
        "es": "Paisaje marino", "nl": "Zeegezicht", "it": "Paesaggio marino",
    },
    "Marynistyka": {
        "en": "Marine art", "de": "Marinemalerei", "fr": "Peinture de marine",
        "es": "Marina", "nl": "Marineschilderkunst", "it": "Pittura di marina",
    },
    "Portret": {
        "en": "Portrait", "de": "Porträt", "fr": "Portrait",
        "es": "Retrato", "nl": "Portret", "it": "Ritratto",
    },
    "Autoportret": {
        "en": "Self-portrait", "de": "Selbstporträt", "fr": "Autoportrait",
        "es": "Autorretrato", "nl": "Zelfportret", "it": "Autoritratto",
    },
    "Martwa natura": {
        "en": "Still life", "de": "Stillleben", "fr": "Nature morte",
        "es": "Bodegón", "nl": "Stilleven", "it": "Natura morta",
    },
    "Scena rodzajowa": {
        "en": "Genre scene", "de": "Genrebild", "fr": "Scène de genre",
        "es": "Escena de género", "nl": "Genrestuk", "it": "Scena di genere",
    },
    "Scena religijna": {
        "en": "Religious scene", "de": "Religiöses Bild", "fr": "Scène religieuse",
        "es": "Escena religiosa", "nl": "Religieus tafereel", "it": "Scena religiosa",
    },
    "Scena historyczna": {
        "en": "Historical scene", "de": "Historienbild", "fr": "Scène historique",
        "es": "Escena histórica", "nl": "Historisch tafereel", "it": "Scena storica",
    },
    "Scena mitologiczna": {
        "en": "Mythological scene", "de": "Mythologisches Bild", "fr": "Scène mythologique",
        "es": "Escena mitológica", "nl": "Mythologisch tafereel", "it": "Scena mitologica",
    },
    "Akt": {
        "en": "Nude", "de": "Akt", "fr": "Nu",
        "es": "Desnudo", "nl": "Naakt", "it": "Nudo",
    },
    "Wedutta": {
        "en": "Veduta", "de": "Vedute", "fr": "Veduta",
        "es": "Veduta", "nl": "Veduta", "it": "Veduta",
    },
    "Pejzaż miejski": {
        "en": "Cityscape", "de": "Stadtansicht", "fr": "Paysage urbain",
        "es": "Paisaje urbano", "nl": "Stadsgezicht", "it": "Paesaggio urbano",
    },
    "Pejzaż górski": {
        "en": "Mountain landscape", "de": "Gebirgslandschaft", "fr": "Paysage de montagne",
        "es": "Paisaje de montaña", "nl": "Berglandschap", "it": "Paesaggio montano",
    },
    "Pejzaż wiejski": {
        "en": "Rural landscape", "de": "Ländliche Landschaft", "fr": "Paysage rural",
        "es": "Paisaje rural", "nl": "Landelijk landschap", "it": "Paesaggio rurale",
    },
    # --- NURTY ---
    "Romantyzm": {
        "en": "Romanticism", "de": "Romantik", "fr": "Romantisme",
        "es": "Romanticismo", "nl": "Romantiek", "it": "Romanticismo",
    },
    "Realizm": {
        "en": "Realism", "de": "Realismus", "fr": "Réalisme",
        "es": "Realismo", "nl": "Realisme", "it": "Realismo",
    },
    "Impresjonizm": {
        "en": "Impressionism", "de": "Impressionismus", "fr": "Impressionnisme",
        "es": "Impresionismo", "nl": "Impressionisme", "it": "Impressionismo",
    },
    "Postimpresjonizm": {
        "en": "Post-Impressionism", "de": "Postimpressionismus", "fr": "Post-impressionnisme",
        "es": "Postimpresionismo", "nl": "Postimpressionisme", "it": "Postimpressionismo",
    },
    "Symbolizm": {
        "en": "Symbolism", "de": "Symbolismus", "fr": "Symbolisme",
        "es": "Simbolismo", "nl": "Symbolisme", "it": "Simbolismo",
    },
    "Modernizm": {
        "en": "Modernism", "de": "Moderne", "fr": "Modernisme",
        "es": "Modernismo", "nl": "Modernisme", "it": "Modernismo",
    },
    "Klasycyzm": {
        "en": "Classicism", "de": "Klassizismus", "fr": "Classicisme",
        "es": "Clasicismo", "nl": "Classicisme", "it": "Classicismo",
    },
    "Neoklasycyzm": {
        "en": "Neoclassicism", "de": "Klassizismus", "fr": "Néoclassicisme",
        "es": "Neoclasicismo", "nl": "Neoclassicisme", "it": "Neoclassicismo",
    },
    "Barok": {
        "en": "Baroque", "de": "Barock", "fr": "Baroque",
        "es": "Barroco", "nl": "Barok", "it": "Barocco",
    },
    "Renesans": {
        "en": "Renaissance", "de": "Renaissance", "fr": "Renaissance",
        "es": "Renacimiento", "nl": "Renaissance", "it": "Rinascimento",
    },
    "Manieryzm": {
        "en": "Mannerism", "de": "Manierismus", "fr": "Maniérisme",
        "es": "Manierismo", "nl": "Maniërisme", "it": "Manierismo",
    },
    "Rokoko": {
        "en": "Rococo", "de": "Rokoko", "fr": "Rococo",
        "es": "Rococó", "nl": "Rococo", "it": "Rococò",
    },
    "Secesja": {
        "en": "Art Nouveau", "de": "Jugendstil", "fr": "Art nouveau",
        "es": "Modernismo", "nl": "Art nouveau", "it": "Art nouveau",
    },
    "Ekspresjonizm": {
        "en": "Expressionism", "de": "Expressionismus", "fr": "Expressionnisme",
        "es": "Expresionismo", "nl": "Expressionisme", "it": "Espressionismo",
    },
    "Kubizm": {
        "en": "Cubism", "de": "Kubismus", "fr": "Cubisme",
        "es": "Cubismo", "nl": "Kubisme", "it": "Cubismo",
    },
    "Surrealizm": {
        "en": "Surrealism", "de": "Surrealismus", "fr": "Surréalisme",
        "es": "Surrealismo", "nl": "Surrealisme", "it": "Surrealismo",
    },
    "Akademizm": {
        "en": "Academic art", "de": "Akademismus", "fr": "Académisme",
        "es": "Academicismo", "nl": "Academisme", "it": "Accademismo",
    },
    "Naturalizm": {
        "en": "Naturalism", "de": "Naturalismus", "fr": "Naturalisme",
        "es": "Naturalismo", "nl": "Naturalisme", "it": "Naturalismo",
    },
    # --- SZKOLY ARTYSTYCZNE ---
    "szkoła düsseldorfska": {
        "en": "Düsseldorf school", "de": "Düsseldorfer Schule", "fr": "École de Düsseldorf",
        "es": "Escuela de Düsseldorf", "nl": "Düsseldorfse school", "it": "Scuola di Düsseldorf",
    },
    "szkoła monachijska": {
        "en": "Munich school", "de": "Münchner Schule", "fr": "École de Munich",
        "es": "Escuela de Múnich", "nl": "Münchense school", "it": "Scuola di Monaco",
    },
    "szkoła wenecka": {
        "en": "Venetian school", "de": "Venezianische Schule", "fr": "École vénitienne",
        "es": "Escuela veneciana", "nl": "Venetiaanse school", "it": "Scuola veneziana",
    },
    "szkoła florencka": {
        "en": "Florentine school", "de": "Florentinische Schule", "fr": "École florentine",
        "es": "Escuela florentina", "nl": "Florentijnse school", "it": "Scuola fiorentina",
    },
    "szkoła barbizońska": {
        "en": "Barbizon school", "de": "Schule von Barbizon", "fr": "École de Barbizon",
        "es": "Escuela de Barbizon", "nl": "School van Barbizon", "it": "Scuola di Barbizon",
    },
    "szkoła haska": {
        "en": "Hague school", "de": "Haager Schule", "fr": "École de La Haye",
        "es": "Escuela de La Haya", "nl": "Haagse School", "it": "Scuola dell'Aia",
    },
    # --- FORMA ---
    "Malarstwo": {
        "en": "Painting", "de": "Malerei", "fr": "Peinture",
        "es": "Pintura", "nl": "Schilderkunst", "it": "Pittura",
    },
    "Rysunek": {
        "en": "Drawing", "de": "Zeichnung", "fr": "Dessin",
        "es": "Dibujo", "nl": "Tekening", "it": "Disegno",
    },
    "Grafika": {
        "en": "Print", "de": "Grafik", "fr": "Estampe",
        "es": "Grabado", "nl": "Grafiek", "it": "Grafica",
    },
    # --- DATY / EPOKI ---
    "XV wiek": {"en": "15th century", "de": "15. Jahrhundert", "fr": "XVe siècle",
                "es": "Siglo XV", "nl": "15e eeuw", "it": "XV secolo"},
    "XVI wiek": {"en": "16th century", "de": "16. Jahrhundert", "fr": "XVIe siècle",
                 "es": "Siglo XVI", "nl": "16e eeuw", "it": "XVI secolo"},
    "XVII wiek": {"en": "17th century", "de": "17. Jahrhundert", "fr": "XVIIe siècle",
                  "es": "Siglo XVII", "nl": "17e eeuw", "it": "XVII secolo"},
    "XVIII wiek": {"en": "18th century", "de": "18. Jahrhundert", "fr": "XVIIIe siècle",
                   "es": "Siglo XVIII", "nl": "18e eeuw", "it": "XVIII secolo"},
    "XIX wiek": {"en": "19th century", "de": "19. Jahrhundert", "fr": "XIXe siècle",
                 "es": "Siglo XIX", "nl": "19e eeuw", "it": "XIX secolo"},
    "XX wiek": {"en": "20th century", "de": "20. Jahrhundert", "fr": "XXe siècle",
                "es": "Siglo XX", "nl": "20e eeuw", "it": "XX secolo"},
    "XXI wiek": {"en": "21st century", "de": "21. Jahrhundert", "fr": "XXIe siècle",
                 "es": "Siglo XXI", "nl": "21e eeuw", "it": "XXI secolo"},
    # --- MIASTA / KRAJE (najczestsze) ---
    "Ostenda": {"en": "Ostend", "de": "Ostende", "fr": "Ostende",
                "es": "Ostende", "nl": "Oostende", "it": "Ostenda"},
    "Düsseldorf": {"en": "Düsseldorf", "de": "Düsseldorf", "fr": "Düsseldorf",
                   "es": "Düsseldorf", "nl": "Düsseldorf", "it": "Düsseldorf"},
    "Monachium": {"en": "Munich", "de": "München", "fr": "Munich",
                  "es": "Múnich", "nl": "München", "it": "Monaco di Baviera"},
    "Wiedeń": {"en": "Vienna", "de": "Wien", "fr": "Vienne",
               "es": "Viena", "nl": "Wenen", "it": "Vienna"},
    "Paryż": {"en": "Paris", "de": "Paris", "fr": "Paris",
              "es": "París", "nl": "Parijs", "it": "Parigi"},
    "Rzym": {"en": "Rome", "de": "Rom", "fr": "Rome",
             "es": "Roma", "nl": "Rome", "it": "Roma"},
    "Florencja": {"en": "Florence", "de": "Florenz", "fr": "Florence",
                  "es": "Florencia", "nl": "Florence", "it": "Firenze"},
    "Wenecja": {"en": "Venice", "de": "Venedig", "fr": "Venise",
                "es": "Venecia", "nl": "Venetië", "it": "Venezia"},
    "Neapol": {"en": "Naples", "de": "Neapel", "fr": "Naples",
               "es": "Nápoles", "nl": "Napels", "it": "Napoli"},
    "Mediolan": {"en": "Milan", "de": "Mailand", "fr": "Milan",
                 "es": "Milán", "nl": "Milaan", "it": "Milano"},
    "Berlin": {"en": "Berlin", "de": "Berlin", "fr": "Berlin",
               "es": "Berlín", "nl": "Berlijn", "it": "Berlino"},
    "Hamburg": {"en": "Hamburg", "de": "Hamburg", "fr": "Hambourg",
                "es": "Hamburgo", "nl": "Hamburg", "it": "Amburgo"},
    "Drezno": {"en": "Dresden", "de": "Dresden", "fr": "Dresde",
               "es": "Dresde", "nl": "Dresden", "it": "Dresda"},
    "Lipsk": {"en": "Leipzig", "de": "Leipzig", "fr": "Leipzig",
              "es": "Lípsia", "nl": "Leipzig", "it": "Lipsia"},
    "Praga": {"en": "Prague", "de": "Prag", "fr": "Prague",
              "es": "Praga", "nl": "Praag", "it": "Praga"},
    "Bruksela": {"en": "Brussels", "de": "Brüssel", "fr": "Bruxelles",
                 "es": "Bruselas", "nl": "Brussel", "it": "Bruxelles"},
    "Antwerpia": {"en": "Antwerp", "de": "Antwerpen", "fr": "Anvers",
                  "es": "Amberes", "nl": "Antwerpen", "it": "Anversa"},
    "Amsterdam": {"en": "Amsterdam", "de": "Amsterdam", "fr": "Amsterdam",
                  "es": "Ámsterdam", "nl": "Amsterdam", "it": "Amsterdam"},
    "Haga": {"en": "The Hague", "de": "Den Haag", "fr": "La Haye",
             "es": "La Haya", "nl": "Den Haag", "it": "L'Aia"},
    "Londyn": {"en": "London", "de": "London", "fr": "Londres",
               "es": "Londres", "nl": "Londen", "it": "Londra"},
    "Madryt": {"en": "Madrid", "de": "Madrid", "fr": "Madrid",
               "es": "Madrid", "nl": "Madrid", "it": "Madrid"},
    "Sankt Petersburg": {"en": "Saint Petersburg", "de": "Sankt Petersburg",
                         "fr": "Saint-Pétersbourg", "es": "San Petersburgo",
                         "nl": "Sint-Petersburg", "it": "San Pietroburgo"},
    "Moskwa": {"en": "Moscow", "de": "Moskau", "fr": "Moscou",
               "es": "Moscú", "nl": "Moskou", "it": "Mosca"},
    "Warszawa": {"en": "Warsaw", "de": "Warschau", "fr": "Varsovie",
                 "es": "Varsovia", "nl": "Warschau", "it": "Varsavia"},
    "Kraków": {"en": "Krakow", "de": "Krakau", "fr": "Cracovie",
               "es": "Cracovia", "nl": "Krakau", "it": "Cracovia"},
    "Niemcy": {"en": "Germany", "de": "Deutschland", "fr": "Allemagne",
               "es": "Alemania", "nl": "Duitsland", "it": "Germania"},
    "Włochy": {"en": "Italy", "de": "Italien", "fr": "Italie",
               "es": "Italia", "nl": "Italië", "it": "Italia"},
    "Francja": {"en": "France", "de": "Frankreich", "fr": "France",
                "es": "Francia", "nl": "Frankrijk", "it": "Francia"},
    "Hiszpania": {"en": "Spain", "de": "Spanien", "fr": "Espagne",
                  "es": "España", "nl": "Spanje", "it": "Spagna"},
    "Holandia": {"en": "Netherlands", "de": "Niederlande", "fr": "Pays-Bas",
                 "es": "Países Bajos", "nl": "Nederland", "it": "Paesi Bassi"},
    "Belgia": {"en": "Belgium", "de": "Belgien", "fr": "Belgique",
               "es": "Bélgica", "nl": "België", "it": "Belgio"},
    "Polska": {"en": "Poland", "de": "Polen", "fr": "Pologne",
               "es": "Polonia", "nl": "Polen", "it": "Polonia"},
    "Anglia": {"en": "England", "de": "England", "fr": "Angleterre",
               "es": "Inglaterra", "nl": "Engeland", "it": "Inghilterra"},
    "Wielka Brytania": {"en": "United Kingdom", "de": "Vereinigtes Königreich",
                        "fr": "Royaume-Uni", "es": "Reino Unido",
                        "nl": "Verenigd Koninkrijk", "it": "Regno Unito"},
    # --- SPECJALNE ---
    "Nieznana": {
        "en": "Unknown", "de": "Unbekannt", "fr": "Inconnu",
        "es": "Desconocido", "nl": "Onbekend", "it": "Sconosciuto",
    },
}


# Buduje case-insensitive lookup raz przy imporcie modulu (PL klucze sa
# normalizowane do lowercase do dopasowania).
_LOWER_INDEX: dict[str, str] = {k.lower(): k for k in COMMON_VALUE_TRANSLATIONS}


def _lookup_single(value_pl: str, lang: str) -> str | None:
    """Tlumaczy POJEDYNCZA wartosc PL ze slownika. Zwraca None jesli brak."""
    s = (value_pl or "").strip()
    if not s:
        return None
    canonical = _LOWER_INDEX.get(s.lower())
    if canonical is None:
        return None
    return COMMON_VALUE_TRANSLATIONS[canonical].get(lang)


# Separatory uzywane miedzy wieloma wartosciami w jednym polu (np. "Romantyzm/Realizm",
# "Düsseldorf / Ostenda", "Romantyzm, Realizm, szkola düsseldorfska").
# Zachowujemy je w wyniku - tlumaczone sa tylko czesci miedzy nimi.
_SPLIT_RE = re.compile(r"(\s*[,/;]\s*|\s+/\s+)")


def translate_field_value(value_pl: str, lang: str) -> str | None:
    """Tlumaczy wartosc pola z mozliwoscia obslugi wielu czesci rozdzielonych
    separatorami ',' '/' ';'. Zwraca None tylko jesli ZADNA czesc nie ma
    tlumaczenia w slowniku (caller wtedy uzywa oryginalnego PL jako fallback).

    Przyklady:
      'Olej na płótnie' (lang='fr') -> 'Huile sur toile'
      'Düsseldorf / Ostenda' (lang='fr') -> 'Düsseldorf / Ostende'
      'Romantyzm/Realizm, szkoła düsseldorfska' (lang='fr')
        -> 'Romantisme/Réalisme, École de Düsseldorf'
      'XIX wiek' (lang='de') -> '19. Jahrhundert'
      '1885' (lang='fr') -> None (brak w slowniku, zostaje '1885' jako fallback)
      'Niezdefiniowana wartosc' (lang='fr') -> None
    """
    s = (value_pl or "").strip()
    if not s or lang not in SUPPORTED_LANGS:
        return None
    parts = _SPLIT_RE.split(s)
    out: list[str] = []
    matched_any = False
    for part in parts:
        if not part:
            continue
        if _SPLIT_RE.fullmatch(part):
            out.append(part)
            continue
        translated = _lookup_single(part, lang)
        if translated:
            matched_any = True
            out.append(translated)
        else:
            out.append(part)
    if not matched_any:
        return None
    return "".join(out)


def translate_field_value_or_pl(value_pl: str, lang: str) -> str:
    """Wersja z fallbackiem: zwraca tlumaczenie ze slownika ALBO oryginalny PL.

    Uzywaj gdy chcesz po prostu cos wstawic do HTML (lepiej PL niz puste pole)."""
    s = (value_pl or "").strip()
    if not s:
        return ""
    t = translate_field_value(s, lang)
    return t if t is not None else s
