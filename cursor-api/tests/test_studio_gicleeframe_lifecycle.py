from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_launcher_gicleeframe_shell_keeps_cached_view() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    shell = text.split("def _show_gicleeframe_shell", 1)[1].split("\n    def ", 1)[0]
    assert "GicleeFrameView(" in shell
    assert '"gicleeframe"' in shell or "'gicleeframe'" in shell
    assert "cache_hit" in shell
    assert ".destroy()" not in shell
    assert 'pop("gicleeframe")' not in shell
    assert "pop('gicleeframe')" not in shell


def test_launcher_return_from_gicleeframe_does_not_destroy_cached_view() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    block = text.split("def _return_from_gicleeframe", 1)[1].split("\n    def ", 1)[0]
    assert ".destroy()" not in block
    assert 'pop("gicleeframe")' not in block
    assert "pop('gicleeframe')" not in block
    assert "_show_hub(category)" in block


def test_gicleeframe_view_has_dynamic_navigation() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def set_navigation" in text
    assert "def _handle_back" in text
    assert "_back_button" in text
    assert "def on_show" in text
    assert "def on_hide" in text


def test_gicleeframe_on_show_does_not_refresh_inventory() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    block = text.split("def on_show", 1)[1].split("\n    def ", 1)[0]
    assert "_refresh_inventory" not in block
    assert "build_gicleeframe_page_inventory" not in block
