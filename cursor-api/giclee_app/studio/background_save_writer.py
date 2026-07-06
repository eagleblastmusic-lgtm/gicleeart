"""Bounded local clear/set_with_ref/restore writer — Studio Preview (F5.4b1 / F5.4b2 / F5.4c1).

Jedyny moduł Studio z write_text i shutil.copy2.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from giclee_app.studio.background_asset_catalog import (
    build_background_asset_catalog,
    resolve_selected_asset_ref,
    validate_selected_asset_id,
)
from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_contract import VIDEO_COLLAGE_SCOPE_ERROR
from giclee_app.studio.background_save_readiness import SaveReadiness
from giclee_app.studio.background_state import (
    STRONAGLOWNA_SECTION_BGS,
    SectionBgZone,
    read_stronaglowna_active_variant,
    section_bg_current_ref,
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
_ERR_NOT_SET_WITH_REF_READY = (
    "Zapis dozwolony tylko dla operacji set_with_ref z gotowością zapisu."
)
_ERR_NO_ZONE = "Nieznana strefa section_background."
_ERR_NO_INDEX = "Brak lub nieczytelny index.json aktywnego wariantu."
_ERR_ALREADY_CLEAR = "Strefa nie ma tła do wyczyszczenia."
_ERR_NO_CHANGES = "Brak zmian — ten sam typ i ten sam asset."
_ERR_INVALID_REF = "Wybrany asset jest nieprawidłowy lub nie pasuje do typu draftu."
_ERR_MISSING_REF = "Brak ref dla wybranego assetu."
_ERR_KIND_MISMATCH = "Typ assetu nie pasuje do draftu."
_ERR_VIDEO_COLLAGE = VIDEO_COLLAGE_SCOPE_ERROR
_ERR_MISSING_INDEX_FILE = "Plik index.json nie istnieje."
_ERR_INVALID_BACKUP = "Nieprawidłowa nazwa pliku backupu."
_ERR_VARIANT_CHANGED = "Aktywny wariant zmienił się od ostatniego zapisu."
_ERR_MISSING_SECTION = "Brak sekcji w backupie."

_BACKUP_FILENAME_RE = re.compile(r"^index-\d{8}-\d{6}\.json$")


@dataclass(frozen=True)
class SaveWriteResult:
    ok: bool
    message: str
    backup_filename: str | None
    zone_field_id: str
    zone_label: str
    section_key: str
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class RestoreWriteResult:
    ok: bool
    message: str
    backup_filename: str
    zone_field_id: str
    zone_label: str
    section_key: str
    restored_fields: tuple[str, ...]


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


def set_section_background_with_ref_backup(
    draft: BackgroundDraftState,
    package_path: Path,
    *,
    readiness: SaveReadiness,
) -> SaveWriteResult:
    """Backup + set_with_ref jednej strefy section_background w aktywnym index.json."""
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

    if not readiness.ready or readiness.operation != "set_with_ref":
        return _fail(empty, _ERR_NOT_SET_WITH_REF_READY)

    if draft.asset_kind == "video_collage":
        return _fail(empty, _ERR_VIDEO_COLLAGE)

    if draft.asset_kind not in ("image", "video"):
        return _fail(empty, _ERR_KIND_MISMATCH)

    if zone is None:
        return _fail(empty, _ERR_NO_ZONE)

    catalog = build_background_asset_catalog(package_path)
    if not validate_selected_asset_id(
        draft.selected_asset_id,
        catalog,
        asset_kind=draft.asset_kind,
    ):
        return _fail(empty, _ERR_INVALID_REF)

    ref = resolve_selected_asset_ref(catalog, draft.selected_asset_id)
    if not ref:
        return _fail(empty, _ERR_MISSING_REF)

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

    current_settings = _section_settings(
        before.get("sections") or {},
        zone.section_key,
    )
    patch = build_set_with_ref_patch(draft.asset_kind, ref, current_settings)

    current_ref = section_bg_current_ref(before, zone)
    if (
        current_ref is not None
        and current_ref.kind == draft.asset_kind
        and current_ref.ref == ref
    ):
        return _fail(empty, _ERR_NO_CHANGES)

    if _patch_matches_settings(current_settings, patch):
        return _fail(empty, _ERR_NO_CHANGES)

    after = copy.deepcopy(before)
    apply_set_with_ref_patch(after, zone.section_key, patch)

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
        return _fail(empty, f"Zapis index.json nie powiódł się: {exc}")

    try:
        verify_raw = index_path.read_text(encoding="utf-8")
        verify_data = json.loads(_strip_json_header(verify_raw))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(empty, f"Walidacja po zapisie nie powiodła się: {exc}")

    if not isinstance(verify_data, dict):
        return _fail(empty, "Walidacja po zapisie — nieprawidłowy format.")

    kind_pl = "obraz" if draft.asset_kind == "image" else "wideo"
    return SaveWriteResult(
        ok=True,
        message=f"Zapisano lokalnie · ustawiono tło ({kind_pl}).",
        backup_filename=backup_path.name,
        zone_field_id=zone.field_id,
        zone_label=zone.label,
        section_key=zone.section_key,
        changed_fields=_CLEAR_FIELDS,
    )


def validate_backup_path(package_path: Path, backup_filename: str) -> Path | None:
    """Walidacja basename backupu — bez glob/rglob."""
    name = (backup_filename or "").strip()
    if not name or name != backup_filename:
        return None
    if "/" in name or "\\" in name or ".." in name:
        return None
    if not _BACKUP_FILENAME_RE.match(name):
        return None
    backup_dir = (package_path / _BACKUPS_DIR).resolve()
    candidate = (backup_dir / name).resolve()
    try:
        candidate.relative_to(backup_dir)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def restore_section_background_from_backup(
    *,
    package_path: Path,
    backup_filename: str,
    section_key: str,
    zone_field_id: str,
    zone_label: str,
    expected_variant_id: str | None = None,
) -> RestoreWriteResult:
    """Przywraca 4 pola tła jednej sekcji z backupu F5.4b1."""
    empty = RestoreWriteResult(
        ok=False,
        message="",
        backup_filename=backup_filename or "",
        zone_field_id=zone_field_id,
        zone_label=zone_label,
        section_key=section_key,
        restored_fields=(),
    )

    backup_path = validate_backup_path(package_path, backup_filename)
    if backup_path is None:
        return _fail_restore(empty, _ERR_INVALID_BACKUP)

    active = read_stronaglowna_active_variant(package_path)
    if active is None:
        return _fail_restore(empty, _ERR_NO_INDEX)
    if expected_variant_id and active[0] != expected_variant_id:
        return _fail_restore(empty, _ERR_VARIANT_CHANGED)

    index_path = resolve_active_index_path(package_path)
    if index_path is None or not index_path.is_file():
        return _fail_restore(empty, _ERR_MISSING_INDEX_FILE)

    try:
        backup_raw = backup_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _fail_restore(empty, f"Nie udało się odczytać backupu: {exc}")

    try:
        backup_data = json.loads(_strip_json_header(backup_raw))
    except json.JSONDecodeError:
        return _fail_restore(empty, "Backup — nieczytelny JSON.")

    if not isinstance(backup_data, dict):
        return _fail_restore(empty, _ERR_INVALID_BACKUP)

    backup_sections = backup_data.get("sections")
    if not isinstance(backup_sections, dict):
        return _fail_restore(empty, _ERR_MISSING_SECTION)
    backup_section = backup_sections.get(section_key)
    if not isinstance(backup_section, dict):
        return _fail_restore(empty, _ERR_MISSING_SECTION)
    backup_settings = backup_section.get("settings")
    if not isinstance(backup_settings, dict):
        return _fail_restore(empty, _ERR_MISSING_SECTION)

    try:
        index_raw = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _fail_restore(empty, f"Nie udało się odczytać index.json: {exc}")

    header = split_json_header(index_raw)
    try:
        before = json.loads(_strip_json_header(index_raw))
    except json.JSONDecodeError:
        return _fail_restore(empty, "index.json — nieczytelny JSON.")

    if not isinstance(before, dict):
        return _fail_restore(empty, _ERR_NO_INDEX)

    after = copy.deepcopy(before)
    try:
        apply_restore_patch(after, section_key, backup_settings)
    except ValueError as exc:
        return _fail_restore(empty, str(exc))

    try:
        assert_bounded_restore_diff(before, after, section_key)
    except ValueError as exc:
        return _fail_restore(empty, str(exc))

    try:
        write_index_json_preserving_header(index_path, after, header)
    except OSError as exc:
        return _fail_restore(empty, f"Zapis index.json nie powiódł się: {exc}")

    try:
        verify_raw = index_path.read_text(encoding="utf-8")
        verify_data = json.loads(_strip_json_header(verify_raw))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail_restore(empty, f"Walidacja po restore nie powiodła się: {exc}")

    if not isinstance(verify_data, dict):
        return _fail_restore(empty, "Walidacja po restore — nieprawidłowy format.")

    return RestoreWriteResult(
        ok=True,
        message="Przywrócono lokalnie · tło sekcji z backupu.",
        backup_filename=backup_path.name,
        zone_field_id=zone_field_id,
        zone_label=zone_label,
        section_key=section_key,
        restored_fields=_CLEAR_FIELDS,
    )


def build_restore_patch(backup_settings: dict[str, Any]) -> dict[str, Any]:
    return {field: backup_settings.get(field) for field in _CLEAR_FIELDS}


def apply_restore_patch(
    template: dict[str, Any],
    section_key: str,
    backup_settings: dict[str, Any],
) -> None:
    sections = template.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("index.json — brak sekcji „sections”.")
    section = sections.get(section_key)
    if not isinstance(section, dict):
        raise ValueError(f"index.json — brak sekcji {section_key}.")
    settings = section.get("settings")
    if not isinstance(settings, dict):
        raise ValueError(f"index.json — nieprawidłowe settings w {section_key}.")
    settings.update(build_restore_patch(backup_settings))


def assert_bounded_restore_diff(
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


def build_set_with_ref_patch(
    asset_kind: str,
    ref: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    overlay = _preserve_overlay_pct(settings)
    if asset_kind == "image":
        return {
            "background_media": "image",
            "background_image": ref,
            "video": "",
            "background_overlay_pct": overlay,
        }
    if asset_kind == "video":
        return {
            "background_media": "video",
            "background_image": "",
            "video": ref,
            "background_overlay_pct": overlay,
        }
    raise ValueError(_ERR_KIND_MISMATCH)


def apply_set_with_ref_patch(
    template: dict[str, Any],
    section_key: str,
    patch: dict[str, Any],
) -> None:
    sections = template.setdefault("sections", {})
    if not isinstance(sections, dict):
        raise ValueError("index.json — brak sekcji „sections”.")
    section = sections.setdefault(section_key, {})
    if not isinstance(section, dict):
        raise ValueError(f"index.json — nieprawidłowa sekcja {section_key}.")
    settings = section.setdefault("settings", {})
    if not isinstance(settings, dict):
        raise ValueError(f"index.json — nieprawidłowe settings w {section_key}.")
    settings.update(patch)


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


def _preserve_overlay_pct(settings: dict[str, Any]) -> int:
    raw = settings.get("background_overlay_pct")
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int) and raw >= 0:
        return raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.isdigit():
            return int(stripped)
    if isinstance(raw, float) and raw >= 0:
        return int(raw)
    return 0


def _patch_matches_settings(
    settings: dict[str, Any],
    patch: dict[str, Any],
) -> bool:
    return all(settings.get(field) == patch.get(field) for field in _CLEAR_FIELDS)


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


def _fail_restore(result: RestoreWriteResult, message: str) -> RestoreWriteResult:
    return RestoreWriteResult(
        ok=result.ok,
        message=message,
        backup_filename=result.backup_filename,
        zone_field_id=result.zone_field_id,
        zone_label=result.zone_label,
        section_key=result.section_key,
        restored_fields=result.restored_fields,
    )


__all__ = [
    "RestoreWriteResult",
    "SaveWriteResult",
    "apply_clear_patch",
    "apply_restore_patch",
    "apply_set_with_ref_patch",
    "assert_bounded_diff",
    "assert_bounded_restore_diff",
    "backup_index_json",
    "build_clear_patch",
    "build_restore_patch",
    "build_set_with_ref_patch",
    "clear_section_background_with_backup",
    "resolve_active_index_path",
    "restore_section_background_from_backup",
    "set_section_background_with_ref_backup",
    "split_json_header",
    "validate_backup_path",
    "write_index_json_preserving_header",
]
