"""Wspólny model warstw tekstowych GicleeApp.

Warstwy są zapisywane per wariant w ``text-layers.json``. Plik nie jest
częścią szablonu Shopify, dzięki czemu tekst można przypisać również do sekcji,
które nie przyjmują natywnych bloków Theme Editor.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterable

from giclee_app.app_paths import atomic_write_text, config_path

from .config import PageEditorConfig

SCHEMA_VERSION = 1
TEXT_LAYER_FILENAME = "text-layers.json"

CONTENT_KINDS = (
    "h1",
    "h2",
    "h3",
    "paragraph",
    "subtitle",
    "eyebrow",
    "quote",
    "signature",
)
LAYOUT_MODES = ("flow", "absolute")
ANCHORS = (
    "top-left",
    "top-center",
    "top-right",
    "center-left",
    "center",
    "center-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)
ALIGNMENTS = ("left", "center", "right")
UNITS = ("px", "%", "vw", "vh")

ENTER_PRESETS = (
    "none",
    "fade",
    "fade-up",
    "fade-down",
    "slide-left",
    "slide-right",
    "soft-blur-reveal",
    "gentle-scale-in",
    "mask-reveal",
    "letter-spacing-reveal",
)
EXIT_PRESETS = (
    "none",
    "fade-out",
    "fade-up-out",
    "fade-down-out",
    "slide-left-out",
    "slide-right-out",
    "blur-away",
    "gentle-scale-out",
    "mask-close",
)
EASINGS = ("museum", "soft", "crisp", "linear")

_LAYER_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{3,80}$")
_PRESET_CONFIG = config_path(
    "text-motion-presets.json",
    legacy=Path(__file__).resolve().parent / "data" / "text-motion-presets.json",
)


def empty_document() -> dict[str, Any]:
    return {"schemaVersion": SCHEMA_VERSION, "sections": {}}


def _number(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = float(default)
    return max(lo, min(hi, result))


def _integer(value: Any, default: int, lo: int, hi: int) -> int:
    return int(round(_number(value, default, lo, hi)))


def _unit_value(
    raw: Any,
    *,
    default_value: float,
    default_unit: str = "px",
    lo: float = -4000,
    hi: float = 4000,
    allowed_units: Iterable[str] = UNITS,
) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    allowed = tuple(allowed_units)
    unit = str(source.get("unit") or default_unit)
    if unit not in allowed:
        unit = default_unit
    value = _number(source.get("value"), default_value, lo, hi)
    if abs(value - round(value)) < 1e-9:
        value = int(round(value))
    return {"value": value, "unit": unit}


def default_device_layout() -> dict[str, Any]:
    return {
        "anchor": "top-left",
        "offsetX": {"value": 0, "unit": "px"},
        "offsetY": {"value": 0, "unit": "px"},
        "maxWidth": {"value": 720, "unit": "px"},
        "align": "left",
        "zIndex": 20,
        "padding": {"value": 0, "unit": "px"},
    }


def _normalize_device_layout(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    anchor = str(source.get("anchor") or "top-left")
    align = str(source.get("align") or "left")
    return {
        "anchor": anchor if anchor in ANCHORS else "top-left",
        "offsetX": _unit_value(source.get("offsetX"), default_value=0),
        "offsetY": _unit_value(source.get("offsetY"), default_value=0),
        "maxWidth": _unit_value(
            source.get("maxWidth"),
            default_value=720,
            lo=40,
            hi=4000,
            allowed_units=("px", "%", "vw"),
        ),
        "align": align if align in ALIGNMENTS else "left",
        "zIndex": _integer(source.get("zIndex"), 20, -100, 1000),
        "padding": _unit_value(
            source.get("padding"),
            default_value=0,
            lo=0,
            hi=600,
        ),
    }


def _normalize_motion(raw: Any, *, enter: bool) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    allowed = ENTER_PRESETS if enter else EXIT_PRESETS
    fallback = "fade-up" if enter else "none"
    preset = str(source.get("preset") or fallback)
    easing = str(source.get("easing") or "museum")
    out = {
        "preset": preset if preset in allowed else fallback,
        "duration": round(_number(source.get("duration"), 0.8 if enter else 0.6, 0.1, 10), 3),
        "easing": easing if easing in EASINGS else "museum",
        "distance": _integer(source.get("distance"), 32, 0, 600),
        "blur": _integer(source.get("blur"), 12 if enter else 16, 0, 100),
        "intensity": round(_number(source.get("intensity"), 1, 0, 2), 3),
    }
    if enter:
        out["delay"] = round(_number(source.get("delay"), 0, 0, 10), 3)
        out["stagger"] = round(_number(source.get("stagger"), 0.04, 0, 0.5), 3)
        out["staggerMode"] = (
            str(source.get("staggerMode"))
            if str(source.get("staggerMode")) in ("none", "words", "characters")
            else "none"
        )
    else:
        out["startPct"] = _integer(source.get("startPct"), 80, 0, 100)
    return out


def _normalize_pin(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    desktop_raw = source.get("desktop")
    desktop_source = desktop_raw if isinstance(desktop_raw, dict) else {}
    mobile_raw = source.get("mobile")
    mobile_source = mobile_raw if isinstance(mobile_raw, dict) else {}
    mobile_mode = str(mobile_source.get("mode") or "inherit")
    if mobile_mode not in ("inherit", "on", "off", "custom"):
        mobile_mode = "inherit"
    end_raw = desktop_source.get("endVh")
    end_vh = None
    if end_raw not in (None, ""):
        end_vh = _integer(end_raw, 100, 0, 2000)
    return {
        "desktop": {
            "enabled": bool(desktop_source.get("enabled", False)),
            "durationVh": _integer(desktop_source.get("durationVh"), 100, 0, 1000),
            "top": _unit_value(
                desktop_source.get("top"),
                default_value=0,
                lo=-100,
                hi=1000,
                allowed_units=("px", "vh"),
            ),
            "startVh": _integer(desktop_source.get("startVh"), 0, 0, 1000),
            "endVh": end_vh,
        },
        "mobile": {
            "mode": mobile_mode,
            "durationVh": _integer(mobile_source.get("durationVh"), 0, 0, 1000),
            "top": _unit_value(
                mobile_source.get("top"),
                default_value=0,
                lo=-100,
                hi=1000,
                allowed_units=("px", "vh"),
            ),
        },
    }


def new_layer(*, name: str = "Tekst 1", layer_id: str | None = None) -> dict[str, Any]:
    stable_id = layer_id or f"text_{uuid.uuid4().hex[:12]}"
    return {
        "id": stable_id,
        "name": name.strip() or "Tekst",
        "enabled": True,
        "order": 0,
        "content": {
            "kind": "paragraph",
            "mode": "plain",
            "text": "",
            "html": "",
        },
        "layout": {
            "mode": "flow",
            "desktop": default_device_layout(),
            "tablet": None,
            "mobile": None,
        },
        "motion": {
            "enter": _normalize_motion({}, enter=True),
            "exit": _normalize_motion({}, enter=False),
        },
        "pin": _normalize_pin({}),
        "importedStyle": {
            "scopedCss": "",
            "fontUrls": [],
            "componentMode": False,
            "ownsMotion": False,
            "behavior": {
                "trigger": "section-progress",
                "threshold": 0.08,
                "rootMargin": "0px",
                "once": False,
            },
        },
    }


def normalize_layer(raw: Any, *, fallback_order: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    layer_id = str(raw.get("id") or "").strip()
    if not _LAYER_ID_RE.match(layer_id):
        layer_id = f"text_{uuid.uuid4().hex[:12]}"
    result = new_layer(name=str(raw.get("name") or "Tekst"), layer_id=layer_id)
    result["enabled"] = bool(raw.get("enabled", True))
    result["order"] = _integer(raw.get("order"), fallback_order, 0, 10000)

    content_raw = raw.get("content")
    content = content_raw if isinstance(content_raw, dict) else {}
    kind = str(content.get("kind") or "paragraph")
    mode = str(content.get("mode") or "plain")
    result["content"] = {
        "kind": kind if kind in CONTENT_KINDS else "paragraph",
        "mode": mode if mode in ("plain", "adapted-code") else "plain",
        "text": str(content.get("text") or "")[:100000],
        "html": str(content.get("html") or "")[:250000],
    }

    layout_raw = raw.get("layout")
    layout = layout_raw if isinstance(layout_raw, dict) else {}
    layout_mode = str(layout.get("mode") or "flow")
    result["layout"] = {
        "mode": layout_mode if layout_mode in LAYOUT_MODES else "flow",
        "desktop": _normalize_device_layout(layout.get("desktop")),
        "tablet": (
            _normalize_device_layout(layout.get("tablet"))
            if isinstance(layout.get("tablet"), dict)
            else None
        ),
        "mobile": (
            _normalize_device_layout(layout.get("mobile"))
            if isinstance(layout.get("mobile"), dict)
            else None
        ),
    }

    motion_raw = raw.get("motion")
    motion = motion_raw if isinstance(motion_raw, dict) else {}
    result["motion"] = {
        "enter": _normalize_motion(motion.get("enter"), enter=True),
        "exit": _normalize_motion(motion.get("exit"), enter=False),
    }
    result["pin"] = _normalize_pin(raw.get("pin"))

    style_raw = raw.get("importedStyle")
    style = style_raw if isinstance(style_raw, dict) else {}
    urls = style.get("fontUrls")
    scoped_css = str(style.get("scopedCss") or "")[:300000]
    imported_component = result["content"]["mode"] == "adapted-code"
    behavior_raw = style.get("behavior")
    behavior = behavior_raw if isinstance(behavior_raw, dict) else {}
    trigger = str(behavior.get("trigger") or "section-progress")
    result["importedStyle"] = {
        "scopedCss": scoped_css,
        "fontUrls": [
            str(url)
            for url in (urls if isinstance(urls, list) else [])
            if str(url).startswith("https://fonts.googleapis.com/")
        ][:8],
        "componentMode": bool(
            style.get("componentMode", imported_component)
        ),
        "ownsMotion": bool(
            style.get("ownsMotion", ".is-entered" in scoped_css)
        ),
        "behavior": {
            "trigger": (
                trigger
                if trigger in {"section-progress", "intersection"}
                else "section-progress"
            ),
            "threshold": round(
                _number(behavior.get("threshold"), 0.08, 0, 1),
                3,
            ),
            "rootMargin": str(behavior.get("rootMargin") or "0px")[:100],
            "once": bool(behavior.get("once", False)),
        },
    }
    return result


def normalize_document(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    raw_sections = source.get("sections")
    sections = raw_sections if isinstance(raw_sections, dict) else {}
    normalized_sections: dict[str, list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()
    for section_key, rows in sections.items():
        key = str(section_key or "").strip()
        if not key or not isinstance(rows, list):
            continue
        out: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            layer = normalize_layer(row, fallback_order=index)
            if layer is None:
                continue
            if layer["id"] in seen_ids:
                layer["id"] = f"text_{uuid.uuid4().hex[:12]}"
            seen_ids.add(layer["id"])
            out.append(layer)
        if out:
            out.sort(key=lambda item: (int(item.get("order", 0)), str(item["id"])))
            for index, layer in enumerate(out):
                layer["order"] = index
            normalized_sections[key] = out
    return {"schemaVersion": SCHEMA_VERSION, "sections": normalized_sections}


def shared_variant_path(
    config: PageEditorConfig,
    variant_id: str,
    *,
    filename: str = TEXT_LAYER_FILENAME,
) -> Path:
    return config.component_dir / "data" / "variants" / str(variant_id) / filename


def load_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return empty_document()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_document()
    return normalize_document(raw)


def save_document(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_document(document)
    atomic_write_text(
        path,
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
    )
    return normalized


def layers_for_section(document: dict[str, Any], section_key: str) -> list[dict[str, Any]]:
    normalized = normalize_document(document)
    return copy.deepcopy(normalized["sections"].get(str(section_key), []))


def effective_device_layout(
    layer: dict[str, Any],
    device: str,
) -> dict[str, Any]:
    """Rozwiąż dziedziczenie mobile → tablet → desktop bez mutacji danych."""

    normalized = normalize_layer(layer)
    if normalized is None:
        return default_device_layout()
    layout = normalized["layout"]
    target = str(device or "desktop").lower()
    if target == "mobile":
        selected = layout.get("mobile") or layout.get("tablet") or layout["desktop"]
    elif target == "tablet":
        selected = layout.get("tablet") or layout["desktop"]
    else:
        selected = layout["desktop"]
    return copy.deepcopy(selected)


def set_section_layers(
    document: dict[str, Any],
    section_key: str,
    layers: list[dict[str, Any]],
) -> dict[str, Any]:
    next_document = normalize_document(document)
    key = str(section_key or "").strip()
    if not key:
        return next_document
    normalized_rows = normalize_document(
        {"sections": {key: layers}}
    )["sections"].get(key, [])
    if normalized_rows:
        next_document["sections"][key] = normalized_rows
    else:
        next_document["sections"].pop(key, None)
    return next_document


def validate_document(
    document: dict[str, Any],
    *,
    known_section_keys: Iterable[str] = (),
) -> list[dict[str, str]]:
    normalized = normalize_document(document)
    known = {str(key) for key in known_section_keys}
    issues: list[dict[str, str]] = []
    h1_count = 0
    for section_key, layers in normalized["sections"].items():
        if known and section_key not in known:
            issues.append(
                {
                    "level": "warn",
                    "section": section_key,
                    "message": "Warstwy wskazują sekcję, której nie ma w bieżącym wariancie.",
                }
            )
        for layer in layers:
            content = layer["content"]
            visible_text = content.get("text") or content.get("html")
            if not str(visible_text or "").strip():
                issues.append(
                    {
                        "level": "warn",
                        "section": section_key,
                        "message": f"«{layer['name']}» nie ma treści.",
                    }
                )
            if content.get("kind") == "h1":
                h1_count += 1
            enter = layer["motion"]["enter"]
            exit_cfg = layer["motion"]["exit"]
            if (
                enter.get("preset") != "none"
                and exit_cfg.get("preset") != "none"
                and int(exit_cfg.get("startPct", 80)) <= 20
            ):
                issues.append(
                    {
                        "level": "warn",
                        "section": section_key,
                        "message": f"«{layer['name']}»: animacja wyjścia zaczyna się zbyt wcześnie i może przykryć wejście.",
                    }
                )
            desktop_pin = layer["pin"]["desktop"]
            if desktop_pin.get("endVh") is not None:
                if int(desktop_pin["endVh"]) < int(desktop_pin.get("startVh", 0)):
                    issues.append(
                        {
                            "level": "error",
                            "section": section_key,
                            "message": f"«{layer['name']}»: koniec przypięcia jest przed początkiem.",
                        }
                    )
    if h1_count > 1:
        issues.append(
            {
                "level": "warn",
                "section": "",
                "message": f"Strona ma {h1_count} warstwy H1. Zwykle powinna mieć jeden główny H1.",
            }
        )
    return issues


def load_motion_preset_library() -> dict[str, Any]:
    path = _PRESET_CONFIG.read_path()
    if not path.is_file():
        return {"schemaVersion": 1, "enter": [], "exit": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schemaVersion": 1, "enter": [], "exit": []}
    if not isinstance(raw, dict):
        return {"schemaVersion": 1, "enter": [], "exit": []}
    result = {"schemaVersion": 1, "enter": [], "exit": []}
    for kind, is_enter in (("enter", True), ("exit", False)):
        rows = raw.get(kind)
        if not isinstance(rows, list):
            continue
        names: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            folded = name.casefold()
            if not name or folded in names:
                continue
            names.add(folded)
            result[kind].append(
                {
                    "id": str(row.get("id") or uuid.uuid4().hex),
                    "name": name[:120],
                    "values": _normalize_motion(row.get("values"), enter=is_enter),
                }
            )
    return result


def save_motion_preset_library(library: dict[str, Any]) -> dict[str, Any]:
    normalized = {"schemaVersion": 1, "enter": [], "exit": []}
    for kind, is_enter in (("enter", True), ("exit", False)):
        rows = library.get(kind) if isinstance(library, dict) else []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            normalized[kind].append(
                {
                    "id": str(row.get("id") or uuid.uuid4().hex),
                    "name": name[:120],
                    "values": _normalize_motion(row.get("values"), enter=is_enter),
                }
            )
    atomic_write_text(
        _PRESET_CONFIG.write_path,
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
    )
    return normalized


__all__ = [
    "ALIGNMENTS",
    "ANCHORS",
    "CONTENT_KINDS",
    "EASINGS",
    "ENTER_PRESETS",
    "EXIT_PRESETS",
    "LAYOUT_MODES",
    "SCHEMA_VERSION",
    "TEXT_LAYER_FILENAME",
    "UNITS",
    "empty_document",
    "effective_device_layout",
    "layers_for_section",
    "load_document",
    "load_motion_preset_library",
    "new_layer",
    "normalize_document",
    "normalize_layer",
    "save_document",
    "save_motion_preset_library",
    "set_section_layers",
    "shared_variant_path",
    "validate_document",
]
