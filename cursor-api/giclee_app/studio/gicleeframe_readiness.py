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
from giclee_app.studio.gicleeframe_page_dry_run import PageStructureDryRun
from giclee_app.studio.gicleeframe_page_inventory import PageInventoryReport

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


@dataclass(frozen=True)
class GicleeFramePageReadiness:
    page_inventory_ready: bool
    ram_draft_ready: bool
    structure_dry_run_ready: bool
    shopify_writer_status: Literal["blocked"]
    save_apply_status: Literal["blocked"]
    sync_deploy_status: Literal["blocked"]
    runtime_mutation_status: Literal["blocked"]
    save_ready: bool
    status_label: str
    summary: str


F2_READINESS_NOTE = "F3: bounded writer do variant JSON — po osobnej akceptacji."


def readiness_page_display_rows(
    readiness: GicleeFramePageReadiness | None = None,
) -> list[ReadinessRow]:
    r = readiness
    return [
        ReadinessRow(
            "Page inventory",
            "ready" if r and r.page_inventory_ready else "—",
            True if r and r.page_inventory_ready else None,
        ),
        ReadinessRow(
            "RAM draft editing",
            "ready",
            True,
        ),
        ReadinessRow(
            "Structure dry-run",
            "ready" if r and r.structure_dry_run_ready else "oczekuje",
            True if r and r.structure_dry_run_ready else False,
        ),
        ReadinessRow("Shopify writer", "blocked", False),
        ReadinessRow("Save/Zapisz/Zastosuj", "blocked", False),
        ReadinessRow("Sync/deploy", "blocked", False),
        ReadinessRow("Runtime mutation", "blocked", False),
    ]


def evaluate_gicleeframe_page_readiness(
    inventory: PageInventoryReport,
    dry_run: PageStructureDryRun,
) -> GicleeFramePageReadiness:
    inv_ready = inventory.source_section_count > 0 and len(inventory.elements) > 0
    spec_ready = dry_run.ok and inv_ready

    if not inv_ready:
        return GicleeFramePageReadiness(
            page_inventory_ready=False,
            ram_draft_ready=True,
            structure_dry_run_ready=False,
            shopify_writer_status=WRITER_STATUS,
            save_apply_status=WRITER_STATUS,
            sync_deploy_status=SYNC_DEPLOY_STATUS,
            runtime_mutation_status=WRITER_STATUS,
            save_ready=False,
            status_label="brak inventory",
            summary="Odśwież inventory lub sprawdź ścieżkę wariantu.",
        )

    return GicleeFramePageReadiness(
        page_inventory_ready=True,
        ram_draft_ready=True,
        structure_dry_run_ready=spec_ready,
        shopify_writer_status=WRITER_STATUS,
        save_apply_status=WRITER_STATUS,
        sync_deploy_status=SYNC_DEPLOY_STATUS,
        runtime_mutation_status=WRITER_STATUS,
        save_ready=False,
        status_label="struktura gotowa (bez zapisu)" if spec_ready else "zablokowane",
        summary="Structure dry-run OK — spec informacyjny. Zapis nadal zablokowany.",
    )


def format_page_readiness_block(readiness: GicleeFramePageReadiness) -> str:
    lines = [
        "Status gotowości (strona)",
        f"Status: {readiness.status_label}",
        f"Page inventory: {'ready' if readiness.page_inventory_ready else 'nie'}",
        f"RAM draft editing: ready",
        f"Structure dry-run: {'ready' if readiness.structure_dry_run_ready else 'nie'}",
        f"Shopify writer: {readiness.shopify_writer_status}",
        f"Save/Zapisz/Zastosuj: {readiness.save_apply_status}",
        f"Sync/deploy: {readiness.sync_deploy_status}",
        f"Runtime mutation: {readiness.runtime_mutation_status}",
        readiness.summary,
        "",
        F3_READINESS_DISCLAIMER,
        SHOPIFY_SCOPE_NOTE,
        F2_READINESS_NOTE,
        NEXT_PHASE_NOTE,
    ]
    return "\n".join(lines)


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
