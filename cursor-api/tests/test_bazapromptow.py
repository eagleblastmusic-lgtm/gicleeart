"""Testy Bazy Promptow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_prompt_store_roundtrip(tmp_path, monkeypatch) -> None:
    from Komponenty.bazapromptow import storage as st

    data_file = tmp_path / "prompts.json"
    monkeypatch.setattr(st, "PROMPTS_FILE", data_file)
    monkeypatch.setattr(st, "DATA_DIR", tmp_path)

    store = st.PromptStore(
        prompts=[
            st.PromptEntry(id="a1", label="Test A", text="Prompt A", sort_key=0),
            st.PromptEntry(id="b2", label="Test B", text="Prompt B", sort_key=1),
        ],
    )
    st.save_prompts(store)
    loaded = st.load_prompts()
    assert len(loaded.prompts) == 2
    assert loaded.sorted()[0].label == "Test A"
    assert loaded.sorted()[1].text == "Prompt B"


def test_apply_prompt_placeholders() -> None:
    from Komponenty.bazapromptow.catalog import apply_prompt_placeholders

    text = "Autor: [autor]\nTytul: [tytuł]\nART: [AUTOR] / [tytul]"
    out = apply_prompt_placeholders(
        text,
        artist="Claude Monet",
        title="Impresja, wschod slonca",
    )
    assert "Claude Monet" in out
    assert "Impresja, wschod slonca" in out
    assert "[autor]" not in out
    assert "[tytuł]" not in out


def test_unique_artists_and_paintings() -> None:
    from Komponenty.bazapromptow.catalog import (
        paintings_for_artist,
        unique_artists,
    )

    rows = [
        {"artist": "Monet", "painting_title": "B", "artist_sort_index": 1, "surname": "Monet"},
        {"artist": "Monet", "painting_title": "A", "artist_sort_index": 1, "surname": "Monet"},
        {"artist": "Renoir", "painting_title": "X", "artist_sort_index": 0, "surname": "Renoir"},
    ]
    assert unique_artists(rows) == ["Renoir", "Monet"]
    assert [r["painting_title"] for r in paintings_for_artist(rows, "Monet")] == ["A", "B"]


def test_prompt_store_empty_file(tmp_path, monkeypatch) -> None:
    from Komponenty.bazapromptow import storage as st

    data_file = tmp_path / "prompts.json"
    monkeypatch.setattr(st, "PROMPTS_FILE", data_file)
    monkeypatch.setattr(st, "DATA_DIR", tmp_path)

    assert st.load_prompts().prompts == []

    data_file.write_text(json.dumps({"version": 1, "prompts": []}), encoding="utf-8")
    assert st.load_prompts().prompts == []
