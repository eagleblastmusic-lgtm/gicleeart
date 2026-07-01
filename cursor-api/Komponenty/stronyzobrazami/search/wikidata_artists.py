"""Aliasy artystow z Wikidata (labels + aliases), cache na dysku."""

from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

from .http import get_json
from .text_norm import norm_search_text

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"
CACHE_FILE = CACHE_DIR / "wikidata_artist_aliases.json"

_SEARCH_LANGS = ("en", "pl", "fr", "de", "it", "es", "ru", "nl", "pt", "sv", "ja", "zh")

_qid_labels: dict[str, list[str]] | None = None
_query_labels: dict[str, list[str]] | None = None


def _load_cache() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    global _qid_labels, _query_labels
    if _qid_labels is not None and _query_labels is not None:
        return _qid_labels, _query_labels
    _qid_labels = {}
    _query_labels = {}
    if CACHE_FILE.is_file():
        try:
            raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                qids = raw.get("qids") or {}
                queries = raw.get("queries") or {}
                if isinstance(qids, dict):
                    _qid_labels = {k: list(v) for k, v in qids.items() if isinstance(v, list)}
                if isinstance(queries, dict):
                    _query_labels = {k: list(v) for k, v in queries.items() if isinstance(v, list)}
        except (OSError, json.JSONDecodeError, TypeError):
            _qid_labels = {}
            _query_labels = {}
    return _qid_labels, _query_labels


def _save_cache() -> None:
    qids, queries = _load_cache()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps({"qids": qids, "queries": queries}, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )


def _dedupe_labels(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        s = re.sub(r"\s+", " ", (value or "").strip())
        if not s:
            continue
        key = norm_search_text(s)
        if key and key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _entity_label_strings(entity: dict) -> list[str]:
    labels: list[str] = []
    for block in (entity.get("labels") or {}).values():
        if isinstance(block, dict):
            val = str(block.get("value") or "").strip()
            if val:
                labels.append(val)
    for lang_aliases in (entity.get("aliases") or {}).values():
        if not isinstance(lang_aliases, list):
            continue
        for block in lang_aliases:
            if isinstance(block, dict):
                val = str(block.get("value") or "").strip()
                if val:
                    labels.append(val)
    return _dedupe_labels(labels)


def _fetch_qid_labels(qid: str, *, timeout: float = 12.0) -> list[str]:
    qs = urllib.parse.urlencode(
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels|aliases",
            "languages": "|".join(_SEARCH_LANGS),
            "format": "json",
        }
    )
    data = get_json(f"{WIKIDATA_API}?{qs}", timeout=timeout)
    entity = ((data or {}).get("entities") or {}).get(qid) or {}
    if not isinstance(entity, dict):
        return []
    return _entity_label_strings(entity)


def _search_artist_qids(query: str, *, limit: int = 4, timeout: float = 10.0) -> list[str]:
    if not query.strip():
        return []
    has_non_ascii = any(ord(c) > 127 for c in query)
    order = ("pl", "fr", "de", "ru", "es", "it", "en") if has_non_ascii else ("en", "pl", "fr", "de", "ru", "es")
    seen: set[str] = set()
    out: list[str] = []
    for lang in order:
        qs = urllib.parse.urlencode(
            {
                "action": "wbsearchentities",
                "search": query,
                "language": lang,
                "format": "json",
                "limit": str(limit),
                "type": "item",
            }
        )
        try:
            data = get_json(f"{WIKIDATA_API}?{qs}", timeout=timeout)
        except RuntimeError:
            continue
        for hit in (data or {}).get("search") or []:
            qid = str((hit or {}).get("id") or "").strip()
            if qid.startswith("Q") and qid not in seen:
                seen.add(qid)
                out.append(qid)
        if out:
            break
    return out


def labels_for_qid(qid: str, *, fetch: bool = True) -> list[str]:
    qid = (qid or "").strip()
    if not qid.startswith("Q"):
        return []
    qids, _queries = _load_cache()
    if qid in qids:
        return list(qids[qid])
    if not fetch:
        return []
    labels = _fetch_qid_labels(qid)
    if labels:
        qids[qid] = labels
        _save_cache()
    return labels


def labels_for_query(query: str, *, fetch: bool = True) -> list[str]:
    key = norm_search_text(query)
    if not key:
        return []
    _qids, queries = _load_cache()
    if key in queries:
        return list(queries[key])
    if not fetch:
        return []
    labels: list[str] = []
    for qid in _search_artist_qids(query):
        labels.extend(labels_for_qid(qid, fetch=True))
    labels = _dedupe_labels(labels)
    if labels:
        queries[key] = labels
        _save_cache()
    return labels


def preload_qids(qids: list[str], *, max_fetch: int = 80) -> None:
    """Uzupelnia cache QID (np. z NGA CSV) — z limitem na sesje."""
    fetched = 0
    for qid in qids:
        if fetched >= max_fetch:
            break
        qid = (qid or "").strip()
        if not qid.startswith("Q"):
            continue
        cache, _ = _load_cache()
        if qid in cache:
            continue
        labels = _fetch_qid_labels(qid)
        if labels:
            cache[qid] = labels
            fetched += 1
    if fetched:
        _save_cache()


def reset_cache_for_tests() -> None:
    global _qid_labels, _query_labels
    _qid_labels = None
    _query_labels = None
