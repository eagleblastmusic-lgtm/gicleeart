"""Wyciaganie podpowiedzi autora / tytulu z samej nazwy pliku.

Znak podkreslnika '_' jest traktowany jak spacja. Funkcja potrafi rozpoznac
formaty typu:
- 'Alfred Sisley - Landscape at Louveciennes.jpg'
- 'alfred_sisley_landscape_at_louveciennes.jpg'
- 'sisley_landscape_louveciennes_1873.jpg'
- 'cows in pasture louveciennes.jpg' (sam tytul)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .artist_from_path import normalize_artist
from .renamer import _strip_extension_artifacts, format_artwork_title

_SEPARATOR_RE = re.compile(r"\s+[-\u2013\u2014:|]\s+")
# Znaki traktowane jak spacja
_SPACE_LIKE = "_"
# Typowe "smieciowe" kawalki do usuniecia z tytulu (po rozdzieleniu)
_NOISE_TOKENS = {
    "painting", "oil", "canvas", "scan", "print", "hd", "hq",
    "wikipedia", "wikimedia", "commons", "public", "domain",
    "copy", "reproduction", "reprodukcja",
}
_YEAR_RE = re.compile(r"\b(?:15|16|17|18|19|20)\d{2}\b")
_MULTISPACE_RE = re.compile(r"\s+")
# Sufiksy duplikatu pliku z Windows: "-1", "-1-2", " (1)", "_full".
# Tne sie na samym koncu nazwy (po _cleanup, gdzie '_' to juz ' ').
# Pojedynczy sufiks duplikatu: 1-3 cyfry albo (NN). Stripujemy iteracyjnie
# (po jednym), zeby nie zniszczyc numerow inwentarzowych typu "_1961_630_0-11".
_DUP_SUFFIX_RE = re.compile(
    r"(?:[\s\-]\(\d+\)|[\s\-]\d{1,3}|[\s\-](?:full|hd|hq|copy|kopia))$",
    re.IGNORECASE,
)
# Prefixy robocze ("Mockup ", "Copy of ", "Final ").
_NOISE_PREFIX_RE = re.compile(
    r"^(?:mockup|copy of|final|kopia|kopia\s+pliku)[\s\-]+",
    re.IGNORECASE,
)


@dataclass
class FilenameHints:
    artist: str
    title: str


def _cleanup(text: str) -> str:
    t = text
    for ch in _SPACE_LIKE:
        t = t.replace(ch, " ")
    t = _MULTISPACE_RE.sub(" ", t).strip(" .-,_:|")
    # Sciagnij prefix typu "Mockup " (czesty u nas - mockupy do sklepu).
    t = _NOISE_PREFIX_RE.sub("", t).strip(" .-,_:|")
    # Sciagnij sufiks duplikatu z Windows ("-1", "-1-2", " (1)").
    # Iteracyjnie - moze ich byc kilka.
    for _ in range(3):
        new_t = _DUP_SUFFIX_RE.sub("", t).strip(" .-,_:|")
        if new_t == t:
            break
        t = new_t
    return t


def _drop_noise(text: str) -> str:
    words = text.split()
    kept = [w for w in words if w.lower() not in _NOISE_TOKENS]
    return " ".join(kept).strip()


def _strip_artist_from(text: str, artist: str) -> str:
    if not artist or not text:
        return text
    parts = [re.escape(p) for p in artist.split() if p]
    if not parts:
        return text
    # Dopuszczamy 1-2 spacje/myslniki miedzy slowami
    pattern = r"\b" + r"[\s\-]+".join(parts) + r"\b"
    cleaned = re.sub(pattern, "", text, flags=re.IGNORECASE)
    # Tez odwrotnie "Nazwisko Imie"
    rev = r"\b" + r"[\s\-]+".join(reversed(parts)) + r"\b"
    cleaned = re.sub(rev, "", cleaned, flags=re.IGNORECASE)
    cleaned = _MULTISPACE_RE.sub(" ", cleaned).strip(" -_:|,.")
    return cleaned


def _looks_like_artist(text: str) -> bool:
    s = text.strip()
    if not s or len(s) < 4 or len(s) > 60:
        return False
    # 2+ slow, wiekszosc zaczyna sie wielka litera (po NFC)
    words = [w for w in re.split(r"[\s\-]+", s) if w]
    if len(words) < 2 or len(words) > 4:
        return False
    cap = sum(1 for w in words if w[:1].isalpha() and w[:1].upper() == w[:1])
    return cap >= max(1, len(words) - 1)


def parse_filename_hints(file_path: str | Path, *, artist_hint: str = "") -> FilenameHints:
    """Zwraca wskazowki autora / tytulu wyciagniete z nazwy pliku.

    artist_hint - jesli znamy juz autora (np. z folderu), uzywa go do wyciecia
    nazwiska z nazwy pliku, co zostawia czystszy tytul.
    """
    stem = Path(file_path).stem
    # Czasem nazwa to "obraz.jpg.jpg" -> stem zostawia ".jpg" w srodku.
    stem = _strip_extension_artifacts(stem)
    cleaned = _cleanup(stem)
    cleaned = _strip_extension_artifacts(cleaned)
    if not cleaned:
        return FilenameHints(artist="", title="")

    artist = ""
    title = ""

    # 1) Separator typu ' - ', ' : ', ' | '
    m = _SEPARATOR_RE.split(cleaned, maxsplit=1)
    if len(m) == 2:
        left, right = m[0].strip(), m[1].strip()
        if _looks_like_artist(left):
            artist, title = normalize_artist(left), right
        elif _looks_like_artist(right):
            artist, title = normalize_artist(right), left
        else:
            # Brak oczywistego autora, ale zakladamy typowy format "Autor - Tytul"
            artist, title = normalize_artist(left), right

    # 2) Brak separatora - sprobuj doklei\u0107 znany artist_hint i odjac z tekstu
    if not artist and artist_hint:
        stripped = _strip_artist_from(cleaned, artist_hint)
        if stripped and stripped != cleaned:
            artist = normalize_artist(artist_hint)
            title = stripped

    # 3) Nadal brak - caly string to potencjalny tytul
    if not title:
        title = cleaned

    # 4) Oczysc tytul: usun rok, drobny noise, spacje na brzegach
    title = _YEAR_RE.sub(" ", title)
    title = _drop_noise(title)
    title = _strip_extension_artifacts(title)
    title = _MULTISPACE_RE.sub(" ", title).strip(" -_:|,.")
    title = format_artwork_title(title)

    return FilenameHints(artist=artist, title=title)
