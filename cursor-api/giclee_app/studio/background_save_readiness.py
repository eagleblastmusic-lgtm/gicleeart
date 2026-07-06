"""Save readiness + ref policy — Studio Preview (F5.4b0). Pure, zero I/O zapisu."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_contract import (
    VIDEO_COLLAGE_SCOPE_ERROR,
    build_background_save_dry_run,
    validate_background_save_request,
)

SaveOperation = Literal["noop", "clear", "set_with_ref"]

READINESS_SECTION_LABEL = "Gotowość zapisu"
F54B0_DISCLAIMER = "F5.4b0 nadal nic nie zapisuje."
F54B1_FUTURE_NOTE = "Realny zapis będzie osobną fazą F5.4b1."
CLEAR_PLAN_CHECKBOX = "Plan: wyczyść tło w strefie (F5.4b1 — bez zapisu teraz)"

_STATUS_READY = "gotowe"
_STATUS_BLOCKED = "zablokowane"
_STATUS_NOOP = "bez zmian"

_BLOCK_KIND_CHANGE = "Zmiana typu wymaga wyboru assetu."
_BLOCK_BRAK_TO_KIND = "Ustawienie tła z „brak” wymaga wyboru assetu."
_BLOCK_SET_WITH_REF = "Ustawienie nowego assetu wymaga wyboru ref (F5.4d)."
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
        )

    if draft.asset_kind == "video_collage":
        return SaveReadiness(
            ready=False,
            operation=None,
            block_reason=VIDEO_COLLAGE_SCOPE_ERROR,
            requires_confirm=False,
            summary=_format_summary(_STATUS_BLOCKED, VIDEO_COLLAGE_SCOPE_ERROR, None),
            status_label=_STATUS_BLOCKED,
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
            )
        return SaveReadiness(
            ready=True,
            operation="clear",
            block_reason=None,
            requires_confirm=True,
            summary=_format_summary(
                _STATUS_READY,
                None,
                "Plan: wyczyść tło w strefie (zapis w F5.4b1).",
            ),
            status_label=_STATUS_READY,
        )

    current = dry_run.current_status
    target = dry_run.target_kind_pl

    if current == "brak" and target in ("obraz", "wideo"):
        return SaveReadiness(
            ready=False,
            operation="set_with_ref",
            block_reason=_BLOCK_BRAK_TO_KIND,
            requires_confirm=False,
            summary=_format_summary(_STATUS_BLOCKED, _BLOCK_BRAK_TO_KIND, None),
            status_label=_STATUS_BLOCKED,
        )

    if not dry_run.type_unchanged:
        return SaveReadiness(
            ready=False,
            operation="set_with_ref",
            block_reason=_BLOCK_KIND_CHANGE,
            requires_confirm=False,
            summary=_format_summary(_STATUS_BLOCKED, _BLOCK_KIND_CHANGE, None),
            status_label=_STATUS_BLOCKED,
        )

    if current != "brak" and dry_run.type_unchanged:
        return SaveReadiness(
            ready=True,
            operation="noop",
            block_reason=None,
            requires_confirm=False,
            summary=_format_summary(
                _STATUS_NOOP,
                None,
                "Typ zgodny z obecnym stanem — zapis nie jest potrzebny.",
            ),
            status_label=_STATUS_NOOP,
        )

    return SaveReadiness(
        ready=False,
        operation="set_with_ref",
        block_reason=_BLOCK_SET_WITH_REF,
        requires_confirm=False,
        summary=_format_summary(_STATUS_BLOCKED, _BLOCK_SET_WITH_REF, None),
        status_label=_STATUS_BLOCKED,
    )


def format_readiness_block(summary: str) -> str:
    """Blok gotowości do panelu — bez URL/ref/ścieżek."""
    lines = [READINESS_SECTION_LABEL, summary, "", F54B0_DISCLAIMER, F54B1_FUTURE_NOTE]
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
        return "Operacja: clear — plan gotowy, zapis dopiero w F5.4b1."
    if block_reason and "assetu" in block_reason.lower():
        return "Operacja: set_with_ref — wymaga F5.4d."
    return ""


__all__ = [
    "CLEAR_PLAN_CHECKBOX",
    "F54B0_DISCLAIMER",
    "F54B1_FUTURE_NOTE",
    "READINESS_SECTION_LABEL",
    "SaveOperation",
    "SaveReadiness",
    "evaluate_save_readiness",
    "format_readiness_block",
]
