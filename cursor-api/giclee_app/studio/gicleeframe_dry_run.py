"""GICLÉE FRAME™ — dry-run planu użycia. Pure module: zero I/O zapisu."""

from __future__ import annotations

from dataclasses import dataclass

from giclee_app.studio.gicleeframe_brief import (
    AVOID_LIST,
    COMPONENT_NAME,
    DRY_RUN_BADGE,
    PLACEMENT_SUGGESTIONS,
    variant_by_id,
)
from giclee_app.studio.gicleeframe_draft_state import GicleeFrameDraftState

FUTURE_OUTPUT_SECTION = "Przyszły output Shopify (informacyjny)"
SHOPIFY_SCOPE_NOTE = "Shopify/sync/deploy: poza zakresem · implementacja motywu: not started."
F3_DISCLAIMER = "Plan informacyjny — writer: not started · brak zapisu do plików motywu."


@dataclass(frozen=True)
class GicleeFramePlanDryRun:
    """Opis przyszłego outputu — bez generowania plików motywu."""

    ok: bool
    errors: tuple[str, ...]
    operation_summary: str
    theme_snippet_hint: str
    variants_available: tuple[str, ...]
    placement_rationale: str
    avoid_notes: tuple[str, ...]
    status_badge: str = DRY_RUN_BADGE


def _theme_snippet_hint(variant_id: str, placement: str | None) -> str:
    placement_note = f" · placement={placement}" if placement else ""
    return (
        f"<!-- przyszły snippet motywu (dry-run, nie zapisano) -->\n"
        f'<div class="giclee-frame-mark giclee-frame-mark--{variant_id}"{placement_note}>\n'
        f'  <span class="giclee-frame-mark__text">{COMPONENT_NAME}</span>\n'
        f"</div>\n"
        f"/* CSS: museum-quality, prefers-reduced-motion, opacity + minimal translateY */"
    )


def build_gicleeframe_plan_dry_run(draft: GicleeFrameDraftState) -> GicleeFramePlanDryRun:
    """Pure dry-run — opis co komponent mógłby wygenerować później dla motywu."""
    if draft.is_empty():
        return GicleeFramePlanDryRun(
            ok=False,
            errors=("Wybierz wariant koncepcyjny.",),
            operation_summary="Plan zablokowany — brak wariantu",
            theme_snippet_hint="(brak — wybierz wariant)",
            variants_available=(),
            placement_rationale="",
            avoid_notes=AVOID_LIST,
        )

    variant = variant_by_id(draft.variant_id)
    if variant is None:
        return GicleeFramePlanDryRun(
            ok=False,
            errors=("Nieznany wariant.",),
            operation_summary="Plan zablokowany",
            theme_snippet_hint="",
            variants_available=(),
            placement_rationale="",
            avoid_notes=AVOID_LIST,
        )

    placement = draft.placement_id
    if placement:
        rationale = f"Strefa „{draft.placement_label_pl()}” — {variant.usage_hint}"
    else:
        rationale = (
            "Strefa nie wybrana — sugerowane miejsca: "
            + "; ".join(PLACEMENT_SUGGESTIONS[:3])
        )

    summary = f"{COMPONENT_NAME} · wariant {variant.label_pl}"
    if placement:
        summary = f"{summary} · {draft.placement_label_pl()}"

    return GicleeFramePlanDryRun(
        ok=True,
        errors=(),
        operation_summary=summary,
        theme_snippet_hint=_theme_snippet_hint(variant.variant_id, placement),
        variants_available=(variant.label_pl,),
        placement_rationale=rationale,
        avoid_notes=AVOID_LIST,
    )


def format_dry_run_summary(dry_run: GicleeFramePlanDryRun) -> str:
    lines = [
        FUTURE_OUTPUT_SECTION,
        f"Status: {dry_run.status_badge}",
        f"Operacja: {dry_run.operation_summary}",
        "",
        "Co komponent mógłby wygenerować później dla motywu:",
        dry_run.theme_snippet_hint,
        "",
        "Dostępne warianty (wybrany):",
        ", ".join(dry_run.variants_available) if dry_run.variants_available else "—",
        "",
        "Gdzie miałby sens na stronie:",
        dry_run.placement_rationale,
        "",
        "Czego unikać:",
    ]
    for note in dry_run.avoid_notes:
        lines.append(f"  • {note}")
    if dry_run.errors:
        lines.extend(["", "Błędy planu:"])
        for err in dry_run.errors:
            lines.append(f"  • {err}")
    lines.extend(["", F3_DISCLAIMER, SHOPIFY_SCOPE_NOTE])
    return "\n".join(lines)
