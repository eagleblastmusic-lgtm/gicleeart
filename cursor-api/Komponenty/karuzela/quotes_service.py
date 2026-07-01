"""Shopify: cytaty per kolekcja (metafield custom.collection_quotes + legacy collection_quote)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.tldobio.service import (
    _node_to_collection_base,
    _paginate_collections_graphql,
    delete_collection_metafield,
    find_collection_metafield,
    upsert_collection_metafield,
)

METAFIELD_NAMESPACE = "custom"
METAFIELD_KEY = "collection_quote"
METAFIELD_TYPE = "multi_line_text_field"
METAFIELD_KEY_QUOTES = "collection_quotes"
METAFIELD_TYPE_QUOTES = "json"

_COMPONENT_DIR = Path(__file__).resolve().parent
_DATA_DIR = _COMPONENT_DIR / "data"
_DATA_FILE = _DATA_DIR / "collection_quotes.json"

Logger = Callable[[str], None]
_DEFINITION_ENSURED = False
_DEFINITION_QUOTES_ENSURED = False


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_quotes(raw: Any) -> list[str]:
    """Zwraca listę niepustych cytatów (stringi)."""
    if raw is None:
        return []
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            text = str(item or "").strip()
            if text:
                out.append(text)
        return out
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return [text]
            return normalize_quotes(parsed)
        return [text]
    return []


def quotes_preview(quotes: list[str], *, max_len: int = 72) -> str:
    if not quotes:
        return ""
    preview = quotes[0].replace("\n", " ").strip()
    if len(quotes) > 1:
        preview = f"{preview} (+{len(quotes) - 1})"
    if len(preview) > max_len:
        preview = preview[: max_len - 1] + "…"
    return preview


def quotes_status_label(quotes: list[str]) -> str:
    n = len(quotes)
    if n == 0:
        return "—"
    if n == 1:
        return "1"
    return str(n)


def load_local_cache() -> dict[str, Any]:
    if not _DATA_FILE.is_file():
        return {"version": 2, "quotes": {}, "catalog": []}
    try:
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"version": 2, "quotes": {}, "catalog": []}
        data.setdefault("version", 2)
        data.setdefault("quotes", {})
        data.setdefault("catalog", [])
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": 2, "quotes": {}, "catalog": []}


def save_local_cache(data: dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["version"] = 2
    _DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _parse_metafield_quotes(mf: dict[str, Any] | None) -> list[str]:
    if not mf:
        return []
    raw = mf.get("value")
    if raw is None or raw == "":
        return []
    if isinstance(raw, (list, dict)):
        return normalize_quotes(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            return normalize_quotes(json.loads(text))
        except json.JSONDecodeError:
            return normalize_quotes(text)
    return []


def ensure_collection_quote_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_ENSURED  # noqa: PLW0603
    if _DEFINITION_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "collection_quote") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _DEFINITION_ENSURED = True
        return
    create = """
    mutation metafieldDefinitionCreate($definition: MetafieldDefinitionInput!) {
      metafieldDefinitionCreate(definition: $definition) {
        createdDefinition { id }
        userErrors { field message code }
      }
    }
    """
    payload = {
        "definition": {
            "name": "Cytat kolekcji",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY,
            "type": METAFIELD_TYPE,
            "ownerType": "COLLECTION",
            "access": {"storefront": "PUBLIC_READ"},
        }
    }
    res = sc.graphql(shop, token, create, payload)
    block = (res or {}).get("metafieldDefinitionCreate") or {}
    errors = block.get("userErrors") or []
    if errors:
        codes = {str(e.get("code") or "") for e in errors}
        if not codes.intersection({"TAKEN", "ALREADY_EXISTS"}):
            raise sc.ShopifyError(f"metafieldDefinitionCreate: {errors}")
    _DEFINITION_ENSURED = True
    _log(logger, "[Karuzela — Cytaty] Metafield custom.collection_quote (COLLECTION, storefront).")


def ensure_collection_quotes_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_QUOTES_ENSURED  # noqa: PLW0603
    if _DEFINITION_QUOTES_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "collection_quotes") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _DEFINITION_QUOTES_ENSURED = True
        return
    create = """
    mutation metafieldDefinitionCreate($definition: MetafieldDefinitionInput!) {
      metafieldDefinitionCreate(definition: $definition) {
        createdDefinition { id }
        userErrors { field message code }
      }
    }
    """
    payload = {
        "definition": {
            "name": "Cytaty kolekcji (lista)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_QUOTES,
            "type": METAFIELD_TYPE_QUOTES,
            "ownerType": "COLLECTION",
            "access": {"storefront": "PUBLIC_READ"},
        }
    }
    res = sc.graphql(shop, token, create, payload)
    block = (res or {}).get("metafieldDefinitionCreate") or {}
    errors = block.get("userErrors") or []
    if errors:
        codes = {str(e.get("code") or "") for e in errors}
        if not codes.intersection({"TAKEN", "ALREADY_EXISTS"}):
            raise sc.ShopifyError(f"metafieldDefinitionCreate: {errors}")
    _DEFINITION_QUOTES_ENSURED = True
    _log(logger, "[Karuzela — Cytaty] Metafield custom.collection_quotes (JSON, storefront).")


_COLLECTIONS_QUOTES_GQL = """
query CollectionsQuotes($first: Int!, $after: String) {
  collections(first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      legacyResourceId
      title
      handle
      quotesJson: metafield(namespace: "custom", key: "collection_quotes") { value }
      quoteLegacy: metafield(namespace: "custom", key: "collection_quote") { value }
    }
  }
}
"""


def _quotes_from_graphql_node(node: dict[str, Any]) -> list[str]:
    mf_list = node.get("quotesJson") or {}
    raw_list = mf_list.get("value") if isinstance(mf_list, dict) else None
    quotes = _parse_metafield_quotes({"value": raw_list} if raw_list is not None else None)
    if quotes:
        return quotes
    mf_single = node.get("quoteLegacy") or {}
    raw_single = mf_single.get("value") if isinstance(mf_single, dict) else None
    return normalize_quotes(raw_single)


def _fetch_collection_rows_with_quotes_graphql(
    shop: str,
    token: str,
    *,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in _paginate_collections_graphql(
        shop,
        token,
        _COLLECTIONS_QUOTES_GQL,
        on_progress=on_progress,
        progress_label="Kolekcje + cytaty",
    ):
        col = _node_to_collection_base(node)
        if not col:
            continue
        items = _quotes_from_graphql_node(node)
        preview = quotes_preview(items)
        rows.append(
            {
                **col,
                "quotes": items,
                "quote": items[0] if items else "",
                "quote_preview": preview,
                "has_quote": bool(items),
                "quote_count": len(items),
                "status": quotes_status_label(items),
            }
        )
    rows.sort(key=lambda r: (r.get("title") or "").lower())
    return rows


def load_cached_collection_rows() -> list[dict[str, Any]] | None:
    cache = load_local_cache()
    catalog = cache.get("catalog")
    if not isinstance(catalog, list) or not catalog:
        return None
    return [dict(row) for row in catalog if isinstance(row, dict)]


def fetch_quotes_for_collection(
    shop: str,
    token: str,
    collection_id: int,
) -> list[str]:
    mf_list = find_collection_metafield(
        shop, token, collection_id, namespace=METAFIELD_NAMESPACE, key=METAFIELD_KEY_QUOTES
    )
    quotes = _parse_metafield_quotes(mf_list)
    if quotes:
        return quotes
    mf_single = find_collection_metafield(
        shop, token, collection_id, namespace=METAFIELD_NAMESPACE, key=METAFIELD_KEY
    )
    return normalize_quotes((mf_single or {}).get("value"))


def fetch_quote_map(
    collections: list[dict[str, Any]],
    *,
    logger: Logger | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, list[str]]:
    """Mapa handle → cytaty. Preferuj load_collections_with_quotes (GraphQL, 1 przebieg)."""
    out: dict[str, list[str]] = {}
    for col in collections:
        handle = str(col.get("handle") or "").strip()
        items = col.get("quotes")
        if handle and isinstance(items, list) and items:
            out[handle] = normalize_quotes(items)
    if out:
        _log(logger, f"[Karuzela — Cytaty] Cytaty (z przekazanej listy): {len(out)}.")
        return out
    shop, token = sc.load_session()
    rows = _fetch_collection_rows_with_quotes_graphql(
        shop, token, on_progress=on_progress
    )
    for row in rows:
        handle = str(row.get("handle") or "").strip()
        items = normalize_quotes(row.get("quotes"))
        if handle and items:
            out[handle] = items
    _log(logger, f"[Karuzela — Cytaty] Kolekcje z cytatami w Shopify: {len(out)}.")
    return out


def sync_local_from_shopify(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cache = load_local_cache()
    cache["version"] = 2
    cache["fetched_at"] = _now_iso()
    quotes = cache.setdefault("quotes", {})
    seen: set[str] = set()
    catalog: list[dict[str, Any]] = []
    for col in rows:
        handle = str(col.get("handle") or "").strip()
        if not handle:
            continue
        seen.add(handle)
        items = normalize_quotes(col.get("quotes"))
        catalog.append(
            {
                "id": col.get("id"),
                "handle": handle,
                "title": col.get("title") or "",
                "kind": col.get("kind") or "collection",
                "quotes": items,
                "quote": items[0] if items else "",
                "quote_preview": quotes_preview(items),
                "has_quote": bool(items),
                "quote_count": len(items),
                "status": quotes_status_label(items),
            }
        )
        if items:
            quotes[handle] = {
                "collection_id": col.get("id"),
                "handle": handle,
                "title": col.get("title") or "",
                "quotes": items,
                "quote": items[0],
                "updated_at": quotes.get(handle, {}).get("updated_at") or _now_iso(),
            }
        elif handle in quotes:
            del quotes[handle]
    for stale in [h for h in list(quotes.keys()) if h not in seen]:
        del quotes[stale]
    cache["catalog"] = catalog
    save_local_cache(cache)
    return cache


def _patch_cached_row(
    handle: str,
    *,
    cache: dict[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    data = cache if cache is not None else load_local_cache()
    catalog = data.get("catalog")
    if isinstance(catalog, list):
        for entry in catalog:
            if entry.get("handle") == handle:
                entry.update(fields)
                break
    if cache is None:
        save_local_cache(data)
    return data


def load_collections_with_quotes(
    *,
    logger: Logger | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    shop, token = sc.load_session()
    rows = _fetch_collection_rows_with_quotes_graphql(
        shop, token, on_progress=on_progress
    )
    sync_local_from_shopify(rows)
    _log(logger, f"[Karuzela — Cytaty] Załadowano {len(rows)} kolekcji (GraphQL).")
    return rows


def save_collection_quote(
    collection_id: int,
    handle: str,
    title: str,
    quote: str,
    *,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Zapis pojedynczego cytatu (kompatybilność wsteczna)."""
    text = str(quote or "").strip()
    quotes = [text] if text else []
    return save_collection_quotes(collection_id, handle, title, quotes, logger=logger)


def save_collection_quotes(
    collection_id: int,
    handle: str,
    title: str,
    quotes: list[str],
    *,
    logger: Logger | None = None,
) -> dict[str, Any]:
    ensure_collection_quote_metafield_definition(logger=logger)
    ensure_collection_quotes_metafield_definition(logger=logger)
    shop, token = sc.load_session()
    cid = int(collection_id)
    h = str(handle or "").strip()
    items = normalize_quotes(quotes)
    if not cid or not h:
        return {"ok": False, "error": "Brak identyfikatora kolekcji."}
    try:
        if items:
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY_QUOTES,
                value=json.dumps(items, ensure_ascii=False),
                ftype=METAFIELD_TYPE_QUOTES,
            )
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY,
                value=items[0],
                ftype=METAFIELD_TYPE,
            )
        else:
            delete_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY_QUOTES,
            )
            delete_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY,
            )
    except sc.ShopifyError as exc:
        return {"ok": False, "error": str(exc)}
    cache = load_local_cache()
    cache_quotes = cache.setdefault("quotes", {})
    preview = quotes_preview(items)
    if items:
        cache_quotes[h] = {
            "collection_id": cid,
            "handle": h,
            "title": title,
            "quotes": items,
            "quote": items[0],
            "updated_at": _now_iso(),
        }
    elif h in cache_quotes:
        del cache_quotes[h]
    _patch_cached_row(
        h,
        cache=cache,
        quotes=items,
        quote=items[0] if items else "",
        quote_preview=preview,
        has_quote=bool(items),
        quote_count=len(items),
        status=quotes_status_label(items),
    )
    save_local_cache(cache)
    _log(logger, f"[Karuzela — Cytaty] Zapisano {len(items)} cytat(ów) dla {h}.")
    return {"ok": True, "quotes": items, "quote": items[0] if items else "", "handle": h}
