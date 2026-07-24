"""Bezpieczny zapis globalnego systemu przycisków motywu."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from giclee_app.app_paths import atomic_write_bytes, backup_path

ButtonStyle = Literal["basic", "nocturne", "frosted", "light-in-motion"]

BUTTON_STYLE_KEY = "giclee_button_style"
DEFAULT_BUTTON_STYLE: ButtonStyle = "basic"
BUTTON_STYLES = frozenset({"basic", "nocturne", "frosted", "light-in-motion"})
THEME_APPLY_CONFIRMATION = "ZASTOSUJ STYL PRZYCISKÓW"

_THEME_SETTINGS_PATH_OVERRIDE: Path | None = None
_SETTING_PATTERN = re.compile(
    rf'(?m)^(?P<indent>[ \t]*)"{BUTTON_STYLE_KEY}"[ \t]*:[ \t]*"(?P<value>[^"]*)"(?P<comma>,?)[ \t]*(?=\r?$)'
)
_PRIMARY_SETTING_PATTERN = re.compile(
    r'(?m)^(?P<indent>[ \t]*)"primary_button_border_width"[ \t]*:'
)
_CURRENT_OBJECT_PATTERN = re.compile(r'(?m)^(?P<indent>[ \t]*)"current"[ \t]*:[ \t]*\{[ \t]*$')


@dataclass(frozen=True)
class ButtonStylePlan:
    path: Path
    style: ButtonStyle
    before_bytes: bytes
    after_bytes: bytes
    before_sha256: str
    after_sha256: str
    diff_text: str

    @property
    def changed(self) -> bool:
        return self.before_bytes != self.after_bytes


@dataclass(frozen=True)
class ButtonStyleApplyResult:
    path: Path
    style: ButtonStyle
    changed: bool
    backup_path: Path | None


def _validate_style(style: str) -> ButtonStyle:
    if style not in BUTTON_STYLES:
        raise ValueError(f"Nieobsługiwany styl przycisków: {style!r}")
    return style  # type: ignore[return-value]


def theme_settings_path() -> Path:
    override = _THEME_SETTINGS_PATH_OVERRIDE
    if override is not None:
        return Path(override)

    from Komponenty.stronaglowna.service import theme_root

    return theme_root() / "config" / "settings_data.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_body(raw: str) -> str:
    stripped = raw.lstrip()
    if not stripped.startswith("/*"):
        return raw
    start = raw.find("/*")
    end = raw.find("*/", start + 2)
    if end < 0:
        raise ValueError("settings_data.json ma niedomknięty nagłówek komentarza.")
    return raw[end + 2 :]


def _parse_document(raw: str) -> dict:
    data = json.loads(_json_body(raw))
    if not isinstance(data, dict):
        raise ValueError("settings_data.json — nieprawidłowy format.")
    current = data.get("current")
    if not isinstance(current, dict):
        raise ValueError("settings_data.json — brak obiektu current.")
    return data


def load_button_style(path: Path | None = None) -> ButtonStyle:
    source = Path(path) if path is not None else theme_settings_path()
    if not source.is_file():
        raise FileNotFoundError(f"Brak pliku ustawień motywu: {source}")
    data = _parse_document(source.read_text(encoding="utf-8"))
    value = str(data["current"].get(BUTTON_STYLE_KEY) or DEFAULT_BUTTON_STYLE)
    return value if value in BUTTON_STYLES else DEFAULT_BUTTON_STYLE  # type: ignore[return-value]


def _render_settings(raw: str, style: ButtonStyle) -> str:
    _parse_document(raw)
    existing = _SETTING_PATTERN.search(raw)
    if existing:
        rendered = _SETTING_PATTERN.sub(
            lambda match: (
                f'{match.group("indent")}"{BUTTON_STYLE_KEY}": '
                f'"{style}"{match.group("comma")}'
            ),
            raw,
            count=1,
        )
    else:
        anchor = _PRIMARY_SETTING_PATTERN.search(raw)
        if anchor:
            insertion = f'{anchor.group("indent")}"{BUTTON_STYLE_KEY}": "{style}",\n'
            rendered = raw[: anchor.start()] + insertion + raw[anchor.start() :]
        else:
            current = _CURRENT_OBJECT_PATTERN.search(raw)
            if not current:
                raise ValueError("settings_data.json — nie znaleziono miejsca zapisu ustawienia.")
            child_indent = current.group("indent") + "  "
            insertion = f'\n{child_indent}"{BUTTON_STYLE_KEY}": "{style}",'
            rendered = raw[: current.end()] + insertion + raw[current.end() :]

    parsed = _parse_document(rendered)
    if parsed["current"].get(BUTTON_STYLE_KEY) != style:
        raise RuntimeError("Nie udało się wyrenderować ustawienia stylu przycisków.")
    return rendered


def _diff_text(path: Path, before: bytes, after: bytes) -> str:
    diff = "\n".join(
        difflib.unified_diff(
            before.decode("utf-8", errors="replace").splitlines(),
            after.decode("utf-8", errors="replace").splitlines(),
            fromfile=f"{path} (przed)",
            tofile=f"{path} (po)",
            lineterm="",
        )
    )
    return diff or "Brak zmian względem aktualnego pliku motywu."


def build_button_style_plan(style: str) -> ButtonStylePlan:
    selected = _validate_style(style)
    path = theme_settings_path()
    before = path.read_bytes()
    raw = before.decode("utf-8")
    after = _render_settings(raw, selected).encode("utf-8")
    return ButtonStylePlan(
        path=path,
        style=selected,
        before_bytes=before,
        after_bytes=after,
        before_sha256=_sha256(before),
        after_sha256=_sha256(after),
        diff_text=_diff_text(path, before, after),
    )


def _backup_before(plan: ButtonStylePlan) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    digest = plan.before_sha256[:12]
    backup = backup_path(
        f"Komponenty/style/button_styles/settings_data-before-{stamp}-{digest}.json"
    ).write_path
    atomic_write_bytes(backup, plan.before_bytes)
    return backup


def apply_button_style_plan(
    plan: ButtonStylePlan,
    *,
    confirmation: str,
) -> ButtonStyleApplyResult:
    if confirmation.strip() != THEME_APPLY_CONFIRMATION:
        raise ValueError(f"Wymagana fraza: {THEME_APPLY_CONFIRMATION}")

    expected_path = theme_settings_path()
    if plan.path.resolve() != expected_path.resolve():
        raise RuntimeError(f"Plan wskazuje niedozwolony plik motywu: {plan.path}")

    current = plan.path.read_bytes()
    if _sha256(current) != plan.before_sha256:
        raise RuntimeError(
            "Ustawienia motywu zmieniły się po przygotowaniu zapisu. "
            "Wczytaj aktualny styl i spróbuj ponownie."
        )

    if current == plan.after_bytes:
        return ButtonStyleApplyResult(
            path=plan.path,
            style=plan.style,
            changed=False,
            backup_path=None,
        )

    backup = _backup_before(plan)
    atomic_write_bytes(plan.path, plan.after_bytes)
    written = plan.path.read_bytes()
    if _sha256(written) != plan.after_sha256:
        raise RuntimeError(f"Nie udało się zweryfikować zapisu pliku: {plan.path}")

    return ButtonStyleApplyResult(
        path=plan.path,
        style=plan.style,
        changed=True,
        backup_path=backup,
    )


__all__ = [
    "BUTTON_STYLE_KEY",
    "BUTTON_STYLES",
    "DEFAULT_BUTTON_STYLE",
    "THEME_APPLY_CONFIRMATION",
    "ButtonStyle",
    "ButtonStyleApplyResult",
    "ButtonStylePlan",
    "apply_button_style_plan",
    "build_button_style_plan",
    "load_button_style",
    "theme_settings_path",
]
