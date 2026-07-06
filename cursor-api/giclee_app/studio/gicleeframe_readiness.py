"""GICLÉE FRAME™ — readiness planu. Pure, zero I/O zapisu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from giclee_app.studio.gicleeframe_brief import NEXT_PHASE_NOTE
from giclee_app.studio.gicleeframe_draft_state import GicleeFrameDraftState
from giclee_app.studio.gicleeframe_dry_run import (
    F3_DISCLAIMER,
    GicleeFramePlanDryRun,
    SHOPIFY_SCOPE_NOTE,
)

READINESS_SECTION_LABEL = "Status gotowości"
WRITER_STATUS: Literal["blocked"] = "blocked"
SHOPIFY_IMPL_STATUS: Literal["not_started"] = "not_started"
SYNC_DEPLOY_STATUS: Literal["blocked"] = "blocked"

WRITER_BLOCK_REASON = "Writer/save: zablokowane"
F3_READINESS_DISCLAIMER = "local planning only — brak writera w tej fazie."
F5_FUTURE_NOTE = "Implementacja Shopify motywu: wymaga osobnej akceptacji fazy."

_STATUS_PLAN_READY = "plan gotowy (bez zapisu)"
_STATUS_BLOCKED = "zablokowane"
_STATUS_EMPTY = "brak planu"


@dataclass(frozen=True)
class GicleeFrameReadiness:
    """Ocena gotowości — save_ready zawsze False."""

    design_brief_ready: bool
    app_planning_ready: bool
    shopify_impl_status: Literal["not_started"]
    sync_deploy_status: Literal["blocked"]
    writer_status: Literal["blocked"]
    plan_complete: bool
    save_ready: bool
    block_reason: str
    status_label: str
    summary: str


@dataclass(frozen=True)
class ReadinessRow:
    label: str
    value: str
    ok: bool | None


def readiness_display_rows() -> list[ReadinessRow]:
    return [
        ReadinessRow("Design brief", "ready", True),
        ReadinessRow("App planning component", "ready", True),
        ReadinessRow("Shopify implementation", "not started", False),
        ReadinessRow("Sync/deploy", "zablokowane", False),
        ReadinessRow("Writer/save", "zablokowane", False),
    ]


def evaluate_gicleeframe_readiness(
    draft: GicleeFrameDraftState,
    dry_run: GicleeFramePlanDryRun,
) -> GicleeFrameReadiness:
    if draft.is_empty():
        return GicleeFrameReadiness(
            design_brief_ready=True,
            app_planning_ready=True,
            shopify_impl_status=SHOPIFY_IMPL_STATUS,
            sync_deploy_status=SYNC_DEPLOY_STATUS,
            writer_status=WRITER_STATUS,
            plan_complete=False,
            save_ready=False,
            block_reason=WRITER_BLOCK_REASON,
            status_label=_STATUS_EMPTY,
            summary="Wybierz wariant, aby wygenerować dry-run.",
        )

    if not dry_run.ok:
        return GicleeFrameReadiness(
            design_brief_ready=True,
            app_planning_ready=True,
            shopify_impl_status=SHOPIFY_IMPL_STATUS,
            sync_deploy_status=SYNC_DEPLOY_STATUS,
            writer_status=WRITER_STATUS,
            plan_complete=False,
            save_ready=False,
            block_reason=WRITER_BLOCK_REASON,
            status_label=_STATUS_BLOCKED,
            summary="Plan niekompletny — popraw wybór wariantu.",
        )

    return GicleeFrameReadiness(
        design_brief_ready=True,
        app_planning_ready=True,
        shopify_impl_status=SHOPIFY_IMPL_STATUS,
        sync_deploy_status=SYNC_DEPLOY_STATUS,
        writer_status=WRITER_STATUS,
        plan_complete=True,
        save_ready=False,
        block_reason=WRITER_BLOCK_REASON,
        status_label=_STATUS_PLAN_READY,
        summary="Dry-run OK — plan informacyjny gotowy. Zapis nadal zablokowany.",
    )


def format_readiness_block(readiness: GicleeFrameReadiness) -> str:
    lines = [
        READINESS_SECTION_LABEL,
        f"Status: {readiness.status_label}",
        f"Design brief: {'ready' if readiness.design_brief_ready else 'nie'}",
        f"App planning: {'ready' if readiness.app_planning_ready else 'nie'}",
        f"Shopify implementation: {readiness.shopify_impl_status}",
        f"Sync/deploy: {readiness.sync_deploy_status}",
        f"Writer: {readiness.writer_status}",
        f"Plan complete: {'tak' if readiness.plan_complete else 'nie'}",
        readiness.block_reason,
        readiness.summary,
        "",
        F3_READINESS_DISCLAIMER,
        SHOPIFY_SCOPE_NOTE,
        F5_FUTURE_NOTE,
        NEXT_PHASE_NOTE,
    ]
    return "\n".join(lines)
