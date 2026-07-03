"""Trwaly zapis linkow do stron z opisem dzialan."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DATA_DIR = Path(__file__).resolve().parent / "data"
PAGES_FILE = DATA_DIR / "pages.json"

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Sklep",
    "Shopify Admin",
    "GicleeApp",
    "Narzedzia",
    "Inne",
)


@dataclass
class PageEntry:
    id: str
    title: str
    url: str
    description: str = ""
    category: str = "Inne"
    sort_key: int = 0

    @property
    def ok(self) -> bool:
        return bool((self.url or "").strip())


@dataclass
class PageStore:
    pages: list[PageEntry] = field(default_factory=list)
    categories: list[str] = field(default_factory=lambda: list(DEFAULT_CATEGORIES))

    def sorted(self) -> list[PageEntry]:
        return sorted(
            self.pages,
            key=lambda p: (p.category.lower(), p.sort_key, p.title.lower()),
        )

    def by_id(self, page_id: str) -> PageEntry | None:
        for page in self.pages:
            if page.id == page_id:
                return page
        return None


def new_page_id() -> str:
    return uuid.uuid4().hex[:12]


def next_sort_key(store: PageStore, *, category: str = "") -> int:
    same = [p.sort_key for p in store.pages if not category or p.category == category]
    return (max(same) + 1) if same else 0


def normalize_url(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        return ""
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url.lstrip("/")
    return url


def title_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().removeprefix("www.")
    path = (parsed.path or "").strip("/")
    if path and path not in ("", "index.html"):
        tail = path.split("/")[-1].replace("-", " ").replace("_", " ")
        if host:
            return f"{host} — {tail}"[:120]
    return host or url[:120]


def parse_link_line(line: str) -> tuple[str, str] | None:
    """Jedna linia: URL albo «Tytul | URL» / «Tytul — URL»."""
    raw = (line or "").strip()
    if not raw or raw.startswith("#"):
        return None
    for sep in (" | ", " — ", " - ", "\t"):
        if sep in raw:
            left, right = raw.split(sep, 1)
            title = left.strip()
            url = normalize_url(right)
            if url:
                return (title or title_from_url(url), url)
    url = normalize_url(raw)
    if not url:
        return None
    return (title_from_url(url), url)


def parse_bulk_links(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        parsed = parse_link_line(line)
        if not parsed:
            continue
        title, url = parsed
        key = url.lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append((title, url))
    return out


def _page_to_dict(page: PageEntry) -> dict[str, Any]:
    return {
        "id": page.id,
        "title": page.title,
        "url": page.url,
        "description": page.description,
        "category": page.category,
        "sort_key": page.sort_key,
    }


def _page_from_dict(row: dict[str, Any]) -> PageEntry | None:
    url = normalize_url(str(row.get("url") or ""))
    if not url:
        return None
    title = str(row.get("title") or "").strip() or title_from_url(url)
    category = str(row.get("category") or "Inne").strip() or "Inne"
    return PageEntry(
        id=str(row.get("id") or new_page_id()),
        title=title,
        url=url,
        description=str(row.get("description") or ""),
        category=category,
        sort_key=int(row.get("sort_key") or 0),
    )


def load_pages() -> PageStore:
    if not PAGES_FILE.is_file():
        return PageStore()
    try:
        data = json.loads(PAGES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return PageStore()
    raw_pages = data.get("pages") if isinstance(data, dict) else None
    raw_categories = data.get("categories") if isinstance(data, dict) else None
    pages: list[PageEntry] = []
    if isinstance(raw_pages, list):
        for row in raw_pages:
            if isinstance(row, dict):
                page = _page_from_dict(row)
                if page:
                    pages.append(page)
    categories = list(DEFAULT_CATEGORIES)
    if isinstance(raw_categories, list):
        for item in raw_categories:
            name = str(item or "").strip()
            if name and name not in categories:
                categories.append(name)
    for page in pages:
        if page.category and page.category not in categories:
            categories.append(page.category)
    return PageStore(pages=pages, categories=categories)


def save_pages(store: PageStore) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "categories": list(store.categories),
        "pages": [_page_to_dict(p) for p in store.sorted()],
    }
    PAGES_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
