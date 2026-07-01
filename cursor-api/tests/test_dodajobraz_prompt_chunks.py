"""Testy dzielenia promptu batch na czesci po 4 obrazy."""

from __future__ import annotations

from Komponenty.dodajobraz.prompt_builder import (
    PROMPT_CHUNK_SIZE,
    build_all_prompt_chunks,
    chunk_prompt_items,
    format_merged_json,
    merge_json_part_lists,
)


def _fake_items(n: int) -> list[dict]:
    return [
        {
            "filename": f"Artysta - Obraz {i}.webp",
            "artist": "Artysta",
            "title": f"Obraz {i}",
            "title_is_polish": True,
        }
        for i in range(1, n + 1)
    ]


def test_chunk_prompt_items_splits_by_four() -> None:
    parts = chunk_prompt_items(_fake_items(10), chunk_size=4)
    assert len(parts) == 3
    assert [len(p) for p in parts] == [4, 4, 2]


def test_build_all_prompt_chunks_count() -> None:
    chunks = build_all_prompt_chunks(_fake_items(9), model="opus")
    assert len(chunks) == 3
    assert chunks[0][0] == 1 and chunks[-1][1] == 3


def test_chunk_prompt_includes_preamble() -> None:
    chunks = build_all_prompt_chunks(_fake_items(6), model="opus")
    assert len(chunks) == 2
    assert "CZESC 1 Z 2" in chunks[0][2]
    assert "CZESC 2 Z 2" in chunks[1][2]
    assert "DOKLADNIE 4 obiektami" in chunks[0][2]
    assert "DOKLADNIE 2 obiektami" in chunks[1][2]


def test_single_chunk_no_preamble() -> None:
    chunks = build_all_prompt_chunks(_fake_items(PROMPT_CHUNK_SIZE), model="opus")
    assert len(chunks) == 1
    assert "CZESC 1 Z" not in chunks[0][2]


def test_merge_json_part_lists_order() -> None:
    parts = {
        2: [{"filename": "b.webp"}],
        1: [{"filename": "a.webp"}],
        3: [{"filename": "c.webp"}],
    }
    merged = merge_json_part_lists(parts, total_parts=3)
    assert [x["filename"] for x in merged] == ["a.webp", "b.webp", "c.webp"]


def test_merge_json_part_lists_partial() -> None:
    merged = merge_json_part_lists({1: [{"n": 1}]}, total_parts=3)
    assert len(merged) == 1


def test_format_merged_json_is_array() -> None:
    text = format_merged_json([{"x": 1}])
    assert text.strip().startswith("[")
