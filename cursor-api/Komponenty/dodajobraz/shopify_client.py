"""Klient Shopify Admin API (REST + GraphQL) dla dodajobraz.

Korzysta z sesji zapisanej przez oauth-server w .shopify_session.json.
"""
from __future__ import annotations

import base64
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_VERSION = "2026-04"
# Sciezka do cursor-api/ liczona jako 3 poziomy w gore:
#   __file__ = cursor-api/Komponenty/dodajobraz/shopify_client.py
#   parents[2] = cursor-api/
ROOT = Path(__file__).resolve().parents[2]
SESSION_FILE = ROOT / ".shopify_session.json"


class ShopifyError(RuntimeError):
    pass


def load_session() -> tuple[str, str]:
    if not SESSION_FILE.is_file():
        raise ShopifyError(
            f"Brak {SESSION_FILE}. Uruchom `npm run oauth` w folderze cursor-api."
        )
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    shop = (data.get("shop") or "").strip()
    token = (data.get("accessToken") or "").strip()
    if not shop or not token:
        raise ShopifyError("Niepelna sesja w .shopify_session.json (shop/accessToken).")
    return shop, token


def _request(
    method: str,
    url: str,
    token: str,
    *,
    body: dict | None = None,
) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Shopify-Access-Token": token,
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise ShopifyError(f"HTTP {e.code} {method} {url}\n{detail}") from e
    if not raw:
        return None
    return json.loads(raw)


def rest_get(shop: str, token: str, path: str, **params: Any) -> Any:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"https://{shop}/admin/api/{API_VERSION}/{path.lstrip('/')}"
    if qs:
        url = f"{url}?{qs}"
    return _request("GET", url, token)


def rest_post(shop: str, token: str, path: str, body: dict) -> Any:
    url = f"https://{shop}/admin/api/{API_VERSION}/{path.lstrip('/')}"
    return _request("POST", url, token, body=body)


def rest_put(shop: str, token: str, path: str, body: dict) -> Any:
    url = f"https://{shop}/admin/api/{API_VERSION}/{path.lstrip('/')}"
    return _request("PUT", url, token, body=body)


def graphql(shop: str, token: str, query: str, variables: dict | None = None) -> dict:
    url = f"https://{shop}/admin/api/{API_VERSION}/graphql.json"
    body = {"query": query, "variables": variables or {}}
    data = _request("POST", url, token, body=body)
    if not isinstance(data, dict):
        raise ShopifyError(f"Nieoczekiwana odpowiedz GraphQL: {data!r}")
    if data.get("errors"):
        raise ShopifyError(f"GraphQL errors: {json.dumps(data['errors'], ensure_ascii=False)}")
    return data.get("data") or {}


def get_reference_variants(shop: str, token: str, product_id: int) -> dict:
    """Zwraca dict z kluczami: options, variants (lista slownikow gotowych do kopiowania)."""
    out = rest_get(shop, token, f"products/{product_id}.json")
    prod = (out or {}).get("product") or {}
    if not prod:
        raise ShopifyError(f"Nie znaleziono produktu referencyjnego id={product_id}")

    options_copy: list[dict] = []
    for opt in prod.get("options") or []:
        options_copy.append(
            {
                "name": opt.get("name"),
                "values": list(opt.get("values") or []),
                "position": opt.get("position"),
            }
        )

    variants_copy: list[dict] = []
    copy_keys = (
        "option1",
        "option2",
        "option3",
        "price",
        "compare_at_price",
        "taxable",
        "inventory_policy",
        "fulfillment_service",
        "inventory_management",
        "requires_shipping",
        "weight",
        "weight_unit",
        "position",
    )
    for v in prod.get("variants") or []:
        new_v = {k: v.get(k) for k in copy_keys if v.get(k) is not None}
        variants_copy.append(new_v)

    return {
        "options": [o for o in options_copy if o.get("name")],
        "variants": variants_copy,
        "source_product": {
            "id": prod.get("id"),
            "title": prod.get("title"),
            "handle": prod.get("handle"),
        },
    }


_H4_RE = re.compile(r"<h4[^>]*>\s*(.*?)\s*</h4>", re.IGNORECASE | re.DOTALL)


def find_artist_collection(shop: str, token: str, collection_title: str) -> dict | None:
    """Szuka kolekcji po tytule 'Nazwisko, Imie' w custom i smart collections.

    Zwraca dict: { id, title, body_html, lifespan, kind } gdzie kind in {'custom','smart'}.
    """
    for path, kind in (("custom_collections.json", "custom"), ("smart_collections.json", "smart")):
        data = rest_get(shop, token, path, title=collection_title, limit=5)
        items = (data or {}).get(path.split(".", 1)[0]) or []
        for item in items:
            if (item.get("title") or "").strip().lower() == collection_title.strip().lower():
                body = item.get("body_html") or ""
                match = _H4_RE.search(body)
                lifespan = match.group(1).strip() if match else ""
                lifespan = re.sub(r"<[^>]+>", "", lifespan).strip()
                return {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "body_html": body,
                    "lifespan": lifespan,
                    "kind": kind,
                }
    return None


def create_product(shop: str, token: str, product: dict) -> dict:
    out = rest_post(shop, token, "products.json", {"product": product})
    return (out or {}).get("product") or {}


def upload_image(
    shop: str,
    token: str,
    product_id: int,
    image_path: Path,
    *,
    alt: str | None = None,
) -> dict:
    raw = image_path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    image_obj: dict = {
        "attachment": b64,
        "filename": image_path.name,
    }
    if alt:
        image_obj["alt"] = alt
    out = rest_post(shop, token, f"products/{product_id}/images.json", {"image": image_obj})
    return (out or {}).get("image") or {}


def add_to_collect(shop: str, token: str, product_id: int, collection_id: int) -> dict:
    out = rest_post(
        shop,
        token,
        "collects.json",
        {"collect": {"product_id": product_id, "collection_id": collection_id}},
    )
    return (out or {}).get("collect") or {}


def set_seo_metafields(
    shop: str,
    token: str,
    product_id: int,
    *,
    title_tag: str,
    description_tag: str,
) -> None:
    for key, value, ftype in (
        ("title_tag", title_tag, "single_line_text_field"),
        ("description_tag", description_tag, "multi_line_text_field"),
    ):
        rest_post(
            shop,
            token,
            f"products/{product_id}/metafields.json",
            {
                "metafield": {
                    "namespace": "global",
                    "key": key,
                    "type": ftype,
                    "value": value,
                }
            },
        )


def set_custom_metafield(
    shop: str,
    token: str,
    product_id: int,
    *,
    namespace: str,
    key: str,
    value: str,
    ftype: str = "single_line_text_field",
) -> None:
    rest_post(
        shop,
        token,
        f"products/{product_id}/metafields.json",
        {
            "metafield": {
                "namespace": namespace,
                "key": key,
                "type": ftype,
                "value": value,
            }
        },
    )


def list_publications(shop: str, token: str) -> list[dict]:
    query = """
    query {
      publications(first: 50) {
        nodes { id name }
      }
    }
    """
    data = graphql(shop, token, query)
    return (data.get("publications") or {}).get("nodes") or []


def publish_product_everywhere(shop: str, token: str, product_gid: str) -> list[str]:
    """Publikuje produkt na wszystkich dostepnych kanalach (publications)."""
    pubs = list_publications(shop, token)
    if not pubs:
        return []
    mutation = """
    mutation publish($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) {
        publishable { ... on Product { id } }
        userErrors { field message }
      }
    }
    """
    variables = {
        "id": product_gid,
        "input": [{"publicationId": p["id"]} for p in pubs],
    }
    data = graphql(shop, token, mutation, variables)
    errors = (data.get("publishablePublish") or {}).get("userErrors") or []
    if errors:
        raise ShopifyError(f"publishablePublish userErrors: {errors}")
    return [p.get("name", "") for p in pubs]


def product_gid(product_id: int) -> str:
    return f"gid://shopify/Product/{product_id}"


def get_product_options_with_gids(
    shop: str, token: str, product_gid_str: str
) -> list[dict]:
    """Zwraca opcje produktu z GID-ami opcji i wartosci (do tlumaczen).

    Format:
      [
        {'id': 'gid://shopify/ProductOption/123', 'name': 'Kolor',
         'values': [{'id': 'gid://shopify/ProductOptionValue/1', 'name': 'Czarny'}, ...]},
        ...
      ]

    Zasoby `ProductOption` i `ProductOptionValue` sa odrebnymi translatable resources
    w Shopify Translations API - dlatego potrzebujemy ich GID-ow, zeby wyslac
    `translationsRegister(resourceId=<option_gid>, fields={'name': ...})` per locale.
    """
    query = """
    query($id: ID!) {
      product(id: $id) {
        options(first: 10) {
          id
          name
          optionValues { id name }
        }
      }
    }
    """
    data = graphql(shop, token, query, {"id": product_gid_str})
    prod = (data or {}).get("product") or {}
    options_field = prod.get("options")
    # GraphQL czasem zwraca obiekt {'nodes':[...]}, czasem juz liste - obsluzmy oba.
    if isinstance(options_field, dict):
        nodes = options_field.get("nodes") or []
    elif isinstance(options_field, list):
        nodes = options_field
    else:
        nodes = []
    out: list[dict] = []
    for opt in nodes:
        if not isinstance(opt, dict):
            continue
        values_field = opt.get("optionValues") or []
        if isinstance(values_field, dict):
            values_nodes = values_field.get("nodes") or []
        else:
            values_nodes = values_field
        out.append({
            "id": opt.get("id") or "",
            "name": opt.get("name") or "",
            "values": [
                {"id": (v or {}).get("id") or "", "name": (v or {}).get("name") or ""}
                for v in values_nodes
                if isinstance(v, dict)
            ],
        })
    return out


def find_product_by_title(shop: str, token: str, title: str) -> dict | None:
    """Szuka produktu po dokladnym tytule (case-insensitive) poprzez query REST.

    Dodatkowo sprawdza po handle (slug), zeby zwiekszyc szanse trafienia.
    Zwraca slownik produktu lub None.
    """
    from .parser import slugify

    target = title.strip()
    target_slug = slugify(target)

    data = rest_get(shop, token, "products.json", title=target, limit=50)
    items = (data or {}).get("products") or []
    for it in items:
        if (it.get("title") or "").strip().lower() == target.lower():
            return it
        if slugify(it.get("handle") or "") == target_slug:
            return it

    data = rest_get(shop, token, "products.json", handle=target_slug, limit=5)
    items = (data or {}).get("products") or []
    for it in items:
        if (it.get("handle") or "").strip().lower() == target_slug:
            return it

    return None


def get_product(shop: str, token: str, product_id: int) -> dict:
    out = rest_get(shop, token, f"products/{product_id}.json")
    return (out or {}).get("product") or {}


def count_product_images(shop: str, token: str, product_id: int) -> int:
    out = rest_get(shop, token, f"products/{product_id}/images/count.json")
    return int((out or {}).get("count") or 0)


def iter_all_products(
    shop: str,
    token: str,
    *,
    product_type: str | None = None,
    fields: str | None = None,
) -> list[dict]:
    """Pobiera wszystkie produkty. Obsluguje paginacje Link-header.

    Domyslnie pobiera 'id,title,handle,variants,options' (potrzebne do hurtowej
    edycji cen). Mozna podac wlasna liste pol przez argument 'fields' - np.
    'id,title,handle,vendor,image,product_type' jesli wystarczy lekkie
    zestawienie bez wariantow.

    Zwraca liste slownikow produktu z Shopify REST.
    """
    params: dict[str, Any] = {
        "limit": 250,
        "fields": fields or "id,title,handle,variants,options",
    }
    if product_type:
        params["product_type"] = product_type
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products.json?"
        + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    )
    all_products: list[dict] = []
    while url:
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Shopify-Access-Token": token,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context()) as resp:
                raw = resp.read().decode("utf-8")
                link_header = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise ShopifyError(f"HTTP {e.code} GET {url}\n{detail}") from e
        data = json.loads(raw) if raw else {}
        all_products.extend((data or {}).get("products") or [])

        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
                    break
        url = next_url
    return all_products


def iter_orders_since(
    shop: str,
    token: str,
    *,
    created_at_min: str | None = None,
    updated_at_min: str | None = None,
    status: str = "any",
    financial_status: str | None = "paid",
    limit: int = 250,
    fields: str | None = None,
) -> list[dict]:
    """Pobiera zamowienia z `/admin/api/{API}/orders.json` z paginacja Link-header.

    Scope: `read_orders`.

    `created_at_min` / `updated_at_min`: ISO8601 (np. '2026-04-20T12:00:00Z').
    Domyslnie pobiera tylko zaplacone (`financial_status=paid`). `status=any`
    obejmuje zarowno `open` jak i `closed` (np. te wyslane).

    Uwaga: poniewaz limit per strona to 250, a kazde zamowienie ma duzo pol,
    dla sklepu z wieloma tysiacami zamowien zawsze podawaj `*_at_min` inaczej
    pobranie calej historii moze byc wolne.
    """
    default_fields = (
        "id,name,created_at,updated_at,financial_status,fulfillment_status,"
        "email,total_price,currency,customer,shipping_address,line_items,"
        "note,tags"
    )
    params: dict[str, Any] = {
        "limit": max(1, min(int(limit), 250)),
        "status": status,
        "fields": fields or default_fields,
    }
    if financial_status:
        params["financial_status"] = financial_status
    if created_at_min:
        params["created_at_min"] = created_at_min
    if updated_at_min:
        params["updated_at_min"] = updated_at_min

    url = (
        f"https://{shop}/admin/api/{API_VERSION}/orders.json?"
        + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    )
    all_orders: list[dict] = []
    while url:
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Shopify-Access-Token": token,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context()) as resp:
                raw = resp.read().decode("utf-8")
                link_header = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise ShopifyError(f"HTTP {e.code} GET {url}\n{detail}") from e
        data = json.loads(raw) if raw else {}
        all_orders.extend((data or {}).get("orders") or [])

        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
                    break
        url = next_url
    return all_orders


def _find_products_by_tag_gql(shop: str, token: str, tag: str, *, limit: int = 5) -> list[dict]:
    """Szuka produktow po tagu przez GraphQL Admin (search query 'tag:"..."').

    GraphQL search obsluguje poprawnie tagi zawierajace znaki specjalne (':' '__'),
    w przeciwienstwie do REST `?tag=`, ktory bywa kapryśny.
    """
    target = tag.strip()
    if not target:
        return []
    safe = target.replace("\\", "\\\\").replace('"', '\\"')
    q = f'tag:"{safe}"'
    query = """
    query($q: String!, $first: Int!) {
      products(first: $first, query: $q) {
        edges {
          node {
            legacyResourceId
            title
            handle
            tags
            vendor
          }
        }
      }
    }
    """
    try:
        data = graphql(shop, token, query, {"q": q, "first": int(limit)})
    except ShopifyError:
        return []
    edges = ((data or {}).get("products") or {}).get("edges") or []
    target_norm = target.lower()
    out: list[dict] = []
    for edge in edges:
        node = (edge or {}).get("node") or {}
        tags_list = [str(t).strip() for t in (node.get("tags") or [])]
        if target_norm not in {t.lower() for t in tags_list}:
            continue
        legacy_id = node.get("legacyResourceId")
        try:
            pid = int(legacy_id)
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "id": pid,
                "title": node.get("title"),
                "handle": node.get("handle"),
                "tags": ", ".join(tags_list),
                "vendor": node.get("vendor"),
            }
        )
    return out


def _find_products_by_tag_rest(shop: str, token: str, tag: str, *, limit: int = 5) -> list[dict]:
    """Fallback: REST `?tag=` z twardym post-filtrem (Shopify czasem ignoruje filtr)."""
    target = tag.strip()
    if not target:
        return []
    data = rest_get(
        shop,
        token,
        "products.json",
        fields="id,title,handle,tags,vendor,image",
        tag=target,
        limit=limit,
    )
    items = (data or {}).get("products") or []
    target_norm = target.lower()
    verified: list[dict] = []
    for it in items:
        raw = it.get("tags")
        if isinstance(raw, list):
            tags = [str(t).strip().lower() for t in raw if str(t).strip()]
        else:
            tags = [t.strip().lower() for t in (raw or "").split(",") if t.strip()]
        if target_norm in tags:
            verified.append(it)
    return verified


def find_products_by_tag(shop: str, token: str, tag: str, *, limit: int = 5) -> list[dict]:
    """Znajduje produkty majace dokladnie dany tag.

    Probuje najpierw GraphQL (obsluguje poprawnie dwukropki i podkreslniki),
    potem REST jako fallback.
    """
    target = tag.strip()
    if not target:
        return []
    hits = _find_products_by_tag_gql(shop, token, target, limit=limit)
    if hits:
        return hits
    return _find_products_by_tag_rest(shop, token, target, limit=limit)


def iter_collection_products(
    shop: str, token: str, collection_id: int, *, fields: str | None = None
) -> list[dict]:
    """Pobiera wszystkie produkty w danej kolekcji (custom lub smart). Obsluguje paginacje."""
    params = {
        "limit": 250,
        "fields": fields or "id,title,handle,vendor,image",
    }
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/collections/{collection_id}/products.json?"
        + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    )
    all_products: list[dict] = []
    while url:
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Shopify-Access-Token": token,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context()) as resp:
                raw = resp.read().decode("utf-8")
                link_header = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise ShopifyError(f"HTTP {e.code} GET {url}\n{detail}") from e
        data = json.loads(raw) if raw else {}
        all_products.extend((data or {}).get("products") or [])

        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
                    break
        url = next_url
    return all_products


def update_variant_price(shop: str, token: str, variant_id: int, price: str) -> dict:
    """Aktualizuje cene pojedynczego wariantu (REST PUT /variants/{id}.json)."""
    out = rest_put(
        shop,
        token,
        f"variants/{variant_id}.json",
        {"variant": {"id": variant_id, "price": str(price)}},
    )
    return (out or {}).get("variant") or {}


def list_product_images(shop: str, token: str, product_id: int) -> list[dict]:
    out = rest_get(shop, token, f"products/{product_id}/images.json")
    return (out or {}).get("images") or []


def delete_product_image(shop: str, token: str, product_id: int, image_id: int) -> None:
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products/{product_id}/images/{image_id}.json"
    )
    _request("DELETE", url, token)


def set_image_position(shop: str, token: str, product_id: int, image_id: int, position: int) -> dict:
    out = rest_put(
        shop,
        token,
        f"products/{product_id}/images/{image_id}.json",
        {"image": {"id": image_id, "position": position}},
    )
    return (out or {}).get("image") or {}


def update_product(shop: str, token: str, product_id: int, fields: dict) -> dict:
    """PUT /products/{id}.json - aktualizuje wskazane pola (body_html, tags, handle, title, ...).

    Nie rusza wariantow, opcji ani kolekcji, chyba ze jawnie je przekazesz.
    """
    payload = {"product": {"id": product_id, **(fields or {})}}
    out = rest_put(shop, token, f"products/{product_id}.json", payload)
    return (out or {}).get("product") or {}


def find_metafield(
    shop: str, token: str, product_id: int, *, namespace: str, key: str
) -> dict | None:
    out = rest_get(
        shop, token, f"products/{product_id}/metafields.json", namespace=namespace, key=key
    )
    items = (out or {}).get("metafields") or []
    return items[0] if items else None


def upsert_metafield(
    shop: str,
    token: str,
    product_id: int,
    *,
    namespace: str,
    key: str,
    value: str,
    ftype: str = "single_line_text_field",
) -> dict:
    """Tworzy lub aktualizuje metapole produktu (znajduje po namespace/key -> PUT, inaczej POST)."""
    existing = find_metafield(shop, token, product_id, namespace=namespace, key=key)
    if existing:
        mid = int(existing["id"])
        out = rest_put(
            shop,
            token,
            f"metafields/{mid}.json",
            {"metafield": {"id": mid, "value": value, "type": ftype}},
        )
        return (out or {}).get("metafield") or {}
    out = rest_post(
        shop,
        token,
        f"products/{product_id}/metafields.json",
        {"metafield": {"namespace": namespace, "key": key, "type": ftype, "value": value}},
    )
    return (out or {}).get("metafield") or {}


# ---------------------------------------------------------------------------
# Smart Collections (kolekcje automatyczne na bazie regul po tagu)
# ---------------------------------------------------------------------------

def find_smart_collection_by_handle(
    shop: str, token: str, handle: str
) -> dict | None:
    """Szuka smart-collection po handle (Shopify zwraca je w polu 'smart_collections')."""
    h = (handle or "").strip().lower()
    if not h:
        return None
    data = rest_get(shop, token, "smart_collections.json", handle=h, limit=5)
    items = (data or {}).get("smart_collections") or []
    for it in items:
        if (it.get("handle") or "").strip().lower() == h:
            return it
    return None


def find_smart_collection_by_title(
    shop: str, token: str, title: str
) -> dict | None:
    """Szuka smart-collection po tytule (case-insensitive)."""
    t = (title or "").strip().lower()
    if not t:
        return None
    data = rest_get(shop, token, "smart_collections.json", title=title, limit=5)
    items = (data or {}).get("smart_collections") or []
    for it in items:
        if (it.get("title") or "").strip().lower() == t:
            return it
    return None


def create_smart_collection_for_tag(
    shop: str,
    token: str,
    *,
    title: str,
    handle: str,
    tag: str,
    body_html: str | None = None,
    sort_order: str = "best-selling",
    published: bool = True,
) -> dict:
    """Tworzy smart-collection z pojedyncza regula 'tag equals <tag>'.

    sort_order: jeden z 'manual', 'best-selling', 'alpha-asc', 'alpha-desc',
                'price-asc', 'price-desc', 'created', 'created-desc'.
    """
    payload = {
        "smart_collection": {
            "title": title,
            "handle": handle,
            "body_html": body_html or "",
            "rules": [
                {"column": "tag", "relation": "equals", "condition": tag}
            ],
            "disjunctive": False,
            "sort_order": sort_order,
            "published": published,
        }
    }
    out = rest_post(shop, token, "smart_collections.json", payload)
    return (out or {}).get("smart_collection") or {}


def upsert_smart_collection_for_tag(
    shop: str,
    token: str,
    *,
    title: str,
    handle: str,
    tag: str,
    body_html: str | None = None,
    sort_order: str = "best-selling",
) -> tuple[dict, bool]:
    """Znajduje istniejaca smart-collection (po handle, potem po title) lub tworzy nowa.

    Zwraca (collection_dict, created_bool).
    """
    existing = find_smart_collection_by_handle(shop, token, handle)
    if not existing:
        existing = find_smart_collection_by_title(shop, token, title)
    if existing:
        return existing, False
    coll = create_smart_collection_for_tag(
        shop, token,
        title=title, handle=handle, tag=tag,
        body_html=body_html, sort_order=sort_order,
    )
    return coll, True


def set_collection_seo_metafields(
    shop: str,
    token: str,
    collection_id: int,
    *,
    title_tag: str,
    description_tag: str,
) -> None:
    """Ustawia metapola SEO dla kolekcji (global.title_tag / global.description_tag)."""
    for key, value, ftype in (
        ("title_tag", title_tag, "single_line_text_field"),
        ("description_tag", description_tag, "multi_line_text_field"),
    ):
        rest_post(
            shop,
            token,
            f"collections/{collection_id}/metafields.json",
            {
                "metafield": {
                    "namespace": "global",
                    "key": key,
                    "type": ftype,
                    "value": value,
                }
            },
        )


def collection_gid(collection_id: int) -> str:
    return f"gid://shopify/Collection/{collection_id}"


# ---------------------------------------------------------------------------
# Translations API (multi-language - GraphQL Admin)
# Wymaga scope: write_translations (oraz read_translations).
# ---------------------------------------------------------------------------

def get_translatable_resource(
    shop: str, token: str, *, resource_gid: str
) -> list[dict]:
    """Zwraca liste pol mozliwych do tlumaczenia dla zasobu (Product, Collection, ...).

    Z odpowiedzi czerpiemy `key` i `digest` ktore sa wymagane jako 'translatableContentDigest'
    przy `translationsRegister`.

    Returns: lista dictow [{ 'key': str, 'value': str, 'digest': str, 'locale': str }, ...]
    """
    query = """
    query($id: ID!) {
      translatableResource(resourceId: $id) {
        resourceId
        translatableContent { key value digest locale }
      }
    }
    """
    data = graphql(shop, token, query, {"id": resource_gid})
    res = (data or {}).get("translatableResource") or {}
    return list(res.get("translatableContent") or [])


def register_translations(
    shop: str, token: str, *,
    resource_gid: str,
    locale: str,
    fields: dict[str, str],
) -> list[dict]:
    """Zapisuje tlumaczenia dla wskazanego zasobu w danym jezyku.

    fields: dict {<key>: <translated_value>}, np. {'title': 'Indian Summer',
            'body_html': '<p>...</p>'}.
    locale: 'en', 'de', 'fr', 'es', 'nl', 'it'.

    Pod kapotem pobiera 'translatableContent' (z digest) zasobu, dopasowuje keye
    i wysyla `translationsRegister` z gotowymi obiektami.
    """
    contents = get_translatable_resource(shop, token, resource_gid=resource_gid)
    by_key: dict[str, dict] = {}
    for c in contents:
        k = (c or {}).get("key") or ""
        if k:
            by_key[k] = c

    translations: list[dict] = []
    skipped: list[str] = []
    for key, value in (fields or {}).items():
        c = by_key.get(key)
        if not c:
            skipped.append(key)
            continue
        translations.append({
            "key": key,
            "value": value,
            "translatableContentDigest": c.get("digest"),
            "locale": locale,
        })

    if not translations:
        return []

    mutation = """
    mutation registerTranslations($id: ID!, $translations: [TranslationInput!]!) {
      translationsRegister(resourceId: $id, translations: $translations) {
        translations { key value locale }
        userErrors { field message }
      }
    }
    """
    data = graphql(shop, token, mutation, {
        "id": resource_gid,
        "translations": translations,
    })
    errs = ((data or {}).get("translationsRegister") or {}).get("userErrors") or []
    if errs:
        raise ShopifyError(
            f"translationsRegister userErrors ({locale}, {resource_gid}): {errs}; "
            f"skipped keys (no translatable content): {skipped}"
        )
    return ((data or {}).get("translationsRegister") or {}).get("translations") or []


# ---------------------------------------------------------------------------
# Markets API (Catalogs / Price Lists - GraphQL Admin)
# Wymaga scope: write_markets (oraz read_markets).
# ---------------------------------------------------------------------------

def list_markets(shop: str, token: str) -> list[dict]:
    """Zwraca liste rynkow z Shopify (Markets) wraz z handle, currency, regionami i Catalog/PriceList GIDs.

    Format wynikowego dictu (per market):
      {
        'id': '<Market GID>',
        'name': 'Hiszpania',
        'handle': 'spain',
        'enabled': True,
        'primary': False,
        'currency': 'EUR',
        'country_codes': ['ES'],
        'catalogs': [{'id': '<Catalog GID>', 'priceList': {'id': '<PriceList GID>',
                     'currency': 'EUR', 'name': 'Hiszpania catalog'}}, ...],
      }
    """
    query = """
    query {
      markets(first: 50) {
        nodes {
          id
          name
          handle
          enabled
          primary
          currencySettings {
            baseCurrency { currencyCode }
          }
          regions(first: 50) {
            nodes {
              id
              name
              ... on MarketRegionCountry { code }
            }
          }
          catalogs(first: 10) {
            nodes {
              id
              ... on MarketCatalog {
                priceList {
                  id
                  name
                  currency
                  parent {
                    adjustment {
                      type
                      value
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    data = graphql(shop, token, query)
    nodes = ((data or {}).get("markets") or {}).get("nodes") or []
    out: list[dict] = []
    for n in nodes:
        cur = (((n.get("currencySettings") or {}).get("baseCurrency") or {}).get("currencyCode")) or ""
        catalogs = ((n.get("catalogs") or {}).get("nodes")) or []
        regions = ((n.get("regions") or {}).get("nodes")) or []
        country_codes: list[str] = []
        for r in regions:
            cc = (r or {}).get("code")
            if cc:
                country_codes.append(str(cc).upper())
        out.append({
            "id": n.get("id"),
            "name": n.get("name"),
            "handle": n.get("handle"),
            "enabled": bool(n.get("enabled")),
            "primary": bool(n.get("primary")),
            "currency": cur,
            "country_codes": country_codes,
            "catalogs": catalogs,
        })
    return out


def update_price_list_percentage_adjustment(
    shop: str, token: str, *,
    price_list_id: str,
    percent: float,
) -> dict:
    """Ustawia procentowy adjustment dla cennika (np. +15% nad bazowy).

    type: PERCENTAGE_INCREASE (gdy percent > 0) / PERCENTAGE_DECREASE (gdy < 0).
    """
    pct = float(percent)
    if abs(pct) < 1e-9:
        adj = {"type": "PERCENTAGE_INCREASE", "value": 0.0}
    elif pct >= 0:
        adj = {"type": "PERCENTAGE_INCREASE", "value": pct}
    else:
        adj = {"type": "PERCENTAGE_DECREASE", "value": abs(pct)}

    mutation = """
    mutation updatePL($id: ID!, $input: PriceListUpdateInput!) {
      priceListUpdate(id: $id, input: $input) {
        priceList {
          id
          parent { adjustment { type value } }
        }
        userErrors { field message }
      }
    }
    """
    data = graphql(shop, token, mutation, {
        "id": price_list_id,
        "input": {"parent": {"adjustment": adj}},
    })
    errs = ((data or {}).get("priceListUpdate") or {}).get("userErrors") or []
    if errs:
        raise ShopifyError(f"priceListUpdate userErrors: {errs}")
    return ((data or {}).get("priceListUpdate") or {}).get("priceList") or {}


def publish_collection_everywhere(shop: str, token: str, coll_gid: str) -> list[str]:
    """Publikuje kolekcje na wszystkich kanalach (publications). Zwraca nazwy kanalow.

    Wymaga scope: write_publications.
    """
    pubs = list_publications(shop, token)
    if not pubs:
        return []
    mutation = """
    mutation publishColl($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) {
        publishable { ... on Collection { id } }
        userErrors { field message }
      }
    }
    """
    variables = {
        "id": coll_gid,
        "input": [{"publicationId": p["id"]} for p in pubs],
    }
    data = graphql(shop, token, mutation, variables)
    errors = (data.get("publishablePublish") or {}).get("userErrors") or []
    if errors:
        raise ShopifyError(f"publishablePublish (collection) userErrors: {errors}")
    return [p.get("name", "") for p in pubs]
