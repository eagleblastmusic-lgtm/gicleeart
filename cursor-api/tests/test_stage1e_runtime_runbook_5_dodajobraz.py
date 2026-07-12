from __future__ import annotations

from pathlib import Path


def test_stage1e_5_dodajobraz_runbook_is_isolated_and_non_destructive() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "stage1e-runtime-paths-local-validation-5-dodajobraz.ps1"
    text = path.read_text(encoding="utf-8")
    assert "GICLEEAPP_LOCAL_ROOT" in text
    assert "GICLEEAPP_ROAMING_ROOT" in text
    assert "gicleeapp-stage1e-5-dodajobraz-validation-" in text
    assert "tests/test_stage1e_external_stores_5_dodajobraz.py" in text
    assert "tests/test_description_update_marks.py" in text
    assert "tests/test_product_template_assignments.py" in text
    assert "tests/test_variant_templates_default.py" in text
    assert "tests/test_r2_usage.py" in text
    assert "tests/test_markets.py" in text
    assert "git status --porcelain" in text
    lowered = text.lower()
    for forbidden in (
        " migrate ",
        " --copy",
        "remove-item",
        "git rm",
        "git add",
        "git commit",
        "git push",
        "shopify deploy",
    ):
        assert forbidden not in lowered
