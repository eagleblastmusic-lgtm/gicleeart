"""Katalog F3 — lokalny draft planu zmian. Tylko in-memory, bez I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

KatalogPlanIntent = Literal[
    "review_structure",
    "plan_collection_layout",
    "plan_zone_settings",
]

PLAN_SECTION_TITLE = "Plan zmian"
DRAFT_BADGE = "draft lokalny · niezapisany"
DRAFT_EMPTY_COPY = "Brak planu · wybierz intencję (i opcjonalnie wariant/strefę)"
DRAFT_DISCLAIMER = "local planning only · writer: not started · nic nie zapisano"
CLEAR_PLAN_LABEL = "Wyczyść plan"
CHECK_PLAN_LABEL = "Sprawdź plan"
PLAN_EMPTY_COPY = (
    "Wybierz intencję planu (i opcjonalnie wariant/strefę), następnie kliknij „Sprawdź plan”."
)

_INTENT_LABELS: dict[KatalogPlanIntent, str] = {
    "review_structure": "Przegląd struktury katalogu",
    "plan_collection_layout": "Plan układu collection.json",
    "plan_zone_settings": "Plan ustawień strefy",
}

_ZONE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("biography", "biography — bio"),
    ("showcase", "showcase — prezentacja"),
    ("works", "works — prace"),
)

_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_INTENT_PLACEHOLDER = "— wybierz intencję —"


@dataclass
class KatalogDraftState:
    """Draft planu zmian Katalog — wyłącznie w pamięci panelu Studio."""

    variant_id: str | None = None
    zone_id: str | None = None
    plan_intent: KatalogPlanIntent | None = None

    def is_empty(self) -> bool:
        return self.plan_intent is None

    def clear(self) -> None:
        self.variant_id = None
        self.zone_id = None
        self.plan_intent = None

    def set_variant(self, variant_id: str | None) -> None:
        value = (variant_id or "").strip()
        if not value or value == _VARIANT_PLACEHOLDER:
            self.variant_id = None
        else:
            self.variant_id = value

    def set_zone(self, zone_id: str | None) -> None:
        value = (zone_id or "").strip()
        if not value:
            self.zone_id = None
        else:
            self.zone_id = value

    def set_intent(self, intent: KatalogPlanIntent | str | None) -> None:
        if intent is None or intent == _INTENT_PLACEHOLDER:
            self.plan_intent = None
            return
        if intent in _INTENT_LABELS:
            self.plan_intent = intent  # type: ignore[assignment]
        else:
            self.plan_intent = None

    def intent_label_pl(self) -> str:
        if self.plan_intent is None:
            return "—"
        return _INTENT_LABELS.get(self.plan_intent, self.plan_intent)

    def zone_label_pl(self) -> str:
        for zid, label in _ZONE_OPTIONS:
            if zid == self.zone_id:
                return label
        return self.zone_id or "—"

    def format_summary(self, *, variant_label: str | None = None) -> str:
        if self.is_empty():
            return DRAFT_EMPTY_COPY
        parts = [f"Plan lokalny: {self.intent_label_pl()} · niezapisany"]
        if self.variant_id:
            label = variant_label or self.variant_id
            parts.append(f"wariant {label}")
        if self.zone_id:
            parts.append(f"strefa {self.zone_label_pl()}")
        return " · ".join(parts)


def intent_menu_options() -> tuple[tuple[KatalogPlanIntent, str], ...]:
    return tuple(_INTENT_LABELS.items())


def zone_menu_options() -> tuple[tuple[str, str], ...]:
    return _ZONE_OPTIONS


def variant_menu_options(
    variant_ids: tuple[str, ...],
    labels: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    """(variant_id, menu label) — bez ścieżek lokalnych."""
    if not variant_ids:
        return ()
    return tuple(
        (vid, f"{vid} — {labels.get(vid, vid)}")
        for vid in variant_ids
    )


def intent_requires_variant(intent: KatalogPlanIntent | None) -> bool:
    return intent in ("plan_collection_layout", "plan_zone_settings")


def intent_requires_zone(intent: KatalogPlanIntent | None) -> bool:
    return intent == "plan_zone_settings"
