from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_katalog_refresh_is_deferred() -> None:
    path = ROOT / "giclee_app" / "ui" / "katalog_view.py"
    text = path.read_text(encoding="utf-8")

    init_block = text.split("def __init__", 1)[1].split("\n    def ", 1)[0]
    assert "_refresh_all()" not in init_block
    assert "after(" in text
    assert "studio.katalog.refresh_pipeline.start" in text
    assert 'event_prefix = f"studio.katalog.refresh.{kind}_rows"' in text
    assert 'f"{event_prefix}.batch"' in text
    assert 'f"{event_prefix}.done"' in text
    assert '"inventory",' in text
    assert '"data_map",' in text
    assert "studio.katalog.refresh.finalize" in text
    assert "_KATALOG_ROW_BATCH_SIZE" in text
    assert "_fill_rows_batch" in text
    assert "studio.katalog.refresh_pipeline.done" in text


def test_launcher_caches_katalog_view() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    block = text.split("def _show_katalog_shell", 1)[1].split("\n    def ", 1)[0]
    assert "cache_hit" in block
    assert 'self._view_cache["katalog"]' in block or "self._view_cache[key]" in block
    assert ".destroy()" not in block


def test_gicleeframe_has_cold_open_breakdown_spans() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "studio.gicleeframe.build.context_bar" in text
    assert "studio.gicleeframe.build.workspace" in text
    assert "studio.gicleeframe.inventory.render_section_list" in text
    assert "studio.gicleeframe.inventory.initial_selection" in text
