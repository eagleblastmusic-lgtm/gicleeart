"""GICLÉE FRAME™ F2/F2.1 — structure dry-run. Pure, zero zapisu."""

from __future__ import annotations

from dataclasses import dataclass

from giclee_app.studio.gicleeframe_page_draft import (
    GicleeFramePageDraft,
    VARIANT_COMPARE_NOTE,
    patch_changed_fields,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    PageInventoryReport,
    inventory_count_stats,
)

STRUCTURE_DRY_RUN_BADGE = "dry-run struktury · nic nie zapisano"
STRUCTURE_SECTION_LABEL = "Dry-run struktury strony"
F3_LOCAL_DRAFT_NOTE = "F3: lokalny zapis draftu do pliku — po osobnej akceptacji."
F4_BOUNDED_WRITER_NOTE = (
    "F4: bounded writer do data/variants/{variant}/page.giclee-frame.json — po akceptacji."
)
F3_WRITER_SHAPE_NOTE = (
    "Writer F3 (po akceptacji): bounded PATCH do "
    "data/variants/{variant}/page.giclee-frame.json — sections.*.blocks.*.settings"
)

_GUARDRAILS = (
    "Brak zapisu do plików motywu w tej fazie",
    "Brak global typography reset",
    "Brak nowej biblioteki JS",
    "Synchronizacja/wdrożenie zablokowane",
    "Brak runtime mutation",
)


@dataclass(frozen=True)
class PageStructureDryRun:
    ok: bool
    variant_id: str | None
    draft_name: str
    draft_edit_count: int
    section_count: int
    separator_count: int
    image_count: int
    text_block_count: int
    source_section_count: int
    elements_total: int
    needs_review_ids: tuple[str, ...]
    draft_edited_ids: tuple[str, ...]
    draft_field_changes: tuple[tuple[str, tuple[str, ...]], ...]
    future_writer_shape: str
    f3_note: str
    f4_note: str
    guardrails: tuple[str, ...]
    status_badge: str = STRUCTURE_DRY_RUN_BADGE


def build_page_structure_dry_run(
    inventory: PageInventoryReport,
    draft: GicleeFramePageDraft,
) -> PageStructureDryRun:
    stats = inventory_count_stats(inventory)
    needs_review: list[str] = []
    draft_edited: list[str] = []
    field_changes: list[tuple[str, tuple[str, ...]]] = []

    for el in inventory.elements:
        if el.status in ("needs_review", "missing_content", "legacy_disabled"):
            needs_review.append(el.element_id)
        if el.element_id in draft.patches:
            draft_edited.append(el.element_id)

    for eid, patch in draft.patches.items():
        if eid not in draft_edited:
            draft_edited.append(eid)
        fields = patch_changed_fields(patch)
        if fields:
            field_changes.append((eid, fields))

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
        variant_id=inventory.variant_id,
        draft_name=draft.draft_name,
        draft_edit_count=draft.draft_edit_count(),
        section_count=stats["media_sections"],
        separator_count=stats["separators"],
        image_count=stats["images"],
        text_block_count=stats["text_blocks"],
        source_section_count=stats["source_sections"],
        elements_total=stats["elements_total"],
        needs_review_ids=tuple(needs_review),
        draft_edited_ids=tuple(draft_edited),
        draft_field_changes=tuple(field_changes),
        future_writer_shape=writer_shape,
        f3_note=F3_LOCAL_DRAFT_NOTE,
        f4_note=F4_BOUNDED_WRITER_NOTE.format(variant=variant),
        guardrails=_GUARDRAILS,
    )


def format_structure_dry_run_summary(dry_run: PageStructureDryRun) -> str:
    lines = [
        STRUCTURE_SECTION_LABEL,
        f"Status: {dry_run.status_badge}",
        "",
        f"Wariant źródłowy (inventory): {dry_run.variant_id or '—'}",
        f"Wariant roboczy RAM: {dry_run.draft_name}",
        f"Zmiany w wariancie: {dry_run.draft_edit_count}",
        "Potwierdzenie: nic nie zapisano",
        VARIANT_COMPARE_NOTE,
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
            fields = next(
                (f for e, f in dry_run.draft_field_changes if e == eid),
                (),
            )
            if fields:
                lines.append(f"  • {eid} — pola: {', '.join(fields)}")
            else:
                lines.append(f"  • {eid}")
    else:
        lines.append("  (brak)")

    lines.extend([
        "",
        "Przyszły kierunek:",
        f"  • {dry_run.f3_note}",
        f"  • {dry_run.f4_note}",
        "",
        "Przyszła struktura danych writera (informacyjnie):",
        dry_run.future_writer_shape,
        "",
        "Guardrails:",
    ])
    for g in dry_run.guardrails:
        lines.append(f"  • {g}")

    return "\n".join(lines)
