"""WS-1.3: testy współbieżnych okien i source-locked Apply."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.service_base import (
    INDEX_HEADER,
    load_template_from_path,
)
from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone
from Komponenty._shared.theme_page_editor import variants as varmod
from Komponenty._shared.theme_page_editor import writer_safety_concurrency_fix as concurrency
from Komponenty._shared.theme_page_editor.writer_safety_concurrency_fix import (
    apply_locked_delta_plan,
    build_locked_delta_apply_plan,
    install_concurrency_fix,
    loaded_variant_sha256,
    persist_variant_for_window,
)


def _config(tmp_path: Path) -> PageEditorConfig:
    zone = TemplateZone(
        zone_id="divider",
        label="Separator",
        description="",
        section_key="divider",
        fields=(
            TemplateField(
                "thickness",
                "Grubość",
                "float",
                ("sections", "divider", "settings", "thickness"),
            ),
        ),
    )
    return PageEditorConfig(
        component_id="test",
        component_dir=tmp_path / "component",
        app_title="Test",
        intro_title="Test",
        intro_body="Test",
        template_rel="templates/page.test.json",
        preview_path="/pages/test",
        variant_id_prefix="t",
        zones=(zone,),
    )


def _template(thickness: float = 0.5) -> dict:
    return {
        "sections": {
            "divider": {
                "type": "divider",
                "settings": {
                    "thickness": thickness,
                    "unmanaged": "keep",
                },
            },
            "foreign": {
                "type": "custom",
                "settings": {"value": 11},
            },
        },
        "order": ["divider", "foreign"],
    }


def _json_bytes(data: dict, *, header: str = "") -> bytes:
    return (header + json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _variant_path(config: PageEditorConfig, variant_id: str = "t1") -> Path:
    return (
        config.component_dir
        / "data"
        / "variants"
        / variant_id
        / config.template_basename
    )


def _base_path(config: PageEditorConfig, variant_id: str = "t1") -> Path:
    return (
        config.component_dir
        / "data"
        / "variant_bases"
        / variant_id
        / config.template_basename
    )


def _theme_path(tmp_path: Path) -> Path:
    return tmp_path / "theme" / "templates" / "page.test.json"


def _write_fixture(tmp_path: Path) -> tuple[PageEditorConfig, Path, Path, Path]:
    config = _config(tmp_path)
    base = _template()
    variant_path = _variant_path(config)
    variant_path.parent.mkdir(parents=True, exist_ok=True)
    variant_path.write_bytes(_json_bytes(base))

    base_path = _base_path(config)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_bytes(_json_bytes(base))

    theme_path = _theme_path(tmp_path)
    theme_path.parent.mkdir(parents=True, exist_ok=True)
    theme_path.write_bytes(_json_bytes(base, header=INDEX_HEADER))

    manifest = config.component_dir / "data" / "variants" / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "active": "t1",
                "variants": [{"id": "t1", "label": "Wersja 1"}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return config, variant_path, base_path, theme_path


def test_two_windows_same_variant_second_save_is_blocked(tmp_path: Path) -> None:
    config, variant_path, _base_path_value, _theme_path_value = _write_fixture(tmp_path)
    install_concurrency_fix()

    window_one = varmod.load_variant_into_editor(config, "t1")
    window_two = varmod.load_variant_into_editor(config, "t1")
    hash_one = loaded_variant_sha256(window_one)
    hash_two = loaded_variant_sha256(window_two)

    assert isinstance(hash_one, str)
    assert hash_two == hash_one

    first_change = copy.deepcopy(window_one)
    first_change["sections"]["divider"]["settings"]["thickness"] = 0.6
    first_result = persist_variant_for_window(
        config,
        "t1",
        first_change,
        expected_sha256=hash_one,
    )
    assert first_result.changed

    second_change = copy.deepcopy(window_two)
    second_change["sections"]["divider"]["settings"]["thickness"] = 0.7
    with pytest.raises(RuntimeError, match="tym oknie"):
        persist_variant_for_window(
            config,
            "t1",
            second_change,
            expected_sha256=hash_two,
        )

    saved = load_template_from_path(variant_path)
    assert saved["sections"]["divider"]["settings"]["thickness"] == 0.6


def test_apply_blocks_variant_changed_after_preview(tmp_path: Path) -> None:
    config, variant_path, base_path, theme_path = _write_fixture(tmp_path)
    variant = _template(0.6)
    variant_path.write_bytes(_json_bytes(variant))
    theme_before = theme_path.read_bytes()
    base_before = base_path.read_bytes()

    plan = build_locked_delta_apply_plan(
        config,
        "t1",
        theme_path=theme_path,
        include_effects_asset=False,
    )

    external = _template(0.7)
    variant_path.write_bytes(_json_bytes(external))

    with pytest.raises(RuntimeError, match="wariant"):
        apply_locked_delta_plan(plan, confirmation="ZASTOSUJ t1")

    assert theme_path.read_bytes() == theme_before
    assert base_path.read_bytes() == base_before


def test_apply_blocks_base_changed_after_preview(tmp_path: Path) -> None:
    config, variant_path, base_path, theme_path = _write_fixture(tmp_path)
    variant_path.write_bytes(_json_bytes(_template(0.6)))
    theme_before = theme_path.read_bytes()

    plan = build_locked_delta_apply_plan(
        config,
        "t1",
        theme_path=theme_path,
        include_effects_asset=False,
    )

    changed_base = _template(0.4)
    base_path.write_bytes(_json_bytes(changed_base))

    with pytest.raises(RuntimeError, match="baza wariantu"):
        apply_locked_delta_plan(plan, confirmation="ZASTOSUJ t1")

    assert theme_path.read_bytes() == theme_before
    assert load_template_from_path(base_path)["sections"]["divider"]["settings"]["thickness"] == 0.4


def test_apply_advances_base_to_exact_preview_variant_bytes(tmp_path: Path) -> None:
    config, variant_path, base_path, theme_path = _write_fixture(tmp_path)
    variant = _template(0.6)
    variant_bytes = _json_bytes(variant)
    variant_path.write_bytes(variant_bytes)

    plan = build_locked_delta_apply_plan(
        config,
        "t1",
        theme_path=theme_path,
        include_effects_asset=False,
    )
    paths = apply_locked_delta_plan(plan, confirmation="ZASTOSUJ t1")

    assert paths == (theme_path,)
    applied = load_template_from_path(theme_path)
    assert applied["sections"]["divider"]["settings"]["thickness"] == 0.6
    assert base_path.read_bytes() == variant_bytes


def test_apply_rolls_back_targets_when_variant_changes_during_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, variant_path, base_path, theme_path = _write_fixture(tmp_path)
    variant_path.write_bytes(_json_bytes(_template(0.6)))
    theme_before = theme_path.read_bytes()
    base_before = base_path.read_bytes()

    plan = build_locked_delta_apply_plan(
        config,
        "t1",
        theme_path=theme_path,
        include_effects_asset=False,
    )
    real_apply = concurrency._core_apply

    def apply_then_mutate(plan_value, *, confirmation: str):
        paths = real_apply(plan_value, confirmation=confirmation)
        variant_path.write_bytes(_json_bytes(_template(0.9)))
        return paths

    monkeypatch.setattr(concurrency, "_core_apply", apply_then_mutate)

    with pytest.raises(RuntimeError, match="wariant"):
        apply_locked_delta_plan(plan, confirmation="ZASTOSUJ t1")

    assert theme_path.read_bytes() == theme_before
    assert base_path.read_bytes() == base_before
