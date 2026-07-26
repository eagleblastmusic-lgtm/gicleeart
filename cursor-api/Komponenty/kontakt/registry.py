"""Mapowanie stref → templates/page.contact.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero",
        label="Hero — Kontakt",
        description="Nagłówek i tło sekcji hero.",
        section_key="hero_VWALbr",
        fields=(
            TemplateField("hero_heading", "Nagłówek", "heading", _s("hero_VWALbr", "blocks", "text_XJxnAG", "settings", "text")),
            TemplateField("hero_image", "Tło — grafika", "shopify_image", _s("hero_VWALbr", "settings", "image_1")),
        ),
    ),
    TemplateZone(
        zone_id="under_hero_bg",
        label="Tło pod hero",
        description=(
            "Tło sekcji formularza (pod hero): wybierz grafikę/film albo gotowy gradient (v1/v2)."
        ),
        section_key="form",
        # Ta sama sekcja co formularz — nie przełączamy widoczności osobno.
        settings_only=True,
        image_effect_selector=(
            ".custom-section-background .background-image-container, "
            ".custom-section-background video-background-component"
        ),
        fields=(
            TemplateField(
                "under_hero_bg_mode",
                "Typ tła",
                "choice",
                _s("form", "settings", "giclee_contact_bg_mode"),
                hint="Grafika — wgraj plik. Gradient — gotowa kompozycja v1 lub v2.",
                choices=(
                    ("image", "Grafika"),
                    ("gradient", "Gradient"),
                ),
            ),
            TemplateField(
                "under_hero_gradient",
                "Wersja gradientu",
                "choice",
                _s("form", "settings", "giclee_contact_bg_gradient"),
                hint="Widoczne przy typie «Gradient».",
                choices=(
                    ("v1", "Wersja 1 — ciepły radial + ciemny linear"),
                    ("v2", "Wersja 2 — radial + winieta + linear"),
                ),
            ),
            TemplateField(
                "under_hero_background",
                "Tło sekcji",
                "section_background",
                _s("form", "settings", "background_image"),
                hint="Widoczne przy typie «Grafika». Grafika lub film (Shopify Files).",
            ),
            TemplateField(
                "under_hero_blur",
                "Rozmycie tła",
                "int",
                _s("form", "settings", "giclee_contact_bg_blur_px"),
                hint="Rozmycie grafiki tła sekcji (px).",
                min_value=0,
                max_value=20,
                step=1,
                unit="px",
            ),
            TemplateField(
                "under_hero_saturate",
                "Saturacja tła",
                "int",
                _s("form", "settings", "giclee_contact_bg_saturate_pct"),
                hint="100% = pełne kolory, niżej = bardziej szare.",
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
            ),
            TemplateField(
                "under_hero_brightness",
                "Jasność tła",
                "int",
                _s("form", "settings", "giclee_contact_bg_brightness_pct"),
                hint="100% = bez ściemnienia filtrem, niżej = ciemniejsza grafika.",
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
            ),
            TemplateField(
                "under_hero_dim_overlay",
                "Nakładka przyciemniająca",
                "int",
                _s("form", "settings", "giclee_contact_bg_dim_overlay_pct"),
                hint="Dodatkowa czarna warstwa nad grafiką (niezależna od «Przyciemnienie» w oknie Tło…).",
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
            ),
            TemplateField(
                "under_hero_scale",
                "Powiększenie kadru",
                "int",
                _s("form", "settings", "giclee_contact_bg_scale_pct"),
                hint="Lekki zoom grafiki (unika prześwitów przy rozmycin).",
                min_value=0,
                max_value=12,
                step=1,
                unit="%",
            ),
        ),
    ),
    TemplateZone(
        zone_id="form",
        label="Formularz kontaktowy",
        description="Przycisk wysyłki formularza.",
        section_key="form",
        fields=(
            TemplateField(
                "submit_label",
                "Etykieta przycisku",
                "text",
                _s("form", "blocks", "contact_form_UwiCkQ", "blocks", "submit-button", "settings", "label"),
            ),
        ),
    ),
)
