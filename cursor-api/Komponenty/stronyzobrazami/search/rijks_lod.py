"""Parsowanie Linked Art JSON z nowego API Rijksmuseum (data.rijksmuseum.nl)."""

from __future__ import annotations

import re
import urllib.request
from typing import Any

from .http import USER_AGENT, get_json

RIJKS_SEARCH = "https://data.rijksmuseum.nl/search/collection"
RIJKS_ID_BASE = "https://id.rijksmuseum.nl/"

_DURABLE_ID_RE = re.compile(r"https://id\.rijksmuseum\.nl/(\d+)")
_AAT_EN = "http://vocab.getty.edu/aat/300388277"
_AAT_TITLE = "http://vocab.getty.edu/aat/300417207"
_AAT_BRIEF = "http://vocab.getty.edu/aat/300404670"
_AAT_CREATOR = "http://vocab.getty.edu/aat/300435416"


def _is_en(block: dict[str, Any]) -> bool:
    for lang in block.get("language") or []:
        if isinstance(lang, dict) and str(lang.get("id") or "") == _AAT_EN:
            return True
    return False


def _classified_ids(block: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in block.get("classified_as") or []:
        if isinstance(row, dict) and row.get("id"):
            out.add(str(row["id"]))
    return out


def _pick_creator(blocks: list[Any]) -> str:
    preferred: list[str] = []
    fallback: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        content = str(block.get("content") or "").strip()
        if not content:
            continue
        if _AAT_CREATOR in _classified_ids(block):
            (preferred if _is_en(block) else fallback).append(content)
        elif block.get("type") in ("Name", "LinguisticObject"):
            fallback.append(content)
    return (preferred or fallback or [""])[0]


def _pick_name(blocks: list[Any], *, want_title: bool) -> str:
    preferred: list[str] = []
    fallback: list[str] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "Name":
            continue
        content = str(block.get("content") or "").strip()
        if not content:
            continue
        ids = _classified_ids(block)
        if want_title:
            if _AAT_TITLE in ids or _AAT_BRIEF in ids:
                (preferred if _is_en(block) else fallback).append(content)
            elif _is_en(block):
                fallback.append(content)
        elif _AAT_CREATOR in ids or not want_title:
            (preferred if _is_en(block) else fallback).append(content)
    return (preferred or fallback or [""])[0]


def _walk_access_points(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        if node.get("type") == "DigitalObject":
            for ap in node.get("access_point") or []:
                if isinstance(ap, dict) and ap.get("id"):
                    out.append(str(ap["id"]))
        for v in node.values():
            _walk_access_points(v, out)
    elif isinstance(node, list):
        for item in node:
            _walk_access_points(item, out)


def rijks_object_url(obj: dict[str, Any]) -> str:
    urls: list[str] = []
    _walk_access_points(obj.get("subject_of"), urls)
    for url in urls:
        if "rijksmuseum.nl" in url and "/collectie/" in url:
            return url.replace("/nl/collectie/", "/en/collection/").replace("/collectie/", "/collection/")
    oid = str(obj.get("id") or "")
    if "/id.rijksmuseum.nl/" in oid:
        num = oid.rsplit("/", 1)[-1]
        return f"https://www.rijksmuseum.nl/en/collection/object/{num}"
    return ""


def durable_id_from_text(text: str) -> str:
    m = _DURABLE_ID_RE.search(text or "")
    return m.group(1) if m else ""


def rijks_object_json_url(ref: str) -> str:
    raw = (ref or "").strip()
    if not raw:
        return ""
    if raw.startswith("http") and "id.rijksmuseum.nl" in raw:
        return raw.split("?")[0].rstrip("/")
    if raw.isdigit():
        return f"{RIJKS_ID_BASE}{raw}"
    num = durable_id_from_text(raw)
    return f"{RIJKS_ID_BASE}{num}" if num else ""


def fetch_rijks_object(ref: str) -> dict[str, Any] | None:
    """Pobierz obiekt Linked Art — po URL id.rijksmuseum.nl lub stronie www z slugiem."""
    api_url = rijks_object_json_url(ref)
    if api_url:
        try:
            data = get_json(api_url, timeout=20)
            return data if isinstance(data, dict) else None
        except RuntimeError:
            pass

    page = (ref or "").strip()
    if not page.startswith("http") or "rijksmuseum.nl" not in page:
        return None
    try:
        req = urllib.request.Request(page, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            html = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None

    durable_id = durable_id_from_text(html)
    if not durable_id:
        return None
    try:
        data = get_json(f"{RIJKS_ID_BASE}{durable_id}", timeout=20)
        return data if isinstance(data, dict) else None
    except RuntimeError:
        return None


def rijks_iiif_service(obj: dict[str, Any], *, cache: dict[str, str] | None = None) -> str:
    thumb = rijks_image_url(obj, cache=cache)
    if not thumb:
        return ""
    return thumb.split("/full/")[0].rstrip("/")


def rijks_image_url(obj: dict[str, Any], *, cache: dict[str, str] | None = None) -> str:
    shows = obj.get("shows") or []
    if not isinstance(shows, list) or not shows:
        return ""
    visual_id = str((shows[0] or {}).get("id") or "")
    if not visual_id:
        return ""
    mem = cache if cache is not None else {}
    if visual_id in mem:
        return mem[visual_id]
    try:
        visual = get_json(visual_id, timeout=15)
        carriers = visual.get("digitally_shown_by") or []
        if not carriers:
            return ""
        dig_id = str((carriers[0] or {}).get("id") or "")
        if not dig_id:
            return ""
        if dig_id in mem:
            return mem[dig_id]
        digital = get_json(dig_id, timeout=15)
        for ap in digital.get("access_point") or []:
            if isinstance(ap, dict) and ap.get("id"):
                url = str(ap["id"])
                thumb = url.replace("/full/max/", "/full/180,/")
                mem[visual_id] = thumb
                mem[dig_id] = thumb
                return thumb
    except RuntimeError:
        return ""
    return ""


def parse_rijks_object(obj: dict[str, Any], *, cache: dict[str, str] | None = None) -> dict[str, str]:
    names = obj.get("identified_by") or []
    title = _pick_name(names if isinstance(names, list) else [], want_title=True)
    prod = obj.get("produced_by") or {}
    artist_blocks: list[Any] = []
    if isinstance(prod, dict):
        artist_blocks.extend(prod.get("referred_to_by") or [])
    artist_blocks.extend(obj.get("attributed_by") or [])
    artist = _pick_creator(artist_blocks)
    date = ""
    if isinstance(prod, dict):
        ts = prod.get("timespan") or {}
        if isinstance(ts, dict):
            for block in ts.get("identified_by") or []:
                if isinstance(block, dict) and block.get("content"):
                    date = str(block["content"])
                    break
    accession = ""
    for block in names if isinstance(names, list) else []:
        if not isinstance(block, dict) or block.get("type") != "Identifier":
            continue
        content = str(block.get("content") or "").strip()
        if content and not content.isdigit():
            accession = content
            break
    return {
        "title": title,
        "artist": artist,
        "date": date,
        "object_url": rijks_object_url(obj),
        "image_url": rijks_image_url(obj, cache=cache),
        "accession": accession,
        "object_type": rijks_object_type(obj),
        "raw_id": str(obj.get("id") or ""),
    }


def rijks_object_type(obj: dict[str, Any]) -> str:
    for block in obj.get("classified_as") or []:
        if not isinstance(block, dict):
            continue
        for note in block.get("notation") or []:
            if isinstance(note, dict):
                val = note.get("en") or note.get("@value") or ""
                if val:
                    return str(val)
            elif isinstance(note, str) and note:
                return note
    return ""
