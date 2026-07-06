"""Save readiness + ref policy — Studio Preview (F5.4b0 / F5.4d). Pure, zero I/O zapisu."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from giclee_app.studio.background_asset_catalog import (
    build_background_asset_catalog,
    resolve_selected_asset_ref,
    validate_selected_asset_id,
)
from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_contract import (
    VIDEO_COLLAGE_SCOPE_ERROR,
    build_background_save_dry_run,
    validate_background_save_request,
)
from giclee_app.studio.background_state import (
    read_stronaglowna_index_template,
    section_bg_current_ref,
)

SaveOperation = Literal["noop", "clear", "set_with_ref"]

READINESS_SECTION_LABEL = "Gotowość zapisu"
F54B0_DISCLAIMER = "F5.4b1: zapis lokalny dostępny tylko dla wyczyść tło."
F54B1_FUTURE_NOTE = "Zapis z ref (set_with_ref) wymaga F5.4b2."
F54B2_PENDING_NOTE = "Draft kompletny — realny zapis z ref w F5.4b2."
SAVE_LOCAL_LABEL = "Zapisz lokalnie"
SAVE_LOCAL_STATUS = "zapisano lokalnie · bez Shopify"
UNDO_LAST_SAVE_LABEL = "Cofnij ostatni zapis"
UNDO_RESTORE_STATUS = "przywrócono lokalnie · bez Shopify"
LAST_BACKUP_LABEL = "Ostatni backup:"
CLEAR_PLAN_CHECKBOX = "Plan: wyczyść tło w strefie"

_STATUS_READY = "gotowe"
_STATUS_BLOCKED = "zablokowane"
_STATUS_NOOP = "bez zmian"
_STATUS_F54B2 = "gotowe · F5.4b2"

_BLOCK_KIND_CHANGE = "Zmiana typu wymaga wyboru assetu."
_BLOCK_BRAK_TO_KIND = "Ustawienie tła z „brak” wymaga wyboru assetu."
_BLOCK_SET_WITH_REF = "Ustawienie nowego assetu wymaga wyboru ref (F5.4d)."
_BLOCK_INVALID_REF = "Wybrany asset jest nieprawidłowy lub nie pasuje do typu draftu."
_BLOCK_VALIDATION = "Draft lub dane wariantu nie przechodzą walidacji."


@dataclass(frozen=True)
class SaveReadiness:
    """Wynik oceny gotowości zapisu — bez mutacji plików."""

    ready: bool
    operation: SaveOperation | None
    block_reason: str | None
    requires_confirm: bool
    summary: str
    status_label: str
    ref_complete: bool


def evaluate_save_readiness(
    draft: BackgroundDraftState,
    package_path: Path,
    *,
    clear_intent: bool = False,
) -> SaveReadiness:
    """Ocena ref policy i gotowości — bez I/O zapisu i bez writera."""
    validation = validate_background_save_request(draft, package_path)
    if not validation.ok:
        reason = validation.errors[0] if validation.errors else _BLOCK_VALIDATION
        return SaveReadiness(
            ready=False,
            operation=None,
            block_reason=reason,
            requires_confirm=False,
            summary=_format_summary(_STATUS_BLOCKED, reason, None),
            status_label=_STATUS_BLOCKED,
            ref_complete=False,
        )

    if draft.asset_kind == "video_collage":
        return SaveReadiness(
            ready=False,
            operation=None,
            block_reason=VIDEO_COLLAGE_SCOPE_ERROR,
            requires_confirm=False,
            summary=_format_summary(_STATUS_BLOCKED, VIDEO_COLLAGE_SCOPE_ERROR, None),
            status_label=_STATUS_BLOCKED,
            ref_complete=False,
        )

    dry_run = build_background_save_dry_run(draft, package_path)
    if not dry_run.ok:
        reason = dry_run.errors[0] if dry_run.errors else _BLOCK_VALIDATION
        return SaveReadiness(
            ready=False,
            operation=None,
            block_reason=reason,
            requires_confirm=False,
            summary=_format_summary(_STATUS_BLOCKED, reason, None),
            status_label=_STATUS_BLOCKED,
            ref_complete=False,
        )

    catalog = build_background_asset_catalog(package_path)
    has_valid_ref = validate_selected_asset_id(
        draft.selected_asset_id,
        catalog,
        asset_kind=draft.asset_kind,
    )

    if clear_intent:
        if dry_run.current_status == "brak":
            return SaveReadiness(
                ready=False,
                operation=None,
                block_reason="Strefa nie ma tła do wyczyszczenia.",
                requires_confirm=False,
                summary=_format_summary(
                    _STATUS_BLOCKED,
                    "Strefa nie ma tła do wyczyszczenia.",
                    None,
                ),
                status_label=_STATUS_BLOCKED,
                ref_complete=has_valid_ref,
            )
        return SaveReadiness(
            ready=True,
            operation="clear",
            block_reason=None,
            requires_confirm=True,
            summary=_format_summary(
                _STATUS_READY,
                None,
                "Plan: wyczyść tło w strefie · użyj „Zapisz lokalnie”.",
            ),
            status_label=_STATUS_READY,
            ref_complete=has_valid_ref,
        )

    current = dry_run.current_status
    target = dry_run.target_kind_pl

    if current == "brak" and target in ("obraz", "wideo"):
        if not has_valid_ref:
            return SaveReadiness(
                ready=False,
                operation="set_with_ref",
                block_reason=_BLOCK_BRAK_TO_KIND,
                requires_confirm=False,
                summary=_format_summary(_STATUS_BLOCKED, _BLOCK_BRAK_TO_KIND, None),
                status_label=_STATUS_BLOCKED,
                ref_complete=False,
            )
        return _pending_f54b2(
            "Plan: ustaw tło z wybranym assetem · zapis w F5.4b2.",
        )

    if not dry_run.type_unchanged:
        if not has_valid_ref:
            return SaveReadiness(
                ready=False,
                operation="set_with_ref",
                block_reason=_BLOCK_KIND_CHANGE,
                requires_confirm=False,
                summary=_format_summary(_STATUS_BLOCKED, _BLOCK_KIND_CHANGE, None),
                status_label=_STATUS_BLOCKED,
                ref_complete=False,
            )
        return _pending_f54b2(
            f"Plan: zmiana typu ({current} → {target}) z wybranym assetem · F5.4b2.",
        )

    if current != "brak" and dry_run.type_unchanged:
        if has_valid_ref:
            index_template = read_stronaglowna_index_template(package_path)
            zone = _zone_for_field_id(draft.zone_field_id)
            if index_template is not None and zone is not None:
                current_ref = section_bg_current_ref(index_template, zone)
                selected_ref = resolve_selected_asset_ref(
                    catalog,
                    draft.selected_asset_id,
                )
                if (
                    current_ref is not None
                    and selected_ref is not None
                    and selected_ref == current_ref.ref
                ):
                    return SaveReadiness(
                        ready=False,
                        operation="noop",
                        block_reason=None,
                        requires_confirm=False,
                        summary=_format_summary(
                            _STATUS_NOOP,
                            None,
                            "Ten sam typ i ten sam asset — zapis nie jest potrzebny.",
                        ),
                        status_label=_STATUS_NOOP,
                        ref_complete=True,
                    )
            return _pending_f54b2(
                "Plan: zamiana assetu przy tym samym typie · F5.4b2.",
            )
        return SaveReadiness(
            ready=False,
            operation="noop",
            block_reason=None,
            requires_confirm=False,
            summary=_format_summary(
                _STATUS_NOOP,
                None,
                "Typ zgodny z obecnym stanem — zapis nie jest potrzebny.",
            ),
            status_label=_STATUS_NOOP,
            ref_complete=False,
        )

    if draft.selected_asset_id and not has_valid_ref:
        return SaveReadiness(
            ready=False,
            operation="set_with_ref",
            block_reason=_BLOCK_INVALID_REF,
            requires_confirm=False,
            summary=_format_summary(_STATUS_BLOCKED, _BLOCK_INVALID_REF, None),
            status_label=_STATUS_BLOCKED,
            ref_complete=False,
        )

    return SaveReadiness(
        ready=False,
        operation="set_with_ref",
        block_reason=_BLOCK_SET_WITH_REF,
        requires_confirm=False,
        summary=_format_summary(_STATUS_BLOCKED, _BLOCK_SET_WITH_REF, None),
        status_label=_STATUS_BLOCKED,
        ref_complete=False,
    )


def _pending_f54b2(detail: str) -> SaveReadiness:
    return SaveReadiness(
        ready=False,
        operation="set_with_ref",
        block_reason=None,
        requires_confirm=False,
        summary=_format_summary(_STATUS_F54B2, None, detail),
        status_label=_STATUS_F54B2,
        ref_complete=True,
    )


def format_readiness_block(summary: str, *, clear_ready: bool = False) -> str:
    """Blok gotowości do panelu — bez URL/ref/ścieżek."""
    lines = [READINESS_SECTION_LABEL, summary]
    if clear_ready:
        lines.append("Operacja clear gotowa — dostępny przycisk „Zapisz lokalnie”.")
    elif "F5.4b2" in summary:
        lines.append(F54B2_PENDING_NOTE)
    lines.extend(["", F54B0_DISCLAIMER, F54B1_FUTURE_NOTE])
    return "\n".join(lines)


def _format_summary(
    status: str,
    block_reason: str | None,
    detail: str | None,
) -> str:
    lines = [f"Status: {status}"]
    if block_reason:
        lines.append(f"Powód: {block_reason}")
    if detail:
        lines.append(detail)
    op_hint = _operation_hint(status, block_reason)
    if op_hint:
        lines.append(op_hint)
    return "\n".join(lines)


def _operation_hint(status: str, block_reason: str | None) -> str:
    if status == _STATUS_NOOP:
        return "Operacja: noop — bez mutacji index.json."
    if status == _STATUS_READY:
        return "Operacja: clear — gotowe do zapisu lokalnego (F5.4b1)."
    if status == _STATUS_F54B2:
        return "Operacja: set_with_ref — draft kompletny · zapis w F5.4b2."
    if block_reason and "assetu" in block_reason.lower():
        return "Operacja: set_with_ref — wymaga wyboru assetu (F5.4d)."
    return ""


def _zone_for_field_id(field_id: str | None):
    from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

    if not field_id:
        return None
    for zone in STRONAGLOWNA_SECTION_BGS:
        if zone.field_id == field_id:
            return zone
    return None


__all__ = [
    "CLEAR_PLAN_CHECKBOX",
    "F54B0_DISCLAIMER",
    "F54B1_FUTURE_NOTE",
    "F54B2_PENDING_NOTE",
    "READINESS_SECTION_LABEL",
    "SAVE_LOCAL_LABEL",
    "SAVE_LOCAL_STATUS",
    "UNDO_LAST_SAVE_LABEL",
    "UNDO_RESTORE_STATUS",
    "LAST_BACKUP_LABEL",
    "SaveOperation",
    "SaveReadiness",
    "evaluate_save_readiness",
    "format_readiness_block",
]
