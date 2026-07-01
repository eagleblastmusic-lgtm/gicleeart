"""Wyszukiwanie dziela po obrazie — reverse image + podobienstwo wizualne miniatur."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Callable

from ..storage import SiteEntry, load_sites
from .dedup import dedupe_hits
from .preview_urls import artwork_preview_url
from .registry import SourceDef, source_for_url, sources_for_sites
from .reverse_urls import ReverseLink, reverse_image_search, serpapi_key
from .thumbnails import fetch_thumbnail_bytes
from .types import ArtworkHit, SourceSearchResult
from .url_lookup import lookup_hit_from_url
from .visual_hash import dhash, similarity_score

CancelCheck = Callable[[], bool] | None
StatusCallback = Callable[[str], None] | None

_TITLE_SPLIT = re.compile(r"\s*[-–—|:]\s*|\s+by\s+", re.I)


@dataclass
class ImageSearchResult:
    image_path: str
    results: list[SourceSearchResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    cancelled: bool = False

    def sorted_hits(self) -> list[ArtworkHit]:
        out: list[ArtworkHit] = []
        for block in self.results:
            out.extend(block.hits)
        out = dedupe_hits(out)
        out.sort(key=lambda h: h.score, reverse=True)
        return out

    @property
    def total_hits(self) -> int:
        return len(self.sorted_hits())


def _parse_title_hint(text: str) -> tuple[str, str]:
    raw = (text or "").strip()
    if not raw:
        return "", ""
    parts = _TITLE_SPLIT.split(raw, maxsplit=1)
    if len(parts) == 2:
        left, right = parts[0].strip(), parts[1].strip()
        markers = (" van ", " de ", " da ", " di ", " le ", " von ", ",")
        left_artist = any(m in left.lower() for m in markers)
        right_artist = any(m in right.lower() for m in markers)
        if right_artist and not left_artist:
            return left, right
        if left_artist and not right_artist:
            return right, left
        return left, right
    return raw, ""


def _enabled_sources(
    sites: list[SiteEntry] | None,
    source_ids: list[str] | None,
) -> list[SourceDef]:
    bookmark_sites = sites if sites is not None else list(load_sites().sorted())
    sources = sources_for_sites(bookmark_sites)
    if source_ids:
        wanted = {s.strip() for s in source_ids if s.strip()}
        sources = [s for s in sources if s.source_id in wanted]
    return sources


def _link_matches_sources(link: ReverseLink, sources: list[SourceDef]) -> bool:
    src = source_for_url(link.url)
    if not src:
        return False
    return any(s.source_id == src.source_id for s in sources)


def _score_hits_with_hash(
    query_hash: int,
    hits: list[ArtworkHit],
    *,
    cancel_check: CancelCheck = None,
    on_status: StatusCallback = None,
) -> None:
    for hit in hits:
        if cancel_check and cancel_check():
            break
        preview = artwork_preview_url(hit)
        if not preview:
            continue
        raw = fetch_thumbnail_bytes(preview)
        if not raw:
            continue
        try:
            thumb_hash = dhash(raw)
            sim = similarity_score(query_hash, thumb_hash)
            hit.score = max(hit.score, sim)
        except (ImportError, OSError, ValueError):
            continue
        if on_status:
            on_status(f"Porownuje: {hit.source_name} — {hit.title[:40]}")


def search_by_image(
    image_path: str | Path,
    *,
    sites: list[SiteEntry] | None = None,
    source_ids: list[str] | None = None,
    limit_per_source: int = 5,
    on_status: StatusCallback = None,
    cancel_event: Event | None = None,
) -> ImageSearchResult:
    path = Path(image_path)
    if not path.is_file():
        return ImageSearchResult(image_path=str(path), notes=["Nie znaleziono pliku obrazu."])

    sources = _enabled_sources(sites, source_ids)
    if not sources:
        return ImageSearchResult(
            image_path=str(path),
            notes=["Dodaj linki muzeow w zakladce «Zakladki», aby wlaczyc wyszukiwanie."],
        )

    def _cancelled() -> bool:
        return bool(cancel_event and cancel_event.is_set())

    notes: list[str] = []
    blocks: dict[str, SourceSearchResult] = {
        s.source_id: SourceSearchResult(source_id=s.source_id, source_name=s.name, hits=[], search_mode="api")
        for s in sources
    }

    if on_status:
        on_status("Obliczam odcisk obrazu…")
    try:
        query_hash = dhash(path.read_bytes())
    except (OSError, ValueError) as exc:
        return ImageSearchResult(image_path=str(path), notes=[f"Nie udalo sie odczytac obrazu: {exc}"])

    hosted: dict[str, str] = {}
    if serpapi_key():
        if on_status:
            on_status("Wgrywam obraz (reverse search)…")
        try:
            from Komponenty.nazwijobraz.image_host import UploadError, upload_image_all_urls

            hosted, _sent, upl_errors = upload_image_all_urls(str(path))
            for err in upl_errors:
                notes.append(f"Upload: {err}")
        except ImportError:
            notes.append("Brak modulu nazwijobraz/image_host — upload niemozliwy.")
        except UploadError as exc:
            notes.append(f"Upload obrazu: {exc}")
        except OSError as exc:
            notes.append(f"Upload obrazu: {exc}")

        if _cancelled():
            return ImageSearchResult(image_path=str(path), results=list(blocks.values()), cancelled=True)

        if hosted:
            if on_status:
                on_status("Reverse image search (Google Lens, Yandex, Bing)…")
            rev = reverse_image_search(hosted)
            notes.extend(rev.errors)

            matched_links = [lk for lk in rev.links if _link_matches_sources(lk, sources)]
            if on_status:
                on_status(f"Linki muzealne: {len(matched_links)} / {len(rev.links)}")

            for link in matched_links[: limit_per_source * len(sources)]:
                if _cancelled():
                    break
                src = source_for_url(link.url)
                if not src or src.source_id not in blocks:
                    continue
                hit = lookup_hit_from_url(link.url, hint_title=link.title)
                if not hit:
                    continue
                hit.score = max(hit.score, 85.0)
                block = blocks[src.source_id]
                if len(block.hits) < limit_per_source:
                    block.hits.append(hit)

            title_hints: list[tuple[str, str]] = []
            for t in rev.titles[:12]:
                title, artist = _parse_title_hint(t)
                if title or artist:
                    title_hints.append((artist, title))

            if title_hints and not _cancelled():
                from .engine import search_collections

                artist, title = title_hints[0]
                if on_status:
                    on_status(f"Uzupelniam tekstem: {artist or '?'} — {title or '?'}")
                agg = search_collections(
                    artist=artist,
                    title=title,
                    sites=sites,
                    source_ids=[s.source_id for s in sources],
                    limit_per_source=limit_per_source,
                    on_status=on_status,
                    cancel_event=cancel_event,
                )
                for block in agg.results:
                    dst = blocks.get(block.source_id)
                    if not dst:
                        continue
                    for hit in block.hits:
                        if len(dst.hits) >= limit_per_source:
                            break
                        hit.score = max(hit.score, 40.0)
                        dst.hits.append(hit)
    else:
        notes.append(
            "Brak SERPAPI_KEY — dodaj klucz do cursor-api/.env (reverse image search, jak w nazwijobraz)."
        )

    if _cancelled():
        return ImageSearchResult(
            image_path=str(path),
            results=[b for b in blocks.values() if b.hits or b.error],
            notes=notes,
            cancelled=True,
        )

    all_hits = [h for b in blocks.values() for h in b.hits]
    if all_hits:
        if on_status:
            on_status("Porownuje podobienstwo graficzne miniatur…")
        _score_hits_with_hash(query_hash, all_hits, cancel_check=_cancelled, on_status=on_status)

    results = [b for b in blocks.values() if b.hits]
    results.sort(key=lambda b: (-max((h.score for h in b.hits), default=0), b.source_name))
    if not results and not notes:
        notes.append("Nie znaleziono dopasowan w wybranych zrodlach.")

    return ImageSearchResult(image_path=str(path), results=results, notes=notes)
