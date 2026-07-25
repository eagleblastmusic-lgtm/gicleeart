"""Mapowanie stref → templates/page.faq.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

_ACCORDION = ("sections", "section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks")

_FAQ_ROWS: tuple[tuple[str, str], ...] = (
    ("accordion_row_mUQFCU", "text_Q8RMTC"),
    ("accordion_row_gq7xgd", "text_dbKFYM"),
    ("accordion_row_fxrNFP", "text_KT9gtp"),
    ("accordion_row_VwgmXW", "text_kCYhHF"),
    ("accordion_row_7nCpLH", "text_BnRprG"),
)


def _faq_row_fields(index: int, row_key: str, text_key: str) -> tuple[TemplateField, ...]:
    n = index + 1
    row_settings = (*_ACCORDION, row_key, "settings")
    return (
        TemplateField(
            f"q{n}_heading",
            f"Pytanie {n}",
            "text",
            (*row_settings, "heading"),
        ),
        TemplateField(
            f"q{n}_image",
            f"Pytanie {n} — tło",
            "shopify_image",
            (*row_settings, "heading_background_image"),
            hint="Opcjonalnie. Puste pole odpowiedzi = ta sama grafika ciągnie się na cały wiersz.",
        ),
        TemplateField(
            f"q{n}_answer",
            f"Odpowiedź {n}",
            "body",
            (*_ACCORDION, row_key, "blocks", text_key, "settings", "text"),
        ),
        TemplateField(
            f"q{n}_answer_image",
            f"Odpowiedź {n} — tło",
            "shopify_image",
            (*row_settings, "answer_background_image"),
            hint="Opcjonalnie osobny obraz. Zostaw puste, żeby kontynuować tło pytania.",
        ),
    )


PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero",
        label="Hero FAQ",
        description="Nagłówek i tło strony FAQ.",
        section_key="hero_NaxrxE",
        fields=(
            TemplateField("hero_title", "Nagłówek", "heading", _s("hero_NaxrxE", "blocks", "text_HJGb9e", "settings", "text")),
            TemplateField("hero_image", "Tło — grafika", "shopify_image", _s("hero_NaxrxE", "settings", "image_1")),
        ),
        image_effect_selector=(
            ".hero__media-wrapper--desktop, "
            "[data-testid=\"hero-picture-1\"]"
        ),
    ),
    TemplateZone(
        zone_id="under_hero_bg",
        label="Tło pod hero",
        description=(
            "Tło sekcji z pytaniami (pod hero): wybierz grafikę/film albo gotowy gradient (v1/v2)."
        ),
        section_key="section_9YgpHf",
        # Ta sama sekcja co accordion — nie przełączamy widoczności osobno.
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
                _s("section_9YgpHf", "settings", "giclee_faq_bg_mode"),
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
                _s("section_9YgpHf", "settings", "giclee_faq_bg_gradient"),
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
                _s("section_9YgpHf", "settings", "background_image"),
                hint="Widoczne przy typie «Grafika». Grafika lub film (Shopify Files).",
            ),
            TemplateField(
                "under_hero_blur",
                "Rozmycie tła",
                "int",
                _s("section_9YgpHf", "settings", "giclee_faq_bg_blur_px"),
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
                _s("section_9YgpHf", "settings", "giclee_faq_bg_saturate_pct"),
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
                _s("section_9YgpHf", "settings", "giclee_faq_bg_brightness_pct"),
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
                _s("section_9YgpHf", "settings", "giclee_faq_bg_dim_overlay_pct"),
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
                _s("section_9YgpHf", "settings", "giclee_faq_bg_scale_pct"),
                hint="Lekki zoom grafiki (unika prześwitów przy rozmycin).",
                min_value=0,
                max_value=12,
                step=1,
                unit="%",
            ),
        ),
    ),
    TemplateZone(
        zone_id="faq_accordion",
        label="Pytania i odpowiedzi",
        description="Accordion z najczęstszymi pytaniami — opcjonalne tła obrazów z gradientem.",
        section_key="section_9YgpHf",
        fields=(
            TemplateField(
                "accordion_style",
                "Styl kart",
                "choice",
                _s("section_9YgpHf", "settings", "giclee_faq_accordion_style"),
                hint=(
                    "Styl 1 — szkło/złoto. Styl 2 — uproszczony hover Galaxy. "
                    "Styl 3 — Galaxy shell + świecąca krawędź (bez orbów)."
                ),
                choices=(
                    ("style1", "Styl 1 — szkło i złoto"),
                    ("style2", "Styl 2 — świecący hover (Galaxy)"),
                    ("style3", "Styl 3 — Galaxy shell + krawędź («Losuj obraz»)"),
                ),
            ),
            *(
                field
                for index, (row_key, text_key) in enumerate(_FAQ_ROWS)
                for field in _faq_row_fields(index, row_key, text_key)
            ),
        ),
    ),
)
