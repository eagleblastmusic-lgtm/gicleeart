"""Read-only podsumowanie lokalnego stanu tła — Studio Preview (F4.3b / F5.1b)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SectionBgStatus = Literal["obraz", "wideo", "brak"]
SectionBgRefKind = Literal["image", "video"]

_TLDOBIO_COLLECTIONS = "data/collections.json"
_STRONAGLOWNA_MANIFEST = "data/variants/manifest.json"
_STRONAGLOWNA_VARIANT_INDEX = "data/variants/{variant_id}/index.json"

_TLDOBIO_NO_CACHE = (
    "Brak lokalnego cache · tło zarządzane w komponencie Tło do Bio"
)
_TLDOBIO_BAD_JSON = "Cache lokalny: nieczytelny · otwórz komponent inline"
_STRONAGLOWNA_NO_VARIANT = (
    "Nie udało się odczytać lokalnego stanu wariantu · "
    "5 stref section_background w komponencie Strona główna"
)


@dataclass(frozen=True)
class SectionBgZone:
    field_id: str
    section_key: str
    label: str


STRONAGLOWNA_SECTION_BGS: tuple[SectionBgZone, ...] = (
    SectionBgZone("ga_background", "section_ThWw4Q", "Giclée Art — intro"),
    SectionBgZone("rest_background", "section_XwRNDp", "Odrestaurowywanie dzieł"),
    SectionBgZone("cc_background", "section_bj9cY3", "Autorska korekcja kolorystyczna"),
    SectionBgZone("pot_background", "section_p9Kcm6", "Potencjał ukryty w zdjęciu"),
    SectionBgZone("sd_background", "section_P9LgB3", "Zobacz różnicę"),
)


@dataclass(frozen=True)
class BackgroundStateSummary:
    """Wielolinijkowy tekst sekcji „Aktualny stan”."""

    text: str


@dataclass(frozen=True)
class SectionBgCurrentRef:
    """Aktualny ref strefy — tylko do contract/readiness, nie do UI."""

    kind: SectionBgRefKind
    ref: str


def _strip_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def _path_get(root: Any, path: tuple[str, ...]) -> Any:
    cur = root
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(_strip_json_header(raw))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def read_stronaglowna_active_variant(package_path: Path) -> tuple[str, str] | None:
    """Read-only aktywny wariant z manifest.json — bez load_manifest()."""
    manifest_path = package_path / _STRONAGLOWNA_MANIFEST
    manifest = _read_json_file(manifest_path)
    if manifest is None:
        return None
    active = str(manifest.get("active") or "").strip()
    if not active:
        return None
    label = active
    variants = manifest.get("variants")
    if isinstance(variants, list):
        for row in variants:
            if isinstance(row, dict) and str(row.get("id") or "") == active:
                label = str(row.get("label") or active)
                break
    return active, label


def read_stronaglowna_index_template(package_path: Path) -> dict[str, Any] | None:
    """Read-only index.json aktywnego wariantu."""
    active_info = read_stronaglowna_active_variant(package_path)
    if active_info is None:
        return None
    index_path = package_path / _STRONAGLOWNA_VARIANT_INDEX.format(
        variant_id=active_info[0]
    )
    return _read_json_file(index_path)


def section_bg_status(template: dict[str, Any], zone: SectionBgZone) -> SectionBgStatus:
    settings = ("sections", zone.section_key, "settings")
    media = str(_path_get(template, (*settings, "background_media")) or "none").strip().lower()
    if media == "video":
        ref = str(_path_get(template, (*settings, "video")) or "").strip()
        return "wideo" if ref else "brak"
    if media == "image":
        ref = str(_path_get(template, (*settings, "background_image")) or "").strip()
        return "obraz" if ref else "brak"
    ref = str(_path_get(template, (*settings, "background_image")) or "").strip()
    if not ref:
        return "brak"
    if "/videos/" in ref or ref.startswith("gid://shopify/Video/"):
        return "wideo"
    if ref.startswith("shopify://") or ref.startswith("http"):
        return "obraz"
    return "brak"


def section_bg_current_ref(
    template: dict[str, Any],
    zone: SectionBgZone,
) -> SectionBgCurrentRef | None:
    """Read-only kind + ref dla strefy — None gdy brak tła."""
    status = section_bg_status(template, zone)
    if status == "brak":
        return None
    settings = ("sections", zone.section_key, "settings")
    if status == "wideo":
        ref = str(_path_get(template, (*settings, "video")) or "").strip()
        if not ref:
            return None
        return SectionBgCurrentRef(kind="video", ref=ref)
    ref = str(_path_get(template, (*settings, "background_image")) or "").strip()
    if not ref:
        return None
    return SectionBgCurrentRef(kind="image", ref=ref)


def stronaglowna_zone_statuses(
    package_path: Path,
) -> tuple[tuple[str, str] | None, list[tuple[SectionBgZone, SectionBgStatus]] | None]:
    """Aktywny wariant + statusy stref; None w liście gdy brak index."""
    active_info = read_stronaglowna_active_variant(package_path)
    index_template = read_stronaglowna_index_template(package_path)
    if index_template is None:
        return active_info, None
    rows = [
        (zone, section_bg_status(index_template, zone)) for zone in STRONAGLOWNA_SECTION_BGS
    ]
    return active_info, rows


def _summarize_tldobio(package_path: Path) -> BackgroundStateSummary:
    path = package_path / _TLDOBIO_COLLECTIONS
    if not path.is_file():
        return BackgroundStateSummary(_TLDOBIO_NO_CACHE)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return BackgroundStateSummary(_TLDOBIO_BAD_JSON)
    if not isinstance(data, dict):
        return BackgroundStateSummary(_TLDOBIO_BAD_JSON)
    backgrounds = data.get("backgrounds")
    if not isinstance(backgrounds, dict):
        return BackgroundStateSummary(_TLDOBIO_BAD_JSON)
    total = len(backgrounds)
    with_bg = 0
    for row in backgrounds.values():
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or "").strip()
        if url:
            with_bg += 1
    lines = [
        f"Cache lokalny: {total} kolekcji · {with_bg} z zapisanym tłem",
        "Źródło prawdy: Shopify (komponent inline) · podgląd nie synchronizuje live",
    ]
    return BackgroundStateSummary("\n".join(lines))


def _summarize_stronaglowna(package_path: Path) -> BackgroundStateSummary:
    active_info, zone_rows = stronaglowna_zone_statuses(package_path)
    lines: list[str] = []
    if active_info is not None:
        active_id, active_label = active_info
        lines.append(f"Aktywny wariant: {active_id} · {active_label}")
    else:
        lines.append("Aktywny wariant: nieznany (brak manifest.json)")

    lines.append(
        f"Strefy section_background: {len(STRONAGLOWNA_SECTION_BGS)} (zdefiniowane w edytorze)"
    )

    if zone_rows is None:
        lines.append(_STRONAGLOWNA_NO_VARIANT)
        for zone in STRONAGLOWNA_SECTION_BGS:
            lines.append(f"· {zone.field_id} ({zone.label}): —")
        return BackgroundStateSummary("\n".join(lines))

    statuses = [status for _, status in zone_rows]
    for zone, status in zone_rows:
        lines.append(f"· {zone.field_id} ({zone.label}): {status}")

    set_count = sum(1 for s in statuses if s != "brak")
    lines.insert(
        2,
        f"Ustawione tło: {set_count}/{len(STRONAGLOWNA_SECTION_BGS)} · "
        f"brak: {len(statuses) - set_count}",
    )
    return BackgroundStateSummary("\n".join(lines))


def summarize_background_state(folder_name: str, package_path: Path) -> BackgroundStateSummary:
    """Read-only summary dla panelu tła — bez importu Komponenty.*."""
    key = (folder_name or "").strip()
    root = Path(package_path)
    if key == "tldobio":
        return _summarize_tldobio(root)
    if key == "stronaglowna":
        return _summarize_stronaglowna(root)
    return BackgroundStateSummary("Brak podsumowania stanu dla tego komponentu.")


__all__ = [
    "BackgroundStateSummary",
    "SectionBgCurrentRef",
    "SectionBgRefKind",
    "SectionBgZone",
    "SectionBgStatus",
    "STRONAGLOWNA_SECTION_BGS",
    "read_stronaglowna_active_variant",
    "read_stronaglowna_index_template",
    "section_bg_current_ref",
    "section_bg_status",
    "stronaglowna_zone_statuses",
    "summarize_background_state",
]
