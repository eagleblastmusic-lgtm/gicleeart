"""Paris Musées — GraphQL API (token) + fallback HTML search (WAF blokuje GraphQL POST)."""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request

from .env_keys import paris_musees_api_token
from .http import USER_AGENT, post_json

PARIS_GRAPHQL = "https://apicollections.parismusees.paris.fr/graphql"
PUBLIC_BASE = "https://www.parismuseescollections.paris.fr/en"
PUBLIC_SEARCH = f"{PUBLIC_BASE}/recherche/type/oeuvre"

_ARTICLE_RE = re.compile(
    r'<article[^>]+about="(?P<path>/en/[^"]+)"[^>]*>(?P<body>.*?)</article>',
    re.S | re.I,
)
_TITLE_RE = re.compile(r"<h3[^>]*>([^<]+)", re.I)
_IMG_RE = re.compile(r'src="(https://apicollections\.parismusees\.paris\.fr/[^"]+)"', re.I)
_NODE_ID_RE = re.compile(r"/node/(\d+)")


class ParisMuseesGraphQLBlocked(RuntimeError):
    """GraphQL zablokowany (403 HTML) — typowe poza przegladarka / przez WAF."""


def _graphql_blocked(raw: str) -> bool:
    low = (raw or "").lower()
    return "http 403" in low and ("<!doctype" in low or "accès refusé" in low or "acces refuse" in low)


def _get_html(url: str, *, timeout: float = 25.0) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _graphql(query: str) -> dict:
    token = paris_musees_api_token()
    if not token:
        raise RuntimeError("Brak PARIS_MUSEES_API_TOKEN w cursor-api/.env")
    headers = {"auth-token": token}
    try:
        data = post_json(PARIS_GRAPHQL, {"query": query}, headers=headers, timeout=25)
    except RuntimeError as exc:
        if _graphql_blocked(str(exc)):
            raise ParisMuseesGraphQLBlocked(str(exc)) from exc
        raise
    if not isinstance(data, dict):
        raise RuntimeError("Niepoprawna odpowiedz Paris Musées")
    errors = data.get("errors")
    if errors:
        msg = errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])
        raise RuntimeError(msg or "Blad GraphQL Paris Musées")
    return data.get("data") or {}


def _parse_search_html(html_text: str, *, limit: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _ARTICLE_RE.finditer(html_text):
        path = match.group("path").strip()
        node_m = _NODE_ID_RE.search(path)
        if not node_m:
            continue
        raw_id = node_m.group(1)
        if raw_id in seen:
            continue
        seen.add(raw_id)
        block = match.group("body")
        title_m = _TITLE_RE.search(block)
        title = html.unescape(title_m.group(1).strip()) if title_m else ""
        if not title:
            continue
        img_m = _IMG_RE.search(block)
        rows.append(
            {
                "title": title,
                "artist": "",
                "date": "",
                "medium": "",
                "object_type": "",
                "object_url": f"https://www.parismuseescollections.paris.fr{path}",
                "image_url": img_m.group(1).strip() if img_m else "",
                "raw_id": raw_id,
            },
        )
        if len(rows) >= limit:
            break
    return rows


def _search_web(*, query: str, limit: int) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    enc = urllib.parse.quote(q)
    url = f"{PUBLIC_SEARCH}?search_api_fulltext={enc}"
    try:
        page = _get_html(url, timeout=30.0)
    except (OSError, urllib.error.URLError, RuntimeError):
        return []
    return _parse_search_html(page, limit=min(limit * 4, 40))


def _search_graphql(*, query: str, limit: int) -> list[dict[str, str]]:
    q = (query or "").strip().replace('"', '\\"')
    if not q:
        return []

    gql = f"""
{{
  nodeQuery(limit: {min(limit * 4, 40)}, filter: {{
    conjunction: OR,
    groups: [
      {{ conjunction: AND, conditions: [
        {{ field: "fieldOeuvreAuteurTexte", value: "{q}", operator: CONTAINS }}
      ] }},
      {{ conjunction: AND, conditions: [
        {{ field: "title", value: "{q}", operator: CONTAINS }}
      ] }}
    ]
  }}) {{
    entities {{
      entityBundle
      ... on NodeOeuvre {{
        entityId
        title
        fieldUrlAlias
        fieldOeuvreAuteurTexte
        fieldOeuvreDateCreation
        fieldOeuvreTechnique
        fieldOeuvreType
        fieldVisuelPrincipal {{
          entity {{
            image {{
              url
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""
    data = _graphql(gql)
    block = data.get("nodeQuery") or {}
    entities = block.get("entities") or []
    rows: list[dict[str, str]] = []
    for ent in entities:
        if not isinstance(ent, dict) or ent.get("entityBundle") != "oeuvre":
            continue
        title = str(ent.get("title") or "").strip()
        if not title:
            continue
        alias = str(ent.get("fieldUrlAlias") or "").strip().lstrip("/")
        object_url = f"{PUBLIC_BASE}/{alias}" if alias else ""
        image_url = ""
        visuel = ent.get("fieldVisuelPrincipal") or {}
        if isinstance(visuel, dict):
            entity = visuel.get("entity") or {}
            if isinstance(entity, dict):
                image = entity.get("image") or {}
                if isinstance(image, dict):
                    image_url = str(image.get("url") or "").strip()
        rows.append(
            {
                "title": title,
                "artist": str(ent.get("fieldOeuvreAuteurTexte") or "").strip(),
                "date": str(ent.get("fieldOeuvreDateCreation") or "").strip(),
                "medium": str(ent.get("fieldOeuvreTechnique") or "").strip(),
                "object_type": str(ent.get("fieldOeuvreType") or "").strip(),
                "object_url": object_url,
                "image_url": image_url,
                "raw_id": str(ent.get("entityId") or "").strip(),
            },
        )
    return rows


def search_paris_musees(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    """Zwraca surowe wiersze (title, artist, object_url, image_url, raw_id)."""
    q = (query or "").strip()
    if not q:
        return []

    if paris_musees_api_token():
        try:
            return _search_graphql(query=q, limit=limit)
        except ParisMuseesGraphQLBlocked:
            pass

    return _search_web(query=q, limit=limit)


def paris_musees_health_probe() -> tuple[bool, str]:
    """Szybki test polaczenia — GraphQL lub fallback HTML."""
    token = paris_musees_api_token()
    if token:
        try:
            _graphql("{ __typename }")
            return True, "GraphQL OK"
        except ParisMuseesGraphQLBlocked:
            pass
        except RuntimeError as exc:
            return False, str(exc)[:120]
    try:
        page = _get_html(f"{PUBLIC_SEARCH}?search_api_fulltext=art", timeout=30.0)
    except (OSError, urllib.error.URLError, RuntimeError) as exc:
        return False, str(exc)[:120]
    if _ARTICLE_RE.search(page) or "search-result" in page:
        if token:
            return True, "HTML search OK (GraphQL zablokowany przez WAF)"
        return True, "HTML search OK (bez tokenu — GraphQL niedostepny)"
    return False, "Brak wynikow w HTML search"
