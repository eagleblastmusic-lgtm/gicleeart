"""Kanoniczny model osi GICLÉE HOME FLOW.

Nazwy użytkowe są metadanymi wariantu i nie modyfikują ``templates/index.json``.
Techniczne identyfikatory pozostają stabilne, natomiast kody ``GH-xx`` i
``GH-Txx`` są wyliczane z aktualnej kolejności przy każdym odczycie.

Schema v2 zachowuje nazwy z Etapu 1 i może przechowywać ``structure_draft`` z
HF-3A. Szkic struktury nie zmienia aktywnej kolejności motywu ani edytora.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any, Iterable

from .homepage_variants import VARIANTS_ROOT

FLOW_SCHEMA_VERSION = 2
FLOW_FILENAME = "home_flow.json"
STRUCTURE_DRAFT_KEY = "structure_draft"


@dataclass(frozen=True)
class HomeFlowItem:
    stable_id: str
    kind: str
    default_name: str
    zone_id: str = ""
    parent_id: str = ""
    placement: str = "inside"
    name: str = ""
    code: str = ""

    @property
    def display_name(self) -> str:
        return self.name.strip() or self.default_name


DEFAULT_FLOW_ITEMS: tuple[HomeFlowItem, ...] = (
    HomeFlowItem(
        "section:prehero",
        "section",
        "Pre-Hero — Od ekranu do materii",
        zone_id="prehero_scroll",
    ),
    HomeFlowItem(
        "phase:portal",
        "phase",
        "Portal i tekst",
        parent_id="section:prehero",
        placement="inside",
    ),
    HomeFlowItem(
        "phase:hero-rise",
        "phase",
        "Wjazd Hero",
        parent_id="section:prehero",
        placement="after",
    ),
    HomeFlowItem(
        "section:hero",
        "section",
        "Hero — Kolaż pracowni",
        zone_id="hero",
    ),
    HomeFlowItem(
        "phase:hero-hold",
        "phase",
        "Postój Hero",
        parent_id="section:hero",
        placement="inside",
    ),
    HomeFlowItem(
        "phase:sound-consent",
        "phase",
        "Decyzja o dźwięku",
        parent_id="section:hero",
        placement="inside",
    ),
    HomeFlowItem(
        "phase:horizontal-curtain",
        "phase",
        "Pozioma kurtyna Hero → Giclée Art",
        parent_id="section:hero",
        placement="after",
    ),
    HomeFlowItem(
        "section:intro",
        "section",
        "Giclée Art — Intro marki",
        zone_id="giclee_art",
    ),
    HomeFlowItem(
        "phase:intro-hold",
        "phase",
        "Postój sekcji",
        parent_id="section:intro",
        placement="after",
    ),
    HomeFlowItem(
        "section:restoration",
        "section",
        "Odtwarzanie dzieł",
        zone_id="restoration",
    ),
    HomeFlowItem(
        "section:color-correction",
        "section",
        "Autorska korekcja kolorystyczna",
        zone_id="color_correction",
    ),
    HomeFlowItem(
        "section:potential",
        "section",
        "Potencjał ukryty w zdjęciu",
        zone_id="potential",
    ),
    HomeFlowItem(
        "section:see-difference",
        "section",
        "Zobacz różnicę",
        zone_id="see_difference",
    ),
    HomeFlowItem(
        "section:notice",
        "section",
        "Powiadomienie strony głównej",
        zone_id="site_notice",
    ),
)


def flow_path(variant_id: str, *, variants_root: Path | None = None) -> Path:
    root = Path(variants_root) if variants_root is not None else VARIANTS_ROOT
    return root / str(variant_id) / FLOW_FILENAME


def _clean_name(raw: Any) -> str:
    return " ".join(str(raw or "").split()).strip()[:120]


def _clean_structure_draft(raw: Any) -> dict[str, Any]:
    """Zachowuje tylko JSON-owe pola szkicu rozpoznawane przez HF-3A."""

    if not isinstance(raw, dict):
        return {}

    order = raw.get("section_order")
    custom = raw.get("custom_sections")
    draft: dict[str, Any] = {}

    if isinstance(order, list):
        clean_order = [str(value).strip() for value in order if str(value).strip()]
        if clean_order:
            draft["section_order"] = clean_order

    if isinstance(custom, list):
        clean_custom: list[dict[str, str]] = []
        for row in custom:
            if not isinstance(row, dict):
                continue
            stable_id = str(row.get("stable_id") or "").strip()
            blueprint_id = str(row.get("blueprint_id") or "").strip()
            name = _clean_name(row.get("name"))
            if stable_id and blueprint_id and name:
                clean_custom.append(
                    {
                        "stable_id": stable_id,
                        "blueprint_id": blueprint_id,
                        "name": name,
                    }
                )
        if clean_custom:
            draft["custom_sections"] = clean_custom

    return draft


def load_flow_metadata(
    variant_id: str,
    *,
    variants_root: Path | None = None,
) -> dict[str, Any]:
    path = flow_path(variant_id, variants_root=variants_root)
    if not path.is_file():
        return {"schema": FLOW_SCHEMA_VERSION, "names": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"schema": FLOW_SCHEMA_VERSION, "names": {}}
    if not isinstance(data, dict):
        return {"schema": FLOW_SCHEMA_VERSION, "names": {}}

    raw_names = data.get("names")
    names: dict[str, str] = {}
    if isinstance(raw_names, dict):
        known = {item.stable_id for item in DEFAULT_FLOW_ITEMS}
        for stable_id, raw_name in raw_names.items():
            name = _clean_name(raw_name)
            if str(stable_id) in known and name:
                names[str(stable_id)] = name

    result: dict[str, Any] = {"schema": FLOW_SCHEMA_VERSION, "names": names}
    draft = _clean_structure_draft(data.get(STRUCTURE_DRAFT_KEY))
    if draft:
        result[STRUCTURE_DRAFT_KEY] = draft
    return result


def save_flow_metadata(
    variant_id: str,
    metadata: dict[str, Any],
    *,
    variants_root: Path | None = None,
) -> Path:
    path = flow_path(variant_id, variants_root=variants_root)
    raw_names = metadata.get("names") if isinstance(metadata, dict) else {}
    known = {item.stable_id: item.default_name for item in DEFAULT_FLOW_ITEMS}
    names: dict[str, str] = {}
    if isinstance(raw_names, dict):
        for stable_id, raw_name in raw_names.items():
            stable_id = str(stable_id)
            name = _clean_name(raw_name)
            if stable_id in known and name and name != known[stable_id]:
                names[stable_id] = name

    payload: dict[str, Any] = {"schema": FLOW_SCHEMA_VERSION, "names": names}
    draft = _clean_structure_draft(
        metadata.get(STRUCTURE_DRAFT_KEY) if isinstance(metadata, dict) else None
    )
    if draft:
        payload[STRUCTURE_DRAFT_KEY] = draft

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def number_flow_items(items: Iterable[HomeFlowItem]) -> tuple[HomeFlowItem, ...]:
    section_number = 0
    phase_number = 1
    numbered: list[HomeFlowItem] = []
    for item in items:
        if item.kind == "section":
            code = f"GH-{section_number:02d}"
            section_number += 1
        else:
            code = f"GH-T{phase_number:02d}"
            phase_number += 1
        numbered.append(replace(item, code=code))
    return tuple(numbered)


def resolve_flow_items(
    variant_id: str,
    *,
    variants_root: Path | None = None,
) -> tuple[HomeFlowItem, ...]:
    """Zwraca aktywną, kanoniczną oś.

    HF-3A nie stosuje szkicu do aktywnej nawigacji. Dopiero bounded writer z
    późniejszego etapu będzie mógł zmienić strukturę motywu.
    """

    metadata = load_flow_metadata(variant_id, variants_root=variants_root)
    names = metadata.get("names") if isinstance(metadata, dict) else {}
    resolved = tuple(
        replace(item, name=_clean_name((names or {}).get(item.stable_id)))
        for item in DEFAULT_FLOW_ITEMS
    )
    return number_flow_items(resolved)


def set_flow_name(
    variant_id: str,
    stable_id: str,
    name: str,
    *,
    variants_root: Path | None = None,
) -> Path:
    item = next((row for row in DEFAULT_FLOW_ITEMS if row.stable_id == stable_id), None)
    if item is None:
        raise ValueError(f"Nieznany element GICLÉE HOME FLOW: {stable_id}")
    cleaned = _clean_name(name)
    if not cleaned:
        raise ValueError("Nazwa nie może być pusta.")
    metadata = load_flow_metadata(variant_id, variants_root=variants_root)
    names = dict(metadata.get("names") or {})
    if cleaned == item.default_name:
        names.pop(stable_id, None)
    else:
        names[stable_id] = cleaned
    metadata["names"] = names
    return save_flow_metadata(variant_id, metadata, variants_root=variants_root)


def reset_flow_name(
    variant_id: str,
    stable_id: str,
    *,
    variants_root: Path | None = None,
) -> Path:
    metadata = load_flow_metadata(variant_id, variants_root=variants_root)
    names = dict(metadata.get("names") or {})
    names.pop(stable_id, None)
    metadata["names"] = names
    return save_flow_metadata(variant_id, metadata, variants_root=variants_root)


def flow_item_by_id(variant_id: str, stable_id: str) -> HomeFlowItem | None:
    return next((item for item in resolve_flow_items(variant_id) if item.stable_id == stable_id), None)


def owner_zone_id(item: HomeFlowItem, items: Iterable[HomeFlowItem]) -> str:
    if item.kind == "section":
        return item.zone_id
    parent = next((row for row in items if row.stable_id == item.parent_id), None)
    return parent.zone_id if parent is not None else ""
