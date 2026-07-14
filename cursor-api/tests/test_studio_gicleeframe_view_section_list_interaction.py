"""Boundary tests for the extracted GICLÉE FRAME section list interaction subsystem."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import customtkinter as ctk
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui import gicleeframe_view_section_list_interaction as interaction_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
)
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
    _GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV,
    _collapse_section_list_on_click_enabled,
)
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
    _SECTION_LIST_WIDTH,
    _SECTION_PLACEHOLDER,
)
from giclee_app.ui.gicleeframe_view_selection_orchestration import (
    GicleeFrameSelectionOrchestrationMixin,
)
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin
from giclee_app.ui.gicleeframe_view_primitives import _GF_BORDER_WARM, _GF_CARD_SOFT

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
INTERACTION_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_interaction.py"
)

_EXPECTED_METHODS = {
    "_selected_section_label",
    "_update_section_list_trigger",
    "_collapse_section_list",
    "_ensure_section_dropdown_rows",
    "_open_section_dropdown",
    "_widget_in_section_dropdown",
    "_bind_section_dropdown_outside_close",
    "_unbind_section_dropdown_outside_close",
    "_on_section_dropdown_outside_click",
    "_toggle_section_list",
    "_on_section_row_click",
    "_top_level_row_id_for_element",
    "_top_level_row_id_for_selection",
    "_set_section_row_highlight",
    "_highlight_section_row",
    "_highlight_section_rows",
    "_section_row_index_at_root_y",
    "_start_section_drag",
    "_finish_section_drag",
}

_HOST_OWNERSHIP = {
    "__init__",
    "_set_merged",
    "_populate_editor",
    "_since_visual_enter_ms",
    "_finalize_full_list_render",
    "_rebuild_page_model_cache",
    "_refresh_inventory",
    "_refresh_inventory_light",
}


class _FakeBooleanVar:
    def __init__(self, value: bool = False) -> None:
        self._value = value

    def get(self) -> bool:
        return self._value

    def set(self, value: bool) -> None:
        self._value = value


class _FakeWidget:
    def __init__(self, *, master: Any | None = None) -> None:
        self.master = master
        self.configure_calls: list[dict[str, Any]] = []
        self.place_calls: list[dict[str, Any]] = []
        self.place_forget_calls = 0
        self.lift_calls = 0
        self.bind_calls: list[tuple[str, Any, str | None]] = []
        self.unbind_calls: list[tuple[str, Any]] = []
        self._width = 200
        self._height = 32
        self._root_x = 10
        self._root_y = 20

    def configure(self, **kwargs: Any) -> None:
        self.configure_calls.append(dict(kwargs))

    def place(self, **kwargs: Any) -> None:
        self.place_calls.append(dict(kwargs))

    def place_forget(self) -> None:
        self.place_forget_calls += 1

    def lift(self) -> None:
        self.lift_calls += 1

    def winfo_width(self) -> int:
        return self._width

    def winfo_height(self) -> int:
        return self._height

    def winfo_rootx(self) -> int:
        return self._root_x

    def winfo_rooty(self) -> int:
        return self._root_y

    def update_idletasks(self) -> None:
        return None

    def bind(self, sequence: str, callback: Any, add: str | None = None) -> None:
        self.bind_calls.append((sequence, callback, add))

    def unbind(self, sequence: str, callback: Any) -> None:
        self.unbind_calls.append((sequence, callback))


class _FakeTopLevel(_FakeWidget):
    pass


class _SectionListInteractionHarness(GicleeFrameSectionListInteractionMixin):
    def __init__(self) -> None:
        self._merged: list[Any] = []
        self._merged_by_id: dict[str, Any] = {}
        self._section_dropdown_options_cache: list[Any] = []
        self._section_tree_rows_cache: list[Any] = []
        self._section_row_frames: dict[str, _FakeWidget] = {}
        self._section_row_ids: list[str] = []
        self._highlighted_section_id: str | None = None
        self._selected_id: str | None = None
        self._selection_generation = 0
        self._selection_click_mono = 0.0
        self._section_list_trigger: _FakeWidget | None = None
        self._section_list_expanded = _FakeBooleanVar(False)
        self._section_dropdown_popup: _FakeWidget | None = None
        self._section_list_column: _FakeWidget | None = None
        self._section_list_scroll: _FakeWidget | None = None
        self._section_list_static_lane: _FakeWidget | None = None
        self._section_list_scroll_upgrade_done = False
        self._section_outside_close_active = False
        self._drag_from_index: int | None = None
        self._page_draft = SimpleNamespace()
        self._inventory: Any | None = None
        self._on_status: Any | None = None
        self._perceived_ready_logged = False
        self._shell_control_built = False
        self._after_calls: list[tuple[int, Any]] = []
        self._select_calls: list[tuple[str, dict[str, Any]]] = []
        self._render_calls = 0
        self._set_merged_calls = 0
        self._update_top_bar_calls = 0
        self._populate_editor_calls: list[Any] = []
        self._collapse_calls = 0
        self._open_calls = 0
        self._highlight_row_calls: list[str | None] = []
        self._highlight_rows_calls = 0
        self._top_level = _FakeTopLevel()

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_calls.append((delay_ms, callback))
        return f"after-{len(self._after_calls)}"

    def winfo_toplevel(self) -> _FakeTopLevel:
        return self._top_level

    def _since_visual_enter_ms(self) -> float:
        return 12.5

    def _select_element(self, element_id: str, *, collapse_list: bool = False) -> None:
        self._select_calls.append((element_id, {"collapse_list": collapse_list}))

    def _render_section_list(self) -> None:
        self._render_calls += 1

    def _set_merged(self, merged: Any) -> None:
        self._set_merged_calls += 1
        self._merged = list(merged)

    def _update_top_bar(self) -> None:
        self._update_top_bar_calls += 1

    def _populate_editor(self, element: Any) -> None:
        self._populate_editor_calls.append(element)

    def _collapse_section_list(self) -> None:
        self._collapse_calls += 1
        GicleeFrameSectionListInteractionMixin._collapse_section_list(self)

    def _open_section_dropdown(self) -> None:
        self._open_calls += 1
        GicleeFrameSectionListInteractionMixin._open_section_dropdown(self)

    def _highlight_section_row(self, previous_id: str | None = None) -> None:
        self._highlight_row_calls.append(previous_id)
        GicleeFrameSectionListInteractionMixin._highlight_section_row(
            self,
            previous_id,
        )

    def _highlight_section_rows(self) -> None:
        self._highlight_rows_calls += 1
        GicleeFrameSectionListInteractionMixin._highlight_section_rows(self)


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def _sample_option(element_id: str, display_label: str) -> SimpleNamespace:
    return SimpleNamespace(element_id=element_id, display_label=display_label)


def _sample_merged(
    element_id: str,
    *,
    element_type: str = "media_section",
    section_key: str = "section-1",
) -> SimpleNamespace:
    return SimpleNamespace(
        element_id=element_id,
        element_type=element_type,
        section_key=section_key,
    )


def test_section_list_interaction_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameSectionListInteractionMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameSectionListInteractionMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameSectionListInteractionMixin.__dict__.items()
        if callable(value) and not name.startswith("__")
    }


def test_section_list_interaction_module_has_no_write_network_or_reverse_host_import() -> None:
    source = INTERACTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "giclee_app.ui.gicleeframe_view"
            assert node.module != ".gicleeframe_view"
    lowered = source.lower()
    assert "write_text(" not in lowered
    assert "subprocess" not in lowered
    assert "shopify" not in lowered
    assert "deploy" not in lowered


def test_section_list_interaction_public_boundary_contract() -> None:
    assert interaction_module.__all__ == (
        "GicleeFrameSectionListInteractionMixin",
        "_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV",
        "_collapse_section_list_on_click_enabled",
    )


def test_collapse_section_list_on_click_enabled_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV, raising=False)
    assert _collapse_section_list_on_click_enabled() is False
    for value in ("1", "true", "TRUE", " yes ", "on", "debug"):
        monkeypatch.setenv(_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV, value)
        assert _collapse_section_list_on_click_enabled() is True
    for value in ("0", "false", "off", "maybe"):
        monkeypatch.setenv(_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV, value)
        assert _collapse_section_list_on_click_enabled() is False


def test_gicleeframe_view_has_eleven_mixins_before_scrollable_frame() -> None:
    mro = GicleeFrameView.__mro__
    for mixin in (
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
    ):
        assert mixin in mro
    assert mro.index(GicleeFrameSectionListRenderingMixin) < mro.index(
        GicleeFrameSectionListInteractionMixin,
    )
    assert mro.index(GicleeFrameSectionListInteractionMixin) < mro.index(
        GicleeFrameSelectionOrchestrationMixin,
    )
    assert mro.index(GicleeFrameSelectionOrchestrationMixin) < mro.index(
        ctk.CTkScrollableFrame,
    )


def test_section_list_interaction_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameSectionListInteractionMixin,
            name,
        )


def test_host_ownership_for_interaction_adapters() -> None:
    for name in _HOST_OWNERSHIP:
        assert name in GicleeFrameView.__dict__


def test_render_section_list_remains_renderer_owned_not_in_interaction() -> None:
    assert "_render_section_list" not in GicleeFrameView.__dict__
    assert "_render_section_list" not in GicleeFrameSectionListInteractionMixin.__dict__
    assert getattr(GicleeFrameView, "_render_section_list") is getattr(
        GicleeFrameSectionListRenderingMixin,
        "_render_section_list",
    )


def test_update_top_bar_remains_ram_variant_owned_not_in_interaction() -> None:
    assert "_update_top_bar" not in GicleeFrameView.__dict__
    assert "_update_top_bar" not in GicleeFrameSectionListInteractionMixin.__dict__
    assert getattr(GicleeFrameView, "_update_top_bar") is getattr(
        GicleeFrameRamVariantMixin,
        "_update_top_bar",
    )


def test_host_keeps_finalize_full_list_render() -> None:
    assert "_finalize_full_list_render" in GicleeFrameView.__dict__
    assert "_finalize_full_list_render" not in GicleeFrameSectionListInteractionMixin.__dict__


def test_selected_section_label_empty_merged() -> None:
    harness = _SectionListInteractionHarness()
    assert harness._selected_section_label() == _SECTION_PLACEHOLDER


def test_selected_section_label_selected_and_child_mapped() -> None:
    harness = _SectionListInteractionHarness()
    harness._merged = [_sample_merged("media-1")]
    harness._section_dropdown_options_cache = [
        _sample_option("media-1", "Media row"),
    ]
    harness._selected_id = "child-1"
    harness._merged_by_id = {
        "child-1": _sample_merged("child-1", element_type="body", section_key="sk1"),
    }
    harness._section_tree_rows_cache = [
        SimpleNamespace(section_key="sk1", row_kind="media_section", element_id="media-1"),
    ]
    assert harness._selected_section_label() == "Media row"


def test_selected_section_label_fallback_to_first_option() -> None:
    harness = _SectionListInteractionHarness()
    harness._merged = [_sample_merged("a")]
    harness._section_dropdown_options_cache = [_sample_option("a", "First")]
    harness._selected_id = "missing"
    assert harness._selected_section_label() == "First"


def test_update_section_list_trigger_noop_and_chevron_copy() -> None:
    harness = _SectionListInteractionHarness()
    harness._update_section_list_trigger()

    trigger = _FakeWidget()
    harness._section_list_trigger = trigger
    harness._section_list_expanded.set(False)
    harness._section_dropdown_options_cache = [_sample_option("a", "Alpha")]
    harness._merged = [_sample_merged("a")]
    harness._selected_id = "a"
    harness._merged_by_id = {"a": _sample_merged("a")}

    harness._update_section_list_trigger()
    assert trigger.configure_calls[-1]["text"].endswith("  ▾")

    harness._section_list_expanded.set(True)
    harness._update_section_list_trigger()
    assert trigger.configure_calls[-1]["text"].endswith("  ▴")


def test_collapse_section_list_order_and_unbind() -> None:
    harness = _SectionListInteractionHarness()
    popup = _FakeWidget()
    trigger = _FakeWidget()
    harness._section_dropdown_popup = popup
    harness._section_list_trigger = trigger
    harness._section_list_expanded.set(True)
    harness._section_outside_close_active = True
    harness._top_level.bind("<Button-1>", harness._on_section_dropdown_outside_click, add="+")

    harness._collapse_section_list()

    assert harness._section_list_expanded.get() is False
    assert popup.place_forget_calls == 1
    assert harness._section_outside_close_active is False
    assert harness._top_level.unbind_calls


def test_ensure_section_dropdown_rows_reuse_and_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListInteractionHarness()
    harness._section_row_ids = ["a"]
    harness._section_row_frames = {"a": _FakeWidget()}
    events: list[tuple[str, dict[str, Any]]] = []

    def _log(event: str, **kwargs: Any) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr(interaction_module, "log_event", _log)
    harness._ensure_section_dropdown_rows()
    assert events == [
        ("studio.gicleeframe.section_dropdown.rows_reused", {"row_count": 1}),
    ]
    assert harness._highlight_row_calls == [None]
    assert harness._render_calls == 0

    harness._section_row_ids = []
    harness._section_row_frames = {}
    harness._ensure_section_dropdown_rows()
    assert ("studio.gicleeframe.section_dropdown.rows_rebuilt", {}) in events
    assert harness._render_calls == 1


def test_open_section_dropdown_guards() -> None:
    harness = _SectionListInteractionHarness()
    GicleeFrameSectionListInteractionMixin._open_section_dropdown(harness)
    assert harness._section_list_expanded.get() is False


def test_open_section_dropdown_geometry_and_delayed_bind() -> None:
    harness = _SectionListInteractionHarness()
    popup = _FakeWidget()
    trigger = _FakeWidget()
    trigger._width = 100
    trigger._height = 24
    trigger._root_x = 50
    trigger._root_y = 60
    parent = _FakeWidget()
    parent._root_x = 10
    parent._root_y = 20
    scroll = _FakeWidget()
    harness._section_dropdown_popup = popup
    harness._section_list_trigger = trigger
    harness._section_list_column = parent
    harness._section_list_scroll = scroll
    harness._section_row_ids = ["a"]
    harness._section_row_frames = {"a": _FakeWidget()}

    GicleeFrameSectionListInteractionMixin._open_section_dropdown(harness)

    assert harness._section_list_expanded.get() is True
    assert popup.configure_calls[-1]["width"] == _SECTION_LIST_WIDTH
    assert scroll.configure_calls[-1]["width"] == max(_SECTION_LIST_WIDTH - 12, 180)
    assert popup.place_calls[-1]["x"] == 40
    assert popup.place_calls[-1]["y"] == 66
    assert popup.lift_calls == 1
    assert harness._after_calls == [(80, harness._bind_section_dropdown_outside_close)]


def test_widget_in_section_dropdown_ancestry() -> None:
    harness = _SectionListInteractionHarness()
    popup = _FakeWidget()
    trigger = _FakeWidget()
    inner = _FakeWidget(master=popup)
    outside = _FakeWidget(master=_FakeWidget())
    harness._section_dropdown_popup = popup
    harness._section_list_trigger = trigger
    assert harness._widget_in_section_dropdown(popup) is True
    assert harness._widget_in_section_dropdown(trigger) is True
    assert harness._widget_in_section_dropdown(inner) is True
    assert harness._widget_in_section_dropdown(outside) is False


def test_bind_unbind_outside_close_idempotence_and_callback_identity() -> None:
    harness = _SectionListInteractionHarness()
    harness._bind_section_dropdown_outside_close()
    assert harness._section_outside_close_active is True
    assert len(harness._top_level.bind_calls) == 1
    callback = harness._top_level.bind_calls[0][1]
    harness._bind_section_dropdown_outside_close()
    assert len(harness._top_level.bind_calls) == 1

    harness._unbind_section_dropdown_outside_close()
    assert harness._section_outside_close_active is False
    assert harness._top_level.unbind_calls == [("<Button-1>", callback)]
    harness._unbind_section_dropdown_outside_close()
    assert len(harness._top_level.unbind_calls) == 1


def test_outside_click_collapsed_inside_and_outside_paths() -> None:
    harness = _SectionListInteractionHarness()
    harness._section_list_expanded.set(False)
    harness._on_section_dropdown_outside_click(SimpleNamespace(widget=_FakeWidget()))
    assert harness._collapse_calls == 0

    popup = _FakeWidget()
    harness._section_dropdown_popup = popup
    harness._section_list_trigger = _FakeWidget()
    harness._section_list_expanded.set(True)
    harness._on_section_dropdown_outside_click(SimpleNamespace(widget=popup))
    assert harness._collapse_calls == 0

    harness._on_section_dropdown_outside_click(SimpleNamespace(widget=_FakeWidget()))
    assert harness._collapse_calls == 1


def test_toggle_section_list_open_and_collapse() -> None:
    harness = _SectionListInteractionHarness()
    harness._toggle_section_list()
    assert harness._open_calls == 1
    harness._section_list_expanded.set(True)
    harness._toggle_section_list()
    assert harness._collapse_calls == 1


def test_on_section_row_click_telemetry_and_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListInteractionHarness()
    harness._merged_by_id = {"a": _sample_merged("a")}
    harness._selection_generation = 3
    events: list[tuple[str, dict[str, Any]]] = []

    def _log(event: str, **kwargs: Any) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr(interaction_module, "log_event", _log)
    monkeypatch.setattr(
        interaction_module,
        "_collapse_section_list_on_click_enabled",
        lambda: False,
    )

    before = harness._selection_click_mono
    harness._on_section_row_click("a")
    assert harness._selection_click_mono >= before
    assert events[0][0] == "studio.gicleeframe.selection.click"
    payload = events[0][1]
    assert payload["element_id"] == "a"
    assert payload["source"] == "row"
    assert payload["selection_generation_next"] == 4
    assert payload["since_enter_ms"] == 12.5
    assert harness._select_calls == [("a", {"collapse_list": False})]

    monkeypatch.setattr(
        interaction_module,
        "_collapse_section_list_on_click_enabled",
        lambda: True,
    )
    harness._on_section_row_click("a")
    assert harness._select_calls[-1] == ("a", {"collapse_list": True})


def test_top_level_row_mapping_and_missing_paths() -> None:
    harness = _SectionListInteractionHarness()
    assert harness._top_level_row_id_for_element(None) is None
    assert harness._top_level_row_id_for_element("missing") is None
    harness._merged_by_id = {
        "child": _sample_merged("child", element_type="image", section_key="sk"),
    }
    harness._section_tree_rows_cache = [
        SimpleNamespace(section_key="sk", row_kind="media_section", element_id="media"),
    ]
    assert harness._top_level_row_id_for_element("child") == "media"
    harness._selected_id = "child"
    assert harness._top_level_row_id_for_selection() == "media"


def test_set_section_row_highlight_and_exception_guard() -> None:
    harness = _SectionListInteractionHarness()

    class _BrokenFrame(_FakeWidget):
        def configure(self, **kwargs: Any) -> None:
            raise RuntimeError("broken")

    harness._set_section_row_highlight(None, True)
    harness._set_section_row_highlight("missing", True)
    frame = _FakeWidget()
    harness._section_row_frames = {"a": frame}
    harness._set_section_row_highlight("a", True)
    assert frame.configure_calls[-1]["fg_color"] == _GF_CARD_SOFT
    harness._set_section_row_highlight("a", False)
    assert frame.configure_calls[-1]["border_width"] == 0

    harness._section_row_frames = {"b": _BrokenFrame()}
    harness._set_section_row_highlight("b", True)


def test_highlight_section_row_targeted_previous_current() -> None:
    harness = _SectionListInteractionHarness()
    prev = _FakeWidget()
    current = _FakeWidget()
    harness._section_row_frames = {"prev": prev, "curr": current}
    harness._merged_by_id = {
        "prev": _sample_merged("prev"),
        "curr": _sample_merged("curr"),
    }
    harness._selected_id = "curr"
    harness._highlight_section_row(previous_id="prev")
    assert prev.configure_calls[-1]["border_width"] == 0
    assert current.configure_calls[-1]["border_width"] == 1
    assert harness._highlighted_section_id == "curr"


def test_highlight_section_rows_full_scan() -> None:
    harness = _SectionListInteractionHarness()
    a = _FakeWidget()
    b = _FakeWidget()
    harness._section_row_ids = ["a", "b"]
    harness._section_row_frames = {"a": a, "b": b}
    harness._selected_id = "b"
    harness._merged_by_id = {"b": _sample_merged("b")}
    harness._highlight_section_rows()
    assert a.configure_calls[-1]["border_width"] == 0
    assert b.configure_calls[-1]["border_width"] == 1
    assert harness._highlighted_section_id == "b"


def test_section_row_index_at_root_y() -> None:
    harness = _SectionListInteractionHarness()
    frame = _FakeWidget()
    frame._root_y = 100
    frame._height = 40
    harness._section_row_ids = ["a"]
    harness._section_row_frames = {"a": frame}
    assert harness._section_row_index_at_root_y(120) == 0
    assert harness._section_row_index_at_root_y(200) is None


def test_start_section_drag_valid_and_invalid() -> None:
    harness = _SectionListInteractionHarness()
    frame = _FakeWidget()
    harness._section_row_ids = ["a"]
    harness._section_row_frames = {"a": frame}
    harness._start_section_drag(0)
    assert harness._drag_from_index == 0
    assert frame.configure_calls[-1]["fg_color"] == _GF_CARD_SOFT
    harness._start_section_drag(5)
    assert harness._drag_from_index == 5


def test_finish_section_drag_missing_origin_and_y() -> None:
    harness = _SectionListInteractionHarness()
    harness._finish_section_drag(SimpleNamespace(y_root=100))
    assert harness._highlight_rows_calls == 1


def test_finish_section_drag_same_or_missing_destination() -> None:
    harness = _SectionListInteractionHarness()
    frame = _FakeWidget()
    frame._root_y = 100
    frame._height = 40
    harness._section_row_ids = ["a"]
    harness._section_row_frames = {"a": frame}
    harness._drag_from_index = 0
    harness._finish_section_drag(SimpleNamespace(y_root=120))
    assert harness._highlight_rows_calls == 1


def test_finish_section_drag_reorder_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListInteractionHarness()
    a = _FakeWidget()
    b = _FakeWidget()
    a._root_y = 100
    a._height = 40
    b._root_y = 150
    b._height = 40
    harness._section_row_ids = ["a", "b"]
    harness._section_row_frames = {"a": a, "b": b}
    harness._drag_from_index = 0
    monkeypatch.setattr(interaction_module, "reorder_page_blocks", lambda *_a, **_k: False)
    harness._finish_section_drag(SimpleNamespace(y_root=170))
    assert harness._highlight_rows_calls == 1
    assert harness._render_calls == 0


def test_finish_section_drag_success_without_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListInteractionHarness()
    a = _FakeWidget()
    b = _FakeWidget()
    a._root_y = 100
    a._height = 40
    b._root_y = 150
    b._height = 40
    harness._section_row_ids = ["a", "b"]
    harness._section_row_frames = {"a": a, "b": b}
    harness._merged = [_sample_merged("a"), _sample_merged("b")]
    harness._merged_by_id = {"a": _sample_merged("a"), "b": _sample_merged("b")}
    harness._selected_id = "a"
    harness._drag_from_index = 0
    status_messages: list[str] = []
    harness._on_status = status_messages.append
    monkeypatch.setattr(interaction_module, "reorder_page_blocks", lambda *_a, **_k: True)

    harness._finish_section_drag(SimpleNamespace(y_root=170))

    assert harness._render_calls == 1
    assert harness._update_top_bar_calls == 1
    assert harness._set_merged_calls == 0
    assert harness._populate_editor_calls == [harness._merged_by_id["a"]]
    assert status_messages == ["Kolejność zaktualizowana w RAM · nic nie zapisano"]


def test_finish_section_drag_success_with_inventory_remerge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListInteractionHarness()
    a = _FakeWidget()
    b = _FakeWidget()
    a._root_y = 100
    a._height = 40
    b._root_y = 150
    b._height = 40
    harness._section_row_ids = ["a", "b"]
    harness._section_row_frames = {"a": a, "b": b}
    harness._merged = [_sample_merged("a"), _sample_merged("b")]
    harness._merged_by_id = {"a": _sample_merged("a"), "b": _sample_merged("b")}
    harness._inventory = SimpleNamespace()
    harness._drag_from_index = 1
    monkeypatch.setattr(interaction_module, "reorder_page_blocks", lambda *_a, **_k: True)
    monkeypatch.setattr(
        interaction_module,
        "merge_inventory_with_draft",
        lambda *_a, **_k: [_sample_merged("b"), _sample_merged("a")],
    )

    harness._finish_section_drag(SimpleNamespace(y_root=120))

    assert harness._set_merged_calls == 1
    assert harness._render_calls == 1


def test_interaction_source_ownership_in_module() -> None:
    text = INTERACTION_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert f"def {name}" in text
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert f"def {name}" not in host_text
    assert "GICLEE_GF_COLLAPSE_SECTION_LIST_ON_CLICK" not in host_text
    assert "def _collapse_section_list_on_click_enabled" not in host_text


def test_selection_click_event_fields_in_interaction_module() -> None:
    text = INTERACTION_PATH.read_text(encoding="utf-8")
    click_body = _method_block(text, "_on_section_row_click")
    assert "studio.gicleeframe.selection.click" in click_body
    for field in (
        "element_id",
        "source",
        "static_lane",
        "scroll_ready",
        "selection_generation_next",
    ):
        assert field in click_body
