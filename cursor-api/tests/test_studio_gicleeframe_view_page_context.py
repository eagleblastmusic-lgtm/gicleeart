"""Boundary tests for the extracted GICLÉE FRAME page context engine subsystem."""

from __future__ import annotations

import ast
import os
import sys
import tkinter as tk
from pathlib import Path
from typing import Any
from unittest.mock import patch

import customtkinter as ctk
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_page_draft import (
    MergedPageElement,
    editor_field_visibility,
)
from giclee_app.studio.gicleeframe_page_settings import PageSettingField
from giclee_app.ui import gicleeframe_view_page_context as page_context_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_details_on_demand import GicleeFrameDetailsOnDemandMixin
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_models import PageContextRowSpec
from giclee_app.ui.gicleeframe_view_page_context import (
    GicleeFramePageContextMixin,
    _DIVIDER_LAZY_GROUPS,
    _F2_FIELD_LABEL_WIDTH,
    _GF_PAGE_CONTEXT_BATCH_DELAY_MS,
    _GF_PAGE_CONTEXT_BATCH_SIZE,
    _GF_PAGE_CONTEXT_DEFER_MS,
    _GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE,
    _GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS,
    _GF_PAGE_CONTEXT_SHELL_STATUS_TEXT,
    _GF_PAGE_CONTEXT_STABLE_DEFER_MS,
    _GF_PROGRESSIVE_PAGE_CONTEXT_ENV,
    _progressive_page_context_enabled,
)
from giclee_app.ui.gicleeframe_view_page_readiness import GicleeFramePageReadinessMixin
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_readiness_row import GicleeFrameReadinessRowMixin
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_shell import GicleeFrameSectionListShellMixin
from giclee_app.ui.gicleeframe_view_selection_orchestration import (
    GicleeFrameSelectionOrchestrationMixin,
)
from giclee_app.ui.gicleeframe_view_structure_dry_run import GicleeFrameStructureDryRunMixin
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin
from giclee_app.ui.gicleeframe_view_visual_detail_renderers import (
    GicleeFrameVisualDetailRenderersMixin,
)

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
PAGE_CONTEXT_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_page_context.py"
EDITOR_SHELL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
DETAILS_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_details_on_demand.py"
VISUAL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_visual_detail_renderers.py"
SELECTION_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_selection_orchestration.py"
PAGE_CONTEXT_PATCH = "giclee_app.ui.gicleeframe_view_page_context"

_EXPECTED_METHODS = {
    "_page_context_shell_summary_lines",
    "_show_page_context_shell_state",
    "_schedule_or_fill_page_context",
    "_pack_field_vertical",
    "_pack_setting_field_row",
    "_hide_page_context_rows",
    "_show_page_context_row",
    "_get_or_create_readonly_card",
    "_get_or_create_page_context_row",
    "_get_or_create_divider_grid",
    "_get_or_create_divider_group",
    "_update_setting_widget",
    "_create_page_setting_widget",
    "_get_or_create_page_setting_row",
    "_get_or_create_setting_card",
    "_reset_page_context_settings_on_layout_change",
    "_edit_panel_pack_anchor",
    "_cancel_page_context_jobs",
    "_schedule_page_context_job",
    "_page_context_pack_kwargs",
    "_clear_page_context_loading_label",
    "_show_page_context_loading_state",
    "_page_context_row_specs",
    "_reset_page_context_lazy_group_visual_state",
    "_make_page_setting_spec",
    "_format_page_setting_value",
    "_create_page_context_setting_summary_row",
    "_close_active_setting_editor",
    "_open_inline_setting_editor",
    "_create_full_setting_editor_inside_row",
    "_create_page_context_collapsed_group_row",
    "_expand_page_context_group",
    "_populate_page_context_group_batch",
    "_precompute_page_context_specs_cache",
    "_create_page_context_row_from_spec",
    "_populate_page_context_batch",
    "_populate_page_context_progressive_stable",
    "_populate_page_context_progressive",
    "_fill_page_context",
}

_PAGE_CONTEXT_CONSTANTS = (
    "_F2_FIELD_LABEL_WIDTH",
    "_GF_PROGRESSIVE_PAGE_CONTEXT_ENV",
    "_GF_PAGE_CONTEXT_BATCH_SIZE",
    "_GF_PAGE_CONTEXT_BATCH_DELAY_MS",
    "_GF_PAGE_CONTEXT_DEFER_MS",
    "_GF_PAGE_CONTEXT_STABLE_DEFER_MS",
    "_GF_PAGE_CONTEXT_SHELL_STATUS_TEXT",
    "_GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE",
    "_GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS",
    "_DIVIDER_LAZY_GROUPS",
)

_HOST_ADAPTER_METHODS = (
    "_ensure_page_context_shell_built",
    "_apply_cached_page_context_summary",
    "_build_setting_group_card",
    "_since_selection_click_ms",
    "_defer_background_for_selection",
    "_schedule_selection_job",
    "_select_element",
    "after",
    "after_cancel",
    "winfo_exists",
)

_HOST_LIFECYCLE_IN_VIEW = (
    "__init__",
    "on_show",
    "_apply_edit_to_draft",
    "_refresh_inventory",
)

_SELECTION_ORCHESTRATION_EXCLUSIONS = (
    "_select_element",
    "_schedule_atomic_swap_populate",
    "_run_atomic_swap_populate",
    "_populate_editor_deferred",
)

_VISUAL_RENDERER_EXCLUSIONS = (
    "_update_section_preview",
    "_update_layer_nav",
    "_fill_children_overview_buttons",
)

_DETAILS_EXCLUSIONS = (
    "_on_details_on_demand_clicked",
    "_execute_details_module",
)

_FOREIGN_ENGINE_METHODS = (
    "_update_section_preview",
    "_update_layer_nav",
    "_fill_children_overview_buttons",
    "_fill_children_overview_buttons_range",
    "_on_details_on_demand_clicked",
    "_execute_details_module",
    "_apply_cached_page_context_summary",
    "_load_inventory",
    "on_show",
    "_ensure_page_context_shell_built",
)


def _host_defines_method(name: str, host_text: str) -> bool:
    return f"def {name}(" in host_text


def _host_initializes_state(name: str, host_text: str) -> bool:
    return f"self.{name}" in host_text


def _sample_merged(
    element_id: str,
    *,
    element_type: str = "media_section",
    section_key: str = "section-1",
    **overrides: Any,
) -> MergedPageElement:
    base = dict(
        element_id=element_id,
        section_key=section_key,
        element_type=element_type,
        group="content",
        order=1,
        label="Label",
        title="Title",
        text="Body text",
        image_ref="shopify://shop_images/foo/bar.png",
        alt="Alt text",
        notes="Notes",
        editable=True,
        source="inventory",
        status="ok",
        has_draft_patch=False,
        visible=True,
        page_settings=(),
        page_fields=(),
    )
    base.update(overrides)
    return MergedPageElement(**base)


def _setting_field(
    key: str,
    *,
    label: str | None = None,
    value: str = "1",
    control: str = "select",
    options: tuple[str, ...] = ("1", "2"),
) -> PageSettingField:
    return PageSettingField(
        label=label or key,
        key=key,
        value=value,
        control=control,
        options=options,
    )


def _divider_merged(**settings: str) -> MergedPageElement:
    fields = tuple(
        _setting_field(key, value=value, options=(value, "other"))
        for key, value in settings.items()
    )
    return _sample_merged("d1", element_type="divider", page_settings=fields)


def _event_payloads(
    events: list[tuple[str, dict[str, Any]]],
    name: str,
) -> list[dict[str, Any]]:
    return [payload for event, payload in events if event == name]


class _FakePackable:
    tk = object()

    def __init__(self, *, master: Any | None = None, text: str = "", **kwargs: Any) -> None:
        self.master = master
        self._text = text
        self._kwargs = kwargs
        self.configure_calls: list[dict[str, Any]] = []
        self.pack_calls: list[dict[str, Any]] = []
        self.pack_forget_calls = 0
        self.grid_calls: list[dict[str, Any]] = []
        self.grid_remove_calls = 0
        self.destroy_calls = 0
        self._managed = False
        self._children: list[Any] = []
        self.bind_calls: list[tuple[str, Any]] = []

    def configure(self, **kwargs: Any) -> None:
        if "text" in kwargs:
            self._text = kwargs["text"]
        self.configure_calls.append(dict(kwargs))

    def cget(self, key: str) -> Any:
        if key == "text":
            return self._text
        return ""

    def pack(self, **kwargs: Any) -> None:
        self._managed = True
        self.pack_calls.append(dict(kwargs))

    def pack_forget(self) -> None:
        self._managed = False
        self.pack_forget_calls += 1

    def pack_propagate(self, _flag: bool) -> None:
        return None

    def pack_configure(self, **kwargs: Any) -> None:
        self.pack(**kwargs)

    def grid_propagate(self, _flag: bool) -> None:
        return None

    def grid(self, **kwargs: Any) -> None:
        self._managed = True
        self.grid_calls.append(dict(kwargs))

    def grid_remove(self) -> None:
        self._managed = False
        self.grid_remove_calls += 1

    def place(self, **_kwargs: Any) -> None:
        return None

    def grid_columnconfigure(self, *_a: Any, **_k: Any) -> None:
        return None

    def destroy(self) -> None:
        self.destroy_calls += 1

    def winfo_manager(self) -> str:
        return "pack" if self._managed else ""

    def winfo_exists(self) -> bool:
        return True

    def winfo_children(self) -> tuple[Any, ...]:
        return tuple(self._children)

    def bind(self, sequence: str, handler: Any) -> None:
        self.bind_calls.append((sequence, handler))


class _FakeFrame(_FakePackable):
    def __init__(self, master: Any | None = None, **kwargs: Any) -> None:
        super().__init__(master=master, **kwargs)
        if isinstance(master, _FakePackable):
            master._children.append(self)


class _FakeLabel(_FakePackable):
    def __init__(self, master: Any | None = None, *, text: str = "", **kwargs: Any) -> None:
        super().__init__(master=master, text=text, **kwargs)
        if isinstance(master, _FakePackable):
            master._children.append(self)


class _FakeButton(_FakePackable):
    def __init__(
        self,
        master: Any | None = None,
        *,
        text: str = "",
        command: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master=master, text=text, **kwargs)
        self._command = command
        if isinstance(master, _FakePackable):
            master._children.append(self)


class _FakeEntry(_FakePackable):
    def __init__(self, master: Any | None = None, **kwargs: Any) -> None:
        super().__init__(master=master, **kwargs)
        self._value = ""
        if isinstance(master, _FakePackable):
            master._children.append(self)

    def insert(self, _index: int | str, value: str) -> None:
        self._value = value

    def delete(self, _start: int | str, _end: int | str) -> None:
        self._value = ""


class _FakeOptionMenu(_FakePackable):
    def __init__(
        self,
        master: Any | None = None,
        *,
        values: list[str] | tuple[str, ...] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(master=master, **kwargs)
        self._values = list(values)
        self._value = values[0] if values else ""
        if isinstance(master, _FakePackable):
            master._children.append(self)

    def set(self, value: str) -> None:
        self._value = value


def _patch_fake_ctk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.ctk.CTkFrame", _FakeFrame)
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.ctk.CTkLabel", _FakeLabel)
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.ctk.CTkButton", _FakeButton)
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.ctk.CTkEntry", _FakeEntry)
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.ctk.CTkOptionMenu", _FakeOptionMenu)
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.theme.get_font", lambda *_a, **_k: "Arial 10")
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.theme.TextMuted", "#aaa")
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.theme.TextPrimary", "#fff")
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.theme.PanelBg", "#111")
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.theme.BorderSubtle", "#222")
    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}.theme.CardHover", "#333")
    for name, value in (
        ("_GF_MUTED", "#888"),
        ("_f2_entry_kwargs", lambda: {}),
        ("_f2_menu_kwargs", lambda: {}),
    ):
        monkeypatch.setattr(page_context_module, name, value, raising=False)

    def _make_gf_card(parent: Any, **_k: Any) -> _FakeFrame:
        return _FakeFrame(parent)

    monkeypatch.setattr(f"{PAGE_CONTEXT_PATCH}._make_gf_card", _make_gf_card)


class GicleeFramePageContextHarness(GicleeFramePageContextMixin):
    def __init__(self) -> None:
        self._edit_panel: _FakeFrame | None = _FakeFrame()
        self._page_context_frame: _FakeFrame | None = _FakeFrame()
        self._page_context_inner: _FakeFrame | None = _FakeFrame()
        self._page_setting_widgets: dict[str, Any] = {}
        self._page_context_row_cache: dict[str, _FakeFrame] = {}
        self._page_context_value_widgets: dict[str, Any] = {}
        self._page_context_visible_keys: set[str] = set()
        self._page_context_row_managers: dict[str, str] = {}
        self._page_context_settings_layout: str = ""
        self._page_context_last_signature: tuple[str, ...] = ()
        self._page_context_readonly_body: _FakeFrame | None = None
        self._page_context_divider_group_bodies: dict[str, _FakeFrame] = {}
        self._page_context_divider_group_grid_opts: dict[str, dict[str, object]] = {}
        self._page_context_setting_card_bodies: dict[str, _FakeFrame] = {}
        self._page_context_after_ids: list[str] = []
        self._page_context_generation = 0
        self._selection_generation = 1
        self._page_context_loading_label: _FakeLabel | None = None
        self._page_context_shell_shown_generation = 0
        self._page_context_specs_cache: dict[str, list[PageContextRowSpec]] = {}
        self._page_context_collapsed_group_rows: dict[str, _FakeFrame] = {}
        self._page_context_collapsed_group_bodies: dict[str, _FakeFrame] = {}
        self._page_context_collapsed_group_buttons: dict[str, _FakeButton] = {}
        self._page_context_expanded_group_ids: set[str] = set()
        self._active_setting_editor_row: _FakeFrame | None = None
        self._active_setting_editor_key: str | None = None
        self._page_context_summary_rows: dict[str, _FakeFrame] = {}
        self._page_context_summary_value_labels: dict[str, _FakeLabel] = {}
        self._notes_row: _FakeFrame | None = None
        self._image_ref_row: _FakeFrame | None = None
        self._selected_id: str | None = None
        self._merged: list[MergedPageElement] = []
        self._atomic_swap_suppress_visible = False
        self._selection_visual_cache_applied = False
        self._scheduled_jobs: list[tuple[int, Any]] = []
        self._after_job_map: dict[str, tuple[int, Any]] = {}
        self._after_counter = 0
        self._select_element_calls: list[str] = []
        self._defer_background_calls: list[dict[str, Any]] = []

    def _build_setting_group_card(
        self,
        parent: Any,
        title: str,
    ) -> tuple[_FakeFrame, _FakeFrame]:
        card = _FakeFrame(parent)
        body = _FakeFrame(card)
        card._title = title  # type: ignore[attr-defined]
        return card, body

    def _ensure_page_context_shell_built(self) -> None:
        return None

    def _apply_cached_page_context_summary(self, *_a: Any, **_k: Any) -> None:
        return None

    def _since_selection_click_ms(self) -> float | None:
        return 5.0

    def _defer_background_for_selection(self, **kwargs: Any) -> bool:
        self._defer_background_calls.append(dict(kwargs))
        return False

    def _schedule_selection_job(self, delay_ms: int, callback: Any) -> None:
        self._scheduled_jobs.append((delay_ms, callback))

    def _select_element(self, element_id: str) -> None:
        self._select_element_calls.append(element_id)

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_counter += 1
        after_id = f"after-{self._after_counter}"
        self._after_job_map[after_id] = (delay_ms, callback)
        return after_id

    def after_cancel(self, after_id: str) -> None:
        self._after_job_map.pop(after_id, None)
        if after_id in self._page_context_after_ids:
            self._page_context_after_ids.remove(after_id)

    def winfo_exists(self) -> bool:
        return True

    def run_scheduled_jobs(self) -> None:
        jobs = list(self._after_job_map.values())
        self._after_job_map.clear()
        for _delay, callback in jobs:
            callback()


# --- §10.1–7 ownership / MRO / host boundaries ---


def test_page_context_exact_thirty_nine_method_ownership_and_identity() -> None:
    assert len(_EXPECTED_METHODS) == 39
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFramePageContextMixin.__dict__.items()
        if callable(value) and not name.startswith("__")
    }
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(GicleeFramePageContextMixin, name)


def test_page_context_module_exports_constants_and_helper() -> None:
    expected_all = (
        "GicleeFramePageContextMixin",
        *_PAGE_CONTEXT_CONSTANTS,
        "_progressive_page_context_enabled",
    )
    assert page_context_module.__all__ == expected_all
    assert _F2_FIELD_LABEL_WIDTH == 88
    assert _GF_PROGRESSIVE_PAGE_CONTEXT_ENV == "GICLEE_GF_PROGRESSIVE_PAGE_CONTEXT"
    assert _GF_PAGE_CONTEXT_BATCH_SIZE == 8
    assert _GF_PAGE_CONTEXT_BATCH_DELAY_MS == 0
    assert _GF_PAGE_CONTEXT_DEFER_MS == 10
    assert _GF_PAGE_CONTEXT_STABLE_DEFER_MS == 80
    assert _GF_PAGE_CONTEXT_SHELL_STATUS_TEXT == "Ustawienia sekcji są aktualizowane…"
    assert _GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE == 1
    assert _GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS == 0
    assert _DIVIDER_LAZY_GROUPS == {
        "line": ("Linia", ("thickness", "width_percent", "alignment_horizontal")),
        "layout": ("Układ", ("section_width", "padding-block-start", "padding-block-end")),
        "style": ("Styl", ("color_scheme", "corner_radius")),
    }


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        (None, True),
        ("1", True),
        ("true", True),
        ("YES", True),
        ("on", True),
        ("debug", True),
        ("0", False),
        ("false", False),
        ("off", False),
        ("disabled", False),
    ],
)
def test_progressive_page_context_enabled_env_semantics(
    env_value: str | None,
    expected: bool,
) -> None:
    with patch.dict(os.environ, {}, clear=True):
        if env_value is not None:
            os.environ[_GF_PROGRESSIVE_PAGE_CONTEXT_ENV] = env_value
        assert _progressive_page_context_enabled() is expected


def test_page_context_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFramePageContextMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFramePageContextMixin.__dict__


def test_page_context_module_has_no_reverse_host_import() -> None:
    source = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "giclee_app.ui.gicleeframe_view"
            assert node.module != ".gicleeframe_view"


def test_page_context_module_has_no_write_network_or_deploy() -> None:
    source = PAGE_CONTEXT_PATH.read_text(encoding="utf-8").lower()
    for token in ("write_text(", "requests", "subprocess", "shopify api", "deploy("):
        assert token not in source


def test_gicleeframe_view_has_fifteen_mixins_before_scrollable_frame() -> None:
    expected = (
        GicleeFrameBrandPanelMixin,
        GicleeFramePageReadinessMixin,
        GicleeFrameStructureDryRunMixin,
        GicleeFrameSafetyCardMixin,
        GicleeFrameReadinessRowMixin,
        GicleeFrameTopBarMixin,
        GicleeFrameRamVariantMixin,
        GicleeFrameSectionListShellMixin,
        GicleeFrameSectionListRenderingMixin,
        GicleeFrameSectionListInteractionMixin,
        GicleeFrameSelectionOrchestrationMixin,
        GicleeFrameEditorShellMixin,
        GicleeFrameDetailsOnDemandMixin,
        GicleeFrameVisualDetailRenderersMixin,
        GicleeFramePageContextMixin,
        ctk.CTkScrollableFrame,
    )
    assert GicleeFrameView.__mro__[1 : 1 + len(expected)] == expected


def test_host_ownership_for_state_lifecycle_and_draft_exclusions() -> None:
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    page_context_text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")
    selection_text = SELECTION_PATH.read_text(encoding="utf-8")
    visual_text = VISUAL_PATH.read_text(encoding="utf-8")
    details_text = DETAILS_PATH.read_text(encoding="utf-8")
    for name in _HOST_LIFECYCLE_IN_VIEW:
        assert _host_defines_method(name, host_text), name
        assert f"def {name}(" not in page_context_text, name
    for name in _SELECTION_ORCHESTRATION_EXCLUSIONS:
        assert f"def {name}(" in selection_text, name
        assert f"def {name}(" not in page_context_text, name
    for name in _VISUAL_RENDERER_EXCLUSIONS:
        assert f"def {name}(" in visual_text, name
        assert f"def {name}(" not in page_context_text, name
    for name in _DETAILS_EXCLUSIONS:
        assert f"def {name}(" in details_text, name
        assert f"def {name}(" not in page_context_text, name
    for state_name in (
        "_page_context_frame",
        "_page_context_inner",
        "_page_context_row_cache",
        "_page_context_specs_cache",
        "_page_context_after_ids",
        "_selection_generation",
        "_atomic_swap_suppress_visible",
        "_selected_id",
        "_merged",
    ):
        assert _host_initializes_state(state_name, host_text), state_name


def test_page_context_module_host_adapters_not_defined() -> None:
    page_context_text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")
    editor_text = EDITOR_SHELL_PATH.read_text(encoding="utf-8")
    details_text = DETAILS_PATH.read_text(encoding="utf-8")
    selection_text = SELECTION_PATH.read_text(encoding="utf-8")
    for name in _HOST_ADAPTER_METHODS:
        assert f"def {name}(" not in page_context_text, name
    assert "def _ensure_page_context_shell_built(" in editor_text
    assert "def _build_setting_group_card(" in editor_text
    assert "def _apply_cached_page_context_summary(" in details_text
    assert "def _defer_background_for_selection(" in selection_text


# --- §10.8–45 behavior ---


def test_page_context_shell_summary_lines_with_and_without_settings() -> None:
    harness = GicleeFramePageContextHarness()
    bare = _sample_merged("m1", element_type="media_section")
    lines = harness._page_context_shell_summary_lines(bare)
    assert ("Typ sekcji", "media_section") in lines
    assert ("Status", "ok") in lines
    assert not any(label == "Ustawienia" for label, _value in lines)

    with_settings = _divider_merged(thickness="2", width_percent="50")
    lines2 = harness._page_context_shell_summary_lines(with_settings)
    assert any(label == "Ustawienia" and "divider" in value for label, value in lines2)


def test_show_page_context_shell_state_suppressed_by_atomic_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    harness._atomic_swap_suppress_visible = True
    m = _sample_merged("m1")
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._show_page_context_shell_state(m)
    assert events == []
    assert harness._page_context_frame.pack_calls == []


def test_show_page_context_shell_state_renders_summary_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    harness._selected_id = "m1"
    m = _sample_merged("m1", element_type="media_section", status="warn")
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._show_page_context_shell_state(m)
    assert harness._page_context_frame.pack_calls
    assert "container:readonly" in harness._page_context_visible_keys
    assert any(key.startswith("shell_summary:") for key in harness._page_context_visible_keys)
    assert harness._page_context_shell_shown_generation == harness._selection_generation
    assert any(event == "studio.gicleeframe.page_context.shell_ready" for event, _ in events)


def test_schedule_or_fill_page_context_progressive_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2")
    fields = editor_field_visibility(m.element_type)
    schedule_calls: list[tuple[int, Any]] = []
    real_schedule = harness._schedule_page_context_job

    def tracked_schedule(delay_ms: int, callback: Any) -> None:
        schedule_calls.append((delay_ms, callback))
        real_schedule(delay_ms, callback)

    harness._schedule_page_context_job = tracked_schedule  # type: ignore[method-assign]
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    with patch.dict(os.environ, {_GF_PROGRESSIVE_PAGE_CONTEXT_ENV: "1"}):
        harness._schedule_or_fill_page_context(m, fields, m.element_type)
    assert "studio.gicleeframe.page_context.deferred" in events
    assert schedule_calls
    assert schedule_calls[0][0] == _GF_PAGE_CONTEXT_STABLE_DEFER_MS


def test_schedule_or_fill_page_context_immediate_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2")
    fields = editor_field_visibility(m.element_type)
    fill_calls: list[tuple[bool, ...]] = []
    harness._fill_page_context = lambda el, *, show: fill_calls.append((show,))  # type: ignore[method-assign]
    with patch.dict(os.environ, {_GF_PROGRESSIVE_PAGE_CONTEXT_ENV: "0"}):
        harness._schedule_or_fill_page_context(m, fields, m.element_type)
    assert fill_calls == [(True,)]


def test_schedule_or_fill_page_context_hidden_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFramePageContextHarness()
    m = _sample_merged("legacy-1", element_type="section_legacy")
    fields = editor_field_visibility(m.element_type)
    fill_calls: list[bool] = []
    harness._fill_page_context = lambda el, *, show: fill_calls.append(show)  # type: ignore[method-assign]
    harness._schedule_or_fill_page_context(m, fields, m.element_type)
    assert fill_calls == [False]


def test_pack_field_vertical_and_setting_field_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    parent = _FakeFrame()
    entry = _FakeEntry()
    harness._pack_field_vertical(parent, "Label", entry)
    assert len(parent.winfo_children()) == 1
    row = parent.winfo_children()[0]
    assert len(row.winfo_children()) == 1
    assert entry.pack_calls

    select_parent = _FakeFrame()
    field = _setting_field("thickness", options=("1", "2", "3"))
    harness._pack_setting_field_row(select_parent, field)
    assert "thickness" in harness._page_setting_widgets

    entry_parent = _FakeFrame()
    text_field = _setting_field("notes", control="text", options=())
    harness._pack_setting_field_row(entry_parent, text_field)
    assert "notes" in harness._page_setting_widgets


def test_hide_page_context_rows_pack_and_grid_tcl_errors() -> None:
    harness = GicleeFramePageContextHarness()
    pack_row = _FakeFrame()
    grid_row = _FakeFrame()
    harness._page_context_row_cache = {
        "pack:1": pack_row,
        "grid:1": grid_row,
    }
    harness._page_context_row_managers = {"pack:1": "pack", "grid:1": "grid"}
    harness._page_context_visible_keys = {"pack:1", "grid:1"}

    def _raise_tcl(*_a: Any, **_k: Any) -> None:
        raise tk.TclError("gone")

    pack_row.pack_forget = _raise_tcl  # type: ignore[method-assign]
    grid_row.grid_remove = _raise_tcl  # type: ignore[method-assign]
    harness._hide_page_context_rows()
    assert harness._page_context_visible_keys == set()

    pack_row.pack_forget = _FakePackable.pack_forget.__get__(pack_row, _FakePackable)  # type: ignore[method-assign]
    grid_row.grid_remove = _FakePackable.grid_remove.__get__(grid_row, _FakePackable)  # type: ignore[method-assign]
    harness._page_context_visible_keys = {"pack:1", "grid:1"}
    harness._hide_page_context_rows()
    assert harness._page_context_visible_keys == set()
    assert pack_row.pack_forget_calls == 1
    assert grid_row.grid_remove_calls == 1


def test_show_page_context_row_idempotent_and_tcl_errors() -> None:
    harness = GicleeFramePageContextHarness()
    frame = _FakeFrame()
    harness._page_context_row_cache["row:1"] = frame
    harness._show_page_context_row("row:1", fill="x")
    harness._show_page_context_row("row:1", fill="x")
    assert frame.pack_calls == [{"fill": "x"}]
    assert "row:1" in harness._page_context_visible_keys

    def _raise_tcl(*_a: Any, **_k: Any) -> None:
        raise tk.TclError("gone")

    frame.pack = _raise_tcl  # type: ignore[method-assign]
    harness._page_context_visible_keys.clear()
    harness._show_page_context_row("row:1", fill="x")
    assert "row:1" not in harness._page_context_visible_keys


def test_get_or_create_readonly_card_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    body1 = harness._get_or_create_readonly_card()
    body2 = harness._get_or_create_readonly_card()
    assert body1 is body2
    assert "container:readonly" in harness._page_context_row_cache


def test_get_or_create_page_context_row_reuses_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    row1, label1 = harness._get_or_create_page_context_row("readonly:Label", label="Label")
    row2, label2 = harness._get_or_create_page_context_row("readonly:Label", label="Label")
    assert row1 is row2
    assert label1 is label2


def test_get_or_create_divider_grid_and_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    grid1 = harness._get_or_create_divider_grid()
    grid2 = harness._get_or_create_divider_grid()
    assert grid1 is grid2
    body1 = harness._get_or_create_divider_group("Linia", 0)
    body2 = harness._get_or_create_divider_group("Linia", 0)
    assert body1 is body2
    assert "divider_group:Linia" in harness._page_context_row_cache


def test_update_setting_widget_entry_and_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    entry = _FakeEntry()
    entry.insert(0, "old")
    harness._update_setting_widget(entry, _setting_field("k", value="new", control="text", options=()))
    assert entry._value == "new"

    menu = _FakeOptionMenu(values=("1", "2"))
    menu.set("1")
    harness._update_setting_widget(
        menu,
        _setting_field("k", value="2", options=("1", "2")),
    )
    assert menu._value == "2"
    assert menu.configure_calls[-1]["values"] == ["1", "2"]


def test_create_page_setting_widget_caches_and_reuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    parent = _FakeFrame()
    field = _setting_field("thickness", value="1", options=("1", "2"))
    widget1 = harness._create_page_setting_widget(parent, field)
    widget2 = harness._create_page_setting_widget(parent, field)
    assert widget1 is widget2
    assert harness._page_setting_widgets["thickness"] is widget1


def test_get_or_create_setting_card_flat_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    field = _setting_field("section_width", value="page-width", options=("page-width", "full-width"))
    body1 = harness._get_or_create_setting_card(field)
    body2 = harness._get_or_create_setting_card(field)
    assert body1 is body2
    assert f"setting_card:{field.key}" in harness._page_context_row_cache


def test_reset_page_context_settings_on_layout_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    divider_card = _FakeFrame()
    harness._page_context_row_cache = {
        "container:divider_grid": _FakeFrame(),
        "divider_group:Linia": divider_card,
        "collapsed_group:line": _FakeFrame(),
        "setting_summary:m1:thickness": _FakeFrame(),
        "setting_card:thickness": _FakeFrame(),
        "container:readonly": _FakeFrame(),
    }
    harness._page_context_row_managers = {key: "pack" for key in harness._page_context_row_cache}
    harness._page_context_visible_keys = set(harness._page_context_row_cache)
    harness._page_context_value_widgets = {"setting:thickness": _FakeEntry()}
    harness._page_context_divider_group_bodies = {"divider_group:Linia": _FakeFrame()}
    harness._page_context_setting_card_bodies = {"thickness": _FakeFrame()}
    harness._page_context_collapsed_group_rows = {"line": _FakeFrame()}
    harness._page_context_collapsed_group_bodies = {"line": _FakeFrame()}
    harness._page_context_collapsed_group_buttons = {"line": _FakeButton()}
    harness._page_context_expanded_group_ids = {"line"}
    harness._page_setting_widgets = {"thickness": _FakeEntry()}
    harness._active_setting_editor_row = _FakeFrame()
    harness._active_setting_editor_key = "m1:thickness"

    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._reset_page_context_settings_on_layout_change("flat")
    assert "container:readonly" in harness._page_context_row_cache
    assert "divider_group:Linia" not in harness._page_context_row_cache
    assert harness._page_setting_widgets == {}
    assert harness._active_setting_editor_row is None
    assert "studio.gicleeframe.page_context.destroy_fallback" in events


def test_edit_panel_pack_anchor_skips_context_and_buttons() -> None:
    harness = GicleeFramePageContextHarness()
    assert harness._edit_panel is not None
    context = harness._page_context_frame
    button = _FakeButton(harness._edit_panel)
    anchor = _FakeFrame(harness._edit_panel)
    anchor.pack(fill="x")
    harness._edit_panel._children = [context, button, anchor]  # type: ignore[union-attr]
    assert harness._edit_panel_pack_anchor() is anchor


def test_cancel_and_schedule_page_context_jobs() -> None:
    harness = GicleeFramePageContextHarness()
    seen: list[str] = []

    def _callback() -> None:
        seen.append("ran")

    harness._schedule_page_context_job(10, _callback)
    assert len(harness._page_context_after_ids) == 1
    cancelled = harness._cancel_page_context_jobs()
    assert cancelled == 1
    assert harness._page_context_after_ids == []
    harness._schedule_page_context_job(0, _callback)
    harness.run_scheduled_jobs()
    assert seen == ["ran"]


def test_page_context_pack_kwargs_prefers_notes_and_image_ref() -> None:
    harness = GicleeFramePageContextHarness()
    notes = _FakeFrame()
    notes.pack(fill="x")
    harness._notes_row = notes
    kwargs = harness._page_context_pack_kwargs()
    assert kwargs.get("before") is notes

    harness._notes_row = None
    image_ref = _FakeFrame()
    image_ref.pack(fill="x")
    harness._image_ref_row = image_ref
    kwargs2 = harness._page_context_pack_kwargs()
    assert kwargs2.get("before") is image_ref


def test_clear_page_context_loading_label_tcl_safe() -> None:
    harness = GicleeFramePageContextHarness()
    label = _FakeLabel()

    def _raise_tcl(*_a: Any, **_k: Any) -> None:
        raise tk.TclError("gone")

    label.destroy = _raise_tcl  # type: ignore[method-assign]
    harness._page_context_loading_label = label
    harness._clear_page_context_loading_label()
    assert harness._page_context_loading_label is None


def test_show_page_context_loading_state_delegates_to_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _sample_merged("m1")
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._show_page_context_loading_state(m)
    assert harness._page_context_frame.pack_calls
    assert "studio.gicleeframe.page_context.loading_state" in events
    assert "studio.gicleeframe.selection.page_context.loading_state" in events


def test_page_context_row_specs_divider_lazy_and_flat() -> None:
    harness = GicleeFramePageContextHarness()
    legacy = _sample_merged("legacy", element_type="section_legacy")
    assert harness._page_context_row_specs(legacy, show=False) == []

    flat = _sample_merged(
        "flat-1",
        element_type="media_section",
        page_settings=(_setting_field("section_width"),),
    )
    flat_specs = harness._page_context_row_specs(flat, show=True)
    assert any(spec.kind == "readonly_card" for spec in flat_specs)
    assert any(spec.kind == "setting_card" for spec in flat_specs)

    divider = _divider_merged(
        thickness="2",
        width_percent="50",
        alignment_horizontal="center",
        section_width="page-width",
    )
    divider_specs = harness._page_context_row_specs(divider, show=True)
    collapsed = [spec for spec in divider_specs if spec.kind == "collapsed_group"]
    assert collapsed
    assert all(spec.group_id in _DIVIDER_LAZY_GROUPS for spec in collapsed)


def test_reset_page_context_lazy_group_visual_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2", width_percent="50", alignment_horizontal="center")
    specs = harness._page_context_row_specs(m, show=True)
    harness._page_context_specs_cache[m.element_id] = specs
    body = _FakeFrame()
    body.pack(fill="x")
    btn = _FakeButton(text="old")
    harness._page_context_collapsed_group_bodies = {"line": body}
    harness._page_context_collapsed_group_buttons = {"line": btn}
    harness._page_context_expanded_group_ids = {"line"}
    harness._reset_page_context_lazy_group_visual_state(m)
    assert harness._page_context_expanded_group_ids == set()
    assert body.pack_forget_calls == 1
    assert "▸" in btn._text


def test_make_page_setting_spec_and_format_value() -> None:
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="3")
    spec = harness._make_page_setting_spec(m, "thickness", group_id="line", group_title="Linia")
    assert spec is not None
    assert spec.kind == "page_setting"
    assert spec.setting_id == "thickness"
    assert harness._format_page_setting_value(m, "thickness") == "3"
    assert harness._format_page_setting_value(m, "missing") == "—"


def test_create_page_context_setting_summary_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2")
    parent = _FakeFrame()
    harness._page_context_collapsed_group_bodies["line"] = parent
    spec = harness._make_page_setting_spec(m, "thickness", group_id="line", group_title="Linia")
    assert spec is not None
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._create_page_context_setting_summary_row(m, spec)
    row_key = f"setting_summary:{m.element_id}:thickness"
    assert row_key in harness._page_context_row_cache
    assert "studio.gicleeframe.page_context.setting_summary_created" in events


def test_close_active_setting_editor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    row = _FakeFrame()
    editor = _FakeFrame(row)
    editor._giclee_inline_setting_editor = True  # type: ignore[attr-defined]
    harness._active_setting_editor_row = row
    harness._active_setting_editor_key = "m1:thickness"
    harness._page_context_value_widgets["setting:thickness"] = _FakeEntry()
    harness._page_setting_widgets["thickness"] = _FakeEntry()
    harness._close_active_setting_editor()
    assert harness._active_setting_editor_row is None
    assert "setting:thickness" not in harness._page_context_value_widgets


def test_open_inline_setting_editor_stale_and_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2")
    spec = harness._make_page_setting_spec(m, "thickness", group_id="line", group_title="Linia")
    assert spec is not None
    row = _FakeFrame()
    events: list[str] = []
    span_calls: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )

    class _FakeSpan:
        def __init__(self, name: str, **_kwargs: Any) -> None:
            self._name = name

        def __enter__(self) -> _FakeSpan:
            span_calls.append(self._name)
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

    monkeypatch.setattr(page_context_module, "span", _FakeSpan)

    harness._selected_id = "other"
    harness._open_inline_setting_editor(m, spec, row)
    assert "studio.gicleeframe.page_context.setting_editor_stale" in events

    events.clear()
    harness._selected_id = m.element_id
    harness._open_inline_setting_editor(m, spec, row)
    assert "studio.gicleeframe.page_context.setting_editor.opened" in events
    assert span_calls == ["studio.gicleeframe.page_context.setting_editor.open"]


def test_create_full_setting_editor_inside_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2")
    spec = harness._make_page_setting_spec(m, "thickness", group_id="line", group_title="Linia")
    assert spec is not None
    row = _FakeFrame()
    harness._create_full_setting_editor_inside_row(m, spec, row)
    editors = [
        child
        for child in row.winfo_children()
        if getattr(child, "_giclee_inline_setting_editor", False)
    ]
    assert len(editors) == 1


def test_create_page_context_collapsed_group_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2", width_percent="50", alignment_horizontal="center")
    spec = next(
        spec
        for spec in harness._page_context_row_specs(m, show=True)
        if spec.kind == "collapsed_group"
    )
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._create_page_context_collapsed_group_row(m, spec)
    assert spec.group_id in harness._page_context_collapsed_group_rows
    assert "studio.gicleeframe.page_context.group_placeholder_created" in events


def test_expand_page_context_group_stale_and_expand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2", width_percent="50", alignment_horizontal="center")
    spec = next(
        spec
        for spec in harness._page_context_row_specs(m, show=True)
        if spec.kind == "collapsed_group" and spec.group_id == "line"
    )
    harness._create_page_context_collapsed_group_row(m, spec)
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )

    harness._selected_id = "other"
    harness._expand_page_context_group(m, spec)
    assert "studio.gicleeframe.page_context.group_expand_stale" in events

    events.clear()
    harness._selected_id = m.element_id
    harness._expand_page_context_group(m, spec)
    assert "studio.gicleeframe.page_context.group_expanded" in events
    assert spec.group_id in harness._page_context_expanded_group_ids


def test_populate_page_context_group_batch_stale_and_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2", width_percent="50", alignment_horizontal="center")
    body = _FakeFrame()
    harness._page_context_collapsed_group_bodies["line"] = body
    setting_specs = [
        harness._make_page_setting_spec(m, sid, group_id="line", group_title="Linia")
        for sid in ("thickness", "width_percent", "alignment_horizontal")
    ]
    setting_specs = [spec for spec in setting_specs if spec is not None]
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )

    harness._selected_id = "other"
    harness._populate_page_context_group_batch(m, "line", setting_specs, 0)
    assert "studio.gicleeframe.page_context.group_batch_stale" in events

    events.clear()
    harness._selected_id = m.element_id
    harness._defer_background_for_selection = lambda **kwargs: True  # type: ignore[method-assign]
    harness._populate_page_context_group_batch(m, "line", setting_specs, 0)
    assert harness._defer_background_calls

    harness._defer_background_for_selection = lambda **kwargs: False  # type: ignore[method-assign]
    harness._populate_page_context_group_batch(m, "line", setting_specs, 0)
    assert "studio.gicleeframe.page_context.group_summary_batch" in events


def test_precompute_page_context_specs_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m1 = _divider_merged(thickness="2")
    legacy = _sample_merged("legacy", element_type="section_legacy")
    harness._merged = [m1, legacy]
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    with patch.dict(os.environ, {}, clear=True):
        harness._precompute_page_context_specs_cache()
    assert m1.element_id in harness._page_context_specs_cache
    assert legacy.element_id not in harness._page_context_specs_cache
    payloads = _event_payloads(events, "studio.gicleeframe.page_context.specs_cache_ready")
    assert payloads
    assert payloads[0]["cached_count"] == 1

    with patch.dict(os.environ, {_GF_PROGRESSIVE_PAGE_CONTEXT_ENV: "0"}):
        harness._page_context_specs_cache.clear()
        harness._precompute_page_context_specs_cache()
        assert harness._page_context_specs_cache == {}


def test_create_page_context_row_from_spec_all_kinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2", width_percent="50", alignment_horizontal="center")
    readonly_specs = [
        PageContextRowSpec(kind="readonly_card"),
        PageContextRowSpec(kind="readonly_row", label="Etykieta", value="Label"),
    ]
    for spec in readonly_specs:
        harness._create_page_context_row_from_spec(m, spec)
    assert "container:readonly" in harness._page_context_visible_keys

    divider_specs = [
        PageContextRowSpec(kind="divider_grid"),
        PageContextRowSpec(kind="divider_group", group_title="Linia", slot=0),
    ]
    for spec in divider_specs:
        harness._create_page_context_row_from_spec(m, spec)
    assert "container:divider_grid" in harness._page_context_row_cache

    collapsed = next(
        spec
        for spec in harness._page_context_row_specs(m, show=True)
        if spec.kind == "collapsed_group"
    )
    harness._create_page_context_row_from_spec(m, collapsed)
    assert collapsed.group_id in harness._page_context_collapsed_group_rows

    flat = _sample_merged(
        "flat",
        element_type="media_section",
        page_settings=(_setting_field("section_width"),),
    )
    card_spec = PageContextRowSpec(kind="setting_card", field=flat.page_settings[0])
    harness._create_page_context_row_from_spec(flat, card_spec)
    assert "setting_card:section_width" in harness._page_context_row_cache


def test_populate_page_context_batch_defer_stale_and_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _sample_merged(
        "flat",
        element_type="media_section",
        label="Label",
        page_settings=(_setting_field("section_width"),),
    )
    specs = harness._page_context_row_specs(m, show=True)
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )

    harness._selected_id = "other"
    harness._populate_page_context_batch(m, specs, 0)
    assert "studio.gicleeframe.page_context.batch_stale" in events

    events.clear()
    harness._selected_id = m.element_id
    harness._populate_page_context_batch(m, specs, 0)
    assert "studio.gicleeframe.page_context.batch" in events
    assert "studio.gicleeframe.page_context.progressive_done" in events
    assert "studio.gicleeframe.page_context.reuse" in events
    assert "studio.gicleeframe.page_context" in events


def test_populate_page_context_progressive_stable_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _divider_merged(thickness="2")
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._selection_generation = 2
    harness._selected_id = m.element_id
    harness._populate_page_context_progressive_stable(m, generation=1)
    assert "studio.gicleeframe.page_context.stable_defer_stale" in events
    assert "studio.gicleeframe.selection.page_context.stale" in events


def test_populate_page_context_progressive_layout_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    divider = _divider_merged(thickness="2", width_percent="50", alignment_horizontal="center")
    harness._selected_id = divider.element_id
    harness._page_context_settings_layout = "flat"
    reset_calls: list[str] = []
    real_reset = harness._reset_page_context_settings_on_layout_change

    def tracked_reset(new_layout: str) -> None:
        reset_calls.append(new_layout)
        real_reset(new_layout)

    harness._reset_page_context_settings_on_layout_change = tracked_reset  # type: ignore[method-assign]
    harness._populate_page_context_progressive(divider)
    assert reset_calls == ["divider"]
    assert harness._page_context_settings_layout == "divider"


def test_fill_page_context_show_false_and_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    m = _sample_merged("m1")
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._fill_page_context(m, show=False)
    assert harness._page_context_frame.pack_forget_calls == 1
    assert "studio.gicleeframe.page_context.reuse" in events

    events.clear()
    empty = _sample_merged("empty", element_type="media_section", label="", title="")
    harness._fill_page_context(empty, show=True)
    assert harness._page_context_frame.pack_forget_calls == 2
    assert "studio.gicleeframe.page_context" in events


def test_fill_page_context_immediate_divider_and_flat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    divider = _divider_merged(
        thickness="2",
        width_percent="50",
        alignment_horizontal="center",
        section_width="page-width",
    )
    events: list[str] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._fill_page_context(divider, show=True)
    assert harness._page_context_frame.pack_calls
    assert "container:divider_grid" in harness._page_context_visible_keys
    assert "studio.gicleeframe.page_context.done" in events

    harness._hide_page_context_rows()
    harness._page_context_settings_layout = ""
    flat = _sample_merged(
        "flat",
        element_type="media_section",
        page_settings=(_setting_field("section_width"),),
    )
    harness._fill_page_context(flat, show=True)
    assert any(key.startswith("setting_card:") for key in harness._page_context_visible_keys)


def test_page_context_module_does_not_implement_foreign_engines() -> None:
    page_context_text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")
    for name in _FOREIGN_ENGINE_METHODS:
        assert f"def {name}(" not in page_context_text, name
    visual_text = VISUAL_PATH.read_text(encoding="utf-8")
    details_text = DETAILS_PATH.read_text(encoding="utf-8")
    assert "def _update_section_preview(" in visual_text
    assert "def _on_details_on_demand_clicked(" in details_text
    assert "def _fill_page_context(" in page_context_text
