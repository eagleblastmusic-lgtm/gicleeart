"""Katalog F2 — bounded data map. Read-only; separates legacy katalog vs tldobio."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .katalog_inventory import (
    KATALOG_COMPONENT_JSON,
    KATALOG_FOLDER,
    KATALOG_MANIFEST,
    KATALOG_REGISTRY_PY,
    KATALOG_VARIANT_COLLECTION,
    TLDOBIO_COLLECTIONS_JSON,
    TLDOBIO_FOLDER,
)

RiskLevel = Literal["low", "medium", "high"]
WritePolicy = Literal["not_defined", "not_started", "planned", "out_of_scope"]

MAX_VARIANTS_PREVIEW = 10
MAX_TLDOBIO_COLLECTION_KEYS = 20
MAX_FILE_BYTES = 2 * 1024 * 1024

_ZONE_ID_RE = re.compile(r'zone_id="([^"]+)"')
_BACKGROUND_IMAGE_RE = re.compile(r"background_image", re.IGNORECASE)

F2_NEXT_NOTE = (
    "F3 local planning active — dry-run + readiness · writer F5+ not started"
)


@dataclass(frozen=True)
class DataMapWarning:
    code: str
    message: str


@dataclass(frozen=True)
class KatalogDataSource:
    source_id: str
    label: str
    exists: bool
    status: str
    risk: RiskLevel
    write_policy: WritePolicy
    note: str = ""


@dataclass(frozen=True)
class KatalogTemplateSummary:
    root_exists: bool
    component_json_exists: bool
    registry_py_exists: bool
    manifest_exists: bool
    variant_count: int
    sample_variants: tuple[str, ...]
    collection_json_count: int
    sample_collections: tuple[str, ...]
    registry_zone_ids: tuple[str, ...]
    has_background_image_refs: bool
    status: str = "legacy_template_json"
    risk: RiskLevel = "medium"
    write_policy: WritePolicy = "not_defined"


@dataclass(frozen=True)
class TldobioSummary:
    root_exists: bool
    collections_json_exists: bool
    collection_count: int
    sample_collection_keys: tuple[str, ...]
    backgrounds_with_url: int
    service_py_exists: bool
    shopify_integration_detected: bool
    metafield_refs_detected: bool
    status: str = "absorbed_cache_or_external_bridge"
    risk: RiskLevel = "high"
    write_policy: WritePolicy = "not_defined"


@dataclass(frozen=True)
class KatalogDataMap:
    components_root: Path
    legacy_katalog: KatalogTemplateSummary
    tldobio: TldobioSummary
    external_shopify: KatalogDataSource
    studio_draft: KatalogDataSource
    studio_writer: KatalogDataSource
    warnings: tuple[DataMapWarning, ...] = field(default_factory=tuple)


def _read_bounded_text(path: Path) -> tuple[str | None, DataMapWarning | None]:
    if not path.is_file():
        return None, None
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, DataMapWarning("stat_error", f"{path.name}: {exc}")
    if size > MAX_FILE_BYTES:
        return None, DataMapWarning(
            "file_too_large",
            f"{path.name} exceeds {MAX_FILE_BYTES} bytes — skipped",
        )
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, DataMapWarning("read_error", f"{path.name}: {exc}")


def _read_bounded_json(path: Path) -> tuple[dict | None, DataMapWarning | None]:
    text, warn = _read_bounded_text(path)
    if warn is not None:
        return None, warn
    if text is None:
        return None, None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, DataMapWarning("invalid_json", f"{path.name}: invalid JSON")
    if not isinstance(data, dict):
        return None, DataMapWarning("invalid_json", f"{path.name}: root is not object")
    return data, None


def _manifest_variants(manifest_path: Path) -> tuple[tuple[str, ...], list[DataMapWarning]]:
    data, warn = _read_bounded_json(manifest_path)
    warnings: list[DataMapWarning] = []
    if warn is not None:
        warnings.append(warn)
        return (), warnings
    if data is None:
        return (), warnings
    variants_raw = data.get("variants")
    if not isinstance(variants_raw, list):
        return (), warnings
    ids: list[str] = []
    for row in variants_raw:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("id") or "").strip()
        if vid:
            ids.append(vid)
    return tuple(ids), warnings


def _registry_summary(registry_path: Path) -> tuple[tuple[str, ...], bool, list[DataMapWarning]]:
    text, warn = _read_bounded_text(registry_path)
    warnings: list[DataMapWarning] = []
    if warn is not None:
        warnings.append(warn)
        return (), False, warnings
    if text is None:
        return (), False, warnings
    zones = tuple(_ZONE_ID_RE.findall(text))
    has_bg = bool(_BACKGROUND_IMAGE_RE.search(text))
    return zones, has_bg, warnings


def _collection_background_scan(collection_path: Path) -> tuple[bool, DataMapWarning | None]:
    text, warn = _read_bounded_text(collection_path)
    if warn is not None:
        return False, warn
    if text is None:
        return False, None
    return bool(_BACKGROUND_IMAGE_RE.search(text)), None


def _service_static_summary(service_path: Path) -> tuple[bool, bool, list[DataMapWarning]]:
    text, warn = _read_bounded_text(service_path)
    warnings: list[DataMapWarning] = []
    if warn is not None:
        warnings.append(warn)
        return False, False, warnings
    if text is None:
        return False, False, warnings
    lower = text.lower()
    shopify = "shopify" in lower or "graphql" in lower
    metafield = "metafield" in lower
    return shopify, metafield, warnings


def _tldobio_backgrounds_summary(
    collections_path: Path,
) -> tuple[int, int, tuple[str, ...], list[DataMapWarning]]:
    data, warn = _read_bounded_json(collections_path)
    warnings: list[DataMapWarning] = []
    if warn is not None:
        warnings.append(warn)
        return 0, 0, (), warnings
    if data is None:
        return 0, 0, (), warnings
    backgrounds = data.get("backgrounds")
    if not isinstance(backgrounds, dict):
        warnings.append(DataMapWarning("missing_backgrounds", "collections.json: no backgrounds object"))
        return 0, 0, (), warnings
    keys = tuple(list(backgrounds.keys())[:MAX_TLDOBIO_COLLECTION_KEYS])
    with_url = 0
    for row in backgrounds.values():
        if isinstance(row, dict) and str(row.get("url") or "").strip():
            with_url += 1
    return len(backgrounds), with_url, keys, warnings


def build_katalog_data_map(components_root: Path) -> KatalogDataMap:
    """Build read-only data ownership map from bounded paths."""
    root = Path(components_root)
    katalog_root = root / KATALOG_FOLDER
    tldobio_root = root / TLDOBIO_FOLDER
    all_warnings: list[DataMapWarning] = []

    manifest_path = katalog_root / KATALOG_MANIFEST
    variant_ids, manifest_warns = _manifest_variants(manifest_path)
    all_warnings.extend(manifest_warns)

    preview_ids = variant_ids[:MAX_VARIANTS_PREVIEW]
    if len(variant_ids) > MAX_VARIANTS_PREVIEW:
        all_warnings.append(DataMapWarning(
            "variant_limit",
            f"Showing {MAX_VARIANTS_PREVIEW} of {len(variant_ids)} variants",
        ))

    collection_present: list[str] = []
    has_bg_in_collections = False
    for vid in preview_ids:
        coll_path = katalog_root / "data" / "variants" / vid / KATALOG_VARIANT_COLLECTION
        if coll_path.is_file():
            collection_present.append(vid)
            found, coll_warn = _collection_background_scan(coll_path)
            if coll_warn is not None:
                all_warnings.append(coll_warn)
            has_bg_in_collections = has_bg_in_collections or found

    zones, has_bg_registry, reg_warns = _registry_summary(katalog_root / KATALOG_REGISTRY_PY)
    all_warnings.extend(reg_warns)

    legacy = KatalogTemplateSummary(
        root_exists=katalog_root.is_dir(),
        component_json_exists=(katalog_root / KATALOG_COMPONENT_JSON).is_file(),
        registry_py_exists=(katalog_root / KATALOG_REGISTRY_PY).is_file(),
        manifest_exists=manifest_path.is_file(),
        variant_count=len(variant_ids),
        sample_variants=preview_ids,
        collection_json_count=len(collection_present),
        sample_collections=tuple(collection_present),
        registry_zone_ids=zones,
        has_background_image_refs=has_bg_registry or has_bg_in_collections,
    )

    collections_path = tldobio_root / TLDOBIO_COLLECTIONS_JSON
    bg_count, bg_with_url, sample_keys, tld_warns = _tldobio_backgrounds_summary(collections_path)
    all_warnings.extend(tld_warns)

    shopify_detected, metafield_detected, svc_warns = _service_static_summary(
        tldobio_root / "service.py",
    )
    all_warnings.extend(svc_warns)

    tldobio = TldobioSummary(
        root_exists=tldobio_root.is_dir(),
        collections_json_exists=collections_path.is_file(),
        collection_count=bg_count,
        sample_collection_keys=sample_keys,
        backgrounds_with_url=bg_with_url,
        service_py_exists=(tldobio_root / "service.py").is_file(),
        shopify_integration_detected=shopify_detected,
        metafield_refs_detected=metafield_detected,
        risk="high" if shopify_detected else "medium",
    )

    external_shopify = KatalogDataSource(
        source_id="external_shopify",
        label="Shopify (metafields / Files / GraphQL)",
        exists=False,
        status="out_of_scope",
        risk="high",
        write_policy="out_of_scope",
        note="F5.5 / Level 3 only — not Studio F2",
    )

    studio_draft = KatalogDataSource(
        source_id="studio_draft",
        label="Studio draft state",
        exists=False,
        status="planned",
        risk="low",
        write_policy="planned",
        note="F3+ — in-memory only, no filesystem write",
    )

    studio_writer = KatalogDataSource(
        source_id="studio_writer",
        label="Bounded local writer",
        exists=False,
        status="not_started",
        risk="medium",
        write_policy="not_started",
        note="Requires finalized data map + dry-run/readiness — no Save in F2",
    )

    if legacy.root_exists and tldobio.root_exists:
        all_warnings.append(DataMapWarning(
            "dual_persistence",
            "Legacy katalog (template JSON) and tldobio (cache/metafields) are separate — "
            "no unified write policy",
        ))

    return KatalogDataMap(
        components_root=root,
        legacy_katalog=legacy,
        tldobio=tldobio,
        external_shopify=external_shopify,
        studio_draft=studio_draft,
        studio_writer=studio_writer,
        warnings=tuple(all_warnings),
    )


def data_map_display_rows(data_map: KatalogDataMap) -> list[tuple[str, str]]:
    """Flat rows for UI — legacy vs tldobio vs out-of-scope."""
    lk = data_map.legacy_katalog
    tb = data_map.tldobio
    rows: list[tuple[str, str]] = [
        ("— Legacy katalog —", lk.status),
        ("Owner", "Komponenty/katalog · template collection.json"),
        ("Exists", "yes" if lk.root_exists else "missing"),
        ("component.json", "present" if lk.component_json_exists else "missing"),
        ("registry.py", "present" if lk.registry_py_exists else "missing"),
        ("manifest.json", "present" if lk.manifest_exists else "missing"),
        ("Variants (total)", str(lk.variant_count)),
    ]
    if lk.sample_variants:
        rows.append(("Sample variants", ", ".join(lk.sample_variants)))
    rows.append(("collection.json (sample)", str(lk.collection_json_count)))
    if lk.registry_zone_ids:
        rows.append(("Registry zones", ", ".join(lk.registry_zone_ids)))
    rows.append((
        "background_image refs",
        "detected" if lk.has_background_image_refs else "not detected in sample",
    ))
    rows.append(("Risk / write policy", f"{lk.risk} · {lk.write_policy}"))

    rows.extend([
        ("— Tło do Bio (tldobio) —", tb.status),
        ("Role", "absorbed subflow · not standalone tile"),
        ("Exists", "yes" if tb.root_exists else "missing"),
        ("collections.json", "present" if tb.collections_json_exists else "missing"),
        ("Cache entries", str(tb.collection_count)),
    ])
    if tb.sample_collection_keys:
        rows.append(("Sample handles", ", ".join(tb.sample_collection_keys[:5])))
        if len(tb.sample_collection_keys) > 5:
            rows.append(("…", f"+{len(tb.sample_collection_keys) - 5} more (bounded)"))
    rows.append(("With URL (cache)", str(tb.backgrounds_with_url)))
    rows.append(("service.py", "present" if tb.service_py_exists else "missing"))
    if tb.service_py_exists:
        rows.append((
            "Static integration hints",
            f"shopify={tb.shopify_integration_detected} · metafields={tb.metafield_refs_detected}",
        ))
    rows.append(("Risk / write policy", f"{tb.risk} · {tb.write_policy}"))

    for src in (data_map.external_shopify, data_map.studio_draft, data_map.studio_writer):
        rows.append((f"— {src.label} —", src.status))
        rows.append(("Write policy", src.write_policy))
        if src.note:
            rows.append(("Note", src.note))

    for w in data_map.warnings:
        rows.append((f"Warning ({w.code})", w.message))

    rows.append(("Next", F2_NEXT_NOTE))
    return rows


def f2_status_strip() -> str:
    return "Read-only · F2 data map · no Save · no writer · Shopify out-of-scope"


def f3_status_strip() -> str:
    return "local planning only · dry-run · writer: not started · nic nie zapisano"
