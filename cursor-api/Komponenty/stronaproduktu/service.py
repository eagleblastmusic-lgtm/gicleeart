"""Shopify: metafield custom.story_pages (stronicowany opis PDP v3) + upload grafik stron."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from Komponenty._shared.storefront_urls import product_storefront_url
from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import PRODUCT_TYPE
from Komponenty.dodajobraz.description_update import load_product_catalog_rows
from Komponenty.dodajobraz.html_template import extract_paragraphs_from_body_html

METAFIELD_NAMESPACE = "custom"
METAFIELD_KEY_STORY = "story_pages"
METAFIELD_KEY_EFFECTS = "pdp_v3_effects"

#: Domyslne ustawienia efektow PDP v3 (motyw traktuje brak pola jako wlaczone;
#: tlo konfiguratora bez own image = zdjecie glowne produktu).
DEFAULT_EFFECTS: dict[str, Any] = {
    "zoom_immersive": True,
    "r2_blur": True,
    "config_bg": {"enabled": True, "image": "", "parallax": True, "blur": True, "brightness": 100},
    "pt_bg": {"enabled": True, "image": "", "blur": False, "brightness": 100},
}

Logger = Callable[[str], None]
_DEFINITION_ENSURED = False
_EFFECTS_DEFINITION_ENSURED = False


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def ensure_story_metafield_definition(*, logger: Logger | None = None) -> None:
    """Definicja metafield JSON z dostępem storefront (Liquid na PDP v3)."""
    global _DEFINITION_ENSURED  # noqa: PLW0603
    if _DEFINITION_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: PRODUCT, namespace: "custom", key: "story_pages") {
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
            "name": "Strony opisu produktu (PDP v3)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_STORY,
            "type": "json",
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
    _log(logger, "[strona produktu] Definicja metafield custom.story_pages (storefront PUBLIC_READ).")


def normalize_story_config(raw: Any) -> dict[str, Any]:
    """Waliduje/porządkuje konfigurację: pages[{paragraphs,image}], details_image."""
    data = raw if isinstance(raw, dict) else {}
    pages_in = data.get("pages")
    pages: list[dict[str, Any]] = []
    if isinstance(pages_in, list):
        for entry in pages_in:
            if not isinstance(entry, dict):
                continue
            try:
                count = max(1, int(entry.get("paragraphs") or 1))
            except (TypeError, ValueError):
                count = 1
            image = str(entry.get("image") or "").strip()
            pages.append({"paragraphs": count, "image": image})
    out: dict[str, Any] = {"pages": pages}
    details_image = str(data.get("details_image") or "").strip()
    if details_image:
        out["details_image"] = details_image
    return out


def fetch_story_map(
    shop: str,
    token: str,
    *,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[int, dict[str, Any]]:
    """Mapa product_id -> konfiguracja stron (metafield custom.story_pages)."""
    query = """
    query StoryPagesPage($first: Int!, $after: String, $q: String!) {
      products(first: $first, after: $after, query: $q) {
        pageInfo { hasNextPage endCursor }
        nodes {
          legacyResourceId
          metafield(namespace: "custom", key: "story_pages") { value }
        }
      }
    }
    """
    q = f'product_type:"{PRODUCT_TYPE}"'
    out: dict[int, dict[str, Any]] = {}
    cursor: str | None = None
    page = 0
    while True:
        if should_cancel and should_cancel():
            break
        page += 1
        if on_progress:
            on_progress(f"Metafield stron: strona {page}...")
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
            raw = str(mf.get("value") or "").strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except (TypeError, ValueError):
                continue
            cfg = normalize_story_config(parsed)
            if cfg["pages"]:
                out[pid] = cfg
        pi = conn.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        cursor = pi.get("endCursor")
        if not cursor:
            break
    _log(logger, f"[strona produktu] Konfiguracja stron: {len(out)} produkt(ów).")
    return out


def load_catalog_with_story_status(
    *,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Lista produktów + flaga czy jest konfiguracja stron."""
    shop, token = sc.load_session()
    rows = load_product_catalog_rows(
        logger=logger,
        should_cancel=should_cancel,
        on_progress=on_progress,
    )
    if should_cancel and should_cancel():
        return rows
    story_map = fetch_story_map(
        shop,
        token,
        logger=logger,
        should_cancel=should_cancel,
        on_progress=on_progress,
    )
    for row in rows:
        pid = int(row.get("product_id") or 0)
        cfg = story_map.get(pid)
        row["story_config"] = cfg
        row["has_story"] = cfg is not None
        row["story_status"] = f"{len(cfg['pages'])} str." if cfg else "—"
    return rows


def load_product_story(
    product_id: int,
    *,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Szczegóły produktu: akapity opisu (PL) + istniejąca konfiguracja stron."""
    shop, token = sc.load_session()
    pid = int(product_id)
    prod = sc.get_product(shop, token, pid)
    if not prod:
        return {"ok": False, "error": f"Nie znaleziono produktu {pid}."}

    paragraphs = extract_paragraphs_from_body_html(str(prod.get("body_html") or ""))

    mf = sc.find_metafield(
        shop, token, pid, namespace=METAFIELD_NAMESPACE, key=METAFIELD_KEY_STORY
    )
    config: dict[str, Any] | None = None
    raw = str((mf or {}).get("value") or "").strip()
    if raw:
        try:
            config = normalize_story_config(json.loads(raw))
        except (TypeError, ValueError):
            config = None

    title = str(prod.get("title") or "").strip()
    handle = str(prod.get("handle") or "").strip()
    store = shop.replace(".myshopify.com", "")
    return {
        "ok": True,
        "product_id": pid,
        "title": title,
        "handle": handle,
        "paragraphs": paragraphs,
        "config": config,
        "has_story": config is not None,
        "admin_url": f"https://{store}.myshopify.com/admin/products/{pid}",
        "storefront_url": product_storefront_url(handle),
    }


def upload_story_image(
    image_path: Path,
    *,
    alt: str | None = None,
    logger: Logger | None = None,
) -> str:
    """Wgrywa grafikę strony do Shopify Files, zwraca URL CDN."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Plik nie istnieje: {path}")
    _log(logger, f"[strona produktu] Upload grafiki: {path.name}")
    return sc.upload_file_to_shopify_files(path, alt=alt or path.stem)


def save_story_config(
    product_id: int,
    config: dict[str, Any],
    *,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Zapisuje konfigurację stron w metafield produktu (JSON)."""
    shop, token = sc.load_session()
    pid = int(product_id)
    cfg = normalize_story_config(config)
    if not cfg["pages"]:
        return {"ok": False, "error": "Konfiguracja nie zawiera żadnej strony."}
    ensure_story_metafield_definition(logger=logger)
    sc.upsert_metafield(
        shop,
        token,
        pid,
        namespace=METAFIELD_NAMESPACE,
        key=METAFIELD_KEY_STORY,
        value=json.dumps(cfg, ensure_ascii=False),
        ftype="json",
    )
    _log(logger, f"[strona produktu] Zapisano metafield {METAFIELD_NAMESPACE}.{METAFIELD_KEY_STORY}")
    return {"ok": True, "product_id": pid, "config": cfg}


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _coerce_brightness(value: Any) -> int:
    try:
        return max(30, min(170, int(value)))
    except (TypeError, ValueError):
        return 100


def normalize_effects_config(raw: Any) -> dict[str, Any]:
    """Waliduje ustawienia efektow PDP v3 (metafield shop custom.pdp_v3_effects)."""
    data = raw if isinstance(raw, dict) else {}
    out: dict[str, Any] = {
        "zoom_immersive": _coerce_bool(data.get("zoom_immersive"), True),
        "r2_blur": _coerce_bool(data.get("r2_blur"), True),
    }
    for key in ("config_bg", "pt_bg"):
        defaults = DEFAULT_EFFECTS[key]
        section = data.get(key) if isinstance(data.get(key), dict) else {}
        block = {
            "enabled": _coerce_bool(section.get("enabled"), bool(defaults["enabled"])),
            "image": str(section.get("image") or "").strip(),
            "blur": _coerce_bool(section.get("blur"), bool(defaults["blur"])),
            "brightness": _coerce_brightness(section.get("brightness")),
        }
        if key == "config_bg":
            block["parallax"] = _coerce_bool(section.get("parallax"), True)
        out[key] = block
    return out


def _shop_gid(shop: str, token: str) -> str:
    data = sc.graphql(shop, token, "query { shop { id } }", {})
    gid = str(((data or {}).get("shop") or {}).get("id") or "")
    if not gid:
        raise sc.ShopifyError("Nie udalo sie pobrac ID sklepu (shop.id).")
    return gid


def ensure_effects_metafield_definition(*, logger: Logger | None = None) -> None:
    """Definicja metafield JSON na sklepie (Liquid czyta shop.metafields...)."""
    global _EFFECTS_DEFINITION_ENSURED  # noqa: PLW0603
    if _EFFECTS_DEFINITION_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: SHOP, namespace: "custom", key: "pdp_v3_effects") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _EFFECTS_DEFINITION_ENSURED = True
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
            "name": "Efekty PDP v3 (strona produktu)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_EFFECTS,
            "type": "json",
            "ownerType": "SHOP",
        }
    }
    res = sc.graphql(shop, token, create, payload)
    block = (res or {}).get("metafieldDefinitionCreate") or {}
    errors = block.get("userErrors") or []
    if errors:
        codes = {str(e.get("code") or "") for e in errors}
        if not codes.intersection({"TAKEN", "ALREADY_EXISTS"}):
            raise sc.ShopifyError(f"metafieldDefinitionCreate (effects): {errors}")
    _EFFECTS_DEFINITION_ENSURED = True
    _log(logger, "[strona produktu] Definicja metafield shop custom.pdp_v3_effects.")


def load_effects_config(*, logger: Logger | None = None) -> dict[str, Any]:
    """Aktualne ustawienia efektow PDP v3 (z defaultami dla brakujacych pol)."""
    shop, token = sc.load_session()
    query = """
    query {
      shop { metafield(namespace: "custom", key: "pdp_v3_effects") { value } }
    }
    """
    data = sc.graphql(shop, token, query, {})
    raw = str((((data or {}).get("shop") or {}).get("metafield") or {}).get("value") or "").strip()
    parsed: Any = None
    if raw:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            parsed = None
    cfg = normalize_effects_config(parsed)
    _log(logger, "[strona produktu] Wczytano ustawienia efektow PDP v3.")
    return cfg


def save_effects_config(config: dict[str, Any], *, logger: Logger | None = None) -> dict[str, Any]:
    """Zapisuje ustawienia efektow PDP v3 w metafieldzie sklepu (JSON)."""
    shop, token = sc.load_session()
    cfg = normalize_effects_config(config)
    ensure_effects_metafield_definition(logger=logger)
    mutation = """
    mutation Set($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { id }
        userErrors { field message code }
      }
    }
    """
    payload = {
        "metafields": [
            {
                "ownerId": _shop_gid(shop, token),
                "namespace": METAFIELD_NAMESPACE,
                "key": METAFIELD_KEY_EFFECTS,
                "type": "json",
                "value": json.dumps(cfg, ensure_ascii=False),
            }
        ]
    }
    res = sc.graphql(shop, token, mutation, payload)
    errors = ((res or {}).get("metafieldsSet") or {}).get("userErrors") or []
    if errors:
        raise sc.ShopifyError(f"metafieldsSet (effects): {errors}")
    _log(
        logger,
        f"[strona produktu] Zapisano metafield shop {METAFIELD_NAMESPACE}.{METAFIELD_KEY_EFFECTS}",
    )
    return {"ok": True, "config": cfg}


def upload_effects_image(
    image_path: Path,
    *,
    alt: str | None = None,
    logger: Logger | None = None,
) -> str:
    """Wgrywa grafike tla (konfigurator / proces+trust) do Shopify Files."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Plik nie istnieje: {path}")
    _log(logger, f"[strona produktu] Upload tla efektow: {path.name}")
    return sc.upload_file_to_shopify_files(path, alt=alt or path.stem)


def clear_story_config(product_id: int, *, logger: Logger | None = None) -> dict[str, Any]:
    """Usuwa metafield konfiguracji stron (motyw wraca do auto-podziału)."""
    shop, token = sc.load_session()
    pid = int(product_id)
    existing = sc.find_metafield(
        shop, token, pid, namespace=METAFIELD_NAMESPACE, key=METAFIELD_KEY_STORY
    )
    if not existing:
        return {"ok": True, "removed": False}
    mid = int(existing.get("id") or 0)
    if mid:
        sc.rest_delete(shop, token, f"metafields/{mid}.json")
        _log(logger, f"[strona produktu] Usunięto metafield produktu {pid}.")
    return {"ok": True, "removed": True}
