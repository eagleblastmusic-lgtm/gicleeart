"""Skróty klawiszowe launchera — bez uruchamiania GUI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.launcher_shortcuts import LAUNCHER_KEY_SHORTCUTS


def test_integracjagpt_shortcut_mapping() -> None:
    assert LAUNCHER_KEY_SHORTCUTS.get("i") == "integracjagpt"


def test_shortcut_key_from_char_and_keysym() -> None:
    from giclee_app.launcher_shortcuts import shortcut_key_from_event

    assert shortcut_key_from_event(type("E", (), {"char": "I", "keysym": "I"})()) == "i"
    assert shortcut_key_from_event(type("E", (), {"char": "", "keysym": "i"})()) == "i"


def test_help_documents_integracjagpt_shortcut() -> None:
    from giclee_app.launcher import _GICLEE_HELP

    assert "integracjagpt" in _GICLEE_HELP
    assert "**i**" in _GICLEE_HELP
