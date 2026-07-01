"""Testy naprawy JSON z odpowiedzi LLM."""

from __future__ import annotations

import json

from Komponenty.dodajobraz.prompt_builder import (
    _fix_polish_open_close_quote_pairs,
    _loads_json_array_blob,
    _sanitize_control_chars_in_strings,
    _strip_json_trailing_commas,
)


def test_trailing_comma_in_array() -> None:
    blob = """[
  {
    "plik": "a.webp",
    "tytul_polski": "Tytul",
    "tytul_orginalny": "Title",
    "akapity": ["jeden", "dwa",],
    "data_powstania": "1866",
    "miejsce_powstania": "Paryz",
    "technika": "Olej",
    "gatunek": "Akt",
    "nurt": "Realizm",
    "forma": "Malarstwo",
    "tagi": ["a"],
    "kategoria": "Obrazy"
  }
]"""
    data = _loads_json_array_blob(blob)
    assert data[0]["plik"] == "a.webp"
    assert data[0]["akapity"] == ["jeden", "dwa"]


def test_unescaped_newline_in_string() -> None:
    raw = '[{"a": "linia1\nlinia2"}]'
    fixed = _sanitize_control_chars_in_strings(raw)
    parsed = json.loads(fixed)
    assert parsed[0]["a"] == "linia1\nlinia2"


def test_polish_open_close_in_string() -> None:
    raw = '[{"akapity": ["„L\'Allegro" to wizja", "drugi „Il Penseroso" koniec"]}]'
    data = _loads_json_array_blob(raw)
    assert "L'Allegro" in data[0]["akapity"][0]
    assert "Il Penseroso" in data[0]["akapity"][1]


def test_polish_quote_in_akapit_before_array_close() -> None:
    raw = (
        '[{"akapity": ["Roman „Der letzte Mohikaner\\" (1826). Koniec."]}]'
    )
    data = _loads_json_array_blob(raw)
    assert "Mohikaner" in data[0]["akapity"][0]


def test_german_title_escaped_quote_not_structural_break() -> None:
    raw = (
        '[{"tlumaczenia": {"de": {"tytul_polski": '
        '"Szene aus „Der letzte Mohikaner\\": Cora kniet zu Füßen Tamenunds", '
        '"akapity": ["x"]}}}]'
    )
    data = _loads_json_array_blob(raw)
    assert "Mohikaner" in data[0]["tlumaczenia"]["de"]["tytul_polski"]


def test_plik_and_akapity_inner_quotes_combo() -> None:
    """Typowy batch Thomas Cole: cudzyslowy w nazwie pliku + polskie „..." w tekscie."""
    raw = (
        '[{"plik": "Thomas Cole - Scene from "the Last of the Mohicans," Cora.webp", '
        '"tytul_polski": "Scena z „Ostatniego Mohikanina" – Cora", '
        '"akapity": ["„L\'Allegro" to wizja natury"]}]'
    )
    data = _loads_json_array_blob(raw)
    assert "Mohicans" in data[0]["plik"]
    assert "Mohikanina" in data[0]["tytul_polski"]
    assert "L'Allegro" in data[0]["akapity"][0]


def test_tytul_with_polish_quotes() -> None:
    raw = (
        '[{"plik": "a.webp", "tytul_polski": "Scena z „Ostatniego Mohikanina" – Cora", '
        '"tytul_orginalny": "T", "akapity": ["a", "b", "c"], "data_powstania": "1827", '
        '"miejsce_powstania": "USA", "technika": "Olej", "gatunek": "Akt", '
        '"nurt": "Realizm", "forma": "Malarstwo", "tagi": ["x"], "kategoria": "Obrazy"}]'
    )
    data = _loads_json_array_blob(raw)
    assert "Mohikanina" in data[0]["tytul_polski"]


def test_strip_trailing_commas_only_outside_strings() -> None:
    raw = '{"tags": ["a", "b",], "ok": true}'
    fixed = _strip_json_trailing_commas(raw)
    assert ",]" not in fixed
    assert '",]' not in fixed.replace(" ", "")
