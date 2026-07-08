from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _method_body(text: str, method_name: str) -> str:
    marker = f"def {method_name}(\n"
    if marker not in text:
        marker = f"def {method_name}("
    block = text.split(marker, 1)[1]
    return block.split("\n    def ", 1)[0]


def test_gicleeframe_logs_fields_lazy_startup() -> None:
    text = _view_text()
    assert "studio.gicleeframe.editor.fields_lazy_startup" in text


def test_form_shell_does_not_chain_editor_fields() -> None:
    text = _view_text()
    body = _method_body(text, "_micro_deferred_editor_form_shell")
    assert "_micro_deferred_editor_fields" not in body


def test_lazy_editor_row_helpers_exist() -> None:
    text = _view_text()
    helpers = (
        "_ensure_title_row_built",
        "_ensure_text_row_built",
        "_ensure_alt_row_built",
        "_ensure_image_ref_row_built",
        "_ensure_notes_row_built",
        "_ensure_children_overview_built",
        "_ensure_page_context_shell_built",
        "_ensure_editor_rows_for_fields",
    )
    for helper in helpers:
        assert helper in text, f"missing helper {helper}"


def test_populate_editor_ensures_lazy_rows() -> None:
    text = _view_text()
    body = _method_body(text, "_populate_editor")
    assert "fields = editor_field_visibility(etype)" in body
    fields_idx = body.index("fields = editor_field_visibility(etype)")
    ensure_idx = body.index("_ensure_minimal_editor_rows_for_fields(fields)")
    assert ensure_idx > fields_idx


def test_lazy_editor_init_flags_exist() -> None:
    text = _view_text()
    init_block = text.split("def __init__", 1)[1].split("\n    def ", 1)[0]
    flags = (
        "_editor_form_shell_ready",
        "_editor_placeholder_label",
        "_title_row_built",
        "_text_row_built",
        "_alt_row_built",
        "_image_ref_row_built",
        "_notes_row_built",
        "_children_overview_built",
        "_page_context_shell_built",
    )
    for flag in flags:
        assert flag in init_block, f"missing init flag {flag}"
