from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_launcher_has_idle_prewarm_queue() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_STUDIO_IDLE_PREWARM" in text
    assert "_studio_idle_prewarm_enabled" in text
    assert "default=False" in text
    assert "studio.prewarm.view_started" in text
    assert "studio.prewarm.cancelled_due_user_action" in text
    assert "studio.prewarm.start" in text
    assert "studio.prewarm.view_done" in text


def test_prewarm_does_not_include_gicleeframe() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    prewarm_block = text.split("def _prewarm_next_step", 1)[1].split("\n    def ", 1)[0]
    assert "gicleeframe" not in prewarm_block
    assert "hub:theme" in prewarm_block
    assert "hub:products" in prewarm_block
    assert "katalog" in prewarm_block


def test_asset_lab_renders_cards_deferred() -> None:
    path = ROOT / "giclee_app" / "ui" / "asset_lab_view.py"
    text = path.read_text(encoding="utf-8")

    assert "studio.asset_lab.visual.shell_ready" in text
    assert "studio.asset_lab.render_cards.shell_batch" in text
    assert "studio.asset_lab.visual.full_ready" in text
    assert "after(" in text
