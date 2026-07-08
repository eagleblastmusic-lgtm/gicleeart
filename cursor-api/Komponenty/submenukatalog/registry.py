"""Mapowanie stref → assets/giclee-catalog-submenu-config.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="list",
        label="Lista artystów",
        description="Układ kolumn i ukryci autorzy w panelu Katalog oraz menu mobilnym.",
        section_key="list",
        settings_only=True,
        fields=(
            TemplateField("columns", "Liczba kolumn", "int", ("list", "columns")),
            TemplateField(
                "show_header",
                "Nagłówek «Artyści»",
                "bool",
                ("list", "show_header"),
            ),
            TemplateField(
                "hidden_artists_text",
                "Ukryci artyści (handle kolekcji)",
                "body",
                ("list", "hidden_artists_text"),
                hint="Jeden handle Shopify na linię (np. claude-monet). Kolekcja nadal działa pod bezpośrednim URL.",
            ),
        ),
    ),
    TemplateZone(
        zone_id="animation",
        label="Animacja wejścia",
        description="Kaskadowe pojawianie się linków po otwarciu panelu.",
        section_key="animation",
        settings_only=True,
        fields=(
            TemplateField(
                "open_reveal_delay_ms",
                "Opóźnienie startu (ms)",
                "int",
                ("animation", "open_reveal_delay_ms"),
            ),
            TemplateField(
                "max_cascade_ms",
                "Maks. czas kaskady (ms)",
                "int",
                ("animation", "max_cascade_ms"),
            ),
            TemplateField(
                "min_interval_ms",
                "Min. odstęp między linkami (ms)",
                "int",
                ("animation", "min_interval_ms"),
            ),
            TemplateField(
                "max_interval_ms",
                "Maks. odstęp między linkami (ms)",
                "int",
                ("animation", "max_interval_ms"),
            ),
            TemplateField(
                "interval_curve",
                "Krzywa zwolnienia (1 = liniowo)",
                "float",
                ("animation", "interval_curve"),
            ),
            TemplateField(
                "link_transition_ms",
                "Czas animacji linku (ms)",
                "int",
                ("animation", "link_transition_ms"),
            ),
        ),
    ),
    TemplateZone(
        zone_id="appearance",
        label="Wygląd panelu",
        description="Rozmiary panelu podglądu w rozwijanym menu Katalog.",
        section_key="appearance",
        settings_only=True,
        fields=(
            TemplateField(
                "preview_width_px",
                "Szerokość podglądu (px)",
                "int",
                ("appearance", "preview_width_px"),
            ),
            TemplateField(
                "panel_max_height_vh",
                "Maks. wysokość panelu (vh)",
                "int",
                ("appearance", "panel_max_height_vh"),
            ),
        ),
    ),
)
