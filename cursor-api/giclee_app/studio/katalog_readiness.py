"""Katalog F4 — readiness planu zmian. Pure, zero I/O zapisu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from giclee_app.studio.katalog_draft_state import KatalogDraftState
from giclee_app.studio.katalog_dry_run import (
    KatalogPlanDryRun,
    SHOPIFY_SCOPE_NOTE,
)

READINESS_SECTION_LABEL = "Gotowość planu"
WRITER_STATUS: Literal["not_started"] = "not_started"
WRITER_BLOCK_REASON = "writer: not started · zapis zablokowany"
F3_READINESS_DISCLAIMER = "local planning only — brak writera w tej fazie."
F5_FUTURE_NOTE = "Bounded local writer (F5+): wymaga finalized data map + osobnej fazy."

_STATUS_PLAN_READY = "plan gotowy (bez zapisu)"
_STATUS_BLOCKED = "zablokowane"
_STATUS_EMPTY = "brak planu"


@dataclass(frozen=True)
class KatalogPlanReadiness:
    """Ocena gotowości planu — save_ready zawsze False dopóki writer nie istnieje."""

    plan_complete: bool
    save_ready: bool
    writer_status: Literal["not_started"]
    block_reason: str
    status_label: str
    summary: str


def evaluate_katalog_plan_readiness(
    draft: KatalogDraftState,
    dry_run: KatalogPlanDryRun,
) -> KatalogPlanReadiness:
    if draft.is_empty():
        return KatalogPlanReadiness(
            plan_complete=False,
            save_ready=False,
            writer_status=WRITER_STATUS,
            block_reason=WRITER_BLOCK_REASON,
            status_label=_STATUS_EMPTY,
            summary="Wybierz intencję planu, aby wygenerować dry-run.",
        )

    if not dry_run.ok:
        return KatalogPlanReadiness(
            plan_complete=False,
            save_ready=False,
            writer_status=WRITER_STATUS,
            block_reason=WRITER_BLOCK_REASON,
            status_label=_STATUS_BLOCKED,
            summary="Plan niekompletny — popraw draft lub inventory.",
        )

    return KatalogPlanReadiness(
        plan_complete=True,
        save_ready=False,
        writer_status=WRITER_STATUS,
        block_reason=WRITER_BLOCK_REASON,
        status_label=_STATUS_PLAN_READY,
        summary="Dry-run OK — plan informacyjny gotowy. Zapis nadal zablokowany.",
    )


def format_readiness_block(readiness: KatalogPlanReadiness) -> str:
    lines = [
        READINESS_SECTION_LABEL,
        f"Status: {readiness.status_label}",
        f"Plan complete: {'tak' if readiness.plan_complete else 'nie'}",
        f"Writer: {readiness.writer_status}",
        readiness.block_reason,
        readiness.summary,
        "",
        F3_READINESS_DISCLAIMER,
        SHOPIFY_SCOPE_NOTE,
        F5_FUTURE_NOTE,
    ]
    return "\n".join(lines)
