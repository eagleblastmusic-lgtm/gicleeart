"""Trwaly zapis zakladek do stron z obrazami."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DATA_DIR = Path(__file__).resolve().parent / "data"
SITES_FILE = DATA_DIR / "sites.json"

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Muzeum",
    "Galeria",
    "Katalog",
    "Aukcja",
    "Inne",
)


@dataclass
class SiteEntry:
    id: str
    title: str
    url: str
    category: str = "Inne"
    notes: str = ""
    sort_key: int = 0

    @property
    def ok(self) -> bool:
        return bool((self.url or "").strip())


@dataclass
class SiteStore:
    sites: list[SiteEntry] = field(default_factory=list)
    categories: list[str] = field(default_factory=lambda: list(DEFAULT_CATEGORIES))

    def sorted(self) -> list[SiteEntry]:
        return sorted(self.sites, key=lambda s: (s.category.lower(), s.sort_key, s.title.lower()))

    def by_id(self, site_id: str) -> SiteEntry | None:
        for site in self.sites:
            if site.id == site_id:
                return site
        return None


def new_site_id() -> str:
    return uuid.uuid4().hex[:12]


def next_sort_key(store: SiteStore, *, category: str = "") -> int:
    same = [s.sort_key for s in store.sites if not category or s.category == category]
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


def _site_to_dict(site: SiteEntry) -> dict[str, Any]:
    return {
        "id": site.id,
        "title": site.title,
        "url": site.url,
        "category": site.category,
        "notes": site.notes,
        "sort_key": site.sort_key,
    }


def _site_from_dict(row: dict[str, Any]) -> SiteEntry | None:
    url = normalize_url(str(row.get("url") or ""))
    if not url:
        return None
    title = str(row.get("title") or "").strip() or title_from_url(url)
    category = str(row.get("category") or "Inne").strip() or "Inne"
    return SiteEntry(
        id=str(row.get("id") or new_site_id()),
        title=title,
        url=url,
        category=category,
        notes=str(row.get("notes") or ""),
        sort_key=int(row.get("sort_key") or 0),
    )


def load_sites() -> SiteStore:
    if not SITES_FILE.is_file():
        return SiteStore()
    try:
        data = json.loads(SITES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return SiteStore()
    raw_sites = data.get("sites") if isinstance(data, dict) else None
    raw_categories = data.get("categories") if isinstance(data, dict) else None
    sites: list[SiteEntry] = []
    if isinstance(raw_sites, list):
        for row in raw_sites:
            if isinstance(row, dict):
                site = _site_from_dict(row)
                if site:
                    sites.append(site)
    categories = list(DEFAULT_CATEGORIES)
    if isinstance(raw_categories, list):
        for item in raw_categories:
            name = str(item or "").strip()
            if name and name not in categories:
                categories.append(name)
    for site in sites:
        if site.category and site.category not in categories:
            categories.append(site.category)
    return SiteStore(sites=sites, categories=categories)


def save_sites(store: SiteStore) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "categories": list(store.categories),
        "sites": [_site_to_dict(s) for s in store.sorted()],
    }
    SITES_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
