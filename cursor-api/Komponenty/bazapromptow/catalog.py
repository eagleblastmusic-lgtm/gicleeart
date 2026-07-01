"""Katalog produktow Shopify i podstawianie placeholderow w promptach."""

from __future__ import annotations

import re
from typing import Any

from Komponenty.dodajobraz.description_update import (
    load_product_catalog_rows,
    product_catalog_sort_key,
)
from Komponenty.tytulyai.batch import resolve_product_image_url

_PLACEHOLDER_RE = re.compile(
    r"\[(autor|tytu[lł]|title|artist)\]",
    re.IGNORECASE,
)


def apply_prompt_placeholders(text: str, *, artist: str, title: str) -> str:
    """Podmienia [autor], [tytuł] (i warianty) na wybrane wartosci."""
    if not text:
        return text

    def _repl(match: re.Match[str]) -> str:
        token = match.group(1).lower()
        if token in ("autor", "artist"):
            return artist
        return title

    return _PLACEHOLDER_RE.sub(_repl, text)


def unique_artists(rows: list[dict[str, Any]]) -> list[str]:
    order: dict[str, tuple[Any, ...]] = {}
    for row in rows:
        artist = str(row.get("artist") or "").strip()
        if not artist:
            continue
        raw_idx = row.get("artist_sort_index")
        sort_idx = int(raw_idx) if raw_idx is not None else 999_999
        key = (
            sort_idx,
            str(row.get("surname") or "").lower(),
            str(row.get("firstname") or "").lower(),
            artist.lower(),
        )
        if artist not in order or key < order[artist]:
            order[artist] = key
    return sorted(order.keys(), key=lambda a: order[a])


def paintings_for_artist(rows: list[dict[str, Any]], artist: str) -> list[dict[str, Any]]:
    artist_key = (artist or "").strip()
    subset = [
        row for row in rows
        if str(row.get("artist") or "").strip() == artist_key
    ]
    return sorted(subset, key=product_catalog_sort_key)


def painting_label(row: dict[str, Any]) -> str:
    return str(row.get("painting_title") or row.get("product_title") or "?").strip()


def painting_display(row: dict) -> str:
    title = painting_label(row)
    pid = int(row.get("product_id") or 0)
    if pid:
        return f"{title}  [{pid}]"
    return title


def load_catalog_rows(
    *,
    on_progress: Any = None,
) -> list[dict[str, Any]]:
    return load_product_catalog_rows(on_progress=on_progress)


def row_image_url(row: dict[str, Any]) -> str:
    return resolve_product_image_url(row)
