"""GICLÉE FRAME™ F2/F2.1 — RAM draft edycji elementów strony. Zero I/O."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace

from giclee_app.studio.gicleeframe_page_inventory import (
    PageElement,
    PageInventoryReport,
)
from giclee_app.studio.gicleeframe_page_settings import (
    PageSettingField,
    apply_settings_patch,
)

PAGE_EDITOR_TITLE = "Strona GICLÉE FRAME™"
SECTION_LIST_TITLE = "Sekcje strony"
SECTION_LIST_DRAG_HINT = "Przeciągnij ⋮⋮, aby zmienić kolejność (RAM draft)."
SECTION_EDITOR_TITLE = "Edytor sekcji"
DEFAULT_VARIANT_NAME = "Wariant 1"
DEFAULT_DRAFT_NAME = DEFAULT_VARIANT_NAME
WORKING_VARIANT_LABEL = "Wariant roboczy"
WORKING_VARIANT_ADD_MENU_LABEL = "+ Dodaj wariant"
ADD_VARIANT_RAM_LABEL = "Dodaj wariant RAM"
DUPLICATE_VARIANT_LABEL = "Duplikuj aktualny wariant"
RENAME_VARIANT_LABEL = "Zmień nazwę wariantu"
NEW_DRAFT_RAM_LABEL = ADD_VARIANT_RAM_LABEL
RENAME_DRAFT_LABEL = RENAME_VARIANT_LABEL
DRAFT_RAM_DISCLAIMER = (
    "Zmiany są tylko lokalnym draftem w pamięci — nic nie zapisano."
)
RAM_ONLY_STATUS = "RAM-only · nic nie zapisano"
VARIANT_COMPARE_NOTE = (
    "Porównanie wariantów odbywa się przez przełączanie wariantu roboczego "
    "i ocenę podglądu."
)
VARIANT_ENV_DEV = "dev"
VARIANT_ENV_LIVE = "live"
CLEAR_VARIANT_RAM_LABEL = "Wyczyść wariant RAM"
CLEAR_DRAFT_LABEL = CLEAR_VARIANT_RAM_LABEL
CHECK_STRUCTURE_LABEL = "Sprawdź strukturę (dry-run)"
REFRESH_INVENTORY_LABEL = "Odśwież inventory"
APPLY_RAM_DRAFT_LABEL = "Uaktualnij wariant RAM"
APPLY_RAM_MICROCOPY = "Tylko pamięć · nic nie zapisuje"
PANEL_STATUS_UNSAVED = "Nic nie zapisano"
STRUCTURE_EMPTY_STATE = "Uruchom dry-run, aby zobaczyć mapę struktury strony."
SECTION_VISIBLE_RAM = "Widoczna w RAM"
SECTION_HIDDEN_RAM = "Ukryta w RAM"
PAGE_SOURCE_FILE = "page.giclee-frame.json"
_DEFAULT_VARIANT_ID = "ram_v1"

_CHILD_LABELS_PL: dict[str, str] = {
    "jumbo": "Nagłówek",
    "body": "Tekst",
    "text_layer": "Warstwa Dodaj tekst",
    "image": "Grafika",
}

_CHILD_TYPE_ORDER = ("jumbo", "body", "text_layer", "image")

_TOP_LEVEL_TYPES = frozenset({
    "divider",
    "section_legacy",
    "media_section",
    "section",
})

_CHILD_ELEMENT_TYPES = frozenset(_CHILD_LABELS_PL.keys())

_FIELD_LABELS_PL: dict[str, str] = {
    "title": "tekst",
    "text": "tekst",
    "alt": "alt",
    "notes": "notatka",
    "status": "status",
    "visible": "visible",
    "order": "order",
}


@dataclass
class ElementDraftPatch:
    title: str | None = None
    text: str | None = None
    alt: str | None = None
    notes: str | None = None
    status: str | None = None
    visible: bool | None = None
    order: int | None = None
    settings: dict[str, str | None] = field(default_factory=dict)


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
    page_settings: tuple[PageSettingField, ...] = ()
    page_fields: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class EditorFieldVisibility:
    page_context: bool = True
    title: bool = False
    text: bool = False
    alt: bool = False
    image_ref: bool = False
    visible: bool = False
    notes: bool = False
    children: bool = False


def editor_field_visibility(element_type: str) -> EditorFieldVisibility:
    if element_type == "divider":
        return EditorFieldVisibility(
            visible=True,
            notes=True,
        )
    if element_type == "jumbo":
        return EditorFieldVisibility(
            title=True,
            visible=True,
            notes=True,
        )
    if element_type == "body":
        return EditorFieldVisibility(
            text=True,
            visible=True,
            notes=True,
        )
    if element_type == "image":
        return EditorFieldVisibility(
            alt=True,
            image_ref=True,
            notes=True,
        )
    if element_type == "media_section":
        return EditorFieldVisibility(
            visible=True,
            notes=True,
            children=True,
        )
    if element_type == "section_legacy":
        return EditorFieldVisibility(page_context=False, notes=True)
    return EditorFieldVisibility(notes=True)


def editor_context_rows(merged: MergedPageElement) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    if merged.label:
        rows.append(("Etykieta", merged.label))
    if merged.element_type == "media_section" and merged.title:
        rows.append(("Nazwa sekcji", merged.title))
    if merged.element_type == "jumbo" and merged.title and not merged.page_fields:
        rows.append(("Nagłówek (inventory)", merged.title))
    if merged.element_type == "body" and merged.text and not merged.page_fields:
        preview = merged.text[:160] + ("…" if len(merged.text) > 160 else "")
        rows.append(("Tekst (inventory)", preview))
    if merged.element_type == "image" and merged.image_ref:
        rows.append(("Grafika (inventory)", merged.image_ref))
    return tuple(rows)


@dataclass
class PageVariantDraft:
    variant_id: str
    name: str
    env_tag: str = VARIANT_ENV_DEV
    patches: dict[str, ElementDraftPatch] = field(default_factory=dict)


def working_variant_menu_label(variant: PageVariantDraft) -> str:
    tag = variant.env_tag if variant.env_tag in (VARIANT_ENV_DEV, VARIANT_ENV_LIVE) else VARIANT_ENV_DEV
    return f"{variant.name} ({tag})"


@dataclass
class GicleeFramePageDraft:
    active_variant_id: str = _DEFAULT_VARIANT_ID
    variants: dict[str, PageVariantDraft] = field(default_factory=dict)
    _next_variant_num: int = 2

    def __post_init__(self) -> None:
        if not self.variants:
            self.variants[_DEFAULT_VARIANT_ID] = PageVariantDraft(
                variant_id=_DEFAULT_VARIANT_ID,
                name=DEFAULT_VARIANT_NAME,
            )

    @property
    def patches(self) -> dict[str, ElementDraftPatch]:
        return self.active_variant().patches

    @property
    def draft_name(self) -> str:
        return self.active_variant().name

    def active_variant(self) -> PageVariantDraft:
        variant = self.variants.get(self.active_variant_id)
        if variant is None:
            raise KeyError(self.active_variant_id)
        return variant

    def variant_names(self) -> list[tuple[str, str]]:
        return [
            (v.variant_id, v.name)
            for v in sorted(self.variants.values(), key=lambda x: x.variant_id)
        ]

    def _alloc_variant_id(self) -> str:
        vid = f"ram_v{self._next_variant_num}"
        self._next_variant_num += 1
        return vid

    def _default_variant_name(self) -> str:
        used = {v.name for v in self.variants.values()}
        n = len(self.variants) + 1
        while f"Wariant {n}" in used:
            n += 1
        return f"Wariant {n}"

    def add_variant(
        self,
        name: str | None = None,
        *,
        env_tag: str = VARIANT_ENV_DEV,
    ) -> PageVariantDraft:
        vid = self._alloc_variant_id()
        vname = (name or "").strip() or self._default_variant_name()
        tag = env_tag if env_tag in (VARIANT_ENV_DEV, VARIANT_ENV_LIVE) else VARIANT_ENV_DEV
        variant = PageVariantDraft(variant_id=vid, name=vname, env_tag=tag)
        self.variants[vid] = variant
        self.active_variant_id = vid
        return variant

    def duplicate_active_variant(self, name: str | None = None) -> PageVariantDraft:
        src = self.active_variant()
        vid = self._alloc_variant_id()
        vname = (name or "").strip() or self._default_variant_name()
        variant = PageVariantDraft(
            variant_id=vid,
            name=vname,
            env_tag=src.env_tag,
            patches=deepcopy(src.patches),
        )
        self.variants[vid] = variant
        self.active_variant_id = vid
        return variant

    def rename_active_variant(self, name: str) -> None:
        cleaned = (name or "").strip()
        if cleaned:
            self.active_variant().name = cleaned

    def switch_variant(self, variant_id: str) -> None:
        if variant_id not in self.variants:
            raise KeyError(variant_id)
        self.active_variant_id = variant_id

    def rename(self, name: str) -> None:
        self.rename_active_variant(name)

    def new_draft(self, name: str | None = None) -> None:
        self.add_variant(name)

    def is_empty(self) -> bool:
        return not self.patches

    def clear(self) -> None:
        self.active_variant().patches.clear()

    def clear_element(self, element_id: str) -> None:
        self.patches.pop(element_id, None)

    def set_patch(self, element_id: str, **fields: object) -> None:
        patch = self.patches.setdefault(element_id, ElementDraftPatch())
        settings = fields.pop("settings", None)
        if isinstance(settings, dict):
            for key, value in settings.items():
                if value is None:
                    patch.settings.pop(str(key), None)
                else:
                    patch.settings[str(key)] = str(value)
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
        return (
            DRAFT_RAM_DISCLAIMER
            + f"\nWariant roboczy: {self.draft_name} · Edycje RAM: {n} element(ów)."
        )


def status_pill_label(status: str, *, has_draft_patch: bool = False) -> str:
    if has_draft_patch or status == "draft_edited":
        return "draft"
    mapping = {
        "ok": "OK",
        "needs_review": "do sprawdzenia",
        "legacy_disabled": "legacy",
        "missing_content": "brak treści",
        "hidden_draft": "draft",
    }
    return mapping.get(status, status)


def patch_changed_fields(patch: ElementDraftPatch) -> tuple[str, ...]:
    fields: list[str] = []
    for key in ("title", "text", "alt", "notes", "status", "visible", "order"):
        if getattr(patch, key) is not None:
            fields.append(_FIELD_LABELS_PL.get(key, key))
    for setting_key in patch.settings:
        fields.append(f"ustawienie:{setting_key}")
    return tuple(fields)


def merged_in_page_order(merged: list[MergedPageElement]) -> list[MergedPageElement]:
    return sorted(merged, key=lambda m: (m.order, m.element_id))


@dataclass(frozen=True)
class SectionTreeChild:
    element_id: str
    child_label: str
    element_type: str
    merged: MergedPageElement


@dataclass(frozen=True)
class SectionTreeRow:
    element_id: str
    row_kind: str
    section_key: str
    order: int
    display_title: str
    merged: MergedPageElement
    children: tuple[SectionTreeChild, ...]


def parent_row_title(merged: MergedPageElement) -> str:
    if merged.element_type == "divider":
        return "Separator"
    return merged.label


def editor_title_for_element(merged: MergedPageElement) -> str:
    if merged.element_type == "jumbo":
        return "Edytor: Nagłówek"
    if merged.element_type == "body":
        return "Edytor: Tekst"
    if merged.element_type == "image":
        return "Edytor: Grafika"
    if merged.element_type == "divider":
        return "Edytor: Separator"
    if merged.element_type == "media_section":
        return "Edytor: Sekcja"
    if merged.element_type == "section_legacy":
        return "Edytor: Sekcja (legacy)"
    return SECTION_EDITOR_TITLE


def aggregate_row_status(
    merged: MergedPageElement,
    children: tuple[SectionTreeChild, ...],
) -> tuple[str, bool]:
    """Parent pill label and whether any draft patch exists in subtree."""
    has_draft = merged.has_draft_patch
    worst = merged.status
    priority = {
        "draft_edited": 5,
        "needs_review": 4,
        "missing_content": 3,
        "legacy_disabled": 2,
        "hidden_draft": 1,
        "ok": 0,
    }
    for child in children:
        c = child.merged
        if c.has_draft_patch:
            has_draft = True
        if priority.get(c.status, 0) > priority.get(worst, 0):
            worst = c.status
    if has_draft:
        return status_pill_label("draft_edited", has_draft_patch=True), True
    return status_pill_label(worst, has_draft_patch=False), has_draft


@dataclass(frozen=True)
class SectionDropdownOption:
    element_id: str
    display_label: str


def _parent_dropdown_label(
    row: SectionTreeRow,
    *,
    divider_index: int | None = None,
) -> str:
    if row.row_kind == "divider":
        return f"Separator {divider_index or 1}"
    return row.display_title


def section_dropdown_options(
    merged: list[MergedPageElement],
    *,
    rows: list[SectionTreeRow] | None = None,
) -> list[SectionDropdownOption]:
    """Top-level page rhythm only: separators + sections (no nested components)."""
    options: list[SectionDropdownOption] = []
    used_labels: set[str] = set()

    def unique_label(base: str, element_id: str) -> str:
        label = base
        if label in used_labels:
            label = f"{base} · {element_id[:8]}"
        used_labels.add(label)
        return label

    divider_no = 0
    tree_rows = rows if rows is not None else section_tree_rows(merged)
    for row in tree_rows:
        if row.row_kind == "divider":
            divider_no += 1
            label = unique_label(
                _parent_dropdown_label(row, divider_index=divider_no),
                row.element_id,
            )
        else:
            label = unique_label(_parent_dropdown_label(row), row.element_id)
        options.append(SectionDropdownOption(element_id=row.element_id, display_label=label))
    return options


def page_blocks(merged: list[MergedPageElement]) -> list[tuple[str, ...]]:
    """Top-level page blocks: each row + nested media children move together."""
    blocks: list[tuple[str, ...]] = []
    for row in section_tree_rows(merged):
        ids = [row.element_id, *(child.element_id for child in row.children)]
        blocks.append(tuple(ids))
    return blocks


def reorder_page_blocks(
    draft: GicleeFramePageDraft,
    merged: list[MergedPageElement],
    from_index: int,
    to_index: int,
) -> bool:
    """Reorder top-level blocks in RAM by patching element order values."""
    blocks = list(page_blocks(merged))
    if not blocks:
        return False
    if from_index < 0 or from_index >= len(blocks):
        return False
    to_index = max(0, min(to_index, len(blocks) - 1))
    if from_index == to_index:
        return False
    block = blocks.pop(from_index)
    blocks.insert(to_index, block)
    flat_ids = [element_id for block in blocks for element_id in block]
    for new_order, element_id in enumerate(flat_ids):
        draft.set_patch(element_id, order=new_order)
    return True


def section_tree_rows(merged: list[MergedPageElement]) -> list[SectionTreeRow]:
    """Hierarchical page rhythm: separators + sections; media children nested."""
    by_section: dict[str, list[MergedPageElement]] = {}
    for m in merged:
        by_section.setdefault(m.section_key, []).append(m)

    rows: list[SectionTreeRow] = []
    for m in merged_in_page_order(merged):
        if m.element_type in _CHILD_ELEMENT_TYPES:
            continue
        if m.element_type not in _TOP_LEVEL_TYPES:
            continue

        children: list[SectionTreeChild] = []
        siblings = by_section.get(m.section_key, [])
        for ctype in _CHILD_TYPE_ORDER:
            matching = [
                c for c in siblings if c.element_type == ctype
            ]
            if m.element_type != "media_section" and ctype != "text_layer":
                continue
            for child in matching:
                if child.element_id != m.element_id:
                    children.append(
                        SectionTreeChild(
                            element_id=child.element_id,
                            child_label=_CHILD_LABELS_PL.get(ctype, ctype),
                            element_type=ctype,
                            merged=child,
                        )
                    )

        rows.append(
            SectionTreeRow(
                element_id=m.element_id,
                row_kind=m.element_type,
                section_key=m.section_key,
                order=m.order,
                display_title=parent_row_title(m),
                merged=m,
                children=tuple(children),
            )
        )
    return rows


def children_for_section(
    merged: list[MergedPageElement],
    section_key: str,
) -> tuple[MergedPageElement, ...]:
    items = [
        m for m in merged_in_page_order(merged)
        if m.section_key == section_key and m.element_type in _CHILD_ELEMENT_TYPES
    ]
    return tuple(items)


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

        page_settings = el.page_settings
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
            if patch.settings:
                page_settings = apply_settings_patch(page_settings, patch.settings)
                has_patch = True
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
                page_settings=page_settings,
                page_fields=tuple((f.label, f.value) for f in page_settings),
            )
        )

    return merged_in_page_order(merged)


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
        page_settings=el.page_settings,
        page_fields=el.page_fields,
    )


def apply_patch_to_merged(
    merged: MergedPageElement,
    patch: ElementDraftPatch,
) -> MergedPageElement:
    page_settings = merged.page_settings
    if patch.settings:
        page_settings = apply_settings_patch(page_settings, patch.settings)
    return replace(
        merged,
        title=patch.title if patch.title is not None else merged.title,
        text=patch.text if patch.text is not None else merged.text,
        alt=patch.alt if patch.alt is not None else merged.alt,
        notes=patch.notes if patch.notes is not None else merged.notes,
        status=patch.status if patch.status is not None else merged.status,
        order=patch.order if patch.order is not None else merged.order,
        visible=patch.visible if patch.visible is not None else merged.visible,
        page_settings=page_settings,
        page_fields=tuple((f.label, f.value) for f in page_settings),
        source="ram_draft",
        has_draft_patch=True,
    )
