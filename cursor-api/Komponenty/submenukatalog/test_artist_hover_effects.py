"""Testy kontraktu efektów aktywnego artysty w Submenu katalog."""

from __future__ import annotations

import copy
import unittest
from types import SimpleNamespace

from Komponenty._shared.theme_page_editor import gui_shell
from Komponenty._shared.theme_page_editor.service_base import apply_zone_values, load_zone_values
from Komponenty.submenukatalog.effects import (
    ARTIST_HOVER_EFFECT_FIELD_ID,
    ARTIST_HOVER_EFFECT_OPTIONS,
    DEFAULT_ARTIST_HOVER_EFFECT,
    normalize_artist_hover_effect,
)
from Komponenty.submenukatalog.gui import _install_section_effects_asset_guard
from Komponenty.submenukatalog.registry import PAGE_ZONES


class ArtistHoverEffectsTests(unittest.TestCase):
    def test_effect_catalog_has_five_unique_ids(self) -> None:
        ids = [effect_id for effect_id, _label in ARTIST_HOVER_EFFECT_OPTIONS]
        self.assertEqual(
            ids,
            [
                "classic",
                "curatorial_glow",
                "depth_of_field",
                "museum_marker",
                "preview_focus",
            ],
        )
        self.assertEqual(len(ids), len(set(ids)))

    def test_missing_and_unknown_values_fall_back_to_classic(self) -> None:
        self.assertEqual(normalize_artist_hover_effect(None), DEFAULT_ARTIST_HOVER_EFFECT)
        self.assertEqual(normalize_artist_hover_effect(""), DEFAULT_ARTIST_HOVER_EFFECT)
        self.assertEqual(
            normalize_artist_hover_effect("not-supported"),
            DEFAULT_ARTIST_HOVER_EFFECT,
        )

    def test_supported_value_is_preserved(self) -> None:
        self.assertEqual(normalize_artist_hover_effect("museum_marker"), "museum_marker")
        self.assertEqual(normalize_artist_hover_effect(" preview_focus "), "preview_focus")

    def test_effect_field_is_between_header_and_hidden_artists(self) -> None:
        list_zone = next(zone for zone in PAGE_ZONES if zone.zone_id == "list")
        field_ids = [field.field_id for field in list_zone.fields]
        self.assertEqual(
            field_ids,
            [
                "columns",
                "show_header",
                ARTIST_HOVER_EFFECT_FIELD_ID,
                "hidden_artists_text",
            ],
        )
        effect_field = next(
            field for field in list_zone.fields if field.field_id == ARTIST_HOVER_EFFECT_FIELD_ID
        )
        self.assertEqual(effect_field.path, ("list", ARTIST_HOVER_EFFECT_FIELD_ID))

    def test_hidden_artist_handles_roundtrip_as_plain_multiline_text(self) -> None:
        list_zone = next(zone for zone in PAGE_ZONES if zone.zone_id == "list")
        hidden_field = next(
            field for field in list_zone.fields if field.field_id == "hidden_artists_text"
        )
        self.assertEqual(hidden_field.kind, "text")

        handles = "claude-monet\nthomas-moran\nrafael-santi"
        template = {
            "version": 1,
            "list": {
                "columns": 3,
                "show_header": True,
                "artist_hover_effect": "curatorial_glow",
                "hidden_artists_text": handles,
            },
        }
        values = load_zone_values(template, list_zone)
        self.assertEqual(values["hidden_artists_text"], handles)

        pending = copy.deepcopy(template)
        apply_zone_values(pending, list_zone, values)
        self.assertEqual(pending["list"]["hidden_artists_text"], handles)
        self.assertNotIn("<p>", pending["list"]["hidden_artists_text"])
        self.assertNotIn("<br", pending["list"]["hidden_artists_text"])

    def test_save_guard_skips_only_catalog_section_effects_asset(self) -> None:
        original = gui_shell.write_page_section_effects_asset
        calls: list[tuple[str, str]] = []

        def fake_writer(config: object, variant_id: str) -> str:
            component_id = str(getattr(config, "component_id", ""))
            calls.append((component_id, variant_id))
            return "written"

        gui_shell.write_page_section_effects_asset = fake_writer
        try:
            _install_section_effects_asset_guard()
            guarded = gui_shell.write_page_section_effects_asset

            self.assertIsNone(
                guarded(SimpleNamespace(component_id="submenukatalog"), "sk2")
            )
            self.assertEqual(calls, [])

            self.assertEqual(
                guarded(SimpleNamespace(component_id="faq"), "fq1"),
                "written",
            )
            self.assertEqual(calls, [("faq", "fq1")])

            _install_section_effects_asset_guard()
            self.assertIs(gui_shell.write_page_section_effects_asset, guarded)
        finally:
            gui_shell.write_page_section_effects_asset = original


if __name__ == "__main__":
    unittest.main()
