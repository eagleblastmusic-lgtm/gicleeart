"""Publikacja zoom HD: kafelki -> R2 + metafield produktu Shopify."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Callable

from . import shopify_client as sc
from .parser import slugify
from .r2_storage import load_r2_config, upload_many
from .r2_usage import record_zoom_upload
from .zoom_tiles import generate_zoom_package, manifest_json

Logger = Callable[[str], None]
Progress = Callable[[int, int, str], None]
Timing = Callable[[dict[str, Any]], None]

ZOOM_METAFIELD_NAMESPACE = "custom"
ZOOM_METAFIELD_KEY = "zoom_manifest"
# Szablon motywu: templates/product.nowy-szblon-produktu.json (zoom tylko tam)
ZOOM_PRODUCT_TEMPLATE_SUFFIX = "nowy-szblon-produktu"


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def format_timing_line(
    *,
    tiles_s: float | None = None,
    upload_s: float | None = None,
    shopify_s: float | None = None,
) -> str:
    parts: list[str] = []
    if tiles_s is not None:
        parts.append(f"kafelki {tiles_s:.1f}s")
    if upload_s is not None:
        parts.append(f"R2 {upload_s:.1f}s")
    if shopify_s is not None:
        parts.append(f"Shopify {shopify_s:.1f}s")
    return " · ".join(parts)


def zoom_storage_prefix(*, artist: str, base_title: str, handle: str | None = None) -> str:
    """Prefiks obiektow R2: zoom/<handle-lub-slug>."""
    if handle:
        slug = re.sub(r"[^a-z0-9-]+", "-", handle.lower()).strip("-")
    else:
        slug = slugify(f"{artist} {base_title}")
    return f"zoom/{slug}"


def publish_product_zoom(
    *,
    product_id: int,
    handle: str,
    full_image_path: Path,
    artist: str = "",
    base_title: str = "",
    logger: Logger | None = None,
    on_progress: Progress | None = None,
    on_timing: Timing | None = None,
) -> dict[str, Any]:
    """Generuje kafelki, wgrywa na R2, zapisuje custom.zoom_manifest (JSON)."""
    cfg = load_r2_config()
    prefix = zoom_storage_prefix(artist=artist, base_title=base_title, handle=handle)
    fname = full_image_path.name
    total_steps = 3  # kafelki, R2, Shopify

    def emit_timing(
        *,
        phase: str,
        tiles_s: float | None = None,
        upload_s: float | None = None,
        shopify_s: float | None = None,
    ) -> None:
        if on_timing:
            on_timing(
                {
                    "phase": phase,
                    "file": fname,
                    "tiles_s": tiles_s,
                    "upload_s": upload_s,
                    "shopify_s": shopify_s,
                }
            )

    if on_progress:
        on_progress(0, total_steps, "kafelki…")

    t_tiles = time.perf_counter()
    pkg = generate_zoom_package(full_image_path, logger=logger)
    tiles_s = time.perf_counter() - t_tiles
    _log(logger, f"[zoom] Kafelki: {tiles_s:.1f}s ({len(pkg.upload_items)} plikow)")
    emit_timing(phase="tiles", tiles_s=tiles_s)
    if on_progress:
        on_progress(1, total_steps, "R2 upload…")

    try:
        _log(logger, f"[zoom] Upload do R2: {prefix}/ ({len(pkg.upload_items)} plikow)")
        t_upload = time.perf_counter()
        upload_many(cfg, prefix=prefix, items=pkg.upload_items, logger=logger)
        upload_s = time.perf_counter() - t_upload
        upload_bytes = sum(p.stat().st_size for _, p in pkg.upload_items if p.is_file())
        record_zoom_upload(total_bytes=upload_bytes, handle=handle)
        _log(logger, f"[zoom] R2 upload: {upload_s:.1f}s")
        emit_timing(phase="upload", tiles_s=tiles_s, upload_s=upload_s)
        if on_progress:
            on_progress(2, total_steps, "Shopify…")

        t_shopify = time.perf_counter()
        manifest_str = manifest_json(pkg.manifest, public_base_url=cfg.public_base_url, prefix=prefix)
        shop, token = sc.load_session()
        sc.upsert_metafield(
            shop,
            token,
            int(product_id),
            namespace=ZOOM_METAFIELD_NAMESPACE,
            key=ZOOM_METAFIELD_KEY,
            value=manifest_str,
            ftype="json",
        )
        _log(logger, f"[zoom] Zapisano {ZOOM_METAFIELD_NAMESPACE}.{ZOOM_METAFIELD_KEY} na produkcie {product_id}")

        try:
            sc.update_product(
                shop,
                token,
                int(product_id),
                {"template_suffix": ZOOM_PRODUCT_TEMPLATE_SUFFIX},
            )
            _log(
                logger,
                f"[zoom] Szablon produktu: {ZOOM_PRODUCT_TEMPLATE_SUFFIX}",
            )
        except sc.ShopifyError as e:
            _log(logger, f"[zoom] Nie ustawiono szablonu produktu: {e}")
        shopify_s = time.perf_counter() - t_shopify
        _log(logger, f"[zoom] Shopify: {shopify_s:.1f}s")
        total_s = tiles_s + upload_s + shopify_s
        timing_line = format_timing_line(
            tiles_s=tiles_s, upload_s=upload_s, shopify_s=shopify_s
        )
        _log(logger, f"[zoom] Czas ({fname}): {timing_line} (razem {total_s:.1f}s)")
        emit_timing(
            phase="done",
            tiles_s=tiles_s,
            upload_s=upload_s,
            shopify_s=shopify_s,
        )
        if on_progress:
            on_progress(total_steps, total_steps, timing_line)

        return {
            "product_id": product_id,
            "handle": handle,
            "prefix": prefix,
            "public_base": f"{cfg.public_base_url.rstrip('/')}/{prefix}",
            "tiles": len(pkg.upload_items),
            "timing": {
                "tiles_s": round(tiles_s, 2),
                "upload_s": round(upload_s, 2),
                "shopify_s": round(shopify_s, 2),
                "total_s": round(total_s, 2),
            },
        }
    finally:
        pkg.cleanup()


def publish_zoom_for_queue_item(
    item: dict[str, Any],
    *,
    logger: Logger | None = None,
    on_progress: Progress | None = None,
    on_timing: Timing | None = None,
) -> dict[str, Any]:
    """Wymaga istniejacego produktu (existing_product_id lub po create) i pliku Full."""
    path = item.get("path")
    if path is None:
        raise ValueError("Brak sciezki pliku w pozycji kolejki.")

    pid = item.get("existing_product_id") or item.get("product_id")
    if not pid:
        raise ValueError(
            f"Brak product_id dla {path.name} — najpierw utworz produkt w Shopify, potem zoom."
        )

    handle = (item.get("shopify_handle") or item.get("handle") or "").strip()
    if not handle:
        shop, token = sc.load_session()
        prod = sc.get_product(shop, token, int(pid))
        handle = (prod.get("handle") or "").strip()
    if not handle:
        raise ValueError(f"Nie mozna ustalic handle produktu id={pid}.")

    return publish_product_zoom(
        product_id=int(pid),
        handle=handle,
        full_image_path=Path(path),
        artist=str(item.get("artist") or ""),
        base_title=str(item.get("base_title") or item.get("title") or ""),
        logger=logger,
        on_progress=on_progress,
        on_timing=on_timing,
    )
