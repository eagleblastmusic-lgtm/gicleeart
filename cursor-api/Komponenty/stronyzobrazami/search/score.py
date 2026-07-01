"""Ocena trafnosci wynikow wyszukiwania."""

from __future__ import annotations

import re

from .artist_match import artist_match
from .text_norm import norm_search_text
from .types import ArtworkHit


def _norm(s: str) -> str:
    return norm_search_text(s)


def _tokens(text: str) -> list[str]:
    return [p for p in re.split(r"[\s,]+", _norm(text)) if len(p) >= 2]


def score_hit(hit: ArtworkHit, *, query_artist: str, query_title: str) -> float:
    base = float(hit.score or 0.0)
    if base <= 0:
        base = 1.0

    score = base
    qt = _norm(query_title)
    title = _norm(hit.title)

    if qt:
        if qt == title:
            score += 4.0
        elif qt in title:
            score += 2.5
        else:
            q_parts = _tokens(query_title)
            if q_parts and all(p in title for p in q_parts):
                score += 1.5

    if (query_artist or "").strip():
        if artist_match(query_artist, hit.artist or "", fetch_wikidata=False):
            score += 2.0
        elif _norm(query_artist) in _norm(hit.artist):
            score += 1.0

    if hit.image_url:
        score += 0.75
    if hit.search_mode == "api":
        score += 0.35
    elif hit.search_mode == "local":
        score += 0.25
    elif hit.search_mode == "web":
        score -= 1.5

    return score


def apply_scores(hits: list[ArtworkHit], *, query_artist: str, query_title: str) -> list[ArtworkHit]:
    out: list[ArtworkHit] = []
    for hit in hits:
        hit.score = score_hit(hit, query_artist=query_artist, query_title=query_title)
        out.append(hit)
    return out
