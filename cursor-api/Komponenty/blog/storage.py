"""Persystencja danych komponentu Blog.

Odczyt preferuje lokalizacje AppData utworzone przez Stage 1E. Stare pliki w
`Komponenty/blog/data/` pozostają tymczasowym fallbackiem tylko do odczytu.
Każdy nowy zapis trafia wyłącznie poza repozytorium.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text, cache_path, data_path

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "data"
_TOPICS = data_path(
    "Komponenty/blog/data/topics.json",
    legacy=_LEGACY_DATA_DIR / "topics.json",
)
_ARTICLES_CACHE = cache_path(
    "Komponenty/blog/data/articles_cache.json",
    legacy=_LEGACY_DATA_DIR / "articles_cache.json",
)


@dataclass
class TopicProposal:
    id: str
    title: str
    reason: str = ""
    keywords: list[str] = field(default_factory=list)
    created_at: str = ""
    used: bool = False

    @staticmethod
    def new(title: str, reason: str = "", keywords: list[str] | None = None) -> "TopicProposal":
        return TopicProposal(
            id=uuid.uuid4().hex[:12],
            title=title.strip(),
            reason=(reason or "").strip(),
            keywords=[(k or "").strip() for k in (keywords or []) if (k or "").strip()],
            created_at=datetime.utcnow().isoformat(timespec="seconds"),
            used=False,
        )


# ---------------------------------------------------------------------------
# Topics (propozycje)
# ---------------------------------------------------------------------------


def load_topics() -> list[TopicProposal]:
    path = _TOPICS.read_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("topics", []) if isinstance(data, dict) else []
    out: list[TopicProposal] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            TopicProposal(
                id=str(item.get("id") or uuid.uuid4().hex[:12]),
                title=str(item.get("title") or "").strip(),
                reason=str(item.get("reason") or "").strip(),
                keywords=[str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()],
                created_at=str(item.get("created_at") or ""),
                used=bool(item.get("used", False)),
            )
        )
    return [t for t in out if t.title]


def save_topics(topics: list[TopicProposal]) -> None:
    payload = {"topics": [asdict(t) for t in topics]}
    atomic_write_text(
        _TOPICS.write_path,
        json.dumps(payload, indent=2, ensure_ascii=False),
    )


def add_topics(new_items: list[TopicProposal]) -> int:
    """Dodaje tematy, pomijajac duplikaty po znormalizowanym tytule. Zwraca ile dodano."""

    existing = load_topics()
    seen = {t.title.strip().lower() for t in existing}
    added = 0
    for item in new_items:
        key = item.title.strip().lower()
        if not key or key in seen:
            continue
        existing.append(item)
        seen.add(key)
        added += 1
    if added:
        save_topics(existing)
    return added


def remove_topic(topic_id: str) -> bool:
    topics = load_topics()
    filtered = [t for t in topics if t.id != topic_id]
    if len(filtered) == len(topics):
        return False
    save_topics(filtered)
    return True


def mark_topic_used(topic_id: str, used: bool = True) -> bool:
    topics = load_topics()
    changed = False
    for topic in topics:
        if topic.id == topic_id:
            topic.used = used
            changed = True
            break
    if changed:
        save_topics(topics)
    return changed


# ---------------------------------------------------------------------------
# Articles cache (snapshot obecnych postow)
# ---------------------------------------------------------------------------


def load_articles_cache() -> dict[str, Any]:
    path = _ARTICLES_CACHE.read_path()
    if not path.is_file():
        return {"fetched_at": 0, "articles": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"fetched_at": 0, "articles": []}
        return data
    except (OSError, json.JSONDecodeError):
        return {"fetched_at": 0, "articles": []}


def save_articles_cache(articles: list[dict[str, Any]]) -> None:
    payload = {"fetched_at": int(time.time()), "articles": articles}
    atomic_write_text(
        _ARTICLES_CACHE.write_path,
        json.dumps(payload, indent=2, ensure_ascii=False),
    )
