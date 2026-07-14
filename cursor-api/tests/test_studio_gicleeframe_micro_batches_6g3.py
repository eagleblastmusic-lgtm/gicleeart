from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _constant_int(text: str, name: str) -> int:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(\d+)$", text, re.MULTILINE)
    assert match is not None, f"missing integer constant: {name}"
    return int(match.group(1))


def test_gicleeframe_section_list_uses_bounded_progressive_batches() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    shell_path = ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    text = path.read_text(encoding="utf-8")
    shell_text = shell_path.read_text(encoding="utf-8")

    first_batch = _constant_int(shell_text, "_GF_SECTION_FIRST_BATCH_SIZE")
    steady_batch = _constant_int(text, "_GF_SECTION_BATCH_SIZE")
    delay_ms = _constant_int(text, "_GF_SECTION_BATCH_DELAY_MS")

    assert 1 <= first_batch <= steady_batch <= 12
    assert 0 <= delay_ms <= 16


def test_gicleeframe_editor_and_control_are_micro_deferred() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "studio.gicleeframe.editor.skeleton_ready" in text
    assert "studio.gicleeframe.editor.deferred_fields" in text
    assert "studio.gicleeframe.control.skeleton_ready" in text
    assert "studio.gicleeframe.control.deferred_safety" in text
