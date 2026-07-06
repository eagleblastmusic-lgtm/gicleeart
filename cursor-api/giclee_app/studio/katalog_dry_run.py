"""Katalog F3/F4 — dry-run planu zmian. Pure module: zero I/O zapisu."""

from __future__ import annotations

from dataclasses import dataclass

from giclee_app.studio.katalog_data_map import KatalogDataMap
from giclee_app.studio.katalog_draft_state import (
    KatalogDraftState,
    intent_requires_variant,
    intent_requires_zone,
)
from giclee_app.studio.katalog_inventory import KatalogInventoryReport

DRY_RUN_BADGE = "dry-run · nic nie zapisano"
F3_DISCLAIMER = "Plan informacyjny — writer: not started · brak zapisu do plików."
SHOPIFY_SCOPE_NOTE = "Shopify/sync/deploy: poza zakresem · tylko legacy katalog w Level 2."

_FIELDS_BY_INTENT: dict[str, tuple[str, ...]] = {
    "review_structure": ("manifest", "sections"),
    "plan_collection_layout": ("sections", "collection.json"),
    "plan_zone_settings": ("sections", "background_image", "zone_id"),
}

_TARGET_BY_INTENT: dict[str, str] = {
    "review_structure": "legacy katalog · struktura wariantów",
    "plan_collection_layout": "legacy collection.json · układ sekcji",
    "plan_zone_settings": "legacy collection.json + registry zone",
}


@dataclass(frozen=True)
class KatalogPlanDryRun:
    """Plan zmian — semantic diff bez wartości ref/URL/ścieżek."""

    ok: bool
    errors: tuple[str, ...]
    operation_summary: str
    target_owner: str
    fields_touched: tuple[str, ...]
    blocked_paths: tuple[str, ...]
    status_badge: str = DRY_RUN_BADGE


def _dual_persistence_active(data_map: KatalogDataMap) -> bool:
    return any(w.code == "dual_persistence" for w in data_map.warnings)


def _validate_draft(
    draft: KatalogDraftState,
    inventory: KatalogInventoryReport,
) -> tuple[str, ...]:
    if draft.is_empty():
        return ("Brak wybranej intencji planu.",)

    errors: list[str] = []
    intent = draft.plan_intent

    if intent_requires_variant(intent) and not draft.variant_id:
        errors.append("Ta intencja wymaga wyboru wariantu.")

    if intent_requires_zone(intent) and not draft.zone_id:
        errors.append("Ta intencja wymaga wyboru strefy.")

    if draft.variant_id:
        known = inventory.katalog.variant_ids
        if known and draft.variant_id not in known:
            errors.append("Wybrany wariant nie występuje w inventory F1.")

    if draft.zone_id:
        known_zones = inventory.katalog.registry_zone_ids
        if known_zones and draft.zone_id not in known_zones:
            errors.append("Wybrana strefa nie występuje w registry (bounded scan).")

    return tuple(errors)


def _build_operation_summary(draft: KatalogDraftState) -> str:
    intent = draft.plan_intent or ""
    base = _TARGET_BY_INTENT.get(intent, "legacy katalog")
    if draft.variant_id:
        base = f"{base} · wariant {draft.variant_id}"
    if draft.zone_id:
        base = f"{base} · strefa {draft.zone_id}"
    return base


def _blocked_paths_for_map(data_map: KatalogDataMap) -> tuple[str, ...]:
    blocked: list[str] = ["Shopify · metafields · Files", "tldobio cache · absorbed"]
    if _dual_persistence_active(data_map):
        blocked.append("dual persistence — brak unified write policy")
    if data_map.external_shopify.write_policy == "out_of_scope":
        blocked.append("external sync/deploy")
    return tuple(blocked)


def build_katalog_plan_dry_run(
    draft: KatalogDraftState,
    inventory: KatalogInventoryReport,
    data_map: KatalogDataMap,
) -> KatalogPlanDryRun:
    """Pure dry-run — wymaga obiektów F1/F2 już zbudowanych przez caller."""
    errors = _validate_draft(draft, inventory)
    intent = draft.plan_intent or ""
    fields = _FIELDS_BY_INTENT.get(intent, ())
    blocked = _blocked_paths_for_map(data_map)
    target = _TARGET_BY_INTENT.get(intent, "legacy katalog")

    if errors:
        return KatalogPlanDryRun(
            ok=False,
            errors=errors,
            operation_summary="Plan zablokowany — uzupełnij draft",
            target_owner=target,
            fields_touched=fields,
            blocked_paths=blocked,
        )

    summary = _build_operation_summary(draft)
    if not inventory.katalog.root_exists:
        return KatalogPlanDryRun(
            ok=False,
            errors=("Legacy katalog nie wykryty w inventory — plan tylko informacyjny.",),
            operation_summary=summary,
            target_owner=target,
            fields_touched=fields,
            blocked_paths=blocked,
        )

    return KatalogPlanDryRun(
        ok=True,
        errors=(),
        operation_summary=summary,
        target_owner=target,
        fields_touched=fields,
        blocked_paths=blocked,
    )


def format_dry_run_summary(dry_run: KatalogPlanDryRun) -> str:
    lines = [DRY_RUN_BADGE, ""]
    if dry_run.errors:
        lines.append("Błędy planu:")
        for err in dry_run.errors:
            lines.append(f"• {err}")
        lines.append("")
    lines.append(f"Cel: {dry_run.operation_summary}")
    lines.append(f"Owner: {dry_run.target_owner}")
    if dry_run.fields_touched:
        lines.append(f"Pola (koncept): {', '.join(dry_run.fields_touched)}")
    if dry_run.blocked_paths:
        lines.append("Poza zakresem planu lokalnego:")
        for path in dry_run.blocked_paths:
            lines.append(f"• {path}")
    lines.append("")
    lines.append(F3_DISCLAIMER)
    lines.append(SHOPIFY_SCOPE_NOTE)
    return "\n".join(lines)
