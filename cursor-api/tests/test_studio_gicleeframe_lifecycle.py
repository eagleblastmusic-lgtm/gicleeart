from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_lifecycle_inventory.py"
HOST_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"


def test_launcher_gicleeframe_shell_keeps_cached_view() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    shell = text.split("def _show_gicleeframe_shell", 1)[1].split("\n    def ", 1)[0]
    mount = text.split("def _mount_gicleeframe_deferred", 1)[1].split("\n    def ", 1)[0]
    assert "_mount_gicleeframe_deferred" in shell
    assert "GicleeFrameView(" in mount
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
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    host_text = HOST_PATH.read_text(encoding="utf-8")

    assert "def set_navigation" in lifecycle_text
    assert "def _handle_back" in lifecycle_text
    assert "_back_button" in host_text
    assert "def on_show" in lifecycle_text
    assert "def on_hide" in lifecycle_text


def test_gicleeframe_on_show_does_not_refresh_inventory() -> None:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")

    block = lifecycle_text.split("def on_show", 1)[1].split("\n    def ", 1)[0]
    assert "_refresh_inventory" not in block
    assert "build_gicleeframe_page_inventory" not in block
