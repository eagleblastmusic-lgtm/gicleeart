"""GICLÉE FRAME™ — editor shell, prewarm and minimal population."""

from __future__ import annotations

import time
import tkinter as tk

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    APPLY_RAM_DRAFT_LABEL,
    APPLY_RAM_MICROCOPY,
    EditorFieldVisibility,
    MergedPageElement,
    editor_context_rows,
    editor_field_visibility,
    editor_title_for_element,
)
from giclee_app.studio.perf import log_event, span
from . import theme
from .gicleeframe_view_models import SectionVisualCacheEntry
from .gicleeframe_view_primitives import (
    _BTN_HEIGHT,
    _CARD_PAD_X,
    _CARD_PAD_Y,
    _GF_BORDER,
    _GF_FIELD,
    _GF_FIELD_HOVER,
    _GF_GOLD_SOFT,
    _GF_MUTED,
    _GF_PREVIEW_MAT,
    _GF_PREVIEW_PAPER,
    _element_pill_colors,
    _f2_entry_kwargs,
    _make_card,
    _make_card_title,
    _make_gf_card,
    _make_pill,
    _make_primary_button,
)
from .gicleeframe_view_section_list_shell import _SECTION_PLACEHOLDER

_LEGACY_READONLY_MSG = (
    "Sekcja legacy — nie jest edytowana w Studio. "
    "Tylko notatka robocza opcjonalna."
)
_EDITOR_FORM_WIDTH = 760
_EDITOR_HERO_PREVIEW_HEIGHT = 118
_PREVIEW_SETTINGS_CAPTION = "Podgląd ustawień"
_LAYER_NAV_TITLE = "Warstwy sekcji"
_IMAGE_SOURCE_TITLE = "Źródło grafiki"
_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS = 80
_GF_EDITOR_IDENTITY_LATE_DEFER_MS = 160
_GF_PREVIEW_BOOTSTRAP_STATUS_TEXT = "Podgląd sekcji pojawi się po wyborze…"
_EDITOR_PLACEHOLDER_TEXT = (
    "Wybierz sekcję po lewej stronie, aby załadować podgląd i ustawienia."
)

__all__ = (
    "GicleeFrameEditorShellMixin",
    "_LEGACY_READONLY_MSG",
    "_EDITOR_FORM_WIDTH",
    "_EDITOR_HERO_PREVIEW_HEIGHT",
    "_PREVIEW_SETTINGS_CAPTION",
    "_LAYER_NAV_TITLE",
    "_IMAGE_SOURCE_TITLE",
    "_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS",
    "_GF_EDITOR_IDENTITY_LATE_DEFER_MS",
    "_GF_PREVIEW_BOOTSTRAP_STATUS_TEXT",
    "_EDITOR_PLACEHOLDER_TEXT",
)


class GicleeFrameEditorShellMixin:
    """Editor shell, prewarm lifecycle and minimal population."""

    def _build_editor_column_deferred(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._shell_editor_built or self._workspace_frame is None:
            return
        log_event(
            "studio.gicleeframe.editor.skeleton_enter",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_editor_deferred_scheduled_mono,
            ),
        )
        self._micro_deferred_editor_skeleton()

    def _micro_deferred_editor_skeleton(self) -> None:
        if self._workspace_frame is None:
            return
        with span("studio.gicleeframe.build.editor_column.skeleton"):
            with span("studio.gicleeframe.build.editor_column.skeleton.ensure_column"):
                if self._editor_column is None:
                    self._editor_column = _make_card(
                        self._workspace_frame, bordered=False, fg_color="transparent",
                    )
                    self._editor_column.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
                else:
                    self._clear_column_children(self._editor_column)
            with span("studio.gicleeframe.build.editor_column.skeleton.identity_card"):
                self._build_section_identity_placeholder(self._editor_column)
            with span("studio.gicleeframe.build.editor_column.skeleton.legacy_message"):
                self._legacy_msg_label = ctk.CTkLabel(
                    self._editor_column,
                    text="",
                    font=theme.get_font(10),
                    text_color=theme.AccentGoldDim,
                    anchor="w",
                    wraplength=_EDITOR_FORM_WIDTH - 24,
                )
        self._shell_editor_built = True
        log_event("studio.gicleeframe.editor.skeleton_ready")
        log_event(
            "studio.gicleeframe.editor.skeleton_done",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_editor_deferred_scheduled_mono,
            ),
        )
        log_event("studio.gicleeframe.editor.deferred_identity")
        log_event("studio.gicleeframe.editor.identity_card_lazy_startup")
        log_event("studio.gicleeframe.shell.deferred_editor")
        self._log_visual_gate_ready(
            "editor",
            source="editor_skeleton",
            since_scheduled_mono=self._shell_editor_deferred_scheduled_mono,
        )
        self._try_mark_perceived_ready(trigger="editor_skeleton_done")
        self._schedule_editor_identity_late_build()
        if self._selected_id is None:
            with span("studio.gicleeframe.build.editor_column.skeleton.placeholder_state"):
                self._show_editor_placeholder_state()
        self.after(self._editor_micro_defer_ms(), self._micro_deferred_editor_form_shell)

    def _build_section_identity_placeholder(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 0))
        self._identity_card = frame

        ctk.CTkLabel(
            frame,
            text="Edytor sekcji",
            font=theme.get_font(12, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(4, 0))

        self._editor_section_subtitle = ctk.CTkLabel(
            frame,
            text="Wybierz sekcję po lewej",
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._editor_section_subtitle.pack(fill="x", padx=4, pady=(2, 8))

        self._editor_status_dot = None
        self._editor_header_visible_row = None
        self._layer_nav_frame = None
        self._section_preview_line = None
        self._section_preview_card = None
        self._section_preview_canvas = None
        self._section_preview_badge = None

    def _schedule_editor_identity_late_build(self) -> None:
        if self._editor_identity_late_build_started:
            return
        self._editor_identity_late_build_started = True
        log_event(
            "studio.gicleeframe.editor.identity_card_late_scheduled",
            delay_ms=_GF_EDITOR_IDENTITY_LATE_DEFER_MS,
        )
        self.after(_GF_EDITOR_IDENTITY_LATE_DEFER_MS, self._build_editor_identity_late)

    def _schedule_editor_identity_prewarm_after_perceived(self) -> None:
        if self._editor_identity_prewarm_scheduled:
            return
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_deferred_after_perceived",
            delay_ms=_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS,
            since_enter_ms=self._since_visual_enter_ms(),
        )
        self.after(
            _GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS,
            lambda: self._schedule_editor_identity_prewarm(reason="after_perceived_ready"),
        )

    def _schedule_editor_identity_prewarm(self, *, reason: str = "editor_skeleton_done") -> None:
        if self._editor_identity_prewarm_scheduled:
            return
        self._editor_identity_prewarm_scheduled = True
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_scheduled",
            since_enter_ms=self._since_visual_enter_ms(),
            reason=reason,
        )
        self.after(self._editor_micro_defer_ms(), self._run_editor_identity_prewarm)

    def _run_editor_identity_prewarm(self) -> None:
        if self._defer_background_for_selection(
            job="editor.identity_prewarm",
            reason="selection_priority_active",
            callback=self._run_editor_identity_prewarm,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        prewarm_started = time.perf_counter()
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_enter",
            since_enter_ms=self._since_visual_enter_ms(),
        )
        if self._editor_identity_late_build_done:
            log_event(
                "studio.gicleeframe.editor.identity_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                already_built=True,
                reason="already_built",
            )
            self._schedule_editor_rows_prewarm()
            return
        if not self._shell_editor_built:
            log_event(
                "studio.gicleeframe.editor.identity_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                already_built=False,
                reason="shell_not_ready",
            )
            return
        self._ensure_editor_identity_built()
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_done",
            since_enter_ms=self._since_visual_enter_ms(),
            elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
            already_built=False,
            reason="built",
        )
        self._schedule_editor_rows_prewarm()

    def _schedule_editor_rows_prewarm(self) -> None:
        if self._editor_rows_prewarm_scheduled:
            return
        self._editor_rows_prewarm_scheduled = True
        log_event(
            "studio.gicleeframe.editor.rows_prewarm_scheduled",
            since_enter_ms=self._since_visual_enter_ms(),
            reason="identity_prewarm_done",
        )
        self.after(self._editor_micro_defer_ms(), self._run_editor_rows_prewarm)

    def _editor_row_shell_flags(self) -> dict[str, bool]:
        return {
            "title": self._title_row_built,
            "text": self._text_row_built,
            "alt": self._alt_row_built,
            "image_ref": self._image_ref_row_built,
            "notes": self._notes_row_built,
        }

    def _editor_row_shells_already_built(self) -> bool:
        flags = self._editor_row_shell_flags()
        return all(flags.values())

    def _ensure_editor_row_shells_for_prewarm(self) -> None:
        if self._edit_panel is None:
            return
        self._ensure_title_row_built()
        self._ensure_text_row_built()
        self._ensure_alt_row_built()
        self._ensure_image_ref_row_built()
        self._ensure_notes_row_built()

    def _run_editor_rows_prewarm(self) -> None:
        if self._should_suppress_visible_prewarm():
            self._log_visible_prewarm_suppressed(job="editor.rows_prewarm")
            return
        if self._defer_background_for_selection(
            job="editor.rows_prewarm",
            reason="selection_priority_active",
            callback=self._run_editor_rows_prewarm,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        prewarm_started = time.perf_counter()
        log_event(
            "studio.gicleeframe.editor.rows_prewarm_enter",
            since_enter_ms=self._since_visual_enter_ms(),
        )
        if self._editor_row_shells_already_built():
            log_event(
                "studio.gicleeframe.editor.rows_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
                already_built=True,
                reason="already_built",
            )
            return
        if not self._shell_editor_built:
            log_event(
                "studio.gicleeframe.editor.rows_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
                already_built=False,
                reason="shell_not_ready",
            )
            return
        if not self._editor_form_shell_ready or self._edit_panel is None:
            log_event(
                "studio.gicleeframe.editor.rows_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
                already_built=False,
                reason="form_shell_not_ready",
            )
            return
        flags_before = self._editor_row_shell_flags()
        self._ensure_editor_row_shells_for_prewarm()
        flags_after = self._editor_row_shell_flags()
        log_event(
            "studio.gicleeframe.editor.rows_prewarm_done",
            since_enter_ms=self._since_visual_enter_ms(),
            elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
            already_built=False,
            reason="built",
            title_row_built=flags_after["title"] and not flags_before["title"],
            text_row_built=flags_after["text"] and not flags_before["text"],
            alt_row_built=flags_after["alt"] and not flags_before["alt"],
            image_ref_row_built=flags_after["image_ref"] and not flags_before["image_ref"],
            notes_row_built=flags_after["notes"] and not flags_before["notes"],
            children_overview_built=False,
        )

    def _ensure_editor_identity_built(self) -> None:
        if self._editor_identity_late_build_done:
            return
        self._build_editor_identity_late()

    def _build_editor_identity_late(self) -> None:
        if self._defer_background_for_selection(
            job="editor.identity_late",
            reason="selection_priority_active",
            callback=self._build_editor_identity_late,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._editor_identity_late_build_done or self._editor_column is None:
            return

        log_event("studio.gicleeframe.editor.identity_card_late_start")

        pack_before = None
        if self._edit_panel is not None:
            pack_before = self._edit_panel.master

        if self._identity_card is not None:
            self._identity_card.destroy()
            self._identity_card = None

        with span("studio.gicleeframe.build.editor_column.identity_card_late"):
            self._build_section_identity_card(self._editor_column, pack_before=pack_before)

        self._editor_identity_late_build_done = True
        log_event("studio.gicleeframe.editor.identity_card_late_done")

        if self._selected_id is None:
            self._show_editor_placeholder_state()
            return

        m = self._merged_by_id.get(self._selected_id)
        if m is None:
            return

        dot_color, _ = _element_pill_colors(m.status, has_draft_patch=m.has_draft_patch)
        if self._editor_status_dot:
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=self._selected_section_label())

    def _micro_deferred_editor_form_shell(self) -> None:
        if self._editor_column is None:
            return
        with span("studio.gicleeframe.build.editor_column.form_shell"):
            form_outer = ctk.CTkFrame(self._editor_column, fg_color="transparent")
            form_outer.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 4))
            form_outer.configure(width=_EDITOR_FORM_WIDTH)
            form_outer.pack_propagate(True)
            self._edit_panel = ctk.CTkFrame(form_outer, fg_color="transparent")
            self._edit_panel.pack(fill="x", anchor="w")
            self._editor_placeholder_label = ctk.CTkLabel(
                self._edit_panel,
                text=_EDITOR_PLACEHOLDER_TEXT,
                font=theme.get_font(10),
                text_color=theme.TextMuted,
                anchor="w",
                wraplength=_EDITOR_FORM_WIDTH - 24,
            )
            self._editor_placeholder_label.pack(fill="x", pady=(4, 8))
        self._editor_form_shell_ready = True
        log_event("studio.gicleeframe.editor.deferred_form_shell")
        log_event("studio.gicleeframe.editor.fields_lazy_startup")
        self._schedule_atomic_reveal_check(trigger="editor_form_shell")

    def _micro_deferred_editor_fields(self) -> None:
        with span("studio.gicleeframe.build.editor_column.fields"):
            self._build_edit_panel_fields()
        log_event("studio.gicleeframe.editor.deferred_fields")
        self.after(self._editor_micro_defer_ms(), self._micro_deferred_editor_children)

    def _micro_deferred_editor_children(self) -> None:
        with span("studio.gicleeframe.build.editor_column.children"):
            self._build_edit_panel_children()
        log_event("studio.gicleeframe.editor.deferred_children")
        self.after(self._editor_micro_defer_ms(), self._micro_deferred_editor_page_context)

    def _micro_deferred_editor_page_context(self) -> None:
        with span("studio.gicleeframe.build.editor_column.page_context"):
            self._build_edit_panel_page_context()

    def _build_section_identity_card(
        self,
        parent: ctk.CTkFrame,
        *,
        pack_before: ctk.CTkBaseClass | None = None,
    ) -> None:
        card = _make_gf_card(parent, variant="panel_deep", radius=16)
        if pack_before is not None:
            card.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 0), before=pack_before)
        else:
            card.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 0))
        self._identity_card = card

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 4))

        self._editor_status_dot = ctk.CTkLabel(
            top,
            text="●",
            width=18,
            text_color=theme.StatusOk,
            font=theme.get_font(13),
        )
        self._editor_status_dot.pack(side="left")

        title_block = ctk.CTkFrame(top, fg_color="transparent")
        title_block.pack(side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(
            title_block,
            text="Workbench sekcji",
            font=theme.get_font(14, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x")
        self._editor_section_subtitle = ctk.CTkLabel(
            title_block,
            text=_SECTION_PLACEHOLDER,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._editor_section_subtitle.pack(fill="x", pady=(2, 0))

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.pack(side="right", padx=(12, 0))

        self._editor_header_visible_row = ctk.CTkFrame(actions, fg_color="transparent")
        self._editor_header_visible_row.pack(side="top", anchor="e", pady=(0, 6))
        self._visible_row = self._editor_header_visible_row

        if self._visible_var is None:
            self._visible_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            self._editor_header_visible_row,
            text="Widoczna",
            variable=self._visible_var,
            font=theme.get_font(11),
        ).pack(side="right")

        _make_primary_button(
            actions,
            APPLY_RAM_DRAFT_LABEL,
            self._apply_edit_to_draft,
            width=160,
        ).pack(side="top", anchor="e", fill="x")

        ctk.CTkLabel(
            actions,
            text=APPLY_RAM_MICROCOPY,
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="e",
        ).pack(side="top", anchor="e", pady=(3, 0))

        self._layer_nav_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._layer_nav_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(8, 0))
        self._layer_nav_frame.pack_forget()

        preview = _make_gf_card(card, variant="preview", radius=14)
        self._section_preview_card = preview
        preview.pack(fill="x", padx=_CARD_PAD_X, pady=(10, 14))
        preview.pack_propagate(False)
        preview.configure(height=_EDITOR_HERO_PREVIEW_HEIGHT)

        preview_head = ctk.CTkFrame(preview, fg_color="transparent")
        preview_head.pack(fill="x", padx=14, pady=(10, 0))

        ctk.CTkLabel(
            preview_head,
            text=_PREVIEW_SETTINGS_CAPTION.upper(),
            font=theme.get_font(9, "bold"),
            text_color=_GF_GOLD_SOFT,
            anchor="w",
        ).pack(side="left")

        self._section_preview_badge = _make_pill(
            preview_head,
            "RAM preview",
            fg_color=_GF_FIELD,
            text_color=_GF_MUTED,
        )
        self._section_preview_badge.pack(side="right")

        stage = ctk.CTkFrame(preview, fg_color="transparent")
        stage.pack(fill="both", expand=True, padx=18, pady=(8, 14))

        paper = ctk.CTkFrame(stage, fg_color=_GF_PREVIEW_PAPER, corner_radius=10)
        paper.pack(fill="both", expand=True)
        paper.pack_propagate(False)

        mat = ctk.CTkFrame(paper, fg_color=_GF_PREVIEW_MAT, corner_radius=8)
        mat.pack(fill="both", expand=True, padx=18, pady=12)
        mat.pack_propagate(False)
        self._section_preview_canvas = mat

        bootstrap = ctk.CTkFrame(
            mat,
            fg_color=_GF_FIELD,
            corner_radius=8,
            border_width=1,
            border_color=_GF_BORDER,
        )
        bootstrap.pack(fill="both", expand=True, padx=12, pady=10)
        self._preview_bootstrap_panel = bootstrap
        self._preview_bootstrap_status_label = ctk.CTkLabel(
            bootstrap,
            text=_GF_PREVIEW_BOOTSTRAP_STATUS_TEXT,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="center",
            justify="center",
            wraplength=320,
        )
        self._preview_bootstrap_status_label.pack(expand=True, fill="both", padx=16, pady=16)
        self._section_preview_line = None

    def _build_action_dock(self, parent: ctk.CTkFrame) -> None:
        action_dock = ctk.CTkFrame(
            parent,
            fg_color=theme.PanelBg,
            corner_radius=10,
        )
        action_dock.pack(fill="x", padx=_CARD_PAD_X, pady=(10, 14))

        _make_primary_button(
            action_dock,
            APPLY_RAM_DRAFT_LABEL,
            self._apply_edit_to_draft,
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkLabel(
            action_dock,
            text=APPLY_RAM_MICROCOPY,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(side="left", padx=(0, 12))

    def _build_editor_column(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        card = _make_card(parent, bordered=False, fg_color="transparent")

        self._build_section_identity_card(card)

        self._legacy_msg_label = ctk.CTkLabel(
            card,
            text="",
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
            wraplength=_EDITOR_FORM_WIDTH - 24,
        )

        form_outer = ctk.CTkFrame(card, fg_color="transparent")
        form_outer.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 4))
        form_outer.configure(width=_EDITOR_FORM_WIDTH)
        form_outer.pack_propagate(True)

        self._edit_panel = ctk.CTkFrame(form_outer, fg_color="transparent")
        self._edit_panel.pack(fill="x", anchor="w")
        self._build_edit_panel()

        # F2.2.3: główna akcja RAM jest w identity card, żeby była widoczna od razu.
        # self._build_action_dock(card)

        return card

    def _build_setting_group_card(
        self,
        parent: ctk.CTkBaseClass,
        title: str,
    ) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        card = _make_gf_card(parent, variant="soft", radius=14)
        _make_card_title(card, title).pack(fill="x", padx=12, pady=(12, 8))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=2, pady=(0, 6))
        return card, body

    def _build_edit_panel(self) -> None:
        if self._edit_panel is None:
            return
        self._build_edit_panel_page_context()
        self._build_edit_panel_fields()
        self._build_edit_panel_children()

    def _build_edit_panel_page_context(self) -> None:
        self._ensure_page_context_shell_built()

    def _ensure_page_context_shell_built(self) -> None:
        if self._page_context_shell_built or self._edit_panel is None:
            return
        self._page_context_frame = ctk.CTkFrame(
            self._edit_panel, fg_color="transparent",
        )
        self._page_context_inner = ctk.CTkFrame(
            self._page_context_frame, fg_color="transparent",
        )
        self._page_context_inner.pack(fill="x")
        self._page_context_shell_built = True

    def _build_edit_panel_fields(self) -> None:
        if self._edit_panel is None:
            return
        self._ensure_title_row_built()
        self._ensure_text_row_built()
        self._ensure_alt_row_built()
        self._ensure_image_ref_row_built()
        self._ensure_notes_row_built()
        self._visible_row = self._editor_header_visible_row

    def _ensure_title_row_built(self) -> None:
        if self._title_row_built or self._edit_panel is None:
            return
        self._title_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        title_card, title_body = self._build_setting_group_card(self._title_row, "Tytuł")
        title_card.pack(fill="x", pady=(0, 8))
        self._title_entry = ctk.CTkEntry(title_body, **_f2_entry_kwargs())
        self._title_entry.pack(fill="x")
        self._title_row_built = True

    def _ensure_text_row_built(self) -> None:
        if self._text_row_built or self._edit_panel is None:
            return
        self._text_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        text_card, text_body = self._build_setting_group_card(self._text_row, "Tekst")
        text_card.pack(fill="x", pady=(0, 8))
        self._text_box = ctk.CTkTextbox(text_body, height=72, font=theme.get_font(11))
        self._text_box.pack(fill="x")
        self._text_row_built = True

    def _ensure_alt_row_built(self) -> None:
        if self._alt_row_built or self._edit_panel is None:
            return
        self._alt_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        alt_card, alt_body = self._build_setting_group_card(self._alt_row, "Alt")
        alt_card.pack(fill="x", pady=(0, 8))
        self._alt_entry = ctk.CTkEntry(alt_body, **_f2_entry_kwargs())
        self._alt_entry.pack(fill="x")
        self._alt_row_built = True

    def _ensure_image_ref_row_built(self) -> None:
        if self._image_ref_row_built or self._edit_panel is None:
            return
        self._image_ref_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        ref_card, ref_body = self._build_setting_group_card(
            self._image_ref_row, _IMAGE_SOURCE_TITLE,
        )
        ref_card.pack(fill="x", pady=(0, 8))
        self._image_ref_entry = ctk.CTkEntry(ref_body, state="disabled", **_f2_entry_kwargs())
        self._image_ref_entry.pack(fill="x")
        self._image_ref_row_built = True

    def _ensure_notes_row_built(self) -> None:
        if self._notes_row_built or self._edit_panel is None:
            return
        self._notes_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        self._notes_group_frame, notes_body = self._build_setting_group_card(
            self._notes_row, "Notatka",
        )
        self._notes_box = ctk.CTkTextbox(
            notes_body,
            height=42,
            font=theme.get_font(10),
            fg_color=_GF_FIELD,
            border_width=1,
            border_color=_GF_BORDER,
        )
        self._notes_box.pack(fill="x")
        self._notes_row_built = True

    def _build_edit_panel_children(self) -> None:
        self._ensure_children_overview_built()

    def _ensure_children_overview_built(self) -> None:
        if self._children_overview_built or self._edit_panel is None:
            return
        self._children_overview_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        child_card, child_body = self._build_setting_group_card(
            self._children_overview_row, _LAYER_NAV_TITLE,
        )
        child_card.pack(fill="x", pady=(0, 4))
        self._children_overview_buttons = ctk.CTkFrame(child_body, fg_color="transparent")
        self._children_overview_buttons.pack(fill="x")
        self._children_overview_built = True

    def _hide_editor_field_placeholder_if_needed(self) -> None:
        if self._editor_placeholder_label is None:
            return
        try:
            if self._editor_placeholder_label.winfo_manager():
                self._editor_placeholder_label.pack_forget()
        except tk.TclError:
            pass

    def _ensure_editor_rows_for_fields(self, fields: EditorFieldVisibility) -> None:
        if fields.title:
            self._ensure_title_row_built()
        if fields.text:
            self._ensure_text_row_built()
        if fields.alt:
            self._ensure_alt_row_built()
        if fields.image_ref:
            self._ensure_image_ref_row_built()
        if fields.notes:
            self._ensure_notes_row_built()
        if fields.children:
            self._ensure_children_overview_built()
        if fields.page_context:
            self._ensure_page_context_shell_built()
        if fields.visible and self._visible_row is None:
            self._visible_row = self._editor_header_visible_row
        self._hide_editor_field_placeholder_if_needed()

    def _ensure_minimal_editor_rows_for_fields(self, fields: EditorFieldVisibility) -> None:
        if fields.title:
            self._ensure_title_row_built()
        if fields.text:
            self._ensure_text_row_built()
        if fields.alt:
            self._ensure_alt_row_built()
        if fields.image_ref:
            self._ensure_image_ref_row_built()
        if fields.notes:
            self._ensure_notes_row_built()
        if fields.page_context:
            self._ensure_page_context_shell_built()
        if fields.visible and self._visible_row is None:
            self._visible_row = self._editor_header_visible_row
        self._hide_editor_field_placeholder_if_needed()

    def _show_editor_placeholder_state(self) -> None:
        if self._editor_status_dot is not None:
            self._editor_status_dot.configure(text="●", text_color=theme.TextMuted)
        if self._editor_section_subtitle is not None:
            self._editor_section_subtitle.configure(text=_EDITOR_PLACEHOLDER_TEXT)
        log_event("studio.gicleeframe.editor.placeholder_state")

    def _log_editor_skeleton_suppressed(
        self,
        *,
        element_id: str,
        element_type: str,
        reason: str,
    ) -> None:
        log_event(
            "studio.gicleeframe.editor.skeleton_suppressed",
            element_id=element_id,
            element_type=element_type,
            reason=reason,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _show_editor_refresh_status(self, text: str) -> None:
        if self._identity_card is None:
            return
        if self._editor_refresh_status_frame is None:
            frame = ctk.CTkFrame(self._identity_card, fg_color="transparent")
            self._editor_refresh_status_label = ctk.CTkLabel(
                frame,
                text=text,
                font=theme.get_font(9),
                text_color=theme.TextMuted,
                anchor="w",
            )
            self._editor_refresh_status_label.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 4))
            self._editor_refresh_status_frame = frame
        elif self._editor_refresh_status_label is not None:
            self._editor_refresh_status_label.configure(text=text)
        if self._editor_refresh_status_frame is None:
            return
        try:
            self._editor_refresh_status_frame.pack(
                fill="x",
                padx=0,
                pady=(0, 2),
                before=self._layer_nav_frame
                if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager()
                else None,
            )
        except tk.TclError:
            try:
                self._editor_refresh_status_frame.pack(fill="x", padx=0, pady=(0, 2))
            except tk.TclError:
                pass

    def _hide_editor_refresh_status(self) -> None:
        if self._editor_refresh_status_frame is None:
            return
        try:
            self._editor_refresh_status_frame.pack_forget()
        except tk.TclError:
            pass

    def _mark_editor_content_ready(self, m: MergedPageElement) -> None:
        self._editor_has_ready_content = True
        self._editor_last_ready_element_id = m.element_id

    def _log_editor_content_swapped(
        self,
        m: MergedPageElement,
        *,
        region: str,
        preview_key: str = "",
    ) -> None:
        log_event(
            "studio.gicleeframe.editor.content_swapped",
            element_id=m.element_id,
            element_type=m.element_type,
            region=region,
            preview_key=preview_key,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _minimal_cache_entry(
        self,
        m: MergedPageElement,
    ) -> SectionVisualCacheEntry | None:
        return self._section_visual_cache.get(m.element_id)

    def _fields_from_cache_entry(self, entry: SectionVisualCacheEntry) -> EditorFieldVisibility:
        return EditorFieldVisibility(
            title=entry.fields_title,
            text=entry.fields_text,
            alt=entry.fields_alt,
            image_ref=entry.fields_image_ref,
            notes=entry.fields_notes,
            visible=entry.fields_visible,
            children=entry.fields_children,
            page_context=entry.fields_page_context,
        )

    def _apply_section_visual_cache(self, m: MergedPageElement) -> bool:
        """Legacy alias — minimal cache only."""
        return self._apply_minimal_cache(m)

    def _apply_minimal_cache(self, m: MergedPageElement) -> bool:
        entry = self._section_visual_cache.get(m.element_id)
        if entry is None:
            return False

        self._ensure_editor_identity_built()
        fields = self._fields_from_cache_entry(entry)
        self._ensure_minimal_editor_rows_for_fields(fields)

        dot_color, _ = _element_pill_colors(
            entry.status,
            has_draft_patch=entry.has_draft_patch,
        )
        if self._editor_status_dot:
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=entry.subtitle_text)

        readonly = entry.element_type == "section_legacy"
        self._set_row_visible(self._title_row, fields.title)
        self._set_row_visible(self._text_row, fields.text)
        self._set_row_visible(self._alt_row, fields.alt)
        self._set_row_visible(self._image_ref_row, fields.image_ref)
        self._set_row_visible(self._notes_row, fields.notes)
        self._set_row_visible(self._visible_row, fields.visible)
        self._set_row_visible(self._children_overview_row, False)

        if self._title_entry:
            self._set_entry(self._title_entry, entry.title, readonly=readonly or not fields.title)
        if self._text_box:
            self._set_textbox(self._text_box, entry.text, readonly=readonly or not fields.text)
        if self._alt_entry:
            self._set_entry(self._alt_entry, entry.alt, readonly=readonly or not fields.alt)
        if self._image_ref_entry:
            self._set_entry(self._image_ref_entry, entry.image_ref, readonly=True)
        if self._notes_box:
            self._set_textbox(self._notes_box, entry.notes, readonly=readonly or not fields.notes)
        if self._visible_var is not None and fields.visible:
            self._visible_var.set(entry.visible)

        self._apply_cached_page_context_summary(entry)
        self._hide_heavy_editor_modules()
        self._hide_media_details_stable_shell()
        self._show_details_on_demand_block(m)

        self._page_context_shell_shown_generation = self._selection_generation
        self._mark_editor_stable_shell_ready(m, from_cache=True)
        self._mark_editor_content_ready(m)
        self._hide_editor_refresh_status()
        self._log_minimal_editor_ready(m, from_cache=True)
        return True

    def _log_minimal_editor_ready(
        self,
        m: MergedPageElement,
        *,
        from_cache: bool,
    ) -> None:
        log_event(
            "studio.gicleeframe.selection.minimal_editor_ready",
            element_id=m.element_id,
            element_type=m.element_type,
            since_click_ms=self._since_selection_click_ms(),
            from_cache=from_cache,
        )

    def _hide_heavy_editor_modules(self) -> None:
        self._hide_preview_frames()
        if self._section_preview_card is not None:
            try:
                self._section_preview_card.pack_forget()
            except tk.TclError:
                pass
        if self._layer_nav_frame is not None:
            try:
                self._layer_nav_frame.pack_forget()
            except tk.TclError:
                pass
        self._set_row_visible(self._children_overview_row, False)

    def _show_heavy_editor_modules(self) -> None:
        if self._section_preview_card is not None:
            try:
                if not self._section_preview_card.winfo_manager():
                    self._section_preview_card.pack(fill="x", padx=_CARD_PAD_X, pady=(10, 14))
            except tk.TclError:
                pass

    def _mark_editor_stable_shell_ready(
        self,
        m: MergedPageElement,
        *,
        from_cache: bool = False,
    ) -> None:
        if m.element_id in self._editor_stable_shell_logged_for and not from_cache:
            return
        if not from_cache:
            self._editor_stable_shell_logged_for.add(m.element_id)
        log_event(
            "studio.gicleeframe.editor.stable_shell_ready",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            from_cache=from_cache,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _maybe_log_layout_shift_guard(
        self,
        m: MergedPageElement,
        *,
        phase: str,
        rows_visible: int,
    ) -> None:
        log_event(
            "studio.gicleeframe.editor.layout_shift_guard",
            element_id=m.element_id,
            element_type=m.element_type,
            phase=phase,
            rows_visible=rows_visible,
            generation=self._selection_generation,
        )

    def _show_editor_selection_stable_shell_state(
        self,
        m: MergedPageElement,
        *,
        from_cache: bool = False,
    ) -> None:
        if self._editor_status_dot:
            if from_cache:
                dot_color, _ = _element_pill_colors(m.status, has_draft_patch=m.has_draft_patch)
            else:
                dot_color = _GF_GOLD_SOFT
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=editor_title_for_element(m))

        log_event(
            "studio.gicleeframe.editor.selection_stable_shell",
            element_id=m.element_id,
            element_type=m.element_type,
            from_cache=from_cache,
        )

    def _show_editor_selection_pending_state(self, m: MergedPageElement) -> None:
        self._show_editor_selection_stable_shell_state(m, from_cache=False)

        log_event(
            "studio.gicleeframe.editor.selection_pending",
            element_id=m.element_id,
            element_type=m.element_type,
        )

    def _mark_editor_shell_ready_after_click(
        self,
        m: MergedPageElement,
        *,
        page_context_shell: bool,
    ) -> None:
        if self._editor_section_subtitle:
            title = editor_title_for_element(m)
            self._editor_section_subtitle.configure(text=title)
        log_event(
            "studio.gicleeframe.editor.shell_ready_after_click",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            page_context_shell=page_context_shell,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _populate_editor(
        self,
        m: MergedPageElement,
        *,
        visual_cache_refresh: bool = False,
        atomic_swap: bool = False,
    ) -> None:
        etype = m.element_type
        fields = editor_field_visibility(etype)
        readonly = etype == "section_legacy"
        cache_entry = self._section_visual_cache.get(m.element_id)
        generation = self._selection_generation
        _ = (visual_cache_refresh, atomic_swap)

        segment_started = time.perf_counter()
        self._ensure_editor_identity_built()
        log_event(
            "studio.gicleeframe.selection.editor.ensure_identity",
            element_id=m.element_id,
            element_type=etype,
            generation=generation,
            elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

        segment_started = time.perf_counter()
        self._ensure_minimal_editor_rows_for_fields(fields)
        log_event(
            "studio.gicleeframe.selection.editor.ensure_rows",
            element_id=m.element_id,
            element_type=etype,
            generation=generation,
            elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

        if self._editor_status_dot:
            dot_color, _ = _element_pill_colors(m.status, has_draft_patch=m.has_draft_patch)
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=self._selected_section_label())

        page_context_from_cache = (
            cache_entry is not None
            and cache_entry.fields_page_context
            and bool(cache_entry.page_context_summary)
        )
        if page_context_from_cache and cache_entry is not None:
            self._apply_cached_page_context_summary(cache_entry)
        elif fields.page_context:
            self._show_page_context_shell_state(m)
        elif self._page_context_frame is not None:
            self._page_context_frame.pack_forget()

        with span(
            "studio.gicleeframe.populate_editor",
            element_type=etype,
            element_id=m.element_id,
            defer_details=True,
        ):
            segment_started = time.perf_counter()
            log_event(
                "studio.gicleeframe.populate_editor.preview_deferred_requested",
                element_id=m.element_id,
                element_type=etype,
                scheduled_from="details_on_demand",
            )
            log_event(
                "studio.gicleeframe.selection.editor.preview",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
                deferred=True,
            )

            segment_started = time.perf_counter()
            with span("studio.gicleeframe.populate_editor.rows_visibility", element_type=etype):
                if self._legacy_msg_label:
                    if readonly:
                        self._legacy_msg_label.configure(text=_LEGACY_READONLY_MSG)
                        self._legacy_msg_label.pack(fill="x", padx=12, pady=(0, 4))
                    else:
                        self._legacy_msg_label.pack_forget()

                self._set_row_visible(self._title_row, fields.title)
                self._set_row_visible(self._text_row, fields.text)
                self._set_row_visible(self._alt_row, fields.alt)
                self._set_row_visible(self._image_ref_row, fields.image_ref)
                self._set_row_visible(self._notes_row, fields.notes)

                if etype == "image" and self._notes_row is not None:
                    self._notes_row.pack_forget()
                    self._notes_row.pack(fill="x", pady=(8, 8))

                self._set_row_visible(self._visible_row, fields.visible)
                self._set_row_visible(self._children_overview_row, False)
            log_event(
                "studio.gicleeframe.selection.editor.rows_visibility",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
            )

            segment_started = time.perf_counter()
            with span("studio.gicleeframe.populate_editor.fields", element_type=etype):
                if self._title_entry:
                    self._set_entry(self._title_entry, m.title, readonly=readonly or not fields.title)
                if self._text_box:
                    self._set_textbox(self._text_box, m.text, readonly=readonly or not fields.text)
                if self._alt_entry:
                    self._set_entry(self._alt_entry, m.alt, readonly=readonly or not fields.alt)
                if self._image_ref_entry:
                    self._set_entry(self._image_ref_entry, m.image_ref, readonly=True)
                if self._notes_box:
                    self._set_textbox(self._notes_box, m.notes, readonly=readonly or not fields.notes)
                if self._visible_var is not None and fields.visible:
                    self._visible_var.set(m.visible)
            log_event(
                "studio.gicleeframe.selection.editor.fields",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
            )

            segment_started = time.perf_counter()
            log_event(
                "studio.gicleeframe.populate_editor.details_deferred",
                element_id=m.element_id,
                element_type=etype,
                scheduled_from="details_on_demand",
            )
            log_event(
                "studio.gicleeframe.selection.editor.layer_nav",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
                deferred=True,
            )

            segment_started = time.perf_counter()
            log_event(
                "studio.gicleeframe.selection.editor.children",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
                deferred=True,
            )

        page_context_shell = bool(
            fields.page_context
            and (
                editor_context_rows(m)
                or m.page_settings
            )
        )
        log_event(
            "studio.gicleeframe.selection.editor.page_context_schedule_or_fill",
            element_id=m.element_id,
            element_type=etype,
            generation=generation,
            elapsed_ms=0.0,
            since_click_ms=self._since_selection_click_ms(),
            shell_ready=page_context_shell,
            scheduled_early=False,
        )

        self._mark_editor_shell_ready_after_click(
            m,
            page_context_shell=page_context_shell,
        )
        self._mark_editor_stable_shell_ready(m)
        self._hide_heavy_editor_modules()
        self._hide_media_details_stable_shell()
        self._show_details_on_demand_block(m)
        self._hide_editor_refresh_status()

        visible_rows = sum(
            1
            for flag in (
                fields.title,
                fields.text,
                fields.alt,
                fields.image_ref,
                fields.notes,
                fields.page_context,
            )
            if flag
        )
        self._maybe_log_layout_shift_guard(m, phase="populate_done", rows_visible=visible_rows)
        self._save_section_visual_cache(m, fields, media_details_built=False)
        self._mark_editor_content_ready(m)
        self._log_minimal_editor_ready(m, from_cache=False)

        if not self._visual_bootstrap_complete:
            log_event(
                "studio.gicleeframe.visual.first_selection_done",
                since_enter_ms=self._since_visual_enter_ms(),
                element_type=etype,
                element_id=m.element_id,
            )

    def _set_row_visible(self, row: ctk.CTkFrame | None, visible: bool) -> None:
        if row is None:
            return
        if self._atomic_swap_suppress_visible:
            self._atomic_swap_deferred_row_visibility.append((row, visible))
            return
        if visible:
            row.pack(fill="x", pady=(0, 8))
            if row is self._notes_row and self._notes_group_frame is not None:
                self._notes_group_frame.pack(fill="x")
        else:
            row.pack_forget()

    def _set_entry(
        self,
        entry: ctk.CTkEntry,
        value: str,
        *,
        readonly: bool,
    ) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state="disabled" if readonly else "normal")

    def _set_textbox(
        self,
        box: ctk.CTkTextbox,
        value: str,
        *,
        readonly: bool,
    ) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", value)
        box.configure(state="disabled" if readonly else "normal")

