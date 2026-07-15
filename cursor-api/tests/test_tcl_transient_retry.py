from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest

from tools.stage2_tcl_retry import (
    call_tk_init_with_transient_retry,
    ci_tcl_retry_enabled,
    is_transient_tcl_runtime_error,
    wait_for_tcl_runtime_readable,
)


def _repo_file(relative: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / relative).read_text(encoding="utf-8")


def test_ci_tcl_retry_is_disabled_even_on_github_actions() -> None:
    assert ci_tcl_retry_enabled({}) is False
    assert ci_tcl_retry_enabled({"GITHUB_ACTIONS": "true"}) is False
    assert (
        ci_tcl_retry_enabled(
            {
                "GITHUB_ACTIONS": "TRUE",
                "TCL_LIBRARY": r"C:\temp\tcl8.6",
                "TK_LIBRARY": r"C:\temp\tk8.6",
            }
        )
        is False
    )


def test_exact_runtime_failure_is_not_retried_on_same_object() -> None:
    calls: list[int] = []

    def original(_instance: object) -> None:
        calls.append(1)
        raise tk.TclError("Can't find a usable init.tcl in the following directories")

    with pytest.raises(tk.TclError, match="Can't find a usable init.tcl"):
        call_tk_init_with_transient_retry(original, object(), (), {})
    assert len(calls) == 1


def test_non_matching_tcl_error_is_not_retried() -> None:
    calls: list[int] = []

    def original(_instance: object) -> None:
        calls.append(1)
        raise tk.TclError("no display name and no $DISPLAY environment variable")

    with pytest.raises(tk.TclError, match="no display name"):
        call_tk_init_with_transient_retry(original, object(), (), {})
    assert len(calls) == 1


def test_runtime_detector_accepts_init_and_tk_signatures_only() -> None:
    assert is_transient_tcl_runtime_error(
        tk.TclError("Can't find a usable init.tcl in the following directories")
    )
    assert is_transient_tcl_runtime_error(
        tk.TclError("Can't find a usable tk.tcl in the following directories")
    )
    assert not is_transient_tcl_runtime_error(
        tk.TclError('invalid command name "tcl_findLibrary"')
    )
    assert not is_transient_tcl_runtime_error(
        tk.TclError("no display name and no $DISPLAY environment variable")
    )


def test_runtime_readability_requires_complete_current_contract(tmp_path: Path) -> None:
    tcl_library = tmp_path / "tcl8.6"
    tk_library = tmp_path / "tk8.6"
    ttk_library = tk_library / "ttk"
    tcl_library.mkdir()
    ttk_library.mkdir(parents=True)

    (tcl_library / "init.tcl").write_text("# init", encoding="utf-8")
    (tk_library / "tk.tcl").write_text("# tk", encoding="utf-8")
    (tk_library / "spinbox.tcl").write_text("# spinbox", encoding="utf-8")
    (ttk_library / "defaults.tcl").write_text("# defaults", encoding="utf-8")

    assert wait_for_tcl_runtime_readable(str(tcl_library), str(tk_library)) is False

    (ttk_library / "winTheme.tcl").write_text("# win", encoding="utf-8")
    assert wait_for_tcl_runtime_readable(str(tcl_library), str(tk_library)) is True


def test_prepare_script_builds_unique_per_run_mirror() -> None:
    script = _repo_file(".github/scripts/prepare-tk-runtime.ps1")

    assert '[switch]$VerifyOnly' in script
    assert '$sourceRoot = Join-Path $pythonRoot "tcl"' in script
    assert 'python-tcl-runtime-$safeIdentity' in script
    assert '$env:GITHUB_RUN_ID' in script
    assert '$env:GITHUB_RUN_ATTEMPT' in script
    assert '$env:GITHUB_JOB' in script
    assert 'Join-Path $env:RUNNER_TEMP' in script
    assert '& robocopy $sourceRoot $targetRoot /E' in script
    assert 'Copy-Item' not in script


def test_prepare_script_verifies_full_sha256_manifest() -> None:
    script = _repo_file(".github/scripts/prepare-tk-runtime.ps1")

    assert 'function Get-RuntimeManifest' in script
    assert 'Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256' in script
    assert 'function Assert-RuntimeManifestsEqual' in script
    assert 'length = [int64]$_.Length' in script
    assert 'sha256 =' in script
    assert 'ConvertTo-Json -Depth 6' in script
    assert 'GICLEEAPP_TK_RUNTIME_MANIFEST' in script
    assert 'Mirror copy' in script
    assert 'VerifyOnly' in script


def test_prepare_script_requires_complete_tk_dependency_tree() -> None:
    script = _repo_file(".github/scripts/prepare-tk-runtime.ps1")

    for required in (
        '"init.tcl"',
        '"tk.tcl"',
        '"icons.tcl"',
        '"spinbox.tcl"',
        '"ttk\\ttk.tcl"',
        '"ttk\\defaults.tcl"',
        '"ttk\\classicTheme.tcl"',
        '"ttk\\winTheme.tcl"',
    ):
        assert required in script


def test_prepare_script_publishes_only_mirrored_libraries() -> None:
    script = _repo_file(".github/scripts/prepare-tk-runtime.ps1")

    assert '$targetTcl = Join-Path $targetRoot $sourceTcl.Name' in script
    assert '$targetTk = Join-Path $targetRoot $sourceTk.Name' in script
    assert '-TclLibrary $targetTcl' in script
    assert '-TkLibrary $targetTk' in script
    assert 'TCL_LIBRARY = $TclLibrary' in script
    assert 'TK_LIBRARY = $TkLibrary' in script
    assert 'GICLEEAPP_TK_RUNTIME_ROOT = $RuntimeRoot' in script
    assert '$env:TCL_LIBRARY = $sourceTcl.FullName' not in script
    assert '$env:TK_LIBRARY = $sourceTk.FullName' not in script


def test_prepare_script_keeps_real_tk_ttk_preflight_without_retry() -> None:
    script = _repo_file(".github/scripts/prepare-tk-runtime.ps1")

    assert 'root = tk.Tk()' in script
    assert 'tk.Spinbox(root)' in script
    assert 'ttk.Style(root)' in script
    assert 'globalgetvar("tcl_library")' in script
    assert 'globalgetvar("tk_library")' in script
    assert 'Start-Sleep' not in script
    assert 'call_tk_init_with_transient_retry' not in script


def test_verify_only_validates_existing_mirror_without_copying_again() -> None:
    script = _repo_file(".github/scripts/prepare-tk-runtime.ps1")

    verify_block = script.split('if ($VerifyOnly) {', 1)[1].split(
        '$pythonRoot = Split-Path -Parent $pythonExe', 1
    )[0]
    assert 'Get-RuntimeManifest -Root $actualRoot' in verify_block
    assert 'Assert-RuntimeManifestsEqual' in verify_block
    assert 'Invoke-TkRuntimePreflight' in verify_block
    assert 'robocopy' not in verify_block
    assert 'Remove-Item' not in verify_block


def test_stage2_workflow_uses_mirror_and_verify_only_before_full_pytest() -> None:
    workflow = _repo_file(".github/workflows/stage2-ci-baseline.yml")

    assert workflow.count('Prepare mirrored Tcl/Tk runtime') == 2
    assert 'Verify mirrored Tcl/Tk runtime before full baseline' in workflow
    assert '-RuntimeName "full-baseline" -VerifyOnly' in workflow
    warm_index = workflow.index('Warm Tcl/Tk on full-baseline runner')
    verify_index = workflow.index('Verify mirrored Tcl/Tk runtime before full baseline')
    full_index = workflow.index('Run full pytest baseline')
    assert warm_index < verify_index < full_index
    assert 'continue-on-error: true' not in workflow
    assert 'stage2-full-baseline-${{ github.run_id }}' in workflow
    assert 'if: always()' in workflow
