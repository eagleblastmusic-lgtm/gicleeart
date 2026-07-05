"""Testy launcher_delegate — bez Popen, bez launcher.GicleeApp."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import Component, discover_components, find_components_dir
from giclee_app.launcher_delegate import (
    INLINE_MESSAGE,
    LaunchOutcome,
    build_subprocess_cmd,
    launch,
)


def _subprocess_component() -> Component:
    root = find_components_dir()
    comp = next(c for c in discover_components(root, include_hidden=True) if c.folder_name == "dodajobraz")
    return comp


def _inline_component() -> Component:
    root = find_components_dir()
    comp = next(c for c in discover_components(root, include_hidden=True) if c.folder_name == "produkcja")
    return comp


def test_build_subprocess_cmd() -> None:
    comp = _subprocess_component()
    cmd, err = build_subprocess_cmd(comp)
    assert cmd is not None, err
    assert cmd[-2:] == ["-m", "Komponenty.dodajobraz"]


def test_launch_inline_blocked() -> None:
    comp = _inline_component()
    result = launch(comp)
    assert result.outcome == LaunchOutcome.BLOCKED_INLINE
    assert INLINE_MESSAGE in result.message


@patch("giclee_app.launcher_delegate.subprocess.Popen")
def test_launch_subprocess_ok(mock_popen: object) -> None:
    class FakeProc:
        pid = 12345

        def wait(self) -> int:
            return 0

    mock_popen.return_value = FakeProc()
    comp = _subprocess_component()
    result = launch(comp)
    assert result.outcome == LaunchOutcome.OK
    assert result.pid == 12345
    mock_popen.assert_called_once()


def test_launch_url_no_url() -> None:
    comp = Component(
        folder_name="x",
        package_path=Path("."),
        name="X",
        description="",
        mode="url",
        url="",
    )
    result = launch(comp)
    assert result.outcome == LaunchOutcome.NO_URL
