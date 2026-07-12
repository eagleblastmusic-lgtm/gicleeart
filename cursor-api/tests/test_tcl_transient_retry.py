from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest

from tools.stage2_tcl_retry import (
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


def test_second_init_tcl_failure_remains_blocking(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    library = tmp_path / "tcl8.6"
    library.mkdir()
    (library / "init.tcl").write_text("# init", encoding="utf-8")
    monkeypatch.setenv("TCL_LIBRARY", str(library))
    calls: list[int] = []

    def original(_instance: object) -> None:
        calls.append(1)
        raise tk.TclError("Can't find a usable init.tcl in the following directories")

    with pytest.raises(tk.TclError, match="Can't find a usable init.tcl"):
        call_tk_init_with_transient_retry(original, object(), (), {})
    assert len(calls) == 2


def test_prepare_script_uses_unique_github_run_identity() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / ".github" / "scripts" / "prepare-tk-runtime.ps1").read_text(
        encoding="utf-8"
    )

    assert "$env:GITHUB_RUN_ID" in script
    assert "$env:GITHUB_RUN_ATTEMPT" in script
    assert "$env:GITHUB_JOB" in script
    assert '"python-tcl-runtime-$safeIdentity"' in script
