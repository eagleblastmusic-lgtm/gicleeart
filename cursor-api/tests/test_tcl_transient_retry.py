from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path

import pytest

from tools.stage2_tcl_retry import (
    activate_preflighted_source_runtime,
    call_tk_init_with_transient_retry,
    ci_tcl_retry_enabled,
)


def test_ci_tcl_retry_requires_github_actions_and_library() -> None:
    assert ci_tcl_retry_enabled({}) is False
    assert ci_tcl_retry_enabled({"GITHUB_ACTIONS": "true"}) is False
    assert (
        ci_tcl_retry_enabled(
            {"GITHUB_ACTIONS": "TRUE", "TCL_LIBRARY": r"C:\temp\tcl8.6"}
        )
        is True
    )


def test_exact_init_tcl_failure_is_retried_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    library = tmp_path / "tcl8.6"
    library.mkdir()
    (library / "init.tcl").write_text("# init", encoding="utf-8")
    monkeypatch.setenv("TCL_LIBRARY", str(library))

    calls: list[int] = []

    def original(_instance: object) -> str:
        calls.append(1)
        if len(calls) == 1:
            raise tk.TclError("Can't find a usable init.tcl in the following directories")
        return "ready"

    assert call_tk_init_with_transient_retry(original, object(), (), {}) == "ready"
    assert len(calls) == 2


def test_non_matching_tcl_error_is_not_retried() -> None:
    calls: list[int] = []

    def original(_instance: object) -> None:
        calls.append(1)
        raise tk.TclError("no display name and no $DISPLAY environment variable")

    with pytest.raises(tk.TclError, match="no display name"):
        call_tk_init_with_transient_retry(original, object(), (), {})
    assert len(calls) == 1


def test_second_init_tcl_failure_remains_blocking_without_source_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    library = tmp_path / "tcl8.6"
    library.mkdir()
    (library / "init.tcl").write_text("# init", encoding="utf-8")
    monkeypatch.setenv("TCL_LIBRARY", str(library))
    monkeypatch.delenv("GICLEEAPP_TCL_SOURCE_LIBRARY", raising=False)
    monkeypatch.delenv("GICLEEAPP_TK_SOURCE_LIBRARY", raising=False)
    calls: list[int] = []

    def original(_instance: object) -> None:
        calls.append(1)
        raise tk.TclError("Can't find a usable init.tcl in the following directories")

    with pytest.raises(tk.TclError, match="Can't find a usable init.tcl"):
        call_tk_init_with_transient_retry(original, object(), (), {})
    assert len(calls) == 2


def test_repeated_copied_runtime_failure_switches_to_preflighted_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    copied_tcl = tmp_path / "copied" / "tcl8.6"
    copied_tk = tmp_path / "copied" / "tk8.6"
    source_tcl = tmp_path / "source" / "tcl8.6"
    source_tk = tmp_path / "source" / "tk8.6"
    for directory in (copied_tcl, copied_tk, source_tcl, source_tk / "ttk"):
        directory.mkdir(parents=True, exist_ok=True)
    (copied_tcl / "init.tcl").write_text("# copied", encoding="utf-8")
    (source_tcl / "init.tcl").write_text("# source", encoding="utf-8")
    (source_tk / "tk.tcl").write_text("# tk", encoding="utf-8")
    (source_tk / "spinbox.tcl").write_text("# spinbox", encoding="utf-8")
    (source_tk / "ttk" / "defaults.tcl").write_text("# ttk", encoding="utf-8")

    monkeypatch.setenv("TCL_LIBRARY", str(copied_tcl))
    monkeypatch.setenv("TK_LIBRARY", str(copied_tk))
    monkeypatch.setenv("GICLEEAPP_TCL_SOURCE_LIBRARY", str(source_tcl))
    monkeypatch.setenv("GICLEEAPP_TK_SOURCE_LIBRARY", str(source_tk))

    calls: list[str] = []

    def original(_instance: object) -> str:
        active = os.environ["TCL_LIBRARY"]
        calls.append(active)
        if Path(active) == copied_tcl:
            raise tk.TclError("Can't find a usable init.tcl in the following directories")
        return "ready-from-source"

    assert (
        call_tk_init_with_transient_retry(original, object(), (), {})
        == "ready-from-source"
    )
    assert calls == [str(copied_tcl), str(copied_tcl), str(source_tcl)]
    assert os.environ["TK_LIBRARY"] == str(source_tk)


def test_source_runtime_activation_requires_complete_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_tcl = tmp_path / "source" / "tcl8.6"
    source_tk = tmp_path / "source" / "tk8.6"
    source_tcl.mkdir(parents=True)
    source_tk.mkdir(parents=True)
    (source_tcl / "init.tcl").write_text("# source", encoding="utf-8")
    (source_tk / "tk.tcl").write_text("# tk", encoding="utf-8")
    monkeypatch.setenv("GICLEEAPP_TCL_SOURCE_LIBRARY", str(source_tcl))
    monkeypatch.setenv("GICLEEAPP_TK_SOURCE_LIBRARY", str(source_tk))

    assert activate_preflighted_source_runtime() is False


def test_prepare_script_uses_unique_github_run_identity() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / ".github" / "scripts" / "prepare-tk-runtime.ps1").read_text(
        encoding="utf-8"
    )

    assert "$env:GITHUB_RUN_ID" in script
    assert "$env:GITHUB_RUN_ATTEMPT" in script
    assert "$env:GITHUB_JOB" in script
    assert '"python-tcl-runtime-$safeIdentity"' in script


def test_prepare_script_verifies_complete_tk_runtime_and_widget_preflight() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / ".github" / "scripts" / "prepare-tk-runtime.ps1").read_text(
        encoding="utf-8"
    )

    assert "Get-RuntimeManifest" in script
    assert "Compare-Object -ReferenceObject $sourceManifest" in script
    assert 'Join-Path $targetTk "spinbox.tcl"' in script
    assert 'Join-Path $targetTk "ttk\\defaults.tcl"' in script
    assert 'globalgetvar("tk_library")' in script
    assert "tk.Spinbox(root)" in script
    assert "ttk.Style(root)" in script
    assert "robocopy" in script
    assert "GICLEEAPP_TCL_SOURCE_LIBRARY" in script
    assert "GICLEEAPP_TK_SOURCE_LIBRARY" in script
