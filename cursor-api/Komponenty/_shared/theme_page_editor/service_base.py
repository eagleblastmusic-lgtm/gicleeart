"""I/O szablonów motywu, pola JSON, backup — delegacja deploy do stronaglowna."""

from __future__ import annotations

import copy
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
from .image_object_x import normalize_object_x, object_x_field_id, object_x_path
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


def backup_variant_bundle(
    config: PageEditorConfig,
    variant_id: str,
    *,
    logger: Logger | None = None,
) -> list[Path]:
    """Jedna pozycja historii: szablon wariantu i jego text-layers.json."""

    variant = str(variant_id or "").strip()
    if not variant:
        return []
    variant_dir = variants_root_for(config) / variant
    template_source = variant_dir / config.template_basename
    if not template_source.is_file():
        template_source = template_path_for_config(config)
    text_source = variant_dir / "text-layers.json"
    template_data = template_source.read_bytes() if template_source.is_file() else b"{}\n"
    text_data = (
        text_source.read_bytes()
        if text_source.is_file()
        else b'{\n  "schemaVersion": 1,\n  "sections": {}\n}\n'
    )
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = backup_write_dir_for(config)
    template_backup = (
        backup_dir
        / f"variant-{variant}-{Path(config.template_basename).stem}-{ts}.json"
    )
    text_backup = backup_dir / f"variant-{variant}-text-layers-{ts}.json"
    created: list[Path] = []
    try:
        atomic_write_bytes(template_backup, template_data)
        created.append(template_backup)
        atomic_write_bytes(text_backup, text_data)
        created.append(text_backup)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    _log(
        logger,
        f"Kopia wariantu {variant}: {template_backup.name} + {text_backup.name}",
    )
    return created


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
            n = int(round(float(value)))
        except (TypeError, ValueError):
            n = 0
        if field.min_value is not None:
            n = max(int(field.min_value), n)
        if field.max_value is not None:
            n = min(int(field.max_value), n)
        path_set(template, field.path, n)
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
            ox_path = object_x_path(fld.path)
            if ox_path:
                out[object_x_field_id(fld.field_id)] = normalize_object_x(path_get(template, ox_path))
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


def _write_image_object_x(
    template: dict[str, Any], field: TemplateField, values: dict[str, Any]
) -> None:
    if field.kind != "shopify_image" or not field.path:
        return
    ox_key = object_x_field_id(field.field_id)
    if ox_key not in values:
        return
    ox_path = object_x_path(field.path)
    if ox_path:
        path_set(template, ox_path, normalize_object_x(values[ox_key]))


def _sync_under_hero_bg(
    template: dict[str, Any], zone: TemplateZone, values: dict[str, Any]
) -> None:
    """Przy gradiencie czyści media tła; przy grafice zostawia section_background.

    Prefiks ustawień i klucz sekcji biorą się ze ścieżki pola ``under_hero_bg_mode``
    (FAQ: ``giclee_faq_bg_*`` / Kontakt: ``giclee_contact_bg_*``).
    """
    mode_fld = next((f for f in zone.fields if f.field_id == "under_hero_bg_mode"), None)
    if mode_fld is None or not mode_fld.path or len(mode_fld.path) < 2:
        return

    mode_key = str(mode_fld.path[-1])
    if not mode_key.endswith("_mode"):
        return
    prefix = mode_key[: -len("_mode")]
    settings = tuple(mode_fld.path[:-1])
    gradient_key = f"{prefix}_gradient"

    mode = str(values.get("under_hero_bg_mode") or "").strip().lower()
    gradient = str(values.get("under_hero_gradient") or "v1").strip().lower()
    if gradient not in ("v1", "v2"):
        gradient = "v1"

    if mode == "gradient":
        path_set(template, (*settings, mode_key), "gradient")
        path_set(template, (*settings, gradient_key), gradient)
        from Komponenty.stronaglowna.registry import HomeField
        from Komponenty.stronaglowna.service import _write_section_background

        _write_section_background(
            template,
            HomeField(
                "under_hero_background",
                "Tło sekcji",
                "section_background",
                (*settings, "background_image"),
            ),
            {"media": "none", "ref": "", "overlay_pct": 0},
        )
    elif mode == "image":
        path_set(template, (*settings, mode_key), "image")
        path_set(template, (*settings, gradient_key), gradient)
    else:
        path_set(template, (*settings, mode_key), "none")


def apply_zone_values(template: dict[str, Any], zone: TemplateZone, values: dict[str, Any]) -> None:
    set_zone_enabled(template, zone, bool(values.get("_enabled", True)))
    _apply_text_fields(template, zone, values)
    for fld in zone.fields:
        if fld.field_id not in values:
            continue
        if fld.kind in ("heading", "body", "theme_asset"):
            continue
        # Gradient czyści media — pomiń zapis grafiki, zrobi to sync.
        if zone.zone_id == "under_hero_bg" and fld.kind == "section_background":
            if str(values.get("under_hero_bg_mode") or "").strip().lower() == "gradient":
                continue
        write_field(template, fld, values[fld.field_id])
        _write_image_object_y(template, fld, values)
        _write_image_object_x(template, fld, values)
    if zone.zone_id == "under_hero_bg":
        _sync_under_hero_bg(template, zone, values)


def apply_all_zone_values(
    template: dict[str, Any],
    zones: tuple[TemplateZone, ...],
    all_values: dict[str, dict[str, Any]],
) -> None:
    for zone in zones:
        vals = all_values.get(zone.zone_id)
        if vals is not None:
            apply_zone_values(template, zone, vals)


def merge_managed_zone_values(
    config: PageEditorConfig,
    current_template: dict[str, Any],
    editor_template: dict[str, Any],
) -> dict[str, Any]:
    """Nałóż pola komponentu na świeży plik, zachowując pozostałą zawartość."""

    merged = copy.deepcopy(current_template)
    editor_sections = editor_template.get("sections")
    merged_sections = merged.get("sections")
    editor_order = editor_template.get("order")
    merged_order = merged.get("order")
    for zone in config.zones:
        if not zone.settings_only:
            if not isinstance(editor_sections, dict):
                continue
            if not isinstance(editor_sections.get(zone.section_key), dict):
                continue
            if isinstance(merged_sections, dict) and not isinstance(
                merged_sections.get(zone.section_key),
                dict,
            ):
                # Sekcja dodana w GicleeApp musi trafić do motywu jako cały
                # obiekt (type/blocks/settings), nie tylko jako zestaw pól.
                merged_sections[zone.section_key] = copy.deepcopy(
                    editor_sections[zone.section_key]
                )
                if (
                    isinstance(editor_order, list)
                    and isinstance(merged_order, list)
                    and zone.section_key in editor_order
                    and zone.section_key not in merged_order
                ):
                    editor_index = editor_order.index(zone.section_key)
                    previous = next(
                        (
                            key
                            for key in reversed(editor_order[:editor_index])
                            if key in merged_order
                        ),
                        None,
                    )
                    if previous is None:
                        merged_order.insert(0, zone.section_key)
                    else:
                        merged_order.insert(
                            merged_order.index(previous) + 1,
                            zone.section_key,
                        )
        apply_zone_values(merged, zone, load_zone_values(editor_template, zone))

    # Puste ekrany są w całości zarządzane przez moduł. Brak ekranu w
    # edytowanym wariancie oznacza świadome usunięcie, więc nie wolno
    # przywracać go ze świeżego pliku motywu podczas bezpiecznego merge.
    if (
        isinstance(editor_sections, dict)
        and isinstance(merged_sections, dict)
        and isinstance(merged_order, list)
    ):
        from .viewport_screen import is_viewport_screen_section

        editor_screen_keys = {
            str(key)
            for key, section in editor_sections.items()
            if is_viewport_screen_section(section)
        }
        current_screen_keys = {
            str(key)
            for key, section in tuple(merged_sections.items())
            if is_viewport_screen_section(section)
        }
        for section_key in current_screen_keys - editor_screen_keys:
            merged_sections.pop(section_key, None)
        for section_key in editor_screen_keys:
            merged_sections[section_key] = copy.deepcopy(
                editor_sections[section_key]
            )

        # Odtwórz pozycje ekranów według wariantu, pozostawiając kolejność
        # wszystkich pozostałych sekcji świeżego motywu bez zmian.
        all_screen_keys = current_screen_keys | editor_screen_keys
        merged_order[:] = [
            key for key in merged_order if str(key) not in all_screen_keys
        ]
        if isinstance(editor_order, list):
            for editor_index, raw_key in enumerate(editor_order):
                section_key = str(raw_key)
                if section_key not in editor_screen_keys:
                    continue
                existing_order_keys = {str(item) for item in merged_order}
                previous = next(
                    (
                        str(key)
                        for key in reversed(editor_order[:editor_index])
                        if str(key) in existing_order_keys
                    ),
                    None,
                )
                if previous is None:
                    merged_order.insert(0, section_key)
                else:
                    previous_index = next(
                        index
                        for index, key in enumerate(merged_order)
                        if str(key) == previous
                    )
                    merged_order.insert(previous_index + 1, section_key)
    return merged


def component_deploy_relpaths(config: PageEditorConfig) -> tuple[str, ...]:
    """Jawna lista plików motywu należących do jednego edytora strony."""

    paths = [config.template_rel.replace("\\", "/")]
    if config.section_effects_asset_enabled:
        from .page_section_effects_settings import effects_asset_basename

        paths.append(f"assets/{effects_asset_basename(config)}")
    paths.extend(path.replace("\\", "/") for path in config.extra_deploy_relpaths)
    root = theme_root()
    for pattern in config.extra_deploy_globs:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                paths.append(path.relative_to(root).as_posix())

    try:
        template = load_template(config)
    except (FileNotFoundError, OSError, ValueError):
        template = {}
    if isinstance(template.get("sections"), dict) and isinstance(
        template.get("order"), list
    ):
        from .text_layers_export import RUNTIME_RELPATHS, asset_basename

        paths.extend(RUNTIME_RELPATHS)
        paths.append(f"assets/{asset_basename(config)}")

    from .film_scroll import (
        FILM_SCROLL_DEPLOY_RELPATHS,
        selected_film_scroll_asset_relpaths,
        template_has_film_scroll,
    )

    if template_has_film_scroll(template):
        paths.extend(FILM_SCROLL_DEPLOY_RELPATHS)
        paths.extend(selected_film_scroll_asset_relpaths(template))

    from .page_scroll import (
        PAGE_SCROLL_DEPLOY_RELPATHS,
        template_has_page_scroll,
    )

    if template_has_page_scroll(template):
        paths.extend(PAGE_SCROLL_DEPLOY_RELPATHS)

    from .viewport_screen import (
        VIEWPORT_SCREEN_DEPLOY_RELPATHS,
        template_has_viewport_screen,
    )

    if template_has_viewport_screen(template):
        paths.extend(VIEWPORT_SCREEN_DEPLOY_RELPATHS)

    if config.component_id == "filozofiamarki":
        from Komponenty.filozofiamarki.video_sequence import (
            active_scroll_video_deploy_relpaths,
            active_scroll_video_frame_globs,
            all_scroll_video_runtime_relpaths,
            sync_scroll_video_shopifyignore,
        )

        sync_scroll_video_shopifyignore(root)
        runtime = set(all_scroll_video_runtime_relpaths())
        paths = [path for path in paths if path not in runtime]
        paths.extend(active_scroll_video_deploy_relpaths(root))
        for pattern in active_scroll_video_frame_globs(root):
            for path in sorted(root.glob(pattern)):
                if path.is_file():
                    paths.append(path.relative_to(root).as_posix())

    return tuple(dict.fromkeys(paths))


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
    "component_deploy_relpaths",
    "backup_variant_bundle",
    "deploy_theme",
    "fetch_thumbnail_bytes",
    "load_template",
    "load_template_from_path",
    "load_zone_values",
    "merge_managed_zone_values",
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
