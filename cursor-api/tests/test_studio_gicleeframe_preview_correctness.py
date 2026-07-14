from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
VISUAL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_visual_detail_renderers.py"


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}(\n"
    if marker not in text:
        marker = f"def {name}("
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_media_section_preview_has_metadata_renderer() -> None:
    text = VISUAL_PATH.read_text(encoding="utf-8")

    assert "_build_media_section_preview_structure" in text
    assert "_update_media_section_preview_content" in text
    assert "Uproszczony podgląd struktury sekcji" in text


def test_legacy_and_default_preview_have_fallback_renderers() -> None:
    text = VISUAL_PATH.read_text(encoding="utf-8")

    assert "_update_legacy_preview_content" in text
    assert "_build_default_preview_structure" in text
    assert "_update_default_preview_content" in text
    assert "Brak szczegółowego podglądu dla tego typu sekcji" in text


def test_preview_fallback_uses_informative_labels_not_skeleton_only() -> None:
    text = VISUAL_PATH.read_text(encoding="utf-8")
    media_block = _method_block(text, "_update_media_section_preview_content")
    default_block = _method_block(text, "_update_default_preview_content")

    assert "_apply_metadata_preview_content" in media_block
    assert "heading_label" in text
    assert "meta_label" in text
    assert "Typ elementu:" in text
    assert "Elementy podrzędne:" in text
    assert "Ustawienia strony:" in default_block or "Ustawienia strony:" in text


def test_preview_key_covers_editorial_section_types() -> None:
    text = VISUAL_PATH.read_text(encoding="utf-8")
    block = _method_block(text, "_preview_key_for_element")

    assert "media_section" in block
    assert "section_legacy" in block


def test_update_section_preview_still_uses_reuse_cache() -> None:
    text = VISUAL_PATH.read_text(encoding="utf-8")
    block = _method_block(text, "_update_section_preview")

    assert "preview.reuse" in block
    assert "_ensure_preview_structure" in block
    assert "_update_preview_content" in block
    assert "_hide_preview_frames" in block
    assert "_show_preview_frame" in block


def test_preview_fallback_logs_event() -> None:
    text = VISUAL_PATH.read_text(encoding="utf-8")

    assert "studio.gicleeframe.preview.fallback_used" in text


def test_preview_correctness_no_writer_or_deploy() -> None:
    text = VISUAL_PATH.read_text(encoding="utf-8")
    preview_block = text.split("def _preview_key_for_element", 1)[1].split(
        "\n    def _hide_preview_frames",
        1,
    )[0]

    forbidden = [
        "write_text(",
        "deploy(",
        "Shopify API",
    ]
    for item in forbidden:
        assert item not in preview_block
