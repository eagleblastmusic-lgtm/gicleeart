"""Orkiestracja rownoleglego wyszukiwania w wielu kolekcjach."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
from typing import Callable

from ..storage import SiteEntry, load_sites
from .adapters import search_source
from .errors import format_source_error
from .registry import SourceDef, sources_for_sites
from .types import AggregatedSearch, SourceSearchResult

StatusCallback = Callable[[str], None] | None
CancelCallback = Callable[[], bool] | None


def _search_one(
    src: SourceDef,
    *,
    artist: str,
    title: str,
    limit: int,
    cancel_check: CancelCallback = None,
) -> SourceSearchResult:
    if cancel_check and cancel_check():
        return SourceSearchResult(
            source_id=src.source_id,
            source_name=src.name,
            error="Anulowano.",
        )
    t0 = time.perf_counter()
    hits, error, mode = search_source(
        src,
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )
    elapsed = int((time.perf_counter() - t0) * 1000)
    friendly = format_source_error(error, source_name=src.name) if error else ""
    return SourceSearchResult(
        source_id=src.source_id,
        source_name=src.name,
        hits=hits,
        error=friendly,
        elapsed_ms=elapsed,
        search_mode=mode,  # type: ignore[arg-type]
    )


def search_collections(
    *,
    artist: str = "",
    title: str = "",
    sites: list[SiteEntry] | None = None,
    source_ids: list[str] | None = None,
    limit_per_source: int = 8,
    max_workers: int = 6,
    on_status: StatusCallback = None,
    cancel_event: Event | None = None,
) -> AggregatedSearch:
    """Przeszukuje zrodla powiazane z zakladkami uzytkownika."""
    artist = (artist or "").strip()
    title = (title or "").strip()
    if not artist and not title:
        return AggregatedSearch(query_artist="", query_title="", results=[])

    bookmark_sites = sites if sites is not None else list(load_sites().sorted())
    sources = sources_for_sites(bookmark_sites)
    if source_ids:
        wanted = {s.strip() for s in source_ids if s.strip()}
        sources = [s for s in sources if s.source_id in wanted]

    if not sources:
        return AggregatedSearch(query_artist=artist, query_title=title, results=[])

    if on_status:
        on_status(f"Szukam w {len(sources)} zrodle(ach)...")

    def _cancelled() -> bool:
        return bool(cancel_event and cancel_event.is_set())

    results: list[SourceSearchResult] = []
    workers = max(1, min(max_workers, len(sources)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _search_one,
                src,
                artist=artist,
                title=title,
                limit=limit_per_source,
                cancel_check=_cancelled if cancel_event else None,
            ): src
            for src in sources
        }
        for fut in as_completed(futures):
            if _cancelled():
                for pending in futures:
                    pending.cancel()
                if on_status:
                    on_status("Anulowano.")
                break
            src = futures[fut]
            try:
                block = fut.result()
            except Exception as exc:
                block = SourceSearchResult(
                    source_id=src.source_id,
                    source_name=src.name,
                    error=format_source_error(str(exc), source_name=src.name),
                )
            results.append(block)
            if on_status:
                n = len(block.hits)
                if n:
                    on_status(f"{src.name}: {n} wynik(ow)")
                elif block.error:
                    on_status(f"{src.name}: {block.error[:60]}")

    order = {s.source_id: i for i, s in enumerate(sources)}
    results.sort(key=lambda r: order.get(r.source_id, 999))
    cancelled = _cancelled()
    return AggregatedSearch(
        query_artist=artist,
        query_title=title,
        results=results,
        cancelled=cancelled,
    )
