"""Laczy sygnaly z roznych zrodel (Google Lens, Wikipedia, Google text, nazwa pliku)
i wybiera najbardziej wiarygodny tytul obrazu.

Algorytm: kazdy kandydat dostaje wage zalezna od zrodla. Dodatkowo kandydaci
zgodni tokenowo z hintem z nazwy pliku oraz pojawiajacy sie w wielu zrodlach
otrzymuja bonusy. Ta sama "kanoniczna" forma (znormalizowana po tokenach
liczy sie raz - laczone sa rozne pisownie).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .renamer import _strip_extension_artifacts, format_artwork_title

_TOKEN_RE = re.compile(r"[A-Za-z\u00C0-\u017F\u0180-\u024F]+")
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "of", "in", "on", "at", "by", "for", "to", "with",
        "and", "or", "from", "into", "near", "over", "under", "vs",
    }
)
# Wagi zrodel - filename ma absolutny priorytet (uzytkownik nazywa pliki swiadomie).
# Inne zrodla pelnia role weryfikacji. W praktyce 2-3 zrodla z multi-source
# bonusem (x1.5/x2.0) potrafily przebic filename, mimo ze user wpisal czysty
# tytul w nazwie pliku (np. "Andreas_Achenbach_Am_Strand_von_Scheveningen_1893")
# - dlatego BUMP filename do 25, plus +4 za kazdy zgodny token (bylo +1).
# Wynikowo filename = "Am Strand von Scheveningen" daje 25 + 4*4 = 41 punktow,
# czego nawet 3 zrodla "Ludolf Bakhuizen" (4+4+5) * 2 = 26 nie przebiją.
#
# UWAGA: visual search rozbity na 3 osobne zrodla (lens / yandex / bing) -
# kazdy reverse-image-engine to NIEZALEZNY sygnal o pikselach obrazu, wiec
# powinien liczyc sie jak osobny "votant", nie jak jeden zlepiony "lens".
# Dzieki temu jak Lens zwroci "Indian Summer", Yandex "Babie Lato", Bing nic,
# resolver widzi 2 niezalezne wizualne potwierdzenia (waga 8+8 + multi-source
# bonus = ~24), a nie jedno (waga 4) jak wczesniej.
_SOURCE_WEIGHT = {
    "filename": 25,
    "lens": 8,        # Google Lens - reverse image (precyzyjne dla pikseli)
    "yandex": 8,      # Yandex Images - reverse image (mocny dla muzealnych)
    "wikiart": 7,     # WikiArt - structured (artist + title + year z URL slug)
    "bing": 6,        # Bing Visual - reverse image (mniej dokladny)
    "met": 6,         # The Met - rzeczywista kolekcja muzealna
    "artic": 6,       # Art Institute of Chicago - jw.
    "wikidata": 5,    # Wikidata - struktur. dane o obrazach
    "wiki": 4,        # Wikipedia OpenSearch
    "commons": 4,     # Wikimedia Commons (kategorie/galleries)
    "art_sites": 3,   # agregat: invaluable/mutualart/artnet/sothebys/...
    "google": 2,      # Google text - tylko fallback
}
# Bonus za kazdy token zgodny z hint-em z nazwy pliku (per token).
_FILENAME_OVERLAP_BONUS = 4

# Generyczne SLOWA, ktore w nazwach plikow nic nie wnosza ("Obraz.jpg" =
# polskie "painting", "Picture.jpg" = generyczne EN). Sa odrzucane na 2 sposoby:
#   1) Filtr `_is_acceptable` odrzuca caly kandydat zaczynajacy sie od takiego slowa.
#   2) `_meaningful_hint_tokens` wycina je z hint_tokens, dzieki czemu nie
#      generuja FAKE bonusu +4 dla kandydatow z innych zrodel zawierajacych
#      to samo generyczne slowo.
_GENERIC_FILENAME_TOKENS = frozenset(
    {
        # polskie generyki
        "obraz", "obrazek", "rysunek", "zdjecie", "zdjęcie",
        "foto", "fotka", "fotografia", "fotografie",
        "skan", "skany", "malarstwo", "malowidlo", "malowidło",
        "bez", "tytul", "tytulu", "tytułu",
        "noname", "brak", "nieznany", "nieznana",
        # angielskie generyki
        "image", "picture", "photo", "photograph", "scan",
        "untitled", "unknown", "drawing", "painting",
        # rosyjskie / cyrylica - "образ" trafial w Wikipedii (Q12797704 = ikona),
        # "картина" = obraz, "рисунок" = rysunek, "фото" = foto, "малярство".
        "образ", "картина", "рисунок", "фото", "фотография", "малярство",
        # camera/scanner defaults
        "img", "dsc", "dscn", "dscf", "pic", "pict",
        # dodatkowe oczywiste
        "file", "media",
    }
)


# Bloki Unicode, ktorych obecnosc oznacza ze nie umiemy sensownie tokenizowac
# tekstu (CJK = japonski/chinski/korean, arabic, hebrew, devanagari ...).
# Dla takich tekstow zwracamy fail-safe `is_generic_title=False` zeby nie
# odrzucac legitnych tytulow (np. "インディアン・サマー" = japonskie "Indian Summer").
_NON_LATIN_CYRILLIC_RE = re.compile(
    r"[\u3040-\u309F"          # hiragana
    r"\u30A0-\u30FF"           # katakana
    r"\u4E00-\u9FFF"           # CJK Unified Ideographs
    r"\uAC00-\uD7AF"           # hangul (korean)
    r"\u0600-\u06FF"           # arabic
    r"\u0590-\u05FF"           # hebrew
    r"\u0900-\u097F"           # devanagari
    r"]"
)


def is_generic_title(text: str) -> bool:
    """True gdy `text` po sprzataniu skladaja sie tylko z generycznych slow.

    Slowo "Obraz" -> True. "Babie Lato" -> False. "Picture of Mona Lisa" -> False
    (bo "mona"/"lisa" sa znaczace).

    Dla tekstow w CJK / arabskim / hebrajskim / devanagari -> False (fail-safe;
    nie umiemy tokenizowac, wiec lepiej zachowac potencjalnie poprawny tytul).

    Uzywane w gui.py do filtrowania wp_en/cm_en/wd_en (english_title), zeby
    Wikipedia/Commons/Wikidata zwracajace "Obraz" jako EN title nie podmienialy
    poprawnego wyniku z Lens/Yandex.
    """
    if not text:
        return True
    s = text.strip()
    if not s:
        return True
    # Fail-safe dla CJK/arabic/hebrew/devanagari - nie tokenizujemy, wiec
    # nie wiemy czy generic. Domyslnie zachowujemy.
    if _NON_LATIN_CYRILLIC_RE.search(s):
        return False
    import re as _re
    toks_lower = [
        t.lower()
        for t in _re.findall(r"[A-Za-z\u00C0-\u017F\u0180-\u024F\u0400-\u04FF]+", s)
        if len(t) >= 2
    ]
    if not toks_lower:
        return True   # sam interpunkcja / liczby
    meaningful = [t for t in toks_lower if t not in _GENERIC_FILENAME_TOKENS and t not in _STOPWORDS]
    return not meaningful


@dataclass
class _CandidateBucket:
    canonical: str  # tokens po lowercase, sortowane chronologicznie
    forms: list[str] = field(default_factory=list)  # widziane warianty pisowni
    sources: Counter = field(default_factory=Counter)
    score: float = 0.0


def _tokens(text: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text or "")
        if len(t) >= 2 and t.lower() not in _STOPWORDS
    ]


def _canonical(text: str) -> str:
    return " ".join(_tokens(text))


def _strip_artist(text: str, artist: str) -> str:
    if not artist or not text:
        return text
    parts = [re.escape(p) for p in artist.split() if p]
    if not parts:
        return text
    name_re = r"\b" + r"[\s\-]+".join(parts) + r"\b"
    rev_re = r"\b" + r"[\s\-]+".join(reversed(parts)) + r"\b"
    out = re.sub(rf"\bby\s+{name_re}\b", "", text, flags=re.IGNORECASE)
    out = re.sub(name_re, "", out, flags=re.IGNORECASE)
    out = re.sub(rev_re, "", out, flags=re.IGNORECASE)
    out = re.sub(r"^[\-\u2013\u2014:|,\s]+|[\-\u2013\u2014:|,\s]+$", "", out)
    out = re.sub(r"\s+", " ", out).strip(" -:|,.")
    return out or text


# Smieci typowe w tytulach z internetu (galerie, sklepy, drukarnie)
_NOISE_SUFFIX_RE = re.compile(
    r"\b("
    r"wikipedia|wikimedia|wikidata|wiki\s*commons|fine\s+art\s+america|"
    r"saatchi\s+art|artstation|tate|moma|the\s+met|metropolitan\s+museum|"
    r"national\s+gallery|sotheby'?s|christie'?s|artnet|wikiart|"
    r"getty\s+images|alamy|shutterstock|pinterest|reddit|"
    r"invaluable|mutualart|art\.com|pixels\.com|findartinfo|"
    r"bruun.?rasmussen|picryl|google\s+arts(?:\s+&\s+culture)?|"
    r"wallpaper(?:s)?|hd\s+wallpaper|stock\s+photo|poster|print|"
    r"canvas\s+print|reproduction|reprodukcja|jpg|jpeg|png|webp"
    r")\b.*$",
    re.IGNORECASE,
)

# Marketplace / e-commerce prefiksy ktore zatruwaja kandydatow z visual search.
# Tytul zaczynajacy sie od takiego prefiksu (np. "Amazon.com: Ivan...") jest
# odrzucany - bo po _clean_for_pick zostalby smietnik typu "Amazon.com: Ivan".
_MARKETPLACE_PREFIX_RE = re.compile(
    r"^\s*("
    r"amazon(?:\.com|\.de|\.co\.uk)?|ebay|aliexpress|allegro|etsy|wildberries|"
    r"yandex\s+market|ozon|art\.com|pixels\.com|saatchi(?:\s+art)?|"
    r"redbubble|zazzle|shutterstock|alamy|getty|fine\s+art\s+america|"
    r"orca\s+art|wur\s*bu|art\s*direct|artcanvas|shop|store"
    r")\b\s*[:\-\u2013\u2014|]",
    re.IGNORECASE,
)

# Suffix typu " (1889), by Ivan Aïvazovski" / ", de Ivan Aïvazovski" /
# " von Author" / " by Author" - czesto wystepujacy w opisach plikow Commons
# (descriptor != title) w roznych jezykach (en/fr/de/it/es/pt/...).
_BY_PREP = r"(?:by|de|du|von|del|della|por|bei)"
_AUTHOR_DESCRIPTOR_SUFFIX_RE = re.compile(
    r"\s*[(]?\s*\d{4}\s*[)]?\s*,?\s*" + _BY_PREP +
    r"\s+[\w\u00C0-\u017F\u0180-\u024F.\s\-']+$",
    re.IGNORECASE,
)
_BY_AUTHOR_SUFFIX_RE = re.compile(
    r"\s*,?\s*" + _BY_PREP + r"\s+[\w\u00C0-\u017F\u0180-\u024F.\s\-']+$",
    re.IGNORECASE,
)
# Sufiks samego roku w nawiasach na koncu - "Tempest (1855)" -> "Tempest".
# Zachowujemy tylko gdy w nawiasie sa NIE-cyfry (typowo disambiguator
# typu "(painting)" - to przekazujemy do wikipedii nieoddzielony).
_YEAR_PAREN_SUFFIX_RE = re.compile(r"\s*\((?:1[0-9]|20)\d{2}\)\s*$")
_TRAILING_YEAR_RE = re.compile(r"\s*,?\s*\b(?:1[0-9]|20)\d{2}\s*$")


def _clean_for_pick(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    # Marketplace prefix ("Amazon.com:", "eBay -", "Etsy |") = caly tytul jest
    # listingiem produktu, nie tytulem dziela. Odrzucamy do pustego.
    if _MARKETPLACE_PREFIX_RE.match(s):
        return ""
    s = re.split(r"\s[\-\u2013\u2014|:]\s", s)[0].strip()
    s = s.strip("\"'\u201c\u201d\u2018\u2019")
    s = _NOISE_SUFFIX_RE.sub("", s).strip(" -:|,.")
    s = _strip_extension_artifacts(s)
    # Wytnij descriptor "(1889), by Ivan Aïvazovski" / ", by Author" -
    # czesto wystepuje w Commons descriptions a NIE jest tytulem dziela.
    s = _AUTHOR_DESCRIPTOR_SUFFIX_RE.sub("", s)
    s = _BY_AUTHOR_SUFFIX_RE.sub("", s)
    # Wytnij sam rok w nawiasach na koncu "Tempest (1855)" -> "Tempest"
    # ale nie ruszamy nawiasow z tekstem typu "(painting)".
    s = _YEAR_PAREN_SUFFIX_RE.sub("", s)
    s = _TRAILING_YEAR_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" -:|,.")
    return s


def clean_title_descriptor(raw: str) -> str:
    """Wycina z tytulu typowe descriptor-suffixy: ", by Author", " (1889)",
    "(1889), by Author", "by Author", oraz noise-suffixy ("Wikipedia", "jpg" itp.)
    BEZ skracania na " - " (zachowuje wieloczlonowe tytuly typu "Self-Portrait").

    Uzywane do oczyszczenia `wp_en`/`cm_en`/`wd_en` (english_title z text-source)
    PRZED uzyciem ich w `[lang] swap` jako finalnego title - bez tego Commons
    zwracajacy 'The wave (1889), by Ivan Aïvazovski' jako EN trafial w nazwe pliku.
    """
    s = (raw or "").strip()
    if not s:
        return ""
    s = s.strip("\"'\u201c\u201d\u2018\u2019")
    s = _NOISE_SUFFIX_RE.sub("", s).strip(" -:|,.")
    s = _strip_extension_artifacts(s)
    s = _AUTHOR_DESCRIPTOR_SUFFIX_RE.sub("", s)
    s = _BY_AUTHOR_SUFFIX_RE.sub("", s)
    s = _YEAR_PAREN_SUFFIX_RE.sub("", s)
    s = _TRAILING_YEAR_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" -:|,.")
    return s


def clean_query_seed(raw: str) -> str:
    """Sanitizuje surowy tytul z visual search do uzycia jako query_seed.

    Wycina " - Wikipedia", " | YouTube", " - Pinterest", noise suffixes,
    rozszerzenia obrazow. ZACHOWUJE nawiasy disambiguacyjne typu "(painting)" -
    sa kluczowe dla wikipedii (bez nich query "Indian Summer" trafia w sezon
    klimatyczny zamiast w obraz Chelmonskiego).

    Przyklady:
        "Indian Summer (painting) - Wikipedia" -> "Indian Summer (painting)"
        "BABIE LATO - Józef Chełmoński 500CFA"  -> "BABIE LATO"
    """
    s = _clean_for_pick(raw)
    s = re.sub(r"\s+", " ", s).strip(" -:|,.")
    return s


_REJECT_FIRST_TOKENS = frozenset(
    {
        # Strony plikow z Wikipedii / Commons.
        "file", "image", "media",
        # Generyczne smieci EN.
        "untitled", "scan", "img", "dsc", "dscn", "dsc_", "img_",
        "picture", "photo", "photograph", "drawing", "unknown", "noname",
        # Generyczne smieci PL - dla plikow typu "Obraz.jpg", "Rysunek.jpg",
        # "Zdjecie.jpg", "Foto.jpg" itp. Bez tego "Obraz" trafial w wikipedii
        # (Q12797704 - rosyjska "икона/образ") i wygrywal jako wynik.
        "obraz", "obrazek", "rysunek", "zdjecie", "zdjęcie",
        "foto", "fotka", "fotografia", "skan", "malarstwo",
        "painting",  # angielski "painting" jako single-word title to tez generyk
    }
)
_REJECT_REGEX = re.compile(
    r"^\s*(?:file|image|media)\s*[:_-]",
    re.IGNORECASE,
)


def _meaningful_hint_tokens(hint: str) -> set[str]:
    """Tokeny z nazwy pliku z odsianymi STOPWORDS i `_GENERIC_FILENAME_TOKENS`.

    Sluzy do liczenia `_FILENAME_OVERLAP_BONUS`. Jesli nazwa pliku to "Obraz.jpg",
    `_tokens` da `["obraz"]`, a po wycieciu generykow zostanie pusty set, wiec
    zaden kandydat z innego zrodla nie dostanie sztucznego bonusu za "obraz".
    """
    return {t for t in _tokens(hint) if t not in _GENERIC_FILENAME_TOKENS}


def _is_acceptable(text: str) -> bool:
    if not text:
        return False
    if _REJECT_REGEX.match(text):
        return False
    toks = _tokens(text)
    if not toks:
        return False
    if toks[0] in _REJECT_FIRST_TOKENS:
        return False
    # Min 2 znaczace slowa albo jedno >= 5 znakow (np. "Sunflowers")
    if len(toks) >= 2:
        return True
    return len(toks[0]) >= 5


# Sygnal "to wyglada na imie i nazwisko OSOBY, nie tytul obrazu".
# Stosujemy gdy nie ma zadnego overlapu z nazwa pliku - patrz `resolve_title`.
_PERSON_NAME_FUNCTION_WORDS = frozenset(
    {
        "the", "of", "in", "at", "on", "by", "with", "for", "to",
        "and", "or", "from", "into", "near", "over", "under",
        "der", "die", "das", "ein", "eine", "und", "von", "zu", "am", "im",
        "le", "la", "les", "du", "des", "et", "au", "aux",
        "il", "lo", "gli", "del", "della",
    }
)

# Slowa typowo wystepujace w TYTULACH OBRAZOW (a nie w imionach osob).
# Obecnosc choc jednego dyskwalifikuje text jako "person name" - zapobiega
# false positive typu "Indian Summer", "Self Portrait", "Lake View" itp.
_PAINTING_TITLE_WORDS = frozenset(
    {
        # pory roku / czasy dnia
        "summer", "winter", "autumn", "spring", "fall",
        "morning", "evening", "night", "noon", "dawn", "dusk", "twilight",
        # przyroda / krajobraz
        "lake", "river", "sea", "ocean", "bay", "shore", "beach", "coast",
        "bridge", "mountain", "mountains", "hill", "hills", "valley",
        "forest", "wood", "woods", "garden", "field", "fields", "meadow",
        "sun", "moon", "star", "stars", "sky", "cloud", "clouds",
        "rain", "snow", "storm", "wind", "waves",
        "rose", "roses", "flower", "flowers", "tree", "trees",
        "fruit", "wheat", "corn", "harvest",
        # postacie i rodzaje portretow
        "lady", "ladies", "woman", "women", "girl", "girls",
        "man", "men", "boy", "boys", "child", "children",
        "lover", "lovers", "mother", "father", "sister", "brother",
        "saint", "madonna", "christ", "angel", "angels", "venus", "mars",
        "king", "queen", "prince", "princess",
        # zwierzeta
        "horse", "horses", "dog", "dogs", "cat", "cats", "bird", "birds",
        "rabbit", "deer", "lion", "tiger", "bull", "cow", "sheep",
        # rodzaje obrazow
        "landscape", "portrait", "self-portrait", "scene", "view", "vista",
        "still", "life", "abstract", "composition", "study",
        "interior", "exterior",
        # wydarzenia / akcje
        "battle", "war", "victory", "death", "birth", "wedding", "dance",
        "music", "feast", "hunt", "prayer",
        # narodowosci/przymiotniki przestrzenne (czesto w tytulach krajobrazow)
        "indian", "japanese", "chinese", "egyptian", "greek", "roman",
        "italian", "french", "spanish", "german", "dutch", "polish",
        "ancient", "modern", "old", "young", "blue", "red", "white", "black",
        "golden", "silver", "great", "little", "small", "big",
    }
)


def _looks_like_person_name(text: str) -> bool:
    """True gdy text wyglada jak imie i nazwisko (2-3 capitalized slow, brak liczb,
    brak slow funkcyjnych typowych dla tytulow ani slow tytulowych malarskich).
    Patrz `gui.App._looks_like_person_name`.
    """
    if not text or any(c.isdigit() for c in text):
        return False
    s = re.sub(r"\s+", " ", text).strip()
    words = s.split()
    if not (2 <= len(words) <= 3):
        return False
    for w in words:
        if len(w) < 2 or not w[0].isupper():
            return False
        wl = w.lower()
        if wl in _PERSON_NAME_FUNCTION_WORDS:
            return False
        # Dyskwalifikacja: slowo typowe dla tytulow obrazow obecne w text.
        # "Indian Summer" -> "summer" w blackliście -> NIE person name.
        # "Lake View" -> "lake","view" w blackliście -> NIE person name.
        if wl in _PAINTING_TITLE_WORDS:
            return False
    return True


def resolve_title(
    *,
    lens_candidates: list[str],
    yandex_candidates: list[str] | None = None,
    bing_candidates: list[str] | None = None,
    wikiart_candidates: list[str] | None = None,
    wiki_candidates: list[str] | None = None,
    wikidata_candidates: list[str] | None = None,
    met_candidates: list[str] | None = None,
    artic_candidates: list[str] | None = None,
    commons_candidates: list[str] | None = None,
    art_sites_candidates: list[str] | None = None,
    google_candidates: list[str] | None = None,
    filename_hint: str = "",
    artist: str = "",
) -> tuple[str, float, list[str], int]:
    """Zwraca (tytul_finalny, pewnosc_0_1, alternatywy, liczba_zrodel_zgodnych).

    `liczba_zrodel_zgodnych` to liczba ROZNYCH zrodel ktore zglosily wygrywajacy
    tytul. Pewnosc jest cap-owana zaleznie od tej liczby:
    1 zrodlo (np. tylko nazwa pliku) -> max 0.5,
    2 zrodla -> max 0.8,
    3 zrodla -> max 0.92,
    4+ zrodel -> bez cap (mozna osiagnac 1.0).
    Dzieki temu w UI od razu widac czy tytul jest tylko "zgadniety" czy faktycznie
    potwierdzony przez wiele niezaleznych baz.
    """
    yandex_candidates = yandex_candidates or []
    bing_candidates = bing_candidates or []
    wikiart_candidates = wikiart_candidates or []
    wiki_candidates = wiki_candidates or []
    wikidata_candidates = wikidata_candidates or []
    met_candidates = met_candidates or []
    artic_candidates = artic_candidates or []
    commons_candidates = commons_candidates or []
    art_sites_candidates = art_sites_candidates or []
    google_candidates = google_candidates or []
    raw_signals: list[tuple[str, str]] = []
    for c in lens_candidates:
        raw_signals.append(("lens", c))
    for c in yandex_candidates:
        raw_signals.append(("yandex", c))
    for c in bing_candidates:
        raw_signals.append(("bing", c))
    for c in wikiart_candidates:
        raw_signals.append(("wikiart", c))
    for c in wiki_candidates:
        raw_signals.append(("wiki", c))
    for c in wikidata_candidates:
        raw_signals.append(("wikidata", c))
    for c in met_candidates:
        raw_signals.append(("met", c))
    for c in artic_candidates:
        raw_signals.append(("artic", c))
    for c in commons_candidates:
        raw_signals.append(("commons", c))
    for c in art_sites_candidates:
        raw_signals.append(("art_sites", c))
    for c in google_candidates:
        raw_signals.append(("google", c))
    if filename_hint:
        raw_signals.append(("filename", filename_hint))

    buckets: dict[str, _CandidateBucket] = defaultdict(lambda: _CandidateBucket(canonical=""))
    # Hint_tokens uzywamy WYLACZNIE do bonusu za zgodnosc - dlatego wycinamy
    # generyki ("obraz", "image", "scan"...). Bez tego "Obraz.jpg" daje hint_tokens
    # = {"obraz"} i kazdy wynik z innego zrodla zawierajacy slowo "obraz" dostaje
    # +4 - co prowadzilo do tego, ze "Obraz" wygrywal ze 100% pewnoscia mimo, ze
    # Lens i Yandex zwrocili poprawne "Babie Lato"/"Indian Summer".
    hint_tokens = _meaningful_hint_tokens(filename_hint)

    for source, raw in raw_signals:
        cleaned = _clean_for_pick(_strip_artist(raw, artist))
        if not _is_acceptable(cleaned):
            continue
        # ANTY-CROSS-ARTIST: jesli kandydat wyglada na imie i nazwisko osoby
        # i nie ma zadnego overlapu z nazwa pliku, prawie na pewno trafilismy
        # w biograficzny artykul innego artysty (np. Lens/Wiki dla Achenbacha
        # zwracaja "Ludolf Bakhuizen"). Pomijamy taki kandydat - nie chcemy
        # zeby nazywal nasz plik imieniem cudzego artysty.
        # Wyjatek: filename ZAWSZE przepuszczamy - user moze nazwac obraz
        # imieniem postaci namalowanej na portrecie.
        if source != "filename" and _looks_like_person_name(cleaned):
            cand_tokens = set(_tokens(cleaned))
            if not (hint_tokens & cand_tokens):
                continue
        canon = _canonical(cleaned)
        if not canon:
            continue
        b = buckets[canon]
        b.canonical = canon
        b.forms.append(cleaned)
        b.sources[source] += 1
        b.score += _SOURCE_WEIGHT.get(source, 1)
        # Bonus za zgodnosc z nazwa pliku - mocno faworyzuje kandydatow,
        # ktorych slowa pojawiaja sie w nazwie pliku (user nazywal swiadomie).
        if hint_tokens:
            cand_tokens = set(canon.split())
            overlap = len(hint_tokens & cand_tokens)
            if overlap:
                b.score += overlap * _FILENAME_OVERLAP_BONUS

    if not buckets:
        # Wszystkie kandydaty odrzucone - jesli mamy hint, uzyj go (z mala pewnoscia)
        if filename_hint:
            return (format_artwork_title(filename_hint), 0.2, [], 1)
        return ("", 0.0, [], 0)

    # Bonus za pojawienie sie w wielu roznych zrodlach
    for b in buckets.values():
        distinct_sources = len([s for s, n in b.sources.items() if n > 0])
        if distinct_sources >= 2:
            b.score *= 1.0 + 0.5 * (distinct_sources - 1)

    ranked = sorted(buckets.values(), key=lambda x: x.score, reverse=True)
    top = ranked[0]
    total = sum(b.score for b in ranked) or 1.0
    raw_conf = min(1.0, top.score / total)

    # Cap pewnosci zaleznie od liczby roznych zrodel zgodnych z wynikiem.
    # Pojedyncze zrodlo (np. tylko nazwa pliku) NIGDY nie powinno dawac 100%.
    distinct_top = len([s for s, n in top.sources.items() if n > 0])
    cap_map = {1: 0.5, 2: 0.8, 3: 0.92}
    cap = cap_map.get(distinct_top, 1.0)
    confidence = min(raw_conf, cap)

    # Wybierz najczesciej widziana pisownie z najlepszego bucketa
    form_freq = Counter(top.forms)
    chosen_form = form_freq.most_common(1)[0][0]
    chosen = format_artwork_title(chosen_form)

    others_seen: set[str] = {chosen.lower()}
    others: list[str] = []
    for b in ranked[1:]:
        f = format_artwork_title(Counter(b.forms).most_common(1)[0][0])
        if f.lower() not in others_seen:
            others_seen.add(f.lower())
            others.append(f)
        if len(others) >= 6:
            break

    return (chosen, confidence, others, distinct_top)
