"""GICLÉE FRAME™ — static F2 safety-card boundary (RAM only)."""

from __future__ import annotations

import customtkinter as ctk

from .gicleeframe_view_primitives import (
    _CARD_PAD_X,
    _build_safety_row,
    _make_card_title,
    _make_gf_card,
)

_SAFETY_TITLE = "Bezpieczeństwo"
_SAFETY_CHECKLIST: tuple[tuple[str, str], ...] = (
    ("RAM-only", "Zmiany tylko w pamięci sesji"),
    ("Brak zapisu motywu", "Panel nie zapisuje plików motywu"),
    ("Sync/deploy zablokowane", "Synchronizacja i wdrożenie wyłączone"),
    ("F3/F4 osobna decyzja", "Lokalny zapis i writer — po akceptacji"),
)
_SAFETY_ROW_WRAPLENGTH = 276


class GicleeFrameSafetyCardMixin:
    """Static safety card rendered by the host-owned control-column composer."""

    def _build_safety_card(self, parent: ctk.CTkFrame) -> None:
        card = _make_gf_card(parent, variant="panel_deep", radius=16)
        card.pack(fill="x")
        _make_card_title(card, _SAFETY_TITLE).pack(
            fill="x",
            padx=_CARD_PAD_X,
            pady=(12, 8),
        )
        for title, detail in _SAFETY_CHECKLIST:
            _build_safety_row(
                card,
                title,
                detail,
                wraplength=_SAFETY_ROW_WRAPLENGTH,
            )
        ctk.CTkLabel(card, text="", height=4).pack()


__all__ = (
    "GicleeFrameSafetyCardMixin",
    "_SAFETY_TITLE",
    "_SAFETY_CHECKLIST",
    "_SAFETY_ROW_WRAPLENGTH",
)
