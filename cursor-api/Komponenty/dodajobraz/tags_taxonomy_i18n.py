"""Wielojezyczne ekwiwalenty SEO dla 6 jezykow obcych: EN, DE, FR, ES, NL, IT.

Kazdy slownik zawiera:
  * always_tags        - stale frazy SEO obowiazkowo na produkcie w tym jezyku
                         (analog ALWAYS_TAGS z tags_taxonomy.py),
  * gift_phrases       - okazje prezentowe,
  * style_phrases      - style wnetrz (przymiotnik w formie odpowiedniej dla jezyka),
  * room_phrases       - pomieszczenia.

UWAGA: te tagi sa dorzucane do tagow produktu (`tags`) w Shopify - sa wspolne dla
calego sklepu (nie sa per-market). Dzieki temu produkt znajduje sie po slowach
'wall art' (EN), 'Wandbild' (DE), 'tableau mural' (FR), 'cuadros decorativos' (ES),
'schilderij voor aan de muur' (NL), 'quadri da parete' (IT) niezaleznie od tego,
ktory market ogladajacy klient ma wlaczony.

Tagi NIE sa tlumaczone osobno per market przez Shopify Translations API
- po prostu siedzi pelen pakiet wielojezyczny w polu `tags` produktu.

Klucze: ISO 639-1 lower-case (en, de, fr, es, nl, it).
"""
from __future__ import annotations

LANG_CODES: tuple[str, ...] = ("en", "de", "fr", "es", "nl", "it")


# ---------------------------------------------------------------------------
# ZAWSZE-tagi (stale fraze brandingowe + zakupowe SEO per jezyk)
# Bazuja na badaniu top fraz w PL e-commerce art (galerie reprodukcji),
# konwertowane na ekwiwalenty rynkowe.
# ---------------------------------------------------------------------------

ALWAYS_TAGS_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "gicleeart", "giclee", "art",
        "wall art", "canvas wall art", "fine art reproduction",
        "giclee print", "canvas print",
        "home decor", "wall decoration", "living room art", "bedroom art",
        "anniversary gift", "wedding gift", "housewarming gift", "birthday gift",
        "gift idea", "gift for her", "gift for him",
    ),
    "de": (
        "gicleeart", "giclee", "art",
        "wandbild", "leinwandbild", "wandkunst",
        "kunstdruck", "giclee druck", "fine art print",
        "wohnaccessoires", "wandgestaltung", "wohnzimmer kunst", "schlafzimmer kunst",
        "geschenk zum jahrestag", "hochzeitsgeschenk", "einweihungsgeschenk", "geburtstagsgeschenk",
        "geschenkidee", "geschenk f\u00fcr sie", "geschenk f\u00fcr ihn",
    ),
    "fr": (
        "gicleeart", "giclee", "art",
        "tableau mural", "toile murale", "art mural",
        "reproduction d'art", "tirage giclee", "impression giclee",
        "decoration murale", "decoration interieure", "art salon", "art chambre",
        "cadeau anniversaire de mariage", "cadeau de mariage", "cadeau de pendaison de cremaillere",
        "cadeau d'anniversaire", "idee cadeau", "cadeau pour elle", "cadeau pour lui",
    ),
    "es": (
        "gicleeart", "giclee", "art",
        "cuadros decorativos", "cuadro pared", "arte mural",
        "reproduccion de arte", "impresion giclee",
        "decoracion hogar", "decoracion pared", "cuadros para salon", "cuadros para dormitorio",
        "regalo aniversario", "regalo boda", "regalo inauguracion casa", "regalo cumpleanos",
        "idea regalo", "regalo para ella", "regalo para el",
    ),
    "nl": (
        "gicleeart", "giclee", "art",
        "schilderij", "wanddecoratie", "muurkunst",
        "kunstreproductie", "giclee print", "canvasprint",
        "interieurdecoratie", "muur decoratie", "schilderij woonkamer", "schilderij slaapkamer",
        "huwelijks jubileum cadeau", "huwelijkscadeau", "housewarming cadeau", "verjaardagscadeau",
        "cadeau idee", "cadeau voor haar", "cadeau voor hem",
    ),
    "it": (
        "gicleeart", "giclee", "art",
        "quadri da parete", "stampa su tela", "arte murale",
        "riproduzione d'arte", "stampa giclee",
        "decorazione casa", "decorazione muro", "quadri soggiorno", "quadri camera da letto",
        "regalo anniversario", "regalo matrimonio", "regalo casa nuova", "regalo compleanno",
        "idea regalo", "regalo per lei", "regalo per lui",
    ),
}


# ---------------------------------------------------------------------------
# Locale -> waga w Shopify Translations API (uzywane przy translationsRegister)
# ---------------------------------------------------------------------------

LOCALE_DISPLAY: dict[str, str] = {
    "en": "English",
    "de": "Deutsch",
    "fr": "Fran\u00e7ais",
    "es": "Espa\u00f1ol",
    "nl": "Nederlands",
    "it": "Italiano",
}


def all_foreign_tags() -> list[str]:
    """Zwraca jednolita liste wszystkich obcojezycznych tagow (deduplikacja case-insensitive).

    Uzywana w `ensure_required_tags()` zeby kazdy produkt mial juz w polu `tags`
    pelen miks PL+EN+DE+FR+ES+NL+IT - dzieki czemu klient kazdego rynku
    znajduje produkt po wlasnych slowach kluczowych.
    """
    seen: set[str] = set()
    out: list[str] = []
    for lang in LANG_CODES:
        for t in ALWAYS_TAGS_BY_LANG.get(lang, ()):
            key = (t or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(t)
    return out


def tags_for_language(lang: str) -> tuple[str, ...]:
    """Zwraca always_tags dla wybranego jezyka (lowercase code: en/de/fr/es/nl/it)."""
    return ALWAYS_TAGS_BY_LANG.get((lang or "").strip().lower(), ())
