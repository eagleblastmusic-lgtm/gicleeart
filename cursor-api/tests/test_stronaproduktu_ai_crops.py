from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "Komponenty" / "stronaproduktu" / "ai_crops.py"
spec = importlib.util.spec_from_file_location("story_ai_crops_under_test", MODULE_PATH)
assert spec and spec.loader
ai = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ai
spec.loader.exec_module(ai)


def test_build_page_texts_respects_counts() -> None:
    assert ai.build_page_texts(["A", "B", "C", "D"], [2, 1]) == ["A\n\nB", "C"]


def test_parse_crop_plan_accepts_fenced_json_and_normalized_boxes() -> None:
    raw = """```json
    {"pages":[{"page_index":1,"candidates":[{"box_2d":[100,200,700,800],"confidence":0.8,"matched_subject":"posta─ç"}]}]}
    ```"""
    plan = ai.parse_crop_plan(raw, page_count=3)
    candidate = plan[1][0]
    assert candidate.box.xmin == pytest.approx(0.2)
    assert candidate.box.ymin == pytest.approx(0.1)
    assert candidate.box.xmax == pytest.approx(0.8)
    assert candidate.box.ymax == pytest.approx(0.7)


def test_fit_box_to_aspect_stays_inside_image_and_hits_ratio() -> None:
    fitted = ai.fit_box_to_aspect(
        ai.NormalizedBox(0.4, 0.2, 0.6, 0.8),
        source_size=(3000, 2000),
        min_width_px=0,
        padding=0,
    )
    assert 0 <= fitted.xmin < fitted.xmax <= 1
    assert 0 <= fitted.ymin < fitted.ymax <= 1
    ratio = (fitted.width * 3000) / (fitted.height * 2000)
    assert ratio == pytest.approx(ai.TARGET_ASPECT_RATIO, rel=1e-5)


def test_rank_candidates_penalizes_duplicate_of_previous_detail() -> None:
    plan = {
        1: [
            ai.CropCandidate(ai.NormalizedBox(0.1, 0.1, 0.5, 0.6), "subject", "A", "A", 0.8)
        ],
        2: [
            ai.CropCandidate(ai.NormalizedBox(0.1, 0.1, 0.5, 0.6), "subject", "powt├│rka", "x", 0.9),
            ai.CropCandidate(ai.NormalizedBox(0.55, 0.2, 0.95, 0.7), "detail", "B", "B", 0.82),
        ],
    }
    ranked = ai.rank_page_candidates(plan, page_count=3, source_size=(2400, 1800))
    assert ranked[2][0].matched_subject == "B"


def test_extract_product_image_url_prefers_featured_image() -> None:
    product = {
        "image": {"src": "https://cdn.example/featured.jpg"},
        "images": [{"src": "https://cdn.example/other.jpg"}],
    }
    assert ai.extract_product_image_url(product).endswith("featured.jpg")


def test_rendered_crop_has_target_ratio(tmp_path: Path) -> None:
    Image = pytest.importorskip("PIL.Image")
    source = Image.new("RGB", (2000, 1400), "white")
    box = ai.fit_box_to_aspect(
        ai.NormalizedBox(0.2, 0.2, 0.7, 0.8),
        source_size=source.size,
        min_width_px=0,
    )
    path = tmp_path / "crop.jpg"
    ai._save_crop(source, box, path, {})
    with Image.open(path) as crop:
        assert crop.width / crop.height == pytest.approx(ai.TARGET_ASPECT_RATIO, rel=0.01)
