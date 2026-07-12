"""Dopasowanie nazw artystow — diakrytyki, transliteracja, aliasy Wikidata, warianty imion."""
from __future__ import annotations

import re

from . import wikidata_artists
from .text_norm import norm_search_text
from .transliterate import transliterate_norm, transliterate_to_latin

_MIN_TOKEN = 3
_FUZZY_MIN = 4


def _split_parts(text: str) -> list[str]:
    n = norm_search_text(text)
    return [p for p in re.split(r"[\s,]+", n) if len(p) >= _MIN_TOKEN]


def _name_part_count(text: str) -> int:
    """Liczba rzeczywistych czlonow nazwy, takze krotszych niz token indeksu."""
    return len([p for p in re.split(r"[\s,]+", norm_search_text(text)) if p])


def name_variants(name: str, *, wikidata_qid: str = "", fetch_wikidata: bool = True) -> list[str]:
    """Mozliwe zapisy nazwy do porownania (oryginal, translit, aliasy WD)."""
    out: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        s = re.sub(r"\s+", " ", (value or "").strip())
        if not s:
            return
        key = norm_search_text(s)
        if key and key not in seen:
            seen.add(key)
            out.append(s)

    raw = (name or "").strip()
    _add(raw)
    if transliterate_to_latin(raw) != raw:
        _add(transliterate_to_latin(raw))

    qid = (wikidata_qid or "").strip()
    if qid.startswith("Q"):
        for label in wikidata_artists.labels_for_qid(qid, fetch=fetch_wikidata):
            _add(label)
    elif fetch_wikidata and raw and _name_part_count(raw) >= 2:
        # Fuzzy wbsearchentities dla pojedynczego nazwiska moze zwrocic inna
        # osobe o podobnej nazwie (np. Monet -> Moneta). Aliasy bez QID sa
        # bezpiecznie rozszerzane tylko dla nazw wieloczlonowych, rowniez gdy
        # jeden czlon jest krotki (np. El Greco).
        for label in wikidata_artists.labels_for_query(raw, fetch=True):
            _add(label)

    return out


def artist_query_parts(artist: str, *, fetch_wikidata: bool = True) -> list[str]:
    """Tokeny zapytania (oryginal + translit + aliasy WD) do indeksu."""
    parts: set[str] = set()
    for variant in name_variants(artist, fetch_wikidata=fetch_wikidata):
        parts.update(_split_parts(variant))
        parts.update(_split_parts(transliterate_norm(variant)))
    return sorted(parts)


def index_lookup_fuzzy(index: dict[str, set], artist: str, *, fetch_wikidata: bool = True) -> set:
    """OID/indeksy majace dopasowanie do wszystkich czesci zapytania (z fuzzy tokenami)."""
    primary: set[str] = set()
    for src in (artist, transliterate_to_latin(artist)):
        primary.update(_split_parts(src))
        primary.update(_split_parts(transliterate_norm(src)))
    if not primary:
        return set()

    def _keys_for_part(part: str) -> set[str]:
        keys = {part}
        for key in index:
            if _tokens_equivalent(part, key):
                keys.add(key)
        return keys

    def _lookup_parts(parts: set[str]) -> set:
        if not parts:
            return set()
        buckets: list[set] = []
        for part in parts:
            matched: set = set()
            for key in _keys_for_part(part):
                matched |= index.get(key, set())
            buckets.append(matched)
        result = buckets[0]
        for bucket in buckets[1:]:
            result &= bucket
        return result

    oids = _lookup_parts(primary)
    if oids or not fetch_wikidata:
        return oids
    for label in wikidata_artists.labels_for_query(artist, fetch=True):
        alt = set(_split_parts(label)) | set(_split_parts(transliterate_norm(label)))
        if alt:
            oids |= _lookup_parts(alt)
    return oids


def artist_index_tokens(text: str, *, wikidata_qid: str = "") -> list[str]:
    """Tokeny do indeksu wyszukiwania (>=3 znaki)."""
    tokens: set[str] = set()
    for variant in name_variants(text, wikidata_qid=wikidata_qid, fetch_wikidata=False):
        for part in _split_parts(variant):
            tokens.add(part)
        tr = transliterate_norm(variant)
        for part in _split_parts(tr):
            tokens.add(part)
    qid = (wikidata_qid or "").strip()
    if qid.startswith("Q"):
        for label in wikidata_artists.labels_for_qid(qid, fetch=False):
            tokens.update(_split_parts(label))
            tokens.update(_split_parts(transliterate_norm(label)))
    if not tokens and text.strip():
        for part in _split_parts(text):
            tokens.add(part)
        for part in _split_parts(transliterate_norm(text)):
            tokens.add(part)
    return sorted(tokens)


_FUZZY_SUFFIXES = frozenset({"", "s", "e", "es", "er", "us", "el", "le", "us"})


def _tokens_equivalent(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) < _FUZZY_MIN or len(b) < _FUZZY_MIN:
        return False
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if longer.startswith(shorter):
        suffix = longer[len(shorter) :]
        if suffix in _FUZZY_SUFFIXES and len(shorter) >= _FUZZY_MIN:
            return True
    return False


def _token_in_hay(token: str, hay_tokens: set[str]) -> bool:
    return any(_tokens_equivalent(token, ht) for ht in hay_tokens)


def _hay_tokens(hay: str) -> set[str]:
    tokens: set[str] = set()
    for variant in (hay, transliterate_to_latin(hay)):
        tokens.update(_split_parts(variant))
        tokens.update(_split_parts(transliterate_norm(variant)))
    return tokens


def _all_parts_match(candidate: str, hay: str) -> bool:
    h_norm = norm_search_text(hay)
    if not h_norm:
        return False
    c_norm = norm_search_text(candidate)
    if c_norm and re.search(rf"\b{re.escape(c_norm)}\b", h_norm):
        return True
    parts = _split_parts(candidate)
    if not parts:
        parts = _split_parts(transliterate_norm(candidate))
    if not parts:
        return False
    hay_tokens = _hay_tokens(hay)
    return all(_token_in_hay(part, hay_tokens) for part in parts)


def artist_match(needle: str, hay: str, *, hay_wikidata_qid: str = "", fetch_wikidata: bool = True) -> bool:
    if not needle:
        return True
    if not (hay or "").strip():
        return False
    for variant in name_variants(needle, fetch_wikidata=fetch_wikidata):
        if _all_parts_match(variant, hay):
            return True
    if hay_wikidata_qid:
        for variant in name_variants(hay, wikidata_qid=hay_wikidata_qid, fetch_wikidata=False):
            if _all_parts_match(needle, variant):
                return True
    return False
