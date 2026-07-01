"""Testy edytowalnej tabeli szablonow paczek."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib  # noqa: E402
import json  # noqa: E402


def _fresh_module(tmp_path):
    """Laduje package_templates z podstawionym katalogiem dane/."""
    from Komponenty.produkcja import package_templates as pt

    pt._DATA_DIR = tmp_path
    pt._FILE = tmp_path / "package_templates.json"
    return pt


class TestLoadSeed:
    def test_seeds_defaults_when_missing(self, tmp_path):
        pt = _fresh_module(tmp_path)
        items = pt.load_templates()
        keys = {t.key for t in items}
        assert "DAB M" in keys
        assert "SOSNA XL" in keys
        assert (tmp_path / "package_templates.json").is_file()


class TestUpsertAndDelete:
    def test_upsert_creates_and_updates(self, tmp_path):
        pt = _fresh_module(tmp_path)
        pt.upsert_template(
            "DAB M", length_cm=70, width_cm=50, height_cm=10, weight_kg=4
        )
        t = pt.get_template("DAB M")
        assert t is not None
        assert t.length_cm == 70
        assert t.weight_kg == 4
        # Upsert case insensitive
        pt.upsert_template(
            "dab m", length_cm=72, width_cm=50, height_cm=10, weight_kg=4
        )
        t = pt.get_template("DAB M")
        assert t is not None
        assert t.length_cm == 72

    def test_delete(self, tmp_path):
        pt = _fresh_module(tmp_path)
        pt.upsert_template(
            "TEST X", length_cm=1, width_cm=1, height_cm=1, weight_kg=1
        )
        assert pt.get_template("TEST X") is not None
        assert pt.delete_template("TEST X") is True
        assert pt.get_template("TEST X") is None

    def test_formatted_for_key(self, tmp_path):
        pt = _fresh_module(tmp_path)
        pt.upsert_template(
            "DAB L", length_cm=85, width_cm=65, height_cm=10, weight_kg=5
        )
        s = pt.formatted_for_key("DAB L")
        assert "85" in s and "65" in s and "5" in s

    def test_reset_to_defaults(self, tmp_path):
        pt = _fresh_module(tmp_path)
        pt.upsert_template(
            "CUSTOM X", length_cm=1, width_cm=1, height_cm=1, weight_kg=1
        )
        pt.reset_to_defaults()
        keys = {t.key for t in pt.load_templates()}
        assert "CUSTOM X" not in keys
        assert "DAB M" in keys


class TestShippingIntegration:
    def test_shipping_suggested_uses_templates(self, tmp_path, monkeypatch):
        pt = _fresh_module(tmp_path)
        pt.upsert_template(
            "DAB M", length_cm=60, width_cm=45, height_cm=10, weight_kg=3
        )
        from Komponenty.produkcja import shipping
        importlib.reload(shipping)
        # shipping._suggested_dimensions nazywa package_templates.formatted_for_key
        assert "60" in shipping._suggested_dimensions("DAB M")
        assert "60" in shipping._suggested_dimensions("DAB S")
        assert shipping._suggested_dimensions("NIEZNANY X") == ""
