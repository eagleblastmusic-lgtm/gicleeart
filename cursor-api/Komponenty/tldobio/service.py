"""Shopify: tło BIO per kolekcja (Files + metafield custom.bio_background_url)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any, Callable

from Komponenty.dodajobraz import shopify_client as sc
from giclee_app.app_paths import atomic_write_text, cache_path

METAFIELD_NAMESPACE = "custom"
METAFIELD_KEY = "bio_background_url"
METAFIELD_KEY_POS_X = "bio_background_pos_x"
METAFIELD_KEY_OVERLAY_PCT = "bio_background_overlay_pct"
METAFIELD_KEY_COVER_SCALE = "bio_background_cover_scale"
METAFIELD_KEY_RADIAL_MASK = "bio_background_radial_mask"
METAFIELD_KEY_MENU_GRADIENT = "bio_background_menu_gradient"
BIO_MENU_GRADIENT_NONE = "none"
BIO_MENU_GRADIENT_NARROW = "narrow"
BIO_MENU_GRADIENT_WIDE = "wide"
BIO_MENU_GRADIENT_WIDE_BOTTOM = "wide_bottom"
BIO_MENU_GRADIENT_WIDE_V2 = "wide_v2"
BIO_MENU_GRADIENT_WIDE_V3 = "wide_v3"
BIO_MENU_GRADIENT_WIDE_V3_BOTTOM = "wide_v3_bottom"
DEFAULT_BIO_MENU_GRADIENT = BIO_MENU_GRADIENT_WIDE
DEFAULT_BIO_POS_X = 50
DEFAULT_BIO_OVERLAY_PCT = 100
DEFAULT_BIO_COVER_SCALE = False
DEFAULT_BIO_RADIAL_MASK: dict[str, Any] = {
    "enabled": False,
    "cx": 35,
    "cy": 50,
    "rx": 55,
    "ry": 85,
    "feather": 50,
    "exposure": 50,
}
BIO_POS_X_MIN = 0
BIO_POS_X_MAX = 100
BIO_OVERLAY_PCT_MIN = 0
BIO_OVERLAY_PCT_MAX = 100
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
SHOPIFY_FILE_MAX_PX = 4472
BIO_BG_RECOMMENDED_MIN_WIDTH = 2560
BIO_BG_DISPLAY_WIDTH = 3840

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "data"
_LEGACY_DATA_FILE = _LEGACY_DATA_DIR / "collections.json"
_DATA_DIR = _LEGACY_DATA_DIR
_DATA_FILE = _LEGACY_DATA_FILE
_CACHE = cache_path(
    "Komponenty/tldobio/data/collections.json",
    legacy=_LEGACY_DATA_FILE,
)

Logger = Callable[[str], None]
_DEFINITION_ENSURED = False
_DEFINITION_POS_ENSURED = False
_DEFINITION_OVERLAY_ENSURED = False
_DEFINITION_COVER_SCALE_ENSURED = False
_DEFINITION_RADIAL_MASK_ENSURED = False
_DEFINITION_MENU_GRADIENT_ENSURED = False


def bio_plain_from_html(html: str, *, max_len: int = 320) -> str:
    """Opis kolekcji (HTML) → krótki tekst do podglądu w GicleeApp."""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rsplit(" ", 1)[0]
    return (cut or text[: max_len - 1]).strip() + "…"


def normalize_bio_pos_x(raw: Any) -> int:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        value = DEFAULT_BIO_POS_X
    return max(BIO_POS_X_MIN, min(BIO_POS_X_MAX, value))


def normalize_bio_overlay_pct(raw: Any) -> int:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        value = DEFAULT_BIO_OVERLAY_PCT
    return max(BIO_OVERLAY_PCT_MIN, min(BIO_OVERLAY_PCT_MAX, value))


def normalize_bio_menu_gradient(raw: Any) -> str:
    if raw is None or raw == "":
        return DEFAULT_BIO_MENU_GRADIENT
    text = str(raw).strip().lower()
    if text in {"none", "off", "0", "false", "nie", "bez", "bez gradientu"}:
        return BIO_MENU_GRADIENT_NONE
    if text in {
        "wide_v3_bottom",
        "wide-v3-bottom",
        "widev3bottom",
        "wide_v3_dol",
        "wide_v3_dół",
        "gradient szeroki v3 + dół",
        "gradient szeroki v3 + dol",
        "szeroki v3 + dół",
        "szeroki v3 + dol",
    }:
        return BIO_MENU_GRADIENT_WIDE_V3_BOTTOM
    if text in {
        "wide_bottom",
        "wide-bottom",
        "widebottom",
        "wide_dol",
        "wide_dół",
        "gradient szeroki + dół",
        "gradient szeroki + dol",
        "szeroki + dół",
        "szeroki + dol",
    }:
        return BIO_MENU_GRADIENT_WIDE_BOTTOM
    if text in {
        "wide_v3",
        "wide-v3",
        "widev3",
        "gradient szeroki v3",
        "szeroki v3",
        "szeroki v3.",
    }:
        return BIO_MENU_GRADIENT_WIDE_V3
    if text in {
        "wide_v2",
        "wide-v2",
        "widev2",
        "gradient szeroki v2",
        "szeroki v2",
        "szeroki v2.",
    }:
        return BIO_MENU_GRADIENT_WIDE_V2
    if text in {
        "wide",
        "szeroki",
        "gradient szeroki",
        "1",
        "true",
        "on",
    }:
        return BIO_MENU_GRADIENT_WIDE
    if text in {
        "narrow",
        "waski",
        "wąski",
        "gradient wąski",
        "was",
    }:
        return BIO_MENU_GRADIENT_NARROW
    return DEFAULT_BIO_MENU_GRADIENT


def normalize_bio_cover_scale(raw: Any) -> bool:
    if raw is True:
        return True
    if raw is False or raw is None:
        return DEFAULT_BIO_COVER_SCALE
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "tak", "on"}:
        return True
    if text in {"0", "false", "no", "nie", "off", ""}:
        return False
    return DEFAULT_BIO_COVER_SCALE


def _clamp_int(raw: Any, default: int, lo: int, hi: int) -> int:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def radial_mask_inner_stop(feather: int) -> float:
    """Stop gradientu (% promienia) — odpowiednik wtapiania w Lightroom."""
    f = _clamp_int(feather, DEFAULT_BIO_RADIAL_MASK["feather"], 0, 100)
    return max(0.0, min(88.0, (100 - f) * 0.55))


def radial_mask_exposure_alpha(exposure: int) -> float:
    """Ekspozycja 0–100 → alpha czerni (50 ≈ −0,5 EV w LR)."""
    e = _clamp_int(exposure, DEFAULT_BIO_RADIAL_MASK["exposure"], 0, 100)
    return round(e / 100.0 * 0.65, 4)


def normalize_bio_radial_mask(raw: Any) -> dict[str, Any]:
    base = dict(DEFAULT_BIO_RADIAL_MASK)
    if raw is None or raw == "":
        return base
    parsed: Any = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return base
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return base
    if not isinstance(parsed, dict):
        return base
    base["enabled"] = normalize_bio_cover_scale(parsed.get("enabled"))
    base["cx"] = _clamp_int(parsed.get("cx"), base["cx"], 0, 100)
    base["cy"] = _clamp_int(parsed.get("cy"), base["cy"], 0, 100)
    base["rx"] = _clamp_int(parsed.get("rx"), base["rx"], 10, 150)
    base["ry"] = _clamp_int(parsed.get("ry"), base["ry"], 10, 150)
    base["feather"] = _clamp_int(parsed.get("feather"), base["feather"], 0, 100)
    base["exposure"] = _clamp_int(parsed.get("exposure"), base["exposure"], 0, 100)
    return base


def bio_radial_mask_json(mask: dict[str, Any] | None) -> str:
    return json.dumps(normalize_bio_radial_mask(mask or {}), ensure_ascii=False, separators=(",", ":"))


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cache_file(*, for_write: bool) -> Path:
    current_file = Path(_DATA_FILE)
    current_dir = Path(_DATA_DIR)
    if current_file != _LEGACY_DATA_FILE:
        return current_file
    if current_dir != _LEGACY_DATA_DIR:
        return current_dir / _LEGACY_DATA_FILE.name
    return _CACHE.write_path if for_write else _CACHE.read_path()


def load_local_cache() -> dict[str, Any]:
    path = _cache_file(for_write=False)
    if not path.is_file():
        return {"version": 2, "backgrounds": {}, "catalog": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"version": 2, "backgrounds": {}, "catalog": []}
        data.setdefault("version", 2)
        data.setdefault("backgrounds", {})
        data.setdefault("catalog", [])
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": 2, "backgrounds": {}, "catalog": []}


def save_local_cache(data: dict[str, Any]) -> None:
    atomic_write_text(
        _cache_file(for_write=True),
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    )


def is_allowed_image(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_SUFFIXES


def bio_background_display_url(url: str, *, width: int = BIO_BG_DISPLAY_WIDTH) -> str:
    """URL tła BIO na storefront — pełniejsza rozdzielczość z CDN Shopify."""
    text = str(url or "").strip()
    if not text:
        return ""
    if "cdn.shopify.com" not in text and "/cdn/" not in text:
        return text
    if re.search(r"[?&]width=\d+", text, flags=re.I):
        return text
    sep = "&" if "?" in text else "?"
    return f"{text}{sep}width={int(width)}"


def inspect_bio_upload_image(path: Path) -> dict[str, Any]:
    """Wymiary pliku + ewentualne ostrzeżenie o ostrości (bez modyfikacji pliku)."""
    from PIL import Image

    with Image.open(path) as im:
        im.load()
        width, height = im.size
    warn = ""
    if width < BIO_BG_RECOMMENDED_MIN_WIDTH:
        warn = (
            f"Szerokość {width}px — na dużym ekranie tło może wyglądać miękko. "
            f"Zalecane min. {BIO_BG_RECOMMENDED_MIN_WIDTH}px (PNG lub wysokiej jakości JPG)."
        )
    return {
        "width": width,
        "height": height,
        "warn_sharpness": warn,
        "exceeds_shopify_max": max(width, height) > SHOPIFY_FILE_MAX_PX,
    }


def prepare_bio_upload_path(path: Path) -> tuple[Path, dict[str, Any], Path | None]:
    """Przygotuj plik do uploadu: tylko skaluj gdy przekracza limit Shopify (4472 px)."""
    from PIL import Image

    info = inspect_bio_upload_image(path)
    width = int(info["width"])
    height = int(info["height"])
    if not info["exceeds_shopify_max"]:
        return path, info, None

    max_side = max(width, height)
    ratio = SHOPIFY_FILE_MAX_PX / max_side
    new_w = max(1, int(round(width * ratio)))
    new_h = max(1, int(round(height * ratio)))
    suffix = path.suffix.lower()
    temp_path = path.with_name(f"{path.stem}.bio-upload{suffix}")
    counter = 0
    while temp_path.exists():
        counter += 1
        temp_path = path.with_name(f"{path.stem}.bio-upload-{counter}{suffix}")

    with Image.open(path) as im:
        im.load()
        resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
        if suffix in {".jpg", ".jpeg"}:
            resized.save(temp_path, format="JPEG", quality=95, optimize=True, progressive=True)
        elif suffix == ".webp":
            resized.save(temp_path, format="WEBP", quality=95, method=6)
        else:
            resized.save(temp_path, format="PNG", optimize=True)

    info = {
        **info,
        "width": new_w,
        "height": new_h,
        "resized_for_shopify": True,
        "source_width": width,
        "source_height": height,
    }
    return temp_path, info, temp_path


def ensure_bio_background_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_ENSURED  # noqa: PLW0603
    if _DEFINITION_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "bio_background_url") {
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
            "name": "Tło sekcji BIO autora",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY,
            "type": "url",
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
    _log(logger, "[Tło do Bio] Metafield custom.bio_background_url (COLLECTION, storefront).")


def ensure_bio_background_pos_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_POS_ENSURED  # noqa: PLW0603
    if _DEFINITION_POS_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "bio_background_pos_x") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _DEFINITION_POS_ENSURED = True
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
            "name": "Pozycja pozioma tła BIO (%)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_POS_X,
            "type": "number_integer",
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
    _DEFINITION_POS_ENSURED = True
    _log(logger, "[Tło do Bio] Metafield custom.bio_background_pos_x (COLLECTION, storefront).")


def ensure_bio_background_overlay_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_OVERLAY_ENSURED  # noqa: PLW0603
    if _DEFINITION_OVERLAY_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "bio_background_overlay_pct") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _DEFINITION_OVERLAY_ENSURED = True
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
            "name": "Przyciemnienie tła BIO (%)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_OVERLAY_PCT,
            "type": "number_integer",
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
    _DEFINITION_OVERLAY_ENSURED = True
    _log(logger, "[Tło do Bio] Metafield custom.bio_background_overlay_pct (COLLECTION, storefront).")


def ensure_bio_background_cover_scale_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_COVER_SCALE_ENSURED  # noqa: PLW0603
    if _DEFINITION_COVER_SCALE_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "bio_background_cover_scale") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _DEFINITION_COVER_SCALE_ENSURED = True
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
            "name": "Powiększenie kadru tła BIO (scale 1.04)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_COVER_SCALE,
            "type": "boolean",
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
    _DEFINITION_COVER_SCALE_ENSURED = True
    _log(logger, "[Tło do Bio] Metafield custom.bio_background_cover_scale (COLLECTION, storefront).")


def ensure_bio_background_radial_mask_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_RADIAL_MASK_ENSURED  # noqa: PLW0603
    if _DEFINITION_RADIAL_MASK_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "bio_background_radial_mask") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _DEFINITION_RADIAL_MASK_ENSURED = True
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
            "name": "Maska radialna tła BIO (JSON)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_RADIAL_MASK,
            "type": "json",
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
    _DEFINITION_RADIAL_MASK_ENSURED = True
    _log(logger, "[Tło do Bio] Metafield custom.bio_background_radial_mask (COLLECTION, storefront).")


def ensure_bio_background_menu_gradient_metafield_definition(*, logger: Logger | None = None) -> None:
    global _DEFINITION_MENU_GRADIENT_ENSURED  # noqa: PLW0603
    if _DEFINITION_MENU_GRADIENT_ENSURED:
        return
    shop, token = sc.load_session()
    check = """
    query {
      metafieldDefinitions(first: 1, ownerType: COLLECTION, namespace: "custom", key: "bio_background_menu_gradient") {
        nodes { id }
      }
    }
    """
    existing = sc.graphql(shop, token, check, {})
    nodes = ((existing or {}).get("metafieldDefinitions") or {}).get("nodes") or []
    if nodes:
        _DEFINITION_MENU_GRADIENT_ENSURED = True
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
            "name": "Gradient u góry tła BIO (menu)",
            "namespace": METAFIELD_NAMESPACE,
            "key": METAFIELD_KEY_MENU_GRADIENT,
            "type": "single_line_text_field",
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
    _DEFINITION_MENU_GRADIENT_ENSURED = True
    _log(logger, "[Tło do Bio] Metafield custom.bio_background_menu_gradient (COLLECTION, storefront).")


_COLLECTIONS_LIST_GQL = """
query CollectionsList($first: Int!, $after: String) {
  collections(first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      legacyResourceId
      title
      handle
    }
  }
}
"""

_COLLECTIONS_BIO_GQL = """
query CollectionsBio($first: Int!, $after: String) {
  collections(first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      legacyResourceId
      title
      handle
      descriptionHtml
      bioBackground: metafield(namespace: "custom", key: "bio_background_url") { value }
      bioPosX: metafield(namespace: "custom", key: "bio_background_pos_x") { value }
      bioOverlayPct: metafield(namespace: "custom", key: "bio_background_overlay_pct") { value }
      bioCoverScale: metafield(namespace: "custom", key: "bio_background_cover_scale") { value }
      bioRadialMask: metafield(namespace: "custom", key: "bio_background_radial_mask") { value }
      bioMenuGradient: metafield(namespace: "custom", key: "bio_background_menu_gradient") { value }
    }
  }
}
"""


def _paginate_collections_graphql(
    shop: str,
    token: str,
    query: str,
    *,
    on_progress: Callable[[str], None] | None = None,
    progress_label: str = "Kolekcje",
) -> list[dict[str, Any]]:
    nodes_all: list[dict[str, Any]] = []
    cursor: str | None = None
    page = 0
    while True:
        page += 1
        if on_progress:
            on_progress(f"{progress_label}: strona {page}…")
        data = sc.graphql(shop, token, query, {"first": 250, "after": cursor})
        conn = (data or {}).get("collections") or {}
        nodes_all.extend(conn.get("nodes") or [])
        pi = conn.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        cursor = pi.get("endCursor")
        if not cursor:
            break
    return nodes_all


def _node_to_collection_base(node: dict[str, Any]) -> dict[str, Any] | None:
    try:
        cid = int(node.get("legacyResourceId") or 0)
    except (TypeError, ValueError):
        return None
    handle = str(node.get("handle") or "").strip()
    title = str(node.get("title") or "").strip()
    if not cid or not handle:
        return None
    return {
        "id": cid,
        "handle": handle,
        "title": title,
        "kind": "collection",
    }


def fetch_collection_list(
    *,
    logger: Logger | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    shop, token = sc.load_session()
    out: list[dict[str, Any]] = []
    for node in _paginate_collections_graphql(
        shop,
        token,
        _COLLECTIONS_LIST_GQL,
        on_progress=on_progress,
        progress_label="Pobieram kolekcje",
    ):
        col = _node_to_collection_base(node)
        if col:
            out.append(col)
    out.sort(key=lambda r: (r.get("title") or "").lower())
    _log(logger, f"[Tło do Bio] Kolekcje: {len(out)}.")
    return out


def _fetch_collection_rows_with_bio_graphql(
    shop: str,
    token: str,
    *,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in _paginate_collections_graphql(
        shop,
        token,
        _COLLECTIONS_BIO_GQL,
        on_progress=on_progress,
        progress_label="Kolekcje + tła BIO",
    ):
        col = _node_to_collection_base(node)
        if not col:
            continue
        mf = node.get("bioBackground") or {}
        url = str(mf.get("value") or "").strip()
        pos_mf = node.get("bioPosX") or {}
        pos_x = normalize_bio_pos_x(pos_mf.get("value"))
        overlay_mf = node.get("bioOverlayPct") or {}
        overlay_pct = normalize_bio_overlay_pct(overlay_mf.get("value"))
        cover_scale_mf = node.get("bioCoverScale") or {}
        cover_scale = normalize_bio_cover_scale(cover_scale_mf.get("value"))
        radial_mf = node.get("bioRadialMask") or {}
        radial_mask = normalize_bio_radial_mask(radial_mf.get("value"))
        menu_gradient_mf = node.get("bioMenuGradient") or {}
        menu_gradient = normalize_bio_menu_gradient(menu_gradient_mf.get("value"))
        description_html = str(node.get("descriptionHtml") or "")
        bio_preview = bio_plain_from_html(description_html)
        rows.append(
            {
                **col,
                "background_url": url,
                "background_pos_x": pos_x,
                "background_overlay_pct": overlay_pct,
                "background_cover_scale": cover_scale,
                "background_radial_mask": radial_mask,
                "background_menu_gradient": menu_gradient,
                "description_html": description_html,
                "bio_preview": bio_preview,
                "has_background": bool(url),
                "status": "tak" if url else "—",
            }
        )
    rows.sort(key=lambda r: (r.get("title") or "").lower())
    return rows


def load_cached_collection_rows() -> list[dict[str, Any]] | None:
    """Ostatni snapshot listy kolekcji z cache lokalnego (natychmiastowy start UI)."""
    cache = load_local_cache()
    catalog = cache.get("catalog")
    if not isinstance(catalog, list) or not catalog:
        return None
    return [dict(row) for row in catalog if isinstance(row, dict)]


def find_collection_metafield(
    shop: str,
    token: str,
    collection_id: int,
    *,
    namespace: str,
    key: str,
) -> dict | None:
    data = sc.rest_get(
        shop,
        token,
        f"collections/{int(collection_id)}/metafields.json",
        limit=250,
    )
    for mf in (data or {}).get("metafields") or []:
        if mf.get("namespace") == namespace and mf.get("key") == key:
            return mf
    return None


def upsert_collection_metafield(
    shop: str,
    token: str,
    collection_id: int,
    *,
    namespace: str,
    key: str,
    value: str,
    ftype: str = "url",
) -> dict:
    existing = find_collection_metafield(
        shop, token, collection_id, namespace=namespace, key=key
    )
    if existing:
        mid = int(existing["id"])
        out = sc.rest_put(
            shop,
            token,
            f"metafields/{mid}.json",
            {"metafield": {"id": mid, "value": value, "type": ftype}},
        )
        return (out or {}).get("metafield") or {}
    out = sc.rest_post(
        shop,
        token,
        f"collections/{int(collection_id)}/metafields.json",
        {
            "metafield": {
                "namespace": namespace,
                "key": key,
                "type": ftype,
                "value": value,
            }
        },
    )
    return (out or {}).get("metafield") or {}


def delete_collection_metafield(
    shop: str,
    token: str,
    collection_id: int,
    *,
    namespace: str,
    key: str,
) -> bool:
    existing = find_collection_metafield(
        shop, token, collection_id, namespace=namespace, key=key
    )
    if not existing:
        return False
    sc.rest_delete(shop, token, f"metafields/{int(existing['id'])}.json")
    return True


def fetch_bio_background_map(
    collections: list[dict[str, Any]],
    *,
    logger: Logger | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """Mapa handle → URL tła. Preferuj load_collections_with_backgrounds (GraphQL, 1 przebieg)."""
    out: dict[str, str] = {}
    for col in collections:
        handle = str(col.get("handle") or "").strip()
        url = str(col.get("background_url") or "").strip()
        if handle and url:
            out[handle] = url
    if out:
        _log(logger, f"[Tło do Bio] Tła (z przekazanej listy): {len(out)}.")
        return out
    shop, token = sc.load_session()
    rows = _fetch_collection_rows_with_bio_graphql(
        shop, token, on_progress=on_progress
    )
    for row in rows:
        handle = str(row.get("handle") or "").strip()
        url = str(row.get("background_url") or "").strip()
        if handle and url:
            out[handle] = url
    _log(logger, f"[Tło do Bio] Tła w Shopify: {len(out)}.")
    return out


def sync_local_from_shopify(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cache = load_local_cache()
    cache["version"] = 2
    cache["fetched_at"] = _now_iso()
    backgrounds = cache.setdefault("backgrounds", {})
    seen: set[str] = set()
    catalog: list[dict[str, Any]] = []
    for col in rows:
        handle = str(col.get("handle") or "").strip()
        if not handle:
            continue
        seen.add(handle)
        url = str(col.get("background_url") or "").strip()
        pos_x = normalize_bio_pos_x(col.get("background_pos_x"))
        overlay_pct = normalize_bio_overlay_pct(col.get("background_overlay_pct"))
        cover_scale = normalize_bio_cover_scale(col.get("background_cover_scale"))
        radial_mask = normalize_bio_radial_mask(col.get("background_radial_mask"))
        menu_gradient = normalize_bio_menu_gradient(col.get("background_menu_gradient"))
        catalog.append(
            {
                "id": col.get("id"),
                "handle": handle,
                "title": col.get("title") or "",
                "kind": col.get("kind") or "collection",
                "background_url": url,
                "background_pos_x": pos_x,
                "background_overlay_pct": overlay_pct,
                "background_cover_scale": cover_scale,
                "background_radial_mask": radial_mask,
                "background_menu_gradient": menu_gradient,
                "bio_preview": col.get("bio_preview") or "",
                "has_background": bool(url),
                "status": "tak" if url else "—",
            }
        )
        if url:
            backgrounds[handle] = {
                "collection_id": col.get("id"),
                "handle": handle,
                "title": col.get("title") or "",
                "url": url,
                "pos_x": pos_x,
                "overlay_pct": overlay_pct,
                "cover_scale": cover_scale,
                "radial_mask": radial_mask,
                "menu_gradient": menu_gradient,
                "updated_at": backgrounds.get(handle, {}).get("updated_at") or _now_iso(),
            }
        elif handle in backgrounds:
            del backgrounds[handle]
    for stale in [h for h in list(backgrounds.keys()) if h not in seen]:
        del backgrounds[stale]
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


def load_collections_with_backgrounds(
    *,
    logger: Logger | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    shop, token = sc.load_session()
    rows = _fetch_collection_rows_with_bio_graphql(
        shop, token, on_progress=on_progress
    )
    sync_local_from_shopify(rows)
    _log(logger, f"[Tło do Bio] Załadowano {len(rows)} kolekcji (GraphQL).")
    return rows


def upload_bio_background(
    collection_id: int,
    handle: str,
    title: str,
    image_path: Path,
    *,
    pos_x: int | None = None,
    overlay_pct: int | None = None,
    cover_scale: bool | None = None,
    radial_mask: dict[str, Any] | None = None,
    menu_gradient: str | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    path = Path(image_path)
    if not path.is_file():
        return {"ok": False, "error": "Plik nie istnieje."}
    if not is_allowed_image(path):
        return {
            "ok": False,
            "error": "Dozwolone formaty: JPG, JPEG, PNG, WEBP.",
        }
    ensure_bio_background_metafield_definition(logger=logger)
    ensure_bio_background_pos_metafield_definition(logger=logger)
    ensure_bio_background_overlay_metafield_definition(logger=logger)
    ensure_bio_background_cover_scale_metafield_definition(logger=logger)
    ensure_bio_background_radial_mask_metafield_definition(logger=logger)
    ensure_bio_background_menu_gradient_metafield_definition(logger=logger)
    shop, token = sc.load_session()
    cid = int(collection_id)
    h = str(handle or "").strip()
    if not cid or not h:
        return {"ok": False, "error": "Brak identyfikatora kolekcji."}
    pos = normalize_bio_pos_x(pos_x if pos_x is not None else DEFAULT_BIO_POS_X)
    overlay = normalize_bio_overlay_pct(
        overlay_pct if overlay_pct is not None else DEFAULT_BIO_OVERLAY_PCT
    )
    scale_cover = normalize_bio_cover_scale(
        cover_scale if cover_scale is not None else DEFAULT_BIO_COVER_SCALE
    )
    radial = normalize_bio_radial_mask(
        radial_mask if radial_mask is not None else DEFAULT_BIO_RADIAL_MASK
    )
    menu_grad = normalize_bio_menu_gradient(
        menu_gradient if menu_gradient is not None else DEFAULT_BIO_MENU_GRADIENT
    )
    upload_path, upload_info, temp_path = prepare_bio_upload_path(path)
    try:
        try:
            url = sc.upload_file_to_shopify_files(
                upload_path,
                alt=f"Tło BIO — {title or h}",
                preserve_original_bytes=True,
            )
            url = bio_background_display_url(url)
        except sc.ShopifyError as exc:
            return {"ok": False, "error": str(exc)}
        try:
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY,
                value=url,
                ftype="url",
            )
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY_POS_X,
                value=str(pos),
                ftype="number_integer",
            )
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY_OVERLAY_PCT,
                value=str(overlay),
                ftype="number_integer",
            )
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY_COVER_SCALE,
                value="true" if scale_cover else "false",
                ftype="boolean",
            )
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY_RADIAL_MASK,
                value=bio_radial_mask_json(radial),
                ftype="json",
            )
            upsert_collection_metafield(
                shop,
                token,
                cid,
                namespace=METAFIELD_NAMESPACE,
                key=METAFIELD_KEY_MENU_GRADIENT,
                value=menu_grad,
                ftype="single_line_text_field",
            )
        except sc.ShopifyError as exc:
            return {"ok": False, "error": str(exc)}
    finally:
        if temp_path and temp_path.is_file():
            try:
                temp_path.unlink()
            except OSError:
                pass
    cache = load_local_cache()
    cache.setdefault("backgrounds", {})[h] = {
        "collection_id": cid,
        "handle": h,
        "title": title,
        "url": url,
        "pos_x": pos,
        "overlay_pct": overlay,
        "cover_scale": scale_cover,
        "radial_mask": radial,
        "menu_gradient": menu_grad,
        "updated_at": _now_iso(),
    }
    _patch_cached_row(
        h,
        cache=cache,
        background_url=url,
        background_pos_x=pos,
        background_overlay_pct=overlay,
        background_cover_scale=scale_cover,
        background_radial_mask=radial,
        background_menu_gradient=menu_grad,
        has_background=True,
        status="tak",
    )
    save_local_cache(cache)
    _log(logger, f"[Tło do Bio] Zapisano tło dla {h}.")
    return {
        "ok": True,
        "url": url,
        "handle": h,
        "background_pos_x": pos,
        "background_overlay_pct": overlay,
        "background_cover_scale": scale_cover,
        "background_radial_mask": radial,
        "background_menu_gradient": menu_grad,
        "upload_width": upload_info.get("width"),
        "upload_height": upload_info.get("height"),
        "warn_sharpness": upload_info.get("warn_sharpness") or "",
        "resized_for_shopify": bool(upload_info.get("resized_for_shopify")),
    }


def save_bio_background_display_settings(
    collection_id: int,
    handle: str,
    *,
    pos_x: int,
    overlay_pct: int,
    cover_scale: bool,
    radial_mask: dict[str, Any] | None = None,
    menu_gradient: str | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    ensure_bio_background_pos_metafield_definition(logger=logger)
    ensure_bio_background_overlay_metafield_definition(logger=logger)
    ensure_bio_background_cover_scale_metafield_definition(logger=logger)
    ensure_bio_background_radial_mask_metafield_definition(logger=logger)
    ensure_bio_background_menu_gradient_metafield_definition(logger=logger)
    shop, token = sc.load_session()
    cid = int(collection_id)
    h = str(handle or "").strip()
    if not cid or not h:
        return {"ok": False, "error": "Brak identyfikatora kolekcji."}
    pos = normalize_bio_pos_x(pos_x)
    overlay = normalize_bio_overlay_pct(overlay_pct)
    scale_cover = normalize_bio_cover_scale(cover_scale)
    radial = normalize_bio_radial_mask(
        radial_mask if radial_mask is not None else DEFAULT_BIO_RADIAL_MASK
    )
    menu_grad = normalize_bio_menu_gradient(
        menu_gradient if menu_gradient is not None else DEFAULT_BIO_MENU_GRADIENT
    )
    try:
        upsert_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_POS_X,
            value=str(pos),
            ftype="number_integer",
        )
        upsert_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_OVERLAY_PCT,
            value=str(overlay),
            ftype="number_integer",
        )
        upsert_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_COVER_SCALE,
            value="true" if scale_cover else "false",
            ftype="boolean",
        )
        upsert_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_RADIAL_MASK,
            value=bio_radial_mask_json(radial),
            ftype="json",
        )
        upsert_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_MENU_GRADIENT,
            value=menu_grad,
            ftype="single_line_text_field",
        )
    except sc.ShopifyError as exc:
        return {"ok": False, "error": str(exc)}
    cache = load_local_cache()
    bg = (cache.get("backgrounds") or {}).get(h)
    if isinstance(bg, dict):
        bg["pos_x"] = pos
        bg["overlay_pct"] = overlay
        bg["cover_scale"] = scale_cover
        bg["radial_mask"] = radial
        bg["menu_gradient"] = menu_grad
    _patch_cached_row(
        h,
        cache=cache,
        background_pos_x=pos,
        background_overlay_pct=overlay,
        background_cover_scale=scale_cover,
        background_radial_mask=radial,
        background_menu_gradient=menu_grad,
    )
    save_local_cache(cache)
    _log(
        logger,
        f"[Tło do Bio] Ustawienia tła {h}: pozycja {pos}%, overlay {overlay}%, scale {scale_cover}, radial {radial.get('enabled')}, menu gradient {menu_grad}.",
    )
    return {
        "ok": True,
        "handle": h,
        "background_pos_x": pos,
        "background_overlay_pct": overlay,
        "background_cover_scale": scale_cover,
        "background_radial_mask": radial,
        "background_menu_gradient": menu_grad,
    }


def save_bio_background_position(
    collection_id: int,
    handle: str,
    pos_x: int,
    *,
    overlay_pct: int | None = None,
    cover_scale: bool | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Kompatybilność wsteczna — zapisuje też overlay i scale gdy podane."""
    overlay = (
        normalize_bio_overlay_pct(overlay_pct)
        if overlay_pct is not None
        else DEFAULT_BIO_OVERLAY_PCT
    )
    scale = (
        normalize_bio_cover_scale(cover_scale)
        if cover_scale is not None
        else DEFAULT_BIO_COVER_SCALE
    )
    return save_bio_background_display_settings(
        collection_id,
        handle,
        pos_x=pos_x,
        overlay_pct=overlay,
        cover_scale=scale,
        logger=logger,
    )


def clear_bio_background(
    collection_id: int,
    handle: str,
    *,
    logger: Logger | None = None,
) -> dict[str, Any]:
    shop, token = sc.load_session()
    cid = int(collection_id)
    h = str(handle or "").strip()
    if not cid or not h:
        return {"ok": False, "error": "Brak identyfikatora kolekcji."}
    try:
        delete_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY,
        )
        delete_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_POS_X,
        )
        delete_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_OVERLAY_PCT,
        )
        delete_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_COVER_SCALE,
        )
        delete_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_RADIAL_MASK,
        )
        delete_collection_metafield(
            shop,
            token,
            cid,
            namespace=METAFIELD_NAMESPACE,
            key=METAFIELD_KEY_MENU_GRADIENT,
        )
    except sc.ShopifyError as exc:
        return {"ok": False, "error": str(exc)}
    cache = load_local_cache()
    backgrounds = cache.get("backgrounds") or {}
    if h in backgrounds:
        del backgrounds[h]
    _patch_cached_row(
        h,
        cache=cache,
        background_url="",
        background_pos_x=DEFAULT_BIO_POS_X,
        background_overlay_pct=DEFAULT_BIO_OVERLAY_PCT,
        background_cover_scale=DEFAULT_BIO_COVER_SCALE,
        background_radial_mask=dict(DEFAULT_BIO_RADIAL_MASK),
        background_menu_gradient=DEFAULT_BIO_MENU_GRADIENT,
        has_background=False,
        status="—",
    )
    save_local_cache(cache)
    _log(logger, f"[Tło do Bio] Usunięto tło dla {h}.")
    return {"ok": True, "handle": h}
