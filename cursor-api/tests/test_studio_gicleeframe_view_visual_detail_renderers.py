"""Boundary tests for the extracted GICLÉE FRAME visual detail renderers subsystem."""

from __future__ import annotations

import ast
import re
import sys
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import customtkinter as ctk
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_page_draft import (
    MergedPageElement,
    SectionTreeChild,
    SectionTreeRow,
    editor_title_for_element,
)
from giclee_app.studio.gicleeframe_page_settings import PageSettingField
from giclee_app.ui import gicleeframe_view_visual_detail_renderers as visual_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_details_on_demand import GicleeFrameDetailsOnDemandMixin
from giclee_app.ui.gicleeframe_view_editor_shell import (
    GicleeFrameEditorShellMixin,
    _LAYER_NAV_TITLE,
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
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
)
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
VISUAL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_visual_detail_renderers.py"
EDITOR_SHELL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
DETAILS_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_details_on_demand.py"
VISUAL_PATCH = "giclee_app.ui.gicleeframe_view_visual_detail_renderers"

_EXPECTED_METHODS = {
    "_parent_row_for_element",
    "_tree_row_for_element",
    "_image_ref_label",
    "_preview_meta_lines",
    "_apply_metadata_preview_content",
    "_build_section_metadata_preview_structure",
    "_selected_layer_items",
    "_layer_nav_tile_signature",
    "_sync_layer_nav_visibility",
    "_hide_layer_nav_tiles",
    "_show_layer_nav_tile",
    "_get_or_create_layer_nav_header",
    "_get_or_create_layer_nav_row",
    "_get_or_create_layer_nav_tile",
    "_update_layer_nav_tile",
    "_update_layer_nav",
    "_preview_key_for_element",
    "_hide_preview_frames",
    "_show_preview_frame",
    "_get_or_create_preview_frame",
    "_get_or_create_preview_label",
    "_clear_preview_shell_bootstrap_once",
    "_divider_preview_dimensions",
    "_build_divider_preview_structure",
    "_update_divider_preview_content",
    "_build_media_section_preview_structure",
    "_update_media_section_preview_content",
    "_build_legacy_preview_structure",
    "_update_legacy_preview_content",
    "_build_default_preview_structure",
    "_update_default_preview_content",
    "_build_image_preview_structure",
    "_update_image_preview_content",
    "_build_text_preview_structure",
    "_update_text_preview_content",
    "_ensure_preview_structure",
    "_update_preview_content",
    "_update_section_preview",
    "_fill_children_overview_buttons",
    "_fill_children_overview_buttons_range"

}


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}("
    assert marker in text, name
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def _host_defines_method(name: str, host_text: str) -> bool:
    return f"def {name}(" in host_text


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


def _divider_merged(**settings: str) -> MergedPageElement:
    fields = tuple(
        PageSettingField(label=key, key=key, value=value, control="select")
        for key, value in settings.items()
    )
    return _sample_merged("d1", element_type="divider", page_settings=fields)


def _event_payloads(
    events: list[tuple[str, dict[str, Any]]],
    name: str,
) -> list[dict[str, Any]]:
    return [payload for event, payload in events if event == name]


def _sample_tree_row(element_id: str, *, children: tuple[str, ...] = ()) -> SectionTreeRow:
    merged = _sample_merged(element_id)
    child_rows = tuple(
        SectionTreeChild(
            element_id=cid,
            child_label=f"Child {cid}",
            element_type="text",
            merged=_sample_merged(cid, element_type="text"),
        )
        for cid in children
    )
    return SectionTreeRow(
        element_id=element_id,
        row_kind="section",
        section_key=merged.section_key,
        order=1,
        display_title="Parent",
        merged=merged,
        children=child_rows,
    )


def _track_method(harness: Any, name: str, order: list[str]) -> None:
    original = getattr(harness, name)

    def tracked(*args: Any, **kwargs: Any) -> Any:
        order.append(name)
        return original(*args, **kwargs)

    setattr(harness, name, tracked)


def _invoke_button1(widget: _FakePackable) -> None:
    for sequence, handler in widget.bind_calls:
        if sequence == "<Button-1>":
            handler(None)
            return
    raise AssertionError("expected <Button-1> bind callback")


def _button1_bind_count(root: _FakePackable) -> int:
    count = sum(1 for sequence, _handler in root.bind_calls if sequence == "<Button-1>")
    for child in root.winfo_children():
        if isinstance(child, _FakePackable):
            count += _button1_bind_count(child)
    return count


def _tile_child_label(tile: _FakeFrame) -> str:
    labels = [child for child in tile.winfo_children() if isinstance(child, _FakeLabel)]
    assert len(labels) >= 2
    return labels[1]._text


def _find_children_tile(harness: GicleeFrameVisualDetailRenderersHarness) -> _FakeFrame:
    grid = None
    for child in harness._children_overview_buttons.winfo_children():
        if isinstance(child, _FakeFrame):
            grid = child
            break
    assert grid is not None
    tiles = [child for child in grid.winfo_children() if isinstance(child, _FakeFrame)]
    assert len(tiles) == 1
    return tiles[0]


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
        self.grid_calls.append(dict(kwargs))

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


class _FakeCanvas(_FakePackable):
    pass


def _patch_fake_ctk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{VISUAL_PATCH}.ctk.CTkFrame", _FakeFrame)
    monkeypatch.setattr(f"{VISUAL_PATCH}.ctk.CTkLabel", _FakeLabel)
    monkeypatch.setattr(f"{VISUAL_PATCH}.theme.get_font", lambda *_a, **_k: "Arial 10")
    for name, value in (
        ("_GF_FIELD", "#111"),
        ("_GF_CARD_SOFT", "#222"),
        ("_GF_FIELD_HOVER", "#333"),
        ("_GF_BORDER", "#444"),
        ("_GF_BORDER_WARM", "#555"),
        ("_GF_GOLD", "#666"),
        ("_GF_GOLD_SOFT", "#777"),
        ("_GF_MUTED", "#888"),
        ("_BTN_HEIGHT", 28),
        ("_CARD_PAD_X", 12),
    ):
        monkeypatch.setattr(visual_module, name, value, raising=False)

    def _make_gf_card(parent: Any, **_k: Any) -> _FakeFrame:
        return _FakeFrame(parent)

    monkeypatch.setattr(f"{VISUAL_PATCH}._make_gf_card", _make_gf_card)


class GicleeFrameVisualDetailRenderersHarness(GicleeFrameVisualDetailRenderersMixin):
    def __init__(self) -> None:
        self._section_tree_rows_cache: list[SectionTreeRow] = []
        self._layer_nav_frame: _FakePackable | None = _FakePackable()
        self._layer_nav_tile_cache: dict[str, _FakePackable] = {}
        self._layer_nav_title_widgets: dict[str, _FakePackable] = {}
        self._layer_nav_meta_widgets: dict[str, _FakePackable] = {}
        self._layer_nav_visible_keys: set[str] = set()
        self._layer_nav_row_frame: _FakePackable | None = None
        self._layer_nav_header_label: _FakePackable | None = None
        self._layer_nav_rendered_signatures: dict[str, tuple[Any, ...]] = {}
        self._layer_nav_bound_targets: dict[str, str] = {}
        self._layer_nav_visible_order: tuple[str, ...] = ()
        self._preview_frame_cache: dict[str, _FakePackable] = {}
        self._preview_value_widgets: dict[str, dict[str, _FakePackable]] = {}
        self._preview_active_key: str | None = None
        self._preview_shell_bootstrapped = False
        self._preview_bootstrap_panel: _FakePackable | None = None
        self._preview_bootstrap_status_label: _FakePackable | None = None
        self._section_preview_canvas: _FakeCanvas | None = _FakeCanvas()
        self._section_preview_badge: _FakePackable | None = _FakePackable()
        self._section_preview_line: _FakePackable | None = _FakePackable()
        self._children_overview_buttons: _FakePackable | None = _FakePackable()
        self._editor_last_ready_element_id: str | None = None
        self._selected_id: str | None = None
        self._merged: list[MergedPageElement] = []
        self._select_element_calls: list[str] = []
        self._content_swapped: list[tuple[MergedPageElement, str, dict[str, Any]]] = []

    def _select_element(self, element_id: str) -> None:
        self._select_element_calls.append(element_id)

    def _log_editor_content_swapped(
        self,
        m: MergedPageElement,
        *,
        region: str,
        **kwargs: Any,
    ) -> None:
        self._content_swapped.append((m, region, dict(kwargs)))

    def _since_selection_click_ms(self) -> float | None:
        return 5.0


# --- §10.1–8 ownership / MRO ---


def test_visual_renderer_exact_forty_method_ownership_and_identity() -> None:
    assert len(_EXPECTED_METHODS) == 40
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameVisualDetailRenderersMixin.__dict__.items()
        if callable(value) and not name.startswith("__")
    }
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameVisualDetailRenderersMixin,
            name,
        )


def test_visual_renderer_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameVisualDetailRenderersMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameVisualDetailRenderersMixin.__dict__


def test_visual_renderer_module_has_no_reverse_host_import() -> None:
    source = VISUAL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "giclee_app.ui.gicleeframe_view"
            assert node.module != ".gicleeframe_view"


def test_visual_renderer_module_has_no_write_network_or_deploy() -> None:
    source = VISUAL_PATH.read_text(encoding="utf-8").lower()
    for token in ("write_text(", "requests", "subprocess", "shopify api", "deploy("):
        assert token not in source


def test_gicleeframe_view_has_fourteen_mixins_before_scrollable_frame() -> None:
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
        ctk.CTkScrollableFrame,
    )
    assert GicleeFrameView.__mro__[1 : 1 + len(expected)] == expected


def test_visual_renderer_module_has_no_boundary_owned_duplicate_constants() -> None:
    assert visual_module.__all__ == ("GicleeFrameVisualDetailRenderersMixin",)
    visual_text = VISUAL_PATH.read_text(encoding="utf-8")
    assert "_LAYER_NAV_TITLE =" not in visual_text


def test_layer_nav_title_remains_editor_shell_owned_and_imported() -> None:
    editor_text = EDITOR_SHELL_PATH.read_text(encoding="utf-8")
    visual_text = VISUAL_PATH.read_text(encoding="utf-8")
    assert "_LAYER_NAV_TITLE = \"Warstwy sekcji\"" in editor_text
    assert "from .gicleeframe_view_editor_shell import _LAYER_NAV_TITLE" in visual_text
    assert _LAYER_NAV_TITLE == "Warstwy sekcji"


def test_host_ownership_for_page_context_and_lifecycle_exclusions() -> None:
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    visual_text = VISUAL_PATH.read_text(encoding="utf-8")
    for name in (
        "_fill_page_context",
        "_hide_page_context_rows",
        "_populate_page_context_batch",
        "_schedule_page_context_job",
        "on_show",
        "__init__",
    ):
        assert _host_defines_method(name, host_text), name
        assert f"def {name}(" not in visual_text, name


# --- §10.9–39 behavior ---


def test_parent_and_tree_row_lookup() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    parent = _sample_tree_row("parent-1", children=("child-1",))
    harness._section_tree_rows_cache = [parent]
    assert harness._parent_row_for_element("child-1") is parent
    assert harness._parent_row_for_element("parent-1") is parent
    assert harness._tree_row_for_element("parent-1") is parent
    assert harness._parent_row_for_element(None) is None
    assert harness._tree_row_for_element("missing") is None


def test_image_ref_label_normalizes_shopify_prefix() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    assert harness._image_ref_label("shopify://shop_images/a/b.png") == "b.png"
    assert harness._image_ref_label("local.png") == "local.png"


def test_preview_meta_lines_includes_type_and_children() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    row = _sample_tree_row("media-1", children=("c1", "c2"))
    harness._section_tree_rows_cache = [row]
    m = _sample_merged("media-1")
    lines = harness._preview_meta_lines(m)
    assert any("Typ elementu:" in line for line in lines)
    assert any("Elementy podrzędne: 2" in line for line in lines)


def test_apply_metadata_preview_content_fallback_logs_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("x", element_type="unknown")
    label = _FakeLabel()
    harness._preview_value_widgets["k"] = {
        "heading_label": label,
        "subtitle_label": label,
        "meta_label": label,
    }
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._apply_metadata_preview_content("k", m, heading="H", subtitle="S", fallback=True)
    assert any(item[0] == "studio.gicleeframe.preview.fallback_used" for item in events)


def test_selected_layer_items_parent_then_children() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    row = _sample_tree_row("media-1", children=("child-1",))
    harness._section_tree_rows_cache = [row]
    items = harness._selected_layer_items(_sample_merged("media-1"))
    assert len(items) == 2
    assert items[0][0] == "media-1"


def test_layer_nav_tile_signature_is_stable() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    sig = harness._layer_nav_tile_signature(
        kind="K", title="T", meta="M", element_id="e1", active=True,
    )
    assert sig == ("K", "T", "M", "e1", True)


def test_sync_layer_nav_visibility_and_hide_show_tcl() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    tile = _FakePackable()
    harness._layer_nav_tile_cache["slot:0"] = tile
    harness._layer_nav_visible_keys = {"slot:0"}
    harness._layer_nav_visible_order = ("slot:0",)

    def _raise_tcl(*_a: Any, **_k: Any) -> None:
        raise tk.TclError("gone")

    tile.pack_forget = _raise_tcl  # type: ignore[method-assign]
    harness._sync_layer_nav_visibility([])
    assert "slot:0" in harness._layer_nav_visible_keys

    tile.pack_forget = _FakePackable.pack_forget.__get__(tile, _FakePackable)  # type: ignore[method-assign]
    harness._layer_nav_visible_keys = {"slot:0"}
    harness._layer_nav_visible_order = ("slot:0",)
    harness._sync_layer_nav_visibility([])
    assert "slot:0" not in harness._layer_nav_visible_keys

    tile.pack = _raise_tcl  # type: ignore[method-assign]
    harness._show_layer_nav_tile("slot:0")
    assert "slot:0" not in harness._layer_nav_visible_keys

    tile.pack = _FakePackable.pack.__get__(tile, _FakePackable)  # type: ignore[method-assign]
    harness._show_layer_nav_tile("slot:0")
    assert "slot:0" in harness._layer_nav_visible_keys

    tile.pack_forget = _raise_tcl  # type: ignore[method-assign]
    harness._hide_layer_nav_tiles()
    assert "slot:0" not in harness._layer_nav_visible_keys


def test_preview_hide_show_tcl_errors() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._preview_frame_cache["preview:text"] = frame
    harness._preview_active_key = "preview:text"

    def _raise_tcl(*_a: Any, **_k: Any) -> None:
        raise tk.TclError("gone")

    frame.pack_forget = _raise_tcl  # type: ignore[method-assign]
    harness._hide_preview_frames()
    assert harness._preview_active_key is None

    frame.pack_forget = _FakePackable.pack_forget.__get__(frame, _FakePackable)  # type: ignore[method-assign]
    harness._preview_active_key = None

    frame.pack = _raise_tcl  # type: ignore[method-assign]
    harness._show_preview_frame("preview:text")
    assert harness._preview_active_key is None

    frame.pack = _FakePackable.pack.__get__(frame, _FakePackable)  # type: ignore[method-assign]
    harness._show_preview_frame("preview:text")
    assert harness._preview_active_key == "preview:text"


def test_layer_nav_header_row_tile_idempotent_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    header1 = harness._get_or_create_layer_nav_header()
    header2 = harness._get_or_create_layer_nav_header()
    assert header1 is header2
    row1 = harness._get_or_create_layer_nav_row()
    row2 = harness._get_or_create_layer_nav_row()
    assert row1 is row2
    tile1 = harness._get_or_create_layer_nav_tile("slot:0")
    tile2 = harness._get_or_create_layer_nav_tile("slot:0")
    assert tile1 is tile2


def test_update_layer_nav_tile_skip_and_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    tile_events: list[str] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: tile_events.append(event)
        if event
        in {
            "studio.gicleeframe.layer_nav.tile_updated",
            "studio.gicleeframe.layer_nav.tile_skipped",
        }
        else None,
    )
    signature = harness._layer_nav_tile_signature(
        kind="K",
        title="Title",
        meta="",
        element_id="e1",
        active=False,
    )
    harness._update_layer_nav_tile(
        "slot:0", kind="K", title="Title", element_id="e1", active=False,
    )
    tile = harness._layer_nav_tile_cache["slot:0"]
    first_bind_count = len(tile.bind_calls)
    first_kind_configure = len(harness._layer_nav_meta_widgets["slot:0"].configure_calls)
    first_title_configure = len(harness._layer_nav_title_widgets["slot:0"].configure_calls)

    assert tile_events == ["studio.gicleeframe.layer_nav.tile_updated"]
    assert harness._layer_nav_rendered_signatures["slot:0"] == signature
    assert harness._layer_nav_bound_targets["slot:0"] == "e1"
    assert first_bind_count >= 1

    nested_labels = [
        child for child in tile.winfo_children() if isinstance(child, _FakeLabel)
    ]
    assert nested_labels

    harness._select_element_calls.clear()
    _invoke_button1(tile)
    _invoke_button1(nested_labels[0])
    assert harness._select_element_calls == ["e1", "e1"]

    first_binding_count = _button1_bind_count(tile)

    harness._update_layer_nav_tile(
        "slot:0", kind="K", title="Title", element_id="e1", active=False,
    )
    assert tile_events == [
        "studio.gicleeframe.layer_nav.tile_updated",
        "studio.gicleeframe.layer_nav.tile_skipped",
    ]
    assert len(tile.bind_calls) == first_bind_count
    assert _button1_bind_count(tile) == first_binding_count
    assert len(harness._layer_nav_meta_widgets["slot:0"].configure_calls) == first_kind_configure
    assert len(harness._layer_nav_title_widgets["slot:0"].configure_calls) == first_title_configure


def test_update_layer_nav_stale_empty_keeps_visible_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    layer_nav_frame = harness._layer_nav_frame
    assert layer_nav_frame is not None
    layer_nav_frame.pack(fill="x")
    assert layer_nav_frame.winfo_manager() == "pack"

    m = _sample_merged("child-1", element_type="text")
    harness._editor_last_ready_element_id = "prev-ready"
    monkeypatch.setattr(harness, "_selected_layer_items", lambda _merged: [])

    sync_calls: list[list[str]] = []
    real_sync = harness._sync_layer_nav_visibility

    def tracked_sync(desired_keys: list[str]) -> None:
        sync_calls.append(list(desired_keys))
        return real_sync(desired_keys)

    harness._sync_layer_nav_visibility = tracked_sync  # type: ignore[method-assign]

    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append((event, dict(kwargs))),
    )

    pack_forget_before = layer_nav_frame.pack_forget_calls
    harness._update_layer_nav(m, stale_refresh=True)

    assert sync_calls == []
    assert layer_nav_frame.pack_forget_calls == pack_forget_before
    assert layer_nav_frame.winfo_manager() == "pack"
    assert events == [
        (
            "studio.gicleeframe.editor.stale_content_kept",
            {
                "element_id": "child-1",
                "element_type": "text",
                "previous_element_id": "prev-ready",
                "since_click_ms": 5.0,
                "region": "layer_nav",
            },
        ),
    ]
    forbidden = {
        "studio.gicleeframe.layer_nav.delta",
        "studio.gicleeframe.layer_nav.reuse",
        "studio.gicleeframe.layer_nav",
    }
    assert {event for event, _payload in events}.isdisjoint(forbidden)


def test_update_layer_nav_empty_and_populated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("media-1")
    harness._update_layer_nav(m, stale_refresh=False)
    row = _sample_tree_row("media-1", children=("c1",))
    harness._section_tree_rows_cache = [row]
    harness._update_layer_nav(m, stale_refresh=False)
    assert harness._layer_nav_header_label is not None


def test_preview_key_is_type_based() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("id-1", element_type="media_section")
    key = harness._preview_key_for_element(m)
    assert key == "preview:media_section"
    assert "id-1" not in key


def test_preview_hide_show_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._preview_frame_cache["divider"] = frame
    harness._preview_active_key = "divider"
    harness._hide_preview_frames()
    assert harness._preview_active_key is None
    harness._show_preview_frame("divider")
    assert harness._preview_active_key == "divider"


def test_preview_frame_label_cache_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    parent = _FakePackable()
    harness._preview_frame_cache["text"] = parent
    f1 = harness._get_or_create_preview_frame("text")
    f2 = harness._get_or_create_preview_frame("text")
    assert f1 is f2
    l1 = harness._get_or_create_preview_label("text", "heading_label", parent=f1, label="A")
    l2 = harness._get_or_create_preview_label("text", "heading_label", parent=f1, label="B")
    assert l1 is l2


def test_clear_preview_shell_bootstrap_preserves_cached_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    canvas = harness._section_preview_canvas
    assert canvas is not None

    cached = _FakeFrame(canvas)
    stale = _FakeFrame(canvas)
    bootstrap_panel = _FakePackable()
    bootstrap_status = _FakePackable()

    harness._preview_frame_cache["preview:text"] = cached
    canvas._children = [cached, stale]
    harness._preview_bootstrap_panel = bootstrap_panel
    harness._preview_bootstrap_status_label = bootstrap_status

    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )

    harness._clear_preview_shell_bootstrap_once()

    assert bootstrap_panel.destroy_calls == 1
    assert stale.destroy_calls == 1
    assert cached.destroy_calls == 0
    assert harness._preview_shell_bootstrapped is True
    assert harness._preview_bootstrap_panel is None
    assert harness._preview_bootstrap_status_label is None
    assert events == [
        ("studio.gicleeframe.preview.destroy_fallback", {"reason": "shell_bootstrap"}),
    ]


def test_divider_preview_dimensions_bounds() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    valid = harness._divider_preview_dimensions(
        _divider_merged(thickness="3", width_percent="50"),
    )
    assert valid == (6, 97)

    extreme = harness._divider_preview_dimensions(
        _divider_merged(thickness="0.5", width_percent="100"),
    )
    assert extreme == (1, 52)

    invalid = harness._divider_preview_dimensions(
        _divider_merged(thickness="bad", width_percent="nope"),
    )
    assert invalid == (2, 52)


def test_divider_preview_structure_and_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakeFrame()
    preview_key = "preview:divider"
    harness._build_divider_preview_structure(frame, preview_key)
    assert set(harness._preview_value_widgets[preview_key]) == {
        "ghost_top",
        "line",
        "ghost_bottom",
    }
    harness._update_divider_preview_content(
        preview_key,
        _divider_merged(thickness="4", width_percent="20"),
    )
    line = harness._preview_value_widgets[preview_key]["line"]
    assert line.configure_calls[-1]["height"] == 8
    assert line.pack_calls[-1]["padx"] == 124


def test_media_section_preview_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    preview_key = "preview:media_section"
    frame = _FakeFrame()
    harness._build_media_section_preview_structure(frame, preview_key)
    widgets = harness._preview_value_widgets[preview_key]
    assert {"heading_label", "subtitle_label", "meta_label", "hint_label"}.issubset(widgets.keys())
    m = _sample_merged("m1", element_type="media_section", title="Section title")
    harness._update_media_section_preview_content(preview_key, m)
    assert widgets["heading_label"]._text == "Section title"
    assert widgets["subtitle_label"]._text == "Uproszczony podgląd struktury sekcji"


def test_legacy_preview_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    preview_key = "preview:section_legacy"
    frame = _FakeFrame()
    harness._build_legacy_preview_structure(frame, preview_key)
    widgets = harness._preview_value_widgets[preview_key]
    assert {"heading_label", "subtitle_label", "meta_label", "hint_label"}.issubset(widgets.keys())
    m = _sample_merged("l1", element_type="section_legacy", label="Legacy label")
    harness._update_legacy_preview_content(preview_key, m)
    assert widgets["heading_label"]._text == "Legacy label"
    assert "legacy" in widgets["subtitle_label"]._text.lower()


def test_default_preview_fallback_event(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    preview_key = "preview:default"
    frame = _FakeFrame()
    harness._build_default_preview_structure(frame, preview_key)
    events: list[str] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    m = _sample_merged("u1", element_type="unknown_type", title="Fallback title")
    harness._update_default_preview_content(preview_key, m)
    assert "studio.gicleeframe.preview.fallback_used" in events
    assert harness._preview_value_widgets[preview_key]["heading_label"]._text == "Fallback title"


def test_image_preview_and_normalized_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    preview_key = "preview:image"
    frame = _FakeFrame()
    harness._build_image_preview_structure(frame, preview_key)
    widgets = harness._preview_value_widgets[preview_key]
    assert {"heading_label", "ref_label", "footnote_label"}.issubset(widgets.keys())
    m = _sample_merged(
        "i1",
        element_type="image",
        image_ref="shopify://shop_images/foo/bar.png",
    )
    harness._update_image_preview_content(preview_key, m)
    assert widgets["ref_label"]._text == "bar.png"
    assert harness._image_ref_label(m.image_ref) == "bar.png"


def test_text_preview_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    preview_key = "preview:text"
    frame = _FakeFrame()
    harness._build_text_preview_structure(frame, preview_key)
    widgets = harness._preview_value_widgets[preview_key]
    assert {"title_label", "kind_label"}.issubset(widgets.keys())
    m = _sample_merged("t1", element_type="text", title="Heading copy")
    harness._update_text_preview_content(preview_key, m)
    assert widgets["title_label"]._text == "Heading copy"
    assert widgets["kind_label"]._text == editor_title_for_element(m)


def test_preview_structure_and_content_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()

    build_routes = {
        "_build_divider_preview_structure": "divider",
        "_build_media_section_preview_structure": "media_section",
        "_build_legacy_preview_structure": "section_legacy",
        "_build_image_preview_structure": "image",
        "_build_text_preview_structure": "text",
        "_build_default_preview_structure": "default",
    }
    update_routes = {
        "_update_divider_preview_content": "divider",
        "_update_media_section_preview_content": "media_section",
        "_update_legacy_preview_content": "section_legacy",
        "_update_image_preview_content": "image",
        "_update_text_preview_content": "text",
        "_update_default_preview_content": "default",
    }

    for preview_key, element_type, expected in (
        ("preview:divider", "divider", "divider"),
        ("preview:media_section", "media_section", "media_section"),
        ("preview:section_legacy", "section_legacy", "section_legacy"),
        ("preview:image", "image", "image"),
        ("preview:text", "text", "text"),
        ("preview:default", "unknown_type", "default"),
    ):
        build_calls: list[str] = []
        update_calls: list[str] = []
        originals_build = {
            name: getattr(GicleeFrameVisualDetailRenderersMixin, name)
            for name in build_routes
        }
        originals_update = {
            name: getattr(GicleeFrameVisualDetailRenderersMixin, name)
            for name in update_routes
        }

        for name, label in build_routes.items():
            original = originals_build[name].__get__(harness, GicleeFrameVisualDetailRenderersHarness)

            def build_recorder(frame: Any, key: str, *, _label: str = label, _original=original) -> None:
                build_calls.append(_label)
                return _original(frame, key)

            monkeypatch.setattr(harness, name, build_recorder)

        for name, label in update_routes.items():
            original = originals_update[name].__get__(harness, GicleeFrameVisualDetailRenderersHarness)

            def update_recorder(key: str, m: MergedPageElement, *, _label: str = label, _original=original) -> None:
                update_calls.append(_label)
                return _original(key, m)

            monkeypatch.setattr(harness, name, update_recorder)

        m = _sample_merged(f"x-{element_type}", element_type=element_type)
        harness._ensure_preview_structure(preview_key)
        harness._update_preview_content(preview_key, m)
        assert build_calls == [expected]
        assert update_calls == [expected]

    build_calls = []
    update_calls = []
    monkeypatch.setattr(
        harness,
        "_build_default_preview_structure",
        lambda frame, key: build_calls.append("unknown"),
    )
    monkeypatch.setattr(
        harness,
        "_update_default_preview_content",
        lambda key, m: update_calls.append("unknown"),
    )
    unknown_key = "preview:weird"
    harness._ensure_preview_structure(unknown_key)
    harness._update_preview_content(unknown_key, _sample_merged("weird", element_type="weird"))
    assert build_calls == ["unknown"]
    assert update_calls == ["unknown"]


def test_update_section_preview_normal_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("m1", element_type="media_section")
    harness._merged = [m]
    call_order: list[str] = []
    for method_name in (
        "_ensure_preview_structure",
        "_update_preview_content",
        "_clear_preview_shell_bootstrap_once",
        "_hide_preview_frames",
        "_show_preview_frame",
    ):
        _track_method(harness, method_name, call_order)

    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )

    harness._update_section_preview(m, stale_refresh=False)

    assert call_order == [
        "_ensure_preview_structure",
        "_update_preview_content",
        "_clear_preview_shell_bootstrap_once",
        "_hide_preview_frames",
        "_show_preview_frame",
    ]
    badge = harness._section_preview_badge
    assert badge is not None
    assert badge.configure_calls[-1]["text"] == "sekcja edytorska"

    reuse_payloads = _event_payloads(events, "studio.gicleeframe.preview.reuse")
    section_payloads = _event_payloads(events, "studio.gicleeframe.section_preview")
    assert len(reuse_payloads) == 1
    assert len(section_payloads) == 1
    assert reuse_payloads[0]["element_type"] == "media_section"
    assert reuse_payloads[0]["active_key"] == "preview:media_section"
    assert "before_children" in reuse_payloads[0]
    assert "after_children" in reuse_payloads[0]
    assert "cached_frames" in reuse_payloads[0]
    assert "widget_count" in reuse_payloads[0]
    assert section_payloads[0]["element_type"] == "media_section"
    assert "children_before_destroy" in section_payloads[0]


def test_update_section_preview_stale_refresh_same_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("m1", element_type="media_section")
    preview_key = harness._preview_key_for_element(m)
    harness._preview_active_key = preview_key
    blocked: list[str] = []
    harness._clear_preview_shell_bootstrap_once = lambda: blocked.append("clear")  # type: ignore[method-assign]
    harness._hide_preview_frames = lambda: blocked.append("hide")  # type: ignore[method-assign]
    harness._show_preview_frame = lambda key: blocked.append(f"show:{key}")  # type: ignore[method-assign]

    harness._update_section_preview(m, stale_refresh=True)

    assert blocked == []
    assert harness._content_swapped == [(m, "preview", {"preview_key": preview_key})]


def test_update_section_preview_stale_refresh_changed_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("m1", element_type="media_section")
    preview_key = harness._preview_key_for_element(m)
    harness._preview_active_key = "preview:default"
    harness._preview_frame_cache[preview_key] = _FakeFrame()
    show_calls: list[str] = []
    real_show = harness._show_preview_frame

    def tracked_show(key: str) -> None:
        show_calls.append(key)
        real_show(key)

    harness._show_preview_frame = tracked_show  # type: ignore[method-assign]

    harness._update_section_preview(m, stale_refresh=True)

    assert show_calls == [preview_key]
    assert harness._preview_active_key == preview_key
    assert harness._content_swapped == [(m, "preview", {"preview_key": preview_key})]


def test_section_preview_telemetry_includes_cache_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    harness._preview_frame_cache["preview:media_section"] = _FakeFrame()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._update_section_preview(_sample_merged("m1"), stale_refresh=False)
    reuse_payloads = _event_payloads(events, "studio.gicleeframe.preview.reuse")
    assert len(reuse_payloads) == 1
    payload = reuse_payloads[0]
    for field in (
        "element_type",
        "before_children",
        "after_children",
        "active_key",
        "cached_frames",
        "widget_count",
    ):
        assert field in payload


def test_children_overview_zero_and_non_media(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._fill_children_overview_buttons(_sample_merged("d1", element_type="divider"))
    assert any(item[1].get("children_count") == 0 for item in events)


def test_children_overview_range_and_grid_reuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    row = _sample_tree_row("media-1", children=("c1", "c2"))
    harness._section_tree_rows_cache = [row]
    m = _sample_merged("media-1", element_type="media_section")
    harness._fill_children_overview_buttons_range(m, 0, 1)
    first_grid = next(
        child
        for child in harness._children_overview_buttons.winfo_children()
        if isinstance(child, _FakeFrame)
    )

    harness._fill_children_overview_buttons_range(m, 1, 2)
    grids = [
        child
        for child in harness._children_overview_buttons.winfo_children()
        if isinstance(child, _FakeFrame)
    ]
    assert grids == [first_grid]
    assert len(first_grid.winfo_children()) == 2

    tiles = [child for child in first_grid.winfo_children() if isinstance(child, _FakeFrame)]
    assert [_tile_child_label(tile) for tile in tiles] == ["Child c1", "Child c2"]


def test_children_stale_refresh_destroy_handles_tcl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    child = _FakePackable()

    def _raise_tcl(*_a: Any, **_k: Any) -> None:
        raise tk.TclError("gone")

    child.destroy = _raise_tcl  # type: ignore[method-assign]
    harness._children_overview_buttons._children = [child]
    row = _sample_tree_row("media-1", children=("c1",))
    harness._section_tree_rows_cache = [row]
    harness._fill_children_overview_buttons_range(
        _sample_merged("media-1"), 0, 1, stale_refresh=True,
    )
    assert len(harness._children_overview_buttons.winfo_children()) >= 1


def test_children_tile_copy_and_selection_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    row = _sample_tree_row("media-1", children=("c1",))
    harness._section_tree_rows_cache = [row]
    harness._fill_children_overview_buttons_range(
        _sample_merged("media-1", element_type="media_section"), 0, 1,
    )
    tile = _find_children_tile(harness)
    labels = [child for child in tile.winfo_children() if isinstance(child, _FakeLabel)]
    assert len(labels) == 3
    assert labels[0]._text == "EDYTOR SEKCJI"
    assert labels[1]._text == "Child c1"
    assert labels[2]._text == "Kliknij, aby edytować"

    _invoke_button1(tile)
    assert harness._select_element_calls == ["c1"]

    harness._select_element_calls.clear()
    _invoke_button1(labels[1])
    assert harness._select_element_calls == ["c1"]


def test_children_completion_logs_and_content_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    row = _sample_tree_row("media-1", children=("c1", "c2"))
    harness._section_tree_rows_cache = [row]
    m = _sample_merged("media-1", element_type="media_section")
    events: list[str] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._fill_children_overview_buttons_range(m, 0, 2, stale_refresh=True)
    assert events == ["studio.gicleeframe.children_overview"]
    assert harness._content_swapped == [(m, "children", {})]


def test_visual_module_does_not_implement_foreign_engines() -> None:
    visual_text = VISUAL_PATH.read_text(encoding="utf-8")
    details_text = DETAILS_PATH.read_text(encoding="utf-8")
    for name in (
        "_fill_page_context",
        "_on_details_on_demand_clicked",
        "_execute_details_module",
        "_load_inventory",
        "on_show",
    ):
        assert f"def {name}(" not in visual_text, name
    assert "def _update_section_preview(" in visual_text
    assert "def _on_details_on_demand_clicked(" in details_text
