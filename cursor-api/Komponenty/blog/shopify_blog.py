"""Klient Shopify Admin API dla Blogow i Artykulow (REST) + tlumaczenia (GraphQL).

Uzywa tej samej sesji (.shopify_session.json) co reszta aplikacji.
Wymagane scopes: `read_content`, `write_content` (blog/articles),
`read_translations`, `write_translations` (multi-jezykowe artykuly),
`read_publications`, `write_publications` (publikacja na kanalach).

Po dodaniu scopes: w `cursor-api/` uruchom `npm run oauth`.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

# Reuzywamy klienta REST/GraphQL z dodajobraz - nie dublujemy kodu.
from Komponenty.dodajobraz.shopify_client import (
    ShopifyError,
    graphql,
    load_session,
    register_translations,
    rest_get,
    rest_post,
    rest_put,
)

__all__ = [
    "ShopifyError",
    "load_session",
    "list_blogs",
    "list_articles",
    "get_article",
    "create_article",
    "update_article",
    "article_gid",
    "register_article_translations",
    "article_admin_url",
]


def list_blogs(shop: str, token: str) -> list[dict]:
    """Zwraca wszystkie blogi (zazwyczaj 1 - 'News')."""
    data = rest_get(shop, token, "blogs.json")
    return (data or {}).get("blogs") or []


def list_articles(shop: str, token: str, blog_id: int, *, limit: int = 250) -> list[dict]:
    """Zwraca wszystkie artykuly z danego bloga (paginacja 250 per strona)."""
    articles: list[dict] = []
    since_id = 0
    while True:
        data = rest_get(
            shop, token, f"blogs/{blog_id}/articles.json",
            limit=limit, since_id=since_id,
        )
        batch = (data or {}).get("articles") or []
        if not batch:
            break
        articles.extend(batch)
        if len(batch) < limit:
            break
        since_id = max(int(a.get("id", 0)) for a in batch)
    return articles


def list_all_articles(shop: str, token: str) -> list[dict]:
    """Zwraca artykuly ze WSZYSTKICH blogow z dodanym polem `_blog_handle` i `_blog_title`."""
    out: list[dict] = []
    for blog in list_blogs(shop, token):
        bid = int(blog.get("id") or 0)
        if not bid:
            continue
        for art in list_articles(shop, token, bid):
            art = dict(art)
            art["_blog_id"] = bid
            art["_blog_handle"] = blog.get("handle") or ""
            art["_blog_title"] = blog.get("title") or ""
            out.append(art)
    return out


def get_article(shop: str, token: str, blog_id: int, article_id: int) -> dict:
    data = rest_get(shop, token, f"blogs/{blog_id}/articles/{article_id}.json")
    return (data or {}).get("article") or {}


def _build_image_payload(image_src: str, image_alt: str) -> dict[str, Any] | None:
    """Buduje obiekt `image` dla Shopify Article API.

    Akceptuje:
    - URL http(s):// -> {"src": URL, "alt": ...}
    - Lokalna sciezka do pliku obrazka (.jpg/.png/.webp/.gif) -> {"attachment": base64, "filename": name, "alt": ...}
    - pusty string -> None (bez zdjecia)
    """
    if not image_src:
        return None
    src = image_src.strip().strip('"')
    if src.startswith("http://") or src.startswith("https://"):
        return {"src": src, "alt": image_alt or ""}
    # Lokalny plik - czytamy i kodujemy base64
    p = Path(src).expanduser()
    if not p.is_file():
        raise ShopifyError(f"Plik obrazka nie istnieje: {p}")
    mime, _ = mimetypes.guess_type(p.name)
    if mime and not mime.startswith("image/"):
        raise ShopifyError(f"Plik nie jest obrazkiem ({mime}): {p}")
    try:
        raw = p.read_bytes()
    except OSError as e:
        raise ShopifyError(f"Nie mozna odczytac pliku {p}: {e}") from e
    # Shopify limit na attachment: ~20MB; ostrzezenie przy >10MB
    if len(raw) > 20 * 1024 * 1024:
        raise ShopifyError(f"Plik {p.name} jest za duzy ({len(raw) // 1024 // 1024} MB). Max ~20MB.")
    b64 = base64.b64encode(raw).decode("ascii")
    return {
        "attachment": b64,
        "filename": p.name,
        "alt": image_alt or p.stem,
    }


def create_article(
    shop: str, token: str, blog_id: int, *,
    title: str,
    body_html: str,
    summary_html: str = "",
    tags: list[str] | None = None,
    author: str = "GicleeArt",
    image_src: str = "",
    image_alt: str = "",
    seo_title: str = "",
    seo_description: str = "",
    published: bool = True,
) -> dict:
    """Tworzy artykul w podanym blogu. Zwraca pelny obiekt z `id`, `handle`, `admin_graphql_api_id`.

    `image_src` moze byc:
    - URL-em (http/https) -> przekazywany jako `image.src`,
    - lokalna sciezka do pliku obrazka -> kodowany base64 i wysylany jako `image.attachment` + `filename`,
    - pusty -> bez zdjecia.
    """
    payload: dict[str, Any] = {
        "article": {
            "title": title,
            "body_html": body_html,
            "summary_html": summary_html or None,
            "author": author or "GicleeArt",
            "tags": ", ".join(tags or []),
            "published": bool(published),
        }
    }
    image_payload = _build_image_payload(image_src, image_alt or title)
    if image_payload:
        payload["article"]["image"] = image_payload

    # SEO -> metafields
    metafields: list[dict] = []
    if seo_title:
        metafields.append({
            "key": "title_tag", "namespace": "global",
            "value": seo_title, "type": "single_line_text_field",
        })
    if seo_description:
        metafields.append({
            "key": "description_tag", "namespace": "global",
            "value": seo_description, "type": "multi_line_text_field",
        })
    if metafields:
        payload["article"]["metafields"] = metafields

    data = rest_post(shop, token, f"blogs/{blog_id}/articles.json", payload)
    return (data or {}).get("article") or {}


def update_article(
    shop: str, token: str, blog_id: int, article_id: int, *,
    fields: dict[str, Any],
) -> dict:
    payload = {"article": {"id": article_id, **fields}}
    data = rest_put(shop, token, f"blogs/{blog_id}/articles/{article_id}.json", payload)
    return (data or {}).get("article") or {}


def article_gid(article_id: int) -> str:
    return f"gid://shopify/Article/{article_id}"


def article_admin_url(shop: str, blog_id: int, article_id: int) -> str:
    # shop = giclee-art-3.myshopify.com
    subdomain = shop.split(".", 1)[0]
    return f"https://admin.shopify.com/store/{subdomain}/articles/{article_id}"


def article_storefront_url(shop: str, primary_domain: str, blog_handle: str, article_handle: str) -> str:
    """Zbuduj URL artykulu na froncie. `primary_domain` bez schematu (np. "gicleeart.eu")."""
    if not primary_domain:
        primary_domain = shop
    return f"https://{primary_domain}/blogs/{blog_handle}/{article_handle}"


def register_article_translations(
    shop: str, token: str, *,
    article_id: int,
    locale: str,
    title: str = "",
    body_html: str = "",
    summary_html: str = "",
    seo_title: str = "",
    seo_description: str = "",
) -> list[dict]:
    """Zarejestruj tlumaczenie artykulu w podanym locale (en/de/fr/es/nl/it).

    Keys obslugiwane przez Shopify translations dla Article:
    `title`, `body_html`, `summary_html`, `meta_title`, `meta_description`.
    (Shopify API ewoluuje - jeli ktorys klucz nie jest translatable, zostanie pominety,
     bez rzucania bledu - `register_translations` weryfikuje to po `translatableResource`.)
    """
    fields: dict[str, str] = {}
    if title:
        fields["title"] = title
    if body_html:
        fields["body_html"] = body_html
    if summary_html:
        fields["summary_html"] = summary_html
    if seo_title:
        fields["meta_title"] = seo_title
    if seo_description:
        fields["meta_description"] = seo_description
    if not fields:
        return []
    return register_translations(
        shop, token,
        resource_gid=article_gid(article_id),
        locale=locale,
        fields=fields,
    )


def get_shop_primary_domain(shop: str, token: str) -> str:
    """Zwraca glowna domene (np. 'gicleeart.eu') - do budowy URL-i storefront."""
    try:
        data = graphql(shop, token, "{ shop { primaryDomain { host } } }")
        return ((data or {}).get("shop") or {}).get("primaryDomain", {}).get("host") or ""
    except ShopifyError:
        return ""
