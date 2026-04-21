"""Reverse image search z wielu silnikow (multi-engine).

Silniki (wszystkie przez SerpAPI - jeden klucz `SERPAPI_KEY`):
- Google Lens     (`engine=google_lens`,        param: `url`)
- Yandex Images   (`engine=yandex_images`,      param: `url`)         - dobry dla reprodukcji muzealnych
- Bing Reverse    (`engine=bing_reverse_image`, param: `image_url`)   - dobry dla obrazow zachodnich

Architektura:
- Kazdy silnik = funkcja `_search_<name>(image_url) -> list[str]`.
- `search_one_engine(name, urls, ...)` probuje silnik kolejno na URL-ach
  dopoki ktorys nie zwroci kandydatow (z preferencja 0x0.st > catbox).
- `search_all_engines(urls, ...)` aggreguje wyniki ze wszystkich silnikow,
  zwraca `MultiVisualResult` z listami kandydatow per silnik + super-listą.

Wszystkie silniki dziela `SERPAPI_KEY`. Zwroc tytuly NIESKLEJONE - tytul
deduplikacji i wyboru robi `title_resolver`.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from .env_loader import get as env_get
from .serpapi_status import SerpApiLimitError, raise_if_serpapi_limit

SERPAPI_URL = "https://serpapi.com/search.json"


class VisualSearchError(RuntimeError):
    pass


@dataclass
class EngineResult:
    """Wynik z jednego silnika dla jednego pliku."""
    engine: str
    titles: list[str] = field(default_factory=list)
    source_url: str = ""        # link do strony zrodlowej (np. wikipedia)
    used_image_url: str = ""    # ktory URL obrazu zadzialal
    error: str = ""             # pusty = OK; wypelniony = co poszlo nie tak
    elapsed: float = 0.0


@dataclass
class MultiVisualResult:
    """Aggregat z wszystkich silnikow."""
    per_engine: dict[str, EngineResult] = field(default_factory=dict)
    all_titles: list[str] = field(default_factory=list)  # union, kolejnosc zachowana

    def best_source_url(self) -> str:
        """Pierwszy nie-pusty source_url z silnikow w kolejnosci priorytetu."""
        for eng in ("google_lens", "yandex_images", "bing_reverse_image"):
            r = self.per_engine.get(eng)
            if r and r.source_url:
                return r.source_url
        return ""

    def has_any_titles(self) -> bool:
        return bool(self.all_titles)


# Domyslne timeouty - SerpAPI lubi byc nerwowe na obciazonej sieci.
_DEFAULT_TIMEOUT = 60.0
# Krotsza pauza miedzy retry - SerpAPI bywa flakey i 1 retry zazwyczaj wystarczy.
_RETRY_DELAY = 1.5
_MAX_RETRIES_PER_URL = 1   # 1 = jedna proba + jeden retry = lacznie 2 calls per URL
# Preferowane hostingi do reverse-image - 0x0.st dziala dla Lens znacznie czesciej
# niz catbox.moe (Google traktuje catbox jako "podejrzane" zrodlo). uguu.se jest
# pomiedzy - lepiej widziany niz catbox, ale mniej znany od 0x0.st.
# Ta sama kolejnosc dla Lens/Yandex/Bing - wszystkie silniki maja ten sam problem
# z catbox. URL probowany jest sekwencyjnie az ktorys da wynik.
HOST_PREFERENCE_LENS = ("0x0.st", "uguu.se", "catbox.moe")
HOST_PREFERENCE_BING = ("0x0.st", "uguu.se", "catbox.moe")
HOST_PREFERENCE_YANDEX = ("0x0.st", "uguu.se", "catbox.moe")


# ----------------------------- HTTP helper -----------------------------

def _serpapi_get(params: dict[str, str], *, timeout: float) -> dict:
    """GET https://serpapi.com/search.json z keep-alive (requests) lub urllib.

    Zwraca sparsowany JSON. Rzuca:
        - SerpApiLimitError - gdy odpowiedz wskazuje wyczerpany limit / zly klucz
          (HTTP 401/403/429 lub `data.error` z odpowiednim wzorcem). To pozwala
          GUI wylapac i pokazac dialog "wpisz nowy klucz".
        - VisualSearchError - przy innych bledach HTTP / parse.
    """
    status_code = 200
    data: dict | None = None
    try:
        from .http_client import get_session
        sess = get_session()
        try:
            resp = sess.get(SERPAPI_URL, params=params, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            raise VisualSearchError(f"polaczenie z SerpAPI: {e}") from e
        status_code = resp.status_code
        try:
            data = resp.json()
        except json.JSONDecodeError:
            data = None
        # Sprawdz limit zanim rzucimy zwykly HTTP error - nawet HTTP 401 powinien
        # pojsc do dialogu o nowy klucz, nie do generic VisualSearchError.
        raise_if_serpapi_limit(data, status_code)
        if status_code >= 400:
            raise VisualSearchError(f"SerpAPI HTTP {status_code}: {resp.reason}")
        if data is None:
            raise VisualSearchError("SerpAPI: niepoprawny JSON")
        return data
    except ImportError:
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            f"{SERPAPI_URL}?{qs}",
            headers={"User-Agent": "nazwijobraz/1.0"},
        )
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=timeout) as resp:
                status_code = resp.status
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = None
                raise_if_serpapi_limit(data, status_code)
                if data is None:
                    raise VisualSearchError("SerpAPI: niepoprawny JSON")
                return data
        except urllib.error.HTTPError as e:
            try:
                err_raw = e.read().decode("utf-8", errors="replace")
                err_data = json.loads(err_raw)
            except (OSError, json.JSONDecodeError):
                err_data = None
            raise_if_serpapi_limit(err_data, e.code)
            raise VisualSearchError(f"SerpAPI HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise VisualSearchError(f"polaczenie z SerpAPI: {e.reason}") from e


# ----------------------------- ENGINES -----------------------------

def _search_google_lens(image_url: str, *, api_key: str, timeout: float) -> tuple[list[str], str]:
    """Google Lens reverse image search.

    Returns: (lista tytulow, source_url).
    Rzuca VisualSearchError przy bledzie HTTP/SerpAPI; przy 'no results' zwraca ([], "").
    """
    data = _serpapi_get(
        {"engine": "google_lens", "url": image_url, "api_key": api_key, "hl": "en"},
        timeout=timeout,
    )
    if isinstance(data, dict) and data.get("error"):
        err = str(data["error"])
        # "hasn't returned any results" jest INFO, nie bledem - zwracamy puste.
        if "any results" in err.lower() or "no results" in err.lower():
            return ([], "")
        raise VisualSearchError(f"google_lens: {err}")
    titles: list[str] = []
    source_url = ""
    kg = data.get("knowledge_graph") if isinstance(data, dict) else None
    if isinstance(kg, dict):
        if kg.get("title"):
            titles.append(str(kg["title"]))
        if kg.get("source_url"):
            source_url = str(kg["source_url"])
    elif isinstance(kg, list):
        for entry in kg[:3]:
            if isinstance(entry, dict) and entry.get("title"):
                titles.append(str(entry["title"]))
    matches = data.get("visual_matches") if isinstance(data, dict) else None
    if isinstance(matches, list):
        for m in matches[:8]:
            if not isinstance(m, dict):
                continue
            t = m.get("title") or m.get("source")
            if t:
                titles.append(str(t))
            if not source_url:
                src = m.get("link") or m.get("source")
                if isinstance(src, str):
                    source_url = src
    return (titles, source_url)


def _search_yandex_images(image_url: str, *, api_key: str, timeout: float) -> tuple[list[str], str]:
    """Yandex Images reverse image search.

    Mocna strona: dobre matchowanie reprodukcji muzealnych, slowianskie zrodla.
    Returns: (lista tytulow, source_url).
    """
    data = _serpapi_get(
        {"engine": "yandex_images", "url": image_url, "api_key": api_key},
        timeout=timeout,
    )
    if isinstance(data, dict) and data.get("error"):
        err = str(data["error"])
        if "any results" in err.lower() or "no results" in err.lower():
            return ([], "")
        raise VisualSearchError(f"yandex_images: {err}")
    titles: list[str] = []
    source_url = ""
    # 1) knowledge_graph (gdy Yandex zna obraz)
    kg = data.get("knowledge_graph") if isinstance(data, dict) else None
    if isinstance(kg, dict):
        if kg.get("title"):
            titles.append(str(kg["title"]))
        if kg.get("source_url"):
            source_url = str(kg["source_url"])
    # 2) image_results - lista stron, na ktorych ten obraz wystepuje
    img_results = data.get("image_results") if isinstance(data, dict) else None
    if isinstance(img_results, list):
        for m in img_results[:10]:
            if not isinstance(m, dict):
                continue
            t = m.get("title") or m.get("snippet") or m.get("source")
            if t:
                titles.append(str(t))
            if not source_url:
                src = m.get("link") or m.get("source")
                if isinstance(src, str):
                    source_url = src
    # 3) similar_images - czasem tytuly podobnych obrazow daja nazwe dziela
    sim = data.get("similar_images") if isinstance(data, dict) else None
    if isinstance(sim, list):
        for m in sim[:5]:
            if isinstance(m, dict) and m.get("title"):
                titles.append(str(m["title"]))
    # 4) image_tags - autorytatywne, krotkie etykiety (czesto = tytul dziela)
    tags = data.get("image_tags") if isinstance(data, dict) else None
    if isinstance(tags, list):
        for t in tags[:5]:
            if isinstance(t, dict) and t.get("text"):
                titles.append(str(t["text"]))
            elif isinstance(t, str):
                titles.append(t)
    return (titles, source_url)


def _search_bing_reverse(image_url: str, *, api_key: str, timeout: float) -> tuple[list[str], str]:
    """Bing Reverse Image (Visual) search.

    Mocna strona: dobre matchowanie obrazow z popularnych galerii zachodnich.
    Returns: (lista tytulow, source_url).
    """
    data = _serpapi_get(
        {
            "engine": "bing_reverse_image",
            "image_url": image_url,
            "api_key": api_key,
            "mkt": "en-US",
        },
        timeout=timeout,
    )
    if isinstance(data, dict) and data.get("error"):
        err = str(data["error"])
        if "any results" in err.lower() or "no results" in err.lower():
            return ([], "")
        raise VisualSearchError(f"bing_reverse: {err}")
    titles: list[str] = []
    source_url = ""
    # 1) knowledge_graph (rzadkie ale precyzyjne)
    kg = data.get("knowledge_graph") if isinstance(data, dict) else None
    if isinstance(kg, dict):
        if kg.get("title"):
            titles.append(str(kg["title"]))
        if kg.get("source"):
            source_url = str(kg["source"])
    # 2) image_results / inline_images / pages_with_matching_images - rozne nazwy
    for key in ("image_results", "inline_images", "pages_with_matching_images", "visual_matches"):
        arr = data.get(key) if isinstance(data, dict) else None
        if not isinstance(arr, list):
            continue
        for m in arr[:10]:
            if not isinstance(m, dict):
                continue
            t = m.get("title") or m.get("name") or m.get("snippet")
            if t:
                titles.append(str(t))
            if not source_url:
                src = m.get("link") or m.get("source") or m.get("url")
                if isinstance(src, str):
                    source_url = src
    # 3) related_searches - tagi
    rel = data.get("related_searches") if isinstance(data, dict) else None
    if isinstance(rel, list):
        for r in rel[:5]:
            if isinstance(r, dict) and r.get("query"):
                titles.append(str(r["query"]))
    return (titles, source_url)


# ----------------------------- DRIVER -----------------------------

# Mapa: nazwa silnika -> funkcja silnika.
_ENGINES: dict[str, Callable[[str], tuple[list[str], str]]] = {
    "google_lens": _search_google_lens,         # type: ignore[dict-item]
    "yandex_images": _search_yandex_images,     # type: ignore[dict-item]
    "bing_reverse_image": _search_bing_reverse, # type: ignore[dict-item]
}

# Domyslna kolejnosc silnikow - Google Lens najlepszy dla obrazow z internetu,
# Yandex z dobrym pokryciem reprodukcji muzealnych (zwlaszcza slowianskich),
# Bing dla zachodnich galerii i stronek aukcyjnych.
DEFAULT_ENGINES: tuple[str, ...] = ("google_lens", "yandex_images", "bing_reverse_image")


def _ordered_urls(urls: dict[str, str], preference: tuple[str, ...]) -> list[str]:
    """Zwraca listy URL-ow w preferowanej kolejnosci hostow.

    `urls` to dict {nazwa_hosta: url}. `preference` to tuple nazw hostow
    od najbardziej preferowanego. URL-e hostow nie wymienionych w preference
    ladaja na koncu (defensywa).
    """
    ordered: list[str] = []
    for host in preference:
        if host in urls and urls[host]:
            ordered.append(urls[host])
    for host, url in urls.items():
        if host not in preference and url and url not in ordered:
            ordered.append(url)
    return ordered


def search_one_engine(
    engine: str,
    urls: dict[str, str],
    *,
    api_key: str = "",
    timeout: float = _DEFAULT_TIMEOUT,
    max_retries: int = _MAX_RETRIES_PER_URL,
) -> EngineResult:
    """Probuje silnik na URL-ach po kolei (preferencja hosta) z retry per URL.

    Sukces = silnik zwrocil >=1 tytul. Pierwsza udana proba konczy szukanie
    dla tego silnika. URL-e i retry sa probowane sekwencyjnie - silnik moze
    miec rate-limit, wiec rownolegle nie ma sensu.
    """
    if not api_key:
        api_key = env_get("SERPAPI_KEY") or ""
    fn = _ENGINES.get(engine)
    if fn is None:
        return EngineResult(engine=engine, error=f"nieznany silnik: {engine}")
    if not api_key:
        return EngineResult(engine=engine, error="brak SERPAPI_KEY")

    if engine == "yandex_images":
        ordered = _ordered_urls(urls, HOST_PREFERENCE_YANDEX)
    elif engine == "bing_reverse_image":
        ordered = _ordered_urls(urls, HOST_PREFERENCE_BING)
    else:
        ordered = _ordered_urls(urls, HOST_PREFERENCE_LENS)
    if not ordered:
        return EngineResult(engine=engine, error="brak URL-ow do sprawdzenia")

    last_err = ""
    t0 = time.monotonic()
    for img_url in ordered:
        for attempt in range(max_retries + 1):
            try:
                titles, source_url = fn(img_url, api_key=api_key, timeout=timeout)
                if titles:
                    return EngineResult(
                        engine=engine,
                        titles=titles,
                        source_url=source_url,
                        used_image_url=img_url,
                        elapsed=time.monotonic() - t0,
                    )
                # Brak wynikow ale call sie udal - sprobujemy ponownie / inny URL.
                last_err = "no results"
            except SerpApiLimitError:
                # Limit wyczerpany - propagujemy w gore zeby GUI moglo pokazac dialog.
                # Bez tego wszystkie pozostale pliki w pool tez bezsensownie odpalalyby
                # SerpAPI dostajac ten sam blad.
                raise
            except VisualSearchError as e:
                last_err = str(e)
            except Exception as e:  # noqa: BLE001
                last_err = f"{type(e).__name__}: {e}"
            if attempt < max_retries:
                time.sleep(_RETRY_DELAY)
    return EngineResult(
        engine=engine,
        error=last_err or "brak wynikow z zadnej proby",
        elapsed=time.monotonic() - t0,
    )


def search_all_engines(
    urls: dict[str, str],
    *,
    engines: tuple[str, ...] = DEFAULT_ENGINES,
    api_key: str = "",
    timeout: float = _DEFAULT_TIMEOUT,
    parallel: bool = True,
) -> MultiVisualResult:
    """Probuje wszystkich silnikow (rownolegle albo sekwencyjnie).

    `parallel=True` pala wszystkich naraz - kazdy file kosztuje 1 SerpAPI call
    per silnik niezaleznie. Latency = max(silniki) zamiast sum(silniki).
    """
    if not api_key:
        api_key = env_get("SERPAPI_KEY") or ""

    results: dict[str, EngineResult] = {}
    limit_error: SerpApiLimitError | None = None
    if parallel:
        with ThreadPoolExecutor(max_workers=max(1, len(engines)), thread_name_prefix="vis") as pool:
            futs = {
                pool.submit(
                    search_one_engine, eng, urls,
                    api_key=api_key, timeout=timeout,
                ): eng
                for eng in engines
            }
            for fut in as_completed(futs):
                eng = futs[fut]
                try:
                    results[eng] = fut.result()
                except SerpApiLimitError as e:
                    # Zapisz, propaguj na koncu (zbieramy po wszystkich futures
                    # zeby nie zostawic kuplowanych watkow w pool).
                    limit_error = e
                    results[eng] = EngineResult(engine=eng, error=f"limit: {e.reason}")
                except Exception as e:  # noqa: BLE001
                    results[eng] = EngineResult(engine=eng, error=f"{type(e).__name__}: {e}")
    else:
        for eng in engines:
            try:
                results[eng] = search_one_engine(eng, urls, api_key=api_key, timeout=timeout)
            except SerpApiLimitError as e:
                limit_error = e
                results[eng] = EngineResult(engine=eng, error=f"limit: {e.reason}")
                # W trybie sekwencyjnym konczymy od razu - nie ma sensu probowac dalej.
                break

    if limit_error is not None:
        raise limit_error

    # Zlep wszystkie tytuly (zachowujac kolejnosc i deduplikujac case-insensitive).
    seen: set[str] = set()
    all_titles: list[str] = []
    # Najpierw tytuly z preferowanego silnika (Google Lens), potem reszta.
    for eng in engines:
        r = results.get(eng)
        if not r:
            continue
        for t in r.titles:
            key = t.strip().lower()
            if key and key not in seen:
                seen.add(key)
                all_titles.append(t)

    return MultiVisualResult(per_engine=results, all_titles=all_titles)
