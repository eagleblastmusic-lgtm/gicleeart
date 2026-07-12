from pathlib import Path


def test_stage1e_3_runbook_is_copy_free_and_non_destructive() -> None:
    text = Path("scripts/stage1e-runtime-paths-local-validation-3.ps1").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "--copy" not in lowered
    assert "git rm" not in lowered
    assert "remove-item" not in lowered
    assert "git add" not in lowered
    assert "git commit" not in lowered
    assert "git push" not in lowered
    assert "shopify" not in lowered
