"""Shopify: metafield grafiki «przed» + wykrywanie obrazu Full («po»)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import PRODUCT_TYPE
from Komponenty.dodajobraz.description_update import load_product_catalog_rows
from Komponenty.infoplikow.product_files import classify_image_role, filename_from_url
from Komponenty.dodajobraz.parser import IMAGE_ROLE_FULL

METAFIELD_NAMESPACE = "custom"
METAFIELD_KEY_BEFORE_URL = "before_retouch_url"

Logger = Callable[[str], None]
_DEFINITION_ENSURED = False


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def ensure_before_retouch_metafield_definition(*, logger: Logger | None = None) -> None:
    """Definicja metafield z dostępem storefront (Liquid na PDP)."""
    global _DEFINITION_ENSURED  # noqa: PLW0603
    if _DEFINITION_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: PRODUCT, namespace: "custom", key: "before_retouch_url") {
        nodes { id access { storefront } }
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
            "name": "Grafika przed obróbką (porównanie PDP)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_BEFORE_URL,
            "type": "url",
            "ownerType": "PRODUCT",
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
    _log(logger, "[przed/po] Definicja metafield custom.before_retouch_url (storefront PUBLIC_READ).")


def fetch_before_url_map(
    shop: str,
    token: str,
    *,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[int, str]:
    """Mapa product_id -> URL grafiki «przed» (metafield custom.before_retouch_url)."""
    query = """
    query BeforeRetouchPage($first: Int!, $after: String, $q: String!) {
      products(first: $first, after: $after, query: $q) {
        pageInfo { hasNextPage endCursor }
        nodes {
          legacyResourceId
          metafield(namespace: "custom", key: "before_retouch_url") { value }
        }
      }
    }
    """
    q = f'product_type:"{PRODUCT_TYPE}"'
    out: dict[int, str] = {}
    cursor: str | None = None
    page = 0
    while True:
        if should_cancel and should_cancel():
            break
        page += 1
        if on_progress:
            on_progress(f"Metafield «przed»: strona {page}...")
        data = sc.graphql(
            shop,
            token,
            query,
            {"first": 250, "after": cursor, "q": q},
        )
        conn = (data or {}).get("products") or {}
        for node in conn.get("nodes") or []:
            try:
                pid = int(node.get("legacyResourceId") or 0)
            except (TypeError, ValueError):
                continue
            if not pid:
                continue
            mf = node.get("metafield") or {}
            url = str(mf.get("value") or "").strip()
            if url:
                out[pid] = url
        pi = conn.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        cursor = pi.get("endCursor")
        if not cursor:
            break
    _log(logger, f"[przed/po] Metafield «przed»: {len(out)} produkt(ów).")
    return out


def load_catalog_with_before_status(
    *,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Lista produktów + flaga czy jest grafika «przed»."""
    shop, token = sc.load_session()
    rows = load_product_catalog_rows(
        logger=logger,
        should_cancel=should_cancel,
        on_progress=on_progress,
    )
    if should_cancel and should_cancel():
        return rows
    before_map = fetch_before_url_map(
        shop,
        token,
        logger=logger,
        should_cancel=should_cancel,
        on_progress=on_progress,
    )
    for row in rows:
        pid = int(row.get("product_id") or 0)
        url = before_map.get(pid, "")
        row["before_url"] = url
        row["has_before"] = bool(url)
        row["before_status"] = "tak" if url else "—"
    return rows


def find_full_image(shop: str, token: str, product_id: int) -> dict[str, Any] | None:
    """Pierwszy obraz galerii z rolą Full (grafika «po obróbce»)."""
    for im in sc.list_product_images(shop, token, int(product_id)):
        src = str(im.get("src") or "").strip()
        alt = str(im.get("alt") or "").strip()
        if classify_image_role(alt=alt, src=src) == IMAGE_ROLE_FULL:
            return {
                "image_id": int(im.get("id") or 0),
                "src": src,
                "alt": alt,
                "filename": filename_from_url(src),
                "width": im.get("width"),
                "height": im.get("height"),
            }
    return None


def load_product_before_after(
    product_id: int,
    *,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Szczegóły produktu: URL «przed», obraz Full «po»."""
    shop, token = sc.load_session()
    pid = int(product_id)
    prod = sc.get_product(shop, token, pid)
    if not prod:
        return {"ok": False, "error": f"Nie znaleziono produktu {pid}."}

    mf = sc.find_metafield(
        shop, token, pid, namespace=METAFIELD_NAMESPACE, key=METAFIELD_KEY_BEFORE_URL
    )
    before_url = str((mf or {}).get("value") or "").strip()
    full = find_full_image(shop, token, pid)

    title = str(prod.get("title") or "").strip()
    handle = str(prod.get("handle") or "").strip()
    store = shop.replace(".myshopify.com", "")
    return {
        "ok": True,
        "product_id": pid,
        "title": title,
        "handle": handle,
        "before_url": before_url,
        "has_before": bool(before_url),
        "after": full,
        "has_after": full is not None,
        "admin_url": f"https://{store}.myshopify.com/admin/products/{pid}",
        "storefront_url": f"https://gicleeart.eu/pl-pl/products/{handle}" if handle else "",
    }


def upload_before_image(
    product_id: int,
    image_path: Path,
    *,
    alt: str | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Wgrywa plik do Shopify Files i zapisuje URL w metafield produktu."""
    shop, token = sc.load_session()
    pid = int(product_id)
    path = Path(image_path)
    if not path.is_file():
        return {"ok": False, "error": f"Plik nie istnieje: {path}"}

    _log(logger, f"[przed/po] Upload: {path.name} -> produkt {pid}")
    ensure_before_retouch_metafield_definition(logger=logger)
    url = sc.upload_file_to_shopify_files(path, alt=alt or path.stem)
    sc.upsert_metafield(
        shop,
        token,
        pid,
        namespace=METAFIELD_NAMESPACE,
        key=METAFIELD_KEY_BEFORE_URL,
        value=url,
        ftype="url",
    )
    _log(logger, f"[przed/po] Zapisano metafield {METAFIELD_NAMESPACE}.{METAFIELD_KEY_BEFORE_URL}")
    return {"ok": True, "before_url": url, "product_id": pid}


def clear_before_image(product_id: int, *, logger: Logger | None = None) -> dict[str, Any]:
    """Usuwa metafield grafiki «przed»."""
    shop, token = sc.load_session()
    pid = int(product_id)
    existing = sc.find_metafield(
        shop, token, pid, namespace=METAFIELD_NAMESPACE, key=METAFIELD_KEY_BEFORE_URL
    )
    if not existing:
        return {"ok": True, "removed": False}
    mid = int(existing.get("id") or 0)
    if mid:
        sc.rest_delete(shop, token, f"metafields/{mid}.json")
        _log(logger, f"[przed/po] Usunięto metafield produktu {pid}.")
    return {"ok": True, "removed": True}
