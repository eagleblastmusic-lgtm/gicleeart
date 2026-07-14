"""Boundary tests for the extracted GICLÉE FRAME section list shell subsystem."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui import gicleeframe_view_section_list_shell as shell_module
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
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
    _GF_SECTION_FIRST_BATCH_SIZE,
    _GF_SECTIONS_COLUMN_EARLY_DEFER_MS,
    _GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS,
    _GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS,
    _SECTION_LIST_HEIGHT,
    _SECTION_LIST_LOADING_TEXT,
    _SECTION_LIST_WIDTH,
    _SECTION_PLACEHOLDER,
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
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin

ROOT = Path(__file__).resolve().parents[1]
SECTION_LIST_SHELL_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
)

_EXPECTED_METHODS = {
    "_schedule_sections_column_early_lane",
    "_log_section_list_column_ready",
    "_build_sections_column_shell",
    "_create_section_list_scroll_frame",
    "_populate_section_list_static_lane",
    "_try_refresh_static_lane_before_scroll_upgrade",
    "_cancel_section_list_scroll_upgrade_fallback",
    "_ensure_section_list_scroll_upgrade_fallback",
    "_schedule_section_list_scroll_upgrade_after_perceived",
    "_schedule_section_list_scroll_upgrade",
    "_build_sections_column_extras",
    "_build_sections_column",
}

_HOST_OWNERSHIP = {
    "__init__",
    "_build_page_editor_section_critical",
    "_build_workspace_critical",
    "_build_sections_column_deferred",
    "_build_sections_column_extras_deferred",
    "_flush_pending_section_list_if_needed",
    "_schedule_section_list_incremental",
    "_upgrade_section_list_scroll",
    "_show_section_list_loading_state",
    "_run_deferred_bootstrap",
    "_try_mark_progressive_full_ready",
    "_finalize_full_list_render",
    "_rebuild_page_model_cache",
    "_log_visual_gate_ready",
    "_try_mark_perceived_ready",
    "_schedule_atomic_reveal_check",
}


class _FakeFrame:
    def __init__(self) -> None:
        self.children: list[Any] = []
        self.pack_calls: list[dict[str, Any]] = []
        self.pack_forget_calls = 0
        self.destroy_calls = 0
        self._exists = True

    def winfo_children(self) -> list[Any]:
        return list(self.children)

    def winfo_exists(self) -> bool:
        return self._exists

    def pack(self, **kwargs: Any) -> None:
        self.pack_calls.append(dict(kwargs))

    def pack_forget(self) -> None:
        self.pack_forget_calls += 1

    def destroy(self) -> None:
        self.destroy_calls += 1
        self._exists = False


class _SectionListShellHarness(GicleeFrameSectionListShellMixin):
    def __init__(self) -> None:
        self._sections_column_early_lane_scheduled = False
        self._shell_sections_built = False
        self._sections_column_early_lane_scheduled_mono = 0.0
        self._sections_column_early_lane_enter_mono = 0.0
        self._section_dropdown_options_cache: list[Any] = []
        self._merged: list[Any] = []
        self._section_tree_rows_cache: list[Any] = []
        self._section_list_column: Any = None
        self._section_list_extras_frame: _FakeFrame | None = None
        self._section_list_static_lane: _FakeFrame | None = None
        self._section_list_scroll: Any = None
        self._section_row_frames: dict[str, Any] = {}
        self._section_row_ids: list[str] = []
        self._section_list_static_lane_real_rows = False
        self._section_list_first_visible_built = False
        self._section_list_scroll_upgrade_scheduled = False
        self._section_list_scroll_upgrade_done = False
        self._section_list_scroll_upgrade_fallback_after_id: str | None = None
        self._perceived_ready_logged = False
        self._sections_column_extras_built = False
        self._section_list_trigger: Any = None
        self._section_dropdown_popup: Any = None
        self._after_calls: list[tuple[int, Any]] = []
        self._after_cancel_calls: list[Any] = []
        self._deferred_calls = 0
        self._upgrade_calls = 0
        self._create_row_calls: list[dict[str, Any]] = []
        self._rebuild_cache_calls = 0
        self._visual_gate_calls: list[dict[str, Any]] = []
        self._perceived_ready_calls: list[str] = []
        self._atomic_reveal_calls: list[str] = []
        self._toggle_calls = 0

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_calls.append((delay_ms, callback))
        return f"after-{len(self._after_calls)}"

    def after_cancel(self, after_id: Any) -> None:
        self._after_cancel_calls.append(after_id)

    def _since_visual_enter_ms(self) -> float:
        return 0.0

    def _queue_latency_since_ms(self, _mono: float) -> float:
        return 0.0

    def _build_sections_column_deferred(self) -> None:
        self._deferred_calls += 1

    def _upgrade_section_list_scroll(self) -> None:
        self._upgrade_calls += 1

    def _create_section_list_row(
        self,
        idx: int,
        element_id: str,
        display_label: str,
        *,
        parent: Any,
        static_lane: bool = False,
    ) -> None:
        self._create_row_calls.append(
            {
                "idx": idx,
                "element_id": element_id,
                "display_label": display_label,
                "parent": parent,
                "static_lane": static_lane,
            }
        )

    def _rebuild_page_model_cache(self) -> None:
        self._rebuild_cache_calls += 1

    def _log_visual_gate_ready(
        self,
        gate: str,
        *,
        source: str,
        since_scheduled_mono: float,
    ) -> None:
        self._visual_gate_calls.append(
            {
                "gate": gate,
                "source": source,
                "since_scheduled_mono": since_scheduled_mono,
            }
        )

    def _try_mark_perceived_ready(self, *, trigger: str) -> None:
        self._perceived_ready_calls.append(trigger)

    def _schedule_atomic_reveal_check(self, *, trigger: str) -> None:
        self._atomic_reveal_calls.append(trigger)

    def _toggle_section_list(self) -> None:
        self._toggle_calls += 1


def test_section_list_shell_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameSectionListShellMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameSectionListShellMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameSectionListShellMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }


def test_section_list_shell_module_has_no_write_network_or_reverse_host_import() -> None:
    source = SECTION_LIST_SHELL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name.startswith("Komponenty") for name in imports)
    assert "giclee_app.ui.gicleeframe_view" not in imports
    for forbidden_import in ("pathlib", "requests", "shutil", "subprocess"):
        assert forbidden_import not in imports
    for forbidden_text in (
        "write_text",
        "open(",
        "filedialog",
        "shopify",
        "deploy",
    ):
        assert forbidden_text not in source.lower()
    assert "after(" in source
    assert "after_cancel(" in source


def test_section_list_shell_public_boundary_contract() -> None:
    assert "GicleeFrameSectionListShellMixin" in shell_module.__all__
    assert "_SECTION_LIST_WIDTH" in shell_module.__all__
    assert "_SECTION_LIST_HEIGHT" in shell_module.__all__


def test_section_list_shell_exact_constants() -> None:
    assert _SECTION_PLACEHOLDER == "— wybierz sekcję —"
    assert _SECTION_LIST_WIDTH == 320
    assert _SECTION_LIST_HEIGHT == 520
    assert _SECTION_LIST_LOADING_TEXT == "Ładowanie struktury sekcji…"
    assert _GF_SECTION_FIRST_BATCH_SIZE == 6
    assert _GF_SECTIONS_COLUMN_EARLY_DEFER_MS == 0
    assert _GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS == 40
    assert _GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS == 800


def test_section_list_shell_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
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
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameSectionListShellMixin,
            name,
        )


def test_host_ownership_for_section_list_adapters() -> None:
    for name in _HOST_OWNERSHIP:
        assert name in GicleeFrameView.__dict__


def test_early_lane_one_shot_guard_and_scheduling() -> None:
    harness = _SectionListShellHarness()
    harness._section_dropdown_options_cache = [SimpleNamespace(element_id="a")]

    harness._schedule_sections_column_early_lane()
    harness._schedule_sections_column_early_lane()

    assert harness._sections_column_early_lane_scheduled
    assert harness._deferred_calls == 0
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_SECTIONS_COLUMN_EARLY_DEFER_MS
    assert harness._after_calls[0][1] == harness._build_sections_column_deferred


def test_early_lane_skips_when_shell_already_built() -> None:
    harness = _SectionListShellHarness()
    harness._shell_sections_built = True

    harness._schedule_sections_column_early_lane()

    assert not harness._sections_column_early_lane_scheduled
    assert harness._after_calls == []


def test_scroll_upgrade_fallback_scheduling_and_cancellation() -> None:
    harness = _SectionListShellHarness()

    harness._ensure_section_list_scroll_upgrade_fallback()
    assert harness._section_list_scroll_upgrade_fallback_after_id is not None
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS

    harness._cancel_section_list_scroll_upgrade_fallback()
    assert harness._section_list_scroll_upgrade_fallback_after_id is None
    assert len(harness._after_cancel_calls) == 1


def test_scroll_upgrade_after_perceived_cancels_fallback_and_schedules() -> None:
    harness = _SectionListShellHarness()
    harness._section_list_static_lane = _FakeFrame()
    harness._section_list_scroll_upgrade_fallback_after_id = "fallback-id"

    harness._schedule_section_list_scroll_upgrade_after_perceived()

    assert harness._after_cancel_calls == ["fallback-id"]
    assert harness._section_list_scroll_upgrade_scheduled
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS
    assert harness._after_calls[0][1] == harness._upgrade_section_list_scroll


def test_scroll_upgrade_fallback_timeout_reason() -> None:
    harness = _SectionListShellHarness()

    harness._schedule_section_list_scroll_upgrade(reason="fallback_timeout")

    assert harness._section_list_scroll_upgrade_scheduled
    assert harness._after_calls[0][0] == 0
    assert harness._after_calls[0][1] == harness._upgrade_section_list_scroll


def test_static_lane_real_rows_emit_first_visible_chain() -> None:
    harness = _SectionListShellHarness()
    lane = _FakeFrame()
    harness._section_list_static_lane = lane
    harness._section_dropdown_options_cache = [
        SimpleNamespace(element_id=f"el-{idx}", display_label=f"Row {idx}")
        for idx in range(3)
    ]

    harness._populate_section_list_static_lane()

    assert harness._section_list_static_lane_real_rows
    assert len(harness._create_row_calls) == 3
    assert all(call["static_lane"] for call in harness._create_row_calls)
    assert harness._section_list_first_visible_built
    assert harness._visual_gate_calls
    assert harness._perceived_ready_calls == ["static_lane_first_visible"]
    assert harness._atomic_reveal_calls == ["static_lane_first_visible"]


def test_static_lane_placeholder_does_not_claim_first_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListShellHarness()
    harness._section_list_static_lane = _FakeFrame()
    monkeypatch.setattr(shell_module.ctk, "CTkLabel", lambda *args, **kwargs: _FakeFrame())
    monkeypatch.setattr(shell_module.theme, "get_font", lambda *_args, **_kwargs: object())

    harness._populate_section_list_static_lane()

    assert not harness._section_list_static_lane_real_rows
    assert not harness._section_list_first_visible_built
    assert harness._create_row_calls == []
    assert harness._visual_gate_calls == []
    assert harness._perceived_ready_calls == []
    assert harness._atomic_reveal_calls == []


def test_build_sections_column_composes_shell_then_extras(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListShellHarness()
    calls: list[str] = []

    def _shell(_parent: Any) -> _FakeFrame:
        calls.append("shell")
        return _FakeFrame()

    def _extras(_card: Any) -> None:
        calls.append("extras")

    monkeypatch.setattr(harness, "_build_sections_column_shell", _shell)
    monkeypatch.setattr(harness, "_build_sections_column_extras", _extras)

    harness._build_sections_column(_FakeFrame())

    assert calls == ["shell", "extras"]


def test_extras_skips_missing_slot() -> None:
    harness = _SectionListShellHarness()
    harness._section_list_extras_frame = None

    harness._build_sections_column_extras(_FakeFrame())

    assert not harness._sections_column_extras_built


def test_extras_skips_destroyed_slot() -> None:
    harness = _SectionListShellHarness()
    slot = _FakeFrame()
    slot._exists = False
    harness._section_list_extras_frame = slot

    harness._build_sections_column_extras(_FakeFrame())

    assert not harness._sections_column_extras_built


def test_shell_static_lane_path_sets_extras_before_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListShellHarness()
    parent = _FakeFrame()
    populate_calls = 0
    ready_calls = 0
    fallback_calls = 0

    def _populate() -> None:
        nonlocal populate_calls
        populate_calls += 1

    def _ready() -> None:
        nonlocal ready_calls
        ready_calls += 1

    def _fallback() -> None:
        nonlocal fallback_calls
        fallback_calls += 1

    monkeypatch.setattr(harness, "_populate_section_list_static_lane", _populate)
    monkeypatch.setattr(harness, "_log_section_list_column_ready", _ready)
    monkeypatch.setattr(harness, "_ensure_section_list_scroll_upgrade_fallback", _fallback)
    monkeypatch.setattr(
        shell_module,
        "_make_gf_card",
        lambda _parent, **kwargs: _FakeFrame(),
    )
    monkeypatch.setattr(shell_module.ctk, "CTkFrame", lambda *args, **kwargs: _FakeFrame())

    card = harness._build_sections_column_shell(parent, use_static_lane=True)

    assert card is not None
    assert harness._section_list_extras_frame is not None
    assert harness._section_list_static_lane is not None
    assert populate_calls == 1
    assert ready_calls == 1
    assert fallback_calls == 1
