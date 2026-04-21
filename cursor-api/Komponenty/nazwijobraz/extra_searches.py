"""Dodatkowe zrodla weryfikacji nazwy obrazu poza Google Lens.

Te funkcje sa pomocnicze - nigdy nie podnosza wyjatku, w razie problemu zwracaja
puste listy / pusty dict. Ich celem jest dolozenie kandydatow do glosowania
w title_resolver.

Zrodla:
- Wikipedia (OpenSearch)              - artykuly EN
- Wikidata (wbsearch + wbgetentities) - tytul EN + tytul w jezyku oryginalnym
- The Met (collectionapi)             - kolekcja Metropolitan Museum of Art
- Art Institute of Chicago (api.artic) - kolekcja Chicago Art Institute
- SerpAPI Google text                 - pomocnicze, gdy reszta zawiedzie
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .env_loader import get as env_get
from .serpapi_status import SerpApiLimitError, raise_if_serpapi_limit

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MET_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
ARTIC_BASE = "https://api.artic.edu/api/v1/artworks/search"
SERPAPI_URL = "https://serpapi.com/search.json"

# Domeny aukcyjne / galerie / kolekcje sztuki - jedno zapytanie SerpAPI
# z site: filtrami zwraca tytuly z wszystkich tych zrodel naraz.
_ART_SITES = (
    "invaluable.com",
    "mutualart.com",
    "artnet.com",
    "fineartamerica.com",
    "artsandculture.google.com",
    "art.com",
    "pixels.com",
    "findartinfo.com",
    "bruun-rasmussen.dk",
    "picryl.com",
    "wikiart.org",
    "sothebys.com",
    "christies.com",
)
_USER_AGENT = "nazwijobraz/1.0 (https://github.com/local) verification"

# Wikidata QIDs traktowane jako "obraz / dziel sztuki".
_WIKIDATA_ARTWORK_QIDS = frozenset(
    {
        "Q3305213",   # painting
        "Q11629",     # work of art (general)
        "Q838948",    # work of art (visual)
        "Q4502142",   # visual artwork
        "Q860861",    # sculpture (akceptujemy)
        "Q15711026",  # drawing
        "Q93184",     # drawing (alt)
        "Q125191",    # photograph
        "Q1335594",   # printed artwork
        "Q11060274",  # print
        "Q18761202",  # icon
    }
)

# Priorytet jezykow dla "oryginalnego" tytulu obrazu (po english).
_ART_LANGS_PRIORITY = (
    "fr", "de", "it", "nl", "es", "ru", "pl", "pt", "ja", "zh", "sv", "no", "da",
)


# Slowa funkcyjne charakterystyczne dla nieangielskich jezykow. Uzywamy do
# wykrywania ze "Am Strand von Scheveningen" to NIE angielski mimo ASCII.
_NON_EN_FUNCTION_WORDS = frozenset(
    {
        # de
        "am", "auf", "bei", "vom", "von", "zum", "zur", "der", "die", "das",
        "ein", "eine", "einer", "einem", "und", "mit", "ohne", "im", "ins",
        "des", "den", "dem",
        # nl
        "een", "het", "naar", "aan",
        # fr
        "le", "la", "les", "du", "des", "et", "au", "aux", "dans", "sur",
        "sous", "sans", "avec", "vers",
        # it
        "il", "lo", "gli", "del", "della", "di", "con", "tra", "fra",
        # es
        "el", "los", "las", "y", "en", "con", "sin", "sobre",
        # pl
        "na", "po", "w", "we", "z", "ze", "do", "od",
    }
)


def _detect_non_english_lang(text: str) -> str:
    """Wykryj prawdopodobny jezyk dla NIE-angielskiego tekstu (heurystyka).

    Zwraca ISO ('de', 'fr', ...) gdy tekst zawiera slowo funkcyjne tego
    jezyka, w przeciwnym razie pusty string.
    """
    if not text:
        return ""
    import re as _re
    words = [w.lower() for w in _re.findall(r"\b[a-zA-Z]+\b", text)]
    de_words = {"von", "der", "die", "das", "ein", "eine", "und", "mit", "vom",
                "zum", "zur", "am", "im", "auf", "bei", "ohne", "uber"}
    nl_words = {"een", "het", "van", "naar", "aan", "bij"}
    fr_words = {"le", "la", "les", "du", "des", "et", "au", "aux", "dans"}
    it_words = {"il", "lo", "gli", "del", "della", "di"}
    es_words = {"el", "los", "las", "y", "en", "con", "sin"}
    for w in words:
        if w in de_words:
            return "de"
        if w in nl_words:
            return "nl"
        if w in fr_words:
            return "fr"
        if w in it_words:
            return "it"
        if w in es_words:
            return "es"
    return ""


def _looks_english_text(text: str) -> bool:
    """True gdy tekst wyglada na angielski - ASCII + brak DE/NL/FR/IT/ES slow."""
    if not text:
        return False
    cleaned = text.replace("\u2019", "'").replace("\u2018", "'")
    if not all(ord(c) < 128 for c in cleaned):
        return False
    import re as _re
    words = [w.lower() for w in _re.findall(r"\b[a-zA-Z]+\b", cleaned)]
    return not any(w in _NON_EN_FUNCTION_WORDS for w in words)


# ---------------------------------------------------------------------------
# Warianty nazwy pliku do sondowania Commons / Wikipedii
# ---------------------------------------------------------------------------
# Pliki z dysku czesto roznia sie od oryginalu na Commons o:
#   - przyrostki Windows ("-1", "-1-2", " (1)", "_1") gdy uzytkownik kopiowal plik
#   - prefiksy robocze ("Mockup ", "Mockup_", "Final_", "Copy of ")
#   - drobne sufiksy "_full", "_hd"
# Bez tych wariantow `File:<orig>` nie trafia w istniejaca strone i przez to
# logika preferencji wybiera bezsensowne kandydatury (np. nazwisko artysty).

_FILENAME_PREFIX_NOISE = (
    "Mockup ", "Mockup_", "mockup ", "mockup_",
    "Copy of ", "copy of ", "Copy_of_",
    "Final ", "Final_", "final ", "final_",
)
# Pojedynczy sufiks "duplikatu" pliku (zawsze krotki: 1-3 cyfry).
# Stripujemy ITERACYJNIE po jednym - dzieki temu generujemy progresywne
# warianty (po 1, po 2, po 3 obcieciach) i sondujemy KAZDY.
# Nie stripujemy "-NNNN" / "-NN-NN" hurtem, zeby nie zniszczyc numerow
# inwentarzowych typu "_1961_630_0-11".
_FILENAME_DUP_SUFFIX_RE = re.compile(
    r"(?:[\s._-]*\(\d+\)|[\s.\-_]\d{1,3}|[\s.\-_](?:full|hd|hq|copy|kopia))$",
    re.IGNORECASE,
)
_FILENAME_EXT_RE = re.compile(
    r"\.(jpg|jpeg|png|gif|webp|tif|tiff|bmp|svg|jfif)$", re.IGNORECASE
)


def _strip_noise_prefix(stem: str) -> str:
    """Sciagnij JEDEN prefix typu "Mockup ", "Copy of ", "Final " (jesli jest)."""
    for pfx in _FILENAME_PREFIX_NOISE:
        if stem.lower().startswith(pfx.lower()):
            return stem[len(pfx):].lstrip(" -_.")
    return stem


def _progressive_suffix_strips(stem: str, *, max_iter: int = 3) -> list[str]:
    """Zwroc liste form: [oryginal, po 1 obcieciu, po 2, po 3].

    Zatrzymuje sie gdy nic juz nie ucinamy. Kazda forma jest odrebnym
    kandydatem do sondazu Commons - nawet jak "za malo" lub "za duzo"
    obetniemy, oryginal pozostaje.
    """
    out = [stem]
    cur = stem
    for _ in range(max_iter):
        new = _FILENAME_DUP_SUFFIX_RE.sub("", cur).rstrip(" .-_")
        if new and new != cur:
            cur = new
            out.append(cur)
        else:
            break
    return out


def _filename_variants(filename: str, *, max_variants: int = 10) -> list[str]:
    """Generuje warianty nazwy pliku do sondowania `File:<...>` na Commons.

    Zwraca liste UNIKALNYCH nazw (z rozszerzeniem). Kolejnosc INTERLEAVE:
    najpierw oryginal, potem obciety o prefix, potem progresywne obcinanie
    sufiksu (na obu formach naraz). Dzieki interleave-owi forma najbardziej
    prawdopodobna - prefix stripped + 1 sufiks - jest na 3-4 pozycji,
    wiec budzet `max_variants` jej nie wycina.

    MediaWiki normalizuje "_" <-> " " w tytulach, wiec NIE generujemy obu
    form: zostawiamy oryginalny separator (zwykle "_") i sondujemy raz.
    """
    if not filename:
        return []
    raw = filename.strip()
    if not raw:
        return []

    m_ext = _FILENAME_EXT_RE.search(raw)
    if m_ext:
        stem = raw[: m_ext.start()]
        ext = raw[m_ext.start():]
    else:
        stem = raw
        ext = ""

    # Dwa "tory" stemu: oryginalny i z obcietym prefiksem typu "Mockup ".
    track_orig = _progressive_suffix_strips(stem)
    track_noprefix = []
    stripped = _strip_noise_prefix(stem)
    if stripped and stripped != stem:
        track_noprefix = _progressive_suffix_strips(stripped)

    # Interleave: orig[0], noprefix[0], orig[1], noprefix[1], ...
    interleaved: list[str] = []
    seen_stems: set[str] = set()
    n = max(len(track_orig), len(track_noprefix))
    for i in range(n):
        for track in (track_orig, track_noprefix):
            if i < len(track):
                s = track[i]
                if s and s not in seen_stems:
                    seen_stems.add(s)
                    interleaved.append(s)

    # Zsklej z rozszerzeniem - jedna forma per stem (Commons normalizuje "_" / " ").
    out: list[str] = []
    seen: set[str] = set()
    for s in interleaved:
        full = f"{s}{ext}"
        key = full.lower()
        if full and key not in seen:
            seen.add(key)
            out.append(full)
        if len(out) >= max_variants:
            return out
    return out


def _serpapi_get(params: dict[str, str], timeout: float) -> dict | None:
    """GET https://serpapi.com/search.json z wykrywaniem limitu konta.

    Zwraca dict z odpowiedzia (sukces) albo None (blad ktory NIE jest limitem
    - po prostu pomijamy ten wynik). Jesli serwer zwroci limit/blad klucza,
    rzuca SerpApiLimitError - GUI to wylapuje i pokazuje dialog.
    """
    qs = urllib.parse.urlencode(params)
    url = f"{SERPAPI_URL}?{qs}"
    status_code = 200
    raw_data: dict | None = None
    try:
        try:
            from .http_client import get_session
            sess = get_session()
            try:
                resp = sess.get(SERPAPI_URL, params=params, timeout=timeout)
            except Exception:  # noqa: BLE001
                return None
            status_code = resp.status_code
            try:
                raw_data = resp.json()
            except Exception:  # noqa: BLE001
                raw_data = None
        except ImportError:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            try:
                with urllib.request.urlopen(
                    req, context=ssl.create_default_context(), timeout=timeout
                ) as resp:
                    status_code = resp.status
                    raw_data = json.loads(resp.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as e:
                status_code = e.code
                try:
                    raw_data = json.loads(e.read().decode("utf-8", errors="replace"))
                except (OSError, json.JSONDecodeError):
                    raw_data = None
            except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
                return None
        # Sprawdz limit ZAWSZE - nawet dla 4xx, bo SerpAPI np. zwraca 401/429.
        raise_if_serpapi_limit(raw_data, status_code)
    except SerpApiLimitError:
        raise
    if status_code >= 400:
        return None
    if not isinstance(raw_data, dict):
        return None
    return raw_data


def _http_get_json(url: str, timeout: float) -> dict | list | None:
    """GET + JSON. Uzywa wspolnej `requests.Session` z keep-alive (http_client).

    Backward-compat: jesli requests nie jest zainstalowany, fallback do urllib.
    """
    try:
        from .http_client import get_json
    except ImportError:
        get_json = None  # type: ignore[assignment]
    if get_json is not None:
        return get_json(url, timeout=timeout, headers={"User-Agent": _USER_AGENT})
    # Fallback urllib (gdy `requests` brak)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(
            req, context=ssl.create_default_context(), timeout=timeout
        ) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


# ------------------------- Wikipedia -------------------------

def wikipedia_titles(query: str, *, limit: int = 6, timeout: float = 12.0) -> list[str]:
    """Wikipedia OpenSearch - zwraca tytuly artykulow pasujacych do query.

    Bardzo dobre dla obrazow ktorych wikipedia ma osobny artykul.
    """
    q = (query or "").strip()
    if not q:
        return []
    qs = urllib.parse.urlencode(
        {
            "action": "opensearch",
            "search": q,
            "limit": str(limit),
            "namespace": "0",
            "format": "json",
        }
    )
    data = _http_get_json(f"{WIKI_API}?{qs}", timeout)
    # OpenSearch: [query, [titles], [descriptions], [urls]]
    if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
        return [str(t) for t in data[1] if t]
    return []


def wikipedia_painting_titles(artist: str, title_hint: str, *, limit: int = 6) -> list[str]:
    """Zlozone zapytania dla Wikipedii (artysta + hint + slowo 'painting')."""
    out: list[str] = []
    seen: set[str] = set()
    queries: list[str] = []
    if title_hint and artist:
        queries.append(f"{title_hint} {artist} painting")
        queries.append(f"{title_hint} {artist}")
    if title_hint:
        queries.append(f"{title_hint} painting")
        queries.append(title_hint)
    if artist and not title_hint:
        queries.append(f"{artist} painting")
    for q in queries:
        for t in wikipedia_titles(q, limit=limit):
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
        if len(out) >= limit * 2:
            break
    return out


# ------------------------- Wikipedia direct page lookup + langlinks -------

# Tytuly typu "(painting)", "(Van Gogh)", "(1888)" w nawiasie - przy wyciaganiu
# samego tytulu obrazu chcemy je opcjonalnie obciac.
_WIKI_PAREN_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _strip_wiki_paren_suffix(title: str) -> str:
    """'Sunflowers (Van Gogh series)' -> 'Sunflowers'."""
    return _WIKI_PAREN_SUFFIX_RE.sub("", title or "").strip()


def wikipedia_lookup(
    artist: str,
    query: str,
    *,
    filename: str = "",
    limit: int = 5,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Pelne sprawdzenie Wikipedii - direct page + OpenSearch + langlinks.

    Zwraca dict zgodny z `wikidata_painting_lookup`:
        {
            "candidates": [...],         # tytul EN + wszystkie tytuly z langlinks
            "english": "...",            # tytul artykulu na enwiki (po obcieciu nawiasu)
            "original_title": "...",     # tytul z preferowanego jezyka non-EN
            "original_lang": "fr",
            "source_url": "https://en.wikipedia.org/wiki/...",
            "wikidata_qid": "Q12418",    # link do Wikidata przez pageprops
        }

    KLUCZOWA optymalizacja (analogicznie do Commons):
    1) jesli `filename` jest podany, probujemy BEZPOSREDNIO dopasowac
       `titles=<filename_bez_rozszerzenia>` - czesto plik nazywa sie tak samo
       jak artykul (np. "Mona_Lisa.jpg" -> /wiki/Mona_Lisa).
    2) `prop=langlinks` daje WSZYSTKIE wersje jezykowe tytulu w jednym requescie
       (Mona Lisa -> 132 jezykow, w tym pl/da/de/fr/...).
    3) `prop=pageprops` daje `wikibase_item` = Wikidata Q-id, ktory mozna
       skojarzyc z innymi zrodlami (Wikidata, Commons).
    """
    out: dict[str, Any] = {
        "candidates": [],
        "english": "",
        "original_title": "",
        "original_lang": "",
        "source_url": "",
        "wikidata_qid": "",
    }
    seen_cands: set[str] = set()

    def _push_cand(text: str) -> None:
        v = (text or "").strip()
        if not v:
            return
        k = v.lower()
        if k in seen_cands:
            return
        seen_cands.add(k)
        out["candidates"].append(v)

    candidate_titles: list[str] = []

    # 1) Direct - bezposrednio nazwa pliku jako tytul artykulu.
    #    Sondujemy WIELE wariantow nazwy (oryginal + obciete sufiksy/prefiksy
    #    Windows-owe i robocze) - patrz `_filename_variants`.
    if filename:
        for variant in _filename_variants(filename, max_variants=6):
            base = _FILENAME_EXT_RE.sub("", variant)
            base = base.replace("_", " ").strip()
            if not base:
                continue
            candidate_titles.append(base)
            # Czesto plik na Commons ma format "Artysta - Tytul - Rok"
            # Wyciagnijmy "Tytul" z srodka.
            parts = [p.strip() for p in base.split(" - ") if p.strip()]
            if len(parts) >= 2:
                for part in parts:
                    if part and not re.fullmatch(r"\d{3,4}", part):
                        candidate_titles.append(part)

    # 2) OpenSearch - fuzzy.
    if query:
        for t in wikipedia_titles(query, limit=limit):
            candidate_titles.append(t)
        if artist and query:
            for t in wikipedia_titles(f"{query} {artist}", limit=limit):
                candidate_titles.append(t)

    # Deduplikuj i ogranicz - max 8 stron, zeby batch byl szybki.
    seen_titles: set[str] = set()
    uniq_titles: list[str] = []
    for t in candidate_titles:
        k = t.strip().lower()
        if k and k not in seen_titles:
            seen_titles.add(k)
            uniq_titles.append(t.strip())
        if len(uniq_titles) >= 8:
            break

    if not uniq_titles:
        return out

    # 3) Batch query - jedna zapytanie zwraca info o wszystkich stronach
    #    + langlinks + pageprops + URL.
    qs = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": "|".join(uniq_titles),
            "prop": "langlinks|pageprops|info",
            "lllimit": "500",
            "llprop": "url|langname",
            "inprop": "url",
            "redirects": "1",  # rozwiaz redirecty (Sloneczniki -> Sunflowers)
            "format": "json",
        }
    )
    data = _http_get_json(f"{WIKI_API}?{qs}", timeout)
    pages_dict = ((data or {}).get("query") or {}).get("pages") or {}
    if not pages_dict:
        return out

    # MediaWiki normalizuje "_" -> " " w tytulach.
    def _norm_title(t: str) -> str:
        return (t or "").replace("_", " ").strip().lower()

    # Iteruj zgodnie z naszą kolejnoscia preferencji (filename first).
    pages_by_norm: dict[str, dict[str, Any]] = {}
    for p in pages_dict.values():
        if isinstance(p, dict):
            t = p.get("title", "")
            if t:
                pages_by_norm[_norm_title(t)] = p

    en_set = False
    orig_set = False
    for orig_title in uniq_titles:
        p = pages_by_norm.get(_norm_title(orig_title))
        if not p or p.get("missing") is not None:
            continue
        page_title = p.get("title", "")
        if not page_title:
            continue
        # Tytul EN to nazwa artykulu na enwiki, po obcieciu nawiasu.
        en_clean = _strip_wiki_paren_suffix(page_title)
        if en_clean:
            _push_cand(en_clean)
            _push_cand(page_title)  # tez pelna z nawiasem - jako alt
        # Pageprops: wikibase_item
        wb_qid = (p.get("pageprops") or {}).get("wikibase_item", "")
        if wb_qid and not out["wikidata_qid"]:
            out["wikidata_qid"] = wb_qid
        # URL
        url = p.get("fullurl", "") or (
            "https://en.wikipedia.org/wiki/"
            + urllib.parse.quote(page_title.replace(" ", "_"))
        )
        if not en_set:
            out["english"] = en_clean
            out["source_url"] = url
            en_set = True
        # Langlinks -> wszystkie wersje jezykowe tytulu
        for ll in p.get("langlinks", []):
            lang = ll.get("lang", "")
            val = ll.get("*", "") or ll.get("value", "")
            if not lang or not val:
                continue
            val_clean = _strip_wiki_paren_suffix(val)
            _push_cand(val_clean)
            _push_cand(val)
            # Wybor "original_title": pierwszy non-EN z naszego priorytetu
            if not orig_set and lang in _ART_LANGS_PRIORITY and val_clean:
                if val_clean.lower() != (out["english"] or "").lower():
                    out["original_title"] = val_clean
                    out["original_lang"] = lang
                    orig_set = True

        # Jesli mamy juz EN + original, mozemy konczyc.
        if en_set and orig_set:
            break

    return out


# ------------------------- SerpAPI Google text -------------------------

def google_text_titles(query: str, *, limit: int = 8, timeout: float = 20.0) -> list[str]:
    """SerpAPI engine=google - zwraca tytuly z knowledge_graph + organic_results."""
    api_key = env_get("SERPAPI_KEY")
    q = (query or "").strip()
    if not api_key or not q:
        return []
    data = _serpapi_get(
        {
            "engine": "google",
            "q": q,
            "api_key": api_key,
            "hl": "en",
            "num": "10",
        },
        timeout,
    )
    if not isinstance(data, dict):
        return []
    out: list[str] = []
    seen: set[str] = set()

    def _add(t: object) -> None:
        if isinstance(t, str):
            v = t.strip()
            if v and v.lower() not in seen:
                seen.add(v.lower())
                out.append(v)

    kg = data.get("knowledge_graph")
    if isinstance(kg, dict):
        _add(kg.get("title"))
    elif isinstance(kg, list):
        for entry in kg[:3]:
            if isinstance(entry, dict):
                _add(entry.get("title"))

    answer_box = data.get("answer_box")
    if isinstance(answer_box, dict):
        _add(answer_box.get("title"))

    organic = data.get("organic_results")
    if isinstance(organic, list):
        for o in organic[:limit]:
            if isinstance(o, dict):
                _add(o.get("title"))

    return out


# ------------------------- Wikidata -------------------------

# Jezyki w ktorych probujemy wbsearchentities - obejmujemy najczestsze
# kolekcje europejskie + japonski/chinski. Gdy nazwa pliku jest po polsku,
# Wikidata znajdzie hity tylko jesli zapytamy z language=pl (wbsearchentities
# uwzglednia aliasy danego jezyka).
_WIKIDATA_SEARCH_LANGS = ("en", "pl", "fr", "de", "it", "nl", "es", "ru", "pt", "sv")


def _wikidata_search(query: str, *, limit: int = 6, timeout: float = 8.0) -> list[dict[str, Any]]:
    """Search Wikidata - probujemy kolejno listy jezykow do znalezienia trafien.

    Zwraca polaczone wyniki z roznych jezykow (deduplikowane po qid).
    Optymalizacja: dla queries ASCII zwykle EN wystarcza i przestajemy
    pytac inne jezyki (oszczedzamy 8-9 HTTP roundtripow per zapytanie).
    """
    if not query:
        return []
    seen_qids: set[str] = set()
    out: list[dict[str, Any]] = []
    has_non_ascii = any(ord(c) > 127 for c in query)
    # Kolejnosc: jesli query ma znaki diakrytyczne, najpierw probujemy
    # PL/FR/DE/IT/ES, potem EN. W przeciwnym razie EN -> reszta.
    if has_non_ascii:
        order = ("pl", "fr", "de", "it", "nl", "es", "pt", "sv", "en")
    else:
        order = _WIKIDATA_SEARCH_LANGS
    # Twardy budzet czasowy na multi-lang wyszukiwanie - zeby pojedyncze
    # spowolnione zapytanie nie zablokowalo calego pipelinu.
    import time as _t
    deadline = _t.monotonic() + max(timeout, 4.0)
    for idx, lang in enumerate(order):
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
        data = _http_get_json(f"{WIKIDATA_API}?{qs}", timeout)
        if not isinstance(data, dict):
            continue
        new_in_this_lang = 0
        for hit in data.get("search") or []:
            qid = (hit or {}).get("id", "")
            if not qid or qid in seen_qids:
                continue
            seen_qids.add(qid)
            hit["_search_lang"] = lang
            out.append(hit)
            new_in_this_lang += 1
        # Krotki obwod: po pierwszym jezyku (EN dla ASCII / PL dla non-ASCII)
        # wystarczy ze mamy >= limit hitow, nie wolajmy juz reszty.
        if idx == 0 and len(out) >= limit:
            break
        # Twardy budzet czasowy
        if _t.monotonic() > deadline:
            break
        # Jesli mamy juz duzo hitow, dosc.
        if len(out) >= limit * 2:
            break
    return out


def _wikidata_get_entities_batch(
    qids: list[str], *, timeout: float = 10.0
) -> dict[str, dict[str, Any]]:
    """Batch wbgetentities - do 50 IDs w jednym HTTP roundtripie.

    Zamienia N osobnych zapytan na 1 (lub kilka, jesli > 50). To ogromny
    zysk gdy Wikidata search zwrocil 5-15 kandydatow.
    """
    qids = [q for q in qids if q]
    if not qids:
        return {}
    result: dict[str, dict[str, Any]] = {}
    # Wikidata limit: 50 IDs na zapytanie.
    for i in range(0, len(qids), 50):
        chunk = qids[i : i + 50]
        qs = urllib.parse.urlencode(
            {
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": "labels|claims|sitelinks/urls",
                "format": "json",
            }
        )
        data = _http_get_json(f"{WIKIDATA_API}?{qs}", timeout)
        if not isinstance(data, dict):
            continue
        entities = data.get("entities") or {}
        for qid, ent in entities.items():
            if isinstance(ent, dict):
                result[qid] = ent
    return result


def _wikidata_get_entity(qid: str, *, timeout: float = 12.0) -> dict[str, Any] | None:
    if not qid:
        return None
    qs = urllib.parse.urlencode(
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels|claims|sitelinks/urls",
            "format": "json",
        }
    )
    data = _http_get_json(f"{WIKIDATA_API}?{qs}", timeout)
    if not isinstance(data, dict):
        return None
    entities = data.get("entities") or {}
    ent = entities.get(qid)
    return ent if isinstance(ent, dict) else None


def wikidata_inception_year(painting_qid: str, *, timeout: float = 10.0) -> str:
    """Zwraca ROK powstania obrazu z Wikidata (P571 = inception).

    Zwraca pusty string gdy:
      - brak qid
      - brak P571 w encji
      - precision < 9 (niepewny - wiek/dekada, nie konkretny rok)
      - rok przed n.e. (EXIF DateTimeOriginal nie wspiera lat ujemnych)

    Wikidata precision values:
        6 = millennium, 7 = century, 8 = decade, 9 = year,
        10 = month, 11 = day.
    Zwracamy tylko gdy >= 9 - user prosil "jesli jestem pewien".
    """
    if not painting_qid:
        return ""
    ent = _wikidata_get_entity(painting_qid, timeout=timeout)
    if not ent:
        return ""
    claims = ent.get("claims") or {}
    p571 = claims.get("P571") or []
    for stmt in p571:
        try:
            val = stmt["mainsnak"]["datavalue"]["value"]
        except (KeyError, TypeError):
            continue
        time_str = val.get("time", "") if isinstance(val, dict) else ""
        precision = val.get("precision", 0) if isinstance(val, dict) else 0
        if not time_str or precision < 9:
            continue
        # Format Wikidata: "+1875-00-00T00:00:00Z" lub "-0050-..." dla BC.
        m = re.match(r"^([+-]?)(\d+)-", time_str)
        if not m:
            continue
        sign, year_digits = m.groups()
        try:
            year_int = int(year_digits)
        except ValueError:
            continue
        if sign == "-":
            continue   # EXIF DateTimeOriginal wymaga lat n.e.
        if year_int < 1 or year_int > 9999:
            continue
        return str(year_int)
    return ""


def wikidata_creator_label(painting_qid: str, *, timeout: float = 10.0) -> str:
    """Zwraca imie i nazwisko autora obrazu z Wikidata (P170 = creator).

    Pipeline:
      1) Pobierz encje obrazu (qid).
      2) Wez claim P170 -> qid autora.
      3) Pobierz encje autora; zwroc label po EN, fallback PL/DE/FR/IT/ES/NL/RU.

    Sluzy do auto-uzupelniania pola "Autor" w nazwijobraz, gdy plik nie jest
    w folderze typu "Sisley, Alfred/" - np. "Obraz.jpg" w katalogu glownym.
    """
    if not painting_qid:
        return ""
    ent = _wikidata_get_entity(painting_qid, timeout=timeout)
    if not ent:
        return ""
    claims = ent.get("claims") or {}
    p170 = claims.get("P170") or []
    creator_qids: list[str] = []
    for stmt in p170:
        try:
            cqid = stmt["mainsnak"]["datavalue"]["value"]["id"]
        except (KeyError, TypeError):
            continue
        if cqid and cqid not in creator_qids:
            creator_qids.append(cqid)
    if not creator_qids:
        return ""
    creators = _wikidata_get_entities_batch(creator_qids[:3], timeout=timeout)
    for cqid in creator_qids:
        c = creators.get(cqid)
        if not isinstance(c, dict):
            continue
        labels = c.get("labels") or {}
        # Preferuj angielski (zazwyczaj transliteracja standardowa: "Józef Chełmoński")
        for lang in ("en", "pl", "de", "fr", "it", "es", "nl", "ru"):
            label = (labels.get(lang) or {}).get("value")
            if label and isinstance(label, str):
                return label.strip()
    return ""


def _is_artwork(entity: dict[str, Any]) -> bool:
    claims = entity.get("claims") or {}
    p31 = claims.get("P31") or []
    for stmt in p31:
        try:
            qid = stmt["mainsnak"]["datavalue"]["value"]["id"]
        except (KeyError, TypeError):
            continue
        if qid in _WIKIDATA_ARTWORK_QIDS:
            return True
    # Czasem brak P31 ale jest P170 (creator) + P217 (inventory number) - tez akceptuj
    if claims.get("P170") and (claims.get("P217") or claims.get("P276")):
        return True
    return False


def wikidata_painting_lookup(artist: str, query: str) -> dict[str, Any]:
    """Pelne sprawdzenie Wikidata: zwraca slownik z tytulami i meta.

    Wynik:
        {
            "candidates": [...],     # wszystkie zaobserwowane tytuly (do glosowania)
            "english": "...",        # angielski tytul artykulu (jesli jest)
            "original_title": "...", # tytul w jezyku oryginalnym (jesli rozni sie od EN)
            "original_lang": "fr",
            "source_url": "https://en.wikipedia.org/wiki/...",
            "qid": "Q12345",
        }
    """
    out: dict[str, Any] = {
        "candidates": [],
        "english": "",
        "original_title": "",
        "original_lang": "",
        "source_url": "",
        "qid": "",
    }
    q = (query or "").strip()
    if not q:
        return out

    queries = []
    if artist:
        queries.append(f"{q} {artist}")
    queries.append(q)

    seen_qids: set[str] = set()
    seen_cands: set[str] = set()

    def _push_cand(text: str) -> None:
        v = (text or "").strip()
        if not v:
            return
        k = v.lower()
        if k in seen_cands:
            return
        seen_cands.add(k)
        out["candidates"].append(v)

    # Faza 1: zbierz QIDs ze wszystkich queries (zwykle 1-2 search calls).
    ordered_qids: list[str] = []
    for sq in queries:
        for hit in _wikidata_search(sq, limit=5):
            qid = hit.get("id", "")
            if not qid or qid in seen_qids:
                continue
            seen_qids.add(qid)
            _push_cand(hit.get("label", ""))
            ordered_qids.append(qid)

    if not ordered_qids:
        return out

    # Faza 2: JEDEN batch wbgetentities zamiast N osobnych - to gigantyczny
    # zysk wydajnosci (1 HTTP zamiast 5-15).
    entities = _wikidata_get_entities_batch(ordered_qids)

    # Faza 3: iterujemy entities w kolejnosci hit-ow z search.
    for qid in ordered_qids:
        entity = entities.get(qid)
        if not entity or not _is_artwork(entity):
            continue
        labels = entity.get("labels") or {}
        en_label = (labels.get("en") or {}).get("value", "")
        if en_label:
            _push_cand(en_label)
        # Wybierz oryginalny tytul w preferowanym jezyku
        chosen_lang = ""
        chosen_label = ""
        for lang in _ART_LANGS_PRIORITY:
            lab = (labels.get(lang) or {}).get("value", "")
            if lab and (not en_label or lab.lower() != en_label.lower()):
                chosen_lang = lang
                chosen_label = lab
                break
        if not chosen_label:
            for lang, lobj in labels.items():
                if lang == "en":
                    continue
                lab = (lobj or {}).get("value", "")
                if lab and (not en_label or lab.lower() != en_label.lower()):
                    chosen_lang = lang
                    chosen_label = lab
                    break
        for lobj in labels.values():
            _push_cand((lobj or {}).get("value", ""))
        sitelinks = entity.get("sitelinks") or {}
        url = ""
        for key in ("enwiki", "frwiki", "dewiki", "itwiki"):
            site = sitelinks.get(key) or {}
            if site.get("url"):
                url = site["url"]
                break
        if not url:
            url = f"https://www.wikidata.org/wiki/{qid}"

        if not out["english"] and en_label:
            out["english"] = en_label
            out["qid"] = qid
            out["source_url"] = url
            if chosen_label:
                out["original_title"] = chosen_label
                out["original_lang"] = chosen_lang
            return out
    return out


# ------------------------- The Met (Metropolitan Museum) -------------------------

def met_museum_titles(artist: str, query: str, *, limit: int = 4, timeout: float = 20.0) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []
    full_q = f"{q} {artist}".strip() if artist else q
    qs = urllib.parse.urlencode({"q": full_q, "hasImages": "true"})
    data = _http_get_json(f"{MET_BASE}/search?{qs}", timeout)
    if not isinstance(data, dict):
        return []
    ids = data.get("objectIDs") or []
    if not ids:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for oid in ids[:limit]:
        obj = _http_get_json(f"{MET_BASE}/objects/{oid}", timeout=10.0)
        if not isinstance(obj, dict):
            continue
        # Filtruj po artyscie - jesli mamy hint artysty, akceptuj tylko zgodne
        if artist:
            adn = (obj.get("artistDisplayName") or "").lower()
            if artist.lower().split()[-1] not in adn:
                continue
        title = obj.get("title")
        if title and title.lower() not in seen:
            seen.add(title.lower())
            out.append(str(title))
    return out


# ------------------------- Art Institute of Chicago -------------------------

def art_institute_titles(artist: str, query: str, *, limit: int = 5, timeout: float = 20.0) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []
    full_q = f"{q} {artist}".strip() if artist else q
    qs = urllib.parse.urlencode(
        {
            "q": full_q,
            "fields": "id,title,artist_display,artist_title",
            "limit": str(limit),
        }
    )
    data = _http_get_json(f"{ARTIC_BASE}?{qs}", timeout)
    if not isinstance(data, dict):
        return []
    items = data.get("data") or []
    out: list[str] = []
    seen: set[str] = set()
    artist_last = artist.lower().split()[-1] if artist else ""
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        if artist_last:
            disp = (it.get("artist_display") or it.get("artist_title") or "").lower()
            if artist_last not in disp:
                continue
        t = it.get("title")
        if t and str(t).lower() not in seen:
            seen.add(str(t).lower())
            out.append(str(t))
    return out


# ---------------------------------------------------------------------------
# Wikimedia Commons - kategorie i pliki opisujace dziela sztuki
# ---------------------------------------------------------------------------


# Regex do wyciagania tytulow w wielu jezykach z wikitext typu
# `{{en|1=Evening atmosphere at Falsterbo beach}} {{da|1=Aftenstemning ved Falsterbo Strand}}`
# Obsluga obowiazkowego `1=` (parametr opcjonalny w MediaWiki) oraz cudzyslowow.
_COMMONS_LANG_TPL_RE = re.compile(
    r"\{\{\s*([a-z]{2,3}(?:-[a-zA-Z0-9]+)?)\s*\|\s*(?:1\s*=\s*)?([^{}]+?)\s*\}\}",
)
# Zdjecie BBcode/HTML/cudzyslowow z wartosci.
_COMMONS_STRIP_HTML_RE = re.compile(r"<[^>]+>")
_COMMONS_QUOTES_RE = re.compile(
    r"^[\"\'\u201c\u201d\u2018\u2019\u00ab\u00bb\u201e\u201a]+|"
    r"[\"\'\u201c\u201d\u2018\u2019\u00ab\u00bb\u201e\u201a]+$",
)
# Commons czesto wpisuje rendery QuickStatements w UKRYTY <div style="display:none">
# albo w <span/p style="display:none">. Po strip HTML zostaje "label QS:Len,..." -
# musimy te bloki usunac PRZED zdjeciem tagow.
_COMMONS_HIDDEN_BLOCK_RE = re.compile(
    r"<(?P<tag>div|span|p)[^>]*style\s*=\s*[\"'][^\"']*display\s*:\s*none[^\"']*[\"'][^>]*>"
    r".*?</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
# Dump QS:Lxx,"..."  / title QS:Pxxxx,...  / label QS:Lxx,"..." - jak juz cos przelezie
# przez HTML, obcinamy od pierwszego wystapienia.
_COMMONS_QS_DUMP_RE = re.compile(
    r"\s*(?:label|title|description)\s*QS\s*:\s*[A-Z][A-Za-z0-9_:,\"'\u201c\u201d\s\-]*$",
    re.DOTALL,
)
# Wikitext italic (''X'') / bold ('''X'''). Po cleanupie chcemy goly tekst.
_COMMONS_WIKITEXT_BOLDITAL_RE = re.compile(r"'{2,5}")
# Pelne nazwy jezykow uzywanych w Commons jako prefiks "German: ...", "Dansk: ...".
# Mapowanie -> ISO. Pozwala rozbic scalone "German: X English: Y" na lang_titles.
_COMMONS_LANG_PREFIX_TO_ISO = {
    "english": "en", "german": "de", "deutsch": "de",
    "french": "fr", "francais": "fr", "francais (france)": "fr",
    "italian": "it", "italiano": "it",
    "dutch": "nl", "nederlands": "nl",
    "danish": "da", "dansk": "da",
    "swedish": "sv", "svenska": "sv",
    "norwegian": "no", "norsk": "no",
    "spanish": "es", "espanol": "es", "español": "es",
    "portuguese": "pt", "portugues": "pt", "português": "pt",
    "russian": "ru", "русский": "ru",
    "polish": "pl", "polski": "pl",
    "japanese": "ja", "日本語": "ja",
    "chinese": "zh", "中文": "zh",
}
# Regex dla podzialu "<Lang>: <text>" w jednym ciagu.
# Match nazwy jezyka (wiele slow), dwukropek, tekst do nastepnego prefixu lub konca.
_COMMONS_LANG_PREFIX_RE = re.compile(
    r"(?:^|\s)(" + "|".join(re.escape(k) for k in _COMMONS_LANG_PREFIX_TO_ISO) + r")\s*:\s*",
    re.IGNORECASE,
)
# Tokeny ktore sygnalizuja ze to OPIS dziela, nie tytul. Stosujemy heurystyke
# w `_looks_like_artwork_description` - gdy obecny -> odrzucamy kandydata.
_COMMONS_DESCRIPTION_TOKENS_RE = re.compile(
    r"(?:\b(?:cm|mm|inches?|signed|signiert|signe[éd]?|sygnowan[eaiy]?|"
    r"oil on (?:canvas|paper|wood|panel|board)|huile sur|olej na|"
    r"\u00d6l auf (?:Leinwand|Holz|Papier|Karton)|"
    r"olio su|tempera|aquarell?|watercolor|acrylic|"
    r"datiert|dated|datowan[ey])\b|"
    r"\d+\s*[x\u00d7]\s*\d+(?:[\.,]\d+)?\s*(?:cm|mm|inches?|in)?\b|"
    r"\bv\.?\s*\d{4}\b|\bca\.?\s*\d{4}\b)",
    re.IGNORECASE,
)


def _commons_clean_text(text: str) -> str:
    if not text:
        return ""
    # 1) Usun bloki ukryte przez CSS display:none (zwykle dump QuickStatements).
    text = _COMMONS_HIDDEN_BLOCK_RE.sub("", text)
    # 2) Usun wikilinki [[X|Y]] -> Y, [[X]] -> X
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    # 3) Strip HTML tagow
    text = _COMMONS_STRIP_HTML_RE.sub("", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    # 3a) Strip wikitext italic/bold ('' i ''') - czesto opakowuja tytuly w {{Artwork}}.
    text = _COMMONS_WIKITEXT_BOLDITAL_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    # 4) Awaryjny strip dump-u QS gdyby przelezial przez HTML strip.
    #    Iteracyjnie - moze byc kilka ogonow.
    for _ in range(3):
        new = _COMMONS_QS_DUMP_RE.sub("", text).strip()
        if new == text:
            break
        text = new
    # 5) Trim cudzyslowy z koncow
    while True:
        new = _COMMONS_QUOTES_RE.sub("", text).strip()
        if new == text:
            break
        text = new
    return text


def _looks_like_artwork_description(text: str) -> bool:
    """True gdy text wyglada na techniczny opis dziela (medium, wymiary, sygnatura).

    Commons czesto wpisuje cala metryke do `title=` zamiast krotkiego tytulu,
    np. "Am Strand von Scheveningen. Öl auf Holz. 49 x 61 cm. Signiert ...".
    Takich nie chcemy w nazwie pliku - to opis, nie tytul.
    """
    if not text:
        return False
    if len(text) > 120:
        return True
    return bool(_COMMONS_DESCRIPTION_TOKENS_RE.search(text))


def _split_compound_lang_string(text: str) -> dict[str, str]:
    """Rozbij scalony tekst typu "German: X English: Y" na {iso: text}.

    Commons czesto zwraca w `extmetadata.ObjectName` SCALONE dwa tytuly bez
    separatora:
    - z dwoma prefiksami: "German: X English: Y"
    - z jednym prefiksem i CamelCase granica: "German: Ein... FlutTowboat..."
    - bez zadnego prefiksu: "Title in deTitle in en" (rzadko, nie obslugujemy)

    Zwraca pusty dict gdy nie ma rozpoznawalnego prefixu.
    """
    if not text:
        return {}
    matches = list(_COMMONS_LANG_PREFIX_RE.finditer(text))
    if not matches:
        return {}
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        lang_word = m.group(1).lower()
        iso = _COMMONS_LANG_PREFIX_TO_ISO.get(lang_word, "")
        if not iso:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip(" .,;:-\"'\u201c\u201d\u2018\u2019")
        if chunk and iso not in out:
            out[iso] = chunk

    # HEURYSTYKA CamelCase: jesli mamy TYLKO jeden prefix (np. "German:")
    # i jego chunk wyglada jak "Ein Schlepper... FlutTowboat leaving...",
    # sprobuj rozbic po granicy "lower-letter + UPPER-letter" gdzie
    # nastepna grupa wyglada na inny jezyk (zwykle EN).
    if len(out) == 1:
        only_lang, only_chunk = next(iter(out.items()))
        # Szukamy granicy: "...mała_litera duża_litera..." albo "...mała_literaduża_litera...".
        # Drugi wariant (bez spacji) to typowy case scalania.
        # Patrz: "FlutTowboat" -> granica po "Flut" przed "Towboat".
        # Ograniczamy do sytuacji gdzie obie czesci maja >= 10 znakow,
        # zeby nie rozbic legalnych tytulow z kapitalizacja w srodku.
        m2 = re.search(r"([a-z\u00DF\u00E4\u00F6\u00FC])([A-Z][a-zA-Z]{4,})", only_chunk)
        if m2 and m2.start() >= 10 and (len(only_chunk) - m2.end() + 1) >= 10:
            split_idx = m2.start() + 1
            first = only_chunk[:split_idx].strip(" .,;:-\"'\u201c\u201d\u2018\u2019")
            second = only_chunk[split_idx:].strip(" .,;:-\"'\u201c\u201d\u2018\u2019")
            if first and second and first != second:
                out[only_lang] = first
                # Drugi kawalek - prawdopodobnie EN (najczesciej dwujezyczne
                # tytuly Commons sa DE+EN albo orig+EN). Zapisujemy jako "en"
                # tylko jesli tekst wyglada na ASCII (angielski).
                looks_en = all(ord(c) < 128 for c in second.replace("'", "'"))
                target_lang = "en" if looks_en else only_lang + "_alt"
                if target_lang not in out:
                    out[target_lang] = second

    return out


def _looks_like_filename_echo(text: str, page_title: str) -> bool:
    """True gdy `text` to praktycznie nazwa pliku (Commons echo nazwy bez tytulu).

    Wykrywamy:
    - text == page_title bez prefiksu "File:" i bez rozszerzenia (modulo "_" vs " ")
    - text == base bez koncowego roku ("- 1893" obciete)
    Chronimy przed sytuacja gdy `extmetadata.ObjectName` zawiera tylko nazwe
    pliku (np. "Andreas Achenbach Am Strand von Scheveningen 1893") - to NIE
    jest prawdziwy tytul.
    """
    if not text or not page_title:
        return False
    base = page_title
    if base.startswith("File:"):
        base = base[len("File:"):]
    base = re.sub(r"\.(jpg|jpeg|png|gif|webp|tif|tiff|bmp|svg)$", "", base, flags=re.I)
    base = base.replace("_", " ").strip()
    t_norm = re.sub(r"\s+", " ", text).strip().lower()
    b_norm = re.sub(r"\s+", " ", base).lower()
    if t_norm == b_norm:
        return True
    # Bez "- 1893" / "- 1909" na koncu
    b_no_year = re.sub(r"\s*[-,]?\s*\d{3,4}\s*$", "", b_norm).strip()
    if b_no_year and t_norm == b_no_year:
        return True
    return False


def _parse_commons_titles_from_wikitext(
    wikitext: str,
) -> dict[str, str]:
    """Z wikitext strony File: na Commons wyciaga {lang_code: title}.

    Patrzy na pole `title=` w {{Artwork}} / {{Information}} i parsuje
    osadzone szablony jezykowe `{{en|...}}`, `{{da|...}}`, etc.
    """
    if not wikitext:
        return {}
    result: dict[str, str] = {}
    # Najpierw spróbuj wycisnac sam blok title= (albo przeszukaj cale wikitext jak nie ma).
    title_block = wikitext
    m = re.search(
        r"\|\s*[Tt]itle\s*=\s*(.+?)(?=\n\s*\|\s*\w+\s*=|\n\}\})",
        wikitext, re.DOTALL,
    )
    if m:
        title_block = m.group(1)
    for lang_match in _COMMONS_LANG_TPL_RE.finditer(title_block):
        lang = lang_match.group(1).lower()
        val = _commons_clean_text(lang_match.group(2))
        if val and lang not in result:
            result[lang] = val
    # Czasem title= zawiera goly tekst bez szablonow jezykowych - zachowaj jako "und"
    if not result:
        plain = _commons_clean_text(title_block)
        if plain and len(plain) <= 200:
            result["und"] = plain
    return result


def wikimedia_commons_lookup(
    artist: str,
    query: str,
    *,
    filename: str = "",
    limit: int = 6,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """Pelne wyszukiwanie w Wikimedia Commons - File:, Category:, Gallery.

    Zwraca dict zgodny z `wikidata_painting_lookup`:
        {
            "candidates": [...],     # wszystkie zaobserwowane tytuly (do glosowania)
            "english": "...",        # angielski tytul z extmetadata.ObjectName lub {{en|...}}
            "original_title": "...", # tytul w jezyku oryginalu (np. duńskim)
            "original_lang": "da",
            "source_url": "https://commons.wikimedia.org/wiki/File:...",
            "page_title": "File:...",
        }

    KLUCZOWA optymalizacja: jesli `filename` jest podany, najpierw probujemy
    BEZPOSREDNIO `File:<filename>` - bardzo czesto plik na dysku ma identyczna
    nazwe co plik na Commons (np. zdjecia z muzeow uploadowane przez wolontariuszy).
    """
    out: dict[str, Any] = {
        "candidates": [],
        "english": "",
        "original_title": "",
        "original_lang": "",
        "source_url": "",
        "page_title": "",
        "wikidata_qid": "",
    }
    seen_pages: set[str] = set()
    seen_cands: set[str] = set()

    def _push_cand(text: str) -> None:
        v = (text or "").strip()
        if not v:
            return
        k = v.lower()
        if k in seen_cands:
            return
        seen_cands.add(k)
        out["candidates"].append(v)

    candidate_pages: list[str] = []
    direct_stems: set[str] = set()  # stem-y plikow ktorych szukamy bezposrednio
                                    # (po nazwie pliku z dysku) - autorytatywne.
                                    # Porownujemy STEMY (bez rozszerzenia), bo
                                    # ten sam plik moze byc na Commons jako
                                    # PNG/JPG/TIF a my mamy JPG.

    def _stem_key(t: str) -> str:
        """Klucz porownania - lowercase, bez rozszerzenia, podkreslnik->spacja."""
        s = (t or "").strip()
        if s.startswith("File:"):
            s = s[len("File:"):]
        s = re.sub(r"\.(jpg|jpeg|png|gif|webp|tif|tiff|bmp|svg)$", "", s, flags=re.I)
        return s.replace("_", " ").strip().lower()

    # 1) Bezposrednio File:<filename> - najwiekszy hit-rate dla obrazow z muzeow.
    #    Sondujemy WIELE wariantow: oryginal + "name" obciety o sufiksy
    #    Windows ("-1", "-1-2", "(1)", "_full") i prefiksy ("Mockup ").
    #    Dzieki temu pliki "Andreas_Achenbach_-_Raddampfer_in_See-1-2.jpg"
    #    dopasuja sie do "File:Andreas_Achenbach_-_Raddampfer_in_See.jpg".
    if filename:
        for variant in _filename_variants(filename, max_variants=8):
            page = f"File:{variant}"
            candidate_pages.append(page)
            direct_stems.add(_stem_key(page))

    # 2) Wyszukiwanie po File: namespace (ns=6) - tu sa obrazy.
    #    UWAGA: te pages SA ZALEDWIE KANDYDATAMI, nie autorytatywnymi tytulami.
    #    Search trafia w INNE obrazy tego samego artysty (np. "Andreas Achenbach
    #    Ships in a storm on the Dutch coast" przy szukaniu "Achenbach storm")
    #    i ich english/original tytuly NIE moga byc przypisywane naszemu plikowi.
    full_q = f"{query} {artist}".strip() if artist else query
    if full_q:
        for ns in ("6", "14", "0"):
            qs = urllib.parse.urlencode(
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": full_q,
                    "srnamespace": ns,
                    "srlimit": str(limit),
                    "format": "json",
                }
            )
            data = _http_get_json(f"{COMMONS_API}?{qs}", timeout)
            if not isinstance(data, dict):
                continue
            for hit in (data.get("query", {}).get("search") or [])[:limit]:
                if not isinstance(hit, dict):
                    continue
                raw = str(hit.get("title", "")).strip()
                if not raw:
                    continue
                if raw.startswith("File:"):
                    candidate_pages.append(raw)
                else:
                    # Category:/Gallery - dodaj jako kandydata po obcięciu prefixu.
                    cleaned = raw
                    for prefix in ("Category:", "Gallery:"):
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()
                            break
                    _push_cand(cleaned)

    # Deduplikuj zachowujac kolejnosc - File: z `filename` ma najwyzszy priorytet.
    uniq_pages: list[str] = []
    for p in candidate_pages:
        if p not in seen_pages:
            seen_pages.add(p)
            uniq_pages.append(p)
        if len(uniq_pages) >= 8:  # limituje liczbe szczegolowych zapytan
            break

    if not uniq_pages:
        return out

    # 3) Pobieramy imageinfo + revisions + pageprops jednym zapytaniem.
    #    pageprops daje wikibase_item -> link do Wikidata (DARMOWY most).
    #    formatversion=2 zwraca content w `slots.main.content` (dawniej `*`).
    qs = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": "|".join(uniq_pages),
            "prop": "imageinfo|revisions|pageprops",
            "iiprop": "extmetadata|url",
            "rvprop": "content",
            "rvslots": "main",
            "formatversion": "2",
            "format": "json",
        }
    )
    data = _http_get_json(f"{COMMONS_API}?{qs}", timeout)
    # formatversion=2 -> pages to LISTA, nie dict; obslugujemy oba.
    pages_raw = ((data or {}).get("query") or {}).get("pages") or []
    if isinstance(pages_raw, dict):
        pages_dict = pages_raw
    else:
        pages_dict = {str(i): p for i, p in enumerate(pages_raw) if isinstance(p, dict)}

    # MediaWiki normalizuje "_" na " " w tytulach, wiec dopasowanie po
    # surowym kluczu nie zadziala. Uzywamy znormalizowanej formy do dopasowania.
    def _norm_title(t: str) -> str:
        return (t or "").replace("_", " ").strip().lower()

    pages_by_title: dict[str, dict[str, Any]] = {}
    for p in pages_dict.values():
        if isinstance(p, dict):
            t = p.get("title", "")
            if t:
                pages_by_title[_norm_title(t)] = p

    en_set = False
    orig_set = False
    for page_title in uniq_pages:
        p = pages_by_title.get(_norm_title(page_title))
        if not p or p.get("missing") is True or p.get("missing") is not None:
            continue
        # CZY TO JEST DIRECT MATCH (nazwa pliku z dysku)?
        # Tylko z direct matchy bierzemy autorytatywne english/original_title.
        # Search hits (inne pliki Achenbacha) zostaja TYLKO jako candidates.
        # Porownujemy po STEMIE, zeby JPG vs PNG na Commons sie dopasowal
        # (ten sam obraz moze byc uploadowany w roznych formatach).
        is_direct = _stem_key(page_title) in direct_stems
        infos = p.get("imageinfo") or []
        revs = p.get("revisions") or []
        em = (infos[0].get("extmetadata", {}) if infos else {}) or {}

        # Pageprops -> wikibase_item (Q-id w Wikidata) - DARMOWY most do Wikidata.
        wb_qid = ((p.get("pageprops") or {}).get("wikibase_item") or "").strip()
        if wb_qid and not out["wikidata_qid"]:
            out["wikidata_qid"] = wb_qid

        def _set_source_url() -> None:
            if out.get("source_url"):
                return
            if infos and infos[0].get("descriptionurl"):
                out["source_url"] = infos[0]["descriptionurl"]
            else:
                out["source_url"] = (
                    "https://commons.wikimedia.org/wiki/"
                    + urllib.parse.quote(page_title.replace(" ", "_"))
                )

        def _accept_title(text: str, page_t: str) -> str:
            """Zwroc text gdy wyglada na sensowny tytul, "" gdy do odrzucenia."""
            if not text:
                return ""
            if _looks_like_artwork_description(text):
                return ""
            if _looks_like_filename_echo(text, page_t):
                return ""
            return text

        # ZBIERAMY KANDYDATOW Z PIERWSZENSTWEM WIKITEXT NAD extmetadata.
        # Wikitext ma czysty `{{en|...}}{{de|...}}` (po jednym tytule per jezyk),
        # extmetadata.ObjectName czesto scala je w jeden ciag bez separatora.
        # formatversion=2 zwraca content w slots.main.content; format v1 w "*".
        wt_lang_titles: dict[str, str] = {}
        if revs:
            wt = ""
            try:
                slot = revs[0].get("slots", {}).get("main", {}) if isinstance(revs[0], dict) else {}
                wt = slot.get("content") or slot.get("*") or ""
                if not wt:
                    # Format v1 bez slots: rev["*"] albo rev["content"].
                    wt = revs[0].get("*") or revs[0].get("content") or ""
            except (KeyError, TypeError, AttributeError):
                wt = ""
            wt_lang_titles = _parse_commons_titles_from_wikitext(wt)

        # 3a) Wikitext - {{en|...}} / {{de|...}} / {{fr|...}} (PREFEROWANE)
        # WAZNE: english/original_title wpisujemy TYLKO z direct match - inaczej
        # tytuly innych obrazow (z ns=6 search) wycieklyby do naszego pliku.
        if wt_lang_titles:
            for v in wt_lang_titles.values():
                _push_cand(v)
            if is_direct:
                en_val = _accept_title(wt_lang_titles.get("en", ""), page_title)
                if en_val and not en_set:
                    out["english"] = en_val
                    out["page_title"] = page_title
                    _set_source_url()
                    en_set = True
                if not orig_set:
                    for lang in _ART_LANGS_PRIORITY:
                        val = _accept_title(wt_lang_titles.get(lang, ""), page_title)
                        if val and val.lower() != (out.get("english") or "").lower():
                            out["original_title"] = val
                            out["original_lang"] = lang
                            orig_set = True
                            break
                    if not orig_set:
                        for lang, val in wt_lang_titles.items():
                            if lang in ("en", "und"):
                                continue
                            v_ok = _accept_title(val, page_title)
                            if v_ok and v_ok.lower() != (out.get("english") or "").lower():
                                out["original_title"] = v_ok
                                out["original_lang"] = lang
                                orig_set = True
                                break

        # 3b) ObjectName z extmetadata - dopelnienie gdy wikitext nie wystarczyl.
        # Przy okazji probujemy rozbic SCALONE "German: X English: Y" (i bez prefixu).
        obj_name = _commons_clean_text((em.get("ObjectName") or {}).get("value", ""))
        if obj_name:
            split = _split_compound_lang_string(obj_name)
            if split:
                for v in split.values():
                    _push_cand(v)
                if is_direct:
                    en_val = _accept_title(split.get("en", ""), page_title)
                    if en_val and not en_set:
                        out["english"] = en_val
                        out["page_title"] = page_title
                        _set_source_url()
                        en_set = True
                    if not orig_set:
                        for lang in _ART_LANGS_PRIORITY:
                            val = _accept_title(split.get(lang, ""), page_title)
                            if val and val.lower() != (out.get("english") or "").lower():
                                out["original_title"] = val
                                out["original_lang"] = lang
                                orig_set = True
                                break
            else:
                obj_ok = _accept_title(obj_name, page_title)
                if obj_ok:
                    _push_cand(obj_ok)
                    if is_direct and not en_set:
                        out["english"] = obj_ok
                        out["page_title"] = page_title
                        _set_source_url()
                        en_set = True

        # 3c) Tytul z page_title (nazwy strony File:) jako fallback.
        # Gdy wikitext + ObjectName nie dały sensownego tytulu, a Commons
        # JEDNAK znalazl strone, nazwa strony zwykle ma format
        # "Andreas_Achenbach_-_Tytul.jpg" albo "Andreas_Achenbach_Am_Strand_..._1893.jpg"
        # Wycinamy artist (znamy go z parametru) i konce typu "_1893" / " - 1893",
        # zostawiajac sam tytul. To NAJWAZNIEJSZE awaryjne zrodlo dla plikow
        # z muzeow ktore na Commons maja tylko strukturyzowane dane bez {{en|...}}.
        if page_title.startswith("File:"):
            base = page_title[len("File:"):]
            base = re.sub(r"\.(jpg|jpeg|png|gif|webp|tif|tiff|bmp|svg)$", "", base, flags=re.I)
            base = base.replace("_", " ").strip()
            # Wytnij artist (z artist + reverse, "Achenbach, Andreas").
            if artist:
                a_parts = [re.escape(p) for p in artist.split() if p]
                if a_parts:
                    name_re = r"\b" + r"[\s\-]+".join(a_parts) + r"\b"
                    rev_re = r"\b" + r"[\s\-]+".join(reversed(a_parts)) + r"\b"
                    base = re.sub(name_re, "", base, flags=re.IGNORECASE)
                    base = re.sub(rev_re, "", base, flags=re.IGNORECASE)
            # Usun typowe suffixy "metadane wokol nazwy pliku":
            # - inventory number w nawiasach: "(SM 875)", "(NG 818)", "(W123)",
            #   "(inv. 1500)" - typowo numer kolekcji muzealnej
            # - rok: " 1893", " - 1893", "_1893", ", 1893"
            base = re.sub(
                r"\s*\(\s*[A-Za-z]{1,5}[.\s]*\d{1,6}[A-Za-z]?\s*\)\s*$",
                "", base,
            )
            base = re.sub(
                r"\s*\(\s*inv\.?\s*\d{1,6}[A-Za-z]?\s*\)\s*$",
                "", base, flags=re.I,
            )
            base = re.sub(r"[\s\-_,]+\d{3,4}\s*$", "", base)
            base = re.sub(r"^[\s\-_,]+|[\s\-_,]+$", "", base)
            base = re.sub(r"\s+", " ", base).strip()
            if base:
                _push_cand(base)
                # WAZNE: jesli mamy DIRECT match po dokladnej nazwie pliku
                # ale nic sensownego nie wybralismy jako english/original,
                # uzyj tej extracted formy. Tylko dla direct match - search
                # hits maja inne nazwy plikow i ich page_title nie reprezentuje
                # naszego pliku.
                if is_direct and not en_set and not orig_set:
                    # Inteligentna detekcja jezyka: ASCII to jeszcze nie EN.
                    # "Am Strand von Scheveningen" jest ASCII ale niemiecki -
                    # zawiera "von" i "am" co jest niemozliwe w EN.
                    if _looks_english_text(base):
                        out["english"] = base
                        en_set = True
                    else:
                        out["original_title"] = base
                        out["original_lang"] = _detect_non_english_lang(base)
                        orig_set = True
                    out["page_title"] = page_title
                    _set_source_url()

        # Jesli mamy juz EN + original, mozemy zakonczyc - resolver i tak
        # zaglosuje na podstawie kandydatow.
        if en_set and orig_set:
            break

    return out


def wikimedia_commons_titles(
    artist: str,
    query: str,
    *,
    filename: str = "",
    limit: int = 8,
    timeout: float = 15.0,
) -> list[str]:
    """Backward-compat wrapper - zwraca tylko liste kandydatow.

    Pelne info (english, original_title, ...) - uzyj `wikimedia_commons_lookup`.
    """
    info = wikimedia_commons_lookup(
        artist, query, filename=filename, limit=limit, timeout=timeout
    )
    return list(info.get("candidates", []))[:limit]


# ---------------------------------------------------------------------------
# Agregator: jedno zapytanie SerpAPI do wielu serwisow aukcyjnych / galerii
# ---------------------------------------------------------------------------


def english_title_for_foreign(
    artist: str,
    foreign_title: str,
    *,
    timeout: float = 20.0,
) -> str:
    """Znajdz angielski tytul obrazu znajac artyste i tytul w jezyku obcym.

    Strategia: SerpAPI Google z site: filtrem na duze galerie aukcyjne
    (invaluable, mutualart, sothebys, christies, artnet) - tam tytuly sa
    POWSZECHNIE po angielsku, bo to globalne rynki sztuki.

    Parsuje:
    - title organic_result (np. "Andreas Achenbach - The Beach at Scheveningen")
    - URL slug (np. invaluable.com/.../andreas-achenbach-the-beach-at-scheveningen-2427)

    Zwraca pusty string gdy nie znalazl niczego sensownego.
    """
    api_key = env_get("SERPAPI_KEY")
    if not api_key or not artist or not foreign_title:
        return ""
    # Restryktywny filtr na strony ktore TYPOWO publikuja po angielsku.
    en_sites = ("invaluable.com", "mutualart.com", "sothebys.com",
                "christies.com", "artnet.com", "findartinfo.com")
    sites_filter = "(" + " OR ".join(f"site:{s}" for s in en_sites) + ")"
    full_q = f'"{artist}" "{foreign_title}" {sites_filter}'
    data = _serpapi_get({
        "engine": "google",
        "q": full_q,
        "api_key": api_key,
        "hl": "en",
        "num": "10",
    }, timeout)
    if not isinstance(data, dict):
        return ""

    artist_lower = artist.lower()
    artist_slug = artist.lower().replace(" ", "-")
    candidates: list[str] = []

    for o in (data.get("organic_results") or []):
        if not isinstance(o, dict):
            continue
        # 1) Title pola - "Artist - Title" lub "Title by Artist"
        title = str(o.get("title") or "").strip()
        if title:
            # Wyciagnij czesc po artyscie (jesli jest)
            t_lower = title.lower()
            if artist_lower in t_lower:
                # Rozdziel po " - " lub " | "
                for sep in (" - ", " | ", ": ", " — "):
                    if sep in title:
                        parts = [p.strip() for p in title.split(sep) if p.strip()]
                        for part in parts:
                            if artist_lower not in part.lower() and len(part) > 3:
                                candidates.append(part)
                        break
                else:
                    # Brak separatora - sprobuj po "by"
                    m = re.split(r"\s+by\s+", title, maxsplit=1, flags=re.I)
                    if len(m) == 2:
                        candidates.append(m[0].strip())

        # 2) URL slug - typowo "/artist-slug-en-title-slug-NNNN-c-..."
        link = str(o.get("link") or "")
        if link and artist_slug in link.lower():
            # Wyciagnij path
            try:
                path = urllib.parse.urlparse(link).path
            except Exception:  # noqa: BLE001
                path = ""
            # Znajdz segment z artist slug
            for seg in path.split("/"):
                seg_lower = seg.lower()
                if artist_slug in seg_lower:
                    # Wytnij artist + ewentualne id na koncu
                    after = seg_lower.split(artist_slug, 1)[1].lstrip("-_")
                    # Usun id na koncu typu "-2427-c-a1a45b..."
                    after = re.sub(r"-\d+(?:-[a-z0-9]+)*$", "", after)
                    after = after.replace("-", " ").strip()
                    if len(after) >= 4 and after.lower() != foreign_title.lower():
                        # Title Case
                        candidates.append(after.title())
                    break

    # Filtruj smieci typowe dla katalogow aukcyjnych ("Sold at Auction",
    # "For Sale", "Lot 23", "Estimate $1,000-$2,000").
    auction_noise_re = re.compile(
        r"\b(?:"
        r"sold at auction|sold|for sale|auction|"
        r"lot\s*\d*|lot\b|"
        r"estimate|estimated|"
        r"realized|hammer price|reserve\s*price|starting\s*price|"
        r"bid|bidding|"
        r"asking\s*price|"
        r"catalog|catalogue|"
        r"price\s*(?:realized|estimate)?|"
        r"private\s*sale"
        r")\b",
        re.IGNORECASE,
    )

    def _significant_tokens(text: str) -> set[str]:
        """Tokeny >= 4 znakow, lowercase, bez stopwords ENG/DE/FR."""
        stop = {
            "the", "and", "with", "from", "into", "onto", "over", "under",
            "der", "die", "das", "von", "vom", "zur", "zum", "des", "den",
            "ein", "eine", "und", "mit", "ohne",
            "los", "las", "del", "della",
        }
        toks = re.findall(r"[A-Za-z\u00C0-\u017F]+", text.lower())
        return {t for t in toks if len(t) >= 4 and t not in stop}

    foreign_tokens = _significant_tokens(foreign_title)
    foreign_lower = foreign_title.lower()
    seen_lower: set[str] = set()

    # Najpierw zbieramy WSZYSTKICH zaakceptowanych kandydatow z ich score
    # (= overlap znaczacych tokenow z foreign_title). Wracamy najlepszego.
    scored: list[tuple[int, str]] = []
    for cand in candidates:
        c_norm = re.sub(r"\s+", " ", cand).strip()
        c_lower = c_norm.lower()
        if not c_norm or len(c_norm) < 4 or len(c_norm) > 120:
            continue
        if c_lower == foreign_lower or c_lower in seen_lower:
            continue
        if not _looks_english_text(c_norm):
            continue
        # FILTR ANTY-NOISE: kandydat zawierajacy tylko aukcyjne smieci.
        if auction_noise_re.search(c_norm):
            continue
        # WYMOG OVERLAPU: kandydat musi miec PRZYNAJMNIEJ JEDNO znaczace
        # slowo wspolne z foreign_title - inaczej jest niezwiazany. Klasyczny
        # case "Sold at Auction" dla "Am Strand von Scheveningen" - zero
        # overlapu, kandydat odrzucony.
        cand_tokens = _significant_tokens(c_norm)
        overlap = len(foreign_tokens & cand_tokens)
        if foreign_tokens and overlap == 0:
            continue
        seen_lower.add(c_lower)
        scored.append((overlap, c_norm))

    if not scored:
        return ""
    # Najlepszy overlap (stabilny - zachowuje kolejnosc oryginalna przy remisie)
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


# WikiArt URL pattern - bardzo regularny, mozna parsowac slug -> title/year/artist:
#   https://www.wikiart.org/en/ivan-aivazovsky/tempest-1855
#   https://www.wikiart.org/en/leonardo-da-vinci/mona-lisa
# Drugi segment = artist (slug), trzeci = painting-slug[-year].
_WIKIART_URL_RE = re.compile(
    r"^https?://(?:www\.)?wikiart\.org/(?:en|[a-z]{2}(?:-[a-z]{2})?)/"
    r"([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)/"
    r"([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)/?",
    re.IGNORECASE,
)
# Painting slug konczacy sie na rok (4 cyfry, opcjonalnie -1 / -2 = wariant):
_WIKIART_YEAR_TAIL_RE = re.compile(r"-((?:1[0-9]|2[01])\d{2})(?:-\d+)?$")


def _wikiart_slug_to_title(slug: str) -> str:
    """'tempest-1855' -> 'Tempest', 'mona-lisa' -> 'Mona Lisa'.

    Odetnij rok z konca, zamien myslniki na spacje, Title Case.
    """
    s = (slug or "").strip("-/ ")
    if not s:
        return ""
    s = _WIKIART_YEAR_TAIL_RE.sub("", s)
    words = [w.capitalize() for w in s.split("-") if w]
    return " ".join(words)


def _wikiart_slug_year(slug: str) -> str:
    """'tempest-1855' -> '1855', 'mona-lisa' -> ''."""
    m = _WIKIART_YEAR_TAIL_RE.search(slug or "")
    return m.group(1) if m else ""


def _wikiart_slug_to_artist(slug: str) -> str:
    """'ivan-aivazovsky' -> 'Ivan Aivazovsky'."""
    s = (slug or "").strip("-/ ")
    if not s:
        return ""
    return " ".join(w.capitalize() for w in s.split("-") if w)


def wikiart_lookup(
    artist: str, query: str, *, limit: int = 8, timeout: float = 20.0
) -> dict[str, Any]:
    """Wyszukaj tytul + autora + rok na WikiArt przez Google site filter.

    WikiArt sam jest za Cloudflare (nie da sie GET-owac bezposrednio bez
    przegladarki), ale jego URL-e maja super-regularny wzor:
        https://www.wikiart.org/en/<artist-slug>/<painting-slug>[-<year>]
    Wyciagamy z Google search (przez SerpAPI) URL-e do wikiart i parsujemy
    slugi - daje to STRUCTURED dane (title + year + artist) ZANIM zaczniemy
    glosowac w title_resolver.

    Returns:
        {
            "candidates": [...]      # tytuly do glosowania
            "english": "Tempest",     # najlepszy tytul (slug -> Title Case)
            "year": "1855",          # rok jesli slug konczyl sie na 4 cyfry
            "artist": "Ivan Aivazovsky",   # imie z artist-slug
            "source_url": "https://...",  # link do strony obrazu
        }
    """
    out: dict[str, Any] = {
        "candidates": [], "english": "", "year": "",
        "artist": "", "source_url": "",
    }
    api_key = env_get("SERPAPI_KEY")
    q = (query or "").strip()
    if not api_key or not q:
        return out
    if artist:
        full_q = f'"{q}" "{artist}" site:wikiart.org'
    else:
        full_q = f'"{q}" site:wikiart.org'
    data = _serpapi_get({
        "engine": "google",
        "q": full_q,
        "api_key": api_key,
        "hl": "en",
        "num": "10",
    }, timeout)
    if not isinstance(data, dict):
        return out
    parsed: list[dict[str, str]] = []
    # Slug-i, ktore NIE sa nazwiskami artystow (kategorie/tagi WikiArt).
    _NOT_ARTIST_SLUGS = {
        "tag", "tags", "style", "styles", "genre", "genres", "media",
        "movement", "movements", "subject", "subjects",
        "artists-by-art-movement", "artists-by-genre", "artists-by-nation",
        "artists-by-school", "artists-by-period",
    }
    _NOT_PAINTING_SLUGS = {
        "all-works", "by-style", "by-genre", "biography",
        "albums", "tags", "follow", "mentioned-in",
    }
    for o in data.get("organic_results", []) or []:
        if not isinstance(o, dict):
            continue
        link = str(o.get("link") or "").split("?")[0].split("#")[0]
        if not link:
            continue
        m = _WIKIART_URL_RE.match(link)
        if not m:
            continue
        artist_slug, painting_slug = m.group(1).lower(), m.group(2).lower()
        if artist_slug in _NOT_ARTIST_SLUGS:
            continue
        if painting_slug in _NOT_PAINTING_SLUGS:
            continue
        title = _wikiart_slug_to_title(painting_slug)
        if not title:
            continue
        year = _wikiart_slug_year(painting_slug)
        artist_name = _wikiart_slug_to_artist(artist_slug)
        parsed.append({
            "title": title,
            "year": year,
            "artist": artist_name,
            "url": link,
        })
        if len(parsed) >= limit:
            break
    if not parsed:
        return out

    # Tokenizacja query + artist_param dla scoringu.
    def _tok(s: str) -> set[str]:
        return {
            t.lower()
            for t in re.findall(r"[A-Za-z\u00C0-\u017F]+", s or "")
            if len(t) >= 3
        }
    q_tokens = _tok(q)
    artist_tokens = _tok(artist)

    # FILTR: jesli mamy artist hint i artist_name z URL slug NIE matchuje nawet
    # jednego tokena, drop. To zapobiega trafianiu w obraz INNEGO autora (np.
    # WikiArt URL Repina dla query "Aivazovsky tempest").
    if artist_tokens:
        compatible = []
        for entry in parsed:
            a_t = _tok(entry["artist"])
            if a_t & artist_tokens:
                compatible.append(entry)
        if compatible:
            parsed = compatible

    # FILTR: kazdy entry musi miec PRZYNAJMNIEJ JEDEN wspolny token miedzy
    # query a (title + artist) - inaczej URL przypadkiem zawiera query gdzies
    # w nawigacji strony, ale painting/artist NIE jest tym o co pytamy.
    def _overlap(entry: dict[str, str]) -> int:
        return len(q_tokens & (_tok(entry["title"]) | _tok(entry["artist"])))

    parsed = [e for e in parsed if _overlap(e) >= 1]
    if not parsed:
        return out

    # Wybierz najlepszy: max overlap z query (preferujac match w title nad artist).
    def _score(entry: dict[str, str]) -> tuple[int, int, int]:
        t_o = len(q_tokens & _tok(entry["title"]))
        a_o = len(q_tokens & _tok(entry["artist"]))
        return (t_o, a_o, len(entry["title"]))   # title-overlap > artist-overlap > krotszy tytul
    parsed.sort(key=_score, reverse=True)
    best = parsed[0]
    out["english"] = best["title"]
    out["year"] = best["year"]
    out["artist"] = best["artist"]
    out["source_url"] = best["url"]
    seen: set[str] = set()
    for entry in parsed:
        t = entry["title"]
        k = t.lower()
        if k and k not in seen:
            seen.add(k)
            out["candidates"].append(t)
    return out


def art_sites_titles(
    artist: str, query: str, *, limit: int = 12, timeout: float = 25.0
) -> list[str]:
    """Wyszukaj tytul w serwisach sztuki przez Google (jedno zapytanie SerpAPI).

    Uzywa filtra ``site:`` dla wszystkich glownych serwisow aukcyjnych
    i galeryjnych (Invaluable, MutualArt, Artnet, Sothebys, Christies,
    Fine Art America, Google Arts & Culture, art.com, pixels.com,
    findartinfo, bruun-rasmussen, picryl, wikiart). To kosztuje tylko
    1 wywolanie SerpAPI - wynikow jest sporo i resolver wyfiltruje smieci.
    """
    api_key = env_get("SERPAPI_KEY")
    q = (query or "").strip()
    if not api_key or not q:
        return []
    sites_filter = "(" + " OR ".join(f"site:{s}" for s in _ART_SITES) + ")"
    if artist:
        full_q = f'"{q}" "{artist}" {sites_filter}'
    else:
        full_q = f'"{q}" painting {sites_filter}'
    data = _serpapi_get(
        {
            "engine": "google",
            "q": full_q,
            "api_key": api_key,
            "hl": "en",
            "num": "10",
        },
        timeout,
    )
    if not isinstance(data, dict):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for o in data.get("organic_results", []) or []:
        if not isinstance(o, dict):
            continue
        t = o.get("title")
        if not t:
            continue
        s = str(t).strip()
        key = s.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(s)
        if len(out) >= limit:
            break
    return out
