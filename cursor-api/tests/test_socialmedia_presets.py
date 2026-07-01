"""Testy biblioteki presetow generatora tresci."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _fresh(tmp_path):
    from Komponenty.socialmedia import presets
    presets._DATA_DIR = tmp_path
    presets._FILE = tmp_path / "content_presets.json"
    return presets


class TestAddAndLoad:
    def test_roundtrip(self, tmp_path):
        presets = _fresh(tmp_path)
        p = presets.Preset.new(
            name="Moj IG/FB",
            platforms=["ig_feed", "fb"],
            language="pl",
            tone="Ton ciepły, krótki",
            topic="jesien",
        )
        presets.add_preset(p)
        loaded = presets.load_presets()
        assert len(loaded) == 1
        assert loaded[0].name == "Moj IG/FB"
        assert loaded[0].platforms == ["ig_feed", "fb"]
        assert loaded[0].tone.startswith("Ton")

    def test_update_and_delete(self, tmp_path):
        presets = _fresh(tmp_path)
        p = presets.Preset.new(name="X", platforms=["ig_feed"])
        presets.add_preset(p)
        assert presets.update_preset(p.id, tone="nowy ton") is not None
        t = presets.get_preset(p.id)
        assert t is not None and t.tone == "nowy ton"
        assert presets.delete_preset(p.id) is True
        assert presets.get_preset(p.id) is None

    def test_series_count_clamp(self, tmp_path):
        presets = _fresh(tmp_path)
        p = presets.Preset.new(name="X", platforms=["ig_feed"], mode="series", series_count=42)
        assert p.series_count <= 7
        p2 = presets.Preset.new(name="Y", platforms=["ig_feed"], mode="series", series_count=1)
        assert p2.series_count >= 2
