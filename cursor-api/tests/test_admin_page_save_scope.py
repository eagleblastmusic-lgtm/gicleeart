"""Regresje izolacji zapisu i wdrożenia komponentów Administracji strony."""

from __future__ import annotations

from pathlib import Path

import pytest

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.service_base import (
    component_deploy_relpaths,
    merge_managed_zone_values,
)
from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone
from Komponenty.stronaglowna import service


def _config(tmp_path: Path, *, effects: bool = True) -> PageEditorConfig:
    zone = TemplateZone(
        zone_id="hero",
        label="Hero",
        description="",
        section_key="hero",
        fields=(
            TemplateField(
                "title",
                "Tytuł",
                "text",
                ("sections", "hero", "settings", "title"),
            ),
        ),
    )
    return PageEditorConfig(
        component_id="faq",
        component_dir=tmp_path / "faq",
        app_title="FAQ",
        intro_title="FAQ",
        intro_body="",
        template_rel="templates/page.faq.json",
        preview_path="/pages/faq",
        variant_id_prefix="fq",
        zones=(zone,),
        section_effects_asset_enabled=effects,
    )


def test_page_save_merges_only_registered_fields_into_fresh_template(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    current = {
        "sections": {
            "hero": {
                "type": "hero",
                "settings": {"title": "Live", "foreign": "keep-current"},
            },
            "other-page-feature": {"settings": {"enabled": True}},
        },
        "order": ["hero", "other-page-feature"],
    }
    editor = {
        "sections": {
            "hero": {
                "type": "hero",
                "settings": {"title": "FAQ po zmianie", "foreign": "stale"},
            },
            "other-page-feature": {"settings": {"enabled": False}},
        },
        "order": ["other-page-feature", "hero"],
    }

    merged = merge_managed_zone_values(config, current, editor)

    assert merged["sections"]["hero"]["settings"] == {
        "title": "FAQ po zmianie",
        "foreign": "keep-current",
    }
    assert merged["sections"]["other-page-feature"]["settings"]["enabled"] is True
    assert merged["order"] == ["hero", "other-page-feature"]
    assert current["sections"]["hero"]["settings"]["title"] == "Live"


def test_component_deploy_lists_only_its_template_and_effect_asset(
    tmp_path: Path,
) -> None:
    assert component_deploy_relpaths(_config(tmp_path)) == (
        "templates/page.faq.json",
        "assets/faq-section-effects.js",
    )
    assert component_deploy_relpaths(_config(tmp_path, effects=False)) == (
        "templates/page.faq.json",
    )


class _FakeProcess:
    def __init__(self) -> None:
        self.stdout = iter(('{"ok":true}\n',))

    def wait(self) -> int:
        return 0


def test_deploy_theme_passes_repeated_exact_only_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "theme"
    (root / "templates").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "shopify.theme.toml").write_text("[environments.development]\n", encoding="utf-8")
    (root / "templates" / "page.faq.json").write_text("{}\n", encoding="utf-8")
    (root / "assets" / "faq-section-effects.js").write_text("// faq\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_popen(cli_args: list[str], *, cwd: Path | str) -> _FakeProcess:
        captured["args"] = cli_args
        captured["cwd"] = Path(cwd)
        return _FakeProcess()

    monkeypatch.setattr(service, "theme_root", lambda: root)
    monkeypatch.setattr(service, "shopify_cli_popen", fake_popen)

    code = service.deploy_theme(
        only_paths=(
            "templates/page.faq.json",
            "assets/faq-section-effects.js",
        )
    )

    assert code == 0
    assert captured["cwd"] == root
    assert captured["args"] == [
        "theme",
        "push",
        "--environment",
        "development",
        "--json",
        "--only",
        "templates/page.faq.json",
        "--only",
        "assets/faq-section-effects.js",
    ]


def test_deploy_theme_rejects_path_outside_theme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "theme"
    root.mkdir()
    (root / "shopify.theme.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(service, "theme_root", lambda: root)

    with pytest.raises(ValueError, match="Nieprawidłowa ścieżka"):
        service.deploy_theme(only_paths=("../secrets.txt",))


def test_home_settings_merge_preserves_foreign_global_keys() -> None:
    current = {
        "current": {
            "giclee_button_style": "nocturne",
            "external_setting": "keep",
            "site_notice_title": "Stary tytuł",
        },
        "presets": {"Keep": {"value": 1}},
    }
    editor = {
        "current": {
            "giclee_button_style": "basic",
            "external_setting": "stale",
            "site_notice_title": "Nowy tytuł",
            "site_notice_enabled": True,
        },
        "presets": {"Stale": {}},
    }

    merged = service.merge_managed_theme_settings(current, editor)

    assert merged["current"]["site_notice_title"] == "Nowy tytuł"
    assert merged["current"]["site_notice_enabled"] is True
    assert merged["current"]["giclee_button_style"] == "nocturne"
    assert merged["current"]["external_setting"] == "keep"
    assert merged["presets"] == {"Keep": {"value": 1}}
