from __future__ import annotations

import json
from pathlib import Path

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.features import list_backups, restore_backup
from Komponenty._shared.theme_page_editor import service_base
from Komponenty._shared.theme_page_editor.service_base import backup_file, backups_dir_for


def _config(tmp_path: Path) -> PageEditorConfig:
    return PageEditorConfig(
        component_id="kontakt",
        component_dir=tmp_path / "checkout" / "Komponenty" / "kontakt",
        app_title="Kontakt",
        intro_title="Kontakt",
        intro_body="Test",
        template_rel="templates/page.contact.json",
        preview_path="/pages/contact",
        variant_id_prefix="contact",
        zones=(),
    )


def test_standard_backup_writes_to_appdata_and_preserves_legacy(
    tmp_path: Path, monkeypatch
) -> None:
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))
    config = _config(tmp_path)

    legacy_dir = config.component_dir / "data" / "backups"
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "page.contact-legacy.json"
    legacy.write_text('{"legacy": true}\n', encoding="utf-8")
    assert backups_dir_for(config) == legacy_dir
    assert [row["name"] for row in list_backups(config)] == [legacy.name]

    source = tmp_path / "theme" / "templates" / "page.contact.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"new": true}\n', encoding="utf-8")
    created = backup_file(source, config)

    expected_root = (
        local
        / "backups"
        / "Komponenty"
        / "kontakt"
        / "data"
        / "backups"
    )
    assert created.parent == expected_root
    assert created.read_bytes() == source.read_bytes()
    assert legacy.read_text(encoding="utf-8") == '{"legacy": true}\n'
    assert backups_dir_for(config) == expected_root
    assert [row["path"] for row in list_backups(config)] == [str(created)]


def test_external_backup_can_be_restored_to_theme_target(
    tmp_path: Path, monkeypatch
) -> None:
    local = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(tmp_path / "roaming"))
    config = _config(tmp_path)

    theme_root = tmp_path / "theme"
    monkeypatch.setattr(service_base, "theme_root", lambda: theme_root)
    source = theme_root / "templates" / "page.contact.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({"version": 1}), encoding="utf-8")
    backup = backup_file(source, config)
    source.write_text(json.dumps({"version": 2}), encoding="utf-8")

    restore_backup(config, backup)

    assert json.loads(source.read_text(encoding="utf-8")) == {"version": 1}
    assert not (config.component_dir / "data" / "backups").exists()
