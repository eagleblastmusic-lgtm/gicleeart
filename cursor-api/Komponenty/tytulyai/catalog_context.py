"""Kontekst katalogu dla batcha tytulow — unikanie duplikatow u artysty."""

from __future__ import annotations

import re
from typing import Any

_LUB_PAREN_RE = re.compile(r"\s*\(\s*lub\s+", re.IGNORECASE)


def pl_title_primary(title: str) -> str:
    """Glowny tytul PL (przed «(lub …)»)."""
    text = (title or "").strip()
    m = _LUB_PAREN_RE.search(text)
    if m:
        return text[: m.start()].strip()
    return text


def pl_title_key(title: str) -> str:
    return pl_title_primary(title).casefold()


def other_pl_titles_for_artist(
    rows: list[dict[str, Any]],
    *,
    artist: str,
    exclude_product_id: int = 0,
) -> list[str]:
    """Inne tytuly PL tego samego artysty (do promptu Gemini)."""
    artist_key = (artist or "").strip().casefold()
    if not artist_key:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        if (str(row.get("artist") or "").strip().casefold()) != artist_key:
            continue
        pid = int(row.get("product_id") or 0)
        if exclude_product_id and pid == exclude_product_id:
            continue
        title = str(row.get("painting_title") or "").strip()
        if not title:
            continue
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(title)
    return out


def find_pl_title_collision(
    new_pl_title: str,
    *,
    artist: str,
    product_id: int,
    catalog_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Zwraca wiersz katalogu z kolizja tytulu PL (ten sam artysta, ten sam tytul)."""
    artist_key = (artist or "").strip().casefold()
    new_key = pl_title_key(new_pl_title)
    if not artist_key or not new_key:
        return None
    for row in catalog_rows:
        if (str(row.get("artist") or "").strip().casefold()) != artist_key:
            continue
        pid = int(row.get("product_id") or 0)
        if product_id and pid == product_id:
            continue
        other = str(row.get("painting_title") or "").strip()
        if pl_title_key(other) == new_key:
            return row
    return None


def collision_warning(
    new_pl_title: str,
    *,
    artist: str,
    product_id: int,
    catalog_rows: list[dict[str, Any]],
) -> str:
    hit = find_pl_title_collision(
        new_pl_title,
        artist=artist,
        product_id=product_id,
        catalog_rows=catalog_rows,
    )
    if not hit:
        return ""
    other_title = str(hit.get("painting_title") or "").strip()
    other_id = int(hit.get("product_id") or 0)
    return (
        f"KOLIZJA TYTULU: «{pl_title_primary(new_pl_title)}» = produkt id={other_id} "
        f"({other_title!r}). Rozrozniaj obrazy tego artysty (detale z obrazu / obecny tytul sklepu)."
    )
