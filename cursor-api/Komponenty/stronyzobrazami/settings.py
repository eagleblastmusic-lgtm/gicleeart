"""Ustawienia modulu (katalog pobierania, watki, zrodla)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

_SETTINGS_PATH = Path(__file__).resolve().parent / "data" / "settings.json"


@dataclass
class ModuleSettings:
    download_dir: str = ""
    iiif_workers: int = 8
    search_limit: int = 10
    force_png: bool = False
    source_checked: dict[str, bool] = field(default_factory=dict)


def load_settings() -> ModuleSettings:
    if not _SETTINGS_PATH.is_file():
        return ModuleSettings()
    try:
        raw = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
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
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
