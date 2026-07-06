"""Save contract + dry-run tła section_background — Studio Preview (F5.4a / F5.4d).

Pure module: zero I/O zapisu, zero importów Komponenty.*.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from giclee_app.studio.background_asset_catalog import (
    build_background_asset_catalog,
    resolve_selected_asset_ref,
    validate_selected_asset_id,
)
from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_state import (
    STRONAGLOWNA_SECTION_BGS,
    SectionBgStatus,
    SectionBgZone,
    read_stronaglowna_active_variant,
    read_stronaglowna_index_template,
    section_bg_current_ref,
    section_bg_status,
)

SectionSaveKind = Literal["image", "video"]

SAVE_PLAN_SECTION_TITLE = "Plan zapisu"
DRY_RUN_BADGE = "dry-run · nic nie zapisano"
CHECK_SAVE_LABEL = "Sprawdź zapis"
F54A_DISCLAIMER = "Realny zapis będzie osobną fazą F5.4b."
F54D_DISCLAIMER = "F5.4d nie zapisuje — wybór ref przygotowuje F5.4b2."
SAVE_PLAN_EMPTY_COPY = (
    "Wybierz strefę i typ assetu w sekcji Draft, następnie kliknij „Sprawdź zapis”."
)
VIDEO_COLLAGE_SCOPE_ERROR = (
    "Typ kolaż wideo dotyczy hero (video_collage_json) — "
    "poza zakresem section_background F5.4."
)

_SECTION_BG_FIELD_NAMES: tuple[str, ...] = (
    "background_media",
    "background_image",
    "video",
    "background_overlay_pct",
)

_KIND_TO_STATUS: dict[SectionSaveKind, SectionBgStatus] = {
    "image": "obraz",
    "video": "wideo",
}


@dataclass(frozen=True)
class BackgroundSaveValidation:
    """Wynik walidacji żądania zapisu (bez I/O zapisu)."""

    ok: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class BackgroundSaveDryRun:
    """Plan zapisu — semantic diff bez wartości ref/URL."""

    ok: bool
    errors: tuple[str, ...]
    zone_field_id: str
    zone_label: str
    target_kind_pl: str
    current_status: SectionBgStatus
    change_summary: str
    type_unchanged: bool
    writable: bool
    fields_touched: tuple[str, ...]
    has_selected_ref: bool
    asset_draft_summary: str
    ref_change_summary: str


def save_plan_enabled_for_folder(folder_name: str) -> bool:
    return (folder_name or "").strip() == "stronaglowna"


def validate_background_save_request(
    draft: BackgroundDraftState,
    package_path: Path,
) -> BackgroundSaveValidation:
    """Walidacja draftu + read-only kontekstu aktywnego wariantu."""
    errors: list[str] = []

    if draft.is_empty():
        errors.append("Draft jest pusty — wybierz strefę i typ assetu.")

    zone = _zone_for_field_id(draft.zone_field_id)
    if draft.zone_field_id and zone is None:
        errors.append(f"Nieznana strefa: {draft.zone_field_id}")

    if draft.asset_kind == "video_collage":
        errors.append(VIDEO_COLLAGE_SCOPE_ERROR)
    elif draft.asset_kind is not None and draft.asset_kind not in ("image", "video"):
        errors.append(f"Nieobsługiwany typ assetu: {draft.asset_kind}")

    active = read_stronaglowna_active_variant(package_path)
    if active is None:
        errors.append("Brak aktywnego wariantu (manifest.json).")

    index_template = read_stronaglowna_index_template(package_path)
    if index_template is None:
        errors.append("Brak lub nieczytelny index.json aktywnego wariantu.")

    if zone is not None and index_template is not None:
        sections = index_template.get("sections")
        if not isinstance(sections, dict):
            errors.append("index.json — brak sekcji „sections”.")
        elif zone.section_key not in sections:
            errors.append(
                f"index.json — brak sekcji {zone.section_key} dla strefy {zone.field_id}."
            )
        else:
            section = sections.get(zone.section_key)
            if not isinstance(section, dict):
                errors.append(f"index.json — nieprawidłowa sekcja {zone.section_key}.")
            else:
                settings = section.get("settings")
                if settings is not None and not isinstance(settings, dict):
                    errors.append(
                        f"index.json — nieprawidłowe settings w {zone.section_key}."
                    )

    if draft.selected_asset_id:
        catalog = build_background_asset_catalog(package_path)
        if not validate_selected_asset_id(
            draft.selected_asset_id,
            catalog,
            asset_kind=draft.asset_kind,
        ):
            errors.append("Wybrany asset jest nieprawidłowy lub nie pasuje do typu draftu.")

    return BackgroundSaveValidation(ok=not errors, errors=tuple(errors))


def build_background_save_dry_run(
    draft: BackgroundDraftState,
    package_path: Path,
) -> BackgroundSaveDryRun:
    """Buduje plan zapisu (semantic diff) — bez I/O zapisu i bez mutacji plików."""
    validation = validate_background_save_request(draft, package_path)
    if not validation.ok:
        return BackgroundSaveDryRun(
            ok=False,
            errors=validation.errors,
            zone_field_id=draft.zone_field_id or "",
            zone_label="—",
            target_kind_pl="—",
            current_status="brak",
            change_summary="—",
            type_unchanged=False,
            writable=False,
            fields_touched=(),
            has_selected_ref=False,
            asset_draft_summary="—",
            ref_change_summary="—",
        )

    zone = _zone_for_field_id(draft.zone_field_id)
    assert zone is not None
    assert draft.asset_kind in ("image", "video")

    index_template = read_stronaglowna_index_template(package_path)
    assert index_template is not None

    catalog = build_background_asset_catalog(package_path)
    has_selected_ref = validate_selected_asset_id(
        draft.selected_asset_id,
        catalog,
        asset_kind=draft.asset_kind,
    )

    current = section_bg_status(index_template, zone)
    target_kind = draft.asset_kind
    target_pl = _KIND_TO_STATUS[target_kind]
    type_unchanged = current == target_pl
    change_summary = _build_change_summary(current, target_pl, has_selected_ref)
    writable = _is_writable(current, target_kind)
    asset_draft_summary = (
        "Asset draft: wybrany" if has_selected_ref else "Asset draft: brak"
    )
    ref_change_summary = _build_ref_change_summary(
        index_template,
        zone,
        draft,
        catalog,
        has_selected_ref=has_selected_ref,
    )

    return BackgroundSaveDryRun(
        ok=True,
        errors=(),
        zone_field_id=zone.field_id,
        zone_label=zone.label,
        target_kind_pl=target_pl,
        current_status=current,
        change_summary=change_summary,
        type_unchanged=type_unchanged,
        writable=writable,
        fields_touched=_SECTION_BG_FIELD_NAMES,
        has_selected_ref=has_selected_ref,
        asset_draft_summary=asset_draft_summary,
        ref_change_summary=ref_change_summary,
    )


def format_dry_run_summary(dry_run: BackgroundSaveDryRun) -> str:
    """Wielolinijkowy wynik dry-run dla panelu — bez URL, ref, ścieżek."""
    if not dry_run.ok:
        lines = [DRY_RUN_BADGE, ""]
        lines.extend(f"Błąd: {err}" for err in dry_run.errors)
        lines.append("")
        lines.append(F54A_DISCLAIMER)
        return "\n".join(lines)

    lines = [
        DRY_RUN_BADGE,
        "",
        f"Strefa: {dry_run.zone_field_id} ({dry_run.zone_label})",
        f"Typ draftu: {dry_run.target_kind_pl}",
        f"Obecny stan: {dry_run.current_status}",
        f"Zmiana: {dry_run.change_summary}",
        dry_run.asset_draft_summary,
        f"Asset: {dry_run.ref_change_summary}",
    ]
    if dry_run.type_unchanged:
        lines.append("Typ: bez zmian")
    elif dry_run.has_selected_ref:
        lines.append(f"Zmiana typu z wybranym assetem ({dry_run.target_kind_pl})")
    if not dry_run.writable and not dry_run.has_selected_ref:
        lines.append(
            "Uwaga: draft nie zawiera pliku assetu — wybierz ref w sekcji „Wybór assetu”."
        )
    if dry_run.fields_touched:
        fields = ", ".join(dry_run.fields_touched)
        lines.append(f"Pola (F5.4b2): {fields}")
    lines.append("")
    lines.append(F54D_DISCLAIMER)
    return "\n".join(lines)


def _zone_for_field_id(field_id: str | None) -> SectionBgZone | None:
    if not field_id:
        return None
    for zone in STRONAGLOWNA_SECTION_BGS:
        if zone.field_id == field_id:
            return zone
    return None


def _build_change_summary(
    current: SectionBgStatus,
    target_pl: str,
    has_selected_ref: bool,
) -> str:
    if current == target_pl:
        return f"{current} → {target_pl} (intencja typu)"
    if has_selected_ref:
        return f"{current} → {target_pl} z wybranym assetem"
    return f"{current} → {target_pl}"


def _build_ref_change_summary(
    template: dict,
    zone: SectionBgZone,
    draft: BackgroundDraftState,
    catalog,
    *,
    has_selected_ref: bool,
) -> str:
    if not has_selected_ref:
        return "brak wyboru ref"
    selected_ref = resolve_selected_asset_ref(catalog, draft.selected_asset_id)
    current_ref = section_bg_current_ref(template, zone)
    if selected_ref is None:
        return "nieprawidłowy wybór"
    if current_ref is None:
        return "brak ref → wybrany asset"
    if selected_ref == current_ref.ref:
        return "ten sam asset"
    return "inny asset"


def _is_writable(current: SectionBgStatus, target_kind: SectionSaveKind) -> bool:
    """F5.4b1 clear — bez ref w draft."""
    target_status = _KIND_TO_STATUS[target_kind]
    if current != target_status:
        return False
    return current != "brak"


__all__ = [
    "BackgroundSaveDryRun",
    "BackgroundSaveValidation",
    "CHECK_SAVE_LABEL",
    "DRY_RUN_BADGE",
    "F54A_DISCLAIMER",
    "F54D_DISCLAIMER",
    "SAVE_PLAN_EMPTY_COPY",
    "SAVE_PLAN_SECTION_TITLE",
    "VIDEO_COLLAGE_SCOPE_ERROR",
    "build_background_save_dry_run",
    "format_dry_run_summary",
    "save_plan_enabled_for_folder",
    "validate_background_save_request",
]
