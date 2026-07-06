"""GICLÉE FRAME™ F2 — structure dry-run. Pure, zero zapisu."""

from __future__ import annotations

from dataclasses import dataclass

from giclee_app.studio.gicleeframe_page_draft import GicleeFramePageDraft
from giclee_app.studio.gicleeframe_page_inventory import (
    PageInventoryReport,
    inventory_count_stats,
)

STRUCTURE_DRY_RUN_BADGE = "dry-run struktury · nic nie zapisano"
STRUCTURE_SECTION_LABEL = "Dry-run struktury strony"
F3_WRITER_SHAPE_NOTE = (
    "Writer F3 (po akceptacji): bounded PATCH do "
    "data/variants/{variant}/page.giclee-frame.json — sections.*.blocks.*.settings"
)

_GUARDRAILS = (
    "Brak zapisu do plików motywu w tej fazie",
    "Brak global typography reset",
    "Brak nowej biblioteki JS",
    "Brak deploy / sync / runtime mutation",
)


@dataclass(frozen=True)
class PageStructureDryRun:
    ok: bool
    section_count: int
    separator_count: int
    image_count: int
    text_block_count: int
    source_section_count: int
    elements_total: int
    needs_review_ids: tuple[str, ...]
    draft_edited_ids: tuple[str, ...]
    future_writer_shape: str
    guardrails: tuple[str, ...]
    status_badge: str = STRUCTURE_DRY_RUN_BADGE


def build_page_structure_dry_run(
    inventory: PageInventoryReport,
    draft: GicleeFramePageDraft,
) -> PageStructureDryRun:
    stats = inventory_count_stats(inventory)
    needs_review: list[str] = []
    draft_edited: list[str] = []

    for el in inventory.elements:
        if el.status in ("needs_review", "missing_content", "legacy_disabled"):
            needs_review.append(el.element_id)
        if el.element_id in draft.patches:
            draft_edited.append(el.element_id)

    for eid in draft.patches:
        if eid not in draft_edited:
            draft_edited.append(eid)

    ok = inventory.source_section_count > 0 and len(inventory.elements) > 0
    variant = inventory.variant_id or "{variant}"
    writer_shape = (
        f"{F3_WRITER_SHAPE_NOTE.format(variant=variant)}\n"
        "Przykład ścieżek (informacyjnie):\n"
        f"  sections.<section_key>.blocks.content.blocks.<block_id>.settings.text\n"
        f"  sections.<section_key>.blocks.media.settings.image\n"
        "Status: not started · save_ready: false"
    )

    return PageStructureDryRun(
        ok=ok,
        section_count=stats["media_sections"],
        separator_count=stats["separators"],
        image_count=stats["images"],
        text_block_count=stats["text_blocks"],
        source_section_count=stats["source_sections"],
        elements_total=stats["elements_total"],
        needs_review_ids=tuple(needs_review),
        draft_edited_ids=tuple(draft_edited),
        future_writer_shape=writer_shape,
        guardrails=_GUARDRAILS,
    )


def format_structure_dry_run_summary(dry_run: PageStructureDryRun) -> str:
    lines = [
        STRUCTURE_SECTION_LABEL,
        f"Status: {dry_run.status_badge}",
        "",
        "Podsumowanie struktury:",
        f"  Źródłowe sekcje (order[]): {dry_run.source_section_count}",
        f"  Elementy inventory (rozwinięte): {dry_run.elements_total}",
        f"  Sekcje media: {dry_run.section_count}",
        f"  Separatory: {dry_run.separator_count}",
        f"  Grafiki: {dry_run.image_count}",
        f"  Bloki tekstowe: {dry_run.text_block_count}",
        "",
        "Elementy wymagające sprawdzenia:",
    ]
    if dry_run.needs_review_ids:
        for eid in dry_run.needs_review_ids[:20]:
            lines.append(f"  • {eid}")
        if len(dry_run.needs_review_ids) > 20:
            lines.append(f"  … i {len(dry_run.needs_review_ids) - 20} więcej")
    else:
        lines.append("  (brak)")

    lines.extend(["", "Elementy z edycją RAM draft:"])
    if dry_run.draft_edited_ids:
        for eid in dry_run.draft_edited_ids:
            lines.append(f"  • {eid}")
    else:
        lines.append("  (brak)")

    lines.extend([
        "",
        "Przyszła struktura danych writera (informacyjnie):",
        dry_run.future_writer_shape,
        "",
        "Guardrails:",
    ])
    for g in dry_run.guardrails:
        lines.append(f"  • {g}")

    return "\n".join(lines)
