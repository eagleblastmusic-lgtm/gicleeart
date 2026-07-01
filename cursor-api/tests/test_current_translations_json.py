"""Testy eksportu JSON obecnych tlumaczen."""

import json

from Komponenty.dodajobraz.description_update import build_current_translations_json


def test_build_current_translations_json_all_locales() -> None:
    payload = build_current_translations_json(
        artist="Monet",
        title="Lilie",
        paragraphs_by_locale={
            "pl": ["pl1", "pl2", "pl3"],
            "en": ["en1", "en2", "en3"],
            "de": ["de1", "de2", "de3"],
            "fr": ["fr1", "fr2", "fr3"],
            "es": ["es1", "es2", "es3"],
            "nl": ["nl1", "nl2", "nl3"],
            "it": ["it1", "it2", "it3"],
        },
    )
    data = json.loads(payload)
    assert data["artysta"] == "Monet"
    assert data["tytul"] == "Lilie"
    assert data["wersja_pierwotna"] == "pl"
    assert "pierwotna" in data["uwaga"].lower()
    assert data["akapit_1"]["pl"] == "pl1"
    assert data["akapit_2"]["en"] == "en2"
    assert data["akapit_3"]["it"] == "it3"
