"""Mapowanie stref → templates/page.faq.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

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
    ),
    TemplateZone(
        zone_id="faq_accordion",
        label="Pytania i odpowiedzi",
        description="Accordion z najczęstszymi pytaniami.",
        section_key="section_9YgpHf",
        fields=(
            TemplateField("q1_heading", "Pytanie 1", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_mUQFCU", "settings", "heading")),
            TemplateField("q1_answer", "Odpowiedź 1", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_mUQFCU", "blocks", "text_Q8RMTC", "settings", "text")),
            TemplateField("q2_heading", "Pytanie 2", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_gq7xgd", "settings", "heading")),
            TemplateField("q2_answer", "Odpowiedź 2", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_gq7xgd", "blocks", "text_dbKFYM", "settings", "text")),
            TemplateField("q3_heading", "Pytanie 3", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_fxrNFP", "settings", "heading")),
            TemplateField("q3_answer", "Odpowiedź 3", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_fxrNFP", "blocks", "text_KT9gtp", "settings", "text")),
            TemplateField("q4_heading", "Pytanie 4", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_VwgmXW", "settings", "heading")),
            TemplateField("q4_answer", "Odpowiedź 4", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_VwgmXW", "blocks", "text_kCYhHF", "settings", "text")),
            TemplateField("q5_heading", "Pytanie 5", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_7nCpLH", "settings", "heading")),
            TemplateField("q5_answer", "Odpowiedź 5", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_7nCpLH", "blocks", "text_BnRprG", "settings", "text")),
        ),
    ),
)
