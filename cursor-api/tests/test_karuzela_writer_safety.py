from __future__ import annotations

from pathlib import Path

import pytest

from Komponenty.karuzela import service
from tools.repository_safety.runtime_writes import scan_python_source


def _isolate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    settings_file = tmp_path / "settings.json"
    theme_file = tmp_path / "theme" / "assets" / "giclee-carousel-config.js"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(tmp_path / "roaming"))
    monkeypatch.setattr(service, "_SETTINGS_FILE", settings_file)
    monkeypatch.setattr(service, "_THEME_CONFIG_FILE_OVERRIDE", theme_file)
    return settings_file, theme_file


def test_save_karuzela_settings_never_writes_theme(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings_file, theme_file = _isolate(monkeypatch, tmp_path)
    theme_file.parent.mkdir(parents=True)
    theme_file.write_bytes(b"original-theme\n")

    service.save_karuzela_settings(
        "Karuzela2",
        "V3",
        "https://example.test/collections/demo",
        False,
    )

    assert theme_file.read_bytes() == b"original-theme\n"
    text = settings_file.read_text(encoding="utf-8")
    assert '"carousel_version": "Karuzela2"' in text
    assert '"showcase_look": "V3"' in text
    assert '"hover_blur_enabled": false' in text


@pytest.mark.parametrize(
    ("setter", "value", "expected"),
    [
        (service.set_carousel_version, "Karuzela2", '"carousel_version": "Karuzela2"'),
        (service.set_showcase_look, "V1", '"showcase_look": "V1"'),
        (service.set_hover_blur, False, '"hover_blur_enabled": false'),
    ],
)
def test_individual_setters_only_persist_app_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    setter,
    value,
    expected: str,
) -> None:
    settings_file, theme_file = _isolate(monkeypatch, tmp_path)
    theme_file.parent.mkdir(parents=True)
    theme_file.write_bytes(b"theme-stays\n")

    setter(value)

    assert expected in settings_file.read_text(encoding="utf-8")
    assert theme_file.read_bytes() == b"theme-stays\n"


def test_build_plan_is_read_only_and_contains_exact_diff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _settings_file, theme_file = _isolate(monkeypatch, tmp_path)
    theme_file.parent.mkdir(parents=True)
    theme_file.write_bytes(b"old\n")
    before = theme_file.read_bytes()

    plan = service.build_theme_config_plan("Karuzela2", "V3", False)

    assert plan.path == theme_file
    assert plan.before_bytes == before
    assert plan.changed is True
    assert 'window.__GICLEE_CAROUSEL_DEFAULT = "Karuzela2";' in plan.after_bytes.decode("utf-8")
    assert 'window.__GICLEE_SHOWCASE_LOOK_DEFAULT = "V3";' in plan.after_bytes.decode("utf-8")
    assert "window.__GICLEE_HOVER_BLUR_ENABLED = false;" in plan.after_bytes.decode("utf-8")
    assert "---" in plan.diff_text
    assert "+++" in plan.diff_text
    assert theme_file.read_bytes() == before


def test_wrong_confirmation_does_not_write_or_backup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _settings_file, theme_file = _isolate(monkeypatch, tmp_path)
    theme_file.parent.mkdir(parents=True)
    theme_file.write_bytes(b"old\n")
    plan = service.build_theme_config_plan("Karuzela1", "V2", True)

    with pytest.raises(ValueError, match="ZASTOSUJ KARUZELĘ"):
        service.apply_theme_config_plan(plan, confirmation="tak")

    assert theme_file.read_bytes() == b"old\n"
    assert not (tmp_path / "local" / "backups").exists()


def test_stale_theme_file_blocks_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _settings_file, theme_file = _isolate(monkeypatch, tmp_path)
    theme_file.parent.mkdir(parents=True)
    theme_file.write_bytes(b"old\n")
    plan = service.build_theme_config_plan("Karuzela2", "V1", True)
    theme_file.write_bytes(b"changed-after-preview\n")

    with pytest.raises(RuntimeError, match="zmienił się po utworzeniu podglądu"):
        service.apply_theme_config_plan(
            plan,
            confirmation=service.THEME_APPLY_CONFIRMATION,
        )

    assert theme_file.read_bytes() == b"changed-after-preview\n"


def test_exact_target_lock_blocks_retargeted_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _settings_file, first_theme = _isolate(monkeypatch, tmp_path)
    first_theme.parent.mkdir(parents=True)
    first_theme.write_bytes(b"first\n")
    plan = service.build_theme_config_plan("Karuzela2", "V2", False)
    second_theme = tmp_path / "other-theme" / "assets" / "giclee-carousel-config.js"
    monkeypatch.setattr(service, "_THEME_CONFIG_FILE_OVERRIDE", second_theme)

    with pytest.raises(RuntimeError, match="niedozwolony plik motywu"):
        service.apply_theme_config_plan(
            plan,
            confirmation=service.THEME_APPLY_CONFIRMATION,
        )

    assert first_theme.read_bytes() == b"first\n"
    assert not second_theme.exists()


def test_successful_apply_creates_external_backup_and_verifies_hash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _settings_file, theme_file = _isolate(monkeypatch, tmp_path)
    theme_file.parent.mkdir(parents=True)
    theme_file.write_bytes(b"old-theme\n")
    plan = service.build_theme_config_plan("Karuzela2", "V3", False)

    result = service.apply_theme_config_plan(
        plan,
        confirmation=service.THEME_APPLY_CONFIRMATION,
    )

    assert result.changed is True
    assert result.path == theme_file
    assert result.after_sha256 == plan.after_sha256
    assert theme_file.read_bytes() == plan.after_bytes
    assert result.backup_path is not None
    assert result.backup_path.read_bytes() == b"old-theme\n"
    assert result.backup_path.is_relative_to(tmp_path / "local" / "backups")
    assert not result.backup_path.is_relative_to(theme_file.parent)


def test_no_change_apply_does_not_create_backup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _settings_file, theme_file = _isolate(monkeypatch, tmp_path)
    theme_file.parent.mkdir(parents=True)
    expected = service.render_theme_config("Karuzela1", "V2", True)
    theme_file.write_bytes(expected)
    plan = service.build_theme_config_plan("Karuzela1", "V2", True)

    result = service.apply_theme_config_plan(
        plan,
        confirmation=service.THEME_APPLY_CONFIRMATION,
    )

    assert plan.changed is False
    assert result.changed is False
    assert result.backup_path is None
    assert theme_file.read_bytes() == expected


def test_gui_exposes_separate_save_and_theme_apply_actions() -> None:
    gui_path = Path(__file__).resolve().parents[1] / "Komponenty" / "karuzela" / "gui.py"
    source = gui_path.read_text(encoding="utf-8")

    assert 'text="Zapisz", command=_save' in source
    assert 'text="Zastosuj do motywu…", command=_apply_theme' in source
    assert "build_theme_config_plan(" in source
    assert "apply_theme_config_plan(plan, confirmation=confirmation)" in source
    assert "Deploy motywu nie został wykonany" in source
    assert "Po Zapisz aktualizowany jest assets/giclee-carousel-config.js" not in source


def test_runtime_write_inventory_no_longer_flags_karuzela_service() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/karuzela/service.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
