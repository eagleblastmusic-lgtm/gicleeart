from __future__ import annotations

from pathlib import Path

from Komponenty.faq.registry import PAGE_ZONES

ROOT = Path(__file__).resolve().parents[2]
ACCORDION_ROW = ROOT / "blocks" / "_accordion-row.liquid"


def test_faq_accordion_exposes_question_and_answer_images() -> None:
    zone = next(z for z in PAGE_ZONES if z.zone_id == "faq_accordion")
    field_ids = {fld.field_id for fld in zone.fields}

    for n in range(1, 6):
        assert f"q{n}_heading" in field_ids
        assert f"q{n}_answer" in field_ids
        assert f"q{n}_image" in field_ids
        assert f"q{n}_answer_image" in field_ids

    q1_image = next(fld for fld in zone.fields if fld.field_id == "q1_image")
    assert q1_image.kind == "shopify_image"
    assert q1_image.path[-1] == "heading_background_image"

    q1_answer_image = next(fld for fld in zone.fields if fld.field_id == "q1_answer_image")
    assert q1_answer_image.kind == "shopify_image"
    assert q1_answer_image.path[-1] == "answer_background_image"


def test_faq_accordion_exposes_card_style_choice() -> None:
    zone = next(z for z in PAGE_ZONES if z.zone_id == "faq_accordion")
    style = next(fld for fld in zone.fields if fld.field_id == "accordion_style")
    assert style.kind == "choice"
    assert dict(style.choices) == {
        "style1": "Styl 1 — szkło i złoto",
        "style2": "Styl 2 — świecący hover (Galaxy)",
        "style3": "Styl 3 — Galaxy shell + krawędź («Losuj obraz»)",
    }
    assert style.path == (
        "sections",
        "section_9YgpHf",
        "settings",
        "giclee_faq_accordion_style",
    )
    assert zone.fields[0].field_id == "accordion_style"

    reach = next(fld for fld in zone.fields if fld.field_id == "art_gradient_reach")
    assert reach.kind == "int"
    assert reach.min_value == 0
    assert reach.max_value == 200
    assert reach.step == 2
    assert reach.unit == "%"
    assert reach.path == (
        "sections",
        "section_9YgpHf",
        "settings",
        "giclee_faq_art_gradient_reach_pct",
    )
    assert zone.fields[1].field_id == "art_gradient_reach"
    # Shopify range: max 101 steps → (200-0)/2+1 = 101
    schema = (ROOT / "sections" / "section.liquid").read_text(encoding="utf-8")
    reach_block = schema.split('"id": "giclee_faq_art_gradient_reach_pct"', 1)[1][:220]
    assert '"max": 200' in reach_block
    assert '"step": 2' in reach_block


def test_faq_exposes_under_hero_section_background() -> None:
    zone = next(z for z in PAGE_ZONES if z.zone_id == "under_hero_bg")
    assert zone.label == "Tło pod hero"
    assert zone.settings_only is True
    assert zone.section_key == "section_9YgpHf"

    mode = next(fld for fld in zone.fields if fld.field_id == "under_hero_bg_mode")
    assert mode.kind == "choice"
    assert dict(mode.choices) == {"image": "Grafika", "gradient": "Gradient"}
    assert mode.path == ("sections", "section_9YgpHf", "settings", "giclee_faq_bg_mode")

    gradient = next(fld for fld in zone.fields if fld.field_id == "under_hero_gradient")
    assert gradient.kind == "choice"
    assert ("v1", "Wersja 1 — ciepły radial + ciemny linear") in gradient.choices
    assert ("v2", "Wersja 2 — radial + winieta + linear") in gradient.choices
    assert gradient.path == ("sections", "section_9YgpHf", "settings", "giclee_faq_bg_gradient")

    bg = next(fld for fld in zone.fields if fld.field_id == "under_hero_background")
    assert bg.kind == "section_background"
    assert bg.path == ("sections", "section_9YgpHf", "settings", "background_image")

    blur = next(fld for fld in zone.fields if fld.field_id == "under_hero_blur")
    assert blur.kind == "int"
    assert blur.min_value == 0
    assert blur.max_value == 20
    assert blur.unit == "px"
    assert blur.path[-1] == "giclee_faq_bg_blur_px"

    saturate = next(fld for fld in zone.fields if fld.field_id == "under_hero_saturate")
    assert saturate.max_value == 100
    assert saturate.unit == "%"
    assert saturate.path[-1] == "giclee_faq_bg_saturate_pct"

    brightness = next(fld for fld in zone.fields if fld.field_id == "under_hero_brightness")
    assert brightness.path[-1] == "giclee_faq_bg_brightness_pct"

    dim = next(fld for fld in zone.fields if fld.field_id == "under_hero_dim_overlay")
    assert dim.path[-1] == "giclee_faq_bg_dim_overlay_pct"

    scale = next(fld for fld in zone.fields if fld.field_id == "under_hero_scale")
    assert scale.max_value == 12
    assert scale.path[-1] == "giclee_faq_bg_scale_pct"


def test_faq_under_hero_gradient_sync_clears_media() -> None:
    from Komponenty._shared.theme_page_editor.service_base import apply_zone_values
    from Komponenty.faq.registry import PAGE_ZONES

    zone = next(z for z in PAGE_ZONES if z.zone_id == "under_hero_bg")
    template = {
        "sections": {
            "section_9YgpHf": {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/demo.jpg",
                    "giclee_faq_bg_mode": "image",
                    "giclee_faq_bg_gradient": "v1",
                }
            }
        }
    }
    apply_zone_values(
        template,
        zone,
        {
            "_enabled": True,
            "under_hero_bg_mode": "gradient",
            "under_hero_gradient": "v2",
            "under_hero_background": {
                "media": "image",
                "ref": "shopify://shop_images/demo.jpg",
                "overlay_pct": 20,
            },
        },
    )
    settings = template["sections"]["section_9YgpHf"]["settings"]
    assert settings["giclee_faq_bg_mode"] == "gradient"
    assert settings["giclee_faq_bg_gradient"] == "v2"
    assert settings["background_media"] == "none"
    assert settings.get("background_image") in ("", None)


def test_accordion_row_renders_art_gradient_layers() -> None:
    source = ACCORDION_ROW.read_text(encoding="utf-8")
    assert "heading_background_image" in source
    assert "answer_background_image" in source
    assert "details__art" in source
    assert "details__art-veil" in source
    assert "details--art" in source
    assert "details--art-shared" in source
    assert "--details-art-image" in source
    assert "linear-gradient" in source
    assert "--faq-art-gradient-reach" in source
    # Shared mode: kadrowanie X+Y z ustawień (domyślnie X=72 jak dawniej).
    assert "--details-art-ox: {{ heading_art_ox }}%" in source
    assert "--details-art-oy: {{ heading_art_oy }}%" in source
    assert (
        "--details-art-position: {{ heading_art_ox }}% {{ heading_art_oy }}%"
        in source
    )
    assert "heading_background_image_object_x" in source
    assert "heading_background_image_object_y" in source
    assert "answer_background_image_object_x" in source
    assert "200% auto" in source
    assert '"min": -50' in source
    assert '"max": 150' in source
    assert "72% 0%" not in source

    galaxy_css = (ROOT / "assets" / "faq-accordion-galaxy.css").read_text(encoding="utf-8")
    assert "--details-art-ox" in galaxy_css
    assert "200% auto" in galaxy_css


def test_faq_under_hero_liquid_marks_image_and_gradient_modes() -> None:
    section_snippet = (ROOT / "snippets" / "section.liquid").read_text(encoding="utf-8")
    assert "giclee_faq_bg_mode" in section_snippet
    assert "--faq-bg-blur" in section_snippet
    assert "--faq-bg-saturate" in section_snippet
    assert "--faq-bg-brightness" in section_snippet
    assert "--faq-bg-dim-overlay" in section_snippet
    assert "--faq-bg-scale" in section_snippet
    assert "giclee_faq_art_gradient_reach_pct" in section_snippet
    assert "--faq-art-gradient-reach" in section_snippet
    assert "giclee_faq_image_active" in section_snippet
    assert "faq-section--bg-image" in section_snippet
    assert "faq-section--gradient-" in section_snippet
    assert "section-background--faq-custom" in section_snippet
    assert "giclee_faq_accordion_style" in section_snippet
    assert "faq-accordion-" in section_snippet
    assert "style3" in section_snippet
    assert "data-faq-galaxy-lottie-url" not in section_snippet
    assert "data-faq-galaxy-star-url" not in section_snippet

    schema = (ROOT / "sections" / "section.liquid").read_text(encoding="utf-8")
    assert "giclee_faq_bg_blur_px" in schema
    assert "giclee_faq_bg_saturate_pct" in schema
    assert "giclee_faq_bg_brightness_pct" in schema
    assert "giclee_faq_bg_dim_overlay_pct" in schema
    assert "giclee_faq_bg_scale_pct" in schema
    assert "giclee_faq_art_gradient_reach_pct" in schema
    assert "giclee_faq_bg_extra_dim_pct" not in schema

    overrides = (ROOT / "snippets" / "giclee-theme-inline-overrides.liquid").read_text(
        encoding="utf-8"
    )
    assert "faq-section--bg-image" in overrides
    assert "position: absolute" in overrides
    assert "faq-section--gradient-v1" in overrides
    assert "faq-section--gradient-v2" in overrides
    assert "faq-accordion-style2" in overrides
    assert "faq-accordion-style3" in overrides
    assert "--faq-gx" in overrides
    assert "--faq-bg-blur" in overrides
    assert "--faq-bg-dim-overlay" in overrides
    assert "--faq-art-gradient-reach" in overrides
    assert "rgba(200, 205, 212" in overrides
    assert "mix-blend-mode: screen" in overrides
    assert "2px solid rgba(255, 255, 255, 0.15)" in overrides
    assert "giclee-galaxy-btn__shell" in overrides
    assert "mask-composite: exclude" in overrides
    assert "faq-galaxy-card__plate" in overrides
    style2_block = overrides.split("faq-accordion-style2", 1)[1].split("FAQ Style 3", 1)[0]
    assert "--details-art-image" in style2_block
    assert "--faq-art-gradient-reach" in style2_block
    assert "svg-wrapper.icon-caret" in style2_block
    assert "background-image: none !important" in style2_block
    assert "details::after" in style2_block
    assert ".details__art,\n" not in style2_block
    assert "details .details__art" not in style2_block

    entrance = (ROOT / "assets" / "faq-accordion-entrance.js").read_text(encoding="utf-8")
    assert "faq-accordion-style2" in entrance
    assert "initStyle2GalaxyHover" in entrance
    assert "--faq-gx" in entrance
    assert "faq-accordion-style3" in entrance
    assert "initStyle3GalaxyFull" in entrance
    assert "faq-galaxy-card__shell" in entrance
    assert "faq-galaxy-card__edge" in entrance
    assert "faq-galaxy-card__circle" not in entrance
    assert "data-faq-galaxy-lottie" not in entrance
    assert "data-faq-galaxy-star" not in entrance
    # Shell musi owijać <details> — wstrzyknięcie do środka chowa chrome gdy zamknięte.
    assert "insertBefore(wrap, card)" in entrance
    assert "wrap.appendChild(card)" in entrance
    assert "--faq-gx" in entrance

    galaxy_css = (ROOT / "assets" / "faq-accordion-galaxy.css").read_text(encoding="utf-8")
    assert "faq-galaxy-card__shell" in galaxy_css
    assert "faq-galaxy-card__plate" in galaxy_css
    assert "faq-galaxy-card__edge" in galaxy_css
    assert "mask-composite: exclude" in galaxy_css
    assert "faq-galaxy-card__circle" not in galaxy_css
    assert ".faq-galaxy-card {" in galaxy_css
    assert "--faq-art-gradient-reach" in galaxy_css

    scripts = (ROOT / "snippets" / "scripts.liquid").read_text(encoding="utf-8")
    assert "faq-accordion-galaxy.css" in scripts
    assert "lottie.min.js" not in scripts.split("template.suffix == 'faq'")[1].split("elsif")[0]

    schema = (ROOT / "sections" / "section.liquid").read_text(encoding="utf-8")
    assert '"id": "giclee_faq_accordion_style"' in schema
    assert '"id": "giclee_faq_art_gradient_reach_pct"' in schema
    assert '"value": "style3"' in schema
