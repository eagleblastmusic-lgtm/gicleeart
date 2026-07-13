"""Persystencja ustawień i jawny, bounded writer komponentu Karuzela."""

from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from giclee_app.app_paths import atomic_write_bytes, atomic_write_text, backup_path, config_path

CarouselVersion = Literal["Karuzela1", "Karuzela2"]
ShowcaseLook = Literal["V1", "V2", "V3"]
SHOWCASE_LOOKS = frozenset({"V1", "V2", "V3"})

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_SETTINGS_FILE = _COMPONENT_DIR / "settings.json"
_SETTINGS_FILE = _LEGACY_SETTINGS_FILE
_SETTINGS = config_path("Komponenty/karuzela/settings.json", legacy=_LEGACY_SETTINGS_FILE)
_THEME_CONFIG_FILE_OVERRIDE: Path | None = None
_THEME_CONFIG_RELATIVE = Path("assets") / "giclee-carousel-config.js"

DEFAULT_PREVIEW_URL = "https://gicleeart.eu/collections/jacob-van-ruisdael"
DEFAULT_VERSION: CarouselVersion = "Karuzela1"
DEFAULT_SHOWCASE_LOOK: ShowcaseLook = "V2"
DEFAULT_HOVER_BLUR = True
STORAGE_KEY = "giclee-carousel-version"
SHOWCASE_LOOK_STORAGE_KEY = "giclee-showcase-look"
HOVER_BLUR_STORAGE_KEY = "giclee-karuzela-hover-blur"
THEME_APPLY_CONFIRMATION = "ZASTOSUJ KARUZELĘ"


@dataclass(frozen=True)
class ThemeConfigPlan:
    path: Path
    before_bytes: bytes | None
    after_bytes: bytes
    before_sha256: str | None
    after_sha256: str
    diff_text: str

    @property
    def changed(self) -> bool:
        return self.before_bytes != self.after_bytes


@dataclass(frozen=True)
class ThemeConfigApplyResult:
    path: Path
    changed: bool
    before_sha256: str | None
    after_sha256: str
    backup_path: Path | None


def _settings_path(*, for_write: bool) -> Path:
    if Path(_SETTINGS_FILE) != _LEGACY_SETTINGS_FILE:
        return Path(_SETTINGS_FILE)
    return _SETTINGS.write_path if for_write else _SETTINGS.read_path()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def theme_config_path() -> Path:
    """Zwróć jedyny dozwolony cel writer-a konfiguracji motywu."""

    override = _THEME_CONFIG_FILE_OVERRIDE
    if override is not None:
        return Path(override)
    from Komponenty.stronaglowna.service import theme_root

    return theme_root() / _THEME_CONFIG_RELATIVE


def load_settings() -> dict:
    path = _settings_path(for_write=False)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(data: dict) -> None:
    atomic_write_text(_settings_path(for_write=True), json.dumps(data, ensure_ascii=False, indent=2) + "\n")


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


def get_hover_blur() -> bool:
    value = load_settings().get("hover_blur_enabled", DEFAULT_HOVER_BLUR)
    return bool(value)


def set_carousel_version(version: CarouselVersion) -> None:
    data = load_settings()
    data["carousel_version"] = version
    save_settings(data)


def set_showcase_look(look: ShowcaseLook) -> None:
    data = load_settings()
    data["showcase_look"] = look
    save_settings(data)


def set_hover_blur(enabled: bool) -> None:
    data = load_settings()
    data["hover_blur_enabled"] = bool(enabled)
    save_settings(data)


def save_karuzela_settings(
    version: CarouselVersion,
    showcase_look: ShowcaseLook,
    preview_url: str | None = None,
    hover_blur: bool | None = None,
) -> None:
    """Zapisz wyłącznie ustawienia aplikacji; nie dotykaj plików motywu."""

    data = load_settings()
    data["carousel_version"] = version
    data["showcase_look"] = showcase_look
    if preview_url is not None:
        data["preview_url"] = preview_url.strip() or DEFAULT_PREVIEW_URL
    if hover_blur is not None:
        data["hover_blur_enabled"] = bool(hover_blur)
    save_settings(data)


def render_theme_config(
    version: CarouselVersion,
    showcase_look: ShowcaseLook,
    hover_blur: bool,
) -> bytes:
    """Zbuduj deterministyczną zawartość assetu bez zapisu."""

    if version not in ("Karuzela1", "Karuzela2"):
        raise ValueError(f"Nieobsługiwana wersja karuzeli: {version!r}")
    if showcase_look not in SHOWCASE_LOOKS:
        raise ValueError(f"Nieobsługiwany wygląd sekcji: {showcase_look!r}")
    hover_blur_js = "true" if hover_blur else "false"
    content = (
        "/** Domyślne ustawienia sekcji «Wybrane dzieła» (GicleeApp → Karuzela). */\n"
        f'window.__GICLEE_CAROUSEL_DEFAULT = "{version}";\n'
        f'window.__GICLEE_SHOWCASE_LOOK_DEFAULT = "{showcase_look}";\n'
        f"window.__GICLEE_HOVER_BLUR_ENABLED = {hover_blur_js};\n"
        "(function (d) {\n"
        "  try {\n"
        "    var look = window.__GICLEE_SHOWCASE_LOOK_DEFAULT;\n"
        "    if (look === \"V1\" || look === \"V2\" || look === \"V3\") {\n"
        "      d.documentElement.setAttribute(\"data-giclee-showcase-look\", look);\n"
        "    }\n"
        "  } catch (_e) {}\n"
        "})(document);\n"
    )
    return content.encode("utf-8")


def _diff_text(path: Path, before: bytes | None, after: bytes) -> str:
    before_text = (before or b"").decode("utf-8", errors="replace")
    after_text = after.decode("utf-8", errors="replace")
    diff = "\n".join(
        difflib.unified_diff(
            before_text.splitlines(),
            after_text.splitlines(),
            fromfile=f"{path} (przed)",
            tofile=f"{path} (po)",
            lineterm="",
        )
    )
    return diff or "Brak zmian względem aktualnego pliku motywu."


def build_theme_config_plan(
    version: CarouselVersion | None = None,
    showcase_look: ShowcaseLook | None = None,
    hover_blur: bool | None = None,
) -> ThemeConfigPlan:
    """Zbuduj podgląd writer-a bez tworzenia katalogów i bez zapisu."""

    selected_version = version or get_carousel_version()
    selected_look = showcase_look or get_showcase_look()
    selected_hover = get_hover_blur() if hover_blur is None else bool(hover_blur)
    path = theme_config_path()
    before = _read_bytes(path)
    after = render_theme_config(selected_version, selected_look, selected_hover)
    return ThemeConfigPlan(
        path=path,
        before_bytes=before,
        after_bytes=after,
        before_sha256=_sha256(before) if before is not None else None,
        after_sha256=_sha256(after),
        diff_text=_diff_text(path, before, after),
    )


def _backup_before(plan: ThemeConfigPlan) -> Path | None:
    if plan.before_bytes is None:
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    digest = (plan.before_sha256 or "missing")[:12]
    backup = backup_path(
        f"Komponenty/karuzela/theme_config/{plan.path.stem}-before-{stamp}-{digest}{plan.path.suffix}"
    ).write_path
    atomic_write_bytes(backup, plan.before_bytes)
    return backup


def apply_theme_config_plan(
    plan: ThemeConfigPlan,
    *,
    confirmation: str,
) -> ThemeConfigApplyResult:
    """Zastosuj plan po exact-target, confirmation i stale-state checks."""

    if confirmation.strip() != THEME_APPLY_CONFIRMATION:
        raise ValueError(f"Wymagana fraza: {THEME_APPLY_CONFIRMATION}")

    expected_path = theme_config_path()
    if plan.path.resolve() != expected_path.resolve():
        raise RuntimeError(f"Plan wskazuje niedozwolony plik motywu: {plan.path}")

    current = _read_bytes(plan.path)
    current_hash = _sha256(current) if current is not None else None
    if current_hash != plan.before_sha256:
        raise RuntimeError(
            "Plik motywu zmienił się po utworzeniu podglądu. "
            "Zbuduj nowy plan i ponownie sprawdź diff."
        )

    if current == plan.after_bytes:
        return ThemeConfigApplyResult(
            path=plan.path,
            changed=False,
            before_sha256=current_hash,
            after_sha256=plan.after_sha256,
            backup_path=None,
        )

    backup = _backup_before(plan)
    atomic_write_bytes(plan.path, plan.after_bytes)
    written = _read_bytes(plan.path)
    if written is None or _sha256(written) != plan.after_sha256:
        raise RuntimeError(f"Nie udało się zweryfikować zapisu pliku motywu: {plan.path}")

    return ThemeConfigApplyResult(
        path=plan.path,
        changed=True,
        before_sha256=current_hash,
        after_sha256=plan.after_sha256,
        backup_path=backup,
    )


def write_theme_config(
    *,
    confirmation: str,
    version: CarouselVersion | None = None,
    showcase_look: ShowcaseLook | None = None,
    hover_blur: bool | None = None,
) -> Path:
    """Kompatybilne API, lecz bez możliwości cichego zapisu motywu."""

    plan = build_theme_config_plan(version, showcase_look, hover_blur)
    return apply_theme_config_plan(plan, confirmation=confirmation).path


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
    hover_blur: bool | None = None,
) -> str:
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    base = get_preview_url()
    ver = version or get_carousel_version()
    look = showcase_look or get_showcase_look()
    hover = get_hover_blur() if hover_blur is None else bool(hover_blur)
    parsed = urlparse(base)
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k not in ("giclee_karuzela", "giclee_showcase_look", "giclee_hover_blur")
    ]
    query.append(("giclee_karuzela", ver))
    query.append(("giclee_showcase_look", look))
    query.append(("giclee_hover_blur", "on" if hover else "off"))
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


__all__ = [
    "DEFAULT_HOVER_BLUR",
    "DEFAULT_PREVIEW_URL",
    "DEFAULT_SHOWCASE_LOOK",
    "DEFAULT_VERSION",
    "HOVER_BLUR_STORAGE_KEY",
    "SHOWCASE_LOOK_STORAGE_KEY",
    "SHOWCASE_LOOKS",
    "STORAGE_KEY",
    "THEME_APPLY_CONFIRMATION",
    "ThemeConfigApplyResult",
    "ThemeConfigPlan",
    "apply_theme_config_plan",
    "build_preview_url",
    "build_theme_config_plan",
    "get_carousel_version",
    "get_hover_blur",
    "get_preview_url",
    "get_showcase_look",
    "load_settings",
    "render_theme_config",
    "save_karuzela_settings",
    "save_settings",
    "set_carousel_version",
    "set_hover_blur",
    "set_preview_url",
    "set_showcase_look",
    "theme_config_path",
    "write_theme_config",
]
