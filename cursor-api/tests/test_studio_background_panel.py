"""Testy Background Panel Shell (F4.2) + handoff (F4.3a) — pure / source inspection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_capabilities import capability_for, tier_display
from giclee_app.studio.background_draft_preview import PREVIEW_SECTION_TITLE, preview_enabled_for_folder
from giclee_app.studio.background_draft_state import (
    CLEAR_DRAFT_LABEL,
    DRAFT_SECTION_TITLE,
    draft_enabled_for_folder,
)
from giclee_app.studio.background_save_contract import (
    CHECK_SAVE_LABEL,
    DRY_RUN_BADGE,
    SAVE_PLAN_SECTION_TITLE,
    save_plan_enabled_for_folder,
)
from giclee_app.studio.background_save_readiness import (
    F54B0_DISCLAIMER,
    READINESS_SECTION_LABEL,
)
from giclee_app.ui.background_panel import (
    _HANDOFF_BUTTON_LABEL,
    panel_rows,
)


def test_panel_rows_tldobio_read_only(tmp_path: Path) -> None:
    cap = capability_for("tldobio")
    assert cap is not None
    rows = dict(
        panel_rows(
            cap,
            component_name="Tło do Bio",
            folder_name="tldobio",
            package_path=tmp_path,
        )
    )
    assert "Typ tła" in rows
    assert cap.label in rows["Typ tła"]
    assert tier_display("bio_workflow") in rows["Typ tła"]
    assert "Aktualny stan" in rows
    assert "Brak lokalnego cache" in rows["Aktualny stan"]
    assert rows["Status"] == "read-only"
    assert _HANDOFF_BUTTON_LABEL in rows["Co dalej"]
    assert cap.inline_note in rows["Kontekst inline"]
    assert "Biblioteka / Assety" not in rows


def test_panel_rows_stronaglowna(tmp_path: Path) -> None:
    cap = capability_for("stronaglowna")
    assert cap is not None
    rows = dict(
        panel_rows(
            cap,
            component_name="Strona główna",
            folder_name="stronaglowna",
            package_path=tmp_path,
        )
    )
    assert tier_display("section_background") in rows["Typ tła"]
    assert cap.source_hint in rows["Źródło"]
    assert "Aktualny stan" in rows
    assert "Biblioteka / Assety" in rows
    assert "F5.1b · read-only" in rows["Biblioteka / Assety"]
    assert "kolaż wideo" in rows["Biblioteka / Assety"]


def test_capability_for_katalog_no_panel() -> None:
    assert capability_for("katalog") is None


def test_launcher_studio_has_background_panel_routing() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    assert "_show_background_panel" in text
    assert "_return_from_background_panel" in text
    assert "_destroy_background_host" in text
    assert "BackgroundPanelView" in text
    return_block = text.split("def _return_from_background_panel")[1].split("\n    def ")[0]
    assert "_show_hub(category)" in return_block
    assert "_apply_inline_window_size" not in text.split("def _show_background_panel")[1].split(
        "\n    def "
    )[0]


def test_component_hub_wires_background_callback() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "on_open_background" in text
    assert "_on_background_click" in text
    assert "capability_for(comp.folder_name) is None" in text


def test_component_card_has_separate_tlo_button() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")
    card_block = text.split("class ComponentCard")[1].split("\nclass ")[0]
    assert "on_open_background" in card_block
    assert 'text="Tło"' in card_block
    assert "command=lambda c=comp: on_open_background(c)" in card_block


def test_escape_back_handles_background_before_inline() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    escape_block = text.split("def _on_escape_back")[1].split("\n    def ")[0]
    assert "_background_host is not None" in escape_block
    assert "_return_from_background_panel()" in escape_block


def test_panel_rows_stronaglowna_no_draft_in_readonly_rows(tmp_path: Path) -> None:
    cap = capability_for("stronaglowna")
    assert cap is not None
    rows = dict(
        panel_rows(
            cap,
            component_name="Strona główna",
            folder_name="stronaglowna",
            package_path=tmp_path,
        )
    )
    assert DRAFT_SECTION_TITLE not in rows
    assert PREVIEW_SECTION_TITLE not in rows
    assert SAVE_PLAN_SECTION_TITLE not in rows
    assert "Draft lokalny" not in "\n".join(rows.values())
    assert "niezastosowany" not in "\n".join(rows.values())


def test_preview_section_only_for_stronaglowna_in_panel_source() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"
    text = path.read_text(encoding="utf-8")
    assert "PREVIEW_SECTION_TITLE" in text
    assert "_render_preview_section" in text
    assert preview_enabled_for_folder("stronaglowna")
    assert not preview_enabled_for_folder("tldobio")


def test_save_plan_section_only_for_stronaglowna_in_panel_source() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"
    text = path.read_text(encoding="utf-8")
    assert "SAVE_PLAN_SECTION_TITLE" in text
    assert "_render_save_plan_section" in text
    assert "CHECK_SAVE_LABEL" in text
    assert "DRY_RUN_BADGE" in text
    assert save_plan_enabled_for_folder("stronaglowna")
    assert not save_plan_enabled_for_folder("tldobio")
    assert "SAVE_LOCAL_LABEL" in text
    assert 'text="Zapisz"' not in text


def test_save_plan_has_readiness_ui() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"
    text = path.read_text(encoding="utf-8")
    assert "evaluate_save_readiness" in text
    assert "format_readiness_block" in text
    assert "F54B0_DISCLAIMER" in text
    assert "F54B1_FUTURE_NOTE" in text
    assert "evaluate_save_readiness" in text
    assert "SAVE_LOCAL_LABEL" in text
    assert "clear_section_background_with_backup" in text


def test_draft_section_only_for_stronaglowna_in_panel_source() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"
    text = path.read_text(encoding="utf-8")
    assert "DRAFT_SECTION_TITLE" in text
    assert "_render_draft_section" in text
    assert "draft_enabled_for_folder" in text
    assert draft_enabled_for_folder("stronaglowna")
    assert not draft_enabled_for_folder("tldobio")


def test_background_panel_has_handoff_callback_and_button() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"
    text = path.read_text(encoding="utf-8")
    assert "on_open_inline" in text
    assert _HANDOFF_BUTTON_LABEL in text
    assert 'self._comp.mode == "inline"' in text
    assert "CLEAR_DRAFT_LABEL" in text
    assert "DRAFT_DISCLAIMER" in text
    assert "PREVIEW_DISCLAIMER" in text
    assert "Zastosuj" not in text


def test_handoff_uses_show_inline_component_and_destroy_background() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    assert "_handoff_background_to_inline" in text
    handoff_block = text.split("def _handoff_background_to_inline")[1].split("\n    def ")[0]
    assert "_show_inline_component(comp, category)" in handoff_block
    assert "_background_return_category" in handoff_block
    assert "_inline_stack" not in handoff_block
    inline_block = text.split("def _show_inline_component")[1].split("\n    def ")[0]
    assert "_destroy_background_host()" in inline_block
    show_bg_block = text.split("def _show_background_panel")[1].split("\n    def ")[0]
    assert "on_open_inline=" in show_bg_block
    assert "_handoff_background_to_inline" in show_bg_block
