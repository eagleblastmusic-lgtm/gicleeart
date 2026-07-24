"""Uzupełnienie generatora pre-Hero o pełny, aktualny pipeline GICLÉE HOME FLOW.

Moduł rozszerza istniejącą integrację bez duplikowania mechanizmu zapisu wariantów.
Dzięki temu główny przycisk „Zapisz” zachowuje wszystkie assety dodane podczas
budowy sekwencji Hero → Giclée Art.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from . import prehero_integration as _base

INTRO_HOLD_KEY = "prehero_intro_hold_screens"
FRAME_MANIFEST_SNIPPET = "giclee-home-prehero-frame-manifest.liquid"

FULL_PREHERO_CODE_ASSETS: tuple[str, ...] = (
    "giclee-home-native-v2.js",
    "giclee-home-native-v2-layer-cull.css",
    "giclee-home-native-v2-layer-cull.js",
    "giclee-home-prehero-scrub.css",
    "giclee-home-prehero-frames.js",
    "giclee-home-prehero-scrub.js",
    "giclee-home-prehero-chrome.css",
    "giclee-home-prehero-chrome.js",
    "giclee-home-prehero-reveal.css",
    "giclee-home-prehero-reveal.js",
    "giclee-home-hero-horizontal-curtain.css",
    "giclee-home-hero-horizontal-curtain.js",
    "giclee-home-hero-horizontal-curtain-live-intro.css",
    "giclee-home-hero-horizontal-curtain-center.css",
    "giclee-home-hero-horizontal-curtain-matte.css",
    "giclee-home-hero-utility-bar.css",
    "giclee-home-hero-utility-bar.js",
    "giclee-home-hero-sound-consent.css",
    "giclee-home-hero-stripe-reveal.css",
    "giclee-home-hero-stripe-reveal.js",
    "giclee-home-hero-video-gate.js",
    "giclee-home-intro-curtain-effects.css",
    "giclee-home-intro-curtain-effects.js",
)

_CSS_ASSETS: tuple[str, ...] = (
    "giclee-home-native-v2-layer-cull.css",
    "giclee-home-prehero-scrub.css",
    "giclee-home-prehero-chrome.css",
    "giclee-home-prehero-reveal.css",
    "giclee-home-hero-stripe-reveal.css",
    "giclee-home-hero-horizontal-curtain.css",
    "giclee-home-hero-horizontal-curtain-live-intro.css",
    "giclee-home-hero-horizontal-curtain-center.css",
    "giclee-home-hero-horizontal-curtain-matte.css",
    "giclee-home-hero-utility-bar.css",
    "giclee-home-hero-sound-consent.css",
    "giclee-home-intro-curtain-effects.css",
)

_JS_ASSETS: tuple[str, ...] = (
    "giclee-home-native-v2.js",
    "giclee-home-native-v2-layer-cull.js",
    "giclee-home-prehero-frames.js",
    "giclee-home-prehero-scrub.js",
    "giclee-home-prehero-chrome.js",
    "giclee-home-prehero-reveal.js",
    "giclee-home-hero-stripe-reveal.js",
    "giclee-home-hero-video-gate.js",
    "giclee-home-hero-horizontal-curtain.js",
    "giclee-home-intro-curtain-effects.js",
    "giclee-home-hero-utility-bar.js",
)


def _full_asset_block() -> str:
    lines = [_base._ASSETS_BEGIN]
    lines.extend(
        "{{ '" + name + "' | asset_url | stylesheet_tag }}" for name in _CSS_ASSETS
    )
    lines.append("<script>{% render 'giclee-home-prehero-frame-manifest' %}</script>")
    lines.extend(
        "<script src=\"{{ '" + name + "' | asset_url }}\" defer></script>"
        for name in _JS_ASSETS
    )
    lines.append(_base._ASSETS_END)
    return "\n".join(lines)


def _upgrade_prehero_zone() -> None:
    from . import registry
    from .registry import HomeField

    for zone in registry.HOME_ZONES:
        if zone.zone_id != _base.PREHERO_ZONE_ID:
            continue
        if any(field.field_id == INTRO_HOLD_KEY for field in zone.fields):
            return
        field = HomeField(
            INTRO_HOLD_KEY,
            "Postój sekcji Giclée Art (ekrany)",
            "int",
            hint=(
                "1 ekran = 100vh pustego scrolla po pełnym odsłonięciu sekcji Giclée Art."
            ),
        )
        # HomeZone jest frozen, ale zachowanie tej samej instancji jest celowe:
        # service.py i home_features.py mogły już pobrać tuple HOME_ZONES.
        object.__setattr__(zone, "fields", (*zone.fields, field))
        return


def _install_config_upgrade() -> None:
    _base.PREHERO_CODE_ASSETS = FULL_PREHERO_CODE_ASSETS
    _base.PREHERO_DEFAULTS[INTRO_HOLD_KEY] = 1
    _base._SETTING_KEYS = tuple(_base.PREHERO_DEFAULTS)

    current_normalize: Callable[..., dict[str, Any]] = _base.normalize_prehero_values
    if not getattr(current_normalize, "_giclee_full_flow", False):

        def normalize_with_intro_hold(raw: dict[str, Any] | None) -> dict[str, Any]:
            out = current_normalize(raw)
            source = raw or {}
            out[INTRO_HOLD_KEY] = _base._bounded_int(
                source.get(INTRO_HOLD_KEY),
                int(_base.PREHERO_DEFAULTS[INTRO_HOLD_KEY]),
                0,
                5,
            )
            return out

        setattr(normalize_with_intro_hold, "_giclee_full_flow", True)
        setattr(normalize_with_intro_hold, "__wrapped__", current_normalize)
        _base.normalize_prehero_values = normalize_with_intro_hold

    current_export: Callable[..., dict[str, Any]] = _base.export_prehero_config
    if not getattr(current_export, "_giclee_full_flow", False):

        def export_with_intro_hold(settings: dict[str, Any] | None) -> dict[str, Any]:
            config = current_export(settings)
            values = _base.load_prehero_values(settings)
            config["introHoldVh"] = int(values.get(INTRO_HOLD_KEY) or 0) * 100
            return config

        setattr(export_with_intro_hold, "_giclee_full_flow", True)
        setattr(export_with_intro_hold, "__wrapped__", current_export)
        _base.export_prehero_config = export_with_intro_hold


def _install_asset_block_upgrade() -> None:
    current: Callable[..., str] = _base.inject_prehero_into_snippet
    if getattr(current, "_giclee_full_assets", False):
        return

    marker_pattern = re.compile(
        re.escape(_base._ASSETS_BEGIN) + r".*?" + re.escape(_base._ASSETS_END),
        flags=re.DOTALL,
    )

    def inject_with_full_assets(
        text: str,
        config: dict[str, Any] | None = None,
    ) -> str:
        generated = current(text, config)
        if _base._ASSETS_BEGIN not in generated:
            return generated
        return marker_pattern.sub(_full_asset_block(), generated).rstrip() + "\n"

    setattr(inject_with_full_assets, "_giclee_full_assets", True)
    setattr(inject_with_full_assets, "__wrapped__", current)
    _base.inject_prehero_into_snippet = inject_with_full_assets


def _missing_assets(config: dict[str, Any]) -> list[str]:
    from .service import theme_root

    root = theme_root()
    assets_dir = root / "assets"
    missing = [
        f"assets/{name}"
        for name in FULL_PREHERO_CODE_ASSETS
        if not (assets_dir / name).is_file()
    ]
    manifest = root / "snippets" / FRAME_MANIFEST_SNIPPET
    if not manifest.is_file():
        missing.append(f"snippets/{FRAME_MANIFEST_SNIPPET}")
    video_ref = str(config.get("videoRef") or "")
    if not video_ref.startswith(("shopify://files/videos/", "gid://shopify/Video/")):
        if not (assets_dir / _base.PREHERO_VIDEO_ASSET).is_file():
            missing.append(f"assets/{_base.PREHERO_VIDEO_ASSET}")
    return missing


def _install_safe_writer_guard() -> None:
    from . import home_features

    current = home_features.write_home_assets
    if getattr(current, "_giclee_full_asset_guard", False):
        return

    def write_home_assets_guarded(*args: Any, **kwargs: Any) -> Any:
        stack_enabled = kwargs.get("stack_enabled")
        if stack_enabled is not False:
            from .service import load_theme_settings

            config = _base.export_prehero_config(load_theme_settings())
            if config.get("enabled", True):
                missing = _missing_assets(config)
                if missing:
                    detail = "\n".join(f"• {name}" for name in missing)
                    raise RuntimeError(
                        "Zapis GICLÉE HOME FLOW został zatrzymany, aby nie usunąć działającej "
                        "sekwencji pre-Hero. Brakuje wymaganych plików:\n" + detail
                    )
        return current(*args, **kwargs)

    setattr(write_home_assets_guarded, "_giclee_full_asset_guard", True)
    setattr(write_home_assets_guarded, "__wrapped__", current)
    home_features.write_home_assets = write_home_assets_guarded


def install_prehero_full_generator() -> None:
    if getattr(_base, "_giclee_full_generator_installed", False):
        return
    _install_config_upgrade()
    _upgrade_prehero_zone()
    _install_asset_block_upgrade()
    _install_safe_writer_guard()
    _base._giclee_full_generator_installed = True
