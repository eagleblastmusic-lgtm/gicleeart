"""HF-3A: bezpieczny planner struktury GICLÉE HOME FLOW.

Ten moduł zapisuje wyłącznie szkic do ``home_flow.json`` schema v2. Nie zmienia
``templates/index.json``, assetów motywu ani nie uruchamia deployu Shopify.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import uuid

from .home_flow import (
    DEFAULT_FLOW_ITEMS,
    HomeFlowItem,
    STRUCTURE_DRAFT_KEY,
    load_flow_metadata,
    number_flow_items,
    save_flow_metadata,
)


@dataclass(frozen=True)
class SectionBlueprint:
    blueprint_id: str
    label: str
    description: str
    supports_stack: bool
    supports_section_scroll: bool


@dataclass(frozen=True)
class StructureIssue:
    severity: str
    code: str
    message: str


SECTION_BLUEPRINTS: tuple[SectionBlueprint, ...] = (
    SectionBlueprint(
        "editorial-image",
        "Editorial — tekst i grafika",
        "Spokojna sekcja narracyjna z tekstem i pojedynczą grafiką.",
        True,
        True,
    ),
    SectionBlueprint(
        "editorial-video",
        "Editorial — tekst i film",
        "Sekcja narracyjna z filmem tła lub materiałem wideo.",
        True,
        True,
    ),
    SectionBlueprint(
        "comparison",
        "Porównanie przed / po",
        "Sekcja z kontrolowanym suwakiem porównawczym.",
        True,
        True,
    ),
    SectionBlueprint(
        "gallery",
        "Galeria dzieł",
        "Sekcja galerii z natywnym przewijaniem zawartości.",
        False,
        False,
    ),
)

CORE_SECTION_IDS: tuple[str, ...] = tuple(
    item.stable_id for item in DEFAULT_FLOW_ITEMS if item.kind == "section"
)
LOCKED_PREFIX: tuple[str, ...] = (
    "section:prehero",
    "section:hero",
    "section:intro",
)
LOCKED_SUFFIX: tuple[str, ...] = ("section:notice",)
CUSTOM_PREFIX = "section:draft:"


def blueprint_by_id(blueprint_id: str) -> SectionBlueprint | None:
    return next(
        (row for row in SECTION_BLUEPRINTS if row.blueprint_id == blueprint_id),
        None,
    )


def is_custom_section(stable_id: str) -> bool:
    return str(stable_id).startswith(CUSTOM_PREFIX)


def _default_section_order() -> list[str]:
    return list(CORE_SECTION_IDS)


def _clean_custom_sections(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []

    known_blueprints = {row.blueprint_id for row in SECTION_BLUEPRINTS}
    seen: set[str] = set()
    cleaned: list[dict[str, str]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        stable_id = str(row.get("stable_id") or "").strip()
        blueprint_id = str(row.get("blueprint_id") or "").strip()
        name = " ".join(str(row.get("name") or "").split()).strip()[:120]
        if (
            not is_custom_section(stable_id)
            or stable_id in seen
            or blueprint_id not in known_blueprints
            or not name
        ):
            continue
        seen.add(stable_id)
        cleaned.append(
            {
                "stable_id": stable_id,
                "blueprint_id": blueprint_id,
                "name": name,
            }
        )
    return cleaned


def _normalize_section_order(
    raw_order: Any,
    custom_sections: Iterable[dict[str, str]],
) -> list[str]:
    custom_ids = [row["stable_id"] for row in custom_sections]
    known = set(CORE_SECTION_IDS) | set(custom_ids)
    out: list[str] = []
    if isinstance(raw_order, list):
        for value in raw_order:
            stable_id = str(value).strip()
            if stable_id in known and stable_id not in out:
                out.append(stable_id)

    for stable_id in CORE_SECTION_IDS:
        if stable_id not in out:
            out.append(stable_id)
    for stable_id in custom_ids:
        if stable_id not in out:
            insert_at = max(len(out) - len(LOCKED_SUFFIX), len(LOCKED_PREFIX))
            out.insert(insert_at, stable_id)
    return out


def load_structure_draft(
    variant_id: str,
    *,
    variants_root=None,
) -> dict[str, Any]:
    metadata = load_flow_metadata(variant_id, variants_root=variants_root)
    raw = metadata.get(STRUCTURE_DRAFT_KEY)
    if not isinstance(raw, dict):
        raw = {}

    custom_sections = _clean_custom_sections(raw.get("custom_sections"))
    section_order = _normalize_section_order(raw.get("section_order"), custom_sections)
    return {
        "section_order": section_order,
        "custom_sections": custom_sections,
    }


def save_structure_draft(
    variant_id: str,
    draft: dict[str, Any],
    *,
    variants_root=None,
):
    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    section_order = _normalize_section_order(
        draft.get("section_order"),
        custom_sections,
    )
    issues = validate_structure_draft(
        {
            "section_order": section_order,
            "custom_sections": custom_sections,
        }
    )
    blockers = [issue for issue in issues if issue.severity == "blocker"]
    if blockers:
        raise ValueError("\n".join(issue.message for issue in blockers))

    metadata = load_flow_metadata(variant_id, variants_root=variants_root)
    metadata[STRUCTURE_DRAFT_KEY] = {
        "section_order": section_order,
        "custom_sections": custom_sections,
    }
    return save_flow_metadata(variant_id, metadata, variants_root=variants_root)


def reset_structure_draft(
    variant_id: str,
    *,
    variants_root=None,
):
    metadata = load_flow_metadata(variant_id, variants_root=variants_root)
    metadata.pop(STRUCTURE_DRAFT_KEY, None)
    return save_flow_metadata(variant_id, metadata, variants_root=variants_root)


def _custom_item(row: dict[str, str]) -> HomeFlowItem:
    return HomeFlowItem(
        stable_id=row["stable_id"],
        kind="section",
        default_name=row["name"],
        name=row["name"],
    )


def resolve_structure_items(
    variant_id: str,
    *,
    variants_root=None,
    draft: dict[str, Any] | None = None,
) -> tuple[HomeFlowItem, ...]:
    metadata = load_flow_metadata(variant_id, variants_root=variants_root)
    names = metadata.get("names") if isinstance(metadata, dict) else {}
    working = draft or load_structure_draft(variant_id, variants_root=variants_root)
    custom_sections = _clean_custom_sections(working.get("custom_sections"))
    section_order = _normalize_section_order(
        working.get("section_order"),
        custom_sections,
    )

    resolved_defaults: list[HomeFlowItem] = []
    for item in DEFAULT_FLOW_ITEMS:
        custom_name = " ".join(str((names or {}).get(item.stable_id) or "").split()).strip()
        if custom_name:
            item = HomeFlowItem(
                stable_id=item.stable_id,
                kind=item.kind,
                default_name=item.default_name,
                zone_id=item.zone_id,
                parent_id=item.parent_id,
                placement=item.placement,
                name=custom_name,
            )
        resolved_defaults.append(item)

    core_sections = {
        item.stable_id: item
        for item in resolved_defaults
        if item.kind == "section"
    }
    phases_by_parent: dict[str, list[HomeFlowItem]] = {}
    for item in resolved_defaults:
        if item.kind == "phase":
            phases_by_parent.setdefault(item.parent_id, []).append(item)

    custom_by_id = {
        row["stable_id"]: _custom_item(row)
        for row in custom_sections
    }

    out: list[HomeFlowItem] = []
    for stable_id in section_order:
        section = core_sections.get(stable_id) or custom_by_id.get(stable_id)
        if section is None:
            continue
        out.append(section)
        out.extend(phases_by_parent.get(stable_id, ()))
    return number_flow_items(out)


def validate_structure_draft(draft: dict[str, Any]) -> tuple[StructureIssue, ...]:
    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    order = _normalize_section_order(draft.get("section_order"), custom_sections)
    issues: list[StructureIssue] = []

    if tuple(order[: len(LOCKED_PREFIX)]) != LOCKED_PREFIX:
        issues.append(
            StructureIssue(
                "blocker",
                "LOCKED_PREFIX",
                "Pre-Hero, Hero i Intro muszą pozostać trzema pierwszymi sekcjami.",
            )
        )

    if tuple(order[-len(LOCKED_SUFFIX) :]) != LOCKED_SUFFIX:
        issues.append(
            StructureIssue(
                "blocker",
                "LOCKED_SUFFIX",
                "Powiadomienie strony głównej musi pozostać ostatnim elementem osi.",
            )
        )

    if len(order) != len(set(order)):
        issues.append(
            StructureIssue(
                "blocker",
                "DUPLICATE_SECTION",
                "Szkic zawiera zduplikowany identyfikator sekcji.",
            )
        )

    missing_core = [stable_id for stable_id in CORE_SECTION_IDS if stable_id not in order]
    if missing_core:
        issues.append(
            StructureIssue(
                "blocker",
                "MISSING_CORE",
                "Brakuje sekcji kanonicznych: " + ", ".join(missing_core),
            )
        )

    if len(custom_sections) > 20:
        issues.append(
            StructureIssue(
                "blocker",
                "CUSTOM_LIMIT",
                "Szkic może zawierać maksymalnie 20 nowych sekcji.",
            )
        )

    if custom_sections:
        issues.append(
            StructureIssue(
                "warning",
                "WRITER_REQUIRED",
                "Nowe sekcje są wyłącznie szkicem. Zastosowanie do index.json wymaga HF-3B.",
            )
        )

    if order != _default_section_order() or custom_sections:
        issues.append(
            StructureIssue(
                "info",
                "DRAFT_ONLY",
                "Zmiany dotyczą tylko szkicu wariantu i nie modyfikują motywu Shopify.",
            )
        )
    return tuple(issues)


def movable_section_ids(draft: dict[str, Any]) -> tuple[str, ...]:
    order = _normalize_section_order(
        draft.get("section_order"),
        _clean_custom_sections(draft.get("custom_sections")),
    )
    locked = set(LOCKED_PREFIX) | set(LOCKED_SUFFIX)
    return tuple(stable_id for stable_id in order if stable_id not in locked)


def move_section(
    draft: dict[str, Any],
    stable_id: str,
    direction: int,
) -> dict[str, Any]:
    if direction not in (-1, 1):
        raise ValueError("Kierunek musi wynosić -1 albo 1.")

    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    order = _normalize_section_order(draft.get("section_order"), custom_sections)
    if stable_id not in order:
        raise ValueError(f"Nieznana sekcja: {stable_id}")
    if stable_id in set(LOCKED_PREFIX) | set(LOCKED_SUFFIX):
        raise ValueError("Ta sekcja jest kotwicą Home Flow i nie może być przesuwana.")

    index = order.index(stable_id)
    target = index + direction
    min_index = len(LOCKED_PREFIX)
    max_index = len(order) - len(LOCKED_SUFFIX) - 1
    if target < min_index or target > max_index:
        raise ValueError("Sekcji nie można przesunąć poza bezpieczny obszar osi.")

    order[index], order[target] = order[target], order[index]
    return {
        "section_order": order,
        "custom_sections": custom_sections,
    }


def reorder_section(
    draft: dict[str, Any],
    source_id: str,
    target_id: str,
) -> dict[str, Any]:
    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    order = _normalize_section_order(draft.get("section_order"), custom_sections)
    if source_id == target_id:
        return {"section_order": order, "custom_sections": custom_sections}
    if source_id not in order or target_id not in order:
        raise ValueError("Nieznana sekcja źródłowa lub docelowa.")
    if source_id in set(LOCKED_PREFIX) | set(LOCKED_SUFFIX):
        raise ValueError("Kotwicy Home Flow nie można przeciągać.")
    if target_id in set(LOCKED_PREFIX) | set(LOCKED_SUFFIX):
        raise ValueError("Nie można upuścić sekcji na kotwicy Home Flow.")

    order.remove(source_id)
    target_index = order.index(target_id)
    order.insert(target_index, source_id)
    return {
        "section_order": order,
        "custom_sections": custom_sections,
    }


def add_custom_section(
    draft: dict[str, Any],
    blueprint_id: str,
    name: str,
    *,
    token: str | None = None,
) -> tuple[dict[str, Any], str]:
    blueprint = blueprint_by_id(blueprint_id)
    if blueprint is None:
        raise ValueError(f"Nieznany blueprint sekcji: {blueprint_id}")

    clean_name = " ".join(str(name or "").split()).strip()[:120]
    if not clean_name:
        raise ValueError("Nazwa nowej sekcji nie może być pusta.")

    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    order = _normalize_section_order(draft.get("section_order"), custom_sections)
    suffix = (token or uuid.uuid4().hex[:10]).strip().lower()
    suffix = "".join(ch for ch in suffix if ch.isalnum() or ch == "-")[:24]
    if not suffix:
        suffix = uuid.uuid4().hex[:10]
    stable_id = f"{CUSTOM_PREFIX}{suffix}"
    known = set(order)
    while stable_id in known:
        stable_id = f"{CUSTOM_PREFIX}{uuid.uuid4().hex[:10]}"

    custom_sections.append(
        {
            "stable_id": stable_id,
            "blueprint_id": blueprint.blueprint_id,
            "name": clean_name,
        }
    )
    insert_at = len(order) - len(LOCKED_SUFFIX)
    order.insert(insert_at, stable_id)
    return (
        {
            "section_order": order,
            "custom_sections": custom_sections,
        },
        stable_id,
    )


def remove_custom_section(
    draft: dict[str, Any],
    stable_id: str,
) -> dict[str, Any]:
    if not is_custom_section(stable_id):
        raise ValueError("Usuwać można wyłącznie nowe sekcje ze szkicu.")

    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    if stable_id not in {row["stable_id"] for row in custom_sections}:
        raise ValueError("Nie znaleziono wskazanej sekcji szkicu.")

    custom_sections = [
        row for row in custom_sections if row["stable_id"] != stable_id
    ]
    order = [
        value
        for value in _normalize_section_order(draft.get("section_order"), custom_sections)
        if value != stable_id
    ]
    return {
        "section_order": order,
        "custom_sections": custom_sections,
    }


def build_structure_plan(
    variant_id: str,
    draft: dict[str, Any],
    *,
    variants_root=None,
) -> dict[str, Any]:
    current_order = list(CORE_SECTION_IDS)
    custom_sections = _clean_custom_sections(draft.get("custom_sections"))
    draft_order = _normalize_section_order(draft.get("section_order"), custom_sections)
    issues = validate_structure_draft(
        {
            "section_order": draft_order,
            "custom_sections": custom_sections,
        }
    )

    custom_by_id = {row["stable_id"]: row for row in custom_sections}
    current_positions = {stable_id: index for index, stable_id in enumerate(current_order)}
    changes: list[str] = []

    for index, stable_id in enumerate(draft_order):
        if stable_id in custom_by_id:
            row = custom_by_id[stable_id]
            blueprint = blueprint_by_id(row["blueprint_id"])
            label = blueprint.label if blueprint else row["blueprint_id"]
            changes.append(
                f"DODAJ: {row['name']} · blueprint: {label} · pozycja {index + 1}"
            )
        elif current_positions.get(stable_id) != index:
            changes.append(
                f"PRZENIEŚ: {stable_id} · {current_positions.get(stable_id, -1) + 1} → {index + 1}"
            )

    blockers = [issue.message for issue in issues if issue.severity == "blocker"]
    warnings = [issue.message for issue in issues if issue.severity == "warning"]
    return {
        "variant_id": variant_id,
        "current_order": current_order,
        "draft_order": draft_order,
        "changes": changes,
        "blockers": blockers,
        "warnings": warnings,
        "changed": bool(changes),
        "ready_for_writer": bool(changes) and not blockers,
        "writer_available": False,
    }


def format_structure_plan(plan: dict[str, Any]) -> str:
    lines = [
        "HF-3A — PLAN STRUKTURY (TYLKO SZKIC)",
        f"Wariant: {plan.get('variant_id', '')}",
        "",
        "Bieżąca kolejność:",
        "  " + " → ".join(plan.get("current_order") or []),
        "",
        "Kolejność w szkicu:",
        "  " + " → ".join(plan.get("draft_order") or []),
        "",
        "Zmiany:",
    ]
    changes = list(plan.get("changes") or [])
    lines.extend(f"  • {row}" for row in changes)
    if not changes:
        lines.append("  • Brak zmian względem kanonicznej osi.")

    blockers = list(plan.get("blockers") or [])
    if blockers:
        lines.extend(["", "BLOKERY:"])
        lines.extend(f"  • {row}" for row in blockers)

    warnings = list(plan.get("warnings") or [])
    if warnings:
        lines.extend(["", "OSTRZEŻENIA:"])
        lines.extend(f"  • {row}" for row in warnings)

    lines.extend(
        [
            "",
            "Status:",
            (
                "  GOTOWE DO HF-3B (writer nie jest dostępny w tym etapie)."
                if plan.get("ready_for_writer")
                else "  Szkic nie zawiera zmian albo wymaga poprawy."
            ),
            "",
            "Ten plan nie modyfikuje templates/index.json ani Shopify.",
        ]
    )
    return "\n".join(lines)
