"""Test promptu «Prompt do nowego opisu» — tytul EN + oryginalny."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_build_new_description_prompt_en_and_original() -> None:
    from Komponenty.dodajobraz.prompt_builder import build_new_description_prompt

    prompt = build_new_description_prompt(
        artist="Gesina ter Borch",
        title_pl="Portret",
        title_en="Portrait of Moses ter Borch",
        title_original="Portret van Moses ter Borch",
    )
    assert "tytul (angielski): Portrait of Moses ter Borch" in prompt
    assert "tytul oryginalny (jezyk artysty): Portret van Moses ter Borch" in prompt
    assert "tytul (polski, w sklepie): Portret" in prompt
    assert "identyfikuj KONKRETNE dzielo" in prompt


def test_build_new_description_prompt_skips_unknown_original() -> None:
    from Komponenty.dodajobraz.prompt_builder import build_new_description_prompt

    prompt = build_new_description_prompt(
        artist="John Waterhouse",
        title_pl="Portret",
        title_en="Portrait",
        title_original="nieznana",
    )
    assert "tytul oryginalny" not in prompt
    assert "tytul (angielski): Portrait" in prompt


def test_build_image_description_prompt() -> None:
    from Komponenty.dodajobraz.prompt_builder import build_image_description_prompt

    prompt = build_image_description_prompt(
        artist="Canaletto",
        title="Widok na Canal Grande",
    )
    assert "Artysta: Canaletto" in prompt
    assert "Tytuł: Widok na Canal Grande" in prompt
    assert "ANALIZĘ WIZUALNĄ" in prompt
    assert '"akapity"' in prompt


def test_build_image_description_prompt_v2() -> None:
    from Komponenty.dodajobraz.prompt_builder import build_image_description_prompt_v2

    prompt = build_image_description_prompt_v2(
        artist="Canaletto",
        title="Widok na Canal Grande",
    )
    assert "Artysta: Canaletto" in prompt
    assert "Tytuł: Widok na Canal Grande" in prompt
    assert "naturalnie, świeżo i interesująco" in prompt
    assert "Nie narzucaj sztywnej struktury" in prompt
    assert "sztywnej struktury ani schematu" in prompt
