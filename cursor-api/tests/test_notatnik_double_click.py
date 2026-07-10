from __future__ import annotations

from pathlib import Path

from Komponenty.notatnik.interactive_gui import double_click_action


def test_double_click_toggles_chapter(tmp_path: Path) -> None:
    chapter = tmp_path / "Rozdzial"
    chapter.mkdir()
    assert double_click_action("Rozdzial", chapter, False) == "toggle"


def test_double_click_toggles_virtual_favorites_root(tmp_path: Path) -> None:
    assert double_click_action("__favorites__", tmp_path, True) == "toggle"


def test_double_click_renames_markdown_note(tmp_path: Path) -> None:
    note = tmp_path / "Notatka.md"
    note.write_text("# Notatka\n", encoding="utf-8")
    assert double_click_action("Notatka.md", note, False) == "rename"


def test_double_click_renames_note_from_favorites_copy(tmp_path: Path) -> None:
    note = tmp_path / "Notatka.md"
    note.write_text("# Notatka\n", encoding="utf-8")
    assert double_click_action("__fav__::Notatka.md", note, False) == "rename"


def test_double_click_ignores_empty_or_unsupported_row(tmp_path: Path) -> None:
    unsupported = tmp_path / "plik.txt"
    unsupported.write_text("x", encoding="utf-8")
    assert double_click_action("", tmp_path, False) == "none"
    assert double_click_action("plik.txt", unsupported, False) == "none"
