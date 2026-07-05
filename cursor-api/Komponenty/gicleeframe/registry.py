"""Mapowanie stref → templates/page.giclee-frame.json (kolejność jak na stronie)."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s


def _divider_zone(
    section_key: str,
    label: str,
    *,
    description: str = "Separator — widoczność i grubość linii.",
) -> TemplateZone:
    return TemplateZone(
        zone_id=section_key,
        label=label,
        description=description,
        section_key=section_key,
        fields=(
            TemplateField(
                "thickness",
                "Grubość linii",
                "float",
                _s(section_key, "settings", "thickness"),
                hint="Np. 0.5 lub 1",
            ),
            TemplateField(
                "width_percent",
                "Szerokość (%)",
                "int",
                _s(section_key, "settings", "width_percent"),
            ),
            TemplateField(
                "pad_top",
                "Odstęp góra",
                "int",
                _s(section_key, "settings", "padding-block-start"),
            ),
            TemplateField(
                "pad_bottom",
                "Odstęp dół",
                "int",
                _s(section_key, "settings", "padding-block-end"),
            ),
        ),
    )


def _media_zone(
    section_key: str,
    label: str,
    *,
    jumbo_block: str,
    text_block: str,
    field_prefix: str,
    description: str = "",
) -> TemplateZone:
    return TemplateZone(
        zone_id=section_key,
        label=label,
        description=description or f"Sekcja editorial: grafika + nagłówek jumbo + treść.",
        section_key=section_key,
        fields=(
            TemplateField(
                f"{field_prefix}_jumbo",
                "Nagłówek jumbo",
                "text",
                _s(section_key, "blocks", "content", "blocks", jumbo_block, "settings", "text"),
            ),
            TemplateField(
                f"{field_prefix}_body",
                "Treść",
                "body",
                _s(section_key, "blocks", "content", "blocks", text_block, "settings", "text"),
            ),
            TemplateField(
                f"{field_prefix}_image",
                "Grafika",
                "shopify_image",
                _s(section_key, "blocks", "media", "settings", "image"),
            ),
            TemplateField(
                f"{field_prefix}_media_pos",
                "Pozycja grafiki",
                "text",
                _s(section_key, "settings", "media_position"),
                hint="left lub right",
            ),
            TemplateField(
                f"{field_prefix}_media_height",
                "Wysokość grafiki",
                "text",
                _s(section_key, "settings", "media_height"),
                hint="Np. 60svh",
            ),
        ),
    )


PAGE_ZONES: tuple[TemplateZone, ...] = (
    _divider_zone("divider_MLHKEp", "Separator — góra strony"),
    TemplateZone(
        zone_id="main",
        label="Strona główna (legacy)",
        description="Sekcja main-page — wyłączona na live; pozostawiona w szablonie.",
        section_key="main",
        fields=(),
    ),
    _media_zone(
        "media_with_content_xdDQna",
        "Intro — Giclée Frame™",
        jumbo_block="jumbo_text_pnNRiB",
        text_block="text_GifUG3",
        field_prefix="intro",
        description="Edytorski: GICLEE FRAME — wprowadzenie produktu.",
    ),
    _divider_zone("divider_kmeBEA", "Separator — po intro"),
    _media_zone(
        "media_with_content_bJdEUY",
        "Materiały",
        jumbo_block="jumbo_text_NBbG7x",
        text_block="text_79rJDi",
        field_prefix="materialy",
        description="Edytorski: MATERIAŁY — drewno, passe-partout, komponenty archiwalne.",
    ),
    _divider_zone("divider_FRqmEM", "Separator — po materiałach"),
    _media_zone(
        "media_with_content_mEjyEw",
        "Wykończenie drewna",
        jumbo_block="jumbo_text_Xz3A7b",
        text_block="text_xktcAN",
        field_prefix="wykonczenie",
        description="Edytorski: WYKOŃCZENIE — olejowoski Rubio Monocoat.",
    ),
    _divider_zone("divider_VjTW9k", "Separator — po wykończeniu"),
    _media_zone(
        "media_with_content_TpnJQ4",
        "Archiwalne passe-partout",
        jumbo_block="jumbo_text_WTK97H",
        text_block="text_e9qjY6",
        field_prefix="passepartout",
        description="Edytorski: PASSEPARTOUT — karton archiwalny Fabriano.",
    ),
    _divider_zone("divider_zayCdU", "Separator — po passe-partout"),
    _media_zone(
        "media_with_content_wDiVPB",
        "Papier Fine Art",
        jumbo_block="jumbo_text_DEGUnA",
        text_block="text_xyy4fN",
        field_prefix="papier",
        description="Edytorski: papier fine art — Hahnemühle, Epson Velvet.",
    ),
    _divider_zone("divider_eeNXD3", "Separator — po papierze"),
    _media_zone(
        "media_with_content_8yinAT",
        "Proporcje i złoty podział",
        jumbo_block="jumbo_text_bX7tqP",
        text_block="text_KxVYV6",
        field_prefix="proporcje",
        description="Edytorski: PROPORCJE I ZŁOTY PODZIAŁ.",
    ),
    _divider_zone("divider_hhVg8j", "Separator — po proporcjach"),
    _media_zone(
        "media_with_content_tyUaLL",
        "Wymiary produktów",
        jumbo_block="jumbo_text_txPMEr",
        text_block="text_LaP347",
        field_prefix="wymiary",
        description="Edytorski: Wymiary produktów S / L / XL.",
    ),
    _divider_zone("divider_qPk6TD", "Separator — przed finałem"),
    _media_zone(
        "media_with_content_RBXALc",
        "Finalna ramka",
        jumbo_block="jumbo_text_fABkbP",
        text_block="text_d3aDXd",
        field_prefix="final",
        description="Edytorski: FINALNA RAMKA — gotowe dzieło do ekspozycji.",
    ),
    _divider_zone("divider_DUG7kA", "Separator — dół strony"),
)
