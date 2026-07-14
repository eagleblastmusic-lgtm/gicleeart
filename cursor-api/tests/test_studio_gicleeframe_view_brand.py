"""Boundary tests for the extracted GICLÉE FRAME F1 brand panel."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import (
    GicleeFrameBrandPanelMixin,
    _F1_BRAND_TITLE,
    _F1_LOADING_TEXT,
    _PLACEMENT_PLACEHOLDER,
    _VARIANT_PLACEHOLDER,
)
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_details_on_demand import (
    GicleeFrameDetailsOnDemandMixin,
)
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)

ROOT = Path(__file__).resolve().parents[1]
BRAND_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_brand.py"

_EXPECTED_METHODS = {
    "_build_f1_brand_section_placeholder",
    "_build_f1_brand_section_deferred",
    "_build_f1_brand_section_full",
    "_build_f1_brand_section_panel_content",
    "_build_rules_section",
    "_clear_brand_plan",
    "_fill_brand_readiness",
    "_on_brand_variant",
    "_on_brand_placement",
    "_run_brand_dry_run",
}

_FORBIDDEN_OWNERSHIP = {
    "__init__",
    "on_show",
    "on_hide",
    "set_navigation",
    "_select_element",
    "_schedule_selection_populate",
    "_begin_selection_priority_window",
    "_build_shell",
    "_try_atomic_reveal",
    "_render_section_list_incremental",
    "_populate_page_context_progressive",
    "_on_details_on_demand_clicked",
    "_save_section_visual_cache",
}


def test_brand_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameBrandPanelMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameBrandPanelMixin.__dict__
    assert _EXPECTED_METHODS <= set(GicleeFrameBrandPanelMixin.__dict__)
    assert not (_FORBIDDEN_OWNERSHIP & set(GicleeFrameBrandPanelMixin.__dict__))


def test_brand_module_has_no_component_or_write_imports() -> None:
    source = BRAND_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name.startswith("Komponenty") for name in imports)
    assert "subprocess" not in imports
    assert "requests" not in imports
    assert "shutil" not in imports
    assert "pathlib" not in imports
    assert "write_text" not in source
    assert "open(" not in source
    assert "filedialog" not in source
    assert "shopify" not in source.lower()


def test_brand_module_preserves_f1_copy_and_event_contracts() -> None:
    source = BRAND_PATH.read_text(encoding="utf-8")
    assert _F1_BRAND_TITLE == "Komponent marki (F1)"
    assert _F1_LOADING_TEXT == "Ładowanie panelu F1…"
    assert _VARIANT_PLACEHOLDER == "— wybierz wariant —"
    assert _PLACEMENT_PLACEHOLDER == "— opcjonalnie: strefa —"
    assert "studio.gicleeframe.build.f1_brand_section.deferred" in source
    assert "Wyczyszczono plan marki · nic nie zapisano" in source
    assert "Zasady wizualne" in source
    assert "Zasady motion" in source


def test_brand_methods_are_defined_by_the_mixin() -> None:
    for name in _EXPECTED_METHODS:
        method = getattr(GicleeFrameBrandPanelMixin, name)
        assert inspect.isfunction(method)
        assert method.__qualname__.startswith("GicleeFrameBrandPanelMixin.")


def test_expand_collapse_adapter_remains_outside_brand_mixin() -> None:
    assert "_toggle_f1_section" not in GicleeFrameBrandPanelMixin.__dict__
    placeholder = inspect.getsource(
        GicleeFrameBrandPanelMixin._build_f1_brand_section_placeholder
    )
    full = inspect.getsource(GicleeFrameBrandPanelMixin._build_f1_brand_section_full)
    assert "command=self._toggle_f1_section" in placeholder
    assert "command=self._toggle_f1_section" in full


def test_shared_readiness_row_renderer_remains_outside_brand_mixin() -> None:
    assert "_pack_readiness_row" not in GicleeFrameBrandPanelMixin.__dict__
    source = inspect.getsource(GicleeFrameBrandPanelMixin._fill_brand_readiness)
    assert "self._pack_readiness_row" in source


def test_brand_panel_mixin_is_wired_into_gicleeframe_view_mro() -> None:
    assert GicleeFrameBrandPanelMixin in GicleeFrameView.__mro__
    assert GicleeFrameSectionListRenderingMixin in GicleeFrameView.__mro__
    assert GicleeFrameSectionListInteractionMixin in GicleeFrameView.__mro__
    assert GicleeFrameEditorShellMixin in GicleeFrameView.__mro__
    assert GicleeFrameDetailsOnDemandMixin in GicleeFrameView.__mro__


def test_brand_methods_resolve_from_mixin_on_gicleeframe_view() -> None:
    for name in _EXPECTED_METHODS:
        assert hasattr(GicleeFrameView, name)
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(GicleeFrameBrandPanelMixin, name)


def test_expand_and_readiness_adapters_remain_host_owned() -> None:
    assert "_toggle_f1_section" in GicleeFrameView.__dict__
    assert "_toggle_f1_section" not in GicleeFrameBrandPanelMixin.__dict__
    assert "_pack_readiness_row" not in GicleeFrameView.__dict__
    assert (
        GicleeFrameView._pack_readiness_row
        is GicleeFrameReadinessRowMixin._pack_readiness_row
    )
    assert "_pack_readiness_row" not in GicleeFrameBrandPanelMixin.__dict__
