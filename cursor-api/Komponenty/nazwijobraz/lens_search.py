"""Reverse image search przez SerpAPI Google Lens.

Zwraca tytul obrazu wyciagniety z visual_matches / knowledge_graph.
Wymaga SERPAPI_KEY w .env (cursor-api/.env).
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass

from .env_loader import get as env_get

SERPAPI_URL = "https://serpapi.com/search.json"


class LensError(RuntimeError):
    pass


@dataclass
class LensResult:
    title: str
    confidence: float  # 0..1
    raw_titles: list[str]
    source_url: str = ""


def _clean_candidate(raw: str) -> str:
    """Usun typowe sufiksy zrodel, kolekcji, itp."""
    s = (raw or "").strip()
    if not s:
        return ""
    # Odetnij wszystko po " - Wikipedia", " | Sotheby's" itd.
    s = re.split(r"\s[\-\u2013\u2014|:]\s", s)[0].strip()
    # Usun nadmiarowe cudzyslowy
    s = s.strip("\"'\u201c\u201d\u2018\u2019")
    # Usun podwojne spacje
    s = re.sub(r"\s+", " ", s)
    return s


def _strip_artist(title: str, artist: str) -> str:
    if not artist:
        return title
    # Usun warianty "by Artist", "Artist," "Artist -" itd.
    parts = artist.split()
    pattern_parts = [re.escape(p) for p in parts if p]
    if not pattern_parts:
        return title
    name_re = r"\b" + r"\s+".join(pattern_parts) + r"\b"
    cleaned = re.sub(rf"\bby\s+{name_re}\b", "", title, flags=re.IGNORECASE).strip()
    cleaned = re.sub(name_re, "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^[\-\u2013\u2014:|,\s]+|[\-\u2013\u2014:|,\s]+$", "", cleaned)
    return cleaned or title


def _token_set(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z\u00C0-\u017F]+", text) if len(t) > 2}


def _pick_best_title(candidates: list[str], *, title_hint: str = "") -> tuple[str, float]:
    """Sposrod kandydatow wybierz najczestszy / najsensowniejszy.

    Jesli mamy title_hint (np. z nazwy pliku), kandydaci wspoldzielacy duzo slow
    z hintem dostaja dodatkowy bonus w glosowaniu.
    """
    cleaned = [c for c in (_clean_candidate(t) for t in candidates) if c and len(c) >= 3]
    if not cleaned:
        return ("", 0.0)

    hint_tokens = _token_set(title_hint) if title_hint else set()
    counts: Counter[str] = Counter()
    for c in cleaned:
        key = c.lower()
        bonus = 0
        if hint_tokens:
            ov = len(hint_tokens & _token_set(c))
            if ov:
                bonus = ov  # kazdy pokrywajacy sie znaczacy wyraz = +1 glos
        counts[key] += 1 + bonus

    top_lower, score = counts.most_common(1)[0]
    best = next((c for c in cleaned if c.lower() == top_lower), cleaned[0])
    total_weight = sum(counts.values()) or 1
    confidence = min(1.0, score / total_weight)
    return (best, confidence)


def reverse_image_search(
    image_url: str,
    *,
    artist_hint: str = "",
    title_hint: str = "",
    timeout: float = 60.0,
) -> LensResult:
    """Zapyta\u0142 SerpAPI Google Lens o ten obraz; zwraca LensResult lub rzuca LensError."""
    api_key = env_get("SERPAPI_KEY")
    if not api_key:
        raise LensError("Brak SERPAPI_KEY w .env (cursor-api/.env).")
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": api_key,
        "hl": "en",
    }
    # Wspolna sesja z keep-alive - SerpAPI lubi byc odpytywany kilka razy z rzedu
    # (kazdy plik = 1 request), wiec recykling polaczenia TLS daje zauwazalny zysk.
    try:
        from .http_client import get_session
        sess = get_session()
        try:
            resp = sess.get(SERPAPI_URL, params=params, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            raise LensError(f"Blad polaczenia z SerpAPI: {e}") from e
        if resp.status_code >= 400:
            raise LensError(f"SerpAPI HTTP {resp.status_code}: {resp.reason}")
        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            raise LensError(f"SerpAPI: niepoprawny JSON ({e})") from e
    except ImportError:
        # Fallback na urllib gdy `requests` brak.
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            f"{SERPAPI_URL}?{qs}",
            headers={"User-Agent": "nazwijobraz/1.0"},
        )
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            raise LensError(f"SerpAPI HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise LensError(f"Blad polaczenia z SerpAPI: {e.reason}") from e

    if isinstance(data, dict) and data.get("error"):
        raise LensError(f"SerpAPI: {data['error']}")

    candidates: list[str] = []
    source_url = ""

    # 1) knowledge_graph (czasem dict, czasem lista)
    kg = data.get("knowledge_graph") if isinstance(data, dict) else None
    if isinstance(kg, dict):
        if kg.get("title"):
            candidates.append(str(kg["title"]))
        if kg.get("source_url"):
            source_url = str(kg["source_url"])
    elif isinstance(kg, list):
        for entry in kg[:3]:
            if isinstance(entry, dict) and entry.get("title"):
                candidates.append(str(entry["title"]))

    # 2) visual_matches
    matches = data.get("visual_matches") if isinstance(data, dict) else None
    if isinstance(matches, list):
        for m in matches[:8]:
            if not isinstance(m, dict):
                continue
            t = m.get("title") or m.get("source")
            if t:
                candidates.append(str(t))
            if not source_url:
                src = m.get("link") or m.get("source")
                if src and isinstance(src, str):
                    source_url = src

    if not candidates:
        raise LensError("Google Lens nie zwrocil tytulu (brak visual_matches).")

    # Strip artysty z kazdego kandydata
    stripped = [_strip_artist(t, artist_hint) for t in candidates]
    title, conf = _pick_best_title(stripped, title_hint=title_hint)
    if not title:
        title, conf = _pick_best_title(candidates, title_hint=title_hint)
    if not title:
        raise LensError("Nie udalo sie wyciagnac tytulu z odpowiedzi Google Lens.")
    return LensResult(title=title, confidence=conf, raw_titles=candidates[:8], source_url=source_url)
