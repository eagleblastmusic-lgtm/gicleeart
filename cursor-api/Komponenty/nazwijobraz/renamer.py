"""Bezpieczne sklejanie i nadawanie nazw plikom obrazow."""

from __future__ import annotations

import re
from pathlib import Path

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = frozenset(
    {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)

# Rozszerzenia obrazow - usuwamy je z tytulu, gdyby wpadly tam przez nazwe pliku.
_IMAGE_EXTS = (
    ".jpg", ".jpeg", ".jpe", ".jfif",
    ".png", ".webp", ".gif", ".bmp",
    ".tif", ".tiff", ".heic", ".heif",
    ".avif", ".svg",
)
_EXT_TAIL_RE = re.compile(
    r"(?:[\s._-]*(?:" + "|".join(re.escape(e[1:]) for e in _IMAGE_EXTS) + r"))+\s*$",
    re.IGNORECASE,
)

# Slowa zostawiane mala litera w srodku tytulu (English / international).
_SMALL_WORDS = frozenset(
    {
        "a", "an", "the",
        "and", "as", "but", "for", "if", "nor", "or", "so", "yet",
        "at", "by", "in", "of", "off", "on", "per", "to", "up", "via",
        "from", "into", "onto", "upon", "with", "over", "under",
        "vs", "vs.", "v",
        "de", "la", "le", "les", "du", "des", "et", "au", "aux",
        "von", "van", "der", "den", "zu", "im", "am",
        "di", "del", "della", "il", "lo", "gli", "i",
        "y", "el", "los", "las",
    }
)
_ROMAN_RE = re.compile(r"^[IVXLCDM]+$")

# Litery typowo obcojezyczne (umlauty, akcenty, eszett, znaki nordyckie itp.).
# Obecnosc takich znakow oznacza ze tytul najprawdopodobniej NIE jest po angielsku
# i Title Case bylby bledny (np. niemieckie "stürmischer" musi pozostac z malej).
_NON_ENGLISH_LETTER_RE = re.compile(
    r"[äöüÄÖÜßéèêëàâçîïôûùÿñœæåØøÅÆÉÈÊËÀÂÇÎÏÔÛÙŸÑŒĄĆĘŁŃÓŚŹŻąćęłńóśźż]"
)
# Trailing junk typu ",,1815" / " - 1815" - rok przyklejony do koncowki.
_TRAILING_YEAR_JUNK_RE = re.compile(r"[\s,;:._-]*\b(?:15|16|17|18|19|20)\d{2}\s*$")

# Prefiks strony pliku Wikipedia / Commons (File:, Image:, Media:).
_WIKI_NAMESPACE_PREFIX_RE = re.compile(
    r"^(?:file|image|media|archivo|datei|fichier|plik)\s*[:_\-]+\s*",
    re.IGNORECASE,
)
_WIKI_NAMESPACE_ONLY_RE = re.compile(
    r"^(?:file|image|media)\s*:?\s*$",
    re.IGNORECASE,
)


def _looks_non_english(text: str) -> bool:
    """Heurystyka: czy tekst zawiera znaki spoza standardowego angielskiego."""
    return bool(_NON_ENGLISH_LETTER_RE.search(text or ""))


def _strip_extension_artifacts(text: str) -> str:
    """Usun nadmiarowe '.jpg', '_jpg', ' jpeg' itd. z konca/poczatku tekstu."""
    if not text:
        return text
    prev = None
    cur = text
    while cur != prev:
        prev = cur
        cur = _EXT_TAIL_RE.sub("", cur).rstrip(" .-_")
    return cur


def _capitalize_word(word: str) -> str:
    if not word:
        return word
    # Liczby rzymskie (II, III, IV, IX, MMXXIV) - tylko gdy >=2 znaki, zeby
    # nie podmieniac slow takich jak 'i' albo 'v'.
    if len(word) >= 2 and _ROMAN_RE.match(word.upper()):
        return word.upper()
    # Krotkie skroty all-caps: USA, NYC, IBM, NFL.
    if word.isupper() and 2 <= len(word) <= 4:
        return word
    # ALL-CAPS dluzsze niz 4 (BATHING, ROCKS) - traktujemy jak zwykly tekst i
    # przepuszczamy przez Title Case ponizej.
    if word.isupper():
        word = word.lower()
    # Mieszany case wpisany swiadomie (MoMA, McDonald, iPad) - zachowaj.
    # Wymagamy obecnosci zarowno wielkich, jak i malych liter, plus aby wielka
    # litera pojawiala sie po pierwszym znaku.
    elif (
        len(word) >= 2
        and any(c.isupper() for c in word[1:])
        and any(c.islower() for c in word)
    ):
        return word[:1].upper() + word[1:]
    parts = re.split(r"(['\u2019\-/])", word)
    out: list[str] = []
    for k, piece in enumerate(parts):
        if piece in ("'", "\u2019", "-", "/"):
            out.append(piece)
            continue
        prev_sep = parts[k - 1] if k > 0 else ""
        if prev_sep in ("'", "\u2019") and piece and len(piece) <= 2:
            out.append(piece.lower())
        else:
            out.append(piece[:1].upper() + piece[1:].lower() if piece else piece)
    return "".join(out)


def strip_wiki_namespace_prefix(text: str) -> str:
    """Usun prefiks strony pliku Wikipedia/Commons (File:, Image:, Media:).

    Przyklady:
        "File: The Wave" -> "The Wave"
        "File" / "File:" -> ""
    """
    s = (text or "").strip()
    if not s:
        return ""
    while True:
        new = _WIKI_NAMESPACE_PREFIX_RE.sub("", s, count=1).strip()
        if new == s:
            break
        s = new
    if _WIKI_NAMESPACE_ONLY_RE.match(s):
        return ""
    return s


def format_artwork_title(text: str) -> str:
    """Sformatuj tytul obrazu w Title Case z poprawnym traktowaniem malych slow.

    Pierwsze i ostatnie slowo zawsze wielka litera; w srodku 'of/in/the/...'
    pisane mala. Zachowuje liczby rzymskie i krotkie skroty (NYC, MoMA).

    UWAGA: dla tytulow zawierajacych znaki obcojezyczne (umlauty, eszett,
    akcenty itp.) NIE zmieniamy kapitalizacji - inaczej zniszczylibysmy
    poprawne formy typu "Raddampfer in stürmischer See" (niemiecki: tylko
    rzeczowniki z duzej, przymiotniki z malej).
    """
    s = (text or "").strip()
    if not s:
        return ""
    s = strip_wiki_namespace_prefix(s)
    if not s:
        return ""
    s = _strip_extension_artifacts(s)
    # Wycinamy "rok przyklejony przez przecinek/podkreslnik" typu ",,1815".
    s = _TRAILING_YEAR_JUNK_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" .-_:|,")
    if not s:
        return ""

    # Tytuly obcojezyczne - zachowaj oryginalna kapitalizacje i wroc.
    if _looks_non_english(s):
        return s

    # Tokenizuj, ale zachowaj separatory (spacje, : ; , ! ?).
    tokens = re.findall(r"[^\s]+|\s+", s)
    word_indices = [i for i, t in enumerate(tokens) if not t.isspace()]
    if not word_indices:
        return s
    first_idx = word_indices[0]
    last_idx = word_indices[-1]

    out: list[str] = []
    for i, tok in enumerate(tokens):
        if tok.isspace():
            out.append(tok)
            continue
        # Czesto na koncu tokenu jest interpunkcja, np. "louveciennes,"
        m = re.match(r"^(.*?)([\.,;:!\?\)\]\}'\"\u201d\u2019]*)$", tok, re.DOTALL)
        body = m.group(1) if m else tok
        tail = m.group(2) if m else ""
        m2 = re.match(r"^([\(\[\{'\"\u201c\u2018]*)(.*)$", body, re.DOTALL)
        head = m2.group(1) if m2 else ""
        core = m2.group(2) if m2 else body
        low = core.lower()
        if i != first_idx and i != last_idx and low in _SMALL_WORDS:
            shaped = low
        else:
            shaped = _capitalize_word(core)
        out.append(f"{head}{shaped}{tail}")
    return "".join(out)


def sanitize_for_filename(s: str) -> str:
    """Wytnij znaki zabronione, zwin spacje, przytnij konce."""
    s = (s or "").strip()
    if not s:
        return ""
    s = _INVALID.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if s.upper() in _RESERVED:
        s = f"_{s}"
    return s


def append_suffix_to_original_filename(filename: str, suffix: str) -> str:
    """Dokleja ' - Sufiks' przed rozszerzeniem do BIEZACEJ nazwy pliku (np. przed wyszukiwaniem).

    Gdy stem juz konczy sie na ' - Sufiks' (bez rozrozniania wielkosci liter), zwraca `filename`
    bez zmian. Pusty sufiks -> bez zmian.
    """
    suf = sanitize_for_filename(_strip_extension_artifacts(suffix or ""))
    if not suf:
        return filename
    p = Path(filename)
    stem, ext = p.stem, p.suffix.lower() or ".jpg"
    tail = f" - {suf}"
    if stem.lower().endswith(tail.lower()):
        return filename
    new_stem = f"{stem}{tail}"
    max_stem = 255 - len(ext)
    if len(new_stem) > max_stem:
        new_stem = new_stem[:max_stem].rstrip(" .")
    return f"{new_stem}{ext}"


def build_new_name(
    artist: str,
    title: str,
    original_path: str | Path,
    *,
    suffix: str = "",
) -> str:
    """Zwraca nowa nazwe (bez sciezki), w formacie 'Artist - Title[ - Suffix].ext'.

    `suffix` (opcjonalny) - dowolny tekst doklejany na koncu stem (przed
    rozszerzeniem), np. 'Mockup', 'Print', 'Hi-Res'. Sufiks jest sanitzyowany
    z znakow zabronionych w nazwie pliku. Pusty / sam whitespace = brak sufiksu.
    """
    p = Path(original_path)
    artist_clean = sanitize_for_filename(artist)
    # Najpierw wytnij ewentualne ".jpg" wpadajace do tytulu, potem Title Case.
    title_norm = format_artwork_title(_strip_extension_artifacts(title))
    title_clean = sanitize_for_filename(title_norm)
    suffix_clean = sanitize_for_filename(_strip_extension_artifacts(suffix or ""))
    ext = p.suffix.lower() or ".jpg"
    if artist_clean and title_clean:
        stem = f"{artist_clean} - {title_clean}"
    elif title_clean:
        stem = title_clean
    elif artist_clean:
        stem = artist_clean
    else:
        stem = p.stem
    if suffix_clean:
        stem = f"{stem} - {suffix_clean}"
    # Windows: max 255 znakow w nazwie pliku.
    max_stem = 255 - len(ext)
    if len(stem) > max_stem:
        stem = stem[:max_stem].rstrip(" .")
    return f"{stem}{ext}"


def is_already_named(artist: str, title: str, current_filename: str) -> bool:
    """Czy biezaca nazwa pliku zawiera juz autora i tytul (bez wzgledu na drobne roznice)."""
    cur = Path(current_filename).stem.lower()
    a = sanitize_for_filename(artist).lower()
    t = sanitize_for_filename(title).lower()
    return bool(a) and bool(t) and a in cur and t in cur


def rename_file(original_path: str | Path, new_name: str, *, overwrite: bool = False) -> Path:
    """Zmienia nazwe pliku na new_name (w tym samym katalogu).

    Zwraca nowa sciezke. Rzuca FileExistsError jezeli target istnieje a overwrite=False.
    """
    src = Path(original_path)
    if not src.is_file():
        raise FileNotFoundError(f"Plik nie istnieje: {src}")
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Pusta nowa nazwa pliku.")
    dst = src.with_name(new_name)
    if dst == src:
        return src
    if dst.exists() and not overwrite:
        raise FileExistsError(f"Plik docelowy juz istnieje: {dst.name}")
    src.rename(dst)
    return dst
