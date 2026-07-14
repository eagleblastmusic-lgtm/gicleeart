from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _editor_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
    ).read_text(encoding="utf-8")


def _lifecycle_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_lifecycle_inventory.py"
    ).read_text(encoding="utf-8")


def test_gicleeframe_has_lazy_shell() -> None:
    host = _view_text()
    editor = _editor_shell_text()
    lifecycle = _lifecycle_text()

    assert "studio.gicleeframe.shell.deferred_editor" in editor
    assert "GICLEE_GF_LAZY_SHELL" in lifecycle
    assert "studio.gicleeframe.shell.critical_ready" in lifecycle
    assert "studio.gicleeframe.shell.deferred_control" in lifecycle
    assert "studio.gicleeframe.f1.lazy_collapsed" in lifecycle
    assert "studio.gicleeframe.f1.build_on_expand" in lifecycle
    assert "_progressive_boot_enabled()" in host


def test_lazy_shell_does_not_auto_defer_f1_build() -> None:
    text = _lifecycle_text()

    lazy_block = text.split("if _lazy_shell_enabled():", 1)[1].split("\n        else:", 1)[0]
    assert "after(_GF_F1_DEFER_MS, self._build_f1_brand_section_deferred)" not in lazy_block
