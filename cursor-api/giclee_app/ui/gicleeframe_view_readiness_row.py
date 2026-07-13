"""GICLÉE FRAME™ — shared stateless readiness-row renderer boundary."""

from __future__ import annotations

import customtkinter as ctk

from . import theme
from .widgets import status_color


class GicleeFrameReadinessRowMixin:
    """Shared F1/F2 readiness-row renderer supplied to the host through MRO.

    The boundary owns no state, lifecycle, scheduling or orchestration. Brand
    and page-readiness panels retain row data and ordering ownership.
    """

    def _pack_readiness_row(
        self,
        parent: ctk.CTkFrame,
        label: str,
        value: str,
        ok: bool | None,
    ) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(
            frame,
            text="●",
            text_color=status_color(ok),
            width=20,
        ).pack(side="left")
        ctk.CTkLabel(
            frame,
            text=label,
            width=180,
            anchor="w",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
        ).pack(side="left")
        ctk.CTkLabel(
            frame,
            text=value,
            anchor="w",
            font=theme.get_font(11, "bold"),
        ).pack(side="left")


__all__ = ("GicleeFrameReadinessRowMixin",)
