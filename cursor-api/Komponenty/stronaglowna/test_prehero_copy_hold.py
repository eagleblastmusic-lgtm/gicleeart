from __future__ import annotations

from pathlib import Path


ASSET_PATH = (
    Path(__file__).resolve().parents[3] / "assets" / "giclee-home-prehero-reveal.js"
)


def test_prehero_copy_holds_until_late_reveal_progress() -> None:
    source = ASSET_PATH.read_text(encoding="utf-8")

    assert "rangeProgress(eased, 0.90, 0.995)" in source
    assert "rangeProgress(eased, 0.76, 0.95)" not in source
