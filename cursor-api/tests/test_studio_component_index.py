"""Testy StudioComponentIndex — jednorazowy discover."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.component_index import StudioComponentIndex


def test_build_discovers_once() -> None:
    with patch("giclee_app.studio.component_index.discover_components") as mock_disc:
        mock_disc.return_value = []
        StudioComponentIndex.build()
        assert mock_disc.call_count == 1


def test_component_counts_from_index() -> None:
    idx = StudioComponentIndex.build()
    total, visible = idx.component_counts()
    assert total >= visible
    assert total == len(idx.all_components)
    assert visible == len(idx.visible_components)
