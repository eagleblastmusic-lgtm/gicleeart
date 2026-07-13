"""GICLÉE FRAME™ — stateful F2 structure dry-run panel boundary (RAM only)."""

from __future__ import annotations

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    CHECK_STRUCTURE_LABEL,
    STRUCTURE_EMPTY_STATE,
)
from giclee_app.studio.gicleeframe_page_dry_run import (
    build_page_structure_dry_run,
    format_structure_dry_run_summary,
)
from giclee_app.studio.gicleeframe_readiness import (
    evaluate_gicleeframe_page_readiness,
    format_page_readiness_block,
)

from . import theme
from .gicleeframe_view_primitives import (
    _CARD_PAD_X,
    _make_card_title,
    _make_empty_state,
    _make_gf_card,
    _make_secondary_button,
)

_STRUCTURE_DRY_RUN_WRAPLENGTH = 292


class GicleeFrameStructureDryRunMixin:
    """F2 structure dry-run UI and synchronous RAM-only action boundary.

    The host retains control-column composition, inventory implementation,
    safety, lifecycle, scheduling, selection and editor ownership. Page
    readiness rendering is supplied by ``GicleeFramePageReadinessMixin``.
    """

    def _build_control_structure_card(self, parent: ctk.CTkFrame) -> None:
        structure_card = _make_gf_card(parent, variant="panel_deep", radius=16)
        structure_card.pack(fill="x", pady=(0, 10))
        _make_card_title(
            structure_card,
            "Podgląd struktury",
            "Kontrola struktury aktualnego wariantu RAM.",
        ).pack(fill="x", padx=_CARD_PAD_X, pady=(12, 6))
        self._structure_dry_run_btn = _make_secondary_button(
            structure_card,
            CHECK_STRUCTURE_LABEL,
            self._run_structure_dry_run,
            subtle=True,
        )
        self._structure_dry_run_btn.pack(
            anchor="w",
            padx=_CARD_PAD_X,
            pady=(0, 8),
        )
        self._structure_dry_label = _make_empty_state(
            structure_card,
            STRUCTURE_EMPTY_STATE,
            wraplength=_STRUCTURE_DRY_RUN_WRAPLENGTH,
        )
        self._structure_dry_label.pack(
            fill="x",
            padx=_CARD_PAD_X,
            pady=(0, 12),
        )

    def _reset_structure_dry_run_display(self) -> None:
        if self._structure_dry_label:
            self._structure_dry_label.configure(
                text=STRUCTURE_EMPTY_STATE,
                text_color=theme.TextMuted,
            )

    def _run_structure_dry_run(self) -> None:
        if self._inventory is None:
            self._refresh_inventory(warn_if_draft=False)
        inv = self._inventory
        if inv is None:
            return
        dry = build_page_structure_dry_run(inv, self._page_draft)
        ready = evaluate_gicleeframe_page_readiness(inv, dry)
        full = (
            format_structure_dry_run_summary(dry)
            + "\n\n"
            + format_page_readiness_block(ready)
        )
        if self._structure_dry_label:
            self._structure_dry_label.configure(
                text=full,
                text_color=theme.TextPrimary,
            )
        self._fill_page_readiness(ready)
        if self._on_status:
            self._on_status(dry.status_badge)


__all__ = (
    "GicleeFrameStructureDryRunMixin",
    "_STRUCTURE_DRY_RUN_WRAPLENGTH",
)
