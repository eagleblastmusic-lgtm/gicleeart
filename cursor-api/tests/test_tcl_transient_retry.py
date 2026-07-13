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


def test_runtime_readability_requires_complete_tcl_and_tk_tree(tmp_path: Path) -> None:
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


def test_prepare_script_uses_setup_python_runtime_without_copy() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / ".github" / "scripts" / "prepare-tk-runtime.ps1").read_text(
        encoding="utf-8"
    )

    assert '$sourceRoot = Join-Path $pythonRoot "tcl"' in script
    assert "$env:TCL_LIBRARY = $sourceTcl.FullName" in script
    assert "$env:TK_LIBRARY = $sourceTk.FullName" in script
    assert "robocopy" not in script
    assert "Copy-Item" not in script
    assert "python-tcl-runtime-" not in script
    assert "GICLEEAPP_TCL_SOURCE_LIBRARY" not in script
    assert "GICLEEAPP_TK_SOURCE_LIBRARY" not in script


def test_prepare_script_verifies_complete_tk_runtime_and_widget_preflight() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / ".github" / "scripts" / "prepare-tk-runtime.ps1").read_text(
        encoding="utf-8"
    )

    assert 'Join-Path $sourceTcl.FullName "init.tcl"' in script
    assert 'Join-Path $sourceTk.FullName "tk.tcl"' in script
    assert 'Join-Path $sourceTk.FullName "spinbox.tcl"' in script
    assert 'Join-Path $sourceTk.FullName "ttk\\defaults.tcl"' in script
    assert 'Join-Path $sourceTk.FullName "ttk\\winTheme.tcl"' in script
    assert 'globalgetvar("tcl_library")' in script
    assert 'globalgetvar("tk_library")' in script
    assert "tk.Spinbox(root)" in script
    assert "ttk.Style(root)" in script
