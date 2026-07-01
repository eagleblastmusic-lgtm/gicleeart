"""Persystencja ustawień komponentu Karuzela."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

CarouselVersion = Literal["Karuzela1", "Karuzela2"]
ShowcaseLook = Literal["V1", "V2", "V3"]
SHOWCASE_LOOKS = frozenset({"V1", "V2", "V3"})

_COMPONENT_DIR = Path(__file__).resolve().parent
_SETTINGS_FILE = _COMPONENT_DIR / "settings.json"
_THEME_ASSETS_DIR = _COMPONENT_DIR.parents[2] / "assets"
_THEME_CONFIG_FILE = _THEME_ASSETS_DIR / "giclee-carousel-config.js"

DEFAULT_PREVIEW_URL = "https://gicleeart.eu/collections/jacob-van-ruisdael"
DEFAULT_VERSION: CarouselVersion = "Karuzela1"
DEFAULT_SHOWCASE_LOOK: ShowcaseLook = "V2"
STORAGE_KEY = "giclee-carousel-version"
SHOWCASE_LOOK_STORAGE_KEY = "giclee-showcase-look"


def load_settings() -> dict:
    if not _SETTINGS_FILE.is_file():
        return {}
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(data: dict) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_carousel_version() -> CarouselVersion:
    version = load_settings().get("carousel_version", DEFAULT_VERSION)
    if version in ("Karuzela1", "Karuzela2"):
        return version  # type: ignore[return-value]
    return DEFAULT_VERSION


def get_showcase_look() -> ShowcaseLook:
    look = load_settings().get("showcase_look", DEFAULT_SHOWCASE_LOOK)
    if look in SHOWCASE_LOOKS:
        return look  # type: ignore[return-value]
    return DEFAULT_SHOWCASE_LOOK


def set_carousel_version(version: CarouselVersion) -> None:
    data = load_settings()
    data["carousel_version"] = version
    save_settings(data)
    write_theme_config()


def set_showcase_look(look: ShowcaseLook) -> None:
    data = load_settings()
    data["showcase_look"] = look
    save_settings(data)
    write_theme_config()


def save_karuzela_settings(
    version: CarouselVersion,
    showcase_look: ShowcaseLook,
    preview_url: str | None = None,
) -> None:
    data = load_settings()
    data["carousel_version"] = version
    data["showcase_look"] = showcase_look
    if preview_url is not None:
        data["preview_url"] = preview_url.strip() or DEFAULT_PREVIEW_URL
    save_settings(data)
    write_theme_config()


def write_theme_config() -> Path:
    """Zapis domyślnych ustawień karuzeli w pliku motywu (wymaga deploy na sklep)."""
    version = get_carousel_version()
    look = get_showcase_look()
    if version not in ("Karuzela1", "Karuzela2"):
        version = DEFAULT_VERSION
    if look not in SHOWCASE_LOOKS:
        look = DEFAULT_SHOWCASE_LOOK
    _THEME_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    content = (
        "/** Domyślne ustawienia sekcji «Wybrane dzieła» (GicleeApp → Karuzela). */\n"
        f'window.__GICLEE_CAROUSEL_DEFAULT = "{version}";\n'
        f'window.__GICLEE_SHOWCASE_LOOK_DEFAULT = "{look}";\n'
        "(function (d) {\n"
        "  try {\n"
        '    var look = window.__GICLEE_SHOWCASE_LOOK_DEFAULT;\n'
        '    if (look === "V1" || look === "V2" || look === "V3") {\n'
        '      d.documentElement.setAttribute("data-giclee-showcase-look", look);\n'
        "    }\n"
        "  } catch (_e) {}\n"
        "})(document);\n"
    )
    _THEME_CONFIG_FILE.write_text(content, encoding="utf-8")
    return _THEME_CONFIG_FILE


def get_preview_url() -> str:
    url = str(load_settings().get("preview_url") or DEFAULT_PREVIEW_URL).strip()
    return url or DEFAULT_PREVIEW_URL


def set_preview_url(url: str) -> None:
    data = load_settings()
    data["preview_url"] = url.strip() or DEFAULT_PREVIEW_URL
    save_settings(data)


def build_preview_url(
    version: CarouselVersion | None = None,
    showcase_look: ShowcaseLook | None = None,
) -> str:
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    base = get_preview_url()
    ver = version or get_carousel_version()
    look = showcase_look or get_showcase_look()
    parsed = urlparse(base)
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k not in ("giclee_karuzela", "giclee_showcase_look")
    ]
    query.append(("giclee_karuzela", ver))
    query.append(("giclee_showcase_look", look))
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query),
            parsed.fragment,
        )
    )
