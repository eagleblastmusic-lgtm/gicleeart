"""GICLÉE FRAME™ — stateful F2 page-readiness panel boundary (RAM only)."""

from __future__ import annotations

import customtkinter as ctk

from giclee_app.studio.gicleeframe_readiness import (
    GicleeFramePageReadiness,
    readiness_page_display_rows,
)

from . import theme
from .gicleeframe_view_primitives import (
    _CARD_PAD_X,
    _make_gf_card,
    _make_status_pill,
    _make_surface,
)

_PAGE_READINESS_TITLE = "Readiness (strona)"


class GicleeFramePageReadinessMixin:
    """F2 page-readiness UI supplied to ``GicleeFrameView`` by composition.

    The host owns control-column composition, structure dry-run orchestration,
    the shared readiness-row renderer and all widget lifecycle/scheduling.
    This mixin deliberately has no ``__init__`` and no Tk widget base class.
    """

    def _build_control_readiness_card(self, parent: ctk.CTkFrame) -> None:
        readiness_card = _make_gf_card(parent, variant="panel_deep", radius=16)
        readiness_card.pack(fill="x", pady=(0, 10))
        header_row = ctk.CTkFrame(readiness_card, fg_color="transparent")
        header_row.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 6))
        self._page_readiness_toggle = ctk.CTkButton(
            header_row,
            text=f"▸ {_PAGE_READINESS_TITLE}",
            anchor="w",
            height=28,
            fg_color="transparent",
            hover_color=theme.CardHover,
            text_color=theme.TextPrimary,
            font=theme.get_font(11, "bold"),
            command=self._toggle_page_readiness,
        )
        self._page_readiness_toggle.pack(side="left", fill="x", expand=True)
        self._page_readiness_badge = _make_status_pill(
            header_row,
            "0 gotowe · 6 zablokowane",
            bold=True,
            fg_color=theme.AppBg,
        )
        self._page_readiness_badge.pack(side="right")
        self._page_readiness_summary = ctk.CTkLabel(
            readiness_card,
            text="",
            font=theme.get_font(0),
            height=0,
        )
        self._page_readiness_summary.pack_forget()
        self._page_readiness_body = ctk.CTkFrame(readiness_card, fg_color="transparent")
        self._page_readiness_frame = _make_surface(
            self._page_readiness_body,
            fg_color=theme.AppBg,
        )
        self._page_readiness_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 12))
        self._fill_page_readiness(None)

    def _toggle_page_readiness(self) -> None:
        if self._page_readiness_body is None or self._page_readiness_toggle is None:
            return
        expanded = not self._page_readiness_expanded.get()
        self._page_readiness_expanded.set(expanded)
        if expanded:
            self._page_readiness_body.pack(fill="x")
            self._page_readiness_toggle.configure(text=f"▾ {_PAGE_READINESS_TITLE}")
        else:
            self._page_readiness_body.pack_forget()
            self._page_readiness_toggle.configure(text=f"▸ {_PAGE_READINESS_TITLE}")

    def _page_readiness_summary_text(self, ready: object | None) -> str:
        r = ready if isinstance(ready, GicleeFramePageReadiness) else None
        rows = readiness_page_display_rows(r)
        ready_n = sum(1 for row in rows if row.ok is True)
        blocked_n = sum(1 for row in rows if row.ok is False)
        if r is not None:
            return f"{r.status_label} · {ready_n} gotowe · {blocked_n} zablokowane"
        return f"{ready_n} gotowe · {blocked_n} zablokowane · rozwiń szczegóły"

    def _fill_page_readiness(self, ready: object | None) -> None:
        if self._page_readiness_frame is None:
            return
        summary = self._page_readiness_summary_text(ready)
        if self._page_readiness_badge is not None:
            self._page_readiness_badge.configure(text=summary)
        if self._page_readiness_summary is not None:
            self._page_readiness_summary.configure(text=summary)
        for child in self._page_readiness_frame.winfo_children():
            child.destroy()

        r = ready if isinstance(ready, GicleeFramePageReadiness) else None
        inner = ctk.CTkFrame(self._page_readiness_frame, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)
        for row in readiness_page_display_rows(r):
            self._pack_readiness_row(inner, row.label, row.value, row.ok)


__all__ = (
    "GicleeFramePageReadinessMixin",
    "_PAGE_READINESS_TITLE",
)
