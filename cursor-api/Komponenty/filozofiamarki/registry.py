"""Mapowanie stref → templates/page.filozofia-marki.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero_manifest",
        label="Hero — manifest",
        description="Główna sekcja filozofii marki z grafiką.",
        section_key="media_with_content_D7REjd",
        fields=(
            TemplateField("hero_title", "Nagłówek", "heading", _s("media_with_content_D7REjd", "blocks", "content", "blocks", "text_UerD4k", "settings", "text")),
            TemplateField("hero_body", "Treść", "body", _s("media_with_content_D7REjd", "blocks", "content", "blocks", "text_kdAGGw", "settings", "text")),
            TemplateField(
                "hero_media_type",
                "Rodzaj grafiki",
                "choice",
                _s("media_with_content_D7REjd", "blocks", "media", "settings", "media_type"),
                choices=(
                    ("image", "Grafika"),
                    ("video", "Wideo Shopify"),
                    ("scroll_video", "Wideo sterowane przewijaniem"),
                ),
            ),
            TemplateField("hero_image", "Grafika", "shopify_image", _s("media_with_content_D7REjd", "blocks", "media", "settings", "image")),
            TemplateField(
                "hero_scroll_video_asset",
                "Plik animacji przewijanej",
                "text",
                _s("media_with_content_D7REjd", "blocks", "media", "settings", "scroll_video_asset"),
                hint="Nazwa pliku MP4 w katalogu assets motywu.",
            ),
            TemplateField(
                "hero_scroll_video_duration",
                "Długość animacji przewijanej",
                "int",
                _s("media_with_content_D7REjd", "blocks", "media", "settings", "scroll_video_duration"),
                min_value=1,
                max_value=6,
                unit="s",
            ),
            TemplateField(
                "hero_scroll_video_viewport",
                "Wysokość obszaru animacji",
                "int",
                _s("media_with_content_D7REjd", "blocks", "media", "settings", "scroll_video_viewport"),
                min_value=100,
                max_value=600,
                step=50,
                unit="vh",
            ),
            TemplateField(
                "hero_video_position",
                "Dopasowanie wideo",
                "choice",
                _s("media_with_content_D7REjd", "blocks", "media", "settings", "video_position"),
                choices=(
                    ("contain", "Pokaż całe wideo"),
                    ("cover", "Wypełnij kadr"),
                ),
            ),
        ),
    ),
    TemplateZone(
        zone_id="section_story",
        label="Sekcja — opowieść",
        description="Druga sekcja media-with-content.",
        section_key="media_with_content_LgNBmd",
        fields=(
            TemplateField("story_title", "Nagłówek", "heading", _s("media_with_content_LgNBmd", "blocks", "content", "blocks", "group_dimbtz", "blocks", "text_nMfgYW", "settings", "text")),
            TemplateField("story_body", "Treść", "body", _s("media_with_content_LgNBmd", "blocks", "content", "blocks", "group_dimbtz", "blocks", "text_9ftdzW", "settings", "text")),
            TemplateField("story_image", "Grafika", "shopify_image", _s("media_with_content_LgNBmd", "blocks", "media", "settings", "image")),
        ),
    ),
    TemplateZone(
        zone_id="section_quote",
        label="Sekcja — cytat",
        description="Sekcja tekstowa pod manifestem.",
        section_key="section_tAj94h",
        fields=(
            TemplateField("quote_text", "Tekst", "body", _s("section_tAj94h", "blocks", "text_RDX6ft", "settings", "text")),
        ),
    ),
)
