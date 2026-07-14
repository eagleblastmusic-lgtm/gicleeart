"""Boundary tests for the shared GICLÉE FRAME readiness-row renderer."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui import gicleeframe_view_readiness_row as row_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_page_context import GicleeFramePageContextMixin
from giclee_app.ui.gicleeframe_view_lifecycle_inventory import (
    GicleeFrameLifecycleInventoryMixin,
)
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
)
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
)
from giclee_app.ui.gicleeframe_view_details_on_demand import (
    GicleeFrameDetailsOnDemandMixin,
)
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_visual_detail_renderers import (
    GicleeFrameVisualDetailRenderersMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)

ROOT = Path(__file__).resolve().parents[1]
ROW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_readiness_row.py"

_EXPECTED_METHODS = {"_pack_readiness_row"}
_FORBIDDEN_OWNERSHIP = {
    "__init__",
    "on_show",
    "on_hide",
    "set_navigation",
    "_build_control_column",
    "_toggle_f1_section",
    "_build_control_readiness_card",
    "_fill_page_readiness",
    "_fill_brand_readiness",
    "_refresh_inventory",
    "_select_element",
    "_schedule_selection_populate",
    "_try_atomic_reveal",
    "_populate_editor",
}


class _FakeWidget:
    created: list["_FakeWidget"] = []

    def __init__(self, master: Any, **kwargs: Any) -> None:
        self.master = master
        self.kwargs = dict(kwargs)
        self.pack_kwargs: dict[str, Any] | None = None
        type(self).created.append(self)

    def pack(self, **kwargs: Any) -> "_FakeWidget":
        self.pack_kwargs = dict(kwargs)
        return self


@pytest.fixture(autouse=True)
def _reset_fake_widgets() -> None:
    _FakeWidget.created = []


def test_readiness_row_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameReadinessRowMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameReadinessRowMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameReadinessRowMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }
    assert not (_FORBIDDEN_OWNERSHIP & set(GicleeFrameReadinessRowMixin.__dict__))


def test_readiness_row_module_has_no_write_network_or_scheduler_ownership() -> None:
    source = ROW_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name.startswith("Komponenty") for name in imports)
    for forbidden_import in ("pathlib", "requests", "shutil", "subprocess"):
        assert forbidden_import not in imports
    for forbidden_text in (
        "write_text",
        "open(",
        "filedialog",
        "shopify",
        "after(",
        "after_idle(",
        "after_cancel(",
    ):
        assert forbidden_text not in source.lower()


def test_readiness_row_public_boundary_contract() -> None:
    assert row_module.__all__ == ("GicleeFrameReadinessRowMixin",)


@pytest.mark.parametrize("ok", [True, False, None])
def test_pack_readiness_row_preserves_widget_order_and_layout(
    monkeypatch: pytest.MonkeyPatch,
    ok: bool | None,
) -> None:
    normal_font = object()
    bold_font = object()
    status_token = object()
    status_calls: list[bool | None] = []

    def _font(size: int, weight: str = "normal") -> object:
        assert size == 11
        return bold_font if weight == "bold" else normal_font

    def _status(value: bool | None) -> object:
        status_calls.append(value)
        return status_token

    monkeypatch.setattr(row_module.ctk, "CTkFrame", _FakeWidget)
    monkeypatch.setattr(row_module.ctk, "CTkLabel", _FakeWidget)
    monkeypatch.setattr(row_module.theme, "get_font", _font)
    monkeypatch.setattr(row_module, "status_color", _status)

    parent = object()
    GicleeFrameReadinessRowMixin()._pack_readiness_row(
        parent,
        "Etykieta",
        "Wartość",
        ok,
    )

    assert status_calls == [ok]
    assert len(_FakeWidget.created) == 4
    frame, dot, label, value = _FakeWidget.created

    assert frame.master is parent
    assert frame.kwargs == {"fg_color": "transparent"}
    assert frame.pack_kwargs == {"fill": "x", "pady": 2}

    assert dot.master is frame
    assert dot.kwargs == {
        "text": "●",
        "text_color": status_token,
        "width": 20,
    }
    assert dot.pack_kwargs == {"side": "left"}

    assert label.master is frame
    assert label.kwargs == {
        "text": "Etykieta",
        "width": 180,
        "anchor": "w",
        "font": normal_font,
        "text_color": row_module.theme.TextMuted,
    }
    assert label.pack_kwargs == {"side": "left"}

    assert value.master is frame
    assert value.kwargs == {
        "text": "Wartość",
        "anchor": "w",
        "font": bold_font,
    }
    assert value.pack_kwargs == {"side": "left"}


def test_readiness_row_mixin_is_wired_into_gicleeframe_view_mro() -> None:
    assert GicleeFrameBrandPanelMixin in GicleeFrameView.__mro__
    assert GicleeFramePageReadinessMixin in GicleeFrameView.__mro__
    assert GicleeFrameStructureDryRunMixin in GicleeFrameView.__mro__
    assert GicleeFrameSafetyCardMixin in GicleeFrameView.__mro__
    assert GicleeFrameReadinessRowMixin in GicleeFrameView.__mro__
    assert GicleeFrameTopBarMixin in GicleeFrameView.__mro__
    assert GicleeFrameRamVariantMixin in GicleeFrameView.__mro__
    assert GicleeFrameSectionListShellMixin in GicleeFrameView.__mro__
    assert GicleeFrameSectionListRenderingMixin in GicleeFrameView.__mro__
    assert GicleeFrameSectionListInteractionMixin in GicleeFrameView.__mro__
    assert GicleeFrameEditorShellMixin in GicleeFrameView.__mro__
    assert GicleeFrameDetailsOnDemandMixin in GicleeFrameView.__mro__
    assert GicleeFrameVisualDetailRenderersMixin in GicleeFrameView.__mro__
    assert GicleeFramePageContextMixin in GicleeFrameView.__mro__
    assert "_pack_readiness_row" not in GicleeFrameView.__dict__
    assert (
        GicleeFrameView._pack_readiness_row
        is GicleeFrameReadinessRowMixin._pack_readiness_row
    )
    assert "_build_control_column" not in GicleeFrameView.__dict__
    assert (
        GicleeFrameView._build_control_column
        is GicleeFrameLifecycleInventoryMixin._build_control_column
    )
    assert "_toggle_f1_section" not in GicleeFrameView.__dict__
    assert (
        GicleeFrameView._toggle_f1_section
        is GicleeFrameLifecycleInventoryMixin._toggle_f1_section
    )
