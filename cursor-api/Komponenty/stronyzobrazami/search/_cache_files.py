"""Pobieranie plikow CSV do cache (NGA, Walters, media)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from .http import USER_AGENT


def ensure_cached_csv(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file():
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp:
            dest.write_bytes(resp.read())
    return dest
