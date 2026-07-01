"""Wspolne typy wynikow wyszukiwania w kolekcjach muzealnych."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SearchMode = Literal["api", "local", "web"]


@dataclass
class ArtworkHit:
    source_id: str
    source_name: str
    title: str
    artist: str = ""
    date: str = ""
    medium: str = ""
    object_url: str = ""
    image_url: str = ""
    accession: str = ""
    department: str = ""
    object_type: str = ""
    search_mode: SearchMode = "api"
    score: float = 0.0
    raw_id: str = ""

    @property
    def ok(self) -> bool:
        return bool((self.title or "").strip() or (self.object_url or "").strip())


@dataclass
class SourceSearchResult:
    source_id: str
    source_name: str
    hits: list[ArtworkHit] = field(default_factory=list)
    error: str = ""
    elapsed_ms: int = 0
    search_mode: SearchMode = "api"

    @property
    def ok(self) -> bool:
        return bool(self.hits) and not self.error


SortMode = Literal["score", "source", "artist", "title"]


@dataclass
class AggregatedSearch:
    query_artist: str
    query_title: str
    results: list[SourceSearchResult] = field(default_factory=list)
    cancelled: bool = False

    def sorted_hits(self, sort_by: SortMode = "score") -> list[ArtworkHit]:
        from .dedup import dedupe_hits
        from .score import apply_scores

        out: list[ArtworkHit] = []
        for block in self.results:
            out.extend(block.hits)
        out = apply_scores(out, query_artist=self.query_artist, query_title=self.query_title)
        out = dedupe_hits(out)
        if sort_by == "source":
            out.sort(key=lambda h: (h.source_name.lower(), -h.score, h.title.lower()))
        elif sort_by == "artist":
            out.sort(key=lambda h: (h.artist.lower(), h.title.lower()))
        elif sort_by == "title":
            out.sort(key=lambda h: (h.title.lower(), h.artist.lower()))
        else:
            out.sort(key=lambda h: h.score, reverse=True)
        return out

    @property
    def all_hits(self) -> list[ArtworkHit]:
        return self.sorted_hits("score")

    @property
    def total_hits(self) -> int:
        return sum(len(r.hits) for r in self.results)

    @property
    def sources_with_errors(self) -> list[str]:
        return [r.source_name for r in self.results if r.error and not r.hits]
