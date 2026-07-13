"""Persistence for the Social Media cycle.

The source-tree files remain read-only compatibility fallbacks. Mutable queue,
state and media writes go to Local AppData; configuration and Meta credentials
go to Roaming AppData.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from giclee_app.app_paths import atomic_write_text, config_path, data_path

from . import platforms_cykl as _cp

_COMPONENT_DIR = Path(__file__).resolve().parents[1]
_LEGACY_DATA_DIR = _COMPONENT_DIR / "data" / "cykl"
_DATA_DIR = _LEGACY_DATA_DIR
_QUEUE_FILE = _DATA_DIR / "queue.json"
_GEN_STATE_FILE = _DATA_DIR / "generation_state.json"
_META_STATE_FILE = _DATA_DIR / "meta_state.json"
_CONFIG_FILE = _DATA_DIR / "config.json"
_CREDS_FILE = _DATA_DIR / "meta_credentials.json"
IMAGES_DIR = _DATA_DIR / "Obrazy"

_RUNTIME_ROOT = "Komponenty/socialmedia/data/cykl"
_PathBucket = Literal["data", "config"]
_DIRECTORY_CONSTANTS = {
    "DATA_DIR": ("_DATA_DIR", "_LEGACY_DATA_DIR", ""),
    "IMAGES_DIR": ("IMAGES_DIR", "_LEGACY_DATA_DIR", "Obrazy"),
}


def _runtime_file(
    current_path: Path,
    filename: str,
    *,
    bucket: _PathBucket,
    for_write: bool = False,
) -> Path:
    current = Path(current_path)
    legacy = Path(_LEGACY_DATA_DIR) / filename
    if current != legacy:
        return current
    factory = config_path if bucket == "config" else data_path
    app_path = factory(f"{_RUNTIME_ROOT}/{filename}", legacy=legacy)
    return app_path.write_path if for_write else app_path.read_path()


def _queue_file(*, for_write: bool = False) -> Path:
    return _runtime_file(_QUEUE_FILE, "queue.json", bucket="data", for_write=for_write)


def _generation_state_file(*, for_write: bool = False) -> Path:
    return _runtime_file(
        _GEN_STATE_FILE,
        "generation_state.json",
        bucket="data",
        for_write=for_write,
    )


def _meta_state_file(*, for_write: bool = False) -> Path:
    return _runtime_file(
        _META_STATE_FILE,
        "meta_state.json",
        bucket="data",
        for_write=for_write,
    )


def _config_file(*, for_write: bool = False) -> Path:
    return _runtime_file(_CONFIG_FILE, "config.json", bucket="config", for_write=for_write)


def _credentials_file(*, for_write: bool = False) -> Path:
    return _runtime_file(
        _CREDS_FILE,
        "meta_credentials.json",
        bucket="config",
        for_write=for_write,
    )


def _explicit_directory_override(
    constant_name: str,
    *,
    for_write: bool,
) -> Path | None:
    """Return a validated explicit directory override, if one is active."""

    name = str(constant_name).strip()
    try:
        current_name, legacy_root_name, relative_legacy = _DIRECTORY_CONSTANTS[name]
    except KeyError as exc:
        raise ValueError(f"Unsafe Social Media cycle directory constant: {constant_name!r}") from exc

    try:
        current = Path(globals()[current_name])
        legacy = Path(globals()[legacy_root_name])
    except KeyError as exc:  # pragma: no cover - guarded by the static mapping
        raise RuntimeError(f"Incomplete Social Media cycle directory mapping for {name}") from exc

    if relative_legacy:
        legacy = legacy / relative_legacy
    if current == legacy:
        return None
    if for_write:
        current.mkdir(parents=True, exist_ok=True)
    return current


def data_dir(*, for_write: bool = False) -> Path:
    override = _explicit_directory_override("DATA_DIR", for_write=for_write)
    if override is not None:
        return override
    legacy = Path(_LEGACY_DATA_DIR)
    app_path = data_path(_RUNTIME_ROOT, legacy=legacy)
    path = app_path.write_path if for_write else app_path.read_path()
    if for_write:
        path.mkdir(parents=True, exist_ok=True)
    return path


def images_dir(*, for_write: bool = False) -> Path:
    override = _explicit_directory_override("IMAGES_DIR", for_write=for_write)
    if override is not None:
        return override
    legacy = Path(_LEGACY_DATA_DIR) / "Obrazy"
    app_path = data_path(f"{_RUNTIME_ROOT}/Obrazy", legacy=legacy)
    path = app_path.write_path if for_write else app_path.read_path()
    if for_write:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_dirs() -> None:
    data_dir(for_write=True)
    images_dir(for_write=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class CykleItem:
    id: str
    artist: str
    artist_handle: str
    painting_title_pl: str
    painting_title_en: str
    painting_handle: str
    product_id: int
    product_gid: str
    product_image_url: str
    product_image_alt: str
    description_pl: str
    description_en: str

    artist_position: int = 0
    artist_total: int = 0
    is_first_of_artist: bool = False
    is_last_of_artist: bool = False
    is_new_artist: bool = False
    is_new_painting: bool = False
    next_artist: str = ""

    scheduled_at: str = ""
    slot: str = ""

    caption_pl: str = ""
    caption_en: str = ""
    caption_fb_pl: str = ""
    caption_fb_en: str = ""
    caption_ig_pl: str = ""
    caption_ig_en: str = ""
    hashtags_pl: list[str] = field(default_factory=list)
    hashtags_en: list[str] = field(default_factory=list)
    zoom_hints: list[str] = field(default_factory=list)

    image_main: str = ""
    image_zooms: list[str] = field(default_factory=list)
    image_mockup: str = ""

    image_fb_main: str = ""
    image_fb_zooms: list[str] = field(default_factory=list)
    image_fb_mockup: str = ""
    image_ig_main: str = ""
    image_ig_zooms: list[str] = field(default_factory=list)
    image_ig_mockup: str = ""

    image_fb_pl: str = ""
    image_fb_en: str = ""
    image_ig_pl: list[str] = field(default_factory=list)
    image_ig_en: list[str] = field(default_factory=list)

    cdn_main: str = ""
    cdn_zooms: list[str] = field(default_factory=list)
    cdn_mockup: str = ""
    cdn_fb_main: str = ""
    cdn_fb_zooms: list[str] = field(default_factory=list)
    cdn_fb_mockup: str = ""
    cdn_ig_main: str = ""
    cdn_ig_zooms: list[str] = field(default_factory=list)
    cdn_ig_mockup: str = ""

    published_fb_pl: str = ""
    published_fb_en: str = ""
    published_ig_pl: str = ""
    published_ig_en: str = ""
    media_ids: dict[str, str] = field(default_factory=dict)

    channels_enabled: list[str] = field(default_factory=lambda: list(_cp.CHANNEL_ORDER))

    status: str = "pending"
    manual_override: bool = False
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def new(**kwargs: Any) -> "CykleItem":
        now = _now_iso()
        defaults = {
            "id": uuid.uuid4().hex[:12],
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(kwargs)
        return CykleItem(**defaults)


def _item_from_dict(d: dict[str, Any]) -> CykleItem:
    allowed = {f.name for f in CykleItem.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    cleaned = {k: v for k, v in d.items() if k in allowed}
    if not cleaned.get("id"):
        cleaned["id"] = uuid.uuid4().hex[:12]
    if not cleaned.get("created_at"):
        cleaned["created_at"] = _now_iso()
    if not cleaned.get("updated_at"):
        cleaned["updated_at"] = _now_iso()
    for list_key in (
        "hashtags_pl",
        "hashtags_en",
        "zoom_hints",
        "image_zooms",
        "image_ig_pl",
        "image_ig_en",
        "image_fb_zooms",
        "image_ig_zooms",
        "cdn_zooms",
        "cdn_fb_zooms",
        "cdn_ig_zooms",
        "channels_enabled",
    ):
        if cleaned.get(list_key) is None:
            cleaned[list_key] = []
    if cleaned.get("media_ids") is None:
        cleaned["media_ids"] = {}
    if not cleaned.get("channels_enabled"):
        cleaned["channels_enabled"] = list(_cp.CHANNEL_ORDER)
    return CykleItem(**cleaned)


def load_queue() -> list[CykleItem]:
    path = _queue_file()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("items", []) if isinstance(data, dict) else []
    return [_item_from_dict(x) for x in raw if isinstance(x, dict)]


def save_queue(items: list[CykleItem]) -> None:
    payload = {
        "items": [asdict(it) for it in items],
        "saved_at": _now_iso(),
    }
    atomic_write_text(
        _queue_file(for_write=True),
        json.dumps(payload, indent=2, ensure_ascii=False),
    )


def get_item(item_id: str) -> CykleItem | None:
    for it in load_queue():
        if it.id == item_id:
            return it
    return None


def update_item(item_id: str, **changes: Any) -> CykleItem | None:
    items = load_queue()
    for i, it in enumerate(items):
        if it.id == item_id:
            for k, v in changes.items():
                if hasattr(it, k):
                    setattr(it, k, v)
            it.updated_at = _now_iso()
            items[i] = it
            save_queue(items)
            return it
    return None


def remove_item(item_id: str) -> bool:
    items = load_queue()
    filtered = [it for it in items if it.id != item_id]
    if len(filtered) == len(items):
        return False
    save_queue(filtered)
    return True


def load_generation_state() -> dict[str, Any]:
    path = _generation_state_file()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_generation_state(state: dict[str, Any]) -> None:
    payload = dict(state)
    payload["updated_at"] = _now_iso()
    atomic_write_text(
        _generation_state_file(for_write=True),
        json.dumps(payload, indent=2, ensure_ascii=False),
    )


def append_meta_log(entry: dict[str, Any]) -> None:
    path = _meta_state_file()
    log: list[dict[str, Any]] = []
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                log = list(raw.get("log") or [])
        except (OSError, json.JSONDecodeError):
            log = []
    item = dict(entry)
    item.setdefault("ts", _now_iso())
    log.append(item)
    log = log[-500:]
    atomic_write_text(
        _meta_state_file(for_write=True),
        json.dumps({"log": log}, indent=2, ensure_ascii=False),
    )


def load_meta_log(limit: int = 50) -> list[dict[str, Any]]:
    path = _meta_state_file()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    log = list(raw.get("log") or []) if isinstance(raw, dict) else []
    return log[-limit:]


DEFAULT_CONFIG: dict[str, Any] = {
    "slot_times": dict(_cp.DEFAULT_SLOT_TIMES),
    "active_channels": list(_cp.CHANNEL_ORDER),
    "auto_publish": False,
    "start_date": "",
    "timezone": "Europe/Warsaw",
    "hashtags_extra_pl": [],
    "hashtags_extra_en": [],
}


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    path = _config_file()
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg.update(raw)
        except (OSError, json.JSONDecodeError):
            pass
    slot_times = dict(_cp.DEFAULT_SLOT_TIMES)
    slot_times.update(cfg.get("slot_times") or {})
    cfg["slot_times"] = slot_times
    if not cfg.get("active_channels"):
        cfg["active_channels"] = list(_cp.CHANNEL_ORDER)
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    atomic_write_text(
        _config_file(for_write=True),
        json.dumps(cfg, indent=2, ensure_ascii=False),
    )


def load_meta_credentials() -> dict[str, dict[str, str]]:
    path = _credentials_file()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for code in _cp.CHANNEL_ORDER:
        entry = raw.get(code) or {}
        if isinstance(entry, dict):
            out[code] = {k: str(v) for k, v in entry.items() if v is not None}
    return out


def save_meta_credentials(creds: dict[str, dict[str, str]]) -> None:
    merged: dict[str, Any] = {}
    path = _credentials_file()
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                merged = dict(raw)
        except (OSError, json.JSONDecodeError):
            merged = {}
    for code, entry in creds.items():
        if isinstance(entry, dict):
            merged[code] = {k: str(v) for k, v in entry.items() if v is not None}
    atomic_write_text(
        _credentials_file(for_write=True),
        json.dumps(merged, indent=2, ensure_ascii=False),
    )
