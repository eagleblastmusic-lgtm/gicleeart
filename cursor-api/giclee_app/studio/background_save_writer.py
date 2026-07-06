"""Bounded local clear writer — Studio Preview (F5.4b1).

Jedyny moduł F5.4b1 z write_text i shutil.copy2.
"""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_readiness import SaveReadiness
from giclee_app.studio.background_state import (
    STRONAGLOWNA_SECTION_BGS,
    SectionBgZone,
    read_stronaglowna_active_variant,
    section_bg_status,
)

_STRONAGLOWNA_VARIANT_INDEX = "data/variants/{variant_id}/index.json"
_BACKUPS_DIR = "data/backups"

_CLEAR_FIELDS: tuple[str, ...] = (
    "background_media",
    "background_image",
    "video",
    "background_overlay_pct",
)

_ERR_NOT_CLEAR_READY = "Zapis dozwolony tylko dla operacji clear z gotowością zapisu."
_ERR_NO_ZONE = "Nieznana strefa section_background."
_ERR_NO_INDEX = "Brak lub nieczytelny index.json aktywnego wariantu."
_ERR_ALREADY_CLEAR = "Strefa nie ma tła do wyczyszczenia."
_ERR_MISSING_INDEX_FILE = "Plik index.json nie istnieje."


@dataclass(frozen=True)
class SaveWriteResult:
    ok: bool
    message: str
    backup_filename: str | None
    zone_field_id: str
    zone_label: str
    section_key: str
    changed_fields: tuple[str, ...]


def clear_section_background_with_backup(
    draft: BackgroundDraftState,
    package_path: Path,
    *,
    readiness: SaveReadiness,
) -> SaveWriteResult:
    """Backup + clear jednej strefy section_background w aktywnym index.json."""
    zone = _zone_for_field_id(draft.zone_field_id)
    empty = SaveWriteResult(
        ok=False,
        message="",
        backup_filename=None,
        zone_field_id=draft.zone_field_id or "",
        zone_label=zone.label if zone else "—",
        section_key=zone.section_key if zone else "",
        changed_fields=(),
    )

    if not readiness.ready or readiness.operation != "clear":
        return _fail(empty, _ERR_NOT_CLEAR_READY)

    if zone is None:
        return _fail(empty, _ERR_NO_ZONE)

    index_path = resolve_active_index_path(package_path)
    if index_path is None:
        return _fail(empty, _ERR_NO_INDEX)
    if not index_path.is_file():
        return _fail(empty, _ERR_MISSING_INDEX_FILE)

    try:
        raw = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _fail(empty, f"Nie udało się odczytać index.json: {exc}")

    header = split_json_header(raw)
    try:
        before = json.loads(_strip_json_header(raw))
    except json.JSONDecodeError:
        return _fail(empty, "index.json — nieczytelny JSON.")

    if not isinstance(before, dict):
        return _fail(empty, _ERR_NO_INDEX)

    if section_bg_status(before, zone) == "brak":
        return _fail(empty, _ERR_ALREADY_CLEAR)

    after = copy.deepcopy(before)
    apply_clear_patch(after, zone.section_key)

    try:
        assert_bounded_diff(before, after, zone.section_key)
    except ValueError as exc:
        return _fail(empty, str(exc))

    try:
        backup_path = backup_index_json(index_path, package_path)
    except OSError as exc:
        return _fail(empty, f"Backup nie powiódł się: {exc}")

    try:
        write_index_json_preserving_header(index_path, after, header)
    except OSError as exc:
        return _fail(
            empty,
            f"Zapis index.json nie powiódł się: {exc}",
        )

    try:
        verify_raw = index_path.read_text(encoding="utf-8")
        verify_data = json.loads(_strip_json_header(verify_raw))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(empty, f"Walidacja po zapisie nie powiodła się: {exc}")

    if not isinstance(verify_data, dict):
        return _fail(empty, "Walidacja po zapisie — nieprawidłowy format.")

    return SaveWriteResult(
        ok=True,
        message="Zapisano lokalnie · wyczyszczono tło sekcji.",
        backup_filename=backup_path.name,
        zone_field_id=zone.field_id,
        zone_label=zone.label,
        section_key=zone.section_key,
        changed_fields=_CLEAR_FIELDS,
    )


def resolve_active_index_path(package_path: Path) -> Path | None:
    active = read_stronaglowna_active_variant(package_path)
    if active is None:
        return None
    return package_path / _STRONAGLOWNA_VARIANT_INDEX.format(variant_id=active[0])


def backup_index_json(index_path: Path, package_path: Path) -> Path:
    backup_dir = package_path / _BACKUPS_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"index-{ts}.json"
    shutil.copy2(index_path, backup_path)
    return backup_path


def build_clear_patch(_settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "background_media": "none",
        "background_image": "",
        "video": "",
        "background_overlay_pct": 0,
    }


def apply_clear_patch(template: dict[str, Any], section_key: str) -> None:
    sections = template.setdefault("sections", {})
    if not isinstance(sections, dict):
        raise ValueError("index.json — brak sekcji „sections”.")
    section = sections.setdefault(section_key, {})
    if not isinstance(section, dict):
        raise ValueError(f"index.json — nieprawidłowa sekcja {section_key}.")
    settings = section.setdefault("settings", {})
    if not isinstance(settings, dict):
        raise ValueError(f"index.json — nieprawidłowe settings w {section_key}.")
    settings.update(build_clear_patch(settings))


def assert_bounded_diff(
    before: dict[str, Any],
    after: dict[str, Any],
    section_key: str,
) -> None:
    before_sections = before.get("sections")
    after_sections = after.get("sections")
    if not isinstance(before_sections, dict) or not isinstance(after_sections, dict):
        raise ValueError("index.json — brak sekcji „sections”.")

    for key, section in before_sections.items():
        if key == section_key:
            continue
        if section != after_sections.get(key):
            raise ValueError(f"Niedozwolona zmiana poza sekcją {section_key}.")

    for key in after_sections:
        if key != section_key and key not in before_sections:
            raise ValueError(f"Niedozwolona nowa sekcja {key}.")

    target_before = _section_settings(before_sections, section_key)
    target_after = _section_settings(after_sections, section_key)
    changed = {
        field
        for field in set(target_before.keys()) | set(target_after.keys())
        if target_before.get(field) != target_after.get(field)
    }
    extra = changed - set(_CLEAR_FIELDS)
    if extra:
        raise ValueError(
            f"Niedozwolone pola poza {_CLEAR_FIELDS}: {sorted(extra)}"
        )


def split_json_header(raw: str) -> str:
    stripped = raw.lstrip()
    if stripped.startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[: end + 2]
    return ""


def write_index_json_preserving_header(
    path: Path,
    template: dict[str, Any],
    header: str,
) -> None:
    body = json.dumps(template, ensure_ascii=False, indent=2) + "\n"
    path.write_text(f"{header}{body}", encoding="utf-8")


def _strip_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def _section_settings(sections: dict[str, Any], section_key: str) -> dict[str, Any]:
    section = sections.get(section_key)
    if not isinstance(section, dict):
        return {}
    settings = section.get("settings")
    return settings if isinstance(settings, dict) else {}


def _zone_for_field_id(field_id: str | None) -> SectionBgZone | None:
    if not field_id:
        return None
    for zone in STRONAGLOWNA_SECTION_BGS:
        if zone.field_id == field_id:
            return zone
    return None


def _fail(result: SaveWriteResult, message: str) -> SaveWriteResult:
    return SaveWriteResult(
        ok=result.ok,
        message=message,
        backup_filename=result.backup_filename,
        zone_field_id=result.zone_field_id,
        zone_label=result.zone_label,
        section_key=result.section_key,
        changed_fields=result.changed_fields,
    )


__all__ = [
    "SaveWriteResult",
    "apply_clear_patch",
    "assert_bounded_diff",
    "backup_index_json",
    "build_clear_patch",
    "clear_section_background_with_backup",
    "resolve_active_index_path",
    "split_json_header",
    "write_index_json_preserving_header",
]
