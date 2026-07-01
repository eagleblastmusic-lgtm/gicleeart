"""Integracja: caly JSON czesci 1/4 Thomas Cole z transkryptu."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.dodajobraz.prompt_builder import _loads_json_array_blob, parse_batch_response_json

_FIXTURE = Path(__file__).parent / "fixtures" / "cole_part1_clean.json"


@pytest.mark.skipif(not _FIXTURE.is_file(), reason="brak fixture cole_part1_clean.json")
def test_cole_part1_clean_fixture_parses() -> None:
    blob = _FIXTURE.read_text(encoding="utf-8")
    data = _loads_json_array_blob(blob)
    assert len(data) == 4
    pliki = {item["plik"] for item in data}
    assert any("Mohicans" in p for p in pliki)
    validated = parse_batch_response_json(blob)
    assert len(validated) == len(data)


@pytest.mark.skipif(not _FIXTURE.is_file(), reason="brak fixture")
def test_cole_part1_raw_json_has_no_unescaped_inner_quotes_after_repair() -> None:
    from Komponenty.dodajobraz.prompt_builder import (
        _fix_polish_open_close_quote_pairs,
        _sanitize_control_chars_in_strings,
        _sanitize_inner_quotes,
        _sanitize_polish_ascii_quotes,
        _strip_json_trailing_commas,
    )

    blob = _FIXTURE.read_text(encoding="utf-8")
    cand = _sanitize_inner_quotes(
        _sanitize_polish_ascii_quotes(
            _sanitize_control_chars_in_strings(
                _strip_json_trailing_commas(_fix_polish_open_close_quote_pairs(blob))
            )
        )
    )
    json.loads(cand)  # nie powinno rzucac
