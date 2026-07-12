from __future__ import annotations

from pathlib import Path


def test_stage1e_8_sales_sync_runbook_is_isolated_and_non_destructive() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "stage1e-runtime-paths-local-validation-8-sales-sync-artifacts.ps1"
    text = path.read_text(encoding="utf-8")

    assert "GICLEEAPP_LOCAL_ROOT" in text
    assert "GICLEEAPP_ROAMING_ROOT" in text
    assert "gicleeapp-stage1e-8-sales-sync-artifacts-validation-" in text
    assert "tests/test_stage1e_external_stores_8_sales_sync_artifacts.py" in text
    assert "Komponenty/dokumentysprzedazy/orders_sync.py" in text
    assert "Komponenty/dokumentysprzedazy/export_monthly.py" in text
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
