"""Walidacja kolejki: kazde dzielo (artysta + tytul bazowy) wymaga preview i Full."""
from __future__ import annotations

from typing import Any

from .parser import IMAGE_ROLE_FULL, IMAGE_ROLE_MOCKUP, IMAGE_ROLE_PREVIEW


def work_group_key(artist: str, base_title: str) -> tuple[str, str]:
    return (artist.strip(), base_title.strip())


def group_needs_preview_full_pair(group: list[dict[str, Any]]) -> bool:
    """False gdy w kolejce sa tylko zalaczniki do istniejacego produktu (F/I/mockup)."""
    for it in group:
        if it.get("image_role") in (IMAGE_ROLE_PREVIEW, IMAGE_ROLE_FULL):
            return True
        if it.get("image_role") == IMAGE_ROLE_MOCKUP:
            continue
        if it.get("follow_up_number") is not None:
            continue
        return True
    return False


def audit_preview_full_pairs(items: list[dict[str, Any]]) -> list[str]:
    """Zwraca komunikaty o brakujacym preview lub Full per grupa (artysta, tytul)."""
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for it in items:
        key = work_group_key(it.get("artist") or "", it.get("base_title") or "")
        if not key[0] or not key[1]:
            continue
        by_key.setdefault(key, []).append(it)

    flags: dict[tuple[str, str], dict[str, bool]] = {}
    for key, group in by_key.items():
        if not group_needs_preview_full_pair(group):
            continue
        flags[key] = {"preview": False, "full": False}
        for it in group:
            role = it.get("image_role")
            if role == IMAGE_ROLE_PREVIEW:
                flags[key]["preview"] = True
            elif role == IMAGE_ROLE_FULL:
                flags[key]["full"] = True

    missing: list[str] = []
    for (artist, title) in sorted(flags.keys(), key=lambda k: (k[0].lower(), k[1].lower())):
        f = flags[(artist, title)]
        lack: list[str] = []
        if not f["preview"]:
            lack.append("(preview)")
        if not f["full"]:
            lack.append("Full")
        if lack:
            missing.append(f"{artist} - {title}: brak {' i '.join(lack)}")
    return missing


def format_pair_status(items: list[dict[str, Any]]) -> str:
    """Jednolinijkowy status do paska licznika."""
    miss = audit_preview_full_pairs(items)
    if not items:
        return ""
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for it in items:
        key = work_group_key(it.get("artist") or "", it.get("base_title") or "")
        if key[0] and key[1]:
            by_key.setdefault(key, []).append(it)
    n_checked = sum(1 for g in by_key.values() if group_needs_preview_full_pair(g))
    if n_checked == 0:
        return "Tylko zalaczniki (F/I/mockup) — para preview+Full nie jest wymagana"
    if not miss:
        return f"OK: {n_checked} dziel — preview + Full kompletne"
    return f"UWAGA: {len(miss)} z {n_checked} dziel bez kompletu preview+Full"
