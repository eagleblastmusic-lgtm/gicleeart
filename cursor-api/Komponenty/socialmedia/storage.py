"""Persystencja postow social media - kolejka planera.

Pliki w `Komponenty/socialmedia/data/`:
- posts.json   - wszystkie zaplanowane/gotowe/opublikowane posty.

Format pojedynczego posta:
    {
      "id": "uuid12",
      "platform": "ig_feed" | "ig_stories" | ... (kod z platforms.PLATFORMS),
      "language": "pl" | "en",
      "topic": "krotki temat (input uzytkownika, opcjonalnie)",
      "title": "tytul (Pinterest) / opcjonalne dla reszty",
      "caption": "glowny tekst posta",
      "on_screen_text": ["napis 1", "napis 2"],   # tylko dla Reels/TikTok
      "hashtags": ["#gicleeart", "#foo"],
      "image_hint": "sugestia co ma byc na zdjeciu",
      "image_path": "absolutna lokalna sciezka albo URL",
      "link": "URL docelowy (Pinterest, FB)",
      "music_hint": "sugestia dzwieku (Reels/TikTok)",
      "series_id": "",        # jesli post nalezy do serii - wspolny id
      "scheduled_at": "2026-04-22T10:00:00",  # ISO local, opcjonalnie
      "status": "pending" | "in_progress" | "done" | "skipped",
      "notes": "",
      "created_at": "...",
      "updated_at": "...",
      "from_task_id": "",    # jesli post powstal z zadania (komponent zadania)
    }
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

_COMPONENT_DIR = Path(__file__).resolve().parent
_DATA_DIR = _COMPONENT_DIR / "data"
_POSTS_FILE = _DATA_DIR / "posts.json"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Post:
    id: str
    platform: str
    language: str
    topic: str = ""
    title: str = ""
    caption: str = ""
    on_screen_text: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    image_hint: str = ""
    image_path: str = ""
    link: str = ""
    music_hint: str = ""
    series_id: str = ""
    scheduled_at: str = ""
    status: str = "pending"   # pending | in_progress | done | skipped
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    from_task_id: str = ""

    @staticmethod
    def new(
        *,
        platform: str,
        language: str,
        topic: str = "",
        title: str = "",
        caption: str = "",
        on_screen_text: list[str] | None = None,
        hashtags: list[str] | None = None,
        image_hint: str = "",
        image_path: str = "",
        link: str = "",
        music_hint: str = "",
        series_id: str = "",
        scheduled_at: str = "",
        notes: str = "",
        from_task_id: str = "",
    ) -> "Post":
        now = _now_iso()
        return Post(
            id=uuid.uuid4().hex[:12],
            platform=platform,
            language=language,
            topic=(topic or "").strip(),
            title=(title or "").strip(),
            caption=caption or "",
            on_screen_text=[s.strip() for s in (on_screen_text or []) if s.strip()],
            hashtags=[_normalize_hashtag(h) for h in (hashtags or []) if (h or "").strip()],
            image_hint=(image_hint or "").strip(),
            image_path=(image_path or "").strip(),
            link=(link or "").strip(),
            music_hint=(music_hint or "").strip(),
            series_id=(series_id or "").strip(),
            scheduled_at=(scheduled_at or "").strip(),
            status="pending",
            notes=(notes or "").strip(),
            created_at=now,
            updated_at=now,
            from_task_id=(from_task_id or "").strip(),
        )


def _normalize_hashtag(h: str) -> str:
    h = (h or "").strip()
    if not h:
        return h
    if not h.startswith("#"):
        h = "#" + h
    return h


def _post_from_dict(d: dict[str, Any]) -> Post:
    return Post(
        id=str(d.get("id") or uuid.uuid4().hex[:12]),
        platform=str(d.get("platform") or ""),
        language=str(d.get("language") or "pl"),
        topic=str(d.get("topic") or ""),
        title=str(d.get("title") or ""),
        caption=str(d.get("caption") or ""),
        on_screen_text=[str(s) for s in (d.get("on_screen_text") or []) if str(s).strip()],
        hashtags=[_normalize_hashtag(str(h)) for h in (d.get("hashtags") or []) if str(h).strip()],
        image_hint=str(d.get("image_hint") or ""),
        image_path=str(d.get("image_path") or ""),
        link=str(d.get("link") or ""),
        music_hint=str(d.get("music_hint") or ""),
        series_id=str(d.get("series_id") or ""),
        scheduled_at=str(d.get("scheduled_at") or ""),
        status=str(d.get("status") or "pending"),
        notes=str(d.get("notes") or ""),
        created_at=str(d.get("created_at") or _now_iso()),
        updated_at=str(d.get("updated_at") or _now_iso()),
        from_task_id=str(d.get("from_task_id") or ""),
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def load_posts() -> list[Post]:
    _ensure_dir()
    if not _POSTS_FILE.is_file():
        return []
    try:
        data = json.loads(_POSTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("posts", []) if isinstance(data, dict) else []
    return [_post_from_dict(x) for x in raw if isinstance(x, dict)]


def save_posts(posts: list[Post]) -> None:
    _ensure_dir()
    payload = {"posts": [asdict(p) for p in posts]}
    _POSTS_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_post(post: Post) -> Post:
    posts = load_posts()
    posts.append(post)
    save_posts(posts)
    return post


def update_post(post_id: str, **changes: Any) -> Post | None:
    posts = load_posts()
    for i, p in enumerate(posts):
        if p.id == post_id:
            for k, v in changes.items():
                if hasattr(p, k):
                    setattr(p, k, v)
            p.updated_at = _now_iso()
            posts[i] = p
            save_posts(posts)
            return p
    return None


def set_status(post_id: str, status: str) -> Post | None:
    if status not in ("pending", "in_progress", "done", "skipped"):
        return None
    return update_post(post_id, status=status)


def remove_post(post_id: str) -> bool:
    posts = load_posts()
    filtered = [p for p in posts if p.id != post_id]
    if len(filtered) == len(posts):
        return False
    save_posts(filtered)
    return True


def get_post(post_id: str) -> Post | None:
    for p in load_posts():
        if p.id == post_id:
            return p
    return None


def filter_posts(
    *,
    platform: str | None = None,
    language: str | None = None,
    status: str | None = None,
    series_id: str | None = None,
) -> list[Post]:
    out = load_posts()
    if platform:
        out = [p for p in out if p.platform == platform]
    if language:
        out = [p for p in out if p.language == language]
    if status:
        out = [p for p in out if p.status == status]
    if series_id:
        out = [p for p in out if p.series_id == series_id]
    return out
