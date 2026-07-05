"""Mapowanie stref → templates/page.wspolpraca.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="main",
        label="Treść strony",
        description="Nagłówek strony (treść z Shopify Pages w bloku page-content).",
        section_key="main",
        fields=(
            TemplateField("heading", "Nagłówek", "heading", _s("main", "blocks", "heading", "settings", "text")),
        ),
    ),
)
