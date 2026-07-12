"""Ustawienia modulu (katalog pobierania, watki, zrodla)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from giclee_app.app_paths import atomic_write_text, config_path

_LEGACY_SETTINGS_PATH = Path(__file__).resolve().parent / "data" / "settings.json"
_SETTINGS_PATH = _LEGACY_SETTINGS_PATH
_SETTINGS = config_path("Komponenty/stronyzobrazami/data/settings.json", legacy=_LEGACY_SETTINGS_PATH)


def _settings_path(*, for_write: bool) -> Path:
    if Path(_SETTINGS_PATH) != _LEGACY_SETTINGS_PATH:
        return Path(_SETTINGS_PATH)
    return _SETTINGS.write_path if for_write else _SETTINGS.read_path()


@dataclass
class ModuleSettings:
    download_dir: str = ""
    iiif_workers: int = 8
    search_limit: int = 10
    force_png: bool = False
    source_checked: dict[str, bool] = field(default_factory=dict)


def load_settings() -> ModuleSettings:
    path = _settings_path(for_write=False)
    if not path.is_file():
        return ModuleSettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return ModuleSettings()
    if not isinstance(raw, dict):
        return ModuleSettings()
    checked = raw.get("source_checked") or {}
    if not isinstance(checked, dict):
        checked = {}
    return ModuleSettings(
        download_dir=str(raw.get("download_dir") or ""),
        iiif_workers=max(1, min(16, int(raw.get("iiif_workers") or 8))),
        search_limit=max(1, min(30, int(raw.get("search_limit") or 10))),
        force_png=bool(raw.get("force_png")),
        source_checked={str(k): bool(v) for k, v in checked.items()},
    )


def save_settings(settings: ModuleSettings) -> None:
    atomic_write_text(_settings_path(for_write=True), json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n")
