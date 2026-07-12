"""Content-generator preset library.

Legacy presets stay readable from the source checkout. New mutable preset
writes go to Roaming AppData configuration.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from giclee_app.app_paths import atomic_write_text, config_path

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "data"
_LEGACY_FILE = _LEGACY_DATA_DIR / "content_presets.json"

# Backward-compatible constants for current tests/tools.
_DATA_DIR = _LEGACY_DATA_DIR
_FILE = _LEGACY_FILE


def _preset_file(*, for_write: bool = False) -> Path:
    current = Path(_FILE)
    legacy = Path(_LEGACY_DATA_DIR) / "content_presets.json"
    if current != legacy:
        return current
    app_path = config_path(
        "Komponenty/socialmedia/data/content_presets.json",
        legacy=legacy,
    )
    return app_path.write_path if for_write else app_path.read_path()


@dataclass
class Preset:
    id: str
    name: str
    platforms: list[str] = field(default_factory=list)
    language: str = "pl"
    tone: str = ""
    topic: str = ""
    link: str = ""
    mode: str = "single"
    series_count: int = 5
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def new(
        *,
        name: str,
        platforms: Iterable[str],
        language: str = "pl",
        tone: str = "",
        topic: str = "",
        link: str = "",
        mode: str = "single",
        series_count: int = 5,
    ) -> "Preset":
        now = datetime.now().isoformat(timespec="seconds")
        return Preset(
            id=uuid.uuid4().hex[:10],
            name=name.strip() or "(bez nazwy)",
            platforms=[c for c in platforms if c],
            language=(language or "pl").strip(),
            tone=(tone or "").strip(),
            topic=(topic or "").strip(),
            link=(link or "").strip(),
            mode="series" if (mode or "single").strip() == "series" else "single",
            series_count=max(2, min(7, int(series_count or 5))),
            created_at=now,
            updated_at=now,
        )


def _load_raw() -> list[dict]:
    path = _preset_file()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("presets") if isinstance(data, dict) else None
    return [x for x in raw or [] if isinstance(x, dict)]


def _from_dict(d: dict) -> Preset:
    return Preset(
        id=str(d.get("id") or uuid.uuid4().hex[:10]),
        name=str(d.get("name") or "(bez nazwy)"),
        platforms=[str(c) for c in (d.get("platforms") or []) if str(c).strip()],
        language=str(d.get("language") or "pl"),
        tone=str(d.get("tone") or ""),
        topic=str(d.get("topic") or ""),
        link=str(d.get("link") or ""),
        mode=str(d.get("mode") or "single"),
        series_count=int(d.get("series_count") or 5),
        created_at=str(d.get("created_at") or ""),
        updated_at=str(d.get("updated_at") or ""),
    )


def load_presets() -> list[Preset]:
    items = [_from_dict(d) for d in _load_raw()]
    items.sort(key=lambda x: (x.name.lower(), x.updated_at))
    return items


def save_presets(presets: Iterable[Preset]) -> None:
    payload = {"presets": [asdict(p) for p in presets]}
    atomic_write_text(
        _preset_file(for_write=True),
        json.dumps(payload, indent=2, ensure_ascii=False),
    )


def add_preset(preset: Preset) -> Preset:
    items = load_presets()
    items.append(preset)
    save_presets(items)
    return preset


def update_preset(preset_id: str, **changes) -> Preset | None:
    items = load_presets()
    for i, p in enumerate(items):
        if p.id == preset_id:
            for k, v in changes.items():
                if hasattr(p, k):
                    setattr(p, k, v)
            p.updated_at = datetime.now().isoformat(timespec="seconds")
            items[i] = p
            save_presets(items)
            return p
    return None


def delete_preset(preset_id: str) -> bool:
    items = load_presets()
    filtered = [p for p in items if p.id != preset_id]
    if len(filtered) == len(items):
        return False
    save_presets(filtered)
    return True


def get_preset(preset_id: str) -> Preset | None:
    for p in load_presets():
        if p.id == preset_id:
            return p
    return None
