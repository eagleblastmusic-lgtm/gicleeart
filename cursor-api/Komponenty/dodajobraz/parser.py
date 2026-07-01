"""Parsowanie nazwy pliku i pomocnicze funkcje (slug)."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

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


_ROLE_ONLY_SUFFIX_RE = re.compile(r"^(?:\(preview\)|full)\s*$", re.IGNORECASE)


def _split_artist_title_tolerant(left: str) -> tuple[str, str]:
    """Dzieli 'Artysta - Tytul' tolerujac brak spacji przy myslniku ('Bakhuizen -The ...')."""
    s = (left or "").strip()
    for sep in (" - ", " \u2013 ", " \u2014 ", " -", "- ", "-"):
        if sep in s:
            artist, title = s.split(sep, 1)
            artist, title = artist.strip(), title.strip()
            if artist and title:
                return artist, title
    raise ValueError(
        f"Nie mozna rozdzielic artysty i tytulu w: {left!r} (oczekiwano 'Artysta - Tytul')."
    )


def parse_filename(path: str | Path) -> tuple[str, str]:
    """'Ivan Aivazovsky - Nadciagajaca burza.jpg' -> ('Ivan Aivazovsky', 'Nadciagajaca burza').

    Separator: ' - ' (spacja mysjnik spacja). Gdy sufiks to tylko 'Full' / '(preview)',
    tytul jest wyciagany z lewej czesci (np. 'Artysta -Tytul - Full.webp').
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
            left, right = left.strip(), right.strip()
            if _ROLE_ONLY_SUFFIX_RE.match(right):
                artist, title = _split_artist_title_tolerant(left)
                return artist, f"{title} - {right}"
            return left, right
    raise ValueError(
        "Nazwa pliku musi miec format 'Artysta - Tytul obrazu.ext' (separator: ' - ')."
    )


_ARTIST_PAREN_SUFFIX_RE = re.compile(r"^(?P<core>.+?)\s+(\([^)]+\))\s*$")

_SURNAME_PARTICLES = {
    "da", "de", "del", "dell", "della", "di", "do", "dos", "du",
    "la", "le", "les", "lo",
    "van", "von", "der", "den", "ten", "ter",
    "af", "av",
    "el", "al",
    "st", "st.", "saint", "ste", "ste.",
    "mc", "mac",
    "y",
    "auf", "zur", "zum", "zu",
}


def artist_collection_title(artist: str) -> str:
    """'Ivan Aivazovsky' -> 'Aivazovsky, Ivan'. 'Vincent van Gogh' -> 'Van Gogh, Vincent'.

    'Pieter Bruegel (starszy)' -> 'Bruegel, Pieter (starszy)' (nawias na koncu nie jest nazwiskiem).
    """
    a = artist.strip()
    suffix = ""
    m = _ARTIST_PAREN_SUFFIX_RE.match(a)
    if m:
        core = m.group("core").strip()
        suffix = " " + m.group(2).strip()
    else:
        core = a
    parts = core.split()
    if len(parts) < 2:
        return a
    surname_start = len(parts) - 1
    while surname_start > 0 and parts[surname_start - 1].lower().rstrip(".") in _SURNAME_PARTICLES:
        surname_start -= 1
    surname = " ".join(parts[surname_start:])
    given = " ".join(parts[:surname_start])
    return f"{surname}, {given}{suffix}"


def _title_case_words(text: str) -> str:
    return " ".join(w.capitalize() for w in (text or "").split())


def normalize_catalog_artist_title(collection_title: str) -> tuple[str, str]:
    """'Gogh, Vincent van' / 'van Gogh, Vincent' -> ('Van Gogh', 'Vincent').

    Czastki nazwiska (van, von, ter, …) przy imieniu wracaja do nazwiska — jak w
    snippets/giclee-artist-catalog-name.liquid.
    """
    raw = (collection_title or "").strip()
    if ", " not in raw:
        return raw, ""
    surname, given = raw.split(", ", 1)
    surname = surname.strip()
    given = given.strip()
    given_words = given.split()
    if len(given_words) > 1:
        last = given_words[-1].lower().rstrip(".")
        if last in _SURNAME_PARTICLES:
            particle = given_words[-1]
            given = " ".join(given_words[:-1]).strip()
            surname = f"{particle} {surname}".strip()
    return _title_case_words(surname), _title_case_words(given)


def catalog_artist_sort_key(collection_title: str) -> tuple[str, str]:
    """Klucz sortowania A–Z po nazwisku (z czastkami), potem imieniu."""
    surname, given = normalize_catalog_artist_title(collection_title)
    return surname.casefold(), given.casefold()


def format_catalog_artist_title(collection_title: str) -> str:
    """'Gogh, Vincent van' -> 'Van Gogh, Vincent' (do wyswietlania i menu)."""
    surname, given = normalize_catalog_artist_title(collection_title)
    if given:
        return f"{surname}, {given}"
    return surname


def parse_artist_catalog_title(collection_title: str) -> tuple[str, str]:
    """'Dahl, Hans' -> ('Dahl', 'Hans'). 'Gogh, Vincent van' -> ('Van Gogh', 'Vincent')."""
    return normalize_catalog_artist_title(collection_title)


def artist_display_from_catalog_title(collection_title: str) -> str:
    """'Gogh, Vincent van' -> 'Vincent van Gogh'."""
    surname, given = parse_artist_catalog_title(collection_title)
    if given:
        return f"{given} {surname}".strip()
    return surname


def artist_collection_handle_from_title(collection_title: str) -> str:
    """'Dahl, Hans' -> 'hans-dahl' (slug z 'Imie Nazwisko')."""
    title = (collection_title or "").strip()
    if ", " not in title:
        return slugify(title)
    surname, given = title.split(", ", 1)
    surname = surname.strip()
    given = given.strip()
    display = f"{given} {surname}".strip() if given else surname
    return slugify(display)


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
# Instalacja / wariant wizualny: 'Tytul I1', 'Tytul - I2' (od I1, nie tylko I2+).
_INSTALLMENT_RE = re.compile(r"^(?P<base>.*?)(?:\s*-\s*)?I(?P<num>\d+)\s*$", re.IGNORECASE)

# Sufiks korekty kolorystycznej: 'WK' (wstepna) lub 'KK' (koncowa). Tylko VERSALIKAMI,
# zeby przypadkiem nie obciac slowa typu "Wk\u00f3l Trasy" (gdyby ktos uzyl maly liter).
# Akceptowane warianty na koncu tytulu (po podziale 'Artysta - Tytul'):
#   'Tytul KK', 'Tytul WK'         (separator: spacja)
#   'Tytul - KK', 'Tytul - WK'     (separator: ' - ' z myslnikiem ASCII / en-dash / em-dash)
_CORRECTION_RE = re.compile(
    r"^(?P<base>.*?)\s+(?:[-\u2013\u2014]\s+)?(?P<sfx>WK|KK)\s*$"
)

# Opcjonalny separator przed sufiksem (ASCII / en-dash / em-dash).
_META_SEP = r"(?:\s*[-\u2013\u2014]\s*)?"

# Podglad katalogowy / menu: 'Tytul - (preview)' lub 'Tytul (preview)'.
_PREVIEW_RE = re.compile(
    rf"^(?P<base>.*?){_META_SEP}\(preview\)\s*$", re.IGNORECASE
)
# Pelna rozdzielczosc do galerii produktu: 'Tytul - Full' lub 'Tytul Full'.
_FULL_RE = re.compile(rf"^(?P<base>.*?){_META_SEP}Full\s*$", re.IGNORECASE)
_MOCKUP_VARIANTS = ("CZB", "CZCZ")
_MOCKUP_RE = re.compile(
    rf"^(?P<base>.*?){_META_SEP}\(mockup\)"
    rf"(?:{_META_SEP}(?P<variant>{'|'.join(_MOCKUP_VARIANTS)}))?\s*$",
    re.IGNORECASE,
)

IMAGE_ROLE_PREVIEW = "preview"
IMAGE_ROLE_FULL = "full"
IMAGE_ROLE_MOCKUP = "mockup"

FOLLOW_UP_KIND_F = "F"
FOLLOW_UP_KIND_I = "I"


def preview_alt_text(artist: str, base_title: str) -> str:
    return f"{artist} - {base_title} (preview)"


def full_alt_text(artist: str, base_title: str) -> str:
    return f"{artist} - {base_title} (Full)"


def mockup_alt_text(artist: str, base_title: str, *, name_suffix: str = "") -> str:
    sfx = (name_suffix or "").strip().upper()
    if sfx:
        return f"{artist} - {base_title} - (mockup) - {sfx}"
    return f"{artist} - {base_title} (mockup)"


def installment_alt_text(artist: str, base_title: str, index: int) -> str:
    return f"{artist} - {base_title} (I{index})"


def alt_is_catalog_preview(alt: str | None) -> bool:
    return "(preview)" in (alt or "").lower()


def alt_is_gallery_full(alt: str | None) -> bool:
    a = (alt or "").lower()
    return "(full)" in a or a.rstrip().endswith(" full")


def alt_is_mockup(alt: str | None) -> bool:
    return "(mockup)" in (alt or "").lower()


_MOCKUP_REF_RE = re.compile(r"[-_ (]mockup[-_. )]", re.IGNORECASE)


def image_ref_is_mockup(ref: str | None) -> bool:
    """True gdy alt lub URL pliku wskazuje na mockup (takze `_mockup_` w CDN Shopify)."""
    if not ref:
        return False
    if alt_is_mockup(ref):
        return True
    return bool(_MOCKUP_REF_RE.search(ref))


def _variant_token_in_mockup_ref(upper: str, variant: str) -> bool:
    if variant not in upper:
        return False
    for token in (
        f"- {variant}",
        f"_{variant}",
        f"-{variant}",
        f" {variant}",
        f"({variant})",
    ):
        if token in upper:
            return True
    return upper.endswith(variant) or upper.endswith(f"{variant}.WEBP")


def mockup_suffixes_in_image_refs(
    refs: Iterable[str | None],
    *,
    variants: tuple[str, ...] = _MOCKUP_VARIANTS,
) -> set[str]:
    """Warianty mockupu (CZB/CZCZ) z altow lub URL-i plikow."""
    found: set[str] = set()
    for ref in refs:
        if not image_ref_is_mockup(ref):
            continue
        upper = (ref or "").upper()
        for variant in sorted(variants, key=len, reverse=True):
            if _variant_token_in_mockup_ref(upper, variant):
                found.add(variant)
    return found


def mockup_suffixes_in_product_images(
    images: list[dict[str, Any]],
    *,
    variants: tuple[str, ...] = _MOCKUP_VARIANTS,
) -> set[str]:
    """Warianty mockupu obecne w galerii produktu (alt + src kazdego zdjecia)."""
    refs: list[str | None] = []
    for im in images:
        refs.append(im.get("alt"))
        refs.append(im.get("src"))
    return mockup_suffixes_in_image_refs(refs, variants=variants)


def mockup_suffixes_in_alts(alts: list[str | None], *, variants: tuple[str, ...] = _MOCKUP_VARIANTS) -> set[str]:
    """Zwraca zestaw wariantow mockupu obecnych w altach (np. {'CZB', 'CZCZ'})."""
    return mockup_suffixes_in_image_refs(alts, variants=variants)


def alt_is_gallery_excluded(alt: str | None) -> bool:
    """Media ukryte w galerii PDP (tylko preview)."""
    return "(preview)" in (alt or "").lower()


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


def parse_title_metadata(
    title: str,
) -> tuple[str, int | None, str | None, str | None, str | None]:
    """Iteracyjnie odlupuje z konca tytulu sufiksy meta.

    Zwraca (base_title, follow_up_number, correction_suffix, image_role, follow_up_kind).
    follow_up_kind: None | 'F' | 'I' (gdy follow_up_number ustawione).
    image_role: None | 'preview' | 'full' | 'mockup'.

    Przyklady:
      'Babie lato I1'                 -> ('Babie lato', 1,    None, None, 'I')
      'Babie lato - (mockup)'         -> ('Babie lato', None, None, 'mockup', None)
      'Babie lato - (mockup) - CZB'   -> ('Babie lato', None, None, 'mockup', None)
      'Babie lato F2'                 -> ('Babie lato', 2,    None, None, 'F')
    """
    if not title:
        return title, None, None, None, None
    s = title.strip()
    follow_up: int | None = None
    follow_up_kind: str | None = None
    correction: str | None = None
    image_role: str | None = None
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
                    follow_up_kind = FOLLOW_UP_KIND_F
                changed = True
                continue
        m_in = _INSTALLMENT_RE.match(s)
        if m_in:
            try:
                num = int(m_in.group("num"))
            except ValueError:
                num = None
            if num is not None and num >= 1:
                s = m_in.group("base").strip()
                if follow_up is None:
                    follow_up = num
                    follow_up_kind = FOLLOW_UP_KIND_I
                changed = True
                continue
        m_cr = _CORRECTION_RE.match(s)
        if m_cr:
            s = m_cr.group("base").strip()
            if correction is None:
                correction = m_cr.group("sfx").upper()
            changed = True
            continue
        m_pr = _PREVIEW_RE.match(s)
        if m_pr:
            s = m_pr.group("base").strip()
            if image_role is None:
                image_role = IMAGE_ROLE_PREVIEW
            changed = True
            continue
        m_fl = _FULL_RE.match(s)
        if m_fl:
            s = m_fl.group("base").strip()
            if image_role is None:
                image_role = IMAGE_ROLE_FULL
            changed = True
            continue
        m_mk = _MOCKUP_RE.match(s)
        if m_mk:
            s = m_mk.group("base").strip()
            if image_role is None:
                image_role = IMAGE_ROLE_MOCKUP
            changed = True
            continue
    return s, follow_up, correction, image_role, follow_up_kind


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
