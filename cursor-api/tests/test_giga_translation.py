"""Testy GIGA tlumaczenia w «Aktualizuj opis»."""

from Komponenty.dodajobraz.description_update import (
    build_giga_translation_prompt,
    build_locales_from_translation_batch,
    parse_giga_translations_json,
)


def test_build_giga_translation_prompt_lists_products() -> None:
    prompt = build_giga_translation_prompt(
        [
            {
                "artist": "Monet",
                "title": "Water Lilies",
                "paragraphs": ["Akapit jeden.", "Akapit dwa.", "Akapit trzy."],
            },
            {
                "artist": "Renoir",
                "title": "Bal",
                "paragraphs": ["Pierwszy.", "Drugi.", "Trzeci."],
            },
        ]
    )
    assert "PRODUKT 1" in prompt
    assert "PRODUKT 2" in prompt
    assert "produkt_1" in prompt
    assert "produkt_2" in prompt
    assert "Monet" in prompt
    assert "Renoir" in prompt


def test_parse_giga_translations_json_roundtrip_shape() -> None:
    raw = """{
      "produkt_1": {
        "akapit_1": {"en":"a1","de":"a1","fr":"a1","es":"a1","nl":"a1","it":"a1"},
        "akapit_2": {"en":"a2","de":"a2","fr":"a2","es":"a2","nl":"a2","it":"a2"}
      },
      "produkt_2": {
        "akapit_1": {"en":"b1","de":"b1","fr":"b1","es":"b1","nl":"b1","it":"b1"}
      }
    }"""
    parsed = parse_giga_translations_json(raw)
    assert parsed[1][0]["en"] == "a1"
    assert parsed[1][1]["de"] == "a2"
    assert parsed[2][0]["it"] == "b1"


def test_build_locales_from_translation_batch_merges_foreign() -> None:
    baseline = {
        "pl": ["pl1", "pl2", "pl3"],
        "en": ["old en1", "old en2", "old en3"],
        "de": ["", "", ""],
    }
    batch = [
        {"en": "en1", "de": "de1", "fr": "fr1", "es": "es1", "nl": "nl1", "it": "it1"},
        {"en": "en2", "de": "de2", "fr": "fr2", "es": "es2", "nl": "nl2", "it": "it2"},
    ]
    out = build_locales_from_translation_batch(
        baseline_by_locale=baseline,
        translation_batch=batch,
    )
    assert "pl" not in out
    assert out["en"][:2] == ["en1", "en2"]
    assert out["de"][:2] == ["de1", "de2"]
