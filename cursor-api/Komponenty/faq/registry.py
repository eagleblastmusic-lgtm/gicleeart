"""Mapowanie stref → templates/page.faq.json dla Wersji 1 i Wersji 2."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Mapping

from Komponenty._shared.theme_page_editor.types import (
    FieldKind,
    PathKey,
    TemplateField,
    TemplateZone,
    _s,
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "data" / "variants" / "manifest.json"


def _active_variant_id() -> str:
    try:
        data = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "fq2"
    active = str(data.get("active") or "fq2")
    return active if active in {"fq1", "fq2"} else "fq2"


@dataclass(frozen=True)
class VariantTemplateField:
    """Pole wybierające ścieżkę na podstawie aktywnej wersji FAQ."""

    field_id: str
    label: str
    kind: FieldKind
    paths_by_variant: Mapping[str, PathKey]
    fallback_variant: str = "fq2"
    theme_asset: str | None = None
    hint: str = ""
    block_paths: tuple[PathKey, ...] = field(default_factory=tuple)

    @property
    def path(self) -> PathKey:
        active = _active_variant_id()
        return self.paths_by_variant.get(active) or self.paths_by_variant[self.fallback_variant]


def _faq_field(
    field_id: str,
    label: str,
    kind: FieldKind,
    *,
    v1: PathKey,
    v2: PathKey,
) -> VariantTemplateField:
    return VariantTemplateField(
        field_id=field_id,
        label=label,
        kind=kind,
        paths_by_variant={"fq1": v1, "fq2": v2},
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
        zone_id="faq_questions",
        label="Pytania i odpowiedzi",
        description="Pola wspólne dla klasycznej Wersji 1 i redakcyjnej Wersji 2.",
        section_key="section_9YgpHf",
        fields=(
            _faq_field(
                "q1_heading", "Pytanie 1", "text",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_mUQFCU", "settings", "heading"),
                v2=_s("section_9YgpHf", "blocks", "faq_mUQFCU", "settings", "question"),
            ),
            _faq_field(
                "q1_answer", "Odpowiedź 1", "body",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_mUQFCU", "blocks", "text_Q8RMTC", "settings", "text"),
                v2=_s("section_9YgpHf", "blocks", "faq_mUQFCU", "settings", "answer"),
            ),
            _faq_field(
                "q2_heading", "Pytanie 2", "text",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_gq7xgd", "settings", "heading"),
                v2=_s("section_9YgpHf", "blocks", "faq_gq7xgd", "settings", "question"),
            ),
            _faq_field(
                "q2_answer", "Odpowiedź 2", "body",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_gq7xgd", "blocks", "text_dbKFYM", "settings", "text"),
                v2=_s("section_9YgpHf", "blocks", "faq_gq7xgd", "settings", "answer"),
            ),
            _faq_field(
                "q3_heading", "Pytanie 3", "text",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_fxrNFP", "settings", "heading"),
                v2=_s("section_9YgpHf", "blocks", "faq_fxrNFP", "settings", "question"),
            ),
            _faq_field(
                "q3_answer", "Odpowiedź 3", "body",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_fxrNFP", "blocks", "text_KT9gtp", "settings", "text"),
                v2=_s("section_9YgpHf", "blocks", "faq_fxrNFP", "settings", "answer"),
            ),
            _faq_field(
                "q4_heading", "Pytanie 4", "text",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_VwgmXW", "settings", "heading"),
                v2=_s("section_9YgpHf", "blocks", "faq_VwgmXW", "settings", "question"),
            ),
            _faq_field(
                "q4_answer", "Odpowiedź 4", "body",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_VwgmXW", "blocks", "text_kCYhHF", "settings", "text"),
                v2=_s("section_9YgpHf", "blocks", "faq_VwgmXW", "settings", "answer"),
            ),
            _faq_field(
                "q5_heading", "Pytanie 5", "text",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_7nCpLH", "settings", "heading"),
                v2=_s("section_9YgpHf", "blocks", "faq_7nCpLH", "settings", "question"),
            ),
            _faq_field(
                "q5_answer", "Odpowiedź 5", "body",
                v1=_s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_7nCpLH", "blocks", "text_BnRprG", "settings", "text"),
                v2=_s("section_9YgpHf", "blocks", "faq_7nCpLH", "settings", "answer"),
            ),
        ),
    ),
)
