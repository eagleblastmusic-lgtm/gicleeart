"""Warianty strony głównej — osobne kopie index.json + ustawień."""

from __future__ import annotations

import copy
import json
import re
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
    {"id": "home3", "label": "Strona Główna 3"},
    {"id": "home4", "label": "Strona Główna 4"},
)

STACK_VARIANT_IDS = frozenset({"home3", "home4"})
_VARIANT_ID_RE = re.compile(r"^home(\d+)$")


def _variant_meta(variant_id: str) -> dict[str, Any] | None:
    manifest = load_manifest()
    for row in manifest.get("variants") or []:
        if isinstance(row, dict) and str(row.get("id")) == variant_id:
            return row
    return None


def _migrate_manifest_home_stack(manifest: dict[str, Any]) -> bool:
    changed = False
    for row in manifest.get("variants") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        if row["id"] in STACK_VARIANT_IDS and "home_stack" not in row:
            row["home_stack"] = True
            changed = True
    return changed


def variant_uses_home_stack(variant_id: str) -> bool:
    meta = _variant_meta(variant_id)
    if meta and "home_stack" in meta:
        return bool(meta["home_stack"])
    return variant_id in STACK_VARIANT_IDS


def set_variant_home_stack(variant_id: str, enabled: bool) -> None:
    manifest = load_manifest()
    for row in manifest.get("variants") or []:
        if isinstance(row, dict) and row.get("id") == variant_id:
            row["home_stack"] = bool(enabled)
            save_manifest(manifest)
            return
    raise ValueError(f"Nieznany wariant: {variant_id}")


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
    if _migrate_manifest_home_stack(data):
        save_manifest(data)
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
    from .service import repair_color_correction_cta_blocks

    repair_color_correction_cta_blocks(template)
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


def _existing_labels(*, exclude_id: str | None = None) -> set[str]:
    out: set[str] = set()
    for row in list_variants():
        if exclude_id and row["id"] == exclude_id:
            continue
        out.add(row["label"].lower())
    return out


def _validate_label(label: str, *, exclude_id: str | None = None) -> str:
    normalized = label.strip()
    if not normalized:
        raise ValueError("Podaj nazwę wersji.")
    if normalized.lower() in _existing_labels(exclude_id=exclude_id):
        raise ValueError(f"Wersja o nazwie «{normalized}» już istnieje.")
    return normalized


def _unique_label(base: str, existing: set[str]) -> str:
    if base.lower() not in existing:
        return base
    n = 2
    while f"{base} ({n})".lower() in existing:
        n += 1
    return f"{base} ({n})"


def next_variant_id() -> str:
    max_n = 0
    for row in list_variants():
        match = _VARIANT_ID_RE.match(row["id"])
        if match:
            max_n = max(max_n, int(match.group(1)))
    if VARIANTS_ROOT.is_dir():
        for child in VARIANTS_ROOT.iterdir():
            if child.is_dir():
                match = _VARIANT_ID_RE.match(child.name)
                if match:
                    max_n = max(max_n, int(match.group(1)))
    return f"home{max_n + 1}"


def suggest_variant_label(source_id: str) -> str:
    base = f"Kopia {variant_label(source_id)}"
    return _unique_label(base, _existing_labels())


def create_variant_copy(source_id: str, label: str) -> str:
    label = _validate_label(label)
    known = {v["id"] for v in list_variants()}
    if source_id not in known:
        raise ValueError(f"Nieznany wariant: {source_id}")
    stack = variant_uses_home_stack(source_id)
    target_id = next_variant_id()
    duplicate_variant(source_id, target_id, label=label)
    manifest = load_manifest()
    for row in manifest.get("variants") or []:
        if isinstance(row, dict) and row.get("id") == target_id:
            row["home_stack"] = stack
            break
    save_manifest(manifest)
    repair_cloned_boomerang_loop(source_id, target_id)
    return target_id


def rename_variant_label(variant_id: str, label: str) -> None:
    label = _validate_label(label, exclude_id=variant_id)
    manifest = load_manifest()
    for row in manifest.get("variants") or []:
        if isinstance(row, dict) and row.get("id") == variant_id:
            row["label"] = label
            save_manifest(manifest)
            return
    raise ValueError(f"Nieznany wariant: {variant_id}")


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
        if _variant_dir("home3").is_dir():
            repair_cloned_boomerang_loop("home2", "home3")
        if _variant_dir("home4").is_dir():
            repair_cloned_boomerang_loop("home3", "home4")
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
    from .scroll_settings import load_scroll_config

    write_home_assets(
        template,
        mobile_slide_urls=[mobile_name] if mobile_name else None,
        stack_enabled=variant_uses_home_stack(variant_id),
        scroll_config=load_scroll_config(variant_id),
    )


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
