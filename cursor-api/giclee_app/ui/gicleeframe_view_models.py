"""Pure view contracts for GICLÉE FRAME — no UI dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from giclee_app.studio.gicleeframe_page_draft import MergedPageElement
from giclee_app.studio.gicleeframe_page_settings import PageSettingField

__all__ = [
    "PageContextRowSpec",
    "SectionVisualCacheEntry",
    "_ellipsize",
    "_section_kind_copy",
]


@dataclass(frozen=True)
class PageContextRowSpec:
    kind: str
    label: str = ""
    value: str = ""
    group_title: str = ""
    slot: int = 0
    field: PageSettingField | None = None
    key: str = ""
    setting_id: str = ""
    group_id: str = ""
    group_settings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SectionVisualCacheEntry:
    """Sesyjny cache wizualny — nie mutuje RAM draft."""

    element_type: str
    status: str
    has_draft_patch: bool
    title: str
    text: str
    alt: str
    image_ref: str
    notes: str
    visible: bool
    subtitle_text: str
    page_context_summary: tuple[tuple[str, str], ...]
    fields_title: bool
    fields_text: bool
    fields_alt: bool
    fields_image_ref: bool
    fields_notes: bool
    fields_visible: bool
    fields_children: bool
    fields_page_context: bool
    media_details_built: bool
    preview_key: str
    layer_nav_visible: bool
    layer_nav_titles: tuple[str, ...]
    details_cache_preview: bool = False
    details_cache_page_context: bool = False
    details_cache_layer_nav: bool = False
    details_cache_children: bool = False


def _ellipsize(text: str, max_chars: int = 42) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "…"


def _section_kind_copy(element_id: str, merged_items: list[MergedPageElement]) -> str:
    merged = next((x for x in merged_items if x.element_id == element_id), None)
    if merged is None:
        return ""
    if merged.element_type == "divider":
        return "separator"
    if merged.element_type == "section_legacy":
        return "legacy"
    if merged.element_type == "media_section":
        return "sekcja edytorska"
    return "sekcja"
