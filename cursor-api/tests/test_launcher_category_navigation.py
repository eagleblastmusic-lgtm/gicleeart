from __future__ import annotations

from giclee_app.category_launcher import (
    category_appearance,
    category_count_text,
    category_display_title,
    category_map,
)


def test_category_count_text_uses_polish_forms() -> None:
    assert category_count_text(0) == "0 komponentów"
    assert category_count_text(1) == "1 komponent"
    assert category_count_text(2) == "2 komponenty"
    assert category_count_text(4) == "4 komponenty"
    assert category_count_text(5) == "5 komponentów"
    assert category_count_text(12) == "12 komponentów"
    assert category_count_text(23) == "23 komponenty"


def test_known_category_has_presentation_metadata() -> None:
    appearance = category_appearance("Administracja produktu")
    assert appearance.icon
    assert appearance.description
    assert appearance.color.startswith("#")


def test_internal_section_title_can_have_polish_display_title() -> None:
    assert category_display_title("Zamowienia") == "Zamówienia"
    assert category_display_title("Narzedzia pomocnicze") == "Narzędzia pomocnicze"


def test_custom_category_uses_neutral_fallback() -> None:
    appearance = category_appearance("Moja kategoria")
    assert appearance.icon == "▦"
    assert category_display_title("Moja kategoria") == "Moja kategoria"


def test_category_map_preserves_sections_and_components() -> None:
    first = object()
    second = object()
    mapped = category_map([
        ("Pierwsza", [first]),
        ("Druga", [second]),
    ])
    assert list(mapped) == ["Pierwsza", "Druga"]
    assert mapped["Pierwsza"] == [first]
    assert mapped["Druga"] == [second]
