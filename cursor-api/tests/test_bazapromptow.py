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

    store = st.load_prompts()
    assert store.prompts == []
    assert any(f.id == st.DEFAULT_FOLDER_ID for f in store.folders)

    data_file.write_text(json.dumps({"version": 1, "prompts": []}), encoding="utf-8")
    loaded = st.load_prompts()
    assert loaded.prompts == []
    assert any(f.label == st.DEFAULT_FOLDER_LABEL for f in loaded.folders)


def test_prompt_context_images_roundtrip(tmp_path, monkeypatch) -> None:
    from Komponenty.bazapromptow import storage as st

    data_file = tmp_path / "prompts.json"
    monkeypatch.setattr(st, "PROMPTS_FILE", data_file)
    monkeypatch.setattr(st, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st, "CONTEXT_IMAGES_DIR", tmp_path / "context_images")

    store = st.PromptStore(
        prompts=[
            st.PromptEntry(
                id="p1",
                label="Img",
                text="t",
                context_images=["context_images/p1/sample.png"],
            ),
        ],
    )
    st.save_prompts(store)
    loaded = st.load_prompts()
    assert loaded.prompts[0].context_images == ["context_images/p1/sample.png"]

    src = tmp_path / "src.jpg"
    src.write_bytes(b"fake")
    rel = st.import_context_image("p1", src)
    assert (tmp_path / rel).is_file()
    st.sync_context_images(["context_images/p1/sample.png"], [rel])
    assert not (tmp_path / "context_images/p1/sample.png").exists()


def test_prompt_folders_and_move(tmp_path, monkeypatch) -> None:
    from Komponenty.bazapromptow import storage as st

    data_file = tmp_path / "prompts.json"
    monkeypatch.setattr(st, "PROMPTS_FILE", data_file)
    monkeypatch.setattr(st, "DATA_DIR", tmp_path)

    sub = st.FolderEntry(id="sub1", label="Hero", sort_key=0, parent_id=st.DEFAULT_FOLDER_ID)
    store = st.PromptStore(
        prompts=[
            st.PromptEntry(id="a1", label="A", text="t1", sort_key=0),
            st.PromptEntry(id="b2", label="B", text="t2", sort_key=1, folder_id="sub1"),
        ],
        folders=[st.default_folder(), sub],
    )
    st.save_prompts(store)
    loaded = st.load_prompts()
    assert loaded.count_in_view(st.FOLDER_ALL) == 2
    assert loaded.count_in_view(st.DEFAULT_FOLDER_ID) == 0
    assert loaded.count_in_view("sub1") == 1
    assert loaded.is_descendant_of("sub1", st.DEFAULT_FOLDER_ID)
    assert loaded.folder_path_label("sub1") == "Strona Główna / Hero"
    assert loaded.descendant_folder_ids(st.DEFAULT_FOLDER_ID) == {st.DEFAULT_FOLDER_ID, "sub1"}
