"""Persystencja zadan marketingowych.

Pliki w `Komponenty/zadania/data/`:
- tasks.json           - lista zadan (wszystkie statusy).
- signals_cache.json   - snapshot ostatnio pobranych sygnalow z Shopify.
- reminders.json       - ostatnie pokazane przypomnienia (np. miesieczny plan).

Format zadania (wersja 2 - multi-channel / multi-market):
    {
      "id": "uuid12",
      "title": "Post IG + FB o nowym Monecie",
      "description": "Szczegoly po polsku",
      "description_translations": {          # <- NOWE: tlumaczenia opisu na rynki zagr.
        "en": "Details in English",
        "de": "Details auf Deutsch"
      },
      "channels": ["ig_feed", "fb"],         # <- NOWE: lista kanalow (bylo 'channel')
      "languages": ["pl", "en"],             # <- NOWE: lista jezykow (bylo 'language')
      "target_markets": ["pl", "eu", "de"],  # <- NOWE: rynki Shopify (7-elementowy zestaw)
      "due_date": "2026-05-05",
      "priority": "low" | "normal" | "high" | "urgent",
      "source": "shopify" | "holiday" | "llm" | "manual" | "evergreen",
      "source_ref": "np. 'Hans Dahl - Babie lato'",
      "suggested_topic": "temat do wklejenia w Generator tresci",
      "status": "pending" | "in_progress" | "done" | "skipped",
      "notes": "",
      "linked_post_ids": [],
      "created_at": "...",
      "updated_at": "..."
    }

BACKCOMPAT: `_from_dict` obsluguje stary format (`channel`, `language` jako string) -
konwertuje automatycznie do list. Sam save zawsze pisze nowy format.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

_COMPONENT_DIR = Path(__file__).resolve().parent
_DATA_DIR = _COMPONENT_DIR / "data"
_TASKS_FILE = _DATA_DIR / "tasks.json"
_SIGNALS_FILE = _DATA_DIR / "signals_cache.json"
_REMINDERS_FILE = _DATA_DIR / "reminders.json"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


VALID_CHANNELS = {
    "ig_feed", "ig_stories", "ig_reels", "fb", "tiktok", "pinterest",
    "blog", "newsletter", "other",
}
VALID_STATUSES = {"pending", "in_progress", "done", "skipped"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
VALID_SOURCES = {"shopify", "holiday", "llm", "manual", "evergreen"}
VALID_LANGUAGES = {"pl", "en", "de", "fr", "es", "nl", "it", "both"}
VALID_MARKETS = {"pl", "eu", "fr", "de", "es", "nl", "it"}

# Polskie etykiety UI
PRIORITY_LABELS_PL = {
    "urgent": "Pilne",
    "high": "Wysoki",
    "normal": "Zwykly",
    "low": "Niski",
}

STATUS_LABELS_PL = {
    "pending": "Oczekuje",
    "in_progress": "W toku",
    "done": "Zrobione",
    "skipped": "Pominiete",
}

CHANNEL_LABELS_PL = {
    "ig_feed": "IG Feed",
    "ig_stories": "IG Stories",
    "ig_reels": "IG Reels",
    "fb": "Facebook",
    "tiktok": "TikTok",
    "pinterest": "Pinterest",
    "blog": "Blog",
    "newsletter": "Newsletter",
    "other": "Inne",
}

MARKET_LABELS_PL = {
    "pl": "PL",
    "eu": "EU",
    "fr": "FR",
    "de": "DE",
    "es": "ES",
    "nl": "NL",
    "it": "IT",
}


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    description_translations: dict[str, str] = field(default_factory=dict)
    channels: list[str] = field(default_factory=lambda: ["other"])
    languages: list[str] = field(default_factory=lambda: ["pl"])
    target_markets: list[str] = field(default_factory=list)
    due_date: str = ""
    priority: str = "normal"
    source: str = "manual"
    source_ref: str = ""
    suggested_topic: str = ""
    status: str = "pending"
    notes: str = ""
    linked_post_ids: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    # ---- helpers dla UI (wsteczna wygoda) ----
    @property
    def channel(self) -> str:
        """Pierwszy kanal (dla kodu ktory nie ogarnia list)."""
        return self.channels[0] if self.channels else "other"

    @property
    def language(self) -> str:
        return self.languages[0] if self.languages else "pl"

    @staticmethod
    def new(
        *,
        title: str,
        description: str = "",
        description_translations: dict[str, str] | None = None,
        channels: list[str] | None = None,
        languages: list[str] | None = None,
        target_markets: list[str] | None = None,
        # backcompat: zezwalamy podac channel/language jako string
        channel: str | None = None,
        language: str | None = None,
        due_date: str = "",
        priority: str = "normal",
        source: str = "manual",
        source_ref: str = "",
        suggested_topic: str = "",
        notes: str = "",
    ) -> "Task":
        now = _now_iso()
        ch = _normalize_channels(channels, channel)
        lg = _normalize_languages(languages, language)
        mk = _normalize_markets(target_markets)
        tr = _normalize_translations(description_translations or {})
        return Task(
            id=uuid.uuid4().hex[:12],
            title=title.strip(),
            description=(description or "").strip(),
            description_translations=tr,
            channels=ch,
            languages=lg,
            target_markets=mk,
            due_date=(due_date or "").strip(),
            priority=priority if priority in VALID_PRIORITIES else "normal",
            source=source if source in VALID_SOURCES else "manual",
            source_ref=(source_ref or "").strip(),
            suggested_topic=(suggested_topic or "").strip(),
            status="pending",
            notes=(notes or "").strip(),
            linked_post_ids=[],
            created_at=now,
            updated_at=now,
        )


def _normalize_channels(channels: list[str] | None, legacy: str | None) -> list[str]:
    if channels:
        out = [c for c in channels if c in VALID_CHANNELS]
        return out or ["other"]
    if legacy and legacy in VALID_CHANNELS:
        return [legacy]
    return ["other"]


def _normalize_languages(languages: list[str] | None, legacy: str | None) -> list[str]:
    if languages:
        out = [l for l in languages if l in VALID_LANGUAGES]
        return out or ["pl"]
    if legacy:
        if legacy == "both":
            return ["pl", "en"]
        if legacy in VALID_LANGUAGES:
            return [legacy]
    return ["pl"]


def _normalize_markets(markets: list[str] | None) -> list[str]:
    if not markets:
        return []
    return [m for m in markets if m in VALID_MARKETS]


def _normalize_translations(tr: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in (tr or {}).items():
        k_str = str(k or "").strip().lower()
        v_str = str(v or "").strip()
        if k_str in VALID_LANGUAGES and k_str not in ("pl", "both") and v_str:
            out[k_str] = v_str
    return out


def _from_dict(d: dict[str, Any]) -> Task:
    """Parsuje task z JSON z obsluga starego formatu (single channel/language)."""
    # backcompat: stary channel (str) lub nowy channels (list)
    channels_raw = d.get("channels") or []
    if not isinstance(channels_raw, list) or not channels_raw:
        legacy = str(d.get("channel") or "other")
        channels = _normalize_channels(None, legacy)
    else:
        channels = _normalize_channels([str(c) for c in channels_raw], None)

    languages_raw = d.get("languages") or []
    if not isinstance(languages_raw, list) or not languages_raw:
        legacy_lang = str(d.get("language") or "pl")
        languages = _normalize_languages(None, legacy_lang)
    else:
        languages = _normalize_languages([str(l) for l in languages_raw], None)

    markets_raw = d.get("target_markets") or []
    markets = _normalize_markets([str(m) for m in markets_raw]) if isinstance(markets_raw, list) else []

    translations_raw = d.get("description_translations") or {}
    translations = _normalize_translations(translations_raw) if isinstance(translations_raw, dict) else {}

    return Task(
        id=str(d.get("id") or uuid.uuid4().hex[:12]),
        title=str(d.get("title") or "").strip(),
        description=str(d.get("description") or ""),
        description_translations=translations,
        channels=channels,
        languages=languages,
        target_markets=markets,
        due_date=str(d.get("due_date") or ""),
        priority=str(d.get("priority") or "normal"),
        source=str(d.get("source") or "manual"),
        source_ref=str(d.get("source_ref") or ""),
        suggested_topic=str(d.get("suggested_topic") or ""),
        status=str(d.get("status") or "pending"),
        notes=str(d.get("notes") or ""),
        linked_post_ids=[str(x) for x in (d.get("linked_post_ids") or [])],
        created_at=str(d.get("created_at") or _now_iso()),
        updated_at=str(d.get("updated_at") or _now_iso()),
    )


# ---------------------------------------------------------------------------
# Tasks CRUD
# ---------------------------------------------------------------------------

def load_tasks() -> list[Task]:
    _ensure_dir()
    if not _TASKS_FILE.is_file():
        return []
    try:
        data = json.loads(_TASKS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("tasks", []) if isinstance(data, dict) else []
    return [_from_dict(x) for x in raw if isinstance(x, dict)]


def save_tasks(tasks: list[Task]) -> None:
    _ensure_dir()
    payload = {"tasks": [asdict(t) for t in tasks]}
    _TASKS_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_tasks(new_items: list[Task], *, dedup_key: str = "title+due") -> int:
    """Dodaje zadania pomijajac duplikaty.

    dedup_key:
    - 'title+due' (default): unikalnosc po (title, due_date).
    - 'title': tylko po tytule.
    - 'none': dodaj wszystko bez deduplikacji.
    """
    existing = load_tasks()

    def _key(t: Task) -> tuple[str, str]:
        title = t.title.strip().lower()
        if dedup_key == "title+due":
            return (title, t.due_date or "")
        if dedup_key == "title":
            return (title, "")
        return ("", "")

    seen: set[tuple[str, str]] = set()
    if dedup_key != "none":
        for t in existing:
            seen.add(_key(t))

    added = 0
    for item in new_items:
        k = _key(item)
        if dedup_key != "none" and (k in seen or not item.title):
            continue
        existing.append(item)
        seen.add(k)
        added += 1
    if added:
        save_tasks(existing)
    return added


def update_task(task_id: str, **changes: Any) -> Task | None:
    tasks = load_tasks()
    for i, t in enumerate(tasks):
        if t.id == task_id:
            for k, v in changes.items():
                if hasattr(t, k):
                    setattr(t, k, v)
            t.updated_at = _now_iso()
            tasks[i] = t
            save_tasks(tasks)
            return t
    return None


def set_status(task_id: str, status: str) -> Task | None:
    if status not in VALID_STATUSES:
        return None
    return update_task(task_id, status=status)


def link_post(task_id: str, post_id: str) -> Task | None:
    t = get_task(task_id)
    if t is None:
        return None
    if post_id not in t.linked_post_ids:
        t.linked_post_ids.append(post_id)
    new_status = t.status if t.status != "pending" else "in_progress"
    return update_task(task_id, linked_post_ids=t.linked_post_ids, status=new_status)


def get_task(task_id: str) -> Task | None:
    for t in load_tasks():
        if t.id == task_id:
            return t
    return None


def remove_task(task_id: str) -> bool:
    tasks = load_tasks()
    filtered = [t for t in tasks if t.id != task_id]
    if len(filtered) == len(tasks):
        return False
    save_tasks(filtered)
    return True


# ---------------------------------------------------------------------------
# Signals cache
# ---------------------------------------------------------------------------

def load_signals_cache() -> dict[str, Any]:
    _ensure_dir()
    if not _SIGNALS_FILE.is_file():
        return {"fetched_at": 0, "signals": {}}
    try:
        data = json.loads(_SIGNALS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"fetched_at": 0, "signals": {}}
        return data
    except (OSError, json.JSONDecodeError):
        return {"fetched_at": 0, "signals": {}}


def save_signals_cache(signals: dict[str, Any]) -> None:
    _ensure_dir()
    payload = {"fetched_at": int(time.time()), "signals": signals}
    _SIGNALS_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Reminders (np. miesieczny plan)
# ---------------------------------------------------------------------------

def load_reminders() -> dict[str, Any]:
    _ensure_dir()
    if not _REMINDERS_FILE.is_file():
        return {}
    try:
        data = json.loads(_REMINDERS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_reminders(data: dict[str, Any]) -> None:
    _ensure_dir()
    _REMINDERS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def mark_reminder_shown(key: str, value: str) -> None:
    """Zapisuje ze reminder `key` zostal pokazany z wartoscia `value` (np. '2026-04')."""
    data = load_reminders()
    data[key] = value
    save_reminders(data)
