"""URL miniatur Minneapolis Institute of Art (shardowany CDN)."""

from __future__ import annotations

import re

_MIA_IMAGE_RE = re.compile(
    r"https?://(?:\d+\.)?api\.artsmia\.org/images/(?P<id>\d+)/(?:small|medium|large|thumbnail)\.jpg",
    re.IGNORECASE,
)


def mia_object_id(raw: str | int) -> int | None:
    text = str(raw or "").strip()
    if not text.isdigit():
        return None
    return int(text)


def mia_preview_url(object_id: str | int, *, large: bool = False) -> str:
    """Zgodnie z collections.artsmia.org (image-cdn.js): shard = id %% 7."""
    oid = mia_object_id(object_id)
    if oid is None:
        return ""
    shard = oid % 7
    if large:
        return f"https://{shard}.api.artsmia.org/800/{oid}.jpg"
    return f"https://{shard}.api.artsmia.org/{oid}.jpg"


def normalize_mia_image_url(url: str) -> str:
    """Stary api.artsmia.org/images/.../small.jpg → dzialajacy shard."""
    u = (url or "").strip()
    if not u:
        return ""
    m = _MIA_IMAGE_RE.match(u)
    if m:
        return mia_preview_url(m.group("id"))
    if "api.artsmia.org" in u and "/images/" in u:
        oid = mia_object_id(u.rsplit("/", 1)[-1].split(".")[0])
        if oid is not None:
            return mia_preview_url(oid)
    return u
