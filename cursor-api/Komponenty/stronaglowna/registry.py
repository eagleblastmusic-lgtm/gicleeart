"""Mapowanie stref strony głównej → ścieżki w templates/index.json i ustawieniach motywu."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

FieldKind = Literal[
    "shopify_image",
    "shopify_video",
    "theme_asset",
    "section_background",
    "media_type",
    "video_collage",
    "heading",
    "body",
    "text",
    "link",
    "bool",
    "int",
    "blocks_visible",
]

PathKey = tuple[str, ...]

SITE_NOTICE_ZONE_ID = "site_notice"


@dataclass(frozen=True)
class HomeField:
    field_id: str
    label: str
    kind: FieldKind
    path: PathKey | None = None
    theme_asset: str | None = None
    hint: str = ""
    block_paths: tuple[PathKey, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HomeZone:
    zone_id: str
    label: str
    description: str
    section_key: str
    fields: tuple[HomeField, ...] = field(default_factory=tuple)
    settings_only: bool = False


def _s(section: str, *parts: str) -> PathKey:
    return ("sections", section, *parts)


def _section_bg(section_key: str, field_id: str) -> HomeField:
    return HomeField(
        field_id,
        "Tło sekcji",
        "section_background",
        _s(section_key, "settings", "background_image"),
        hint="Grafika lub film w tle całej sekcji (Shopify Files).",
    )


HOME_ZONES: tuple[HomeZone, ...] = (
    HomeZone(
        zone_id="hero",
        label="Hero — slideshow",
        description="Pełnoekranowa karuzela na górze strony. Na mobile pierwszy slajd zastępuje grafika z motywu (assets/MALE_ORG.webp).",
        section_key="slideshow_4LMfx7",
        fields=(
            HomeField(
                "hero_media_type",
                "Typ slajdu desktop",
                "media_type",
                _s("slideshow_4LMfx7", "blocks", "slide_NPidVp", "settings", "media_type_1"),
                hint="Grafika, pojedynczy film lub kolaż wielu filmów z przejściami.",
            ),
            HomeField(
                "hero_desktop",
                "Slajd desktop — grafika (Shopify Files)",
                "shopify_image",
                _s("slideshow_4LMfx7", "blocks", "slide_NPidVp", "settings", "image_1"),
            ),
            HomeField(
                "hero_desktop_video",
                "Slajd desktop — film (Shopify Files)",
                "shopify_video",
                _s("slideshow_4LMfx7", "blocks", "slide_NPidVp", "settings", "video_1"),
                hint="MP4, WebM lub MOV. Odtwarzany bez dźwięku (jak w motywie).",
            ),
            HomeField(
                "hero_video_boomerang",
                "Film — odtwarzanie do przodu i w tył",
                "bool",
                _s("slideshow_4LMfx7", "blocks", "slide_NPidVp", "settings", "video_boomerang"),
                hint="Przy zapisie GicleeApp generuje jeden plik MP4 (do przodu + w tył) — odtwarzany w zwykłej pętli, bez mignięcia.",
            ),
            HomeField(
                "hero_desktop_video_reversed",
                "Film — pętla tam i z powrotem (auto)",
                "shopify_video",
                _s("slideshow_4LMfx7", "blocks", "slide_NPidVp", "settings", "video_1_reversed"),
            ),
            HomeField(
                "hero_video_collage",
                "Kolaż wideo",
                "video_collage",
                _s("slideshow_4LMfx7", "blocks", "slide_NPidVp", "settings", "video_collage_json"),
                hint="Wiele klipów MP4/WebM/MOV z przejściami (fade, crossfade, dip, push).",
            ),
            HomeField(
                "hero_mobile",
                "Slajd mobile (plik motywu)",
                "theme_asset",
                theme_asset="assets/MALE_ORG.webp",
                hint="Kopiowany do repozytorium motywu; używany przez JS na urządzeniach mobilnych.",
            ),
            HomeField(
                "hero_autoplay",
                "Autoodtwarzanie",
                "bool",
                _s("slideshow_4LMfx7", "settings", "autoplay"),
            ),
            HomeField(
                "hero_autoplay_speed",
                "Czas slajdu (s)",
                "int",
                _s("slideshow_4LMfx7", "settings", "autoplay_speed"),
            ),
        ),
    ),
    HomeZone(
        zone_id="giclee_art",
        label="Giclée Art — intro",
        description="Portret + opis pracowni pod hero (sekcja z animacją wejścia).",
        section_key="section_ThWw4Q",
        fields=(
            HomeField(
                "ga_portrait",
                "Portret / grafika",
                "shopify_image",
                _s(
                    "section_ThWw4Q",
                    "blocks",
                    "group_CkHdkn",
                    "blocks",
                    "group_6WWAKH",
                    "blocks",
                    "image_dVqVFn",
                    "settings",
                    "image",
                ),
            ),
            HomeField(
                "ga_heading",
                "Nagłówek",
                "heading",
                _s(
                    "section_ThWw4Q",
                    "blocks",
                    "group_CkHdkn",
                    "blocks",
                    "group_6WWAKH",
                    "blocks",
                    "text_EgnMm8",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "ga_body",
                "Treść",
                "body",
                _s(
                    "section_ThWw4Q",
                    "blocks",
                    "group_CkHdkn",
                    "blocks",
                    "group_6WWAKH",
                    "blocks",
                    "text_EgnMm8",
                    "settings",
                    "text",
                ),
            ),
            _section_bg("section_ThWw4Q", "ga_background"),
        ),
    ),
    HomeZone(
        zone_id="restoration",
        label="Odrestaurowywanie dzieł",
        description="Tekst + suwak przed/po restauracji.",
        section_key="section_XwRNDp",
        fields=(
            HomeField(
                "rest_heading",
                "Nagłówek",
                "heading",
                _s(
                    "section_XwRNDp",
                    "blocks",
                    "group_QpXMAh",
                    "blocks",
                    "group_c7gh6z",
                    "blocks",
                    "text_ywirTH",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "rest_body",
                "Treść",
                "body",
                _s(
                    "section_XwRNDp",
                    "blocks",
                    "group_QpXMAh",
                    "blocks",
                    "group_c7gh6z",
                    "blocks",
                    "text_EpbDYf",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "rest_before",
                "Przed — obraz",
                "shopify_image",
                _s("section_XwRNDp", "blocks", "comparison_slider_diQHbT", "settings", "before_image"),
            ),
            HomeField(
                "rest_after",
                "Po — obraz",
                "shopify_image",
                _s("section_XwRNDp", "blocks", "comparison_slider_diQHbT", "settings", "after_image"),
            ),
            _section_bg("section_XwRNDp", "rest_background"),
        ),
    ),
    HomeZone(
        zone_id="color_correction",
        label="Autorska korekcja kolorystyczna",
        description="Suwak PRZED/PO + opis + przyciski CTA do kolekcji.",
        section_key="section_bj9cY3",
        fields=(
            HomeField(
                "cc_before",
                "Przed — obraz",
                "shopify_image",
                _s("section_bj9cY3", "blocks", "comparison_slider_bQWJGa", "settings", "before_image"),
            ),
            HomeField(
                "cc_after",
                "Po — obraz",
                "shopify_image",
                _s("section_bj9cY3", "blocks", "comparison_slider_bQWJGa", "settings", "after_image"),
            ),
            HomeField(
                "cc_before_label",
                "Etykieta «przed»",
                "text",
                _s("section_bj9cY3", "blocks", "comparison_slider_bQWJGa", "settings", "before_text"),
            ),
            HomeField(
                "cc_after_label",
                "Etykieta «po»",
                "text",
                _s("section_bj9cY3", "blocks", "comparison_slider_bQWJGa", "settings", "after_text"),
            ),
            HomeField(
                "cc_heading",
                "Nagłówek",
                "heading",
                _s(
                    "section_bj9cY3",
                    "blocks",
                    "group_FCVUiD",
                    "blocks",
                    "group_AjTVRg",
                    "blocks",
                    "text_EVaB7H",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "cc_body",
                "Treść",
                "body",
                _s(
                    "section_bj9cY3",
                    "blocks",
                    "group_FCVUiD",
                    "blocks",
                    "group_AjTVRg",
                    "blocks",
                    "text_9XdqrW",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "cc_cta_visible",
                "Pokaż przyciski CTA",
                "blocks_visible",
                hint="«Wyświetl wszystko» i «Kup teraz» pod opisem sekcji.",
                block_paths=(
                    _s(
                        "section_bj9cY3",
                        "blocks",
                        "group_FCVUiD",
                        "blocks",
                        "group_PKPWxV",
                        "blocks",
                        "button_UgW9Kt",
                    ),
                    _s(
                        "section_bj9cY3",
                        "blocks",
                        "group_FCVUiD",
                        "blocks",
                        "group_PKPWxV",
                        "blocks",
                        "button_7G6q7x",
                    ),
                ),
            ),
            HomeField(
                "cc_btn1_label",
                "Przycisk 1 — etykieta",
                "text",
                _s(
                    "section_bj9cY3",
                    "blocks",
                    "group_FCVUiD",
                    "blocks",
                    "group_PKPWxV",
                    "blocks",
                    "button_UgW9Kt",
                    "settings",
                    "label",
                ),
            ),
            HomeField(
                "cc_btn1_link",
                "Przycisk 1 — link",
                "link",
                _s(
                    "section_bj9cY3",
                    "blocks",
                    "group_FCVUiD",
                    "blocks",
                    "group_PKPWxV",
                    "blocks",
                    "button_UgW9Kt",
                    "settings",
                    "link",
                ),
            ),
            HomeField(
                "cc_btn2_label",
                "Przycisk 2 — etykieta",
                "text",
                _s(
                    "section_bj9cY3",
                    "blocks",
                    "group_FCVUiD",
                    "blocks",
                    "group_PKPWxV",
                    "blocks",
                    "button_7G6q7x",
                    "settings",
                    "label",
                ),
            ),
            HomeField(
                "cc_btn2_link",
                "Przycisk 2 — link",
                "link",
                _s(
                    "section_bj9cY3",
                    "blocks",
                    "group_FCVUiD",
                    "blocks",
                    "group_PKPWxV",
                    "blocks",
                    "button_7G6q7x",
                    "settings",
                    "link",
                ),
            ),
            _section_bg("section_bj9cY3", "cc_background"),
        ),
    ),
    HomeZone(
        zone_id="potential",
        label="Potencjał ukryty w zdjęciu",
        description="Opis + suwak przed/po korekty tonalnej.",
        section_key="section_p9Kcm6",
        fields=(
            HomeField(
                "pot_heading",
                "Nagłówek",
                "heading",
                _s(
                    "section_p9Kcm6",
                    "blocks",
                    "group_TJVmwT",
                    "blocks",
                    "group_MNQiQA",
                    "blocks",
                    "text_qLVbAJ",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "pot_body",
                "Treść",
                "body",
                _s(
                    "section_p9Kcm6",
                    "blocks",
                    "group_TJVmwT",
                    "blocks",
                    "group_MNQiQA",
                    "blocks",
                    "text_FhBhaC",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "pot_before",
                "Przed — obraz",
                "shopify_image",
                _s("section_p9Kcm6", "blocks", "comparison_slider_LBjinq", "settings", "before_image"),
            ),
            HomeField(
                "pot_after",
                "Po — obraz",
                "shopify_image",
                _s("section_p9Kcm6", "blocks", "comparison_slider_LBjinq", "settings", "after_image"),
            ),
            HomeField(
                "pot_before_label",
                "Etykieta «przed»",
                "text",
                _s("section_p9Kcm6", "blocks", "comparison_slider_LBjinq", "settings", "before_text"),
            ),
            HomeField(
                "pot_after_label",
                "Etykieta «po»",
                "text",
                _s("section_p9Kcm6", "blocks", "comparison_slider_LBjinq", "settings", "after_text"),
            ),
            _section_bg("section_p9Kcm6", "pot_background"),
        ),
    ),
    HomeZone(
        zone_id="see_difference",
        label="Zobacz różnicę",
        description="Dwa suwaki przed/po (Restoration Edition) z tekstem pośrodku.",
        section_key="section_P9LgB3",
        fields=(
            HomeField(
                "sd_heading",
                "Nagłówek",
                "heading",
                _s(
                    "section_P9LgB3",
                    "blocks",
                    "group_QHbMGt",
                    "blocks",
                    "group_rMqMRt",
                    "blocks",
                    "text_rmKL7r",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "sd_body",
                "Treść",
                "body",
                _s(
                    "section_P9LgB3",
                    "blocks",
                    "group_QHbMGt",
                    "blocks",
                    "group_rMqMRt",
                    "blocks",
                    "text_zLzkLW",
                    "settings",
                    "text",
                ),
            ),
            HomeField(
                "sd_s1_before",
                "Suwak 1 — przed",
                "shopify_image",
                _s("section_P9LgB3", "blocks", "comparison_slider_kNChAj", "settings", "before_image"),
            ),
            HomeField(
                "sd_s1_after",
                "Suwak 1 — po",
                "shopify_image",
                _s("section_P9LgB3", "blocks", "comparison_slider_kNChAj", "settings", "after_image"),
            ),
            HomeField(
                "sd_s2_before",
                "Suwak 2 — przed",
                "shopify_image",
                _s("section_P9LgB3", "blocks", "comparison_slider_8yNUpn", "settings", "before_image"),
            ),
            HomeField(
                "sd_s2_after",
                "Suwak 2 — po",
                "shopify_image",
                _s("section_P9LgB3", "blocks", "comparison_slider_8yNUpn", "settings", "after_image"),
            ),
            _section_bg("section_P9LgB3", "sd_background"),
        ),
    ),
    HomeZone(
        zone_id=SITE_NOTICE_ZONE_ID,
        label="Powiadomienie modalne",
        description=(
            "Okno informacyjne po wejściu na stronę główną (tytuł, treść, przycisk «Rozumiem»). "
            "Zwiększ wersję, aby ponownie pokazać użytkownikom, którzy już zamknęli modal."
        ),
        section_key="",
        settings_only=True,
        fields=(
            HomeField("sn_enabled", "Pokaż modal na stronie głównej", "bool"),
            HomeField("sn_version", "Wersja (localStorage)", "text", hint="Zmień np. z 1 na 2 — modal wróci dla wszystkich."),
            HomeField("sn_title", "Tytuł", "text"),
            HomeField("sn_message", "Treść", "text"),
            HomeField("sn_button", "Przycisk", "text"),
        ),
    ),
)


def zone_by_id(zone_id: str) -> HomeZone | None:
    for zone in HOME_ZONES:
        if zone.zone_id == zone_id:
            return zone
    return None


def zone_enabled(template: dict[str, Any], zone: HomeZone) -> bool:
    if zone.settings_only:
        return True
    section = (template.get("sections") or {}).get(zone.section_key)
    if not isinstance(section, dict):
        return False
    return not bool(section.get("disabled"))


def set_zone_enabled(template: dict[str, Any], zone: HomeZone, enabled: bool) -> None:
    if zone.settings_only:
        return
    section = (template.get("sections") or {}).get(zone.section_key)
    if not isinstance(section, dict):
        return
    if enabled:
        section.pop("disabled", None)
    else:
        section["disabled"] = True


ZONE_HOME_HOOK: dict[str, str] = {
    "hero": "hero",
    "giclee_art": "intro",
    "restoration": "restoration",
    "color_correction": "color-correction",
    "potential": "potential",
    "see_difference": "see-difference",
}

SECTION_NAME_HINTS: dict[str, list[str]] = {
    "hero": ["slideshow", "hero", "karuzela"],
    "giclee_art": ["giclée art", "giclee art", "intro"],
    "restoration": ["odrestaurowywanie", "restoration"],
    "color_correction": ["korekcja", "color correction", "autorska korekcja"],
    "potential": ["potencjał", "potential"],
    "see_difference": ["zobacz różnicę", "see difference", "restoration edition"],
}
