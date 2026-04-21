"""Tlumaczenia nazw opcji wariantow i ich wartosci na 6 jezykow obcych.

Opcje wariantow (Kolor / Rozmiar / Rodzaj drewna) i ich wartosci (Czarny / Brąz /
Sosna / Dąb / S / L / XL / 50x70 / ...) sa STALE w sklepie - powtarzaja sie na
KAZDYM produkcie generowanym przez `dodajobraz`. Dlatego trzymamy tlumaczenia
deterministycznie po stronie aplikacji (zero zuzycia tokenow LLM, zero ryzyka
rozjazdu nazw miedzy produktami, idealna spojnosc multi-market).

Push do Shopify odbywa sie przez Translations API (resource: ProductOption,
ProductOptionValue) - patrz `create.push_option_translations`.

Jesli dojdzie nowa nazwa opcji / nowa wartosc (nieobecna w slownikach),
funkcje `translate_option_name` / `translate_option_value` zwroca polskie
oryginaly (graceful fallback) i wypisza warning w logu - wtedy dopisujemy
brakujace tlumaczenia ponizej.
"""
from __future__ import annotations

# Jezyki obce sklepu - musza pokrywac sie z TRANSLATION_LANGS z prompt_builder.py.
SUPPORTED_LANGS: tuple[str, ...] = ("en", "de", "fr", "es", "nl", "it")


# ---------------------------------------------------------------------------
# Nazwy opcji wariantow ('Kolor', 'Rozmiar', 'Rodzaj drewna')
# ---------------------------------------------------------------------------

OPTION_NAME_TRANSLATIONS: dict[str, dict[str, str]] = {
    "Kolor": {
        "en": "Color",
        "de": "Farbe",
        "fr": "Couleur",
        "es": "Color",
        "nl": "Kleur",
        "it": "Colore",
    },
    "Rozmiar": {
        "en": "Size",
        "de": "Größe",
        "fr": "Taille",
        "es": "Tamaño",
        "nl": "Maat",
        "it": "Dimensione",
    },
    "Rodzaj drewna": {
        "en": "Wood type",
        "de": "Holzart",
        "fr": "Type de bois",
        "es": "Tipo de madera",
        "nl": "Houtsoort",
        "it": "Tipo di legno",
    },
}


# ---------------------------------------------------------------------------
# Wartosci opcji - tlumaczenia per jezyk.
#
# Konwencja:
#   - rozmiary literowe (S/L/XL) i wymiarowe (50x70, 70x100) - bez tlumaczenia,
#     identycznie we wszystkich jezykach (uzywamy 'as_is' helpera w runtime).
#   - kolory ramy / rodzaje drewna - tlumaczone naturalnie.
# ---------------------------------------------------------------------------

OPTION_VALUE_TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- KOLORY RAMY ---
    "Czarny": {
        "en": "Black",
        "de": "Schwarz",
        "fr": "Noir",
        "es": "Negro",
        "nl": "Zwart",
        "it": "Nero",
    },
    "Brąz": {
        "en": "Brown",
        "de": "Braun",
        "fr": "Marron",
        "es": "Marrón",
        "nl": "Bruin",
        "it": "Marrone",
    },
    "Jasny Brąz": {
        "en": "Light brown",
        "de": "Hellbraun",
        "fr": "Marron clair",
        "es": "Marrón claro",
        "nl": "Lichtbruin",
        "it": "Marrone chiaro",
    },
    "Ciemny Brąz": {
        "en": "Dark brown",
        "de": "Dunkelbraun",
        "fr": "Marron foncé",
        "es": "Marrón oscuro",
        "nl": "Donkerbruin",
        "it": "Marrone scuro",
    },
    "Biały": {
        "en": "White",
        "de": "Weiß",
        "fr": "Blanc",
        "es": "Blanco",
        "nl": "Wit",
        "it": "Bianco",
    },
    "Złoty": {
        "en": "Gold",
        "de": "Gold",
        "fr": "Or",
        "es": "Oro",
        "nl": "Goud",
        "it": "Oro",
    },
    "Srebrny": {
        "en": "Silver",
        "de": "Silber",
        "fr": "Argent",
        "es": "Plata",
        "nl": "Zilver",
        "it": "Argento",
    },
    "Szary": {
        "en": "Gray",
        "de": "Grau",
        "fr": "Gris",
        "es": "Gris",
        "nl": "Grijs",
        "it": "Grigio",
    },
    # --- RODZAJ DREWNA ---
    "Sosna": {
        "en": "Pine",
        "de": "Kiefer",
        "fr": "Pin",
        "es": "Pino",
        "nl": "Grenen",
        "it": "Pino",
    },
    "Dąb": {
        "en": "Oak",
        "de": "Eiche",
        "fr": "Chêne",
        "es": "Roble",
        "nl": "Eiken",
        "it": "Rovere",
    },
    "Buk": {
        "en": "Beech",
        "de": "Buche",
        "fr": "Hêtre",
        "es": "Haya",
        "nl": "Beuken",
        "it": "Faggio",
    },
    "Jesion": {
        "en": "Ash",
        "de": "Esche",
        "fr": "Frêne",
        "es": "Fresno",
        "nl": "Es",
        "it": "Frassino",
    },
    "Orzech": {
        "en": "Walnut",
        "de": "Nussbaum",
        "fr": "Noyer",
        "es": "Nogal",
        "nl": "Notenhout",
        "it": "Noce",
    },
}


# Wartosci ktore zostaja IDENTYCZNE we wszystkich jezykach (rozmiary literowe i
# wymiary "AxB" - traktowane jako pseudo-tlumaczenie 1:1, zeby Shopify mial
# zarejestrowany wpis tlumaczenia, nie zostawial pola pustego).
_AS_IS_LITERAL_SIZES: frozenset[str] = frozenset({"XS", "S", "M", "L", "XL", "XXL", "XXXL"})


def _is_dimensional_size(value: str) -> bool:
    """Zwraca True jesli wartosc wyglada jak '50x70', '70 x 100', '30X40 cm', itp."""
    s = (value or "").strip().lower().replace(" ", "")
    if not s:
        return False
    parts = s.replace("cm", "").split("x")
    if len(parts) != 2:
        return False
    try:
        int("".join(c for c in parts[0] if c.isdigit()))
        int("".join(c for c in parts[1] if c.isdigit()))
    except ValueError:
        return False
    return True


def _is_pass_through(value: str) -> bool:
    """Wartosci ktore w kazdym jezyku brzmia tak samo (rozmiar S/L/XL, '50x70')."""
    s = (value or "").strip()
    if not s:
        return False
    return s.upper() in _AS_IS_LITERAL_SIZES or _is_dimensional_size(s)


def translate_option_name(name_pl: str, lang: str) -> str | None:
    """Zwraca tlumaczenie nazwy opcji (np. 'Kolor' -> 'Couleur') albo None jesli brak.

    None -> caller MUSI pominac to pole (Shopify zostawi polski oryginal).
    """
    if not name_pl or lang not in SUPPORTED_LANGS:
        return None
    block = OPTION_NAME_TRANSLATIONS.get(name_pl.strip())
    if not block:
        return None
    val = (block.get(lang) or "").strip()
    return val or None


def translate_option_value(value_pl: str, lang: str) -> str | None:
    """Zwraca tlumaczenie wartosci opcji (np. 'Czarny' -> 'Noir') albo None.

    Dla 'pass-through' (S/L/XL, '50x70') zwraca te sama wartosc - dzieki temu
    Shopify dostaje wpis tlumaczenia (a nie pusty backstop)."""
    if not value_pl or lang not in SUPPORTED_LANGS:
        return None
    s = value_pl.strip()
    if _is_pass_through(s):
        return s
    block = OPTION_VALUE_TRANSLATIONS.get(s)
    if not block:
        return None
    val = (block.get(lang) or "").strip()
    return val or None


def find_missing_option_translations(
    option_names: list[str],
    option_values: list[str],
) -> dict[str, list[str]]:
    """Zwraca dict {lang: [missing_polish_strings...]} dla nazw/wartosci, ktorych
    nie ma w slownikach (do logowania ostrzezen i poszerzania slownika)."""
    out: dict[str, list[str]] = {lang: [] for lang in SUPPORTED_LANGS}
    for lang in SUPPORTED_LANGS:
        for n in option_names or []:
            if translate_option_name(n, lang) is None:
                out[lang].append(f"option:{n}")
        for v in option_values or []:
            if translate_option_value(v, lang) is None:
                out[lang].append(f"value:{v}")
    return {k: sorted(set(v)) for k, v in out.items() if v}
