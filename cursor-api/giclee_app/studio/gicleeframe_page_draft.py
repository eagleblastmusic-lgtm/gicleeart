"""GICLÉE FRAME™ F2 — RAM draft edycji elementów strony. Zero I/O."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from giclee_app.studio.gicleeframe_page_inventory import (
    PageElement,
    PageInventoryReport,
)

DRAFT_RAM_DISCLAIMER = (
    "Zmiany są tylko lokalnym draftem w pamięci — nic nie zapisano."
)
CLEAR_DRAFT_LABEL = "Wyczyść wybór"
CHECK_STRUCTURE_LABEL = "Sprawdź strukturę (dry-run)"
REFRESH_INVENTORY_LABEL = "Odśwież inventory"
APPLY_RAM_DRAFT_LABEL = "Uaktualnij RAM draft"

_DRAFT_STATUS_OPTIONS = (
    "ok",
    "needs_review",
    "missing_content",
    "draft_edited",
    "hidden_draft",
)


@dataclass
class ElementDraftPatch:
    title: str | None = None
    text: str | None = None
    alt: str | None = None
    notes: str | None = None
    status: str | None = None
    visible: bool | None = None
    order: int | None = None


@dataclass
class MergedPageElement:
    element_id: str
    section_key: str
    element_type: str
    group: str
    order: int
    label: str
    title: str
    text: str
    image_ref: str
    alt: str
    notes: str
    editable: bool
    source: str
    status: str
    has_draft_patch: bool
    visible: bool


@dataclass
class GicleeFramePageDraft:
    patches: dict[str, ElementDraftPatch] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.patches

    def clear(self) -> None:
        self.patches.clear()

    def clear_element(self, element_id: str) -> None:
        self.patches.pop(element_id, None)

    def set_patch(self, element_id: str, **fields: object) -> None:
        patch = self.patches.setdefault(element_id, ElementDraftPatch())
        for key, value in fields.items():
            if not hasattr(patch, key):
                continue
            setattr(patch, key, value)

    def draft_edit_count(self) -> int:
        return len(self.patches)

    def format_summary(self) -> str:
        n = self.draft_edit_count()
        if n == 0:
            return DRAFT_RAM_DISCLAIMER + "\nBrak edycji RAM."
        return DRAFT_RAM_DISCLAIMER + f"\nEdycje RAM: {n} element(ów)."


def draft_status_menu_options() -> list[tuple[str, str]]:
    return [(s, s) for s in _DRAFT_STATUS_OPTIONS]


def merge_inventory_with_draft(
    report: PageInventoryReport,
    draft: GicleeFramePageDraft,
) -> list[MergedPageElement]:
    merged: list[MergedPageElement] = []
    for el in report.elements:
        patch = draft.patches.get(el.element_id)
        has_patch = patch is not None
        title = el.title
        text = el.text
        alt = el.alt
        notes = el.notes
        status = el.status
        order = el.order
        visible = True
        source = el.source

        if patch is not None:
            if patch.title is not None:
                title = patch.title
            if patch.text is not None:
                text = patch.text
            if patch.alt is not None:
                alt = patch.alt
            if patch.notes is not None:
                notes = patch.notes
            if patch.status is not None:
                status = patch.status
            if patch.order is not None:
                order = patch.order
            if patch.visible is not None:
                visible = patch.visible
            source = "ram_draft"
            if status == "ok" and has_patch:
                status = "draft_edited"

        merged.append(
            MergedPageElement(
                element_id=el.element_id,
                section_key=el.section_key,
                element_type=el.element_type,
                group=el.group,
                order=order,
                label=el.label,
                title=title,
                text=text,
                image_ref=el.image_ref,
                alt=alt,
                notes=notes,
                editable=el.editable,
                source=source,
                status=status,
                has_draft_patch=has_patch,
                visible=visible,
            )
        )

    merged.sort(key=lambda m: (m.order, m.element_id))
    return merged


def merged_from_element(el: PageElement) -> MergedPageElement:
    return MergedPageElement(
        element_id=el.element_id,
        section_key=el.section_key,
        element_type=el.element_type,
        group=el.group,
        order=el.order,
        label=el.label,
        title=el.title,
        text=el.text,
        image_ref=el.image_ref,
        alt=el.alt,
        notes=el.notes,
        editable=el.editable,
        source=el.source,
        status=el.status,
        has_draft_patch=False,
        visible=True,
    )


def apply_patch_to_merged(
    merged: MergedPageElement,
    patch: ElementDraftPatch,
) -> MergedPageElement:
    return replace(
        merged,
        title=patch.title if patch.title is not None else merged.title,
        text=patch.text if patch.text is not None else merged.text,
        alt=patch.alt if patch.alt is not None else merged.alt,
        notes=patch.notes if patch.notes is not None else merged.notes,
        status=patch.status if patch.status is not None else merged.status,
        order=patch.order if patch.order is not None else merged.order,
        visible=patch.visible if patch.visible is not None else merged.visible,
        source="ram_draft",
        has_draft_patch=True,
    )
