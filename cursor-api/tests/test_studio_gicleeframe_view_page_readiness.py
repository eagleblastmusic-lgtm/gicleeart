"""Boundary tests for the extracted GICLÉE FRAME F2 page-readiness panel."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_readiness import GicleeFramePageReadiness
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
    _PAGE_READINESS_TITLE,
)
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin

ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_page_readiness.py"
)

_EXPECTED_METHODS = {
    "_build_control_readiness_card",
    "_toggle_page_readiness",
    "_page_readiness_summary_text",
    "_fill_page_readiness",
}

_FORBIDDEN_OWNERSHIP = {
    "__init__",
    "on_show",
    "on_hide",
    "set_navigation",
    "_build_control_column",
    "_build_control_structure_card",
    "_build_safety_card",
    "_run_structure_dry_run",
    "_pack_readiness_row",
    "_select_element",
    "_schedule_selection_populate",
    "_try_atomic_reveal",
    "_render_section_list_incremental",
    "_populate_page_context_progressive",
    "_save_section_visual_cache",
}


class _FakeExpanded:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = value


class _FakeBody:
    def __init__(self) -> None:
        self.pack_kwargs: dict[str, object] | None = None
        self.forgotten = False

    def pack(self, **kwargs: object) -> None:
        self.pack_kwargs = dict(kwargs)
        self.forgotten = False

    def pack_forget(self) -> None:
        self.forgotten = True


class _FakeToggle:
    def __init__(self) -> None:
        self.configured: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.configured.update(kwargs)


def _ready_fixture() -> GicleeFramePageReadiness:
    return GicleeFramePageReadiness(
        page_inventory_ready=True,
        editor_workflow_ready=True,
        ram_draft_ready=True,
        section_selection_ready=True,
        structure_dry_run_ready=True,
        local_draft_persistence_status="not_started",
        shopify_writer_status="blocked",
        save_apply_status="blocked",
        sync_deploy_status="blocked",
        runtime_mutation_status="blocked",
        save_ready=False,
        status_label="struktura gotowa (bez zapisu)",
        summary="Structure dry-run OK — spec informacyjny.",
    )


def test_page_readiness_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFramePageReadinessMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFramePageReadinessMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFramePageReadinessMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }
    assert not (_FORBIDDEN_OWNERSHIP & set(GicleeFramePageReadinessMixin.__dict__))


def test_page_readiness_module_has_no_write_network_or_scheduler_ownership() -> None:
    source = READINESS_PATH.read_text(encoding="utf-8")
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


def test_page_readiness_public_boundary_contract() -> None:
    from giclee_app.ui import gicleeframe_view_page_readiness as module

    assert isinstance(module.__all__, tuple)
    assert module.__all__ == (
        "GicleeFramePageReadinessMixin",
        "_PAGE_READINESS_TITLE",
    )
    assert _PAGE_READINESS_TITLE == "Readiness (strona)"


def test_page_readiness_summary_preserves_empty_counts() -> None:
    mixin = GicleeFramePageReadinessMixin()
    assert (
        mixin._page_readiness_summary_text(None)
        == "0 gotowe · 6 zablokowane · rozwiń szczegóły"
    )


def test_page_readiness_summary_preserves_ready_counts_and_status() -> None:
    mixin = GicleeFramePageReadinessMixin()
    assert mixin._page_readiness_summary_text(_ready_fixture()) == (
        "struktura gotowa (bez zapisu) · 5 gotowe · 5 zablokowane"
    )


def test_page_readiness_toggle_expands_with_existing_copy() -> None:
    mixin = GicleeFramePageReadinessMixin()
    body = _FakeBody()
    toggle = _FakeToggle()
    expanded = _FakeExpanded(False)
    mixin._page_readiness_body = body
    mixin._page_readiness_toggle = toggle
    mixin._page_readiness_expanded = expanded

    mixin._toggle_page_readiness()

    assert expanded.get() is True
    assert body.pack_kwargs == {"fill": "x"}
    assert toggle.configured == {"text": "▾ Readiness (strona)"}


def test_page_readiness_toggle_collapses_with_existing_copy() -> None:
    mixin = GicleeFramePageReadinessMixin()
    body = _FakeBody()
    toggle = _FakeToggle()
    expanded = _FakeExpanded(True)
    mixin._page_readiness_body = body
    mixin._page_readiness_toggle = toggle
    mixin._page_readiness_expanded = expanded

    mixin._toggle_page_readiness()

    assert expanded.get() is False
    assert body.forgotten is True
    assert toggle.configured == {"text": "▸ Readiness (strona)"}


def test_shared_row_renderer_and_control_orchestration_remain_host_dependencies() -> None:
    assert "_pack_readiness_row" not in GicleeFramePageReadinessMixin.__dict__
    assert "_build_control_column" not in GicleeFramePageReadinessMixin.__dict__
    assert "_run_structure_dry_run" not in GicleeFramePageReadinessMixin.__dict__
    source = inspect.getsource(GicleeFramePageReadinessMixin._fill_page_readiness)
    assert "self._pack_readiness_row" in source


def test_page_readiness_mixin_is_wired_into_gicleeframe_view_mro() -> None:
    assert GicleeFrameBrandPanelMixin in GicleeFrameView.__mro__
    assert GicleeFramePageReadinessMixin in GicleeFrameView.__mro__
    assert GicleeFrameStructureDryRunMixin in GicleeFrameView.__mro__
    assert GicleeFrameSafetyCardMixin in GicleeFrameView.__mro__
    assert GicleeFrameReadinessRowMixin in GicleeFrameView.__mro__
    assert GicleeFrameTopBarMixin in GicleeFrameView.__mro__


def test_page_readiness_methods_resolve_from_mixin_on_gicleeframe_view() -> None:
    for name in _EXPECTED_METHODS:
        assert hasattr(GicleeFrameView, name)
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(GicleeFramePageReadinessMixin, name)


def test_control_orchestration_remains_host_owned_and_renderer_resolves_from_mixin() -> None:
    assert "_build_control_column" in GicleeFrameView.__dict__
    assert "_pack_readiness_row" not in GicleeFrameView.__dict__
    assert (
        GicleeFrameView._pack_readiness_row
        is GicleeFrameReadinessRowMixin._pack_readiness_row
    )
