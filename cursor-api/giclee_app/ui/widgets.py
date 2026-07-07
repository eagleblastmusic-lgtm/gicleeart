"""Wspólne widgety Studio."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.component_loader import Component
from giclee_app.studio.background_capabilities import capability_for

from . import theme

_SHELL_STATUS_TEXT = "Gotowe · kliknij, aby otworzyć"
_CARD_STABLE_HEIGHT = 152
_HYDRATION_STAGES = 3


def status_color(ok: bool | None) -> str:
    if ok is True:
        return theme.StatusOk
    if ok is False:
        return theme.StatusErr
    return theme.StatusUnknown


class StatusPill(ctk.CTkFrame):
    """Kompaktowy wskaźnik statusu w topbarze."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        *,
        ok: bool | None = None,
        detail: str = "",
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.PanelBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        self._dot = ctk.CTkLabel(self, text="●", width=16, text_color=status_color(ok))
        self._dot.pack(side="left", padx=(8, 2), pady=6)
        self._title = ctk.CTkLabel(
            self, text=title, font=theme.get_font(12, "bold"),
            text_color=theme.TextPrimary,
        )
        self._title.pack(side="left", padx=(0, 8), pady=6)

    def update_status(self, ok: bool | None, title: str, detail: str = "") -> None:
        self._dot.configure(text_color=status_color(ok))
        self._title.configure(text=title)
        self.tooltip_text = detail


def _card_truncated_description(comp: Component) -> str:
    desc = (comp.description or "")[:120]
    if len(comp.description or "") > 120:
        desc += "…"
    return desc or comp.folder_name


def _card_build_accent(parent: ctk.CTkFrame, comp: Component) -> ctk.CTkFrame:
    accent = ctk.CTkFrame(
        master=parent,
        width=theme.CardAccentWidth,
        fg_color=comp.color,
        corner_radius=0,
    )
    accent.pack(side="left", fill="y")
    accent.pack_propagate(False)
    return accent


def _card_build_description(body: ctk.CTkFrame, comp: Component) -> None:
    ctk.CTkLabel(
        body,
        text=_card_truncated_description(comp),
        font=theme.get_font(11),
        text_color=theme.TextMuted,
        anchor="nw",
        justify="left",
        wraplength=260,
    ).pack(fill="x", pady=(6, 4))


def _card_build_badges(body: ctk.CTkFrame, comp: Component) -> ctk.CTkFrame:
    badges = ctk.CTkFrame(body, fg_color="transparent")
    badges.pack(fill="x", side="bottom")
    ctk.CTkLabel(
        badges,
        text=comp.mode,
        font=theme.get_font(10),
        text_color=theme.AccentGoldDim,
        fg_color=theme.AppBg,
        corner_radius=4,
        width=70,
        height=20,
    ).pack(side="left", padx=(0, 6))
    if capability_for(comp.folder_name) is not None:
        ctk.CTkLabel(
            badges,
            text="Tło",
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=36,
            height=20,
        ).pack(side="left", padx=(0, 6))
    if comp.hidden:
        ctk.CTkLabel(
            badges,
            text="ukryty",
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=50,
            height=20,
        ).pack(side="left")
    return badges


def _card_build_background_action(
    body: ctk.CTkFrame,
    comp: Component,
    on_open_background: Callable[[Component], None],
) -> ctk.CTkFrame:
    actions = ctk.CTkFrame(body, fg_color="transparent")
    actions.pack(fill="x", side="bottom", pady=(4, 0))
    ctk.CTkButton(
        actions,
        text="Tło",
        width=48,
        height=22,
        font=theme.get_font(10),
        fg_color=theme.AppBg,
        hover_color=theme.CardHover,
        text_color=theme.AccentGoldDim,
        border_width=1,
        border_color=theme.BorderSubtle,
        command=lambda c=comp: on_open_background(c),
    ).pack(side="right")
    return actions


def _card_bind_interactions(
    *,
    bind_targets: list[ctk.CTkBaseClass],
    on_enter: Callable[[object], None],
    on_leave: Callable[[object], None],
    on_click: Callable[[object], None],
    on_right_click: Callable[[Component, object], None] | None,
    comp: Component,
) -> None:
    for w in bind_targets:
        w.bind("<Enter>", on_enter)
        w.bind("<Leave>", on_leave)
        w.bind("<Button-1>", on_click)
        if on_right_click is not None:
            w.bind("<Button-3>", lambda e, c=comp, fn=on_right_click: fn(c, e))


class ComponentCardShell(ctk.CTkFrame):
    """Stable lightweight hub card.

    This is the default card shown in Studio Hub.
    Heavy hydration is optional and must not run automatically during initial hub load.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        *,
        on_click: Callable[[Component], None],
        on_right_click: Callable[[Component, object], None] | None = None,
        on_open_background: Callable[[Component], None] | None = None,
        on_request_hydration: Callable[[str], None] | None = None,
        pinned: bool = False,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.CardBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
            height=_CARD_STABLE_HEIGHT,
        )
        self.pack_propagate(False)
        self._comp = comp
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._on_open_background = on_open_background
        self._on_request_hydration = on_request_hydration
        self._normal_bg = theme.CardBg
        self._hover_bg = theme.CardHover
        self._pin_label: ctk.CTkLabel | None = None
        self._pinned = pinned
        self._hydration_stage = 0
        self._body: ctk.CTkFrame | None = None
        self._title_row: ctk.CTkFrame | None = None
        self._badges: ctk.CTkFrame | None = None
        self._actions: ctk.CTkFrame | None = None
        self._status_label: ctk.CTkLabel | None = None
        self._actions_slot: ctk.CTkFrame | None = None

        _card_build_accent(self, comp)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=10)
        self._body = body

        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x")
        self._title_row = title_row

        self._title_label = ctk.CTkLabel(
            title_row,
            text=comp.name,
            font=theme.get_font(14, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )
        self._title_label.pack(side="left", fill="x", expand=True)

        if self._pinned:
            self._apply_pin_label()

        self._description_label = ctk.CTkLabel(
            body,
            text=_card_truncated_description(comp),
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=260,
        )
        self._description_label.pack(fill="x", pady=(6, 4))

        self._status_label = ctk.CTkLabel(
            body,
            text=_SHELL_STATUS_TEXT,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._status_label.pack(anchor="w", pady=(4, 0))

        self._actions_slot = ctk.CTkFrame(body, fg_color="transparent", height=26)
        self._actions_slot.pack(fill="x", side="bottom", pady=(4, 0))
        self._actions_slot.pack_propagate(False)

        for target in (
            self,
            body,
            title_row,
            self._title_label,
            self._description_label,
            self._status_label,
        ):
            self._bind_shell_target(target)

    @property
    def component(self) -> Component:
        return self._comp

    @property
    def is_fully_hydrated(self) -> bool:
        return self._hydration_stage >= _HYDRATION_STAGES

    def hydration_stage(self) -> int:
        return self._hydration_stage

    def hydrate_stage_1(self) -> None:
        if self._hydration_stage >= 1 or self._title_row is None or self._body is None:
            return
        comp = self._comp
        if comp.icon:
            icon = ctk.CTkLabel(
                self._title_row,
                text=comp.icon,
                font=theme.get_font(18),
                width=28,
            )
            icon.pack(side="left", before=self._title_label)
        if self._pinned:
            self._apply_pin_label()
        self._badges = _card_build_badges(self._body, comp)
        self._hydration_stage = 1

    def hydrate_stage_2(self) -> None:
        if self._hydration_stage >= 2 or self._body is None:
            return
        comp = self._comp
        if (
            capability_for(comp.folder_name) is not None
            and self._on_open_background is not None
            and self._actions_slot is not None
        ):
            self._actions = _card_build_background_action(
                self._actions_slot,
                comp,
                self._on_open_background,
            )
        self._hydration_stage = 2

    def hydrate_stage_3(self) -> None:
        if self._hydration_stage >= 3:
            return

        if self._status_label is not None:
            self._status_label.configure(text="Gotowe")

        targets: list[ctk.CTkBaseClass] = []
        if self._badges is not None:
            targets.append(self._badges)
        if self._actions is not None:
            targets.append(self._actions)

        for target in targets:
            self._bind_shell_target(target)
            for child in target.winfo_children():
                if isinstance(child, ctk.CTkBaseClass):
                    self._bind_shell_target(child)

        self._hydration_stage = 3

    def _bind_shell_target(self, widget: ctk.CTkBaseClass) -> None:
        widget.bind("<Button-1>", self._handle_click)
        widget.bind("<Enter>", self._handle_enter)
        widget.bind("<Leave>", self._handle_leave)
        if self._on_right_click is not None:
            widget.bind("<Button-3>", self._handle_right)

    def _apply_pin_label(self) -> None:
        if self._title_row is None or self._pin_label is not None:
            return
        self._pin_label = ctk.CTkLabel(
            self._title_row,
            text="📌",
            font=theme.get_font(12),
            width=20,
        )
        self._pin_label.pack(side="right")

    @staticmethod
    def _on_enter(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, ComponentCardShell):
                w.configure(fg_color=w._hover_bg)
                break
            w = w.master  # type: ignore[attr-defined]

    @staticmethod
    def _on_leave(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, ComponentCardShell):
                w.configure(fg_color=w._normal_bg)
                break
            w = w.master  # type: ignore[attr-defined]

    def set_pinned(self, pinned: bool) -> None:
        self._pinned = pinned
        if pinned:
            self._apply_pin_label()
        elif self._pin_label is not None:
            self._pin_label.destroy()
            self._pin_label = None

    def _handle_enter(self, event: object) -> None:
        self._on_enter(event)
        if self._on_request_hydration is not None:
            self._on_request_hydration(self._comp.folder_name)

    def _handle_leave(self, event: object) -> None:
        self._on_leave(event)

    def _handle_click(self, _event: object) -> None:
        self._on_click(self._comp)

    def _handle_right(self, event: object) -> None:
        if self._on_right_click:
            self._on_right_click(self._comp, event)


class ComponentCard(ctk.CTkFrame):
    """Karta komponentu w hubie."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        *,
        on_click: Callable[[Component], None],
        on_right_click: Callable[[Component, object], None] | None = None,
        on_open_background: Callable[[Component], None] | None = None,
        pinned: bool = False,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.CardBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
            height=140,
        )
        self.pack_propagate(False)
        self._comp = comp
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._normal_bg = theme.CardBg
        self._hover_bg = theme.CardHover
        self._pin_label: ctk.CTkLabel | None = None

        _card_build_accent(self, comp)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=10)

        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x")
        self._title_row = title_row
        if comp.icon:
            ctk.CTkLabel(
                title_row, text=comp.icon, font=theme.get_font(18), width=28,
            ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text=comp.name,
            font=theme.get_font(14, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        if pinned:
            self._pin_label = ctk.CTkLabel(
                title_row,
                text="📌",
                font=theme.get_font(12),
                width=20,
            )
            self._pin_label.pack(side="right")

        _card_build_description(body, comp)
        badges = _card_build_badges(body, comp)

        cap = capability_for(comp.folder_name)
        actions: ctk.CTkFrame | None = None
        if cap is not None and on_open_background is not None:
            self.configure(height=152)
            actions = _card_build_background_action(body, comp, on_open_background)

        bind_targets = [self, body, title_row, badges]
        if actions is not None:
            bind_targets.append(actions)
        _card_bind_interactions(
            bind_targets=bind_targets,
            on_enter=self._on_enter,
            on_leave=self._on_leave,
            on_click=self._handle_click,
            on_right_click=on_right_click,
            comp=comp,
        )

    @staticmethod
    def _on_enter(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, ComponentCard):
                w.configure(fg_color=w._hover_bg)
                break
            w = w.master  # type: ignore[attr-defined]

    @staticmethod
    def _on_leave(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, ComponentCard):
                w.configure(fg_color=w._normal_bg)
                break
            w = w.master  # type: ignore[attr-defined]

    def set_pinned(self, pinned: bool) -> None:
        if pinned and self._pin_label is None:
            self._pin_label = ctk.CTkLabel(
                self._title_row,
                text="📌",
                font=theme.get_font(12),
                width=20,
            )
            self._pin_label.pack(side="right")
        elif not pinned and self._pin_label is not None:
            self._pin_label.destroy()
            self._pin_label = None

    def _handle_click(self, _event: object) -> None:
        self._on_click(self._comp)

    def _handle_right(self, event: object) -> None:
        if self._on_right_click:
            self._on_right_click(self._comp, event)


class AssetLabToolCard(ctk.CTkFrame):
    """Karta narzędzia Asset Lab — ten sam język wizualny co ComponentCard."""

    _CLICK_HINT = "kliknij, aby otworzyć"

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        *,
        summary: str,
        risk: str,
        on_launch: Callable[[Component], None],
        available: bool = True,
        legacy_badge: str = "legacy backend",
        unavailable_label: str = "niedostępny",
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.CardBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle if available else theme.TextMuted,
            height=140,
        )
        self.pack_propagate(False)
        self._comp = comp
        self._on_launch = on_launch
        self._available = available
        self._normal_bg = theme.CardBg
        self._hover_bg = theme.CardHover

        accent_color = comp.color if available else theme.TextMuted
        accent = ctk.CTkFrame(
            master=self,
            width=theme.CardAccentWidth,
            fg_color=accent_color,
            corner_radius=0,
        )
        accent.pack(side="left", fill="y")
        accent.pack_propagate(False)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=10)

        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x")
        if comp.icon:
            ctk.CTkLabel(
                title_row, text=comp.icon, font=theme.get_font(18), width=28,
            ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text=comp.name,
            font=theme.get_font(14, "bold"),
            text_color=theme.TextPrimary if available else theme.TextMuted,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        desc = (summary or "")[:120]
        if len(summary or "") > 120:
            desc += "…"
        ctk.CTkLabel(
            body,
            text=desc or comp.folder_name,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=260,
        ).pack(fill="x", pady=(6, 4))

        badges = ctk.CTkFrame(body, fg_color="transparent")
        badges.pack(fill="x", side="bottom")
        ctk.CTkLabel(
            badges,
            text=comp.mode,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=70,
            height=20,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            badges,
            text=f"ryz. {risk}",
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=44,
            height=20,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            badges,
            text=legacy_badge,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=88,
            height=20,
        ).pack(side="left")
        if available:
            ctk.CTkLabel(
                badges,
                text=self._CLICK_HINT,
                font=theme.get_font(10),
                text_color=theme.TextMuted,
                anchor="e",
            ).pack(side="right")
        else:
            ctk.CTkLabel(
                badges,
                text=unavailable_label,
                font=theme.get_font(10),
                text_color=theme.TextMuted,
                anchor="e",
            ).pack(side="right")

        bind_targets = [self, body, title_row, badges]
        for w in bind_targets:
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            if available:
                w.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event: object) -> None:
        if self._available:
            self._on_launch(self._comp)

    @staticmethod
    def _on_enter(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, AssetLabToolCard):
                w.configure(fg_color=w._hover_bg)
                if w._available:
                    w.configure(cursor="hand2")
                break
            w = w.master  # type: ignore[attr-defined]

    @staticmethod
    def _on_leave(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, AssetLabToolCard):
                w.configure(fg_color=w._normal_bg, cursor="")
                break
            w = w.master  # type: ignore[attr-defined]


class StatCard(ctk.CTkFrame):
    """Kafelek statystyki na dashboardzie."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        value: str,
        *,
        muted: bool = False,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        ctk.CTkLabel(
            self,
            text=title,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 0))
        self._value_label = ctk.CTkLabel(
            self,
            text=value,
            font=theme.get_font(22 if not muted else 18, "bold", brand=not muted),
            text_color=theme.TextMuted if muted else theme.TextPrimary,
            anchor="w",
        )
        self._value_label.pack(fill="x", padx=14, pady=(4, 12))

    def update_value(self, value: str) -> None:
        self._value_label.configure(text=value)


class SectionHeader(ctk.CTkLabel):
    def __init__(self, master: ctk.CTkBaseClass, text: str) -> None:
        super().__init__(
            master,
            text=text,
            font=theme.get_font(16, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )


class CompactComponentChip(ctk.CTkButton):
    """Kompaktowy chip komponentu na dashboardzie."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        *,
        on_click: Callable[[Component], None],
    ) -> None:
        label = comp.name if len(comp.name) <= 22 else comp.name[:20] + "…"
        super().__init__(
            master,
            text=label,
            font=theme.get_font(11),
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            text_color=theme.TextPrimary,
            border_width=1,
            border_color=theme.BorderSubtle,
            height=28,
            width=max(80, len(label) * 8),
            command=lambda c=comp: on_click(c),
        )
        self._comp = comp


ComponentChip = CompactComponentChip
