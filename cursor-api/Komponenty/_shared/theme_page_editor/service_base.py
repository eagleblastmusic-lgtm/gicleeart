"""I/O szablonów motywu, pola JSON, backup — delegacja deploy do stronaglowna."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from giclee_app.app_paths import atomic_write_bytes, backup_path

from Komponenty.stronaglowna.service import (
    cdn_url_to_shopify_ref,
    deploy_theme,
    fetch_thumbnail_bytes,
    normalize_shopify_video_ref,
    path_get,
    path_set,
    shopify_ref_label,
    theme_root,
    upload_shopify_image,
    upload_shopify_video,
)
from Komponenty.stronaglowna.text_html import (
    body_to_html,
    build_heading_html,
    html_to_body_plain,
    merge_heading_body_html,
    parse_heading,
    split_combined_html,
)

from .config import PageEditorConfig
from .image_object_y import normalize_object_y, object_y_field_id, object_y_path
from .types import TemplateField, TemplateZone, set_zone_enabled, zone_enabled

Logger = Callable[[str], None]

INDEX_HEADER = """/*
 * ------------------------------------------------------------
 * IMPORTANT: The contents of this file are auto-generated.
 *
 * This file may be updated by the Shopify admin theme editor
 * or related systems. Please exercise caution as any changes
 * made to this file may be overwritten.
 * ------------------------------------------------------------
 */
"""

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def _strip_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def component_data_dir(config: PageEditorConfig) -> Path:
    return config.component_dir / "data"


def backup_write_dir_for(
    config: PageEditorConfig, category: str = "backups"
) -> Path:
    """Return the external writable directory for editor backup category."""

    marker = backup_path(
        f"Komponenty/{config.component_id}/data/{category}/.backup-root"
    )
    return marker.write_path.parent


def backups_dir_for(config: PageEditorConfig) -> Path:
    """Prefer external backups, with the source directory as read-only fallback."""

    external = backup_write_dir_for(config)
    if external.is_dir():
        return external
    legacy = component_data_dir(config) / "backups"
    if legacy.is_dir():
        return legacy
    return external


def variants_root_for(config: PageEditorConfig) -> Path:
    return component_data_dir(config) / "variants"


def template_path_for_config(config: PageEditorConfig) -> Path:
    return theme_root() / config.template_rel.replace("/", "\\").replace("\\", "/")


def load_template_from_path(path: Path, *, logger: Logger | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku szablonu: {path}")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(_strip_json_header(raw))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} — nieprawidłowy format.")
    _log(logger, f"[{config_slug(path)}] Wczytano {path.name}.")
    return data


def config_slug(path: Path) -> str:
    return path.stem


def save_template_to_path(path: Path, template: dict[str, Any], *, logger: Logger | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(template, ensure_ascii=False, indent=2) + "\n"
    rel = str(path).replace("\\", "/")
    header = INDEX_HEADER if "/templates/" in rel else ""
    path.write_text(header + body, encoding="utf-8")
    _log(logger, f"Zapisano {path.name}.")


def load_template(config: PageEditorConfig, *, logger: Logger | None = None) -> dict[str, Any]:
    return load_template_from_path(template_path_for_config(config), logger=logger)


def save_template(
    config: PageEditorConfig, template: dict[str, Any], *, logger: Logger | None = None
) -> None:
    save_template_to_path(template_path_for_config(config), template, logger=logger)


def backup_file(path: Path, config: PageEditorConfig, *, logger: Logger | None = None) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku do kopii: {path}")
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_write_dir_for(config)
    stamped = backup_dir / f"{path.stem}-{ts}{path.suffix}"
    atomic_write_bytes(stamped, path.read_bytes())
    _log(logger, f"Kopia zapasowa: {stamped.name}")
    return stamped


def backup_before_save(config: PageEditorConfig, *, logger: Logger | None = None) -> list[Path]:
    path = template_path_for_config(config)
    if path.is_file():
        return [backup_file(path, config, logger=logger)]
    return []


def _block_at(template: dict[str, Any], block_path: tuple[str, ...]) -> dict[str, Any] | None:
    block = path_get(template, block_path)
    return block if isinstance(block, dict) else None


def _read_blocks_visible(template: dict[str, Any], field: TemplateField) -> bool:
    paths = field.block_paths
    if not paths:
        return True
    found = False
    for block_path in paths:
        block = _block_at(template, block_path)
        if block is None:
            continue
        found = True
        if block.get("disabled"):
            return False
    return found


def _write_blocks_visible(template: dict[str, Any], field: TemplateField, visible: bool) -> None:
    for block_path in field.block_paths:
        block = _block_at(template, block_path)
        if block is None:
            continue
        if visible:
            block.pop("disabled", None)
        else:
            block["disabled"] = True


def read_field(template: dict[str, Any], field: TemplateField) -> Any:
    if field.kind == "blocks_visible":
        return _read_blocks_visible(template, field)
    if field.kind == "section_background" and field.path:
        from Komponenty.stronaglowna.registry import HomeField
        from Komponenty.stronaglowna.service import _read_section_background

        home_field = HomeField(
            field.field_id,
            field.label,
            "section_background",
            field.path,
            hint=field.hint or "",
        )
        return _read_section_background(template, home_field)
    if not field.path:
        return None
    return path_get(template, field.path)


def _heading_tag_key(field_id: str) -> str:
    return f"_{field_id}_tag"


def _load_text_fields(template: dict[str, Any], zone: TemplateZone) -> dict[str, Any]:
    out: dict[str, Any] = {}
    by_path: dict[tuple[str, ...], list[TemplateField]] = {}
    for fld in zone.fields:
        if fld.kind in ("heading", "body") and fld.path:
            by_path.setdefault(fld.path, []).append(fld)

    handled_paths: set[tuple[str, ...]] = set()
    for fld in zone.fields:
        if fld.kind not in ("heading", "body") or not fld.path:
            continue
        if fld.path in handled_paths:
            continue
        raw = str(path_get(template, fld.path) or "")
        fields_at_path = by_path.get(fld.path, [])
        if len(fields_at_path) > 1:
            tag, heading, body = split_combined_html(raw)
            handled_paths.add(fld.path)
            for f in fields_at_path:
                if f.kind == "heading":
                    out[f.field_id] = heading
                    out[_heading_tag_key(f.field_id)] = tag
                else:
                    out[f.field_id] = body
        elif fld.kind == "heading":
            tag, heading = parse_heading(raw)
            out[fld.field_id] = heading
            out[_heading_tag_key(fld.field_id)] = tag
        else:
            out[fld.field_id] = html_to_body_plain(raw)
    return out


def _apply_text_fields(template: dict[str, Any], zone: TemplateZone, values: dict[str, Any]) -> None:
    by_path: dict[tuple[str, ...], list[TemplateField]] = {}
    for fld in zone.fields:
        if fld.kind in ("heading", "body") and fld.path:
            by_path.setdefault(fld.path, []).append(fld)

    for path, fields_at_path in by_path.items():
        heading_fields = [f for f in fields_at_path if f.kind == "heading"]
        body_fields = [f for f in fields_at_path if f.kind == "body"]
        if heading_fields and body_fields:
            hf = heading_fields[0]
            bf = body_fields[0]
            tag = str(values.get(_heading_tag_key(hf.field_id), "h2") or "h2")
            merged = merge_heading_body_html(
                str(values.get(hf.field_id, "") or ""),
                str(values.get(bf.field_id, "") or ""),
                tag=tag,
            )
            path_set(template, path, merged)
        elif heading_fields:
            hf = heading_fields[0]
            tag = str(values.get(_heading_tag_key(hf.field_id), "h2") or "h2")
            path_set(template, path, build_heading_html(str(values.get(hf.field_id, "") or ""), tag=tag))
        elif body_fields:
            bf = body_fields[0]
            path_set(template, path, body_to_html(str(values.get(bf.field_id, "") or "")))


def write_field(template: dict[str, Any], field: TemplateField, value: Any) -> None:
    if field.kind in ("heading", "body", "theme_asset"):
        return
    if field.kind == "blocks_visible":
        _write_blocks_visible(template, field, bool(value))
        return
    if not field.path:
        return
    if field.kind == "bool":
        path_set(template, field.path, bool(value))
    elif field.kind == "int":
        try:
            path_set(template, field.path, int(value))
        except (TypeError, ValueError):
            path_set(template, field.path, 0)
    elif field.kind == "float":
        try:
            path_set(template, field.path, float(str(value).replace(",", ".")))
        except (TypeError, ValueError):
            path_set(template, field.path, 0.0)
    elif field.kind == "section_background" and field.path:
        from Komponenty.stronaglowna.registry import HomeField
        from Komponenty.stronaglowna.service import _write_section_background

        home_field = HomeField(
            field.field_id,
            field.label,
            "section_background",
            field.path,
            hint=field.hint or "",
        )
        _write_section_background(template, home_field, value)
    else:
        path_set(template, field.path, value)


def load_zone_values(template: dict[str, Any], zone: TemplateZone) -> dict[str, Any]:
    out: dict[str, Any] = {"_enabled": zone_enabled(template, zone)}
    out.update(_load_text_fields(template, zone))
    for fld in zone.fields:
        if fld.kind in ("heading", "body"):
            continue
        val = read_field(template, fld)
        if fld.kind in ("bool", "blocks_visible"):
            out[fld.field_id] = bool(val)
        elif fld.kind == "int":
            try:
                out[fld.field_id] = int(val or 0)
            except (TypeError, ValueError):
                out[fld.field_id] = 0
        elif fld.kind == "float":
            try:
                out[fld.field_id] = float(val if val is not None else 0)
            except (TypeError, ValueError):
                out[fld.field_id] = 0.0
        elif fld.kind == "shopify_image" and fld.path:
            out[fld.field_id] = val if val is not None else ""
            oy_path = object_y_path(fld.path)
            if oy_path:
                out[object_y_field_id(fld.field_id)] = normalize_object_y(path_get(template, oy_path))
        elif fld.kind == "section_background":
            from Komponenty.stronaglowna.service import _parse_section_background

            out[fld.field_id] = _parse_section_background(val)
        else:
            out[fld.field_id] = val if val is not None else ""
    return out


def _write_image_object_y(
    template: dict[str, Any], field: TemplateField, values: dict[str, Any]
) -> None:
    if field.kind != "shopify_image" or not field.path:
        return
    oy_key = object_y_field_id(field.field_id)
    if oy_key not in values:
        return
    oy_path = object_y_path(field.path)
    if oy_path:
        path_set(template, oy_path, normalize_object_y(values[oy_key]))


def apply_zone_values(template: dict[str, Any], zone: TemplateZone, values: dict[str, Any]) -> None:
    set_zone_enabled(template, zone, bool(values.get("_enabled", True)))
    _apply_text_fields(template, zone, values)
    for fld in zone.fields:
        if fld.field_id not in values:
            continue
        if fld.kind in ("heading", "body", "theme_asset"):
            continue
        write_field(template, fld, values[fld.field_id])
        _write_image_object_y(template, fld, values)


def apply_all_zone_values(
    template: dict[str, Any],
    zones: tuple[TemplateZone, ...],
    all_values: dict[str, dict[str, Any]],
) -> None:
    for zone in zones:
        vals = all_values.get(zone.zone_id)
        if vals is not None:
            apply_zone_values(template, zone, vals)


def validate_template_paths(
    template: dict[str, Any], zones: tuple[TemplateZone, ...], *, logger: Logger | None = None
) -> list[str]:
    missing: list[str] = []
    for zone in zones:
        if zone.settings_only:
            continue
        for fld in zone.fields:
            if fld.kind in ("heading", "body", "theme_asset"):
                continue
            if fld.kind == "blocks_visible":
                for block_path in fld.block_paths:
                    if _block_at(template, block_path) is None:
                        missing.append(f"{zone.label} → {fld.label}")
                continue
            if not fld.path:
                continue
            if path_get(template, fld.path) is None:
                missing.append(f"{zone.label} → {fld.label}")
    if missing and logger:
        _log(logger, f"Brak {len(missing)} pól w szablonie.")
    return missing


def preview_url(config: PageEditorConfig) -> str:
    base = "https://gicleeart.eu"
    path = config.preview_path if config.preview_path.startswith("/") else f"/{config.preview_path}"
    q = config.preview_query.strip("&?")
    if q:
        return f"{base}{path}?{q}"
    return f"{base}{path}"


def upload_image(local_path: Path, *, logger: Logger | None = None) -> str:
    return upload_shopify_image(local_path, logger=logger)


def upload_video(local_path: Path, *, logger: Logger | None = None) -> str:
    ref = upload_shopify_video(local_path, logger=logger)
    return normalize_shopify_video_ref(ref, logger=logger)


def normalize_video_ref(ref: str, *, logger: Logger | None = None) -> str:
    return normalize_shopify_video_ref(ref, logger=logger)


__all__ = [
    "INDEX_HEADER",
    "apply_all_zone_values",
    "apply_zone_values",
    "backup_before_save",
    "backup_file",
    "backup_write_dir_for",
    "backups_dir_for",
    "component_data_dir",
    "deploy_theme",
    "fetch_thumbnail_bytes",
    "load_template",
    "load_template_from_path",
    "load_zone_values",
    "normalize_video_ref",
    "preview_url",
    "save_template",
    "save_template_to_path",
    "shopify_ref_label",
    "template_path_for_config",
    "upload_image",
    "upload_video",
    "validate_template_paths",
    "variants_root_for",
]
