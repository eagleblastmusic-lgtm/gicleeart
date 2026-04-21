"""Heurystyka wyszukania nazwiska artysty w sciezce do pliku.

Skanuje wszystkie segmenty od katalogu pliku w gore i wybiera pierwszy,
ktory wyglada jak imie/nazwisko ("Word Word" lub "Lastname, Firstname").
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Segmenty zawsze ignorowane (case-insensitive).
_STOPWORDS: frozenset[str] = frozenset(
    {
        "users", "user", "appdata", "roaming", "local", "temp", "tmp",
        "desktop", "pulpit", "documents", "dokumenty",
        "downloads", "pobrane", "downloads_",
        "pictures", "obrazy", "obraz", "zdjecia", "zdjecia_",
        "photos", "images", "img", "picture",
        "onedrive", "dropbox", "google drive", "icloud",
        "folder", "new folder", "nowy folder",
        "nowe", "pusty", "test", "tests", "tmp",
        "cursor-api", "nazwijobraz", "dodajobraz",
        "skarabeusz",
        "projekty", "projekty cursor",
        "scans", "skany", "skan", "scan",
        "src", "source", "sources",
        "git", ".git", ".cursor", ".vscode",
        "c:", "d:", "e:", "f:", "g:", "h:", "i:", "j:", "k:",
        "l:", "m:", "n:", "o:", "p:", "q:", "r:", "s:", "t:",
        "u:", "v:", "w:", "x:", "y:", "z:",
        "a", "b", "c",
        "00", "01", "02", "03", "04", "05",
        # Typowe nazwy "polek/kategorii" katalogow z reprodukcjami - lapia sie
        # na ogolny pattern "Word Word", a NIE sa nazwiskami artystow.
        "reprodukcje mistrzów", "reprodukcje mistrzow", "reprodukcje",
        "mistrzów", "mistrzow", "mistrzowie", "mistrz", "mistrzowie malarstwa",
        "stare obrazy", "stare", "stary", "stare malarstwo",
        "old masters", "old master", "masters", "master",
        "sea paintings", "landscape paintings", "portrait paintings",
        "marynistyka", "pejzaze", "pejzaż", "pejzaze_", "portrety",
        "kolekcja", "kolekcje", "collection", "collections",
        "galeria", "galerie", "gallery", "galleries",
        "muzeum", "museum", "museums",
        "wystawa", "wystawy", "exhibition", "exhibitions",
        "katalog", "katalogi", "catalog", "catalogs", "catalogue",
        "do druku", "do_druku", "do wydruku", "do wydruków",
        "produkty", "produkt", "products", "product",
        "sklep", "shop", "store", "magazyn",
        "klient", "klienci", "client", "clients",
        "zamowienia", "zamówienia", "orders", "order",
        "dla klientow", "dla klientów",
        "in-progress", "in progress", "wip", "draft", "drafts",
        "final", "finalne", "gotowe", "ready",
        "input", "output", "wejscie", "wyjscie", "wyjście",
        "raw", "raws", "edited", "edited_", "originals", "oryginaly",
        "do zrobienia", "todo", "to do", "to_do",
        "archive", "archives", "archiwum", "archiwa",
        "backup", "backups", "kopia", "kopie", "kopia zapasowa",
    }
)

_NAME_CHARS = r"A-Za-z\u00C0-\u017F\u0180-\u024F"
_RE_LASTFIRST = re.compile(rf"^([{_NAME_CHARS}][{_NAME_CHARS}\-']+),\s+([{_NAME_CHARS}][{_NAME_CHARS}\-' ]+)$")
_RE_FIRSTLAST = re.compile(
    rf"^([{_NAME_CHARS}][{_NAME_CHARS}\-']+(?:\s+[{_NAME_CHARS}][{_NAME_CHARS}\-']+){{1,3}})$"
)


def _looks_like_artist(segment: str) -> tuple[bool, str]:
    s = segment.strip()
    if not s or len(s) < 4 or len(s) > 60:
        return (False, "")
    if s.lower() in _STOPWORDS:
        return (False, "")
    # Drive letters like "C:"
    if re.fullmatch(r"[A-Za-z]:", s):
        return (False, "")
    # Tylko cyfry / przewazajaca czesc cyfr / interpunkcji
    if not any(ch.isalpha() for ch in s):
        return (False, "")
    # "Lastname, Firstname"
    m = _RE_LASTFIRST.match(s)
    if m:
        last, first = m.group(1).strip(), m.group(2).strip()
        return (True, _title_case(f"{first} {last}"))
    # "Firstname Lastname [Middle]"
    m = _RE_FIRSTLAST.match(s)
    if m:
        return (True, _title_case(s))
    return (False, "")


def _title_case(s: str) -> str:
    parts = []
    for word in re.split(r"(\s+|-)", s):
        if not word or word.isspace() or word == "-":
            parts.append(word)
            continue
        # Apostrofy: O'Keeffe, d'Orsay
        sub = re.split(r"(['\u2019])", word)
        rebuilt = []
        for k, piece in enumerate(sub):
            if piece in ("'", "\u2019"):
                rebuilt.append(piece)
            else:
                if k == 0 or sub[k - 1] not in ("'", "\u2019"):
                    rebuilt.append(piece.capitalize())
                else:
                    rebuilt.append(piece.capitalize())
        parts.append("".join(rebuilt))
    return "".join(parts)


def normalize_artist(name: str) -> str:
    """Normalizuje wpisany przez uzytkownika lub wyciagniety string nazwiska."""
    s = unicodedata.normalize("NFC", (name or "").strip())
    if not s:
        return ""
    if "," in s:
        m = _RE_LASTFIRST.match(s)
        if m:
            return _title_case(f"{m.group(2).strip()} {m.group(1).strip()}")
    return _title_case(re.sub(r"\s+", " ", s))


def find_artist_in_path(file_path: str | Path) -> str:
    """Znajdz autora w sciezce, idac od katalogu pliku w gore.

    Zwraca pusty string, jesli nic nie pasuje.
    """
    p = Path(file_path).resolve()
    parents = list(p.parents)
    for parent in parents:
        name = parent.name
        if not name:
            continue
        ok, normalized = _looks_like_artist(name)
        if ok:
            return normalized
    return ""
