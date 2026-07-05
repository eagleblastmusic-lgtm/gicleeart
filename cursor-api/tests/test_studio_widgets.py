"""Testy widgetów Studio — brak odczytu dysku per karta."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_component_card_does_not_read_component_json() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")
    assert "_is_hidden" not in text
    assert "component.json" not in text
    assert "comp.hidden" in text


def test_component_card_uses_theme_font_cache() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")
    assert "theme.get_font" in text
    assert "CTkFont(" not in text


def test_stat_card_no_tkfont_families() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")
    assert "tkfont" not in text
    assert "families()" not in text
