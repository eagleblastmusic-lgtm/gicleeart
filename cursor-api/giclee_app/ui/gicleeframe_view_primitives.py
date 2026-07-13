"""Stateless UI primitives and local visual tokens for GICLÉE FRAME."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from . import theme

__all__ = (
    "_BTN_HEIGHT",
    "_CARD_PAD_X",
    "_CARD_PAD_Y",
    "_GF_BG",
    "_GF_PANEL",
    "_GF_CARD",
    "_GF_CARD_SOFT",
    "_GF_FIELD",
    "_GF_FIELD_HOVER",
    "_GF_BORDER",
    "_GF_BORDER_WARM",
    "_GF_GOLD_SOFT",
    "_GF_GOLD",
    "_GF_MUTED",
    "_GF_PREVIEW_BG",
    "_GF_PREVIEW_PAPER",
    "_GF_PREVIEW_MAT",
    "_GF_SUCCESS",
    "_GF_DANGER",
    "_f2_entry_kwargs",
    "_make_surface",
    "_make_card",
    "_make_gf_card",
    "_make_section_caption",
    "_make_card_title",
    "_make_section_title",
    "_make_status_pill",
    "_make_pill",
    "_make_empty_state",
    "_build_safety_row",
    "_make_secondary_button",
    "_make_primary_button",
    "_f2_menu_kwargs",
    "_element_pill_colors",
)

_BTN_HEIGHT = 28
_CARD_PAD_X = 14
_CARD_PAD_Y = 12

# F2.2.6 — local neutral gray palette for GICLÉE FRAME workbench.
# Lokalnie dla tego widoku; nie zmienia globalnego theme.py.
_GF_BG = "#161618"
_GF_PANEL = "#1e1e21"
_GF_CARD = "#27272a"
_GF_CARD_SOFT = "#303033"
_GF_FIELD = "#1a1a1c"
_GF_FIELD_HOVER = "#353538"
_GF_BORDER = "#3d3d42"
_GF_BORDER_WARM = "#52525a"
_GF_GOLD_SOFT = "#8a8270"
_GF_GOLD = "#b8a878"
_GF_MUTED = "#9a9a9f"
_GF_PREVIEW_BG = "#131315"
_GF_PREVIEW_PAPER = "#2e2e32"
_GF_PREVIEW_MAT = "#222225"
_GF_SUCCESS = "#7a9480"
_GF_DANGER = "#a07068"


def _f2_entry_kwargs() -> dict:
    return {
        "height": 32,
        "fg_color": _GF_FIELD,
        "border_width": 1,
        "border_color": _GF_BORDER,
    }


def _make_surface(
    master: ctk.CTkBaseClass,
    *,
    fg_color: str | None = None,
    radius: int = 10,
) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        master,
        fg_color=fg_color or theme.PanelBg,
        corner_radius=radius,
    )


def _make_card(
    master: ctk.CTkBaseClass,
    *,
    fg_color: str | None = None,
    bordered: bool = True,
    radius: int = 10,
) -> ctk.CTkFrame:
    kwargs: dict = {
        "fg_color": fg_color or theme.PanelBg,
        "corner_radius": radius,
    }
    if bordered:
        kwargs["border_width"] = 1
        kwargs["border_color"] = theme.BorderSubtle
    return ctk.CTkFrame(master, **kwargs)


def _make_gf_card(
    master: ctk.CTkBaseClass,
    *,
    variant: str = "panel",
    bordered: bool = False,
    radius: int = 14,
) -> ctk.CTkFrame:
    if variant == "soft":
        fg = _GF_CARD_SOFT
    elif variant == "field":
        fg = _GF_FIELD
    elif variant == "preview":
        fg = _GF_PREVIEW_BG
    elif variant == "panel_deep":
        fg = _GF_PANEL
    else:
        fg = _GF_CARD

    kwargs: dict = {
        "fg_color": fg,
        "corner_radius": radius,
    }
    if bordered:
        kwargs["border_width"] = 1
        kwargs["border_color"] = _GF_BORDER
    return ctk.CTkFrame(master, **kwargs)


def _make_section_caption(
    master: ctk.CTkBaseClass,
    text: str,
) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master,
        text=text.upper(),
        font=theme.get_font(9, "bold"),
        text_color=theme.AccentGoldDim,
        anchor="w",
    )


def _make_card_title(
    master: ctk.CTkBaseClass,
    title: str,
    subtitle: str | None = None,
) -> ctk.CTkFrame:
    row = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(
        row,
        text=title,
        font=theme.get_font(13, "bold"),
        text_color=theme.TextPrimary,
        anchor="w",
    ).pack(fill="x")
    if subtitle:
        ctk.CTkLabel(
            row,
            text=subtitle,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
            wraplength=420,
        ).pack(fill="x", pady=(2, 0))
    return row


def _make_section_title(
    master: ctk.CTkBaseClass,
    text: str,
    *,
    size: int = 11,
) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master,
        text=text,
        font=theme.get_font(size, "bold"),
        text_color=theme.TextPrimary,
        anchor="w",
    )


def _make_status_pill(
    master: ctk.CTkBaseClass,
    text: str,
    *,
    bold: bool = False,
    fg_color: str | None = None,
    text_color: str | None = None,
    accent: bool = False,
) -> ctk.CTkLabel:
    if accent:
        fg = fg_color or _GF_FIELD
        tc = text_color or _GF_GOLD_SOFT
    else:
        fg = fg_color or _GF_FIELD
        tc = text_color or _GF_MUTED
    return ctk.CTkLabel(
        master,
        text=text,
        font=theme.get_font(10, "bold" if (bold or accent) else "normal"),
        text_color=tc,
        fg_color=fg,
        corner_radius=999,
        padx=10,
        pady=4,
    )


def _make_pill(
    master: ctk.CTkBaseClass,
    text: str,
    *,
    bold: bool = False,
    fg_color: str | None = None,
    text_color: str | None = None,
) -> ctk.CTkLabel:
    return _make_status_pill(
        master,
        text,
        bold=bold,
        fg_color=fg_color,
        text_color=text_color,
    )


def _make_empty_state(
    master: ctk.CTkBaseClass,
    text: str,
    *,
    wraplength: int = 240,
) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master,
        text=text,
        font=theme.get_font(10),
        text_color=theme.TextMuted,
        anchor="nw",
        justify="left",
        wraplength=wraplength,
    )


def _build_safety_row(
    parent: ctk.CTkBaseClass,
    title: str,
    detail: str,
    *,
    wraplength: int = 240,
) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=12, pady=(0, 10))
    ctk.CTkLabel(
        row,
        text="•",
        width=18,
        text_color=_GF_GOLD_SOFT,
        font=theme.get_font(11, "bold"),
    ).pack(side="left", anchor="n")
    body = ctk.CTkFrame(row, fg_color="transparent")
    body.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(
        body,
        text=title,
        font=theme.get_font(10, "bold"),
        text_color=theme.TextPrimary,
        anchor="w",
    ).pack(fill="x")
    ctk.CTkLabel(
        body,
        text=detail,
        font=theme.get_font(9),
        text_color=_GF_MUTED,
        anchor="w",
        wraplength=wraplength,
    ).pack(fill="x", pady=(2, 0))


def _make_secondary_button(
    master: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
    *,
    width: int | None = None,
    subtle: bool = False,
) -> ctk.CTkButton:
    kwargs: dict = {
        "text": text,
        "height": _BTN_HEIGHT,
        "fg_color": "transparent" if subtle else _GF_FIELD,
        "hover_color": _GF_FIELD_HOVER,
        "border_width": 0 if subtle else 1,
        "border_color": _GF_BORDER,
        "text_color": theme.TextPrimary,
        "font": theme.get_font(11),
        "command": command,
    }
    if width is not None:
        kwargs["width"] = width
    return ctk.CTkButton(master, **kwargs)


def _make_primary_button(
    master: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
    *,
    width: int = 220,
) -> ctk.CTkButton:
    return ctk.CTkButton(
        master,
        text=text,
        width=width,
        height=36,
        fg_color=_GF_GOLD_SOFT,
        hover_color=_GF_GOLD,
        text_color=_GF_BG,
        font=theme.get_font(11, "bold"),
        command=command,
    )


def _f2_menu_kwargs() -> dict:
    return {
        "fg_color": _GF_FIELD,
        "button_color": _GF_FIELD,
        "button_hover_color": _GF_FIELD_HOVER,
        "dropdown_fg_color": _GF_PANEL,
        "dropdown_hover_color": _GF_CARD_SOFT,
        "font": theme.get_font(12),
    }


def _element_pill_colors(status: str, *, has_draft_patch: bool) -> tuple[str, str]:
    if has_draft_patch or status in ("draft_edited", "hidden_draft"):
        return theme.AccentGoldDim, theme.TextPrimary
    if status == "ok":
        return theme.StatusOk, theme.AppBg
    if status == "needs_review":
        return theme.StatusWarn, theme.AppBg
    if status == "missing_content":
        return theme.StatusErr, theme.TextPrimary
    if status == "legacy_disabled":
        return theme.StatusUnknown, theme.TextPrimary
    return theme.PanelBg, theme.TextMuted
