from __future__ import annotations

from pathlib import Path


RUNBOOK = Path("scripts/repository-safety-local-validation.ps1")


def test_local_validation_runbook_contains_only_dry_run_repository_actions() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    lower = text.lower()

    assert "tools.repository_safety audit" in text
    assert "tools.repository_safety migrate" in text
    assert "--profile all" in text
    assert "--include-untracked" in text
    assert "tools.repository_safety snapshot" in text
    assert "tests/test_gicleeapp_push_allowlist.py" in text
    assert "tests/test_repository_migration_profiles.py" in text

    forbidden_command_patterns = (
        "--copy",
        "& git ",
        "\ngit ",
        "start-process git",
        "& shopify ",
        "\nshopify ",
        "start-process shopify",
        "remove-item ",
        "move-item ",
        "copy-item ",
    )
    for token in forbidden_command_patterns:
        assert token not in lower, token


def test_local_validation_uses_isolated_tools_but_scans_canonical_checkout() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert '[string]$ToolRoot = ""' in text
    assert '[string]$ScanRoot = "C:\\Strona\\pusty\\cursor-api"' in text
    assert "Push-Location $ToolRoot" in text
    assert "audit --repo $ScanRoot" in text
    assert "migrate --repo $ScanRoot --profile all --include-untracked" in text
    assert "snapshot --source $ScanRoot --staging $StagingRoot" in text


def test_powershell_51_tool_root_is_resolved_after_parameter_binding() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    param_block = text.split(")\n\n$ErrorActionPreference", 1)[0]

    assert "$PSScriptRoot" not in param_block
    assert "[string]::IsNullOrWhiteSpace($ToolRoot)" in text
    assert 'Join-Path $PSScriptRoot ".."' in text


def test_local_validation_reports_are_written_outside_repository_by_default() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "$env:TEMP" in text
    assert "gicleeapp-repository-safety" in text
    assert "gicleeapp-migration-dry-run.json" in text
    assert "gicleeapp-snapshot-dry-run.json" in text
