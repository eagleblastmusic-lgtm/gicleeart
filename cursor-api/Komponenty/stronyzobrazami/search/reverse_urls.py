"""Reverse image search — wyciaganie linkow do stron muzeow z SerpAPI."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from Komponenty.nazwijobraz.env_loader import get as env_get

SERPAPI_URL = "https://serpapi.com/search.json"

_LINK_KEYS = (
    "visual_matches",
    "image_results",
    "inline_images",
    "pages_with_matching_images",
    "similar_images",
)


@dataclass
class ReverseLink:
    url: str
    title: str = ""
    engine: str = ""


@dataclass
class ReverseImageResult:
    links: list[ReverseLink] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    uploaded_urls: dict[str, str] = field(default_factory=dict)


def serpapi_key() -> str:
    return (env_get("SERPAPI_KEY") or "").strip()


def _serpapi_get(params: dict[str, str], *, timeout: float) -> dict:
    try:
        from Komponenty.nazwijobraz.http_client import get_session
        from Komponenty.nazwijobraz.serpapi_status import raise_if_serpapi_limit

        resp = get_session().get(SERPAPI_URL, params=params, timeout=timeout)
        raise_if_serpapi_limit(resp.json() if resp.content else None, resp.status_code)
        if resp.status_code >= 400:
            raise RuntimeError(f"SerpAPI HTTP {resp.status_code}")
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError("SerpAPI: niepoprawny JSON")
        return data
    except ImportError:
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            f"{SERPAPI_URL}?{qs}",
            headers={"User-Agent": "stronyzobrazami/1.0"},
        )
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise RuntimeError("SerpAPI: niepoprawny JSON")
            return data


def _append_link(out: list[ReverseLink], seen: set[str], url: str, *, title: str, engine: str) -> None:
    u = (url or "").strip()
    if not u.startswith("http"):
        return
    key = u.lower().rstrip("/")
    if key in seen:
        return
    seen.add(key)
    out.append(ReverseLink(url=u, title=(title or "").strip(), engine=engine))


def _links_from_payload(data: dict, *, engine: str) -> tuple[list[ReverseLink], list[str]]:
    links: list[ReverseLink] = []
    titles: list[str] = []
    seen: set[str] = set()

    kg = data.get("knowledge_graph")
    if isinstance(kg, dict):
        if kg.get("title"):
            titles.append(str(kg["title"]))
        src = kg.get("source_url") or kg.get("source")
        if isinstance(src, str):
            _append_link(links, seen, src, title=str(kg.get("title") or ""), engine=engine)
    elif isinstance(kg, list):
        for entry in kg[:3]:
            if isinstance(entry, dict) and entry.get("title"):
                titles.append(str(entry["title"]))

    for key in _LINK_KEYS:
        arr = data.get(key)
        if not isinstance(arr, list):
            continue
        for m in arr[:20]:
            if not isinstance(m, dict):
                continue
            t = str(m.get("title") or m.get("name") or m.get("snippet") or m.get("source") or "")
            if t:
                titles.append(t)
            for lk in ("link", "source", "url"):
                src = m.get(lk)
                if isinstance(src, str):
                    _append_link(links, seen, src, title=t, engine=engine)

    tags = data.get("image_tags")
    if isinstance(tags, list):
        for t in tags[:8]:
            if isinstance(t, dict) and t.get("text"):
                titles.append(str(t["text"]))
            elif isinstance(t, str) and t.strip():
                titles.append(t.strip())

    return links, titles


def _engine_params(engine: str, image_url: str, api_key: str) -> dict[str, str]:
    if engine == "google_lens":
        return {"engine": "google_lens", "url": image_url, "api_key": api_key, "hl": "en"}
    if engine == "yandex_images":
        return {"engine": "yandex_images", "url": image_url, "api_key": api_key}
    if engine == "bing_reverse_image":
        return {"engine": "bing_reverse_image", "image_url": image_url, "api_key": api_key, "mkt": "en-US"}
    raise ValueError(f"Nieznany silnik: {engine}")


def reverse_image_search(
    hosted_urls: dict[str, str],
    *,
    engines: tuple[str, ...] = ("google_lens", "yandex_images", "bing_reverse_image"),
    api_key: str = "",
    timeout: float = 60.0,
) -> ReverseImageResult:
    """Odpytuje silniki reverse-image; zwraca unikalne linki i tytuly."""
    key = (api_key or serpapi_key()).strip()
    out = ReverseImageResult(uploaded_urls=dict(hosted_urls))
    if not key:
        out.errors.append("Brak SERPAPI_KEY w cursor-api/.env (reverse image search).")
        return out
    if not hosted_urls:
        out.errors.append("Brak publicznego URL obrazu (upload nieudany).")
        return out

    from Komponenty.nazwijobraz.visual_search import (
        HOST_PREFERENCE_BING,
        HOST_PREFERENCE_LENS,
        HOST_PREFERENCE_YANDEX,
        _ordered_urls,
    )

    pref = {
        "google_lens": HOST_PREFERENCE_LENS,
        "yandex_images": HOST_PREFERENCE_YANDEX,
        "bing_reverse_image": HOST_PREFERENCE_BING,
    }

    all_links: list[ReverseLink] = []
    all_titles: list[str] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for engine in engines:
        ordered = _ordered_urls(hosted_urls, pref.get(engine, HOST_PREFERENCE_LENS))
        engine_ok = False
        last_err = ""
        for img_url in ordered:
            try:
                data = _serpapi_get(_engine_params(engine, img_url, key), timeout=timeout)
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
                continue
            if isinstance(data, dict) and data.get("error"):
                err = str(data["error"])
                if "any results" in err.lower() or "no results" in err.lower():
                    last_err = "brak wynikow"
                    continue
                last_err = err
                continue
            links, titles = _links_from_payload(data, engine=engine)
            if links or titles:
                engine_ok = True
                for link in links:
                    k = link.url.lower().rstrip("/")
                    if k not in seen_urls:
                        seen_urls.add(k)
                        all_links.append(link)
                for t in titles:
                    tl = t.lower().strip()
                    if tl and tl not in seen_titles:
                        seen_titles.add(tl)
                        all_titles.append(t)
                break
        if not engine_ok:
            out.errors.append(f"{engine}: {last_err or 'brak wynikow'}")

    out.links = all_links
    out.titles = all_titles
    return out
