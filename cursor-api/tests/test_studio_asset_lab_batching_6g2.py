from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_asset_lab_uses_small_batches_after_first_paint() -> None:
    path = ROOT / "giclee_app" / "ui" / "asset_lab_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_ASSET_LAB_RENDER_BATCH_SIZE = 1" in text
    assert "_ASSET_LAB_FIRST_BATCH_DELAY_MS" in text
    assert "studio.asset_lab.render_cards.shell_batch" in text
    assert "studio.asset_lab.card.shell_created" in text
