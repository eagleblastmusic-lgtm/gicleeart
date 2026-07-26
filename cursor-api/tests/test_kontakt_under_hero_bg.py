from __future__ import annotations

from pathlib import Path

from Komponenty.kontakt.registry import PAGE_ZONES

ROOT = Path(__file__).resolve().parents[2]


def test_kontakt_exposes_under_hero_section_background() -> None:
    zone = next(z for z in PAGE_ZONES if z.zone_id == "under_hero_bg")
    assert zone.label == "Tło pod hero"
    assert zone.settings_only is True
    assert zone.section_key == "form"

    mode = next(fld for fld in zone.fields if fld.field_id == "under_hero_bg_mode")
    assert mode.kind == "choice"
    assert dict(mode.choices) == {"image": "Grafika", "gradient": "Gradient"}
    assert mode.path == ("sections", "form", "settings", "giclee_contact_bg_mode")

    gradient = next(fld for fld in zone.fields if fld.field_id == "under_hero_gradient")
    assert gradient.path == ("sections", "form", "settings", "giclee_contact_bg_gradient")

    bg = next(fld for fld in zone.fields if fld.field_id == "under_hero_background")
    assert bg.kind == "section_background"
    assert bg.path == ("sections", "form", "settings", "background_image")

    blur = next(fld for fld in zone.fields if fld.field_id == "under_hero_blur")
    assert blur.path[-1] == "giclee_contact_bg_blur_px"
    assert next(fld for fld in zone.fields if fld.field_id == "under_hero_saturate").path[-1] == (
        "giclee_contact_bg_saturate_pct"
    )
    assert next(fld for fld in zone.fields if fld.field_id == "under_hero_brightness").path[-1] == (
        "giclee_contact_bg_brightness_pct"
    )
    assert next(fld for fld in zone.fields if fld.field_id == "under_hero_dim_overlay").path[-1] == (
        "giclee_contact_bg_dim_overlay_pct"
    )
    assert next(fld for fld in zone.fields if fld.field_id == "under_hero_scale").path[-1] == (
        "giclee_contact_bg_scale_pct"
    )


def test_kontakt_under_hero_gradient_sync_clears_media() -> None:
    from Komponenty._shared.theme_page_editor.service_base import apply_zone_values

    zone = next(z for z in PAGE_ZONES if z.zone_id == "under_hero_bg")
    template = {
        "sections": {
            "form": {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/demo.jpg",
                    "giclee_contact_bg_mode": "image",
                    "giclee_contact_bg_gradient": "v1",
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
    settings = template["sections"]["form"]["settings"]
    assert settings["giclee_contact_bg_mode"] == "gradient"
    assert settings["giclee_contact_bg_gradient"] == "v2"
    assert settings["background_media"] == "none"
    assert settings.get("background_image") in ("", None)


def test_kontakt_under_hero_schema_and_liquid() -> None:
    schema = (ROOT / "sections" / "section.liquid").read_text(encoding="utf-8")
    for key in (
        "giclee_contact_bg_mode",
        "giclee_contact_bg_gradient",
        "giclee_contact_bg_blur_px",
        "giclee_contact_bg_saturate_pct",
        "giclee_contact_bg_brightness_pct",
        "giclee_contact_bg_dim_overlay_pct",
        "giclee_contact_bg_scale_pct",
    ):
        assert key in schema

    section_snippet = (ROOT / "snippets" / "section.liquid").read_text(encoding="utf-8")
    assert "giclee_contact_bg_mode" in section_snippet
    assert "template.suffix == 'contact'" in section_snippet
    assert "template.suffix == 'faq'" in section_snippet

    contact = (ROOT / "templates" / "page.contact.json").read_text(encoding="utf-8")
    assert "giclee_contact_bg_mode" in contact
    assert "contact-section-bg-pen" in contact
