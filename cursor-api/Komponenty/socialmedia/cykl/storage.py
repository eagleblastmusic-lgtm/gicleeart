"""Persystencja komponentu cykl.

Pliki w `Komponenty/socialmedia/data/cykl/`:
- queue.json              - aktualna kolejka postow (lista CykleItem)
- generation_state.json   - stan generacji (do kiedy jest tresc + hashe dla delta detection)
- meta_state.json         - log publikacji Meta (per item per kanal)
- config.json             - ustawienia (godziny slotow, data startu, aktywne kanaly)
- meta_credentials.json   - tokeny Meta API (gitignore!)

CykleItem - pojedyncza pozycja w kolejce:
- identyfikacja (artysta + tytul),
- flagi kontekstu (pierwsza/ostatnia u artysty, nowy artysta/obraz),
- harmonogram (scheduled_at, slot),
- tresc per jezyk i per kanal (mozliwe nadpisania z edycji),
- obrazy (lokalne + upload'owane CDN URL),
- statusy publikacji per kanal.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from . import platforms_cykl as _cp

_COMPONENT_DIR = Path(__file__).resolve().parents[1]  # Komponenty/socialmedia
_DATA_DIR = _COMPONENT_DIR / "data" / "cykl"
_QUEUE_FILE = _DATA_DIR / "queue.json"
_GEN_STATE_FILE = _DATA_DIR / "generation_state.json"
_META_STATE_FILE = _DATA_DIR / "meta_state.json"
_CONFIG_FILE = _DATA_DIR / "config.json"
_CREDS_FILE = _DATA_DIR / "meta_credentials.json"
IMAGES_DIR = _DATA_DIR / "Obrazy"


def _ensure_dirs() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Model: CykleItem
# ---------------------------------------------------------------------------

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

    # Pozycja w kolekce artysty
    artist_position: int = 0
    artist_total: int = 0
    is_first_of_artist: bool = False
    is_last_of_artist: bool = False
    is_new_artist: bool = False
    is_new_painting: bool = False
    next_artist: str = ""

    # Harmonogram
    scheduled_at: str = ""   # ISO "YYYY-MM-DDTHH:MM:SS" (lokalny)
    slot: str = ""           # "morning" | "afternoon" | "evening"

    # Tresc - baza (z Opusa) + nadpisania per kanal
    caption_pl: str = ""
    caption_en: str = ""
    caption_fb_pl: str = ""
    caption_fb_en: str = ""
    caption_ig_pl: str = ""
    caption_ig_en: str = ""
    hashtags_pl: list[str] = field(default_factory=list)
    hashtags_en: list[str] = field(default_factory=list)
    zoom_hints: list[str] = field(default_factory=list)

    # Obrazy (sciezki wzgledne do data/cykl/Obrazy/)
    # Domyslny "master" zestaw wykryty z folderu (do wsadowego zerowania cdn_cache).
    image_main: str = ""
    image_zooms: list[str] = field(default_factory=list)
    image_mockup: str = ""

    # AKTUALNE zestawy per-platforma (ta sama zawartosc dla obu jezykow):
    # - FB: main + zoomy + mockup -> FB multi-photo feed post (attached_media).
    # - IG: main + zoomy + mockup -> IG carousel.
    # Zapisywane osobno zeby user mogl miec rozne zdjecia na FB i IG.
    image_fb_main: str = ""
    image_fb_zooms: list[str] = field(default_factory=list)
    image_fb_mockup: str = ""
    image_ig_main: str = ""
    image_ig_zooms: list[str] = field(default_factory=list)
    image_ig_mockup: str = ""

    # (Legacy - zostawione dla wstecznej kompatybilnosci z queue.json bez nowych pol)
    image_fb_pl: str = ""
    image_fb_en: str = ""
    image_ig_pl: list[str] = field(default_factory=list)
    image_ig_en: list[str] = field(default_factory=list)

    # CDN URL-e po uplodzie do Shopify Files (cache, zeby nie re-uplodowac)
    # Oddzielnie FB i IG zeby zmiana jednego nie invaldowala drugiego.
    cdn_main: str = ""                                            # legacy
    cdn_zooms: list[str] = field(default_factory=list)            # legacy
    cdn_mockup: str = ""                                          # legacy
    cdn_fb_main: str = ""
    cdn_fb_zooms: list[str] = field(default_factory=list)
    cdn_fb_mockup: str = ""
    cdn_ig_main: str = ""
    cdn_ig_zooms: list[str] = field(default_factory=list)
    cdn_ig_mockup: str = ""

    # Status publikacji per kanal: "" | "done@<iso>" | "error: <msg>"
    published_fb_pl: str = ""
    published_fb_en: str = ""
    published_ig_pl: str = ""
    published_ig_en: str = ""
    media_ids: dict[str, str] = field(default_factory=dict)  # {channel: page_<id>_<id>}

    # Kanaly aktywne (domyslnie wszystkie; user moze wylaczyc per item)
    channels_enabled: list[str] = field(default_factory=lambda: list(_cp.CHANNEL_ORDER))

    status: str = "pending"     # pending | ready | publishing | done | skipped | error
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
    # Tolerancyjny konstruktor - ignoruje nieznane pola, dopelnia defaults
    allowed = {f.name for f in CykleItem.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    cleaned = {k: v for k, v in d.items() if k in allowed}
    if not cleaned.get("id"):
        cleaned["id"] = uuid.uuid4().hex[:12]
    if not cleaned.get("created_at"):
        cleaned["created_at"] = _now_iso()
    if not cleaned.get("updated_at"):
        cleaned["updated_at"] = _now_iso()
    # Dopelnij listy/dict jesli przyszly jako None
    for list_key in ("hashtags_pl", "hashtags_en", "zoom_hints",
                     "image_zooms", "image_ig_pl", "image_ig_en",
                     "image_fb_zooms", "image_ig_zooms",
                     "cdn_zooms", "cdn_fb_zooms", "cdn_ig_zooms",
                     "channels_enabled"):
        if cleaned.get(list_key) is None:
            cleaned[list_key] = []
    if cleaned.get("media_ids") is None:
        cleaned["media_ids"] = {}
    if not cleaned.get("channels_enabled"):
        cleaned["channels_enabled"] = list(_cp.CHANNEL_ORDER)
    return CykleItem(**cleaned)


# ---------------------------------------------------------------------------
# Queue - CRUD
# ---------------------------------------------------------------------------

def load_queue() -> list[CykleItem]:
    _ensure_dirs()
    if not _QUEUE_FILE.is_file():
        return []
    try:
        data = json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("items", []) if isinstance(data, dict) else []
    return [_item_from_dict(x) for x in raw if isinstance(x, dict)]


def save_queue(items: list[CykleItem]) -> None:
    _ensure_dirs()
    payload = {
        "items": [asdict(it) for it in items],
        "saved_at": _now_iso(),
    }
    _QUEUE_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
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


# ---------------------------------------------------------------------------
# Generation state
# ---------------------------------------------------------------------------

def load_generation_state() -> dict[str, Any]:
    _ensure_dirs()
    if not _GEN_STATE_FILE.is_file():
        return {}
    try:
        return json.loads(_GEN_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_generation_state(state: dict[str, Any]) -> None:
    _ensure_dirs()
    state = dict(state)
    state["updated_at"] = _now_iso()
    _GEN_STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Meta state (log publikacji)
# ---------------------------------------------------------------------------

def append_meta_log(entry: dict[str, Any]) -> None:
    _ensure_dirs()
    log: list[dict[str, Any]] = []
    if _META_STATE_FILE.is_file():
        try:
            raw = json.loads(_META_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                log = list(raw.get("log") or [])
        except (OSError, json.JSONDecodeError):
            log = []
    entry = dict(entry)
    entry.setdefault("ts", _now_iso())
    log.append(entry)
    # Trzymamy ostatnie 500 wpisow - nie rosniemy w nieskonczonosc
    log = log[-500:]
    _META_STATE_FILE.write_text(
        json.dumps({"log": log}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_meta_log(limit: int = 50) -> list[dict[str, Any]]:
    _ensure_dirs()
    if not _META_STATE_FILE.is_file():
        return []
    try:
        raw = json.loads(_META_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    log = list(raw.get("log") or []) if isinstance(raw, dict) else []
    return log[-limit:]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "slot_times": dict(_cp.DEFAULT_SLOT_TIMES),
    "active_channels": list(_cp.CHANNEL_ORDER),
    "auto_publish": False,     # gdy True -> publisher daemon w launcherze bedzie wysylac
    "start_date": "",          # "YYYY-MM-DD"; puste = jutro
    "timezone": "Europe/Warsaw",
    "hashtags_extra_pl": [],   # dodatkowe (poza locked) - uzywane w promptach
    "hashtags_extra_en": [],
}


def load_config() -> dict[str, Any]:
    _ensure_dirs()
    cfg = dict(DEFAULT_CONFIG)
    if _CONFIG_FILE.is_file():
        try:
            raw = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg.update(raw)
        except (OSError, json.JSONDecodeError):
            pass
    # Uzupelnij brakujace sloty
    slot_times = dict(_cp.DEFAULT_SLOT_TIMES)
    slot_times.update(cfg.get("slot_times") or {})
    cfg["slot_times"] = slot_times
    if not cfg.get("active_channels"):
        cfg["active_channels"] = list(_cp.CHANNEL_ORDER)
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    _ensure_dirs()
    _CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Meta credentials (tokeny API - gitignore!)
# ---------------------------------------------------------------------------

def load_meta_credentials() -> dict[str, dict[str, str]]:
    """Zwraca dict: {channel_code: {page_id, access_token, ig_user_id (opcjonalnie)}}.

    Dla FB: page_id + access_token (Page Access Token long-lived).
    Dla IG: ig_user_id (Instagram Business Account ID) + access_token
            (zwykle ten sam Page Access Token powiazanej strony FB).
    """
    _ensure_dirs()
    if not _CREDS_FILE.is_file():
        return {}
    try:
        raw = json.loads(_CREDS_FILE.read_text(encoding="utf-8"))
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
    _ensure_dirs()
    merged: dict[str, Any] = {}
    if _CREDS_FILE.is_file():
        try:
            raw = json.loads(_CREDS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                merged = dict(raw)
        except (OSError, json.JSONDecodeError):
            merged = {}
    for code, entry in creds.items():
        if isinstance(entry, dict):
            merged[code] = {k: str(v) for k, v in entry.items() if v is not None}
    _CREDS_FILE.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Paths - public (dla innych modulow)
# ---------------------------------------------------------------------------

def data_dir() -> Path:
    _ensure_dirs()
    return _DATA_DIR


def images_dir() -> Path:
    _ensure_dirs()
    return IMAGES_DIR
