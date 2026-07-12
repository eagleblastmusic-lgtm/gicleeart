from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "scripts" / "stage1e-runtime-paths-local-validation.ps1"


def test_stage1e_runbook_is_isolated_and_copy_free() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "GICLEEAPP_LOCAL_ROOT" in text
    assert "GICLEEAPP_ROAMING_ROOT" in text
    assert "[Guid]::NewGuid" in text
    assert "tests/test_app_paths.py" in text
    assert "tests/test_stage1e_external_stores.py" in text
    assert "python -m compileall" in text
    assert "git status --porcelain" in text

    forbidden = (
        "--copy",
        "Remove-Item",
        "git clean",
        "git reset",
        "git checkout --",
        "git add",
        "git commit",
        "git push",
        "shopify theme push",
    )
    for token in forbidden:
        assert token not in text


def test_stage1e_runbook_does_not_use_psscriptroot_in_parameter_default() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    param_block = text.split(")", 1)[0]

    assert "$PSScriptRoot" not in param_block
    assert "if ([string]::IsNullOrWhiteSpace($ToolRoot))" in text
