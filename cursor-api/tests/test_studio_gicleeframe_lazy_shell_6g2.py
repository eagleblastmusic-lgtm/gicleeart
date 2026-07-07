from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_gicleeframe_has_lazy_shell() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_GF_LAZY_SHELL" in text
    assert "studio.gicleeframe.shell.critical_ready" in text
    assert "studio.gicleeframe.shell.deferred_editor" in text
    assert "studio.gicleeframe.shell.deferred_control" in text
    assert "studio.gicleeframe.f1.lazy_collapsed" in text
    assert "studio.gicleeframe.f1.build_on_expand" in text


def test_lazy_shell_does_not_auto_defer_f1_build() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    lazy_block = text.split("if _lazy_shell_enabled():", 1)[1].split("\n        else:", 1)[0]
    assert "after(_GF_F1_DEFER_MS, self._build_f1_brand_section_deferred)" not in lazy_block
