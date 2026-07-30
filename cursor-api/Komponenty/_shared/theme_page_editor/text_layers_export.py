"""Eksport warstw tekstowych wariantu do bezpiecznego assetu motywu."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text

from .config import PageEditorConfig
from .text_layers import load_document, normalize_document, shared_variant_path

RUNTIME_RELPATHS = (
    "assets/giclee-text-layers.css",
    "assets/giclee-text-layers.js",
    "snippets/scripts.liquid",
)


def template_asset_slug(template_rel: str) -> str:
    stem = Path(str(template_rel)).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return slug or "page"


def asset_basename_for_template(template_rel: str) -> str:
    return f"giclee-text-layers-{template_asset_slug(template_rel)}.js"


def asset_basename(config: PageEditorConfig) -> str:
    return asset_basename_for_template(config.template_rel)


def export_document(
    document: dict[str, Any],
    *,
    page: str,
    variant_id: str,
) -> dict[str, Any]:
    normalized = normalize_document(document)
    sections = {
        section_key: [
            layer
            for layer in layers
            if bool(layer.get("enabled", True))
        ]
        for section_key, layers in normalized["sections"].items()
    }
    sections = {key: rows for key, rows in sections.items() if rows}
    return {
        "schemaVersion": 1,
        "page": page,
        "variant": str(variant_id),
        "sections": sections,
    }


def payload_bytes(payload: dict[str, Any]) -> bytes:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        "window.GICLEE_TEXT_LAYERS = " + encoded + ";\n"
    ).encode("utf-8")


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    data = payload_bytes(payload).decode("utf-8")
    try:
        current = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        current = None
    if current == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, data)


def write_shared_text_layers_asset(
    config: PageEditorConfig,
    variant_id: str,
) -> Path:
    from Komponenty.stronaglowna.service import theme_root

    document = load_document(shared_variant_path(config, variant_id))
    payload = export_document(
        document,
        page=template_asset_slug(config.template_rel),
        variant_id=variant_id,
    )
    path = theme_root() / "assets" / asset_basename(config)
    _write_payload(path, payload)
    return path


def write_home_text_layers_asset(variant_id: str) -> Path:
    from Komponenty.stronaglowna.homepage_variants import variant_file_path
    from Komponenty.stronaglowna.service import theme_root

    document = load_document(
        variant_file_path(variant_id, "text-layers.json")
    )
    payload = export_document(
        document,
        page="index",
        variant_id=variant_id,
    )
    path = theme_root() / "assets" / asset_basename_for_template(
        "templates/index.json"
    )
    _write_payload(path, payload)
    return path


__all__ = [
    "RUNTIME_RELPATHS",
    "asset_basename",
    "asset_basename_for_template",
    "export_document",
    "payload_bytes",
    "template_asset_slug",
    "write_home_text_layers_asset",
    "write_shared_text_layers_asset",
]
