"""Testy modulu roboczych opisow (tytulyai/descriptions)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_format_draft_display() -> None:
    from Komponenty.tytulyai.descriptions import format_draft_display

    text = format_draft_display(["Akapit 1.", "Akapit 2.", "Akapit 3."])
    assert text == "Akapit 1.\n\nAkapit 2.\n\nAkapit 3."


def test_format_akapity_compare_json_roundtrip() -> None:
    from Komponenty.dodajobraz.description_update import parse_full_akapity_json
    from Komponenty.tytulyai.descriptions import format_akapity_compare_json

    akapity = ["Pierwszy akapit.", "Drugi akapit.", "Trzeci akapit."]
    raw = format_akapity_compare_json(akapity)
    assert parse_full_akapity_json(raw) == akapity
    assert '"akapity"' in raw


def test_format_akapity_compare_json_requires_three() -> None:
    from Komponenty.tytulyai.descriptions import format_akapity_compare_json
    import pytest

    with pytest.raises(ValueError, match="Minimum 3"):
        format_akapity_compare_json(["Jeden", "Dwa"])


def test_process_description_row_missing_artist() -> None:
    from Komponenty.tytulyai.descriptions import process_description_row

    result = process_description_row(
        {"product_id": 1, "painting_title": "Test"},
        model="gemini-2.5-flash",
    )
    assert result.v1.error
    assert result.v2.error
    assert "artysty" in result.v1.error.lower()


def test_process_description_row_generates_v1_and_v2(monkeypatch) -> None:
    from Komponenty.tytulyai import descriptions as mod

    prompts: list[str] = []

    def fake_generate(**kwargs):
        prompts.append(kwargs["prompt"])
        if "naturalnie" in kwargs["prompt"] or "bez sztywnej" in kwargs["prompt"]:
            return ('{"akapity": ["V2-1", "V2-2", "V2-3"]}', "gemini-test")
        return ('{"akapity": ["V1-1", "V1-2", "V1-3"]}', "gemini-test")

    monkeypatch.setattr(mod, "generate_from_image_bytes", fake_generate)

    row = {
        "product_id": 42,
        "artist": "Canaletto",
        "painting_title": "Widok na Canal Grande",
        "image_src": "https://cdn.shopify.com/x.jpg",
    }
    result = mod.process_description_row(
        row,
        model="gemini-test",
        image_bytes=b"fake",
        mime_type="image/jpeg",
    )
    assert result.v1.ok
    assert result.v2.ok
    assert result.v1.akapity[0] == "V1-1"
    assert result.v2.akapity[0] == "V2-1"
    assert len(prompts) == 2
    assert "Canaletto" in prompts[0]
    assert "ANALIZĘ WIZUALNĄ" in prompts[0]
    assert "naturalnie" in prompts[1].lower() or "bez sztywnej" in prompts[1].lower()


def test_merge_description_drafts_keeps_ok_variants() -> None:
    from Komponenty.tytulyai.descriptions import (
        DescriptionVariant,
        ProductDescriptionDrafts,
        merge_description_drafts,
    )

    existing = ProductDescriptionDrafts(
        product_id=7,
        artist="Monet",
        painting_title="Lilie",
        v1=DescriptionVariant(
            akapity=["Stary v1"],
            model_used="gemini-old",
            generated_at="2026-01-01",
        ),
        v2=DescriptionVariant(error="Blad polaczenia z Gemini (timeout/siec)."),
    )
    new = ProductDescriptionDrafts(
        product_id=7,
        artist="Monet",
        painting_title="Lilie",
        v1=DescriptionVariant(akapity=["Nowy v1"], model_used="gemini-new"),
        v2=DescriptionVariant(akapity=["Nowy v2"], model_used="gemini-new"),
    )
    merged = merge_description_drafts(existing, new)
    assert merged.v1.akapity == ["Stary v1"]
    assert merged.v1.model_used == "gemini-old"
    assert merged.v2.akapity == ["Nowy v2"]


def test_process_description_row_skips_ok_existing_variant(monkeypatch) -> None:
    from Komponenty.tytulyai import descriptions as mod
    from Komponenty.tytulyai.descriptions import DescriptionVariant, ProductDescriptionDrafts

    calls: list[str] = []

    def fake_generate(**kwargs):
        calls.append(kwargs["prompt"])
        return ('{"akapity": ["V2-1", "V2-2", "V2-3"]}', "gemini-test")

    monkeypatch.setattr(mod, "generate_from_image_bytes", fake_generate)

    existing = ProductDescriptionDrafts(
        product_id=99,
        artist="Canaletto",
        painting_title="Canal Grande",
        v1=DescriptionVariant(akapity=["Zachowany v1"], model_used="gemini-old"),
        v2=DescriptionVariant(error="Blad generowania"),
    )
    row = {
        "product_id": 99,
        "artist": "Canaletto",
        "painting_title": "Canal Grande",
    }
    result = mod.process_description_row(
        row,
        model="gemini-test",
        image_bytes=b"fake",
        mime_type="image/jpeg",
        existing=existing,
    )
    assert len(calls) == 1
    assert result.v1.akapity == ["Zachowany v1"]
    assert result.v2.akapity == ["V2-1", "V2-2", "V2-3"]
