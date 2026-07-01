"""Szybki test polaczenia ze zrodlami wyszukiwania."""

from __future__ import annotations

import urllib.parse

from .adapters import (
    GETTY_SEARCH,
    MET_BASE,
    SMITHSONIAN_BASE,
)
from .belvedere_iiif import belvedere_search_url
from .env_keys import (
    fng_api_key,
    smithsonian_api_key,
    europeana_api_key,
    cooper_hewitt_access_token,
    nypl_api_token,
)
from .iiif_presentation_search import ALBERTINA_IIIF_SEARCH, iiif_search_url
from .http import get_json, post_json
from .newfields_api import NEWFIELDS_SEARCH
from .registry import SourceDef
from .rijks_lod import RIJKS_SEARCH

_PROBE_TIMEOUT = 12.0


def test_source(src: SourceDef) -> tuple[bool, str]:
    try:
        if src.source_id == "met":
            get_json(f"{MET_BASE}/objects/1", timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "artic":
            get_json("https://api.artic.edu/api/v1/artworks/1?fields=id", timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "cleveland":
            get_json(
                "https://openaccess-api.clevelandart.org/api/artworks/?has_image=1&limit=1",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "smk":
            get_json(
                "https://api.smk.dk/api/v1/art/search/?keys=test&rows=1&lang=en",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "mia":
            get_json("https://search.artsmia.org/id:1", timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "smithsonian":
            key = smithsonian_api_key()
            if not key:
                return False, "Brak SMITHSONIAN_API_KEY"
            get_json(
                f"{SMITHSONIAN_BASE}?{urllib.parse.urlencode({'api_key': key, 'q': 'art', 'rows': 1})}",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "rijks":
            get_json(f"{RIJKS_SEARCH}?imageAvailable=true&title=test", timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "getty":
            get_json(f"{GETTY_SEARCH}?{urllib.parse.urlencode({'q': 'painting', 'size': 1})}", timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "belvedere":
            get_json(belvedere_search_url("art"), timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "newfields":
            post_json(NEWFIELDS_SEARCH, {"searchTerm": "painting", "from": 0}, timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "nga":
            from . import local_data as ld

            ld._load_nga()
            return True, "CSV w cache"
        if src.source_id == "walters":
            from .walters_images import walters_preview_url

            walters_preview_url("7")
            return True, "CSV w cache"
        if src.source_id == "yale":
            get_json("https://manifests.collections.yale.edu/ycba/obj/1772", timeout=_PROBE_TIMEOUT)
            return True, "Manifest IIIF OK (katalog WWW moze blokowac boty)"
        if src.source_id == "albertina":
            get_json(iiif_search_url(ALBERTINA_IIIF_SEARCH, "art"), timeout=_PROBE_TIMEOUT)
            return True, "OK"
        if src.source_id == "paris_musees":
            from .paris_musees_api import paris_musees_health_probe

            return paris_musees_health_probe()
        if src.source_id == "fng":
            key = fng_api_key()
            if not key:
                return False, "Brak FNG_API_KEY"
            from .fng_api import KOKOELMA_API

            post_json(
                f"{KOKOELMA_API}/v1/search",
                {"searchTerms": ["art"], "hasImage": True},
                headers={"x-api-key": key},
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK (kokoelma API)"
        if src.source_id == "loc":
            get_json(
                "https://www.loc.gov/search/?fo=json&q=art&at=results&c=1&fa=online-format:image",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "wellcome":
            get_json(
                "https://api.wellcomecollection.org/catalogue/v2/works?query=art&pageSize=1",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "tepapa":
            get_json(
                "https://collections.tepapa.govt.nz/api/search?q=art&type=Object",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "risd":
            get_json(
                "https://risdmuseum.org/api/v1/collection?search_api_fulltext=art&items_per_page=1",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "europeana":
            key = europeana_api_key()
            if not key:
                return False, "Brak EUROPEANA_API_KEY"
            get_json(
                f"https://api.europeana.eu/record/v2/search.json?{urllib.parse.urlencode({'wskey': key, 'query': 'art', 'rows': 1})}",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "cooper_hewitt":
            token = cooper_hewitt_access_token()
            if not token:
                return False, "Brak COOPER_HEWITT_ACCESS_TOKEN"
            get_json(
                f"https://api.collection.cooperhewitt.org/rest/?{urllib.parse.urlencode({'method': 'cooperhewitt.search.objects', 'access_token': token, 'query': 'design', 'per_page': 1})}",
                timeout=_PROBE_TIMEOUT,
            )
            return True, "OK"
        if src.source_id == "nypl":
            token = nypl_api_token()
            if not token:
                return False, "Brak NYPL_API_TOKEN"
            get_json(
                "https://api.repo.nypl.org/api/v2/items/search?q=art&per_page=1",
                timeout=_PROBE_TIMEOUT,
                headers={"Authorization": f'Token token="{token}"'},
            )
            return True, "OK"
        if src.source_id == "birmingham_trust":
            from .birmingham_trust_api import search_birmingham_trust

            rows = search_birmingham_trust(query="art", limit=1)
            if rows:
                return True, "OK"
            return True, "OK (brak wynikow testowych)"
        if not src.api and src.web_fallback:
            return True, "Wyszukiwanie WWW (link w wynikach)"
        return False, "Brak testu API"
    except Exception as exc:
        return False, str(exc)[:120]


def test_sources(sources: list[SourceDef]) -> list[tuple[str, bool, str]]:
    return [(src.name, *test_source(src)) for src in sources]
