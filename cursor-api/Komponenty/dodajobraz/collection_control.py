"""Kontrola przypisania produktow (Obraz) do kolekcji artysty w Shopify."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any, Callable

from . import shopify_client as sc
from .create import PRODUCT_TYPE, VENDOR, _split_artist_title
from .parser import artist_collection_title

Logger = Callable[[str], None]


def is_probable_artist_collection(title: str) -> bool:
    """Heurystyka: «Monet, Claude» — kolekcja artysty (nie tagowa smart-collection)."""
    t = (title or "").strip()
    if ", " not in t:
        return False
    left, right = t.split(", ", 1)
    return bool(left.strip() and right.strip() and left[0].isupper())


def _admin_product_url(shop: str, product_id: int) -> str:
    host = shop.replace(".myshopify.com", "")
    return f"https://{host}.myshopify.com/admin/products/{product_id}"


def _catalog_entry_for_title(catalog: dict[int, dict[str, Any]], title: str) -> dict[str, Any] | None:
    target = title.strip().lower()
    if not target:
        return None
    for meta in catalog.values():
        if (meta.get("title") or "").strip().lower() == target:
            return meta
    return None


def _collection_name_tokens(title: str) -> frozenset[str]:
    """Tokeny imienia/nazwiska — bez kolejnosci, myslnikow i diakrytykow (porownanie kolekcji)."""
    t = unicodedata.normalize("NFKD", (title or "").strip())
    t = t.encode("ascii", "ignore").decode("ascii").lower()
    t = t.replace("-", " ").replace(",", " ")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    parts = [p for p in t.split() if p]
    return frozenset(parts)


def collection_title_matches_expected(actual: str, expected: str) -> bool:
    """«Canal, Antonio (Canaletto)» pasuje do «Canal, Antonio»; «Van Gogh, Vincent» do «Gogh, Vincent van»."""
    a = (actual or "").strip()
    e = (expected or "").strip()
    if not e or not a:
        return False
    al = a.lower()
    el = e.lower()
    if al == el:
        return True
    if al.startswith(el + " ") or al.startswith(el + "("):
        return True
    at = _collection_name_tokens(a)
    et = _collection_name_tokens(e)
    if len(at) >= 2 and len(et) >= 2 and at == et:
        return True
    return False


def resolve_artist_collection_in_catalog(
    catalog: dict[int, dict[str, Any]],
    expected: str,
) -> dict[str, Any] | None:
    """Kolekcja artysty w sklepie — dokladna nazwa lub wariant z nawiasem (Canaletto)."""
    exact = _catalog_entry_for_title(catalog, expected)
    if exact:
        return exact
    exp = (expected or "").strip().lower()
    if not exp:
        return None
    fuzzy: list[dict[str, Any]] = []
    for meta in catalog.values():
        title = (meta.get("title") or "").strip()
        if not title or not is_probable_artist_collection(title):
            continue
        if collection_title_matches_expected(title, expected):
            fuzzy.append(meta)
    if not fuzzy:
        return None
    if len(fuzzy) == 1:
        return fuzzy[0]
    fuzzy.sort(key=lambda m: (len(m.get("title") or ""), (m.get("title") or "").lower()))
    return fuzzy[0]


def matched_artist_collection_in_titles(
    expected: str,
    titles: set[str] | list[str],
) -> str | None:
    for t in titles:
        if collection_title_matches_expected(t, expected):
            return t.strip()
    return None


def evaluate_collection_row_status(
    *,
    artist: str,
    titles: set[str] | list[str],
    catalog: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Status wiersza kontroli kolekcji (wspolna logika ladowania i odswiezania)."""
    title_set = set(titles) if not isinstance(titles, set) else titles
    if not (artist or "").strip():
        return {
            "status": "BRAK ARTYSTY",
            "expected_collection": "",
            "expected_collection_id": None,
            "expected_kind": None,
            "shop_collection": "",
            "in_expected": False,
        }

    expected = artist_collection_title(artist)
    shop_meta = resolve_artist_collection_in_catalog(catalog, expected)
    shop_title = (shop_meta.get("title") or "").strip() if shop_meta else ""
    matched = matched_artist_collection_in_titles(expected, title_set)

    if matched:
        return {
            "status": "OK",
            "expected_collection": expected,
            "expected_collection_id": shop_meta.get("id") if shop_meta else None,
            "expected_kind": shop_meta.get("kind") if shop_meta else None,
            "shop_collection": shop_title or matched,
            "in_expected": True,
        }
    if shop_meta:
        return {
            "status": "BRAK W KOLEKCJI",
            "expected_collection": expected,
            "expected_collection_id": shop_meta.get("id"),
            "expected_kind": shop_meta.get("kind"),
            "shop_collection": shop_title,
            "in_expected": False,
        }
    return {
        "status": "BRAK KOLEKCJI",
        "expected_collection": expected,
        "expected_collection_id": None,
        "expected_kind": None,
        "shop_collection": "",
        "in_expected": False,
    }


def refresh_product_collection_titles(
    shop: str,
    token: str,
    product_id: int,
    *,
    artist: str,
    catalog: dict[int, dict[str, Any]],
) -> set[str]:
    """Aktualne kolekcje produktu (custom collects + sprawdzenie kolekcji artysty smart/custom)."""
    titles: set[str] = set()
    for c in sc.list_product_collects(shop, token, int(product_id)):
        meta = catalog.get(int(c.get("collection_id") or 0))
        if meta and meta.get("title"):
            titles.add(meta["title"])

    expected = artist_collection_title(artist) if artist.strip() else ""
    if expected:
        shop_meta = resolve_artist_collection_in_catalog(catalog, expected)
        if shop_meta:
            cid = int(shop_meta["id"])
            if sc.is_product_in_collection(
                shop,
                token,
                int(product_id),
                cid,
                collection_kind=shop_meta.get("kind"),
            ):
                titles.add(shop_meta["title"])
    return titles


def build_product_collection_membership(
    shop: str,
    token: str,
    catalog: dict[int, dict[str, Any]],
    collects: list[dict],
    *,
    logger: Logger | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[int, set[str]]:
    """product_id -> zestaw tytulow kolekcji (custom + smart artystow)."""
    by_product: dict[int, set[str]] = defaultdict(set)

    for row in collects:
        pid = int(row.get("product_id") or 0)
        cid = int(row.get("collection_id") or 0)
        meta = catalog.get(cid)
        if pid and meta and meta.get("title"):
            by_product[pid].add(meta["title"])

    smart_artist = [
        meta
        for meta in catalog.values()
        if meta.get("kind") == "smart" and is_probable_artist_collection(meta.get("title") or "")
    ]
    total = len(smart_artist)
    for i, meta in enumerate(smart_artist, start=1):
        cid = int(meta["id"])
        title = meta["title"]
        if on_progress:
            on_progress(f"Smart kolekcje artystow: {i}/{total} — {title[:40]}")
        if logger:
            logger(f"[kolekcje] Skanuje smart: {title}")
        try:
            for prod in sc.iter_collection_products(shop, token, cid, fields="id"):
                pid = int(prod.get("id") or 0)
                if pid:
                    by_product[pid].add(title)
        except sc.ShopifyError as e:
            if logger:
                logger(f"[kolekcje] BLAD smart '{title}': {e}")

    return by_product


def load_collection_control_rows(
    *,
    logger: Logger | None = None,
    on_progress: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Zwraca (wiersze_produktow, lista_kolekcji_do_combobox).

    Kazdy wiersz: product_id, product_title, artist, painting_title, handle,
    expected_collection, in_expected (bool), collections (str), status, admin_url,
    expected_collection_id, expected_kind.
    """
    shop, token = sc.load_session()
    if on_progress:
        on_progress("Pobieram katalog kolekcji...")
    if logger:
        logger("[kolekcje] Pobieram katalog kolekcji...")
    catalog = sc.fetch_collection_catalog(shop, token)
    collection_choices = sorted(
        [
            {"id": m["id"], "title": m["title"], "kind": m["kind"]}
            for m in catalog.values()
            if (m.get("title") or "").strip()
        ],
        key=lambda x: x["title"].lower(),
    )

    if should_cancel and should_cancel():
        raise sc.OperationCancelled("Przerwano.")

    if on_progress:
        on_progress("Pobieram powiazania collects...")
    collects = sc.fetch_all_collects(shop, token)

    if should_cancel and should_cancel():
        raise sc.OperationCancelled("Przerwano.")

    membership = build_product_collection_membership(
        shop,
        token,
        catalog,
        collects,
        logger=logger,
        on_progress=on_progress,
    )

    if on_progress:
        on_progress("Pobieram produkty (Obraz)...")
    if logger:
        logger(f"[kolekcje] Pobieram produkty typ={PRODUCT_TYPE!r}...")
    products = sc.fetch_all_products(
        shop,
        token,
        product_type=PRODUCT_TYPE,
        fields="id,title,handle,vendor,product_type",
        should_cancel=should_cancel,
        on_page_progress=lambda n: on_progress(f"Produkty: {n}") if on_progress else None,
    )

    rows: list[dict[str, Any]] = []
    for prod in products:
        pid = int(prod.get("id") or 0)
        if not pid:
            continue
        title_full = (prod.get("title") or "").strip()
        artist, painting_title = _split_artist_title(title_full, prod.get("vendor"))
        titles = sorted(membership.get(pid) or set(), key=str.lower)
        collections_str = "; ".join(titles) if titles else "—"

        ev = evaluate_collection_row_status(
            artist=artist,
            titles=titles,
            catalog=catalog,
        )

        rows.append(
            {
                "product_id": pid,
                "product_title": title_full,
                "artist": artist,
                "painting_title": painting_title,
                "handle": (prod.get("handle") or "").strip(),
                "expected_collection": ev["expected_collection"],
                "expected_collection_id": ev["expected_collection_id"],
                "expected_kind": ev["expected_kind"],
                "shop_collection": ev.get("shop_collection") or "",
                "in_expected": ev["in_expected"],
                "collection_titles": titles,
                "collections": collections_str,
                "status": ev["status"],
                "admin_url": _admin_product_url(shop, pid),
            }
        )

    rows.sort(
        key=lambda r: (
            0 if r["status"] == "OK" else 1,
            (r.get("artist") or "\uffff").lower(),
            (r.get("painting_title") or "").lower(),
        )
    )
    if logger:
        problems = sum(1 for r in rows if r["status"] != "OK")
        logger(f"[kolekcje] Gotowe: {len(rows)} produktow, problemow: {problems}.")
    return rows, collection_choices


def remove_product_from_custom_collection(
    *,
    product_id: int,
    collection_title: str,
    logger: Logger | None = None,
) -> None:
    """Usuwa produkt z custom collection (przez DELETE collect)."""
    shop, token = sc.load_session()
    coll = sc.find_artist_collection(shop, token, collection_title.strip())
    if not coll:
        raise sc.ShopifyError(f"Nie znaleziono kolekcji: {collection_title!r}")
    if (coll.get("kind") or "").lower() != "custom":
        raise sc.ShopifyError(
            f"Kolekcja «{collection_title}» jest smart — usuniecie reczne nie jest mozliwe."
        )
    cid = int(coll["id"])
    for row in sc.list_product_collects(shop, token, int(product_id)):
        if int(row.get("collection_id") or 0) == cid:
            collect_id = int(row.get("id") or 0)
            if collect_id:
                sc.delete_collect(shop, token, collect_id)
                if logger:
                    logger(f"[kolekcje] Usunieto produkt {product_id} z «{collection_title}».")
                return
    raise sc.ShopifyError(f"Produkt nie jest w kolekcji «{collection_title}».")
