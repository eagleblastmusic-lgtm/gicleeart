"""Testy promptu zmiany tytulow produktu."""
from Komponenty.dodajobraz.description_update import (
    build_title_change_prompt,
    drop_article_only_alternatives,
    format_title_alternative_parenthetical,
    parse_title_change_fields,
    parse_title_change_product_ref,
)


def test_parse_product_ref() -> None:
    title, artist = parse_title_change_product_ref(
        "Miejska przystań latem (lub Port miejski latem)\nSalomon Verveer"
    )
    assert title == "Miejska przystań latem (lub Port miejski latem)"
    assert artist == "Salomon Verveer"


def test_parse_fields_without_newlines() -> None:
    raw = (
        "Tytuł angielski: Town dock in summer"
        "Tytuł polski: Miejska przystań latem lub Port miejski latem"
        "Tytuł oryginalny (niderlandzki): Stadshaven in de zomer"
    )
    fields = parse_title_change_fields(raw)
    assert fields["en"] == "Town dock in summer"
    assert fields["pl"] == "Miejska przystań latem lub Port miejski latem"
    assert fields["orig"] == "Stadshaven in de zomer"


def test_build_prompt() -> None:
    prompt = build_title_change_prompt(
        painting_title="Miejska przystań latem (lub Port miejski latem)",
        artist="Salomon Verveer",
        titles={
            "en": "Town dock in summer",
            "pl": "Miejska przystań latem lub Port miejski latem",
            "orig": "Stadshaven in de zomer",
        },
    )
    assert "W produkcie:" in prompt
    assert "Salomon Verveer" in prompt
    assert "Tytuł angielski: Town dock in summer" in prompt
    assert "Tytuł polski: Miejska przystań latem (lub Port miejski latem)" in prompt
    assert "Tytuł oryginalny: Stadshaven in de zomer" in prompt


def test_parse_single_field() -> None:
    fields = parse_title_change_fields("Tytuł polski: Kwitnące drzewo brzoskwiniowe")
    assert fields == {"pl": "Kwitnące drzewo brzoskwiniowe"}


def test_build_prompt_partial() -> None:
    prompt = build_title_change_prompt(
        painting_title="Kwitnąca brzoskwinia",
        artist="Vincent Van Gogh",
        titles={"orig": "Bloeiende perzikboom"},
    )
    assert "Tytuł oryginalny: Bloeiende perzikboom" in prompt
    assert "Tytuł angielski:" not in prompt
    assert "Tytuł polski:" not in prompt


def test_parse_multilang_block_without_newlines() -> None:
    raw = (
        "Tytuł oryginalny / niderlandzki (NL): Romeinse liefde lub Cimon en Pero"
        "Tytuł polski: Karitas rzymska lub Cimon i Pero"
        "Tytuł angielski: Roman Charity lub Cimon and Pero"
        "Tytuły w pozostałych językach:"
        "Tytuł niemiecki (DE): Römische Caritas lub Cimon und Pero"
        "Tytuł francuski (FR): La Charité romaine lub Cimon et Péro"
        "Tytuł hiszpański (ES): Caridad romana lub Cimón y Pero"
        "Tytuł włoski (IT): Carità Romana lub Cimone e Pero"
    )
    fields = parse_title_change_fields(raw)
    assert fields["orig"] == "Romeinse liefde lub Cimon en Pero"
    assert fields["pl"] == "Karitas rzymska lub Cimon i Pero"
    assert fields["en"] == "Roman Charity lub Cimon and Pero"
    assert fields["de"] == "Römische Caritas lub Cimon und Pero"
    assert fields["fr"] == "La Charité romaine lub Cimon et Péro"
    assert fields["es"] == "Caridad romana lub Cimón y Pero"
    assert fields["it"] == "Carità Romana lub Cimone e Pero"


def test_build_prompt_multilang_block() -> None:
    prompt = build_title_change_prompt(
        painting_title="Karitas rzymska lub Cimon i Pero",
        artist="Peter Paul Rubens",
        titles=parse_title_change_fields(
            "Tytuł oryginalny / niderlandzki (NL): Romeinse liefde lub Cimon en Pero"
            "Tytuł polski: Karitas rzymska lub Cimon i Pero"
            "Tytuł angielski: Roman Charity lub Cimon and Pero"
            "Tytuły w pozostałych językach:"
            "Tytuł niemiecki (DE): Römische Caritas lub Cimon und Pero"
            "Tytuł włoski (IT): Carità Romana lub Cimone e Pero"
        ),
    )
    assert "Tytuł oryginalny: Romeinse liefde (of Cimon en Pero)" in prompt
    assert "Tytuł polski: Karitas rzymska (lub Cimon i Pero)" in prompt
    assert "Tytuł angielski: Roman Charity (or Cimon and Pero)" in prompt
    assert "Tytuły w pozostałych językach:" in prompt
    assert "Tytuł niemiecki (DE): Römische Caritas (oder Cimon und Pero)" in prompt
    assert "Tytuł włoski (IT): Carità Romana (o Cimone e Pero)" in prompt
    assert "Roman Charity lub Cimon and PeroTytuły" not in prompt


def test_format_title_alternative_parenthetical() -> None:
    assert (
        format_title_alternative_parenthetical("Roman Charity lub Cimon and Pero", "en")
        == "Roman Charity (or Cimon and Pero)"
    )
    assert (
        format_title_alternative_parenthetical("Karitas rzymska lub Cimon i Pero", "pl")
        == "Karitas rzymska (lub Cimon i Pero)"
    )
    assert (
        format_title_alternative_parenthetical("Romeinse liefde lub Cimon en Pero", "orig")
        == "Romeinse liefde (of Cimon en Pero)"
    )
    assert format_title_alternative_parenthetical("Bez alternatywy", "en") == "Bez alternatywy"
    assert (
        format_title_alternative_parenthetical(
            "Kwitnące drzewo brzoskwiniowe (lub Kwitnące drzewo migdałowe lub Drzewo brzoskwiniowe w rozkwicie)",
            "pl",
        )
        == "Kwitnące drzewo brzoskwiniowe (lub Kwitnące drzewo migdałowe/Drzewo brzoskwiniowe w rozkwicie)"
    )
    assert (
        format_title_alternative_parenthetical(
            "Żona rybaka na plaży lub Żona rybaka lub Rybaczka na plaży",
            "pl",
        )
        == "Żona rybaka na plaży (lub Żona rybaka/Rybaczka na plaży)"
    )


def test_drop_article_only_alternatives() -> None:
    assert (
        drop_article_only_alternatives(
            "The Massacre of the Innocents (or Massacre of the Innocents)",
            "en",
        )
        == "The Massacre of the Innocents"
    )
    assert (
        drop_article_only_alternatives(
            "Der Kindermord zu Bethlehem (oder Kindermord zu Bethlehem)",
            "de",
        )
        == "Der Kindermord zu Bethlehem"
    )
    assert (
        drop_article_only_alternatives(
            "The Hunters in the Snow (or Hunters in the Snow or Return of the Hunters)",
            "en",
        )
        == "The Hunters in the Snow (or Return of the Hunters)"
    )
    assert (
        drop_article_only_alternatives(
            "The Bull (or The Young Bull)",
            "en",
        )
        == "The Bull (or The Young Bull)"
    )


def test_build_prompt_strips_trailing_period() -> None:
    prompt = build_title_change_prompt(
        painting_title="Ogród szpitala w Saint-Rémy",
        artist="Vincent Van Gogh",
        titles={
            "en": "The Good Samaritan (after Delacroix).",
            "orig": "De tuin van de inrichting in Saint-Rémy.",
        },
    )
    assert "Tytuł angielski: The Good Samaritan (after Delacroix)" in prompt
    assert "after Delacroix)." not in prompt
    assert "Tytuł oryginalny: De tuin van de inrichting in Saint-Rémy" in prompt
    assert "Saint-Rémy." not in prompt.split("Zmień:\n", 1)[1]
