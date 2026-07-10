from __future__ import annotations

import json
from pathlib import Path

from Komponenty.notatnik.note_order import NoteOrderStore


def _files(folder: Path, *names: str) -> list[str]:
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_text(f"# {name}\n", encoding="utf-8")
    return list(names)


def test_missing_file_uses_alphabetical_fallback(tmp_path: Path) -> None:
    names = _files(tmp_path, "Zulu.md", "alfa.md", "Beta.md")
    store = NoteOrderStore(tmp_path)
    assert store.ordered_names(tmp_path, names) == ["alfa.md", "Beta.md", "Zulu.md"]


def test_move_persists_and_reloads(tmp_path: Path) -> None:
    names = _files(tmp_path, "A.md", "B.md", "C.md")
    store = NoteOrderStore(tmp_path)
    assert store.move(tmp_path, "B.md", -1, names)
    assert NoteOrderStore(tmp_path).ordered_names(tmp_path, names) == [
        "B.md",
        "A.md",
        "C.md",
    ]


def test_move_down_and_boundaries(tmp_path: Path) -> None:
    names = _files(tmp_path, "A.md", "B.md", "C.md")
    store = NoteOrderStore(tmp_path)
    assert not store.move(tmp_path, "A.md", -1, names)
    assert not store.move(tmp_path, "C.md", 1, names)
    assert store.move(tmp_path, "B.md", 1, names)
    assert store.ordered_names(tmp_path, names) == ["A.md", "C.md", "B.md"]


def test_unknown_notes_append_alphabetically_and_stale_are_ignored(tmp_path: Path) -> None:
    _files(tmp_path, "A.md", "B.md", "C.md")
    (tmp_path / ".note_order.json").write_text(
        json.dumps({"version": 1, "chapters": {".": ["B.md", "Gone.md"]}}),
        encoding="utf-8",
    )
    store = NoteOrderStore(tmp_path)
    assert store.ordered_names(tmp_path, ["C.md", "A.md", "B.md"]) == [
        "B.md",
        "A.md",
        "C.md",
    ]


def test_corrupt_json_is_safe(tmp_path: Path) -> None:
    (tmp_path / ".note_order.json").write_text("{broken", encoding="utf-8")
    store = NoteOrderStore(tmp_path)
    assert store.ordered_names(tmp_path, ["B.md", "A.md"]) == ["A.md", "B.md"]


def test_rename_note_keeps_position(tmp_path: Path) -> None:
    names = _files(tmp_path, "A.md", "B.md", "C.md")
    store = NoteOrderStore(tmp_path)
    store.move(tmp_path, "B.md", -1, names)
    (tmp_path / "B.md").rename(tmp_path / "Renamed.md")
    store.rename_note(tmp_path / "B.md", tmp_path / "Renamed.md")
    assert NoteOrderStore(tmp_path).ordered_names(
        tmp_path,
        ["A.md", "Renamed.md", "C.md"],
    ) == ["Renamed.md", "A.md", "C.md"]


def test_move_note_between_chapters_appends_to_target(tmp_path: Path) -> None:
    source = tmp_path / "Source"
    target = tmp_path / "Target"
    _files(source, "A.md", "B.md")
    _files(target, "X.md")
    store = NoteOrderStore(tmp_path)
    store.move(source, "B.md", -1, ["A.md", "B.md"])
    (source / "B.md").rename(target / "B.md")
    store.rename_note(source / "B.md", target / "B.md")
    reloaded = NoteOrderStore(tmp_path)
    assert reloaded.ordered_names(source, ["A.md"]) == ["A.md"]
    assert reloaded.ordered_names(target, ["X.md", "B.md"]) == ["X.md", "B.md"]


def test_rename_chapter_moves_nested_keys(tmp_path: Path) -> None:
    old = tmp_path / "Old"
    child = old / "Child"
    _files(old, "B.md", "A.md")
    _files(child, "D.md", "C.md")
    store = NoteOrderStore(tmp_path)
    store.move(old, "B.md", -1, ["A.md", "B.md"])
    store.move(child, "D.md", -1, ["C.md", "D.md"])
    new = tmp_path / "New"
    old.rename(new)
    store.rename_chapter(old, new)
    reloaded = NoteOrderStore(tmp_path)
    assert reloaded.ordered_names(new, ["A.md", "B.md"]) == ["B.md", "A.md"]
    assert reloaded.ordered_names(new / "Child", ["C.md", "D.md"]) == [
        "D.md",
        "C.md",
    ]


def test_remove_note_and_chapter(tmp_path: Path) -> None:
    chapter = tmp_path / "Chapter"
    child = chapter / "Child"
    _files(chapter, "A.md", "B.md")
    _files(child, "C.md", "D.md")
    store = NoteOrderStore(tmp_path)
    store.move(chapter, "B.md", -1, ["A.md", "B.md"])
    store.move(child, "D.md", -1, ["C.md", "D.md"])
    store.remove_note(chapter / "B.md")
    store.remove_chapter(chapter)
    payload = json.loads((tmp_path / ".note_order.json").read_text(encoding="utf-8"))
    assert "Chapter" not in payload["chapters"]
    assert "Chapter/Child" not in payload["chapters"]


def test_rejects_paths_outside_notes_root(tmp_path: Path) -> None:
    store = NoteOrderStore(tmp_path / "notes")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        store.chapter_key(outside)
    except ValueError:
        pass
    else:
        raise AssertionError("outside path should be rejected")
