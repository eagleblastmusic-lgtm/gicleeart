"""Testy logiki Wybor Trybu (bez GUI)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Komponenty.wybortrybu.data_loader import (
    SHOPIFY_SNAPSHOT_MODE_ID,
    filter_modes,
    load_catalog,
    resolve_modes_with_dependencies,
)
from Komponenty.wybortrybu.import_from_xlsx import import_from_xlsx, parse_xlsx
from Komponenty.wybortrybu.knowledge_sources import check_knowledge_sources
from Komponenty.wybortrybu.prompt_builder import (
    VEO_MODE_ID,
    command_for_mode,
    full_prompt_for_modes,
    short_prompt_for_modes,
)


class WyborTrybuDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.data_dir = Path(__file__).resolve().parent / "data"
        cls.runtime_modes_mtime = (cls.data_dir / "work_modes.json").stat().st_mtime

    def test_catalog_schema_v2(self) -> None:
        self.assertEqual(self.catalog.schema_version, 2)
        self.assertEqual(self.catalog.knowledge_pack, "v37")

    def test_seventeen_formal_modes(self) -> None:
        formal = self.catalog.formal_modes()
        self.assertEqual(len(formal), 17)
        analyst = [m for m in formal if m.family == "analyst"]
        shopify = [m for m in formal if m.family == "shopify"]
        self.assertEqual(len(analyst), 8)
        self.assertEqual(len(shopify), 9)

    def test_foundations_present_and_not_selectable(self) -> None:
        self.assertEqual(len(self.catalog.foundations), 3)
        ids = {f.id for f in self.catalog.foundations}
        self.assertEqual(ids, {"instructions_v37", "current_app_state", "analyst_base"})
        for foundation in self.catalog.foundations:
            self.assertFalse(foundation.selectable)

    def test_gicleeapp_architect_alias_on_foundation(self) -> None:
        base = self.catalog.foundation("analyst_base")
        assert base is not None
        self.assertIn("GicleeApp Architect", base.aliases)
        for mode in self.catalog.modes:
            self.assertNotIn("GicleeApp Architect", mode.aliases)

    def test_workflow_and_legacy_not_formal(self) -> None:
        workflow = self.catalog.mode("cursor_prompt_architect")
        legacy = self.catalog.mode("medyczny_ostrozny")
        assert workflow is not None
        assert legacy is not None
        self.assertFalse(workflow.is_formal)
        self.assertFalse(legacy.is_formal)

    def test_all_combination_mode_ids_resolve(self) -> None:
        for combo in self.catalog.combinations:
            self.assertTrue(combo.mode_ids, combo.name)
            for mode_id in combo.mode_ids:
                self.assertIsNotNone(self.catalog.mode(mode_id), f"{combo.name} -> {mode_id}")

    def test_seven_combinations_no_stored_prompts(self) -> None:
        self.assertEqual(len(self.catalog.combinations), 7)
        raw = json.loads((self.data_dir / "combinations.json").read_text(encoding="utf-8"))
        for row in raw["combinations"]:
            self.assertNotIn("prompt_short", row)
            self.assertNotIn("prompt_full", row)

    def test_veo_activation_commands(self) -> None:
        veo = self.catalog.mode("analyst_veo_flow_director")
        assert veo is not None
        commands = {p.id: p.command for p in veo.activation_profiles}
        self.assertEqual(commands["veo_premium"], "Veo premium")
        self.assertEqual(commands["veo_krotko"], "Veo krótko")
        self.assertEqual(commands["veo_popraw"], "Veo popraw")
        self.assertEqual(commands["tryb_flow"], "TRYB FLOW")
        self.assertEqual(commands["tryb_image_prompt"], "TRYB IMAGE PROMPT")
        self.assertEqual(commands["tryb_image_video_prompt"], "TRYB IMAGE-VIDEO PROMPT")

    def test_search_by_alias_command_and_source_file(self) -> None:
        by_alias = filter_modes(self.catalog, query="Motion Director")
        self.assertTrue(any(m.id == "shopify_motion_interaction" for m in by_alias))

        by_command = filter_modes(self.catalog, query="Tryb Performance")
        self.assertTrue(any(m.id == "analyst_performance" for m in by_command))

        by_file = filter_modes(self.catalog, query="GICLEE_SHOPIFY_MODE_SEO_CONTENT")
        self.assertTrue(any(m.id == "shopify_seo_content" for m in by_file))

    def test_shopify_snapshot_auto_included(self) -> None:
        modes, _ = resolve_modes_with_dependencies(
            self.catalog, ["shopify_homepage_art_direction"]
        )
        ids = [m.id for m in modes]
        self.assertIn(SHOPIFY_SNAPSHOT_MODE_ID, ids)
        self.assertEqual(ids.count(SHOPIFY_SNAPSHOT_MODE_ID), 1)

    def test_shopify_snapshot_in_short_prompt(self) -> None:
        text = short_prompt_for_modes(self.catalog, ["shopify_motion_interaction"])
        lines = text.strip().split("\n")
        self.assertIn("Tryb Motion", lines)
        self.assertIn("Tryb Shopify Snapshot", lines)
        self.assertEqual(lines.count("Tryb Shopify Snapshot"), 1)

    def test_veo_motion_split_in_full_prompt(self) -> None:
        text = full_prompt_for_modes(
            self.catalog, [VEO_MODE_ID, "shopify_motion_interaction"]
        )
        self.assertIn("Rozdziel zadanie", text)
        self.assertIn("generowanie assetu/wideo", text)
        self.assertIn("motion strony Shopify", text)

    def test_prompt_determinism_across_input_order(self) -> None:
        ids_a = ["shopify_product_page_pdp", "shopify_conversion_trust", "shopify_copy_brand_story"]
        ids_b = list(reversed(ids_a))
        full_a = full_prompt_for_modes(self.catalog, ids_a)
        full_b = full_prompt_for_modes(self.catalog, ids_b)
        short_a = short_prompt_for_modes(self.catalog, ids_a)
        short_b = short_prompt_for_modes(self.catalog, ids_b)
        self.assertEqual(full_a, full_b)
        self.assertEqual(short_a, short_b)
        for marker in (
            "Fundament (zawsze):",
            "GICLEE_ANALYST_BASE_PROMPT_v1.md",
            "Tryb Shopify Snapshot",
            "[Wklej zadanie]",
        ):
            self.assertIn(marker, full_a)
        snapshot_lines = [ln for ln in full_a.split("\n") if "SHOPIFY_SNAPSHOT" in ln or "Shopify Snapshot" in ln]
        self.assertTrue(snapshot_lines)

    def test_compact_activation_commands_not_h1(self) -> None:
        perf = self.catalog.mode("analyst_performance")
        assert perf is not None
        self.assertEqual(command_for_mode(perf), "Tryb Performance")
        self.assertNotIn("—", command_for_mode(perf))

    def test_knowledge_sources_temp_dir_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            starter = Path(tmp)
            for mode in self.catalog.formal_modes():
                (starter / mode.source_file).write_text("# stub\n", encoding="utf-8")
            result = check_knowledge_sources(self.catalog, starter_dir=starter)
            self.assertEqual(result.status, "current")
            self.assertEqual(result.missing_files, ())
            self.assertEqual(result.unknown_files, ())

    def test_knowledge_sources_drift_missing_and_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            starter = Path(tmp)
            formal = list(self.catalog.formal_modes())
            for mode in formal[:-1]:
                (starter / mode.source_file).write_text("# stub\n", encoding="utf-8")
            (starter / "GICLEE_ANALYST_MODE_FUTURE_v2.md").write_text("# new\n", encoding="utf-8")
            result = check_knowledge_sources(self.catalog, starter_dir=starter)
            self.assertEqual(result.status, "drift")
            self.assertTrue(result.missing_files)
            self.assertTrue(result.unknown_files)

    def test_knowledge_sources_unavailable(self) -> None:
        result = check_knowledge_sources(
            self.catalog, starter_dir=Path("/nonexistent/path/for/wybortrybu")
        )
        self.assertEqual(result.status, "unavailable")

    def test_broader_glob_detects_v2_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            starter = Path(tmp)
            for mode in self.catalog.formal_modes():
                alt = mode.source_file.replace("_v1.md", "_v2.md")
                (starter / alt).write_text("# v2\n", encoding="utf-8")
            result = check_knowledge_sources(self.catalog, starter_dir=starter)
            self.assertEqual(result.status, "drift")
            self.assertEqual(len(result.missing_files), 17)
            self.assertEqual(len(result.unknown_files), 17)

    def test_xlsx_parse_only_does_not_touch_runtime(self) -> None:
        stats = import_from_xlsx()
        self.assertEqual(stats["modes"], 10)
        self.assertEqual(stats["combinations"], 6)
        mtime_after = (self.data_dir / "work_modes.json").stat().st_mtime
        self.assertEqual(mtime_after, self.runtime_modes_mtime)

    def test_xlsx_write_requires_explicit_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "legacy_out"
            stats = import_from_xlsx(output_dir=out)
            self.assertEqual(stats["modes"], 10)
            self.assertTrue((out / "work_modes.json").is_file())
            payload = json.loads((out / "work_modes.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)

    def test_parse_xlsx_returns_data(self) -> None:
        parsed = parse_xlsx()
        self.assertEqual(len(parsed.modes), 10)
        self.assertEqual(len(parsed.combinations), 6)


if __name__ == "__main__":
    unittest.main()
