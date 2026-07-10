"""Budowanie krótkich i pełnych promptów aktywacyjnych (schema v2)."""

from __future__ import annotations

from .data_loader import (
    SHOPIFY_SNAPSHOT_MODE_ID,
    Combination,
    WorkMode,
    WorkModeCatalog,
    resolve_modes_with_dependencies,
)

VEO_MODE_ID = "analyst_veo_flow_director"
SHOPIFY_MOTION_MODE_ID = "shopify_motion_interaction"

_VEO_MOTION_SPLIT = (
    "Rozdziel zadanie na dwa niezależne wątki:\n"
    "1) generowanie assetu/wideo (Veo / Flow / prompt generatywny),\n"
    "2) motion strony Shopify (CSS, JS, hover, scroll reveal).\n"
    "Nie mieszaj promptów generatywnych z implementacją motion motywu."
)


def command_for_mode(mode: WorkMode, profile_id: str | None = None) -> str:
    return mode.profile(profile_id).command


def _auto_added_snapshot(mode_ids: list[str], resolved_ids: list[str]) -> bool:
    return (
        SHOPIFY_SNAPSHOT_MODE_ID in resolved_ids
        and SHOPIFY_SNAPSHOT_MODE_ID not in mode_ids
    )


def _needs_veo_motion_split(resolved_ids: list[str]) -> bool:
    return VEO_MODE_ID in resolved_ids and SHOPIFY_MOTION_MODE_ID in resolved_ids


def _foundation_lines(catalog: WorkModeCatalog) -> list[str]:
    return [f"- {f.source_file}" for f in catalog.foundations]


def _mode_file_lines(
    modes: list[WorkMode],
    *,
    selected_ids: list[str],
    auto_snapshot: bool,
) -> list[str]:
    lines: list[str] = []
    for mode in modes:
        suffix = ""
        if auto_snapshot and mode.id == SHOPIFY_SNAPSHOT_MODE_ID:
            suffix = "  [auto]"
        if mode.source_file:
            lines.append(f"- {mode.source_file}{suffix}")
    return lines


def _command_lines(modes: list[WorkMode], profile_map: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for mode in modes:
        profile_id = profile_map.get(mode.id)
        lines.append(command_for_mode(mode, profile_id))
    return lines


def short_prompt_for_modes(
    catalog: WorkModeCatalog,
    mode_ids: list[str],
    *,
    profile_map: dict[str, str] | None = None,
) -> str:
    modes, resolved_profiles = resolve_modes_with_dependencies(
        catalog, mode_ids, profile_map=profile_map
    )
    if not modes:
        return ""
    commands = _command_lines(modes, resolved_profiles)
    return "\n".join(commands)


def full_prompt_for_modes(
    catalog: WorkModeCatalog,
    mode_ids: list[str],
    *,
    profile_map: dict[str, str] | None = None,
) -> str:
    modes, resolved_profiles = resolve_modes_with_dependencies(
        catalog, mode_ids, profile_map=profile_map
    )
    if not modes:
        return ""

    resolved_ids = [m.id for m in modes]
    auto_snapshot = _auto_added_snapshot(mode_ids, resolved_ids)
    lines: list[str] = []

    lines.append("Fundament (zawsze):")
    lines.extend(_foundation_lines(catalog))
    lines.append("")
    lines.append("Tryby:")
    file_lines = _mode_file_lines(
        modes, selected_ids=mode_ids, auto_snapshot=auto_snapshot
    )
    if file_lines:
        lines.extend(file_lines)
    else:
        lines.append("- (brak plików trybów)")
    lines.append("")
    lines.append("Komendy aktywujące:")
    lines.extend(_command_lines(modes, resolved_profiles))

    if _needs_veo_motion_split(resolved_ids):
        lines.append("")
        lines.append("Uwaga — rozdzielenie zadań:")
        lines.append(_VEO_MOTION_SPLIT)

    lines.append("")
    lines.append("[Wklej zadanie]")
    return "\n".join(lines)


def prompt_for_combination(
    catalog: WorkModeCatalog,
    combo: Combination,
    *,
    profile_map: dict[str, str] | None = None,
) -> str:
    return full_prompt_for_modes(catalog, list(combo.mode_ids), profile_map=profile_map)


def short_prompt_for_combination(
    catalog: WorkModeCatalog,
    combo: Combination,
    *,
    profile_map: dict[str, str] | None = None,
) -> str:
    return short_prompt_for_modes(catalog, list(combo.mode_ids), profile_map=profile_map)
