"""Parsowanie nazwy pliku i pomocnicze funkcje (slug)."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_POLISH_MAP = str.maketrans(
    {
        "\u0105": "a", "\u0107": "c", "\u0119": "e", "\u0142": "l",
        "\u0144": "n", "\u00f3": "o", "\u015b": "s", "\u017a": "z",
        "\u017c": "z",
        "\u0104": "A", "\u0106": "C", "\u0118": "E", "\u0141": "L",
        "\u0143": "N", "\u00d3": "O", "\u015a": "S", "\u0179": "Z",
        "\u017b": "Z",
    }
)


def parse_filename(path: str | Path) -> tuple[str, str]:
    """'Ivan Aivazovsky - Nadciagajaca burza.jpg' -> ('Ivan Aivazovsky', 'Nadciagajaca burza').

    Separator: ' - ' (spacja mysjnik spacja).
    """
    p = Path(path)
    stem = p.stem.strip()
    # '_' w nazwie pliku traktujemy jak spacje (np. 'Jozef_Chelmonski_-_Babie_lato')
    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    # preferuj ' - ' ale toleruj ' \u2013 ' (en-dash) i ' \u2014 ' (em-dash)
    for sep in (" - ", " \u2013 ", " \u2014 "):
        if sep in stem:
            left, right = stem.split(sep, 1)
            return left.strip(), right.strip()
    raise ValueError(
        "Nazwa pliku musi miec format 'Artysta - Tytul obrazu.ext' (separator: ' - ')."
    )


def artist_collection_title(artist: str) -> str:
    """'Ivan Aivazovsky' -> 'Aivazovsky, Ivan'. 'Vincent van Gogh' -> 'Gogh, Vincent van'."""
    parts = artist.strip().split()
    if len(parts) < 2:
        return artist.strip()
    surname = parts[-1]
    rest = " ".join(parts[:-1])
    return f"{surname}, {rest}"


def slugify(text: str) -> str:
    s = text.translate(_POLISH_MAP)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def surname_only(artist: str) -> str:
    parts = artist.strip().split()
    return parts[-1] if parts else artist


SOURCE_TAG_PREFIX = "src:"


def compute_source_key(artist: str, base_title: str) -> str:
    """Stabilny, jezykowo-niezalezny identyfikator produktu wyliczony z nazwy pliku.

    Przyklad:
      compute_source_key('Hans Dahl', 'Girl beside a fjord')
        -> 'hans-dahl__girl-beside-a-fjord'

    Identyczny dla 'Hans Dahl - Girl beside a fjord' i 'Hans Dahl - Girl beside a fjord F2'
    (uzywamy tytulu bazowego bez sufiksu F<N>).
    """
    a = slugify(artist or "")
    t = slugify(base_title or "")
    if a and t:
        return f"{a}__{t}"
    return a or t


def source_key_tag(source_key: str) -> str:
    return f"{SOURCE_TAG_PREFIX}{source_key}"


_FOLLOWUP_RE = re.compile(r"^(?P<base>.*?)\s+F(?P<num>\d+)\s*$", re.IGNORECASE)

# Sufiks korekty kolorystycznej: 'WK' (wstepna) lub 'KK' (koncowa). Tylko VERSALIKAMI,
# zeby przypadkiem nie obciac slowa typu "Wk\u00f3l Trasy" (gdyby ktos uzyl maly liter).
# Akceptowane warianty na koncu tytulu (po podziale 'Artysta - Tytul'):
#   'Tytul KK', 'Tytul WK'         (separator: spacja)
#   'Tytul - KK', 'Tytul - WK'     (separator: ' - ' z myslnikiem ASCII / en-dash / em-dash)
_CORRECTION_RE = re.compile(
    r"^(?P<base>.*?)\s+(?:[-\u2013\u2014]\s+)?(?P<sfx>WK|KK)\s*$"
)


def parse_follow_up(title: str) -> tuple[str, int | None]:
    """Rozpoznaje sufiks 'F<N>' na koncu tytulu.

    'Babie lato F2' -> ('Babie lato', 2); 'Babie lato' -> ('Babie lato', None).
    """
    if not title:
        return title, None
    m = _FOLLOWUP_RE.match(title.strip())
    if not m:
        return title.strip(), None
    base = m.group("base").strip()
    try:
        num = int(m.group("num"))
    except ValueError:
        return title.strip(), None
    if num < 2:
        return title.strip(), None
    return base, num


def parse_title_metadata(title: str) -> tuple[str, int | None, str | None]:
    """Iteracyjnie odlupuje z konca tytulu sufiksy meta: 'F<N>' oraz 'WK'/'KK'.

    Zwraca (base_title, follow_up_number, correction_suffix).

    Przyklady:
      'Babie lato'              -> ('Babie lato', None, None)
      'Babie lato F2'           -> ('Babie lato', 2,    None)
      'Babie lato KK'           -> ('Babie lato', None, 'KK')
      'Babie lato WK'           -> ('Babie lato', None, 'WK')
      'Babie lato - KK'         -> ('Babie lato', None, 'KK')
      'Babie lato - WK'         -> ('Babie lato', None, 'WK')
      'Babie lato F2 KK'        -> ('Babie lato', 2,    'KK')
      'Babie lato KK F2'        -> ('Babie lato', 2,    'KK')
      'Babie lato F2 - KK'      -> ('Babie lato', 2,    'KK')

    Sufiksy moga wystapic w dowolnej kolejnosci - sciagamy je w petli az zostanie tylko tytul.
    """
    if not title:
        return title, None, None
    s = title.strip()
    follow_up: int | None = None
    correction: str | None = None
    changed = True
    while changed:
        changed = False
        m_fu = _FOLLOWUP_RE.match(s)
        if m_fu:
            try:
                num = int(m_fu.group("num"))
            except ValueError:
                num = None
            if num is not None and num >= 2:
                s = m_fu.group("base").strip()
                if follow_up is None:
                    follow_up = num
                changed = True
                continue
        m_cr = _CORRECTION_RE.match(s)
        if m_cr:
            s = m_cr.group("base").strip()
            if correction is None:
                correction = m_cr.group("sfx").upper()
            changed = True
            continue
    return s, follow_up, correction


_POLISH_DIACRITICS = set("\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c"
                         "\u0104\u0106\u0118\u0141\u0143\u00d3\u015a\u0179\u017b")

_POLISH_HINT_WORDS = {
    "i", "w", "na", "z", "ze", "do", "od", "po", "u",
    "burza", "morze", "las", "pole", "lato", "zima", "jesien",
    "wiosna", "noc", "dzien", "kobieta", "mezczyzna", "dziecko",
    "koscol", "wies", "miasto", "portret", "pejzaz", "martwa",
    "natura", "bitwa", "mloda", "stary", "stara", "mlody",
    "babie", "swit", "zachod", "wschod", "slonca",
}

_NON_POLISH_HINT_WORDS = {
    "the", "of", "and", "a", "an",
    "at", "by", "with", "near", "over", "under", "from", "through", "across", "along", "beside", "above", "below",
    "der", "die", "das", "und", "von", "am", "im",
    "la", "le", "les", "et", "un", "une", "du", "de", "des", "aux",
    "el", "los", "las", "y", "una",
    "il", "gli", "delle", "dei",
    "wave", "waves", "storm", "stormy", "weather", "night", "day", "woman", "girl", "boy", "man", "child",
    "portrait", "landscape", "seascape", "still", "life",
    "in", "on", "off", "into", "onto",
    "steam", "steamer", "paddlesteamer", "paddle", "sailboat", "sailing",
    "river", "rivers", "lake", "lakes", "stream", "pond", "sea", "ocean", "bay", "harbor", "harbour",
    "beach", "coast", "shore", "cliff", "cliffs", "rock", "rocks", "stone", "sand", "snow",
    "mountain", "mountains", "hill", "hills", "valley", "meadow", "meadows", "field", "fields",
    "forest", "woods", "garden", "gardens", "farm", "tree", "trees", "flower", "flowers",
    "cloud", "clouds", "sky", "sun", "moon", "dawn", "dusk", "morning", "evening", "afternoon", "twilight",
    "spring", "summer", "autumn", "winter", "fall",
    "village", "town", "city", "cottage", "house", "houses", "barn", "mill", "windmill",
    "bridge", "road", "path", "street", "market", "square",
    "church", "cathedral", "castle", "tower", "ruins",
    "drying", "nets", "net", "boat", "boats", "ship", "ships", "fisherman", "fishermen",
    "morgen", "abend", "sturm",
    "noche", "manana",
    "mare", "notte", "giorno",
}


_ENGLISH_SUFFIXES = (
    "ing", "tion", "sion", "ness", "ship",
    "ous", "ful", "less", "able", "ible", "ment",
)

_OVERLAP_WORDS = _POLISH_HINT_WORDS & _NON_POLISH_HINT_WORDS
_PL_ONLY = _POLISH_HINT_WORDS - _OVERLAP_WORDS
_NON_PL_ONLY = _NON_POLISH_HINT_WORDS - _OVERLAP_WORDS


def is_polish_title(text: str) -> bool:
    """Heurystyczna detekcja polskiego tytulu (bez zewnetrznych zaleznosci).

    - Polskie diakrytyki -> polski.
    - Angielskie koncowki (-ing, -tion, ...) -> obcy.
    - Slowa obcego pochodzenia (the, der, la, mountains, river, ...) przewazajace nad polskimi -> obcy.
    - Slowa pojawiajace sie w obu listach (np. 'las' po polsku = forest,
      po hiszpansku = rodzajnik) sa traktowane neutralnie - nie daja sygnalu.
    - W razie watpliwosci -> polski (najbezpieczniej dla standardowego usera PL).
    """
    if not text:
        return True
    for ch in text:
        if ch in _POLISH_DIACRITICS:
            return True
    low = text.lower()
    tokens = re.findall(r"[a-z\u00c0-\u024f]+", low)
    if not tokens:
        return True
    for t in tokens:
        if len(t) > 4 and t.endswith(_ENGLISH_SUFFIXES):
            return False
    non_pl = sum(1 for t in tokens if t in _NON_PL_ONLY)
    pl = sum(1 for t in tokens if t in _PL_ONLY)
    if non_pl > 0 and non_pl >= pl:
        return False
    return True
