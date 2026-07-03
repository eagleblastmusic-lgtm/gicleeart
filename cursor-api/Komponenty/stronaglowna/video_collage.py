"""Kolaż wideo hero — JSON, walidacja, eksport do motywu."""

from __future__ import annotations

import json
from typing import Any

from .service import resolve_shopify_file_download_url

ENTRY_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("none", "Bez (cut)"),
    ("fade_in", "Fade in"),
    ("dip_black", "Dip from black"),
    ("dip_white", "Dip from white"),
    ("push_left", "Push z prawej"),
    ("push_right", "Push z lewej"),
)

EXIT_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("none", "Bez (cut)"),
    ("fade_out", "Fade out"),
    ("dip_black", "Dip to black"),
    ("dip_white", "Dip to white"),
    ("push_left", "Push w lewo"),
    ("push_right", "Push w prawo"),
)

# Zachowanie wsteczne (stary jeden combobox)
TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("none", "Bez przejścia (cut)"),
    ("fade_in", "Fade in"),
    ("fade_out", "Fade out"),
    ("crossfade", "Crossfade / Dissolve"),
    ("dip_black", "Dip to black"),
    ("dip_white", "Dip to white"),
    ("push_left", "Push w lewo"),
    ("push_right", "Push w prawo"),
)

ENTRY_IDS = {t[0] for t in ENTRY_TRANSITIONS}
EXIT_IDS = {t[0] for t in EXIT_TRANSITIONS}
LEGACY_IDS = {t[0] for t in TRANSITIONS}

DEFAULT_TRANSITION_IN = "fade_in"
DEFAULT_TRANSITION_OUT = "fade_out"
DEFAULT_TRANSITION_MS = 800
DEFAULT_TRANSITION_IN_MS = 800
DEFAULT_TRANSITION_OUT_MS = 800


def empty_collage() -> dict[str, Any]:
    return {"loop": True, "clips": []}


def _normalize_ms(raw: Any, *, fallback: int = DEFAULT_TRANSITION_MS) -> int:
    try:
        ms = int(raw if raw is not None and raw != "" else fallback)
    except (TypeError, ValueError):
        ms = fallback
    return max(150, min(4000, ms))


def _clip_timing(item: dict[str, Any]) -> tuple[int, int]:
    """(transition_in_ms, transition_out_ms) z migracją ze starego transition_ms."""
    legacy = _normalize_ms(item.get("transition_ms"))
    in_ms = _normalize_ms(item.get("transition_in_ms"), fallback=legacy)
    out_ms = _normalize_ms(item.get("transition_out_ms"), fallback=legacy)
    return in_ms, out_ms


def _legacy_to_in_out(legacy: str, *, is_first: bool) -> tuple[str, str, bool]:
    """Stare pole transition → (in, out, cross_effect)."""
    legacy = (legacy or "").strip().lower()
    if legacy == "crossfade":
        return "fade_in", "fade_out", not is_first
    if legacy == "fade_in":
        return "fade_in", DEFAULT_TRANSITION_OUT, False
    if legacy == "fade_out":
        return DEFAULT_TRANSITION_IN, "fade_out", False
    if legacy in ENTRY_IDS:
        return legacy, DEFAULT_TRANSITION_OUT, False
    if legacy in EXIT_IDS:
        return DEFAULT_TRANSITION_IN, legacy, False
    if legacy in {"dip_black", "dip_white", "push_left", "push_right"}:
        return legacy, legacy, False
    return (DEFAULT_TRANSITION_IN if is_first else DEFAULT_TRANSITION_IN, DEFAULT_TRANSITION_OUT, False)


def parse_collage(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return empty_collage()
        if not isinstance(data, dict):
            return empty_collage()
    else:
        return empty_collage()

    clips_in = data.get("clips")
    if not isinstance(clips_in, list):
        clips_in = []

    clips: list[dict[str, Any]] = []
    for i, item in enumerate(clips_in):
        if not isinstance(item, dict):
            continue
        video = str(item.get("video") or item.get("ref") or "").strip()
        if not video:
            continue

        in_ms, out_ms = _clip_timing(item)
        cross = bool(item.get("cross_effect"))

        if "transition_in" in item or "transition_out" in item:
            tin = str(item.get("transition_in") or DEFAULT_TRANSITION_IN).strip().lower()
            tout = str(item.get("transition_out") or DEFAULT_TRANSITION_OUT).strip().lower()
            if tin not in ENTRY_IDS:
                tin = DEFAULT_TRANSITION_IN
            if tout not in EXIT_IDS:
                tout = DEFAULT_TRANSITION_OUT
        else:
            legacy = str(item.get("transition") or "").strip().lower()
            tin, tout, cross = _legacy_to_in_out(legacy, is_first=(i == 0))

        label = str(item.get("label") or "").strip()
        clip: dict[str, Any] = {
            "video": video,
            "transition_in": tin,
            "transition_out": tout,
            "transition_in_ms": in_ms,
            "transition_out_ms": out_ms,
            "cross_effect": cross,
        }
        if label:
            clip["label"] = label
        clips.append(clip)

    for i in range(1, len(clips)):
        if clips[i].get("cross_effect"):
            if clips[i - 1].get("transition_out") in (None, "", "none"):
                clips[i - 1]["transition_out"] = "fade_out"
            if clips[i].get("transition_in") in (None, "", "none"):
                clips[i]["transition_in"] = "fade_in"

    return {"loop": bool(data.get("loop", True)), "clips": clips}


def new_clip(*, is_first: bool) -> dict[str, Any]:
    return {
        "video": "",
        "transition_in": DEFAULT_TRANSITION_IN if is_first else DEFAULT_TRANSITION_IN,
        "transition_out": DEFAULT_TRANSITION_OUT,
        "transition_in_ms": DEFAULT_TRANSITION_IN_MS,
        "transition_out_ms": DEFAULT_TRANSITION_OUT_MS,
        "cross_effect": not is_first,
    }


def apply_cross_preset(clips: list[dict[str, Any]], idx: int) -> None:
    """Ustawia cross: poprzedni fade out + bieżący fade in jednocześnie."""
    if idx <= 0 or idx >= len(clips):
        return
    clips[idx - 1]["transition_out"] = "fade_out"
    clips[idx]["transition_in"] = "fade_in"
    clips[idx]["cross_effect"] = True


def serialize_collage(data: dict[str, Any]) -> str:
    parsed = parse_collage(data)
    return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))


def validate_collage(data: dict[str, Any]) -> list[str]:
    parsed = parse_collage(data)
    errors: list[str] = []
    if not parsed["clips"]:
        errors.append("Dodaj co najmniej jeden klip wideo do kolażu.")
        return errors
    for i, clip in enumerate(parsed["clips"], start=1):
        ref = str(clip.get("video") or "")
        if not ref.startswith("shopify://files/videos/"):
            errors.append(f"Klip {i}: brak prawidłowego pliku wideo (Shopify Files).")
    return errors


def resolve_collage_for_theme(data: dict[str, Any], *, logger: Any = None) -> dict[str, Any]:
    parsed = parse_collage(data)
    clips: list[dict[str, Any]] = []
    for clip in parsed["clips"]:
        ref = str(clip.get("video") or "")
        url = resolve_shopify_file_download_url(ref, logger=logger)
        if not url:
            continue
        out: dict[str, Any] = {
            "url": url,
            "transition_in": clip.get("transition_in", DEFAULT_TRANSITION_IN),
            "transition_out": clip.get("transition_out", DEFAULT_TRANSITION_OUT),
            "transition_in_ms": clip.get("transition_in_ms", DEFAULT_TRANSITION_IN_MS),
            "transition_out_ms": clip.get("transition_out_ms", DEFAULT_TRANSITION_OUT_MS),
            "cross_effect": bool(clip.get("cross_effect")),
        }
        if clip.get("label"):
            out["label"] = clip["label"]
        clips.append(out)
    return {"loop": parsed["loop"], "clips": clips}


def write_collage_asset(data: dict[str, Any], assets_dir: Any, *, logger: Any = None) -> None:
    payload = resolve_collage_for_theme(data, logger=logger)
    body = "window.GICLEE_HERO_VIDEO_COLLAGE = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "giclee-hero-video-collage.js").write_text(body, encoding="utf-8")
