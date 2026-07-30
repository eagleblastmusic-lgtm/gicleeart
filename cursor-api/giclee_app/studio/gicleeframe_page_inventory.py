"""GICLÉE FRAME™ F2 — read-only inventory strony. Bounded paths, zero Komponenty imports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path

from giclee_app.studio.gicleeframe_page_settings import (
    PageSettingField,
    page_settings_from_section,
)

GICLEEFRAME_FOLDER = "gicleeframe"
MANIFEST_REL = "data/variants/manifest.json"
REGISTRY_REL = "registry.py"
PAGE_TEMPLATE = "page.giclee-frame.json"
TEXT_LAYERS_FILE = "text-layers.json"

INVENTORY_READ_NOTE = (
    "F2 inventory — bounded read variant JSON · zero write · RAM draft osobno"
)

F2_STATUS_STRIP = (
    "Status: planowanie lokalne · inventory strony · RAM draft · writer zablokowany"
)

GROUP_LABELS_PL: dict[str, str] = {
    "hero": "Hero",
    "sections": "Sekcje",
    "technology": "Technologia ramy",
    "graphics": "Grafiki",
    "texts": "Teksty",
    "separators": "Separatory",
    "footer": "Stopka",
    "cta": "CTA",
}

_SECTION_KEY_RE = re.compile(
    r'_(?:media_zone|divider_zone)\(\s*"([^"]+)"\s*,\s*"([^"]+)"',
)

_GROUP_ORDER = (
    "hero",
    "sections",
    "technology",
    "graphics",
    "texts",
    "separators",
    "footer",
    "cta",
)

_TEXT_TRUNCATE = 140


@dataclass(frozen=True)
class PageElement:
    element_id: str
    section_key: str
    element_type: str
    group: str
    order: int
    label: str
    title: str
    text: str
    image_ref: str
    alt: str
    notes: str
    editable: bool
    source: str
    status: str
    page_settings: tuple[PageSettingField, ...] = ()
    page_fields: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PageInventoryReport:
    components_root: Path
    variant_id: str | None
    live_variant_id: str | None
    page_path: Path | None
    source_section_count: int
    elements: tuple[PageElement, ...]
    warnings: tuple[str, ...] = field(default_factory=lambda: (INVENTORY_READ_NOTE,))


def _page_settings_and_fields(section: dict) -> tuple[tuple[PageSettingField, ...], tuple[tuple[str, str], ...]]:
    page_settings = page_settings_from_section(section)
    page_fields = tuple((field.label, field.value) for field in page_settings)
    return page_settings, page_fields


def _strip_shopify_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def _load_json_dict(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(_strip_shopify_json_header(raw))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _read_manifest_env(
    manifest_path: Path,
) -> tuple[str | None, str | None, tuple[str, ...]]:
    data = _load_json_dict(manifest_path)
    if not data:
        return None, None, ()
    active = data.get("active")
    active_id = str(active).strip() if active else None
    live_raw = data.get("live")
    live_id = str(live_raw).strip() if live_raw else active_id
    variants_raw = data.get("variants")
    ids: list[str] = []
    if isinstance(variants_raw, list):
        for row in variants_raw:
            if isinstance(row, dict) and row.get("id"):
                ids.append(str(row["id"]).strip())
    return active_id, live_id, tuple(ids)


def variant_environment_tag(
    variant_id: str | None,
    *,
    active_id: str | None,
    live_id: str | None,
) -> str:
    """dev = aktywny wariant w lokalnym workspace; live = wariant na produkcji."""
    if not variant_id:
        return "dev"
    if active_id and variant_id == active_id:
        return "dev"
    if live_id and variant_id == live_id:
        return "live"
    return "dev"


def _read_manifest_active(manifest_path: Path) -> tuple[str | None, tuple[str, ...]]:
    active_id, _live_id, variant_ids = _read_manifest_env(manifest_path)
    return active_id, variant_ids


def _registry_labels(registry_path: Path) -> dict[str, str]:
    """Parse registry.py as text — zone_key -> label PL."""
    labels: dict[str, str] = {}
    if not registry_path.is_file():
        return labels
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError:
        return labels
    for key, label in _SECTION_KEY_RE.findall(text):
        labels[key] = label
    main_match = re.search(
        r'zone_id="main"[^}]*label="([^"]+)"',
        text,
        re.DOTALL,
    )
    if main_match:
        labels["main"] = main_match.group(1)
    return labels


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    return " ".join(text.split())


def _truncate(value: str, limit: int = _TEXT_TRUNCATE) -> str:
    v = (value or "").strip()
    if len(v) <= limit:
        return v
    return v[: limit - 1] + "…"


def _narrative_group(section_key: str, label: str, section_type: str) -> str:
    low = label.lower()
    if section_type == "divider":
        return "separators"
    if section_key == "main" or section_type == "main-page":
        return "sections"
    if "intro" in low or section_key == "media_with_content_xdDQna":
        return "hero"
    if "finalna" in low or "finał" in low:
        return "footer"
    if section_type == "media-with-content":
        return "technology"
    return "sections"


def _section_disabled(section: dict) -> bool:
    blocks = section.get("blocks")
    if not isinstance(blocks, dict) or not blocks:
        return False
    for block in blocks.values():
        if isinstance(block, dict) and block.get("disabled"):
            return True
    return False


def _extract_media_children(
    section_key: str,
    section: dict,
    *,
    base_order: int,
    section_label: str,
    narrative_group: str,
) -> list[PageElement]:
    elements: list[PageElement] = []
    sec_name = str(section.get("name") or section_label)
    section_page_settings, section_page_fields = _page_settings_and_fields(section)

    elements.append(
        PageElement(
            element_id=f"{section_key}::section",
            section_key=section_key,
            element_type="media_section",
            group=narrative_group,
            order=base_order,
            label=section_label,
            title=sec_name,
            text="",
            image_ref="",
            alt="",
            notes="",
            editable=True,
            source="variant_json",
            status="ok",
            page_settings=section_page_settings,
            page_fields=section_page_fields,
        )
    )

    blocks = section.get("blocks") if isinstance(section.get("blocks"), dict) else {}
    media = blocks.get("media") if isinstance(blocks.get("media"), dict) else {}
    media_settings = media.get("settings") if isinstance(media.get("settings"), dict) else {}
    image_ref = str(media_settings.get("image") or "").strip()
    alt = str(media_settings.get("alt") or "").strip()

    img_status = "ok" if image_ref else "missing_content"
    elements.append(
        PageElement(
            element_id=f"{section_key}::image",
            section_key=section_key,
            element_type="image",
            group="graphics",
            order=base_order + 1,
            label=f"{section_label} — grafika",
            title="",
            text="",
            image_ref=image_ref,
            alt=alt,
            notes="",
            editable=True,
            source="variant_json",
            status=img_status,
        )
    )

    content = blocks.get("content") if isinstance(blocks.get("content"), dict) else {}
    inner = content.get("blocks") if isinstance(content.get("blocks"), dict) else {}
    block_order = content.get("block_order")
    ordered_ids: list[str] = []
    if isinstance(block_order, list):
        ordered_ids = [str(x) for x in block_order]
    else:
        ordered_ids = list(inner.keys())

    sub = 2
    for bid in ordered_ids:
        block = inner.get(bid)
        if not isinstance(block, dict):
            continue
        btype = str(block.get("type") or "")
        settings = block.get("settings") if isinstance(block.get("settings"), dict) else {}
        raw_text = str(settings.get("text") or "")
        plain = _strip_html(raw_text) if btype == "text" else raw_text.strip()

        if "jumbo" in btype or bid.startswith("jumbo"):
            etype = "jumbo"
            grp = "texts"
            title = plain
            body = ""
        else:
            etype = "body"
            grp = "texts"
            title = ""
            body = plain

        st = "ok" if (title or body) else "missing_content"
        if len(plain) < 8 and plain:
            st = "needs_review"

        elements.append(
            PageElement(
                element_id=f"{section_key}::{bid}",
                section_key=section_key,
                element_type=etype,
                group=grp,
                order=base_order + sub,
                label=f"{section_label} — {etype}",
                title=title,
                text=body,
                image_ref="",
                alt="",
                notes="",
                editable=True,
                source="variant_json",
                status=st,
            )
        )
        sub += 1

    return elements


def _parse_page_inventory(
    page_data: dict,
    labels: dict[str, str],
) -> tuple[int, tuple[PageElement, ...]]:
    sections = page_data.get("sections")
    order_raw = page_data.get("order")
    if not isinstance(sections, dict) or not isinstance(order_raw, list):
        return 0, ()

    source_section_count = len(order_raw)
    elements: list[PageElement] = []
    element_order = 0

    for section_key in order_raw:
        key = str(section_key)
        section = sections.get(key)
        if not isinstance(section, dict):
            continue
        section_type = str(section.get("type") or "")
        label = labels.get(key) or str(section.get("name") or key)
        narrative = _narrative_group(key, label, section_type)

        if section_type == "divider":
            divider_settings, divider_fields = _page_settings_and_fields(section)
            elements.append(
                PageElement(
                    element_id=f"{key}::divider",
                    section_key=key,
                    element_type="divider",
                    group="separators",
                    order=element_order,
                    label=label,
                    title=label,
                    text="",
                    image_ref="",
                    alt="",
                    notes="",
                    editable=True,
                    source="variant_json",
                    status="ok",
                    page_settings=divider_settings,
                    page_fields=divider_fields,
                )
            )
            element_order += 1
            continue

        if section_type == "main-page" or key == "main":
            status = "legacy_disabled" if _section_disabled(section) else "needs_review"
            elements.append(
                PageElement(
                    element_id=f"{key}::legacy",
                    section_key=key,
                    element_type="section_legacy",
                    group="sections",
                    order=element_order,
                    label=label,
                    title=label,
                    text="Sekcja main-page — wyłączona na live",
                    image_ref="",
                    alt="",
                    notes="",
                    editable=False,
                    source="variant_json",
                    status=status,
                )
            )
            element_order += 1
            continue

        if section_type == "media-with-content":
            children = _extract_media_children(
                key,
                section,
                base_order=element_order,
                section_label=label,
                narrative_group=narrative,
            )
            elements.extend(children)
            element_order += len(children)
            continue

        elements.append(
            PageElement(
                element_id=f"{key}::unknown",
                section_key=key,
                element_type="section",
                group=narrative,
                order=element_order,
                label=label,
                title=label,
                text="",
                image_ref="",
                alt="",
                notes="",
                editable=True,
                source="variant_json",
                status="needs_review",
            )
        )
        element_order += 1

    return source_section_count, tuple(elements)


def _text_layer_inventory(
    data: dict,
    *,
    page_data: dict,
    labels: dict[str, str],
    base_order: int,
) -> tuple[tuple[PageElement, ...], tuple[str, ...]]:
    sections = data.get("sections")
    page_sections = page_data.get("sections")
    if not isinstance(sections, dict) or not isinstance(page_sections, dict):
        return (), ()

    elements: list[PageElement] = []
    warnings: list[str] = []
    offset = 0
    for raw_section_key, raw_layers in sections.items():
        section_key = str(raw_section_key)
        if section_key not in page_sections:
            warnings.append(
                f"Osierocone warstwy tekstowe: sekcja {section_key}"
            )
        if not isinstance(raw_layers, list):
            continue
        section_label = labels.get(section_key, section_key)
        for raw_layer in raw_layers:
            if not isinstance(raw_layer, dict):
                continue
            content = (
                raw_layer.get("content")
                if isinstance(raw_layer.get("content"), dict)
                else {}
            )
            kind = str(content.get("kind") or "paragraph")
            text = str(content.get("text") or "")
            if content.get("mode") == "adapted-code":
                text = _strip_html(str(content.get("html") or ""))
            name = str(raw_layer.get("name") or "Tekst")
            layer_id = str(raw_layer.get("id") or f"text_{offset}")
            enabled = bool(raw_layer.get("enabled", True))
            status = "ok" if text.strip() else "missing_content"
            if not enabled:
                status = "disabled"
            title = text if kind in {"h1", "h2", "h3"} else ""
            body = "" if title else text
            elements.append(
                PageElement(
                    element_id=f"{section_key}::{layer_id}",
                    section_key=section_key,
                    element_type="text_layer",
                    group="texts",
                    order=base_order + offset,
                    label=f"{section_label} — {name}",
                    title=_truncate(title),
                    text=_truncate(body),
                    image_ref="",
                    alt="",
                    notes=f"Warstwa Dodaj tekst · {kind}",
                    editable=False,
                    source="text-layers.json",
                    status=status,
                )
            )
            offset += 1
    return tuple(elements), tuple(warnings)


def build_gicleeframe_page_inventory(components_root: Path) -> PageInventoryReport:
    """Read-only inventory from bounded paths under components_root."""
    root = Path(components_root)
    gf_root = root / GICLEEFRAME_FOLDER
    warnings: list[str] = [INVENTORY_READ_NOTE]

    manifest_path = gf_root / MANIFEST_REL
    active_id, live_id, variant_ids = _read_manifest_env(manifest_path)
    variant_id = active_id or (variant_ids[0] if variant_ids else None)

    page_path: Path | None = None
    if variant_id:
        candidate = gf_root / "data" / "variants" / variant_id / PAGE_TEMPLATE
        if candidate.is_file():
            page_path = candidate

    labels = _registry_labels(gf_root / REGISTRY_REL)
    if not labels:
        warnings.append("registry.py — brak etykiet (regex)")

    source_section_count = 0
    elements: tuple[PageElement, ...] = ()
    if page_path is None:
        warnings.append("Brak page.giclee-frame.json dla aktywnego wariantu")
    else:
        page_data = _load_json_dict(page_path)
        if page_data is None:
            warnings.append(f"Nie udało się sparsować: {page_path.name}")
        else:
            source_section_count, elements = _parse_page_inventory(page_data, labels)
            text_layers_path = page_path.parent / TEXT_LAYERS_FILE
            if text_layers_path.is_file():
                text_data = _load_json_dict(text_layers_path)
                if text_data is None:
                    warnings.append(
                        f"Nie udało się sparsować: {TEXT_LAYERS_FILE}"
                    )
                else:
                    text_elements, text_warnings = _text_layer_inventory(
                        text_data,
                        page_data=page_data,
                        labels=labels,
                        base_order=len(elements),
                    )
                    elements = elements + text_elements
                    warnings.extend(text_warnings)

    return PageInventoryReport(
        components_root=root,
        variant_id=variant_id,
        live_variant_id=live_id,
        page_path=page_path,
        source_section_count=source_section_count,
        elements=elements,
        warnings=tuple(warnings),
    )


def inventory_count_stats(report: PageInventoryReport) -> dict[str, int]:
    counts = {
        "source_sections": report.source_section_count,
        "elements_total": len(report.elements),
        "separators": 0,
        "media_sections": 0,
        "images": 0,
        "text_blocks": 0,
        "needs_review": 0,
    }
    for el in report.elements:
        if el.element_type == "divider":
            counts["separators"] += 1
        if el.element_type == "media_section":
            counts["media_sections"] += 1
        if el.element_type == "image":
            counts["images"] += 1
        if el.element_type in ("jumbo", "body", "text_layer"):
            counts["text_blocks"] += 1
        if el.status in ("needs_review", "missing_content", "legacy_disabled"):
            counts["needs_review"] += 1
    return counts


def inventory_elements_by_group(
    report: PageInventoryReport,
) -> dict[str, list[PageElement]]:
    buckets: dict[str, list[PageElement]] = {g: [] for g in _GROUP_ORDER}
    for el in report.elements:
        buckets.setdefault(el.group, []).append(el)
    return {g: buckets[g] for g in _GROUP_ORDER if buckets.get(g)}


def inventory_display_rows(report: PageInventoryReport) -> list[tuple[str, str]]:
    stats = inventory_count_stats(report)
    return [
        ("Wariant", report.variant_id or "—"),
        ("Źródłowe sekcje (order[])", str(stats["source_sections"])),
        ("Elementy inventory (po rozwinięciu)", str(stats["elements_total"])),
        ("Separatory", str(stats["separators"])),
        ("Sekcje media", str(stats["media_sections"])),
        ("Grafiki", str(stats["images"])),
        ("Bloki tekstowe", str(stats["text_blocks"])),
        ("Do sprawdzenia", str(stats["needs_review"])),
    ]


def element_display_summary(el: PageElement) -> str:
    parts: list[str] = []
    if el.title:
        parts.append(_truncate(el.title, 60))
    if el.text:
        parts.append(_truncate(el.text, 80))
    if el.image_ref:
        ref = el.image_ref
        if len(ref) > 48:
            ref = ref[:45] + "…"
        parts.append(ref)
    return " · ".join(parts) if parts else "—"
