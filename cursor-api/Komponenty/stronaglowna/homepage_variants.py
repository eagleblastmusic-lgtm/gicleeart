"""Warianty strony głównej — osobne kopie index.json + ustawień."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

from .home_features import write_home_assets
from .service import (
    INDEX_HEADER,
    SETTINGS_HEADER,
    _data_dir,
    _strip_json_header,
    load_index_template,
    load_theme_settings,
    mobile_hero_path,
    save_index_template,
    save_theme_settings,
)

VARIANTS_ROOT = _data_dir() / "variants"
MANIFEST_PATH = VARIANTS_ROOT / "manifest.json"

DEFAULT_VARIANTS: tuple[dict[str, str], ...] = (
    {"id": "home1", "label": "Strona Główna 1"},
    {"id": "home2", "label": "Strona Główna 2"},
)


def _variant_dir(variant_id: str) -> Path:
    return VARIANTS_ROOT / variant_id


def _load_json_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(_strip_json_header(raw))
    if not isinstance(data, dict):
        raise ValueError(f"Nieprawidłowy JSON: {path}")
    return data


def _save_json_file(path: Path, data: dict[str, Any], *, header: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(header + body, encoding="utf-8")


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        return {"active": "home1", "variants": list(DEFAULT_VARIANTS)}
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest.json — nieprawidłowy format.")
    variants = data.get("variants")
    if not isinstance(variants, list) or not variants:
        data["variants"] = list(DEFAULT_VARIANTS)
    if not str(data.get("active") or "").strip():
        data["active"] = str(data["variants"][0]["id"])
    return data


def save_manifest(manifest: dict[str, Any]) -> None:
    VARIANTS_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_variants() -> list[dict[str, str]]:
    manifest = load_manifest()
    out: list[dict[str, str]] = []
    for row in manifest.get("variants") or []:
        if isinstance(row, dict) and row.get("id") and row.get("label"):
            out.append({"id": str(row["id"]), "label": str(row["label"])})
    return out or [{"id": "home1", "label": "Strona Główna 1"}]


def active_variant_id() -> str:
    return str(load_manifest().get("active") or "home1")


def set_active_variant(variant_id: str) -> None:
    manifest = load_manifest()
    known = {v["id"] for v in list_variants()}
    if variant_id not in known:
        raise ValueError(f"Nieznany wariant: {variant_id}")
    manifest["active"] = variant_id
    save_manifest(manifest)


def variant_label(variant_id: str) -> str:
    for row in list_variants():
        if row["id"] == variant_id:
            return row["label"]
    return variant_id


def save_variant_data(
    variant_id: str,
    template: dict[str, Any],
    settings: dict[str, Any],
    *,
    copy_mobile_from_theme: bool = True,
) -> None:
    root = _variant_dir(variant_id)
    root.mkdir(parents=True, exist_ok=True)
    _save_json_file(root / "index.json", template, header=INDEX_HEADER)
    _save_json_file(root / "settings.json", settings, header=SETTINGS_HEADER)
    mobile_dest = root / "mobile_hero.webp"
    if copy_mobile_from_theme:
        src = mobile_hero_path()
        if src.is_file():
            shutil.copy2(src, mobile_dest)
        elif not mobile_dest.is_file():
            mobile_dest.unlink(missing_ok=True)


def load_variant_data(variant_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    root = _variant_dir(variant_id)
    index_path = root / "index.json"
    settings_path = root / "settings.json"
    if not index_path.is_file() or not settings_path.is_file():
        raise FileNotFoundError(f"Brak danych wariantu «{variant_label(variant_id)}».")
    template, settings = _load_json_file(index_path), _load_json_file(settings_path)
    return copy.deepcopy(template), copy.deepcopy(settings)


def load_variant_into_editor(variant_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return load_variant_data(variant_id)


def _hero_field_path(field_id: str) -> tuple[str, ...] | None:
    from .registry import zone_by_id

    hero = zone_by_id("hero")
    if not hero:
        return None
    fld = next((f for f in hero.fields if f.field_id == field_id), None)
    return fld.path if fld else None


def repair_cloned_boomerang_loop(source_id: str, target_id: str) -> bool:
    """Uzupełnia brakującą pętlę boomerang w klona (ten sam film bazowy co w źródle)."""
    from .service import path_get, path_set

    p_forward = _hero_field_path("hero_desktop_video")
    p_boom = _hero_field_path("hero_video_boomerang")
    p_loop = _hero_field_path("hero_desktop_video_reversed")
    if not p_forward or not p_boom or not p_loop:
        return False

    target_file = _variant_dir(target_id) / "index.json"
    source_file = _variant_dir(source_id) / "index.json"
    if not target_file.is_file() or not source_file.is_file():
        return False

    target_t = _load_json_file(target_file)
    source_t = _load_json_file(source_file)

    forward = str(path_get(target_t, p_forward) or "").strip()
    source_forward = str(path_get(source_t, p_forward) or "").strip()
    loop = str(path_get(target_t, p_loop) or "").strip()
    source_loop = str(path_get(source_t, p_loop) or "").strip()
    boomerang = bool(path_get(target_t, p_boom))

    if not forward or forward != source_forward or not boomerang or loop or not source_loop:
        return False

    path_set(target_t, p_loop, source_loop)
    _save_json_file(target_file, target_t, header=INDEX_HEADER)
    return True


def duplicate_variant(source_id: str, target_id: str, *, label: str) -> None:
    src = _variant_dir(source_id)
    dst = _variant_dir(target_id)
    if dst.exists():
        shutil.rmtree(dst)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        template, settings = load_index_template(), load_theme_settings()
        save_variant_data(target_id, template, settings)

    manifest = load_manifest()
    variants = manifest.setdefault("variants", [])
    if not any(v.get("id") == target_id for v in variants if isinstance(v, dict)):
        variants.append({"id": target_id, "label": label})
    save_manifest(manifest)


def ensure_variants_initialized() -> dict[str, Any]:
    """Pierwsze uruchomienie: home1 z motywu, home2 jako kopia home1."""
    if MANIFEST_PATH.is_file() and _variant_dir("home1").is_dir() and _variant_dir("home2").is_dir():
        repair_cloned_boomerang_loop("home1", "home2")
        return load_manifest()

    VARIANTS_ROOT.mkdir(parents=True, exist_ok=True)
    template = load_index_template()
    settings = load_theme_settings()
    save_variant_data("home1", template, settings)
    duplicate_variant("home1", "home2", label="Strona Główna 2")

    manifest = {"active": "home1", "variants": list(DEFAULT_VARIANTS)}
    save_manifest(manifest)
    return manifest


def apply_variant_to_theme(variant_id: str) -> None:
    """Zapisuje wariant do plików motywu (podgląd / theme dev)."""
    template, settings = load_variant_data(variant_id)
    save_index_template(copy.deepcopy(template))
    save_theme_settings(copy.deepcopy(settings))
    mobile_src = _variant_dir(variant_id) / "mobile_hero.webp"
    if mobile_src.is_file():
        shutil.copy2(mobile_src, mobile_hero_path())
    mobile_name = mobile_hero_path().name if mobile_hero_path().is_file() else None
    write_home_assets(template, mobile_slide_urls=[mobile_name] if mobile_name else None)


def persist_editor_to_variant(
    variant_id: str,
    template: dict[str, Any],
    settings: dict[str, Any],
) -> None:
    save_variant_data(
        variant_id,
        copy.deepcopy(template),
        copy.deepcopy(settings),
        copy_mobile_from_theme=True,
    )
