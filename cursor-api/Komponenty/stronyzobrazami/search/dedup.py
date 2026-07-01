"""Deduplikacja wynikow miedzy muzeami."""

from __future__ import annotations

import re

from .types import ArtworkHit


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _dedup_key(hit: ArtworkHit) -> str:
    if hit.accession and len(hit.accession) >= 4:
        return f"acc:{_norm(hit.accession)}"
    title = _norm(hit.title)
    artist = _norm(hit.artist.split(",")[0] if hit.artist else "")
    if title and artist:
        return f"ta:{artist}|{title}"
    if title:
        return f"t:{title}"
    url = (hit.object_url or "").rstrip("/").lower()
    if url:
        return f"u:{url}"
    return f"id:{hit.source_id}:{hit.raw_id or hit.title}"


def dedupe_hits(hits: list[ArtworkHit]) -> list[ArtworkHit]:
    best: dict[str, ArtworkHit] = {}
    order: list[str] = []
    for hit in hits:
        key = _dedup_key(hit)
        if key not in best:
            best[key] = hit
            order.append(key)
            continue
        prev = best[key]
        if hit.score > prev.score:
            hit.source_name = f"{hit.source_name} (+ {prev.source_name})"
            best[key] = hit
        else:
            prev.source_name = f"{prev.source_name} (+ {hit.source_name})"
    return [best[k] for k in order]
