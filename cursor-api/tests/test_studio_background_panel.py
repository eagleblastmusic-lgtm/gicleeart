"""Testy Background Panel Shell (F4.2) — pure / source inspection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_capabilities import capability_for, tier_display
from giclee_app.ui.background_panel import panel_rows


def test_panel_rows_tldobio_read_only() -> None:
    cap = capability_for("tldobio")
    assert cap is not None
    rows = dict(panel_rows(cap, component_name="Tło do Bio"))
    assert "Typ tła" in rows
    assert cap.label in rows["Typ tła"]
    assert tier_display("bio_workflow") in rows["Typ tła"]
    assert rows["Status"] == "read-only"
    assert "F4.3" in rows["Co dalej"]
    assert cap.inline_note in rows["Kontekst inline"]


def test_panel_rows_stronaglowna() -> None:
    cap = capability_for("stronaglowna")
    assert cap is not None
    rows = dict(panel_rows(cap, component_name="Strona główna"))
    assert tier_display("section_background") in rows["Typ tła"]
    assert cap.source_hint in rows["Źródło"]


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
