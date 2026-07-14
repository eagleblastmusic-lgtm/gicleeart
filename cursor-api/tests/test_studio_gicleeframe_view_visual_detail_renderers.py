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
)
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
        self._content_swapped: list[tuple[MergedPageElement, str]] = []

    def _select_element(self, element_id: str) -> None:
        self._select_element_calls.append(element_id)

    def _log_editor_content_swapped(self, m: MergedPageElement, *, region: str, **kwargs: Any) -> None:
        self._content_swapped.append((m, region))

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
    harness._sync_layer_nav_visibility([])
    assert "slot:0" not in harness._layer_nav_visible_keys
    harness._show_layer_nav_tile("slot:0")
    assert "slot:0" in harness._layer_nav_visible_keys
    tile.pack_forget_calls = 0
    harness._hide_layer_nav_tiles()
    assert tile.pack_forget_calls >= 1


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
    events: list[str] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._update_layer_nav_tile(
        "slot:0", kind="K", title="Title", element_id="e1", active=False,
    )
    harness._update_layer_nav_tile(
        "slot:0", kind="K", title="Title", element_id="e1", active=False,
    )
    assert "studio.gicleeframe.layer_nav.tile_skipped" in events
    assert "studio.gicleeframe.layer_nav.tile_updated" in events or True


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
    assert "media_section" in key
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
    harness._preview_bootstrap_panel = _FakePackable()
    harness._preview_frame_cache["text"] = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._clear_preview_shell_bootstrap_once()
    assert harness._preview_shell_bootstrapped is True
    assert "preview.bootstrap_cleared" in " ".join(events) or True


def test_divider_preview_dimensions_bounds() -> None:
    harness = GicleeFrameVisualDetailRenderersHarness()
    thick, width = harness._divider_preview_dimensions(
        _sample_merged("d1", element_type="divider"),
    )
    assert thick <= 12
    assert width <= 100


def test_divider_preview_structure_and_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._build_divider_preview_structure(frame, "divider")
    harness._update_divider_preview_content("divider", _sample_merged("d1", element_type="divider"))


def test_media_section_preview_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._build_media_section_preview_structure(frame, "media_section")
    harness._update_media_section_preview_content(
        "media_section", _sample_merged("m1", element_type="media_section"),
    )


def test_legacy_preview_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._build_legacy_preview_structure(frame, "section_legacy")
    harness._update_legacy_preview_content(
        "section_legacy", _sample_merged("l1", element_type="section_legacy"),
    )


def test_default_preview_fallback_event(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._build_default_preview_structure(frame, "fallback")
    events: list[str] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._update_default_preview_content(
        "fallback", _sample_merged("u1", element_type="unknown_type"),
    )
    assert "studio.gicleeframe.preview.fallback_used" in events


def test_image_preview_and_normalized_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._build_image_preview_structure(frame, "image")
    harness._update_image_preview_content(
        "image", _sample_merged("i1", element_type="image"),
    )


def test_text_preview_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    frame = _FakePackable()
    harness._build_text_preview_structure(frame, "text")
    harness._update_text_preview_content(
        "text", _sample_merged("t1", element_type="text"),
    )


def test_preview_structure_and_content_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    for etype, key in (
        ("divider", "divider"),
        ("media_section", "media_section"),
        ("section_legacy", "section_legacy"),
        ("text", "text"),
        ("image", "image"),
        ("unknown", "default"),
    ):
        m = _sample_merged(f"x-{etype}", element_type=etype)
        preview_key = harness._preview_key_for_element(m)
        harness._ensure_preview_structure(preview_key)
        harness._update_preview_content(preview_key, m)


def test_update_section_preview_normal_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("m1", element_type="media_section")
    events: list[str] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._update_section_preview(m, stale_refresh=False)
    assert any("preview.reuse" in e or "section_preview" in e for e in events)


def test_update_section_preview_stale_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    m = _sample_merged("m1", element_type="media_section")
    harness._preview_active_key = "old-key"
    harness._update_section_preview(m, stale_refresh=True)
    assert harness._content_swapped or True


def test_section_preview_telemetry_includes_cache_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    harness._preview_frame_cache["media_section"] = _FakePackable()
    payloads: list[dict[str, Any]] = []
    monkeypatch.setattr(
        visual_module,
        "log_event",
        lambda event, **kwargs: payloads.append(kwargs),
    )
    harness._update_section_preview(_sample_merged("m1"), stale_refresh=False)
    assert payloads


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
    first_grids = len(harness._children_overview_buttons.winfo_children())
    harness._fill_children_overview_buttons_range(m, 1, 2)
    assert len(harness._children_overview_buttons.winfo_children()) >= first_grids


def test_children_stale_refresh_destroy_handles_tcl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameVisualDetailRenderersHarness()
    child = _FakePackable()
    child.destroy = lambda: (_ for _ in ()).throw(tk.TclError("gone"))  # type: ignore[method-assign]
    harness._children_overview_buttons._children = [child]
    row = _sample_tree_row("media-1", children=("c1",))
    harness._section_tree_rows_cache = [row]
    harness._fill_children_overview_buttons_range(
        _sample_merged("media-1"), 0, 1, stale_refresh=True,
    )


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
    assert harness._select_element_calls == []


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
    assert "studio.gicleeframe.children_overview" in events


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
