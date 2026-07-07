from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_gicleeframe_progressive_boot_flags_exist() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_GF_PROGRESSIVE_BOOT" in text
    assert "GICLEE_GF_EAGER_BOOT" in text
    assert "def _progressive_boot_enabled" in text


def test_gicleeframe_progressive_boot_uses_light_refresh() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def _refresh_inventory_light" in text
    assert "studio.gicleeframe.refresh_inventory.light" in text
    assert "studio.gicleeframe.inventory.light_ready" in text


def test_gicleeframe_progressive_boot_skips_initial_selection() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "initial_selection.skipped_progressive" in text
    assert "_show_editor_placeholder_state" in text


def test_gicleeframe_section_list_is_incremental() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def _render_section_list_incremental" in text
    assert "def _render_section_list_batch" in text
    assert "studio.gicleeframe.section_list.incremental_batch" in text


def test_gicleeframe_f1_brand_section_is_deferred() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "f1_brand_section.placeholder" in text
    assert "f1_brand_section.deferred" in text
