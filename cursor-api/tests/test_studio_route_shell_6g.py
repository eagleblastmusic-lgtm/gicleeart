from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_launcher_has_route_shell_for_cold_views() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    assert "_show_route_shell" in text
    assert "studio.route_shell.visible" in text
    assert "studio.show_view.deferred_factory" in text
    assert "studio.show_view.mounted" in text


def test_cold_show_view_does_not_update_idletasks_before_route_shell() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    route_block = _method_block(text, "_show_route_shell")
    assert "update_idletasks" not in route_block

    show_view_block = _method_block(text, "_show_view")
    cold_section = show_view_block.split("if not cache_hit and not skip_route_shell:", 1)[1]
    before_deferred = cold_section.split("self.after(", 1)[0]
    assert "update_idletasks" not in before_deferred


def test_launcher_warm_cache_path_unchanged() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    block = _method_block(text, "_show_view")
    assert "cache_hit=cache_hit" in block
    mount_lane = _method_block(text, "_mount_view_lane")
    assert "except_key=key" in mount_lane
