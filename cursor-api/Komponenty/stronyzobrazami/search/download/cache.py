"""Cache info.json IIIF i resolve_hit (TTL w pamieci)."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

_T = TypeVar("_T")

_CACHE: dict[str, tuple[float, Any]] = {}
_DEFAULT_TTL = 600.0


def cached(key: str, loader: Callable[[], _T], *, ttl: float = _DEFAULT_TTL) -> _T:
    now = time.monotonic()
    entry = _CACHE.get(key)
    if entry and now - entry[0] < ttl:
        return entry[1]  # type: ignore[return-value]
    value = loader()
    _CACHE[key] = (now, value)
    return value


def clear_cache() -> None:
    _CACHE.clear()
