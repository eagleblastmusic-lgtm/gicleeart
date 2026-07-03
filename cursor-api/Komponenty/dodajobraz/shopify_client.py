"""Klient Shopify Admin API (REST + GraphQL) dla dodajobraz.

Korzysta z sesji zapisanej przez oauth-server w .shopify_session.json.
"""
from __future__ import annotations

import base64
import errno
import json
import mimetypes
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

API_VERSION = "2026-04"
# Sciezka do cursor-api/ liczona jako 3 poziomy w gore:
#   __file__ = cursor-api/Komponenty/dodajobraz/shopify_client.py
#   parents[2] = cursor-api/
ROOT = Path(__file__).resolve().parents[2]
SESSION_FILE = ROOT / ".shopify_session.json"
REQUEST_TIMEOUT_SECONDS = 45
_RETRY_DELAYS_SECONDS = (2, 5, 10)
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}
# Shopify REST: 2 wywolania/s na klienta API — odstep chroni batch (create + metafields + upload).
_MIN_REQUEST_INTERVAL_SECONDS = 0.55
_last_request_monotonic = 0.0


class ShopifyError(RuntimeError):
    pass


class OperationCancelled(ShopifyError):
    """Uzytkownik przerwal dluga operacje (np. pobieranie katalogu produktow)."""


def _retry_after_seconds(headers: Any) -> float | None:
    raw = (headers or {}).get("Retry-After") if headers else None
    if raw is None:
        return None
    try:
        return max(0.0, min(float(raw), 30.0))
    except (TypeError, ValueError):
        return None


def _is_transient_network_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return True
        if isinstance(reason, OSError):
            exc = reason
        else:
            text = str(reason).lower()
            return "timed out" in text or "timeout" in text
    if isinstance(exc, OSError):
        code = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
        return code in {
            10053,  # connection aborted
            10054,  # connection reset
            10060,  # connection timed out
            errno.ECONNABORTED,
            errno.ECONNRESET,
            errno.ETIMEDOUT,
        }
    return False


def _throttle_shopify_request() -> None:
    global _last_request_monotonic
    now = time.monotonic()
    if _last_request_monotonic > 0:
        wait = _MIN_REQUEST_INTERVAL_SECONDS - (now - _last_request_monotonic)
        if wait > 0:
            time.sleep(wait)
    _last_request_monotonic = time.monotonic()


def _urlopen_with_retries(req: urllib.request.Request) -> Any:
    method = req.get_method().upper()
    idempotent = method in {"GET", "PUT", "DELETE", "HEAD"}
    attempts = len(_RETRY_DELAYS_SECONDS) + 1
    last_error: BaseException | None = None
    for attempt in range(attempts):
        _throttle_shopify_request()
        try:
            return urllib.request.urlopen(
                req,
                context=ssl.create_default_context(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code not in _TRANSIENT_HTTP_CODES or attempt >= attempts - 1:
                raise
            # POST tylko przy 429 (odrzucone przez limiter) — unikamy duplikatow przy 5xx.
            if not idempotent and e.code != 429:
                raise
            delay = _retry_after_seconds(e.headers) or _RETRY_DELAYS_SECONDS[attempt]
            e.close()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            if not _is_transient_network_error(e) or attempt >= attempts - 1:
                raise ShopifyError(
                    "Tymczasowy blad polaczenia z Shopify po "
                    f"{attempt + 1} probach: {e}"
                ) from e
            delay = _RETRY_DELAYS_SECONDS[attempt]
        time.sleep(delay)
    raise ShopifyError(f"Tymczasowy blad polaczenia z Shopify: {last_error}")


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
        with _urlopen_with_retries(req) as resp:
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


def rest_delete(shop: str, token: str, path: str) -> None:
    url = f"https://{shop}/admin/api/{API_VERSION}/{path.lstrip('/')}"
    _request("DELETE", url, token)


def _paginate_link_header(url: str, token: str, *, list_key: str) -> Iterator[list[dict]]:
    """GET z paginacja Link: rel=next."""
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
            with _urlopen_with_retries(req) as resp:
                raw = resp.read().decode("utf-8")
                link_header = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise ShopifyError(f"HTTP {e.code} GET {url}\n{detail}") from e
        data = json.loads(raw) if raw else {}
        yield (data or {}).get(list_key) or []

        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
                    break
        url = next_url


def fetch_all_collects(shop: str, token: str) -> list[dict]:
    """Wszystkie powiazania produkt <-> custom collection (collects)."""
    base = (
        f"https://{shop}/admin/api/{API_VERSION}/collects.json?"
        + urllib.parse.urlencode({"limit": 250})
    )
    out: list[dict] = []
    for batch in _paginate_link_header(base, token, list_key="collects"):
        out.extend(batch)
    return out


def fetch_collection_catalog(shop: str, token: str) -> dict[int, dict[str, Any]]:
    """id kolekcji -> {id, title, kind} (custom | smart)."""
    catalog: dict[int, dict[str, Any]] = {}
    for list_key, kind in (("custom_collections", "custom"), ("smart_collections", "smart")):
        base = (
            f"https://{shop}/admin/api/{API_VERSION}/{list_key}.json?"
            + urllib.parse.urlencode({"limit": 250, "fields": "id,title"})
        )
        for batch in _paginate_link_header(base, token, list_key=list_key):
            for item in batch:
                cid = int(item.get("id") or 0)
                if not cid:
                    continue
                catalog[cid] = {
                    "id": cid,
                    "title": (item.get("title") or "").strip(),
                    "kind": kind,
                }
    return catalog


def list_product_collects(shop: str, token: str, product_id: int) -> list[dict]:
    data = rest_get(shop, token, "collects.json", product_id=int(product_id), limit=250)
    return (data or {}).get("collects") or []


def delete_collect(shop: str, token: str, collect_id: int) -> None:
    rest_delete(shop, token, f"collects/{int(collect_id)}.json")


def graphql(shop: str, token: str, query: str, variables: dict | None = None) -> dict:
    url = f"https://{shop}/admin/api/{API_VERSION}/graphql.json"
    body = {"query": query, "variables": variables or {}}
    data = _request("POST", url, token, body=body)
    if not isinstance(data, dict):
        raise ShopifyError(f"Nieoczekiwana odpowiedz GraphQL: {data!r}")
    if data.get("errors"):
        raise ShopifyError(f"GraphQL errors: {json.dumps(data['errors'], ensure_ascii=False)}")
    return data.get("data") or {}


def get_presentment_currency_setting(
    shop: str,
    token: str,
    currency_code: str = "EUR",
) -> dict[str, Any]:
    """Zwraca ustawienia waluty prezentacji z `Shop.currencySettings` (Admin GraphQL).

    Dla sklepu w PLN i waluty EUR pole `manual_rate` to opcjonalny mnoznik przy konwersji
    **ze waluty sklepu** (gdy wlaczony reczny kurs w Shopify). Gdy `manual_rate` jest None,
    Shopify stosuje kurs automatyczny — liczby nie ma w tym API (zostaje `rate_updated_at`).

    Zwraca m.in.: `shop_currency`, `found`, `currency`, `enabled`, `manual_rate`, `rate_updated_at`.
    """
    target = (currency_code or "EUR").strip().upper()
    query = """
    query ShopCurrencySettings($first: Int!) {
      shop {
        currencyCode
        currencySettings(first: $first) {
          edges {
            node {
              currencyCode
              currencyName
              enabled
              manualRate
              rateUpdatedAt
            }
          }
        }
      }
    }
    """
    data = graphql(shop, token, query, {"first": 80})
    s = (data or {}).get("shop") or {}
    base = str(s.get("currencyCode") or "").upper()
    edges = (((s.get("currencySettings") or {}).get("edges")) or [])
    for e in edges:
        n = (e or {}).get("node") or {}
        code = str(n.get("currencyCode") or "").upper()
        if code != target:
            continue
        raw_mr = n.get("manualRate")
        manual: float | None
        if raw_mr is None or raw_mr == "":
            manual = None
        else:
            try:
                manual = float(raw_mr)
            except (TypeError, ValueError):
                manual = None
        return {
            "found": True,
            "shop_currency": base,
            "currency": target,
            "currency_name": str(n.get("currencyName") or ""),
            "enabled": bool(n.get("enabled")),
            "manual_rate": manual,
            "rate_updated_at": n.get("rateUpdatedAt"),
        }
    return {
        "found": False,
        "shop_currency": base,
        "currency": target,
    }


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
    position: int | None = None,
    logger: Callable[[str], None] | None = None,
) -> dict:
    from .image_upload import resolve_shopify_upload

    resolved = resolve_shopify_upload(image_path, logger=logger)
    try:
        raw = resolved.path.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        image_obj: dict = {
            "attachment": b64,
            "filename": resolved.filename,
        }
        if alt:
            image_obj["alt"] = alt
        if position is not None:
            image_obj["position"] = int(position)
        out = rest_post(shop, token, f"products/{product_id}/images.json", {"image": image_obj})
        return (out or {}).get("image") or {}
    finally:
        resolved.cleanup()


def add_to_collect(shop: str, token: str, product_id: int, collection_id: int) -> dict:
    out = rest_post(
        shop,
        token,
        "collects.json",
        {"collect": {"product_id": product_id, "collection_id": collection_id}},
    )
    return (out or {}).get("collect") or {}


def is_product_in_collection(
    shop: str,
    token: str,
    product_id: int,
    collection_id: int,
    *,
    collection_kind: str | None = None,
) -> bool:
    """Sprawdza, czy produkt jest w danej kolekcji (custom przez collects, smart przez liste produktow)."""
    pid = int(product_id)
    cid = int(collection_id)
    kind = (collection_kind or "").strip().lower()
    if kind == "custom":
        data = rest_get(shop, token, "collects.json", product_id=pid, limit=250)
        for row in (data or {}).get("collects") or []:
            if int(row.get("collection_id") or 0) == cid:
                return True
        return False
    for prod in iter_collection_products(shop, token, cid, fields="id"):
        if int(prod.get("id") or 0) == pid:
            return True
    return False


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


def get_variant_featured_image_url(
    shop: str,
    token: str,
    *,
    variant_id: int | None,
    product_id: int | None = None,
) -> str | None:
    """URL glownego obrazu wariantu (do miniatur w Produkcji itd.).

    Kolejnosc: obraz przypisany do wariantu (`image_id`), inaczej pierwsze zdjecie produktu.
    """
    if not variant_id:
        return None
    try:
        vid = int(variant_id)
    except (TypeError, ValueError):
        return None
    try:
        out = rest_get(shop, token, f"variants/{vid}.json")
        v = (out or {}).get("variant") or {}
        pid = int(v.get("product_id") or product_id or 0)
        image_id = v.get("image_id")
        if not pid:
            return None
        imgs_out = rest_get(shop, token, f"products/{pid}/images.json")
        images = (imgs_out or {}).get("images") or []
        if image_id:
            iid = int(image_id)
            for im in images:
                if int(im.get("id") or 0) == iid:
                    src = str(im.get("src") or "").strip()
                    return src or None
        if images:
            return str(images[0].get("src") or "").strip() or None
    except ShopifyError:
        return None
    return None


def count_product_images(shop: str, token: str, product_id: int) -> int:
    out = rest_get(shop, token, f"products/{product_id}/images/count.json")
    return int((out or {}).get("count") or 0)


def iter_each_product_page(
    shop: str,
    token: str,
    *,
    product_type: str | None = None,
    fields: str | None = None,
) -> Iterator[list[dict]]:
    """Yields kolejne strony produktow (max 250 na strone). Paginacja Link-header."""
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
            with _urlopen_with_retries(req) as resp:
                raw = resp.read().decode("utf-8")
                link_header = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise ShopifyError(f"HTTP {e.code} GET {url}\n{detail}") from e
        data = json.loads(raw) if raw else {}
        batch = (data or {}).get("products") or []
        yield batch

        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
                    break
        url = next_url


def fetch_all_products(
    shop: str,
    token: str,
    *,
    product_type: str | None = None,
    fields: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_page_progress: Callable[[int], None] | None = None,
) -> list[dict]:
    """Pobiera wszystkie produkty z opcjonalnym anulowaniem miedzy stronami.

    `on_page_progress(n)` wywolywane po kazdej stronie z licznikiem produktow dotychczas.
    """
    all_products: list[dict] = []
    for batch in iter_each_product_page(
        shop, token, product_type=product_type, fields=fields
    ):
        if should_cancel and should_cancel():
            raise OperationCancelled("Przerwano pobieranie katalogu produktow.")
        all_products.extend(batch)
        if on_page_progress:
            on_page_progress(len(all_products))
    return all_products


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
    return fetch_all_products(shop, token, product_type=product_type, fields=fields)


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
            with _urlopen_with_retries(req) as resp:
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
            with _urlopen_with_retries(req) as resp:
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
    return update_variant(shop, token, variant_id, {"price": str(price)})


def create_product_variant(shop: str, token: str, product_id: int, fields: dict) -> dict:
    """Tworzy wariant produktu (REST POST /products/{product_id}/variants.json)."""
    out = rest_post(
        shop,
        token,
        f"products/{int(product_id)}/variants.json",
        {"variant": dict(fields or {})},
    )
    return (out or {}).get("variant") or {}


def update_variant(shop: str, token: str, variant_id: int, fields: dict) -> dict:
    """Aktualizuje pola wariantu, zachowujac pozostale dane Shopify (SKU, barcode itd.)."""
    vid = int(variant_id)
    out = rest_put(
        shop,
        token,
        f"variants/{vid}.json",
        {"variant": {"id": vid, **dict(fields or {})}},
    )
    return (out or {}).get("variant") or {}


def delete_product_variant(shop: str, token: str, product_id: int, variant_id: int) -> None:
    """Usuwa wariant produktu (REST DELETE /products/{product_id}/variants/{variant_id}.json)."""
    rest_delete(shop, token, f"products/{int(product_id)}/variants/{int(variant_id)}.json")


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


def set_product_featured_image(
    shop: str, token: str, product_id: int, image_id: int
) -> dict:
    """Ustawia zdjecie glowne produktu (kolekcje, kafelki) niezaleznie od position w galerii."""
    return update_product(shop, token, product_id, {"image": {"id": image_id}})


def find_redirect(shop: str, token: str, redirect_path: str) -> dict | None:
    """GET /redirects.json?path=... — pierwsze dopasowanie lub None."""
    normalized = redirect_path if redirect_path.startswith("/") else f"/{redirect_path}"
    qs = urllib.parse.urlencode({"path": normalized, "limit": 1})
    out = rest_get(shop, token, f"redirects.json?{qs}")
    items = (out or {}).get("redirects") or []
    return items[0] if items else None


def create_redirect(shop: str, token: str, path: str, target: str) -> dict:
    """POST/PUT /redirects.json — przekierowanie (np. stary handle produktu)."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    normalized_target = target if target.startswith("/") else f"/{target}"
    existing = find_redirect(shop, token, normalized_path)
    if existing:
        rid = int(existing.get("id") or 0)
        if existing.get("target") == normalized_target:
            return existing
        if rid:
            out = rest_put(
                shop,
                token,
                f"redirects/{rid}.json",
                {
                    "redirect": {
                        "id": rid,
                        "path": normalized_path,
                        "target": normalized_target,
                    }
                },
            )
            return (out or {}).get("redirect") or {}
    out = rest_post(
        shop,
        token,
        "redirects.json",
        {"redirect": {"path": normalized_path, "target": normalized_target}},
    )
    return (out or {}).get("redirect") or {}


def ensure_product_handle_redirect(
    shop: str, token: str, old_handle: str, new_handle: str
) -> dict | None:
    """Redirect /products/{old} -> /products/{new} gdy handle sie zmienil."""
    old_handle = (old_handle or "").strip()
    new_handle = (new_handle or "").strip()
    if not old_handle or not new_handle or old_handle == new_handle:
        return None
    return create_redirect(
        shop,
        token,
        f"/products/{old_handle}",
        f"/products/{new_handle}",
    )


def update_product(shop: str, token: str, product_id: int, fields: dict) -> dict:
    """PUT /products/{id}.json - aktualizuje wskazane pola (body_html, tags, handle, title, ...).

    Nie rusza wariantow, opcji ani kolekcji, chyba ze jawnie je przekazesz.
    Przy zmianie handle tworzy redirect ze starego URL produktu.
    """
    fields = dict(fields or {})
    old_handle: str | None = None
    new_handle = fields.get("handle")
    if new_handle:
        prod = get_product(shop, token, product_id)
        old_handle = (prod or {}).get("handle") or ""
    payload = {"product": {"id": product_id, **fields}}
    out = rest_put(shop, token, f"products/{product_id}.json", payload)
    product = (out or {}).get("product") or {}
    if new_handle and old_handle and old_handle != new_handle:
        ensure_product_handle_redirect(shop, token, old_handle, new_handle)
    return product


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


def find_custom_collection_by_title(shop: str, token: str, title: str) -> dict | None:
    """Szuka custom-collection po tytule (case-insensitive)."""
    t = (title or "").strip().lower()
    if not t:
        return None
    data = rest_get(shop, token, "custom_collections.json", title=title, limit=5)
    for it in (data or {}).get("custom_collections") or []:
        if (it.get("title") or "").strip().lower() == t:
            return it
    return None


def create_custom_collection(
    shop: str,
    token: str,
    *,
    title: str,
    body_html: str = "",
    published: bool = True,
    handle: str | None = None,
) -> dict:
    """Tworzy custom-collection (np. kolekcje artysty 'Nazwisko, Imie')."""
    from .parser import artist_collection_handle_from_title

    payload = {
        "custom_collection": {
            "title": title,
            "body_html": body_html,
            "published": published,
        }
    }
    h = (handle or "").strip()
    if not h and ", " in (title or ""):
        h = artist_collection_handle_from_title(title)
    if h:
        payload["custom_collection"]["handle"] = h
    out = rest_post(shop, token, "custom_collections.json", payload)
    return (out or {}).get("custom_collection") or {}


def update_custom_collection(
    shop: str,
    token: str,
    collection_id: int,
    *,
    body_html: str | None = None,
    image_src: str | None = None,
    handle: str | None = None,
) -> dict:
    """Aktualizuje custom-collection (opis `body_html`, baner `image.src`, opcjonalnie `handle`)."""
    cc: dict[str, Any] = {"id": int(collection_id)}
    if body_html is not None:
        cc["body_html"] = body_html
    if image_src:
        cc["image"] = {"src": image_src}
    if handle is not None:
        cc["handle"] = handle
    out = rest_put(
        shop, token, f"custom_collections/{int(collection_id)}.json", {"custom_collection": cc}
    )
    return (out or {}).get("custom_collection") or {}


def _http_post_multipart(url: str, body: bytes, content_type: str) -> None:
    """POST multipart na zewnetrzny URL (staged upload target - GCS/S3), bez tokenu Shopify."""
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": content_type}, method="POST"
    )
    try:
        with _urlopen_with_retries(req) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise ShopifyError(f"HTTP {e.code} POST (staged upload)\n{detail}") from e


def _poll_file_node_url(shop: str, token: str, file_id: str) -> str | None:
    """Zwraca CDN url pliku z Shopify Files (gdy READY), inaczej None."""
    query = """
    query FileUrl($id: ID!) {
      node(id: $id) {
        ... on MediaImage {
          fileStatus
          image { url }
          originalSource { url }
        }
        ... on GenericFile { fileStatus url }
      }
    }
    """
    node_data = graphql(shop, token, query, {"id": file_id})
    node = (node_data or {}).get("node") or {}
    if (node.get("fileStatus") or "").upper() != "READY":
        return None
    original = node.get("originalSource") or {}
    original_url = (original.get("url") or "").strip()
    img = node.get("image") or {}
    image_url = (img.get("url") or "").strip()
    generic_url = (node.get("url") or "").strip()
    return generic_url or image_url or original_url or None


def _poll_file_node_ready(shop: str, token: str, file_id: str) -> bool:
    query = """
    query FileReady($id: ID!) {
      node(id: $id) {
        ... on MediaImage { fileStatus }
        ... on GenericFile { fileStatus }
        ... on Video { fileStatus }
      }
    }
    """
    node_data = graphql(shop, token, query, {"id": file_id})
    node = (node_data or {}).get("node") or {}
    return (node.get("fileStatus") or "").upper() == "READY"


def video_gid_to_shopify_ref(file_id: str) -> str:
    """Konwertuje gid://shopify/Video/… na shopify://files/videos/… (format theme JSON)."""
    gid = (file_id or "").strip()
    if not gid.startswith("gid://shopify/Video/"):
        raise ShopifyError(f"Nieprawidłowy GID wideo: {gid!r}")
    shop, token = load_session()
    query = """
    query VideoFilename($id: ID!) {
      node(id: $id) {
        ... on Video { filename }
      }
    }
    """
    data = graphql(shop, token, query, {"id": gid})
    node = (data or {}).get("node") or {}
    filename = str(node.get("filename") or "").strip()
    if not filename:
        raise ShopifyError(f"Brak filename dla wideo {gid}.")
    return f"shopify://files/videos/{filename}"


def upload_video_to_shopify_files(
    local_path: Path,
    *,
    alt: str | None = None,
) -> str:
    """Upload wideo do Shopify Files (resource VIDEO). Zwraca shopify://files/videos/… do theme JSON."""
    local_path = Path(local_path)
    if not local_path.is_file():
        raise ShopifyError(f"Plik nie istnieje: {local_path}")
    shop, token = load_session()
    raw = local_path.read_bytes()
    size = len(raw)
    ext = local_path.suffix.lower()
    mime_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    }
    mime = mime_map.get(ext) or mimetypes.guess_type(local_path.name)[0] or "video/mp4"
    filename = local_path.name

    staged = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets { url resourceUrl parameters { name value } }
        userErrors { field message }
      }
    }
    """
    data = graphql(
        shop,
        token,
        staged,
        {
            "input": [
                {
                    "resource": "VIDEO",
                    "filename": filename,
                    "mimeType": mime,
                    "httpMethod": "POST",
                    "fileSize": str(size),
                }
            ]
        },
    )
    res = (data or {}).get("stagedUploadsCreate") or {}
    if res.get("userErrors"):
        raise ShopifyError(f"stagedUploadsCreate errors: {res['userErrors']}")
    targets = res.get("stagedTargets") or []
    if not targets:
        raise ShopifyError("stagedUploadsCreate: brak targets.")
    t = targets[0]
    upload_url = t.get("url")
    resource_url = t.get("resourceUrl")
    params = {p["name"]: p["value"] for p in (t.get("parameters") or [])}

    boundary = "----gicleeart-" + uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in params.items():
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        parts.append(f"{value}\r\n".encode("utf-8"))
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(
            "utf-8"
        )
    )
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    parts.append(raw)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    _http_post_multipart(
        upload_url, b"".join(parts), f"multipart/form-data; boundary={boundary}"
    )

    file_create = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { id fileStatus ... on Video { id } }
        userErrors { field message }
      }
    }
    """
    fc = graphql(
        shop,
        token,
        file_create,
        {
            "files": [
                {
                    "alt": alt or filename,
                    "originalSource": resource_url,
                    "contentType": "VIDEO",
                }
            ]
        },
    )
    fc_res = (fc or {}).get("fileCreate") or {}
    errors = fc_res.get("userErrors") or []
    if errors:
        raise ShopifyError(f"fileCreate errors: {errors}")
    files = fc_res.get("files") or []
    if not files:
        raise ShopifyError("fileCreate: brak files w odpowiedzi.")
    file_id = str(files[0].get("id") or "")
    if not file_id:
        raise ShopifyError("fileCreate: brak id w odpowiedzi.")

    for _ in range(60):
        if _poll_file_node_ready(shop, token, file_id):
            return video_gid_to_shopify_ref(file_id)
        time.sleep(1)
    raise ShopifyError(f"Shopify Video {file_id} nie bylo gotowe po 60s.")


def upload_file_to_shopify_files(
    local_path: Path,
    *,
    alt: str | None = None,
    preserve_original_bytes: bool = False,
) -> str:
    """Uploaduje lokalny plik do Shopify Files i zwraca publiczny CDN URL.

    Kroki (GraphQL Admin 2026-04): stagedUploadsCreate -> POST multipart ->
    fileCreate -> polling fileStatus=READY. Wymaga scope `write_files`.
    """
    local_path = Path(local_path)
    if not local_path.is_file():
        raise ShopifyError(f"Plik nie istnieje: {local_path}")
    shop, token = load_session()
    raw = local_path.read_bytes()
    size = len(raw)
    mime = mimetypes.guess_type(local_path.name)[0] or "image/jpeg"
    filename = local_path.name

    staged = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets { url resourceUrl parameters { name value } }
        userErrors { field message }
      }
    }
    """
    data = graphql(
        shop,
        token,
        staged,
        {
            "input": [
                {
                    "resource": "FILE",
                    "filename": filename,
                    "mimeType": mime,
                    "httpMethod": "POST",
                    "fileSize": str(size),
                }
            ]
        },
    )
    res = (data or {}).get("stagedUploadsCreate") or {}
    if res.get("userErrors"):
        raise ShopifyError(f"stagedUploadsCreate errors: {res['userErrors']}")
    targets = res.get("stagedTargets") or []
    if not targets:
        raise ShopifyError("stagedUploadsCreate: brak targets.")
    t = targets[0]
    upload_url = t.get("url")
    resource_url = t.get("resourceUrl")
    params = {p["name"]: p["value"] for p in (t.get("parameters") or [])}

    boundary = "----gicleeart-" + uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in params.items():
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        parts.append(f"{value}\r\n".encode("utf-8"))
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(
            "utf-8"
        )
    )
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    parts.append(raw)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    _http_post_multipart(
        upload_url, b"".join(parts), f"multipart/form-data; boundary={boundary}"
    )

    file_input: dict[str, Any] = {
        "alt": alt or filename,
        "originalSource": resource_url,
    }
    if preserve_original_bytes:
        file_input["contentType"] = "FILE"

    file_create = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { id fileStatus ... on MediaImage { image { url } } ... on GenericFile { url } }
        userErrors { field message }
      }
    }
    """
    fc = graphql(
        shop,
        token,
        file_create,
        {"files": [file_input]},
    )
    fc_res = (fc or {}).get("fileCreate") or {}
    errors = fc_res.get("userErrors") or []
    if errors and preserve_original_bytes:
        fc = graphql(
            shop,
            token,
            file_create,
            {"files": [{"alt": alt or filename, "originalSource": resource_url}]},
        )
        fc_res = (fc or {}).get("fileCreate") or {}
        errors = fc_res.get("userErrors") or []
    if errors:
        raise ShopifyError(f"fileCreate errors: {errors}")
    files = fc_res.get("files") or []
    if not files:
        raise ShopifyError("fileCreate: brak files w odpowiedzi.")
    file_id = files[0].get("id")

    for _ in range(30):
        url = _poll_file_node_url(shop, token, file_id)
        if url:
            return url
        time.sleep(1)
    raise ShopifyError(f"Shopify File {file_id} nie bylo gotowe po 30s.")


# ---------------------------------------------------------------------------
# Online Store Navigation (menu) - GraphQL Admin
# Wymaga scope: read_online_store_navigation, write_online_store_navigation.
# menuUpdate NADPISUJE cale menu, wiec zawsze rekonstruujemy pelne drzewo pozycji.
# ---------------------------------------------------------------------------

_MENU_ITEM_FIELDS = "id title type url resourceId tags"


def _menu_items_block(depth: int = 3) -> str:
    block = _MENU_ITEM_FIELDS
    for _ in range(depth - 1):
        block = _MENU_ITEM_FIELDS + " items { " + block + " }"
    return block


def list_menus(shop: str, token: str, *, first: int = 50) -> list[dict]:
    """Lista menu nawigacji z zagniezdzonymi pozycjami (do 3 poziomow)."""
    query = (
        "query Menus($first: Int!) { menus(first: $first) { nodes { "
        "id handle title items { " + _menu_items_block(3) + " } } } }"
    )
    data = graphql(shop, token, query, {"first": int(first)})
    return ((data.get("menus") or {}).get("nodes")) or []


def _find_menu_item(items: list[dict], title: str) -> dict | None:
    want = (title or "").strip().lower()
    for it in items or []:
        if (it.get("title") or "").strip().lower() == want:
            return it
        sub = _find_menu_item(it.get("items") or [], title)
        if sub:
            return sub
    return None


def fetch_artist_catalog_order(
    shop: str,
    token: str,
    *,
    menu_handle: str = "main-menu",
    parent_title: str = "ARTYŚCI",
) -> list[dict]:
    """Kolejnosc artystow jak w katalogu na stronie (menu -> ARTYSCI -> dzieci).

    Kazdy element: {sort_index, collection_title}.
    """
    menu = find_menu(shop, token, handle=menu_handle)
    if menu is None:
        menu = find_menu(shop, token, contains_item_title=parent_title)
    if not menu:
        return []
    parent = _find_menu_item(menu.get("items") or [], parent_title)
    if not parent:
        return []
    out: list[dict] = []
    for idx, child in enumerate(parent.get("items") or []):
        title = (child.get("title") or "").strip()
        if not title:
            continue
        out.append({"sort_index": idx, "collection_title": title})
    return out


def find_menu(
    shop: str,
    token: str,
    *,
    handle: str | None = None,
    contains_item_title: str | None = None,
) -> dict | None:
    """Znajduje menu po handle lub po obecnosci pozycji o danym tytule."""
    menus = list_menus(shop, token)
    if handle:
        h = handle.strip().lower()
        for m in menus:
            if (m.get("handle") or "").strip().lower() == h:
                return m
    if contains_item_title:
        for m in menus:
            if _find_menu_item(m.get("items") or [], contains_item_title):
                return m
    return None


def _item_to_input(item: dict) -> dict:
    """Pozycja z query -> MenuItemUpdateInput (zachowuje id/typ/zasob/zagniezdzenia)."""
    out: dict = {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "type": item.get("type") or "HTTP",
    }
    if item.get("url"):
        out["url"] = item["url"]
    if item.get("resourceId"):
        out["resourceId"] = item["resourceId"]
    if item.get("tags"):
        out["tags"] = item["tags"]
    children = item.get("items") or []
    if children:
        out["items"] = [_item_to_input(c) for c in children]
    return out


def _find_input_by_title(items: list[dict], title: str) -> dict | None:
    want = (title or "").strip().lower()
    for it in items or []:
        if (it.get("title") or "").strip().lower() == want:
            return it
        sub = _find_input_by_title(it.get("items") or [], title)
        if sub:
            return sub
    return None


def add_menu_child_collection(
    shop: str,
    token: str,
    *,
    parent_title: str,
    child_title: str,
    collection_gid: str,
    menu_handle: str | None = None,
    skip_if_exists: bool = True,
    keep_sorted: bool = True,
) -> dict:
    """Dodaje pozycje typu COLLECTION pod parentem o danym tytule (np. 'ARTYSCI').

    Gdy keep_sorted=True wstawia nowa pozycje alfabetycznie (case-insensitive)
    miedzy rodzenstwo, NIE zmieniajac kolejnosci pozostalych pozycji.

    Zwraca {'menu_handle', 'created': bool}. Gdy pozycja juz istnieje i
    skip_if_exists=True - nie modyfikuje menu.
    """
    menu = None
    if menu_handle:
        menu = find_menu(shop, token, handle=menu_handle)
    if menu is None:
        menu = find_menu(shop, token, contains_item_title=parent_title)
    if menu is None:
        raise ShopifyError(
            f"Nie znaleziono menu z pozycja '{parent_title}'. "
            "Podaj poprawny handle (np. 'main-menu')."
        )

    items = [_item_to_input(it) for it in (menu.get("items") or [])]
    parent = _find_input_by_title(items, parent_title)
    if parent is None:
        raise ShopifyError(
            f"W menu '{menu.get('handle')}' brak pozycji nadrzednej '{parent_title}'."
        )

    parent.setdefault("items", [])
    if skip_if_exists:
        for ch in parent["items"]:
            if (ch.get("title") or "").strip().lower() == child_title.strip().lower():
                return {"menu_handle": menu.get("handle"), "created": False}

    new_child = {"title": child_title, "type": "COLLECTION", "resourceId": collection_gid}
    if keep_sorted:
        from .parser import catalog_artist_sort_key

        key = catalog_artist_sort_key(child_title)
        insert_at = len(parent["items"])
        for idx, ch in enumerate(parent["items"]):
            if catalog_artist_sort_key(ch.get("title") or "") > key:
                insert_at = idx
                break
        parent["items"].insert(insert_at, new_child)
    else:
        parent["items"].append(new_child)

    mutation = (
        "mutation MenuUpdate($id: ID!, $title: String!, $handle: String!, "
        "$items: [MenuItemUpdateInput!]!) { "
        "menuUpdate(id: $id, title: $title, handle: $handle, items: $items) { "
        "menu { id handle title } userErrors { field message } } }"
    )
    res = graphql(
        shop,
        token,
        mutation,
        {
            "id": menu["id"],
            "title": menu["title"],
            "handle": menu["handle"],
            "items": items,
        },
    )
    payload = res.get("menuUpdate") or {}
    errs = payload.get("userErrors") or []
    if errs:
        raise ShopifyError(
            f"menuUpdate userErrors: {json.dumps(errs, ensure_ascii=False)}"
        )
    return {"menu_handle": menu.get("handle"), "created": True}


def resort_artist_menu_children(
    shop: str,
    token: str,
    *,
    parent_title: str = "ARTYŚCI",
    menu_handle: str | None = None,
) -> dict:
    """Ponownie sortuje dzieci pozycji menu (np. ARTYŚCI) po nazwisku z czastkami."""
    from .parser import catalog_artist_sort_key, format_catalog_artist_title

    menu = None
    if menu_handle:
        menu = find_menu(shop, token, handle=menu_handle)
    if menu is None:
        menu = find_menu(shop, token, contains_item_title=parent_title)
    if menu is None:
        raise ShopifyError(
            f"Nie znaleziono menu z pozycja '{parent_title}'. "
            "Podaj poprawny handle (np. 'main-menu')."
        )

    items = [_item_to_input(it) for it in (menu.get("items") or [])]
    parent = _find_input_by_title(items, parent_title)
    if parent is None:
        raise ShopifyError(
            f"W menu '{menu.get('handle')}' brak pozycji nadrzednej '{parent_title}'."
        )

    children = parent.get("items") or []
    for ch in children:
        raw = (ch.get("title") or "").strip()
        if raw:
            ch["title"] = format_catalog_artist_title(raw)
    children.sort(key=lambda ch: catalog_artist_sort_key(ch.get("title") or ""))
    parent["items"] = children

    mutation = (
        "mutation MenuUpdate($id: ID!, $title: String!, $handle: String!, "
        "$items: [MenuItemUpdateInput!]!) { "
        "menuUpdate(id: $id, title: $title, handle: $handle, items: $items) { "
        "menu { id handle title } userErrors { field message } } }"
    )
    res = graphql(
        shop,
        token,
        mutation,
        {
            "id": menu["id"],
            "title": menu["title"],
            "handle": menu["handle"],
            "items": items,
        },
    )
    payload = res.get("menuUpdate") or {}
    errs = payload.get("userErrors") or []
    if errs:
        raise ShopifyError(
            f"menuUpdate userErrors: {json.dumps(errs, ensure_ascii=False)}"
        )
    return {"menu_handle": menu.get("handle"), "count": len(children)}


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
