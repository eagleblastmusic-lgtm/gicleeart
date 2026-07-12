from __future__ import annotations

import json
import zipfile
from pathlib import Path


def _set_roots(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))
    return local, roaming


def test_activity_log_seeds_legacy_and_appends_external(monkeypatch, tmp_path: Path) -> None:
    from Komponenty._shared import activity_log

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy = tmp_path / "repo" / "activity_log.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy_line = {
        "ts": "2026-07-01T00:00:00+00:00",
        "component": "legacy",
        "level": "info",
        "message": "stary wpis",
    }
    legacy.write_text(json.dumps(legacy_line) + "\n", encoding="utf-8")
    before = legacy.read_bytes()

    monkeypatch.setattr(activity_log, "_LEGACY_LOG_FILE", legacy)

    activity_log.append_activity("test", "nowy wpis", detail="szczegol")

    target = local / "logs" / "Komponenty" / "_shared" / "activity_log.jsonl"
    records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert [record["message"] for record in records] == ["stary wpis", "nowy wpis"]
    assert records[-1]["detail"] == "szczegol"
    assert legacy.read_bytes() == before
    assert activity_log.read_tail()[-1].endswith("nowy wpis  (szczegol)")


def test_activity_log_preserves_log_file_override(monkeypatch, tmp_path: Path) -> None:
    from Komponenty._shared import activity_log

    explicit = tmp_path / "explicit" / "activity.jsonl"
    monkeypatch.setattr(activity_log, "LOG_FILE", explicit)

    activity_log.append_activity("test", "override")

    assert explicit.is_file()
    assert activity_log.read_tail()[-1].endswith("override")


def test_backup_archive_and_state_write_outside_source(monkeypatch, tmp_path: Path) -> None:
    from Komponenty._shared import backup

    local, _ = _set_roots(monkeypatch, tmp_path)
    source_root = tmp_path / "cursor-api"
    source_file = source_root / "Komponenty" / "demo" / "data" / "state.json"
    source_file.parent.mkdir(parents=True)
    source_file.write_text('{"ok": true}', encoding="utf-8")

    legacy_backups = source_root / "backups"
    legacy_backups.mkdir()
    legacy_state = legacy_backups / ".last_run.json"
    legacy_state.write_text('{"last_backup_date": "2000-01-01"}', encoding="utf-8")
    legacy_before = legacy_state.read_bytes()

    monkeypatch.setattr(backup, "_CURSOR_API_DIR", source_root)
    monkeypatch.setattr(backup, "_LEGACY_BACKUPS_DIR", legacy_backups)
    monkeypatch.setattr(backup, "_LEGACY_STATE_FILE", legacy_state)
    monkeypatch.setattr(backup, "_BACKUPS_DIR", None)
    monkeypatch.setattr(backup, "_STATE_FILE", None)
    monkeypatch.setattr(backup, "_INCLUDE_PATTERNS", ["Komponenty/demo/data/*.json"])
    monkeypatch.setattr(backup, "_EXCLUDE_PATTERNS", [])

    archive = backup.create_backup()
    assert archive is not None
    assert archive.parent == local / "backups"
    assert not (legacy_backups / archive.name).exists()
    with zipfile.ZipFile(archive, "r") as handle:
        assert "Komponenty/demo/data/state.json" in handle.namelist()
        assert "_backup_manifest.json" in handle.namelist()

    assert backup._read_state()["last_backup_date"] == "2000-01-01"
    backup._write_state({"last_backup_date": "2026-07-12", "last_backup_file": archive.name})
    external_state = local / "backups" / ".last_run.json"
    assert json.loads(external_state.read_text(encoding="utf-8"))["last_backup_file"] == archive.name
    assert legacy_state.read_bytes() == legacy_before


def test_backup_preserves_private_path_overrides(monkeypatch, tmp_path: Path) -> None:
    from Komponenty._shared import backup

    explicit_dir = tmp_path / "explicit-backups"
    explicit_state = explicit_dir / "state.json"
    monkeypatch.setattr(backup, "_BACKUPS_DIR", explicit_dir)
    monkeypatch.setattr(backup, "_STATE_FILE", explicit_state)

    backup._write_state({"ok": True})

    assert json.loads(explicit_state.read_text(encoding="utf-8")) == {"ok": True}
    assert backup._backups_dir() == explicit_dir


def test_list_backups_falls_back_to_legacy_when_external_is_empty(monkeypatch, tmp_path: Path) -> None:
    from Komponenty._shared import backup

    _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-backups"
    legacy_dir.mkdir()
    legacy_zip = legacy_dir / "2026-07-01.zip"
    with zipfile.ZipFile(legacy_zip, "w") as handle:
        handle.writestr("file.txt", "x")
    monkeypatch.setattr(backup, "_LEGACY_BACKUPS_DIR", legacy_dir)
    monkeypatch.setattr(backup, "_BACKUPS_DIR", None)

    rows = backup.list_backups()
    assert [row["name"] for row in rows] == [legacy_zip.name]
    assert rows[0]["path"] == str(legacy_zip)
