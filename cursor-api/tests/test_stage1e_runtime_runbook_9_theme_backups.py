from __future__ import annotations

from pathlib import Path


def test_stage1e_9_theme_backup_runbook_is_isolated_and_non_destructive() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "stage1e-runtime-paths-local-validation-9-theme-backups.ps1"
    text = path.read_text(encoding="utf-8")
    assert "GICLEEAPP_LOCAL_ROOT" in text
    assert "GICLEEAPP_ROAMING_ROOT" in text
    assert "gicleeapp-stage1e-9-theme-backups-validation-" in text
    assert "tests/test_stage1e_external_stores_9_theme_backups.py" in text
    assert "tests/test_theme_page_editor_writer_safety.py" in text
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
