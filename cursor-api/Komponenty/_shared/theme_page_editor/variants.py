"""Warianty szablonów stron menu — manifest + kopia bieżącego."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .config import PageEditorConfig
from .service_base import (
    INDEX_HEADER,
    load_template_from_path,
    save_template_to_path,
    template_path_for_config,
    variants_root_for,
)

_VARIANT_NUM_RE = re.compile(r"^(\w+?)(\d+)$")


def manifest_path(config: PageEditorConfig) -> Path:
    return variants_root_for(config) / "manifest.json"


def _variant_dir(config: PageEditorConfig, variant_id: str) -> Path:
    return variants_root_for(config) / variant_id


def _template_variant_path(config: PageEditorConfig, variant_id: str) -> Path:
    return _variant_dir(config, variant_id) / config.template_basename


def _strip_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def _load_json_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(_strip_json_header(raw))
    if not isinstance(data, dict):
        raise ValueError(f"Nieprawidłowy JSON: {path}")
    return data


def _save_json_file(path: Path, data: dict[str, Any], *, header: str = INDEX_HEADER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(header + body, encoding="utf-8")


def _default_variant_id(config: PageEditorConfig) -> str:
    return f"{config.variant_id_prefix}1"


def load_manifest(config: PageEditorConfig) -> dict[str, Any]:
    path = manifest_path(config)
    default_id = _default_variant_id(config)
    if not path.is_file():
        return {
            "active": default_id,
            "variants": [{"id": default_id, "label": config.variant_label_default}],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest.json — nieprawidłowy format.")
    variants = data.get("variants")
    if not isinstance(variants, list) or not variants:
        data["variants"] = [{"id": default_id, "label": config.variant_label_default}]
    if not data.get("active"):
        data["active"] = default_id
    return data


def save_manifest(config: PageEditorConfig, manifest: dict[str, Any]) -> None:
    path = manifest_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_variants(config: PageEditorConfig) -> list[dict[str, str]]:
    manifest = load_manifest(config)
    out: list[dict[str, str]] = []
    for row in manifest.get("variants") or []:
        if isinstance(row, dict) and row.get("id"):
            out.append({"id": str(row["id"]), "label": str(row.get("label") or row["id"])})
    return out


def active_variant_id(config: PageEditorConfig) -> str:
    return str(load_manifest(config).get("active") or _default_variant_id(config))


def set_active_variant(config: PageEditorConfig, variant_id: str) -> None:
    manifest = load_manifest(config)
    known = {v["id"] for v in list_variants(config)}
    if variant_id not in known:
        raise ValueError(f"Nieznany wariant: {variant_id}")
    manifest["active"] = variant_id
    save_manifest(config, manifest)


def variant_label(config: PageEditorConfig, variant_id: str) -> str:
    for row in list_variants(config):
        if row["id"] == variant_id:
            return row["label"]
    return variant_id


def _existing_labels(config: PageEditorConfig) -> set[str]:
    return {v["label"] for v in list_variants(config)}


def _validate_label(label: str, *, exclude_id: str | None = None, config: PageEditorConfig) -> str:
    clean = (label or "").strip()
    if not clean:
        raise ValueError("Etykieta wariantu nie może być pusta.")
    for row in list_variants(config):
        if exclude_id and row["id"] == exclude_id:
            continue
        if row["label"].casefold() == clean.casefold():
            raise ValueError(f"Wariant «{clean}» już istnieje.")
    return clean


def _unique_label(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    n = 2
    while f"{base} ({n})" in taken:
        n += 1
    return f"{base} ({n})"


def next_variant_id(config: PageEditorConfig) -> str:
    prefix = config.variant_id_prefix
    nums: list[int] = []
    for row in list_variants(config):
        m = _VARIANT_NUM_RE.match(row["id"])
        if m and m.group(1) == prefix:
            nums.append(int(m.group(2)))
    return f"{prefix}{(max(nums) + 1) if nums else 2}"


def suggest_variant_label(config: PageEditorConfig, source_id: str) -> str:
    base = f"Kopia {variant_label(config, source_id)}"
    return _unique_label(base, _existing_labels(config))


def save_variant_data(config: PageEditorConfig, variant_id: str, template: dict[str, Any]) -> None:
    _save_json_file(_template_variant_path(config, variant_id), template)


def load_variant_data(config: PageEditorConfig, variant_id: str) -> dict[str, Any]:
    path = _template_variant_path(config, variant_id)
    if path.is_file():
        return _load_json_file(path)
    theme_path = template_path_for_config(config)
    if theme_path.is_file():
        return load_template_from_path(theme_path)
    raise FileNotFoundError(f"Brak danych wariantu {variant_id}")


def ensure_variants_initialized(config: PageEditorConfig) -> None:
    root = variants_root_for(config)
    root.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(config)
    save_manifest(config, manifest)
    for row in manifest.get("variants") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        vid = str(row["id"])
        vpath = _template_variant_path(config, vid)
        if not vpath.is_file():
            theme_path = template_path_for_config(config)
            if theme_path.is_file():
                vpath.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(theme_path, vpath)
            else:
                save_variant_data(config, vid, {"sections": {}, "order": []})


def load_variant_into_editor(config: PageEditorConfig, variant_id: str) -> dict[str, Any]:
    return copy.deepcopy(load_variant_data(config, variant_id))


def persist_editor_to_variant(
    config: PageEditorConfig, variant_id: str, template: dict[str, Any]
) -> None:
    save_variant_data(config, variant_id, template)


def apply_variant_to_theme(config: PageEditorConfig, variant_id: str) -> None:
    data = load_variant_data(config, variant_id)
    save_template_to_path(template_path_for_config(config), data)


def duplicate_variant(
    config: PageEditorConfig, source_id: str, target_id: str, *, label: str
) -> None:
    src = _variant_dir(config, source_id)
    dst = _variant_dir(config, target_id)
    if dst.exists():
        shutil.rmtree(dst)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        data = load_variant_data(config, source_id)
        save_variant_data(config, target_id, data)

    manifest = load_manifest(config)
    variants = manifest.setdefault("variants", [])
    if not any(v.get("id") == target_id for v in variants if isinstance(v, dict)):
        variants.append({"id": target_id, "label": label})
    save_manifest(config, manifest)


def create_variant_copy(config: PageEditorConfig, source_id: str, label: str) -> str:
    label = _validate_label(label, config=config)
    known = {v["id"] for v in list_variants(config)}
    if source_id not in known:
        raise ValueError(f"Nieznany wariant: {source_id}")
    target_id = next_variant_id(config)
    duplicate_variant(config, source_id, target_id, label=label)
    return target_id


def rename_variant_label(config: PageEditorConfig, variant_id: str, label: str) -> None:
    label = _validate_label(label, exclude_id=variant_id, config=config)
    manifest = load_manifest(config)
    for row in manifest.get("variants") or []:
        if isinstance(row, dict) and row.get("id") == variant_id:
            row["label"] = label
            save_manifest(config, manifest)
            return
    raise ValueError(f"Nieznany wariant: {variant_id}")
