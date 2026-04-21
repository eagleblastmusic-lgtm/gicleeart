"""Sygnaly marketingowe z Shopify.

Co sciagamy (zeby LLM mial kontekst do planowania zadan):
- Nowe produkty dodane w ostatnich N dniach (domyslnie 14).
- Nowi autorzy, ktorzy pojawili sie w ostatnich N dniach.
  'Autor' pobierany z pierwszej czesci tytulu produktu (wzorzec 'Autor - Tytul').
- Nowe smart-kolekcje (tagowe) stworzone w ostatnich N dniach.
- Produkty bez obrazka albo bez publikacji (warte pilnej uwagi).

Wszystkie funkcje zwracaja czyste struktury Pythonowe + zapisuja snapshot do
`signals_cache.json` (zeby ekran sygnalow nie musial zawsze czekac na API).

Uzywamy klienta `Komponenty.dodajobraz.shopify_client` (ten sam co reszta apki).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from Komponenty.dodajobraz.shopify_client import (
    ShopifyError,
    iter_all_products,
    load_session,
    rest_get,
)


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Shopify zwraca '2026-04-18T12:34:56-04:00' albo '...Z'
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _extract_artist(title: str) -> str:
    """Z 'Hans Dahl - Babie lato' wyciaga 'Hans Dahl'."""
    if not title:
        return ""
    for sep in (" - ", " – ", " — "):
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def fetch_new_products(*, days: int = 14, limit: int = 500) -> list[dict[str, Any]]:
    """Produkty o `created_at` nowszym niz `days` dni.

    Pobiera wszystkie produkty (paginowane) i filtruje lokalnie. Shopify ma tez
    parametr `created_at_min`, ale iter_all_products nie wspiera go out-of-the-box -
    filter lokalny jest wystarczajaco szybki dla typowego sklepu <10k produktow.
    """
    shop, token = load_session()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    out: list[dict[str, Any]] = []
    count = 0
    for product in iter_all_products(shop, token):
        count += 1
        if count > limit:
            break
        created = _parse_ts(str(product.get("created_at") or ""))
        if created is None:
            continue
        if created < cutoff:
            # Shopify najczesciej zwraca produkty od najnowszego, ale nie gwarantuje -
            # wiec kontynuujemy, zeby nie przegapic nic ponizej.
            continue
        out.append({
            "id": product.get("id"),
            "title": str(product.get("title") or ""),
            "artist": _extract_artist(str(product.get("title") or "")),
            "handle": str(product.get("handle") or ""),
            "created_at": str(product.get("created_at") or ""),
            "status": str(product.get("status") or ""),
            "image_src": (product.get("image") or {}).get("src") or "",
            "tags": [t.strip() for t in str(product.get("tags") or "").split(",") if t.strip()],
        })
    out.sort(key=lambda p: str(p.get("created_at") or ""), reverse=True)
    return out


def fetch_new_collections(*, days: int = 30) -> list[dict[str, Any]]:
    """Kolekcje utworzone w ostatnich `days` dniach (smart + custom).

    Laczy dwa endpointy REST: /smart_collections.json i /custom_collections.json.
    """
    shop, token = load_session()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict[str, Any]] = []

    for endpoint in ("smart_collections.json", "custom_collections.json"):
        try:
            data = rest_get(shop, token, endpoint, limit=250)
        except ShopifyError:
            continue
        items = (data or {}).get(endpoint.split(".")[0], []) or []
        for c in items:
            created = _parse_ts(str(c.get("published_at") or c.get("updated_at") or ""))
            if created is None:
                continue
            if created < cutoff:
                continue
            out.append({
                "id": c.get("id"),
                "title": str(c.get("title") or ""),
                "handle": str(c.get("handle") or ""),
                "created_at": str(c.get("published_at") or c.get("updated_at") or ""),
                "kind": "smart" if endpoint.startswith("smart") else "custom",
                "body_html": str(c.get("body_html") or "")[:200],
            })
    out.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return out


def aggregate_signals(*, days: int = 14) -> dict[str, Any]:
    """Pobiera wszystkie sygnaly w jednym wywolaniu i zwraca slownik gotowy do LLM / cache.

    Struktura:
    {
      "period_days": 14,
      "fetched_at": "2026-04-20T12:00:00",
      "new_products": [...],           // z fetch_new_products
      "new_collections": [...],        // z fetch_new_collections (30d default)
      "new_artists": [{"name", "products_count", "first_seen"}],
      "products_without_image": [...],
      "unpublished_products": [...],
    }
    """
    fetched_at = datetime.now().isoformat(timespec="seconds")

    new_products = fetch_new_products(days=days)
    new_collections = fetch_new_collections(days=max(days, 30))

    # Nowi autorzy - group by extracted artist
    artist_groups: dict[str, list[dict[str, Any]]] = {}
    for p in new_products:
        a = p.get("artist") or ""
        if not a:
            continue
        artist_groups.setdefault(a, []).append(p)
    new_artists = [
        {
            "name": a,
            "products_count": len(items),
            "first_seen": min(str(x.get("created_at") or "") for x in items),
            "sample_titles": [x["title"] for x in items[:3]],
        }
        for a, items in sorted(artist_groups.items(), key=lambda kv: len(kv[1]), reverse=True)
    ]

    products_without_image = [
        {"id": p["id"], "title": p["title"]}
        for p in new_products if not p.get("image_src")
    ]
    unpublished_products = [
        {"id": p["id"], "title": p["title"], "status": p["status"]}
        for p in new_products if p.get("status") != "active"
    ]

    return {
        "period_days": days,
        "fetched_at": fetched_at,
        "new_products": new_products,
        "new_collections": new_collections,
        "new_artists": new_artists,
        "products_without_image": products_without_image,
        "unpublished_products": unpublished_products,
    }


def format_signals_for_prompt(signals: dict[str, Any]) -> str:
    """Krotki tekst sygnalow do wklejenia w prompt LLM."""
    if not signals:
        return "(brak sygnalow - nie pobrano danych z Shopify)"
    parts: list[str] = []
    parts.append(f"Okres analizy: ostatnie {signals.get('period_days', 14)} dni")

    new_products = signals.get("new_products") or []
    if new_products:
        parts.append(f"\nNOWE PRODUKTY ({len(new_products)}):")
        for p in new_products[:15]:
            parts.append(f"- {p.get('title', '')} (tagi: {', '.join(p.get('tags') or [])[:60]})")
        if len(new_products) > 15:
            parts.append(f"- ... i {len(new_products) - 15} wiecej")
    else:
        parts.append("\nNOWE PRODUKTY: brak")

    new_artists = signals.get("new_artists") or []
    if new_artists:
        parts.append(f"\nNOWI AUTORZY ({len(new_artists)}):")
        for a in new_artists[:10]:
            parts.append(
                f"- {a.get('name', '')} ({a.get('products_count', 0)} produktow; "
                f"np. {' | '.join(a.get('sample_titles') or [])[:140]})"
            )
        if len(new_artists) > 10:
            parts.append(f"- ... i {len(new_artists) - 10} wiecej")
    else:
        parts.append("\nNOWI AUTORZY: brak")

    new_collections = signals.get("new_collections") or []
    if new_collections:
        parts.append(f"\nNOWE KOLEKCJE ({len(new_collections)}):")
        for c in new_collections[:10]:
            parts.append(f"- {c.get('title', '')} ({c.get('kind', 'smart')})")

    products_wo_img = signals.get("products_without_image") or []
    if products_wo_img:
        parts.append(f"\nPRODUKTY BEZ OBRAZKA (do pilnej uwagi): {len(products_wo_img)}")

    return "\n".join(parts)
