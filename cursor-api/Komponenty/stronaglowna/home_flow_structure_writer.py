"""HF-3B: bounded writer struktury GICLÉE HOME FLOW.

Writer modyfikuje wyłącznie ``index.json`` wskazanego wariantu lokalnego.
Nie zapisuje ``templates/index.json``, nie generuje assetów i nie uruchamia
żadnego deployu Shopify.

Zakres HF-3B:
- ponowna walidacja szkicu i pliku wariantu,
- zmiana kolejności istniejących, zarządzanych sekcji,
- dokładny backup bajtowy,
- zapis tymczasowy + ``os.replace``,
- jednooperacyjne Undo chronione hashami.

Blueprinty nowych sekcji pozostają zablokowane do HF-3C, ponieważ HF-3A
przechowuje ich opis, a nie gotowy i zwalidowany fragment sekcji Shopify.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any
import uuid

from .home_flow import DEFAULT_FLOW_ITEMS
from .home_flow_structure import (
    _clean_custom_sections,
    _normalize_section_order,
    load_structure_draft,
    validate_structure_draft,
)
from .homepage_variants import VARIANTS_ROOT, _load_json_file
from .registry import zone_by_id
from .service import INDEX_HEADER


WRITER_SCHEMA_VERSION = 1
WRITER_STATE_FILENAME = "home_flow_structure_writer.json"
WRITER_BACKUP_DIRNAME = "home_flow_structure_backups"


class StructureWriterError(RuntimeError):
    """Kontrolowany błąd bounded writer-a."""


def _variant_root(variant_id: str, *, variants_root: Path | None = None) -> Path:
    root = Path(variants_root) if variants_root is not None else VARIANTS_ROOT
    return root / str(variant_id)


def variant_index_path(variant_id: str, *, variants_root: Path | None = None) -> Path:
    return _variant_root(variant_id, variants_root=variants_root) / "index.json"


def writer_state_path(variant_id: str, *, variants_root: Path | None = None) -> Path:
    return _variant_root(variant_id, variants_root=variants_root) / WRITER_STATE_FILENAME


def writer_backup_dir(variant_id: str, *, variants_root: Path | None = None) -> Path:
    return _variant_root(variant_id, variants_root=variants_root) / WRITER_BACKUP_DIRNAME


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_bytes(path, text.encode("utf-8"))


def _serialize_index(template: dict[str, Any]) -> bytes:
    body = json.dumps(template, ensure_ascii=False, indent=2) + "\n"
    return (INDEX_HEADER + body).encode("utf-8")


def _core_section_key_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in DEFAULT_FLOW_ITEMS:
        if item.kind != "section" or not item.zone_id:
            continue
        zone = zone_by_id(item.zone_id)
        if zone is None or zone.settings_only or not zone.section_key:
            continue
        mapping[item.stable_id] = zone.section_key
    return mapping


def _issue(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _normalized_draft(draft: dict[str, Any]) -> dict[str, Any]:
    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    section_order = _normalize_section_order(draft.get("section_order"), custom_sections)
    return {"section_order": section_order, "custom_sections": custom_sections}


def _replace_managed_slots(
    source_order: list[str],
    desired_managed_order: list[str],
    managed_keys: set[str],
) -> list[str]:
    iterator = iter(desired_managed_order)
    return [next(iterator) if key in managed_keys else key for key in source_order]


def build_writer_plan(
    variant_id: str,
    *,
    variants_root: Path | None = None,
    draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Buduje dry-run HF-3B bez zapisu na dysk."""

    working = _normalized_draft(
        draft if isinstance(draft, dict) else load_structure_draft(
            variant_id, variants_root=variants_root
        )
    )
    issues: list[dict[str, str]] = [
        _issue(issue.severity, issue.code, issue.message)
        for issue in validate_structure_draft(working)
        if issue.severity == "blocker"
    ]

    if working["custom_sections"]:
        issues.append(
            _issue(
                "blocker",
                "BLUEPRINT_RUNTIME_PENDING",
                "Szkic zawiera nowe blueprinty. HF-3B zapisuje wyłącznie kolejność istniejących sekcji; materializacja blueprintów wymaga HF-3C.",
            )
        )

    index_path = variant_index_path(variant_id, variants_root=variants_root)
    template: dict[str, Any] | None = None
    source_order: list[str] = []
    target_order: list[str] = []
    source_hash = ""

    if not index_path.is_file():
        issues.append(_issue("blocker", "INDEX_MISSING", f"Brak pliku wariantu: {index_path}"))
    else:
        try:
            source_bytes = index_path.read_bytes()
            source_hash = _sha256_bytes(source_bytes)
            template = _load_json_file(index_path)
        except (OSError, ValueError, TypeError) as exc:
            issues.append(_issue("blocker", "INDEX_INVALID", f"Nie można odczytać index.json wariantu: {exc}"))

    sections: dict[str, Any] = {}
    if isinstance(template, dict):
        raw_sections = template.get("sections")
        raw_order = template.get("order")
        if not isinstance(raw_sections, dict):
            issues.append(_issue("blocker", "SECTIONS_INVALID", "Pole sections nie jest obiektem JSON."))
        else:
            sections = raw_sections
        if not isinstance(raw_order, list) or not all(isinstance(value, str) for value in raw_order):
            issues.append(_issue("blocker", "ORDER_INVALID", "Pole order nie jest listą identyfikatorów."))
        else:
            source_order = list(raw_order)

    stable_to_key = _core_section_key_map()
    managed_keys = set(stable_to_key.values())
    desired_stable_ids = [stable_id for stable_id in working["section_order"] if stable_id in stable_to_key]
    desired_keys = [stable_to_key[stable_id] for stable_id in desired_stable_ids]

    if source_order and sections:
        for stable_id, section_key in stable_to_key.items():
            if section_key not in sections:
                issues.append(_issue("blocker", "SECTION_OBJECT_MISSING", f"{stable_id}: brak sekcji {section_key} w sections."))
            if section_key not in source_order:
                issues.append(_issue("blocker", "SECTION_ORDER_MISSING", f"{stable_id}: brak sekcji {section_key} w order."))
            if source_order.count(section_key) > 1:
                issues.append(_issue("blocker", "SECTION_ORDER_DUPLICATE", f"{stable_id}: sekcja {section_key} występuje wielokrotnie w order."))

        current_managed = [key for key in source_order if key in managed_keys]
        if len(current_managed) != len(desired_keys) or set(current_managed) != set(desired_keys):
            issues.append(_issue("blocker", "MANAGED_SET_MISMATCH", "Zestaw zarządzanych sekcji w index.json nie odpowiada rejestrowi Home Flow."))
        else:
            target_order = _replace_managed_slots(source_order, desired_keys, managed_keys)

    blockers = [row for row in issues if row["severity"] == "blocker"]
    changed = bool(target_order and source_order != target_order)
    changes: list[dict[str, Any]] = []
    if source_order and target_order:
        reverse = {key: stable for stable, key in stable_to_key.items()}
        for section_key in desired_keys:
            before = source_order.index(section_key)
            after = target_order.index(section_key)
            if before != after:
                changes.append({
                    "stable_id": reverse.get(section_key, section_key),
                    "section_key": section_key,
                    "from": before,
                    "to": after,
                })

    warnings: list[dict[str, str]] = []
    if not blockers and not changed:
        warnings.append(_issue("info", "NO_CHANGES", "Szkic nie zmienia rzeczywistej kolejności zarządzanych sekcji."))
    if source_order:
        unmanaged_count = len([key for key in source_order if key not in managed_keys])
        warnings.append(_issue("info", "UNMANAGED_PRESERVED", f"Writer zachowa bez zmian {unmanaged_count} niezarządzanych pozycji i podmieni tylko istniejące sloty Home Flow."))

    return {
        "schema": WRITER_SCHEMA_VERSION,
        "variant_id": str(variant_id),
        "index_path": str(index_path),
        "source_sha256": source_hash,
        "draft": working,
        "source_order": source_order,
        "target_order": target_order,
        "stable_to_key": stable_to_key,
        "changes": changes,
        "issues": issues,
        "warnings": warnings,
        "changed": changed,
        "ready": changed and not blockers,
        "writer_available": True,
        "writes_variant_only": True,
        "writes_theme": False,
        "deploys_shopify": False,
    }


def format_writer_plan(plan: dict[str, Any]) -> str:
    lines = [
        "HF-3B — BOUNDED WRITER",
        f"Wariant: {plan.get('variant_id', '')}",
        f"Cel zapisu: {plan.get('index_path', '')}",
        "",
        "Zakres bezpieczeństwa:",
        "  • tylko index.json wybranego wariantu",
        "  • dokładny backup przed zapisem",
        "  • zapis tymczasowy + atomic replace",
        "  • Undo tylko, gdy plik nie zmienił się po operacji",
        "  • zero templates/index.json, assetów i deployu Shopify",
        "",
        "Zmiany kolejności:",
    ]
    changes = list(plan.get("changes") or [])
    if changes:
        for row in changes:
            lines.append(f"  • {row.get('stable_id')} / {row.get('section_key')}: {int(row.get('from', 0)) + 1} → {int(row.get('to', 0)) + 1}")
    else:
        lines.append("  • Brak rzeczywistej zmiany kolejności.")

    issues = list(plan.get("issues") or [])
    if issues:
        lines.extend(["", "BLOKERY:"])
        lines.extend(f"  • [{row.get('code')}] {row.get('message')}" for row in issues)
    warnings = list(plan.get("warnings") or [])
    if warnings:
        lines.extend(["", "INFORMACJE:"])
        lines.extend(f"  • {row.get('message')}" for row in warnings)
    lines.extend(["", "Status:", "  GOTOWE — można zastosować szkic do lokalnego wariantu." if plan.get("ready") else "  ZABLOKOWANE albo brak zmian do zapisania."])
    return "\n".join(lines)


def load_writer_state(variant_id: str, *, variants_root: Path | None = None) -> dict[str, Any]:
    path = writer_state_path(variant_id, variants_root=variants_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def writer_undo_status(variant_id: str, *, variants_root: Path | None = None) -> dict[str, Any]:
    state = load_writer_state(variant_id, variants_root=variants_root)
    index_path = variant_index_path(variant_id, variants_root=variants_root)
    result = {"available": False, "reason": "Brak zapisanej operacji HF-3B.", "state": state}
    if not state:
        return result
    if state.get("undone_at"):
        result["reason"] = "Ostatnia operacja została już cofnięta."
        return result
    if not index_path.is_file():
        result["reason"] = "Brak index.json wariantu."
        return result

    expected_after = str(state.get("after_sha256") or "")
    current = sha256_file(index_path)
    if not expected_after or current != expected_after:
        result["reason"] = "index.json zmienił się po operacji HF-3B; bezpieczne Undo jest zablokowane."
        result["current_sha256"] = current
        return result

    backup_rel = str(state.get("backup_path") or "")
    backup = _variant_root(variant_id, variants_root=variants_root) / backup_rel
    if not backup.is_file():
        result["reason"] = "Brak dokładnego pliku backupu."
        return result
    expected_before = str(state.get("before_sha256") or "")
    if not expected_before or sha256_file(backup) != expected_before:
        result["reason"] = "Backup nie zgadza się z zapisanym hashem."
        return result

    result.update({
        "available": True,
        "reason": "Można bezpiecznie cofnąć ostatnią operację.",
        "backup_path": str(backup),
        "current_sha256": current,
    })
    return result


def apply_structure_draft_to_variant(
    variant_id: str,
    *,
    variants_root: Path | None = None,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Stosuje wyłącznie reorder istniejących sekcji do wariantu."""

    plan = build_writer_plan(variant_id, variants_root=variants_root)
    if expected_source_sha256 and plan.get("source_sha256") != expected_source_sha256:
        raise StructureWriterError("index.json zmienił się od czasu podglądu. Odśwież plan przed zapisem.")
    if not plan.get("ready"):
        messages = [str(row.get("message")) for row in plan.get("issues") or [] if row.get("severity") == "blocker"] or ["Brak bezpiecznej zmiany do zapisania."]
        raise StructureWriterError("\n".join(messages))

    index_path = variant_index_path(variant_id, variants_root=variants_root)
    before_bytes = index_path.read_bytes()
    before_hash = _sha256_bytes(before_bytes)
    if before_hash != plan.get("source_sha256"):
        raise StructureWriterError("index.json zmienił się podczas przygotowania operacji. Zapis przerwany.")

    template = copy.deepcopy(_load_json_file(index_path))
    template["order"] = list(plan["target_order"])
    after_bytes = _serialize_index(template)
    after_hash = _sha256_bytes(after_bytes)

    backup_dir = writer_backup_dir(variant_id, variants_root=variants_root)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"index-before-hf3b-{_timestamp()}-{before_hash[:10]}.json"
    shutil.copy2(index_path, backup_path)
    if sha256_file(backup_path) != before_hash:
        backup_path.unlink(missing_ok=True)
        raise StructureWriterError("Weryfikacja dokładnego backupu nie powiodła się.")

    variant_root = _variant_root(variant_id, variants_root=variants_root)
    state_path = writer_state_path(variant_id, variants_root=variants_root)
    previous_state = state_path.read_bytes() if state_path.is_file() else None
    try:
        _atomic_write_bytes(index_path, after_bytes)
        if sha256_file(index_path) != after_hash:
            raise StructureWriterError("Weryfikacja zapisanego index.json nie powiodła się.")
        state = {
            "schema": WRITER_SCHEMA_VERSION,
            "variant_id": str(variant_id),
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "backup_path": str(backup_path.relative_to(variant_root)),
            "before_sha256": before_hash,
            "after_sha256": after_hash,
            "before_order": list(plan["source_order"]),
            "after_order": list(plan["target_order"]),
            "changes": list(plan["changes"]),
            "undone_at": "",
        }
        _atomic_write_json(state_path, state)
    except Exception:
        _atomic_write_bytes(index_path, before_bytes)
        if previous_state is None:
            state_path.unlink(missing_ok=True)
        else:
            _atomic_write_bytes(state_path, previous_state)
        backup_path.unlink(missing_ok=True)
        raise

    return {
        "variant_id": str(variant_id),
        "index_path": str(index_path),
        "backup_path": str(backup_path),
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "changes": list(plan["changes"]),
    }


def undo_last_structure_write(variant_id: str, *, variants_root: Path | None = None) -> dict[str, Any]:
    status = writer_undo_status(variant_id, variants_root=variants_root)
    if not status.get("available"):
        raise StructureWriterError(str(status.get("reason") or "Undo jest niedostępne."))

    state = dict(status["state"])
    index_path = variant_index_path(variant_id, variants_root=variants_root)
    backup_path = Path(str(status["backup_path"]))
    backup_bytes = backup_path.read_bytes()
    before_hash = str(state["before_sha256"])
    if _sha256_bytes(backup_bytes) != before_hash:
        raise StructureWriterError("Backup zmienił się przed Undo. Operacja przerwana.")

    _atomic_write_bytes(index_path, backup_bytes)
    if sha256_file(index_path) != before_hash:
        raise StructureWriterError("Weryfikacja Undo nie powiodła się.")

    state["undone_at"] = datetime.now(timezone.utc).isoformat()
    state["undo_result_sha256"] = before_hash
    _atomic_write_json(writer_state_path(variant_id, variants_root=variants_root), state)
    return {
        "variant_id": str(variant_id),
        "index_path": str(index_path),
        "restored_from": str(backup_path),
        "restored_sha256": before_hash,
    }
