from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_asset_lab_full_cards_are_on_demand_by_default() -> None:
    path = ROOT / "giclee_app" / "ui" / "asset_lab_view.py"
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_ASSET_LAB_AUTO_FULL_CARDS" in text
    assert "full_auto_disabled" in text
    assert "full_requested" in text
    assert "full_created_on_demand" in text
