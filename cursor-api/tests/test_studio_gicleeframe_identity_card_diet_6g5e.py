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


def test_identity_card_late_build_constants_and_methods_exist() -> None:
    text = _editor_shell_text()
    assert "_GF_EDITOR_IDENTITY_LATE_DEFER_MS" in text
    assert "_schedule_editor_identity_late_build" in text
    assert "_build_editor_identity_late" in text
    assert "_build_section_identity_placeholder" in text


def test_identity_card_lazy_startup_events_exist() -> None:
    text = _editor_shell_text()
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in text
    assert "studio.gicleeframe.editor.identity_card_late_start" in text
    assert "studio.gicleeframe.editor.identity_card_late_done" in text
    assert "studio.gicleeframe.build.editor_column.identity_card_late" in text


def test_startup_skeleton_uses_placeholder_not_full_identity_card() -> None:
    text = _editor_shell_text()

    start = text.index("def _micro_deferred_editor_skeleton")
    end = text.index("def _build_section_identity_placeholder")
    body = text[start:end]

    assert "_build_section_identity_placeholder" in body
    assert "_build_section_identity_card" not in body


def test_identity_card_diet_preserves_prior_6g5_optimizations() -> None:
    editor_text = _editor_shell_text()
    lifecycle_text = _lifecycle_text()
    assert "studio.gicleeframe.editor.fields_lazy_startup" in editor_text
    assert "studio.gicleeframe.control.deferred_readiness_late" in lifecycle_text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in editor_text
    assert "studio.gicleeframe.build.editor_column.skeleton.identity_card" in editor_text
