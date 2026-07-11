"""Testy WS-1: zapis wariantu bez motywu i bounded apply."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.service_base import INDEX_HEADER
from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone
from Komponenty._shared.theme_page_editor import variants as varmod
from Komponenty._shared.theme_page_editor.writer_safety import (
    apply_bounded_plan,
    build_bounded_apply_plan,
    install_writer_safety,
    merge_managed_zones,
    record_variant_baseline,
    safe_persist_editor_to_variant,
)


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class WriterSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.component_dir = root / "cursor-api" / "Komponenty" / "gicleeframe"
        self.theme_path = root / "templates" / "page.giclee-frame.json"

        zone = TemplateZone(
            zone_id="managed",
            label="Zarządzana sekcja",
            description="",
            section_key="managed",
            fields=(
                TemplateField(
                    "line_width",
                    "Grubość linii",
                    "float",
                    ("sections", "managed", "settings", "line_width"),
                ),
                TemplateField(
                    "title",
                    "Tytuł",
                    "text",
                    ("sections", "managed", "settings", "title"),
                ),
            ),
        )
        self.config = PageEditorConfig(
            component_id="gicleeframe",
            component_dir=self.component_dir,
            app_title="Test",
            intro_title="Test",
            intro_body="Test",
            template_rel="templates/page.giclee-frame.json",
            preview_path="/pages/giclee-frame",
            variant_id_prefix="gf",
            zones=(zone,),
        )

        self.theme = {
            "sections": {
                "managed": {
                    "type": "managed",
                    "settings": {
                        "line_width": 0.5,
                        "title": "Motyw",
                        "unmanaged_flag": "zachowaj",
                    },
                    "blocks": {
                        "external": {
                            "type": "external",
                            "settings": {"value": 11},
                        }
                    },
                },
                "external-section": {
                    "type": "custom",
                    "settings": {"keep": True},
                },
            },
            "order": ["managed", "external-section"],
            "unmanaged_root": {"keep": "yes"},
        }
        self.variant1 = copy.deepcopy(self.theme)
        self.variant1["sections"]["managed"]["settings"]["line_width"] = 1.25
        self.variant1["sections"]["managed"]["settings"]["title"] = "Wersja 1"
        self.variant1["sections"]["managed"]["settings"]["unmanaged_flag"] = "nie kopiuj"
        self.variant1["sections"]["managed"]["blocks"]["external"]["settings"]["value"] = 999
        self.variant1["sections"]["external-section"]["settings"]["keep"] = False
        self.variant1["unmanaged_root"]["keep"] = "variant"

        self.variant2 = copy.deepcopy(self.theme)
        self.variant2["sections"]["managed"]["settings"]["line_width"] = 2.0

        self._write_theme(self.theme)
        self._write_variant("gf1", self.variant1)
        self._write_variant("gf2", self.variant2)
        self._write_manifest()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _variant_path(self, variant_id: str) -> Path:
        return (
            self.component_dir
            / "data"
            / "variants"
            / variant_id
            / self.config.template_basename
        )

    def _write_variant(self, variant_id: str, data: dict) -> None:
        path = self._variant_path(variant_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_json_bytes(data))

    def _write_manifest(self) -> None:
        path = self.component_dir / "data" / "variants" / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "active": "gf1",
                    "variants": [
                        {"id": "gf1", "label": "Wersja 1"},
                        {"id": "gf2", "label": "Wersja 2"},
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_theme(self, data: dict) -> None:
        self.theme_path.parent.mkdir(parents=True, exist_ok=True)
        self.theme_path.write_bytes(
            (INDEX_HEADER + json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            )
        )

    def _read_json(self, path: Path) -> dict:
        raw = path.read_text(encoding="utf-8")
        if raw.lstrip().startswith("/*"):
            raw = raw[raw.find("*/") + 2 :]
        return json.loads(raw)

    def test_save_variant_changes_only_selected_variant(self) -> None:
        theme_before = self.theme_path.read_bytes()
        gf2_before = self._variant_path("gf2").read_bytes()
        gf1_before = self._variant_path("gf1").read_bytes()

        record_variant_baseline(self.config, "gf1")
        changed = copy.deepcopy(self.variant1)
        changed["sections"]["managed"]["settings"]["line_width"] = 3.5
        result = safe_persist_editor_to_variant(self.config, "gf1", changed)

        self.assertTrue(result.changed)
        self.assertEqual(self.theme_path.read_bytes(), theme_before)
        self.assertEqual(self._variant_path("gf2").read_bytes(), gf2_before)
        self.assertNotEqual(self._variant_path("gf1").read_bytes(), gf1_before)
        self.assertIsNotNone(result.backup_path)
        self.assertEqual(result.backup_path.read_bytes(), gf1_before)

    def test_save_variant_blocks_stale_disk_state(self) -> None:
        record_variant_baseline(self.config, "gf1")
        external = copy.deepcopy(self.variant1)
        external["sections"]["managed"]["settings"]["line_width"] = 8
        self._write_variant("gf1", external)

        with self.assertRaisesRegex(RuntimeError, "zmieniła się"):
            safe_persist_editor_to_variant(self.config, "gf1", self.variant1)

    def test_noop_variant_save_does_not_create_backup(self) -> None:
        record_variant_baseline(self.config, "gf1")
        result = safe_persist_editor_to_variant(self.config, "gf1", self.variant1)
        self.assertFalse(result.changed)
        self.assertIsNone(result.backup_path)

    def test_merge_managed_zones_preserves_unmanaged_content(self) -> None:
        merged = merge_managed_zones(self.config, self.theme, self.variant1)

        settings = merged["sections"]["managed"]["settings"]
        self.assertEqual(settings["line_width"], 1.25)
        self.assertEqual(settings["title"], "Wersja 1")
        self.assertEqual(settings["unmanaged_flag"], "zachowaj")
        self.assertEqual(
            merged["sections"]["managed"]["blocks"]["external"]["settings"]["value"],
            11,
        )
        self.assertTrue(
            merged["sections"]["external-section"]["settings"]["keep"]
        )
        self.assertEqual(merged["order"], ["managed", "external-section"])
        self.assertEqual(merged["unmanaged_root"], {"keep": "yes"})

    def test_bounded_apply_writes_only_managed_fields_and_exact_backup(self) -> None:
        theme_before = self.theme_path.read_bytes()
        plan = build_bounded_apply_plan(
            self.config,
            "gf1",
            theme_path=self.theme_path,
            include_effects_asset=False,
        )
        paths = apply_bounded_plan(plan, confirmation="ZASTOSUJ gf1")

        self.assertEqual(paths, (self.theme_path,))
        saved = self._read_json(self.theme_path)
        self.assertEqual(
            saved["sections"]["managed"]["settings"]["line_width"],
            1.25,
        )
        self.assertEqual(
            saved["sections"]["managed"]["settings"]["unmanaged_flag"],
            "zachowaj",
        )
        self.assertEqual(
            saved["sections"]["managed"]["blocks"]["external"]["settings"]["value"],
            11,
        )
        self.assertTrue(
            saved["sections"]["external-section"]["settings"]["keep"]
        )
        backups = list(
            (self.component_dir / "data" / "apply_backups" / "gf1").glob("*")
        )
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), theme_before)

    def test_bounded_apply_blocks_stale_preview(self) -> None:
        plan = build_bounded_apply_plan(
            self.config,
            "gf1",
            theme_path=self.theme_path,
            include_effects_asset=False,
        )
        external = copy.deepcopy(self.theme)
        external["unmanaged_root"]["later"] = True
        self._write_theme(external)

        with self.assertRaisesRegex(RuntimeError, "zmienił się"):
            apply_bounded_plan(plan, confirmation="ZASTOSUJ gf1")

    def test_bounded_apply_requires_exact_confirmation(self) -> None:
        plan = build_bounded_apply_plan(
            self.config,
            "gf1",
            theme_path=self.theme_path,
            include_effects_asset=False,
        )
        with self.assertRaisesRegex(ValueError, "ZASTOSUJ gf1"):
            apply_bounded_plan(plan, confirmation="TAK")

    def test_duplicate_and_rename_do_not_touch_source_or_theme(self) -> None:
        source_before = self._variant_path("gf1").read_bytes()
        theme_before = self.theme_path.read_bytes()

        new_id = varmod.create_variant_copy(
            self.config,
            "gf1",
            "Kopia bezpieczna",
        )
        self.assertEqual(self._variant_path(new_id).read_bytes(), source_before)
        self.assertEqual(self._variant_path("gf1").read_bytes(), source_before)
        self.assertEqual(self.theme_path.read_bytes(), theme_before)

        new_before = self._variant_path(new_id).read_bytes()
        varmod.rename_variant_label(self.config, new_id, "Nowa nazwa")
        self.assertEqual(self._variant_path(new_id).read_bytes(), new_before)
        self.assertEqual(self._variant_path("gf1").read_bytes(), source_before)
        self.assertEqual(self.theme_path.read_bytes(), theme_before)

    def test_install_patches_shared_variant_io(self) -> None:
        install_writer_safety()
        self.assertTrue(
            getattr(varmod.persist_editor_to_variant, "_giclee_writer_safety", False)
        )
        self.assertTrue(
            getattr(varmod.load_variant_into_editor, "_giclee_writer_safety", False)
        )


if __name__ == "__main__":
    unittest.main()
