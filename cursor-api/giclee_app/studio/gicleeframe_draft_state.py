"""GICLÉE FRAME™ — lokalny draft planu. Tylko in-memory, bez I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from giclee_app.studio.gicleeframe_brief import variant_by_id

GicleeFramePlacement = Literal[
    "hero",
    "section_intro",
    "product_page",
    "footer_mark",
]

PLAN_SECTION_TITLE = "Plan użycia komponentu"
DRAFT_BADGE = "draft lokalny · niezapisany"
DRAFT_DISCLAIMER = "local planning only · writer: not started · nic nie zapisano"
CLEAR_PLAN_LABEL = "Wyczyść wybór"
CHECK_PLAN_LABEL = "Sprawdź plan (dry-run)"
PLAN_EMPTY_COPY = (
    "Wybierz wariant koncepcyjny (i opcjonalnie strefę docelową), "
    "następnie kliknij „Sprawdź plan (dry-run)”."
)

_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_PLACEMENT_PLACEHOLDER = "— opcjonalnie: strefa —"

_PLACEMENT_LABELS: dict[GicleeFramePlacement, str] = {
    "hero": "hero — pierwszy ekran / intro",
    "section_intro": "section_intro — etykieta sekcji",
    "product_page": "product_page — strona produktu Giclée Frame",
    "footer_mark": "footer_mark — podpis marki w stopce",
}

_PLACEMENT_OPTIONS: tuple[tuple[str, str], ...] = tuple(
    (pid, label) for pid, label in _PLACEMENT_LABELS.items()
)


@dataclass
class GicleeFrameDraftState:
    """Draft planu GICLÉE FRAME™ — wyłącznie w pamięci panelu Studio."""

    variant_id: str | None = None
    placement_id: GicleeFramePlacement | None = None

    def is_empty(self) -> bool:
        return self.variant_id is None

    def clear(self) -> None:
        self.variant_id = None
        self.placement_id = None

    def set_variant(self, variant_id: str | None) -> None:
        value = (variant_id or "").strip()
        if not value or value == _VARIANT_PLACEHOLDER:
            self.variant_id = None
        else:
            self.variant_id = value

    def set_placement(self, placement_id: GicleeFramePlacement | str | None) -> None:
        if placement_id is None or placement_id == _PLACEMENT_PLACEHOLDER:
            self.placement_id = None
            return
        if placement_id in _PLACEMENT_LABELS:
            self.placement_id = placement_id  # type: ignore[assignment]
        else:
            self.placement_id = None

    def variant_label_pl(self) -> str:
        v = variant_by_id(self.variant_id)
        return v.label_pl if v else "—"

    def placement_label_pl(self) -> str:
        if self.placement_id is None:
            return "—"
        return _PLACEMENT_LABELS.get(self.placement_id, self.placement_id)

    def format_summary(self) -> str:
        if self.is_empty():
            return DRAFT_BADGE + "\n" + PLAN_EMPTY_COPY
        lines = [
            DRAFT_BADGE,
            f"Wariant: {self.variant_label_pl()}",
            f"Strefa docelowa: {self.placement_label_pl()}",
        ]
        v = variant_by_id(self.variant_id)
        if v:
            lines.append(f"Podpowiedź: {v.usage_hint}")
        return "\n".join(lines)


def placement_menu_options() -> list[tuple[str, str]]:
    return list(_PLACEMENT_OPTIONS)
