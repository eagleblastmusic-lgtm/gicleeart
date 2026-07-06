"""Katalog F1 — read-only inventory. Bounded paths only; no Komponenty imports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

KATALOG_FOLDER = "katalog"
TLDOBIO_FOLDER = "tldobio"

KATALOG_COMPONENT_JSON = "component.json"
KATALOG_REGISTRY_PY = "registry.py"
KATALOG_MANIFEST = "data/variants/manifest.json"
KATALOG_VARIANT_COLLECTION = "collection.json"
TLDOBIO_COLLECTIONS_JSON = "data/collections.json"

TLDOBIO_ABSORBED_STATUS = "tldobio absorbed into katalog"

DATA_MAP_WARNING = (
    "Legacy Katalog (template JSON / background_image) and tldobio (Shopify metafields per "
    "collection) use different persistence — no writer before bounded data map."
)

F1_READ_ONLY_NOTE = (
    "F1 read-only shell — no Save, no writer, no Shopify, no upload, no deploy/sync."
)

NEXT_PHASE_NOTE = "Next: F3 local draft / dry-run (F2 data map in katalog_data_map.py)"

_MAX_VARIANT_IDS = 64
_ZONE_ID_RE = re.compile(r'zone_id="([^"]+)"')


@dataclass(frozen=True)
class KatalogSideInventory:
    root_exists: bool
    component_json_exists: bool
    registry_py_exists: bool
    manifest_exists: bool
    active_variant_id: str | None
    variant_ids: tuple[str, ...]
    variant_labels: dict[str, str]
    collection_json_by_variant: dict[str, bool]
    registry_zone_ids: tuple[str, ...]


@dataclass(frozen=True)
class TldobioSideInventory:
    root_exists: bool
    collections_json_exists: bool
    cache_version: int | None
    background_count: int
    backgrounds_with_url: int
    absorbed_status: str = TLDOBIO_ABSORBED_STATUS


@dataclass(frozen=True)
class KatalogInventoryReport:
    components_root: Path
    katalog: KatalogSideInventory
    tldobio: TldobioSideInventory
    warnings: tuple[str, ...] = field(
        default_factory=lambda: (DATA_MAP_WARNING, F1_READ_ONLY_NOTE, NEXT_PHASE_NOTE),
    )


def _read_manifest_variants(manifest_path: Path) -> tuple[str | None, tuple[str, ...], dict[str, str]]:
    if not manifest_path.is_file():
        return None, (), {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None, (), {}
    if not isinstance(data, dict):
        return None, (), {}
    active = data.get("active")
    active_id = str(active).strip() if active else None
    variants_raw = data.get("variants")
    if not isinstance(variants_raw, list):
        return active_id, (), {}
    ids: list[str] = []
    labels: dict[str, str] = {}
    for row in variants_raw[:_MAX_VARIANT_IDS]:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("id") or "").strip()
        if not vid:
            continue
        ids.append(vid)
        label = str(row.get("label") or vid).strip()
        labels[vid] = label
    return active_id, tuple(ids), labels


def _registry_zone_ids(registry_path: Path) -> tuple[str, ...]:
    if not registry_path.is_file():
        return ()
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError:
        return ()
    return tuple(_ZONE_ID_RE.findall(text))


def _tldobio_cache_stats(collections_path: Path) -> tuple[int | None, int, int]:
    if not collections_path.is_file():
        return None, 0, 0
    try:
        data = json.loads(collections_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None, 0, 0
    if not isinstance(data, dict):
        return None, 0, 0
    version_raw = data.get("version")
    version = int(version_raw) if isinstance(version_raw, int) else None
    backgrounds = data.get("backgrounds")
    if not isinstance(backgrounds, dict):
        return version, 0, 0
    total = len(backgrounds)
    with_url = 0
    for row in backgrounds.values():
        if not isinstance(row, dict):
            continue
        if str(row.get("url") or "").strip():
            with_url += 1
    return version, total, with_url


def build_katalog_inventory(components_root: Path) -> KatalogInventoryReport:
    """Read-only inventory from bounded paths under ``components_root``."""
    root = Path(components_root)
    katalog_root = root / KATALOG_FOLDER
    tldobio_root = root / TLDOBIO_FOLDER

    manifest_path = katalog_root / KATALOG_MANIFEST
    active_id, variant_ids, variant_labels = _read_manifest_variants(manifest_path)

    collection_by_variant: dict[str, bool] = {}
    for vid in variant_ids:
        coll_path = katalog_root / "data" / "variants" / vid / KATALOG_VARIANT_COLLECTION
        collection_by_variant[vid] = coll_path.is_file()

    katalog_side = KatalogSideInventory(
        root_exists=katalog_root.is_dir(),
        component_json_exists=(katalog_root / KATALOG_COMPONENT_JSON).is_file(),
        registry_py_exists=(katalog_root / KATALOG_REGISTRY_PY).is_file(),
        manifest_exists=manifest_path.is_file(),
        active_variant_id=active_id,
        variant_ids=variant_ids,
        variant_labels=variant_labels,
        collection_json_by_variant=collection_by_variant,
        registry_zone_ids=_registry_zone_ids(katalog_root / KATALOG_REGISTRY_PY),
    )

    collections_path = tldobio_root / TLDOBIO_COLLECTIONS_JSON
    cache_version, bg_count, bg_with_url = _tldobio_cache_stats(collections_path)

    tldobio_side = TldobioSideInventory(
        root_exists=tldobio_root.is_dir(),
        collections_json_exists=collections_path.is_file(),
        cache_version=cache_version,
        background_count=bg_count,
        backgrounds_with_url=bg_with_url,
    )

    return KatalogInventoryReport(
        components_root=root,
        katalog=katalog_side,
        tldobio=tldobio_side,
    )


def inventory_display_rows(report: KatalogInventoryReport) -> list[tuple[str, str]]:
    """Flat label/value rows for UI and tests — no Tk."""
    k = report.katalog
    t = report.tldobio
    rows: list[tuple[str, str]] = [
        ("Status", "Read-only · Katalog rebuild F1"),
        ("Role", "Parent workflow"),
        ("Tło do Bio", f"{TLDOBIO_ABSORBED_STATUS} · subflow (not standalone tile)"),
        ("Komponenty/katalog", "present" if k.root_exists else "missing"),
        ("katalog/component.json", "present" if k.component_json_exists else "missing"),
        ("katalog/registry.py", "present" if k.registry_py_exists else "missing"),
        ("katalog/data/variants/manifest.json", "present" if k.manifest_exists else "missing"),
    ]
    if k.active_variant_id:
        rows.append(("Active variant", k.active_variant_id))
    if k.variant_ids:
        rows.append(("Variants", ", ".join(k.variant_ids)))
    for vid in k.variant_ids:
        label = k.variant_labels.get(vid, vid)
        has_coll = k.collection_json_by_variant.get(vid, False)
        rows.append((
            f"  {vid} ({label})",
            "collection.json present" if has_coll else "collection.json missing",
        ))
    if k.registry_zone_ids:
        rows.append(("Registry zones", ", ".join(k.registry_zone_ids)))
    rows.extend([
        ("Komponenty/tldobio", "present" if t.root_exists else "missing"),
        ("tldobio/data/collections.json", "present" if t.collections_json_exists else "missing"),
    ])
    if t.cache_version is not None:
        rows.append(("tldobio cache version", str(t.cache_version)))
    if t.collections_json_exists:
        rows.append((
            "tldobio backgrounds (cache)",
            f"{t.background_count} entries · {t.backgrounds_with_url} with URL",
        ))
    return rows


def workflow_summary() -> str:
    return (
        "Studio v2 parent workflow for catalog pages, structure, and absorbed Tło do Bio subflow."
    )


def status_strip() -> str:
    return "Read-only · F1+F2 · no Save · no writer · no Shopify"
