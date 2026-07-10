from __future__ import annotations

from datetime import datetime
from pathlib import Path

from Komponenty.notatnik.clipboard_images import (
    iter_render_segments,
    make_asset_destination,
    markdown_image_reference,
    resolve_local_image,
    rewrite_local_image_links_for_move,
)


def test_asset_destination_uses_hidden_global_assets_folder(tmp_path: Path) -> None:
    destination = make_asset_destination(
        tmp_path,
        now=datetime(2026, 7, 10, 20, 45, 0, 123456),
        token="abc123",
    )
    assert destination.parent == tmp_path / ".assets"
    assert destination.name == "paste-20260710-204500-123456-abc123.png"


def test_markdown_reference_is_relative_to_nested_note(tmp_path: Path) -> None:
    note = tmp_path / "A" / "B" / "notatka.md"
    image = tmp_path / ".assets" / "grafika.png"
    assert markdown_image_reference(note, image) == (
        "![Wklejona grafika](../../.assets/grafika.png)"
    )


def test_resolve_local_image_accepts_assets_inside_notes_root(tmp_path: Path) -> None:
    note = tmp_path / "Rozdzial" / "notatka.md"
    image = tmp_path / ".assets" / "grafika.png"
    note.parent.mkdir()
    image.parent.mkdir()
    image.write_bytes(b"png")
    resolved = resolve_local_image(note, "../.assets/grafika.png", tmp_path)
    assert resolved == image.resolve()


def test_resolve_local_image_rejects_traversal_and_remote_urls(tmp_path: Path) -> None:
    note = tmp_path / "notatka.md"
    outside = tmp_path.parent / "poza.png"
    outside.write_bytes(b"png")
    assert resolve_local_image(note, "../poza.png", tmp_path) is None
    assert resolve_local_image(note, "https://example.com/image.png", tmp_path) is None
    assert resolve_local_image(note, "data:image/png;base64,AAA", tmp_path) is None


def test_rewrite_local_image_link_after_note_move(tmp_path: Path) -> None:
    old_note = tmp_path / "A" / "notatka.md"
    new_note = tmp_path / "A" / "B" / "notatka.md"
    image = tmp_path / ".assets" / "grafika.png"
    old_note.parent.mkdir(parents=True)
    new_note.parent.mkdir(parents=True)
    image.parent.mkdir()
    image.write_bytes(b"png")
    content = "# Tytul\n\n![Podglad](../.assets/grafika.png)\n"
    rewritten = rewrite_local_image_links_for_move(
        content,
        old_note,
        new_note,
        tmp_path,
    )
    assert "![Podglad](../../.assets/grafika.png)" in rewritten


def test_render_segments_extracts_standalone_images_only() -> None:
    content = (
        "# Tytul\n"
        "\n"
        "![Grafika](.assets/a.png)\n"
        "Zwykly tekst z ![inline](.assets/b.png) w srodku.\n"
    )
    segments = list(iter_render_segments(content))
    assert ("image", "Grafika", ".assets/a.png") in segments
    markdown = "".join(first for kind, first, _ in segments if kind == "markdown")
    assert "![inline](.assets/b.png)" in markdown
