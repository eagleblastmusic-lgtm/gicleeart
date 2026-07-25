from __future__ import annotations

from pathlib import Path

from Komponenty.faq.registry import PAGE_ZONES

ROOT = Path(__file__).resolve().parents[2]
ACCORDION_ROW = ROOT / "blocks" / "_accordion-row.liquid"


def test_faq_accordion_exposes_question_and_answer_images() -> None:
    zone = next(z for z in PAGE_ZONES if z.zone_id == "faq_accordion")
    field_ids = {fld.field_id for fld in zone.fields}

    for n in range(1, 6):
        assert f"q{n}_heading" in field_ids
        assert f"q{n}_answer" in field_ids
        assert f"q{n}_image" in field_ids
        assert f"q{n}_answer_image" in field_ids

    q1_image = next(fld for fld in zone.fields if fld.field_id == "q1_image")
    assert q1_image.kind == "shopify_image"
    assert q1_image.path[-1] == "heading_background_image"

    q1_answer_image = next(fld for fld in zone.fields if fld.field_id == "q1_answer_image")
    assert q1_answer_image.kind == "shopify_image"
    assert q1_answer_image.path[-1] == "answer_background_image"


def test_accordion_row_renders_art_gradient_layers() -> None:
    source = ACCORDION_ROW.read_text(encoding="utf-8")
    assert "heading_background_image" in source
    assert "answer_background_image" in source
    assert "details__art" in source
    assert "details__art-veil" in source
    assert "details--art" in source
    assert "details--art-shared" in source
    assert "--details-art-image" in source
    assert "linear-gradient" in source
    # Shared mode must honor kadrowanie (object_y), not a hardcoded top anchor.
    assert "--details-art-position: 72% {{ heading_art_oy }}%" in source
    assert "heading_background_image_object_y" in source
    assert "72% 0%" not in source
