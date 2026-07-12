from __future__ import annotations

from pathlib import Path


RUNBOOK = Path("scripts/repository-safety-copy-archive-cache.ps1")


def _text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_runbook_uses_explicit_copy_only_profiles_and_untracked_discovery() -> None:
    text = _text()

    assert 'Invoke-ProfileCopyGate -Profile "archive"' in text
    assert 'Invoke-ProfileCopyGate -Profile "cache"' in text
    assert '"--profile", $Profile' in text
    assert '"--include-untracked"' in text
    assert '"--copy"' in text
    assert "--profile all" not in text


def test_runbook_requires_preflight_copy_and_post_copy_hash_verification() -> None:
    text = _text()

    assert "preflight.json" in text
    assert "copy.json" in text
    assert "post-copy.json" in text
    assert "source_sha256" in text
    assert "destination_sha256" in text
    assert 'status -ne "verified_existing"' in text
    assert "Get-FileHash" in text
    assert "Assert-ReportsEquivalentSources" in text


def test_runbook_never_deletes_moves_untracks_or_invokes_shopify() -> None:
    lower = _text().lower()

    forbidden = (
        "remove-item",
        "move-item",
        "git rm",
        "git clean",
        "git reset",
        "--force",
        "shopify ",
        "start-process shopify",
    )
    for token in forbidden:
        assert token not in lower, token


def test_runbook_preserves_canonical_git_state_and_reports_safety_markers() -> None:
    text = _text()

    assert "status --porcelain=v1 --untracked-files=all" in text
    assert "$statusBefore" in text
    assert "$statusAfter" in text
    assert "Canonical source files modified: NO" in text
    assert "Source files removed: 0" in text
    assert "Git changes created: 0" in text
    assert "Cleanup/untracking performed: NO" in text
    assert "STAGE 1E.10 ARCHIVE/CACHE COPY GATE COMPLETE" in text


def test_runbook_defaults_reports_outside_repository_and_works_on_powershell_51() -> None:
    text = _text()
    param_block = text.split(")\n\n$ErrorActionPreference", 1)[0]

    assert '[string]$ToolRoot = ""' in text
    assert '[string]$ScanRoot = "C:\\Strona\\pusty\\cursor-api"' in text
    assert "$PSScriptRoot" not in param_block
    assert "[string]::IsNullOrWhiteSpace($ToolRoot)" in text
    assert "$env:TEMP" in text
    assert "ConvertFrom-Json" in text


def test_runbook_routes_python_stdout_to_host_not_function_output() -> None:
    text = _text()

    assert "& python @Arguments | Out-Host" in text
    assert "\n    & python @Arguments\n" not in text


def test_runbook_is_ascii_only_for_windows_powershell_51_parser_safety() -> None:
    raw = RUNBOOK.read_bytes()
    text = raw.decode("ascii")

    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert "Python command failed" in text
    assert "Canonical repository Git status changed during copy-only." in text
