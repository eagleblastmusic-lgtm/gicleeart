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
        image_effect_selector=(
            ".hero__media-wrapper--desktop, "
            "[data-testid=\"hero-picture-1\"]"
        ),
    ),
    TemplateZone(
        zone_id="faq_archive",
        label="Pytania i odpowiedzi",
        description="Redakcyjny indeks FAQ z kartą odpowiedzi.",
        section_key="section_9YgpHf",
        fields=(
            TemplateField("q1_heading", "Pytanie 1", "text", _s("section_9YgpHf", "blocks", "faq_mUQFCU", "settings", "question")),
            TemplateField("q1_answer", "Odpowiedź 1", "body", _s("section_9YgpHf", "blocks", "faq_mUQFCU", "settings", "answer")),
            TemplateField("q2_heading", "Pytanie 2", "text", _s("section_9YgpHf", "blocks", "faq_gq7xgd", "settings", "question")),
            TemplateField("q2_answer", "Odpowiedź 2", "body", _s("section_9YgpHf", "blocks", "faq_gq7xgd", "settings", "answer")),
            TemplateField("q3_heading", "Pytanie 3", "text", _s("section_9YgpHf", "blocks", "faq_fxrNFP", "settings", "question")),
            TemplateField("q3_answer", "Odpowiedź 3", "body", _s("section_9YgpHf", "blocks", "faq_fxrNFP", "settings", "answer")),
            TemplateField("q4_heading", "Pytanie 4", "text", _s("section_9YgpHf", "blocks", "faq_VwgmXW", "settings", "question")),
            TemplateField("q4_answer", "Odpowiedź 4", "body", _s("section_9YgpHf", "blocks", "faq_VwgmXW", "settings", "answer")),
            TemplateField("q5_heading", "Pytanie 5", "text", _s("section_9YgpHf", "blocks", "faq_7nCpLH", "settings", "question")),
            TemplateField("q5_answer", "Odpowiedź 5", "body", _s("section_9YgpHf", "blocks", "faq_7nCpLH", "settings", "answer")),
        ),
    ),
)
