from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_gicleeframe_section_list_uses_smaller_batches() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_GF_SECTION_BATCH_SIZE = 3" in text or "_GF_SECTION_BATCH_SIZE = 2" in text
    assert "_GF_SECTION_BATCH_DELAY_MS = 16" in text


def test_gicleeframe_editor_and_control_are_micro_deferred() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "studio.gicleeframe.editor.skeleton_ready" in text
    assert "studio.gicleeframe.editor.deferred_fields" in text
    assert "studio.gicleeframe.control.skeleton_ready" in text
    assert "studio.gicleeframe.control.deferred_safety" in text
