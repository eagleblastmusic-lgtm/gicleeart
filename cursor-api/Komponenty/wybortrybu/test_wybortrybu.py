"""Testy logiki Wybor Trybu (bez GUI)."""

from __future__ import annotations

import unittest

from Komponenty.wybortrybu.data_loader import filter_modes, load_catalog
from Komponenty.wybortrybu.import_from_xlsx import import_from_xlsx
from Komponenty.wybortrybu.prompt_builder import full_prompt_for_modes, short_prompt_for_modes


class WyborTrybuDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()

    def test_catalog_has_ten_modes(self) -> None:
        self.assertEqual(len(self.catalog.modes), 10)

    def test_catalog_has_six_combinations(self) -> None:
        self.assertEqual(len(self.catalog.combinations), 6)

    def test_all_combination_mode_ids_resolve(self) -> None:
        for combo in self.catalog.combinations:
            self.assertTrue(combo.mode_ids, combo.name)
            for mode_id in combo.mode_ids:
                self.assertIsNotNone(self.catalog.mode(mode_id), f"{combo.name} -> {mode_id}")

    def test_filter_by_category(self) -> None:
        ui_modes = filter_modes(self.catalog, category="UI")
        self.assertEqual(len(ui_modes), 1)
        self.assertEqual(ui_modes[0].id, "gui_ui_premium")

    def test_filter_by_query(self) -> None:
        found = filter_modes(self.catalog, query="shopify")
        self.assertTrue(any(m.id == "shopify_snapshot_reviewer" for m in found))

    def test_short_command_for_single_mode(self) -> None:
        mode = self.catalog.mode("gui_ui_premium")
        assert mode is not None
        from Komponenty.wybortrybu.prompt_builder import short_command_for_mode

        self.assertEqual(short_command_for_mode(mode), "TRYB GUI Premium")
        self.assertNotEqual(short_command_for_mode(mode), mode.sample_command)

        modes = self.catalog.modes_for_ids(["gui_ui_premium", "motion_director"])
        text = short_prompt_for_modes(modes)
        self.assertIn("GUI Premium", text)
        self.assertIn("Motion Director", text)
        self.assertTrue(text.startswith("TRYB "))

    def test_prompt_builder_full_contains_rules(self) -> None:
        modes = self.catalog.modes_for_ids(["code_aware_reviewer"])
        text = full_prompt_for_modes(modes)
        self.assertIn("Pracuj w trybie:", text)
        self.assertIn("Zasady:", text)
        self.assertIn("Przykładowe komendy:", text)

    def test_import_from_default_source(self) -> None:
        stats = import_from_xlsx()
        self.assertEqual(stats["modes"], 10)
        self.assertEqual(stats["combinations"], 6)


if __name__ == "__main__":
    unittest.main()
