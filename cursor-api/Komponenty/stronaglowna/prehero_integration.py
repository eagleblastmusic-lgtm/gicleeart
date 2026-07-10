"""Edycja i eksport sekwencji pre-Hero strony głównej.

Pre-Hero nie jest natywną sekcją ``templates/index.json``. Jest wstrzykiwany przed
Hero przez assety ``giclee-home-prehero-*``. Ustawienia są przechowywane w
``config/settings_data.json`` (a więc także osobno w każdym wariancie strony głównej),
a generator eksportuje je do ``window.GICLEE_PREHERO_CONFIG``.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

PREHERO_ZONE_ID = "prehero_scroll"
PREHERO_VIDEO_ASSET = "giclee-home-prehero-scrub.mp4"
PREHERO_CODE_ASSETS = (
    "giclee-home-prehero-scrub.css",
    "giclee-home-prehero-scrub.js",
    "giclee-home-prehero-chrome.css",
    "giclee-home-prehero-chrome.js",
    "giclee-home-prehero-reveal.css",
    "giclee-home-prehero-reveal.js",
)

DEFAULT_COPY_TEXT = (
    "Fotografia i obraz zaczynają żyć w pełni\n"
    "dopiero wtedy, gdy opuszczają ekran\n"
    "i stają się częścią świata fizycznego."
)

PREHERO_DEFAULTS: dict[str, Any] = {
    "prehero_enabled": True,
    "prehero_video": "",
    "prehero_scroll_screens": 6,
    "prehero_reveal_screens": 2,
    "prehero_hero_rise_screens": 1,
    "prehero_copy_enabled": True,
    "prehero_copy_text": DEFAULT_COPY_TEXT,
}

_SETTING_KEYS = tuple(PREHERO_DEFAULTS)
_SCRIPT_BEGIN = "/* GICLEE_PREHERO_CONFIG_BEGIN */"
_SCRIPT_END = "/* GICLEE_PREHERO_CONFIG_END */"
_ASSETS_BEGIN = "{% comment %} GICLEE_PREHERO_ASSETS_BEGIN {% endcomment %}"
_ASSETS_END = "{% comment %} GICLEE_PREHERO_ASSETS_END {% endcomment %}"


def _bounded_int(raw: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def normalize_prehero_values(raw: dict[str, Any] | None) -> dict[str, Any]:
    source = raw or {}
    hero_rise = _bounded_int(
        source.get("prehero_hero_rise_screens"),
        int(PREHERO_DEFAULTS["prehero_hero_rise_screens"]),
        1,
        5,
    )
    scroll = _bounded_int(
        source.get("prehero_scroll_screens"),
        int(PREHERO_DEFAULTS["prehero_scroll_screens"]),
        3,
        20,
    )
    scroll = max(scroll, hero_rise + 2)
    max_reveal = max(1, scroll - 1 - hero_rise)
    reveal = _bounded_int(
        source.get("prehero_reveal_screens"),
        int(PREHERO_DEFAULTS["prehero_reveal_screens"]),
        1,
        min(10, max_reveal),
    )

    text = str(source.get("prehero_copy_text") or DEFAULT_COPY_TEXT).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = DEFAULT_COPY_TEXT.splitlines()
    lines = lines[:5]

    video = str(source.get("prehero_video") or "").strip()
    if video and not video.startswith(("shopify://files/videos/", "gid://shopify/Video/")):
        video = ""

    return {
        "prehero_enabled": bool(source.get("prehero_enabled", True)),
        "prehero_video": video,
        "prehero_scroll_screens": scroll,
        "prehero_reveal_screens": reveal,
        "prehero_hero_rise_screens": hero_rise,
        "prehero_copy_enabled": bool(source.get("prehero_copy_enabled", True)),
        "prehero_copy_text": "\n".join(lines),
    }


def _prehero_zone() -> Any:
    from .registry import HomeField, HomeZone

    return HomeZone(
        zone_id=PREHERO_ZONE_ID,
        label="Pre-Hero — scrollowane wideo",
        description=(
            "Pełnoekranowe wideo sterowane przewijaniem przed «Hero — slideshow». "
            "W końcowej części filmu portal otwiera się od środka, wyświetla tekst, "
            "a następnie od dołu wjeżdża oryginalny Hero z filmem-kolażem."
        ),
        section_key="",
        settings_only=True,
        fields=(
            HomeField(
                "prehero_enabled",
                "Sekcja aktywna",
                "bool",
                hint="Wyłączenie usuwa pre-Hero z wygenerowanego snippetu, bez kasowania assetów.",
            ),
            HomeField(
                "prehero_video",
                "Film do scrollowania",
                "shopify_video",
                hint=(
                    "Wybierz lub wgraj film w Shopify Files. Puste pole zachowuje lokalny "
                    "assets/giclee-home-prehero-scrub.mp4."
                ),
            ),
            HomeField(
                "prehero_scroll_screens",
                "Długość całej sekwencji (ekrany)",
                "int",
                hint="6 ekranów = 600vh wysokości sekcji.",
            ),
            HomeField(
                "prehero_reveal_screens",
                "Start portalu przed końcem filmu (ekrany)",
                "int",
                hint="2 ekrany = portal zaczyna się około 200vh przed końcem scrubbingu.",
            ),
            HomeField(
                "prehero_hero_rise_screens",
                "Wjazd oryginalnego Hero (ekrany)",
                "int",
                hint="1 ekran = Hero wjeżdża od dołu przez 100vh.",
            ),
            HomeField(
                "prehero_copy_enabled",
                "Pokaż tekst w portalu",
                "bool",
            ),
            HomeField(
                "prehero_copy_text",
                "Tekst przejścia",
                "body",
                hint="Każda niepusta linia jest animowana osobno; maksymalnie 5 linii.",
            ),
        ),
    )


def register_prehero_zone() -> None:
    from . import registry

    if any(zone.zone_id == PREHERO_ZONE_ID for zone in registry.HOME_ZONES):
        return
    registry.HOME_ZONES = (_prehero_zone(), *registry.HOME_ZONES)


def _settings_current(settings: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(settings, dict):
        return {}
    current = settings.get("current")
    if not isinstance(current, dict):
        current = {}
        settings["current"] = current
    return current


def load_prehero_values(settings: dict[str, Any] | None) -> dict[str, Any]:
    current = _settings_current(settings)
    values = normalize_prehero_values({key: current.get(key) for key in _SETTING_KEYS})
    values["_enabled"] = bool(values["prehero_enabled"])
    return values


def apply_prehero_values(settings: dict[str, Any], values: dict[str, Any]) -> None:
    current = _settings_current(settings)
    normalized = normalize_prehero_values(values)
    current.update(normalized)


def export_prehero_config(settings: dict[str, Any] | None) -> dict[str, Any]:
    values = load_prehero_values(settings)
    lines = [line.strip() for line in values["prehero_copy_text"].splitlines() if line.strip()]
    return {
        "enabled": bool(values["prehero_enabled"]),
        "scrollHeightVh": int(values["prehero_scroll_screens"]) * 100,
        "revealOverlapVh": int(values["prehero_reveal_screens"]) * 100,
        "heroRiseVh": int(values["prehero_hero_rise_screens"]) * 100,
        "copyEnabled": bool(values["prehero_copy_enabled"]),
        "copyLines": lines,
        "videoRef": str(values["prehero_video"] or ""),
    }


def wrap_service_fields() -> None:
    from . import service

    current_load: Callable[..., Any] = service.load_zone_values
    current_apply: Callable[..., Any] = service.apply_zone_values
    if getattr(current_load, "_giclee_prehero_wrapped", False):
        return

    def load_zone_values_with_prehero(
        template: dict[str, Any],
        zone: Any,
        *,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if getattr(zone, "zone_id", "") == PREHERO_ZONE_ID:
            return load_prehero_values(settings)
        return current_load(template, zone, settings=settings)

    def apply_zone_values_with_prehero(
        template: dict[str, Any],
        zone: Any,
        values: dict[str, Any],
        *,
        settings: dict[str, Any] | None = None,
    ) -> None:
        if getattr(zone, "zone_id", "") == PREHERO_ZONE_ID:
            if settings is not None:
                apply_prehero_values(settings, values)
            return
        current_apply(template, zone, values, settings=settings)

    setattr(load_zone_values_with_prehero, "_giclee_prehero_wrapped", True)
    setattr(apply_zone_values_with_prehero, "_giclee_prehero_wrapped", True)
    service.load_zone_values = load_zone_values_with_prehero
    service.apply_zone_values = apply_zone_values_with_prehero


def _remove_marked_block(text: str, begin: str, end: str) -> str:
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\s*", flags=re.DOTALL)
    return pattern.sub("", text)


def _video_liquid(config: dict[str, Any]) -> str:
    ref = str(config.get("videoRef") or "")
    if ref.startswith("shopify://files/videos/"):
        filename = ref.rsplit("/", 1)[-1].replace("'", "\\'")
        return "{{ '" + filename + "' | file_url | json }}"
    return "{{ 'giclee-home-prehero-scrub.mp4' | asset_url | json }}"


def inject_prehero_into_snippet(text: str, config: dict[str, Any] | None = None) -> str:
    clean = _remove_marked_block(text, _SCRIPT_BEGIN, _SCRIPT_END)
    clean = _remove_marked_block(clean, _ASSETS_BEGIN, _ASSETS_END)
    cfg = dict(config or export_prehero_config(None))

    if "window.GICLEE_HOME_STACK = true;" not in clean or not cfg.get("enabled", True):
        return clean.rstrip() + "\n"

    close_index = clean.find("</script>")
    if close_index < 0:
        return clean

    public_cfg = {key: value for key, value in cfg.items() if key != "videoRef"}
    script_block = "\n".join(
        (
            "",
            _SCRIPT_BEGIN,
            "window.GICLEE_HOME_SECTION_SCROLL_DISABLED = true;",
            "window.GICLEE_HOME_SCROLL_CONFIG = Object.assign({}, window.GICLEE_HOME_SCROLL_CONFIG || {}, { enabled: false });",
            "window.GICLEE_PREHERO_CONFIG = " + json.dumps(public_cfg, ensure_ascii=False) + ";",
            "window.GICLEE_PREHERO_SCRUB_VIDEO_URL = " + _video_liquid(cfg) + ";",
            "(function () {",
            "  function disableHomeSectionScroll() {",
            "    var api = window.GICLEE_HOME_SECTION_SCROLL;",
            "    if (api && typeof api.destroy === 'function') api.destroy();",
            "    document.documentElement.removeAttribute('data-giclee-home-section-scroll');",
            "    document.documentElement.classList.remove('giclee-home-section-scroll');",
            "  }",
            "  if (document.readyState === 'loading') {",
            "    document.addEventListener('DOMContentLoaded', function () { requestAnimationFrame(disableHomeSectionScroll); }, { once: true });",
            "  } else { requestAnimationFrame(disableHomeSectionScroll); }",
            "  window.addEventListener('load', disableHomeSectionScroll, { once: true });",
            "})();",
            _SCRIPT_END,
            "",
        )
    )

    asset_block = "\n".join(
        (
            "",
            _ASSETS_BEGIN,
            "{{ 'giclee-home-prehero-scrub.css' | asset_url | stylesheet_tag }}",
            "{{ 'giclee-home-prehero-chrome.css' | asset_url | stylesheet_tag }}",
            "{{ 'giclee-home-prehero-reveal.css' | asset_url | stylesheet_tag }}",
            "<script src=\"{{ 'giclee-home-prehero-scrub.js' | asset_url }}\" defer></script>",
            "<script src=\"{{ 'giclee-home-prehero-chrome.js' | asset_url }}\" defer></script>",
            "<script src=\"{{ 'giclee-home-prehero-reveal.js' | asset_url }}\" defer></script>",
            _ASSETS_END,
            "",
        )
    )

    with_script = clean[:close_index] + script_block + clean[close_index:]
    after_script = close_index + len(script_block) + len("</script>")
    return (with_script[:after_script] + asset_block + with_script[after_script:]).rstrip() + "\n"


def prehero_assets_ready(config: dict[str, Any] | None = None) -> bool:
    from .service import theme_root

    cfg = config or export_prehero_config(None)
    assets_dir = theme_root() / "assets"
    if not all((assets_dir / name).is_file() for name in PREHERO_CODE_ASSETS):
        return False
    if str(cfg.get("videoRef") or "").startswith(("shopify://files/videos/", "gid://shopify/Video/")):
        return True
    return (assets_dir / PREHERO_VIDEO_ASSET).is_file()


def patch_generated_prehero_snippet(config: dict[str, Any] | None = None) -> bool:
    from .service import theme_root

    cfg = config or export_prehero_config(None)
    path = theme_root() / "snippets" / "giclee-home-stack-critical.liquid"
    if not path.is_file():
        return False

    original = path.read_text(encoding="utf-8")
    if cfg.get("enabled", True) and not prehero_assets_ready(cfg):
        return False
    updated = inject_prehero_into_snippet(original, cfg)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def wrap_home_assets_writer() -> None:
    from . import home_features

    current: Callable[..., Any] = home_features.write_home_assets
    if getattr(current, "_giclee_prehero_wrapped", False):
        return

    def write_home_assets_with_prehero(*args: Any, **kwargs: Any) -> Any:
        result = current(*args, **kwargs)
        try:
            from .service import load_theme_settings

            cfg = export_prehero_config(load_theme_settings())
            patch_generated_prehero_snippet(cfg)
        except Exception:
            pass
        return result

    setattr(write_home_assets_with_prehero, "_giclee_prehero_wrapped", True)
    setattr(write_home_assets_with_prehero, "__wrapped__", current)
    home_features.write_home_assets = write_home_assets_with_prehero


def install_prehero_integration() -> None:
    register_prehero_zone()
    wrap_service_fields()
    wrap_home_assets_writer()
