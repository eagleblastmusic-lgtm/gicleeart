"""Boundary tests for the extracted GICLÉE FRAME top bar subsystem."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_page_draft import (
    ADD_VARIANT_RAM_LABEL,
    CHECK_STRUCTURE_LABEL,
    CLEAR_VARIANT_RAM_LABEL,
    DUPLICATE_VARIANT_LABEL,
    RENAME_VARIANT_LABEL,
    REFRESH_INVENTORY_LABEL,
)
from giclee_app.ui import gicleeframe_view_top_bar as top_bar_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
)
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
)
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import (
    GicleeFrameTopBarMixin,
    _BACK_LABEL,
    _GF_TOP_BAR_ACTIONS_LATE_DEFER_MS,
    _GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS,
    _GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS,
    _GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS,
    _SHELL_STATUS_CHIP,
)
from giclee_app.ui.gicleeframe_view_primitives import _BTN_HEIGHT

ROOT = Path(__file__).resolve().parents[1]
TOP_BAR_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_top_bar.py"

_EXPECTED_METHODS = {
    "_build_context_bar",
    "_build_context_bar_actions_placeholder",
    "_build_context_bar_actions",
    "_schedule_top_bar_actions_late_build",
    "_start_top_bar_actions_late_build",
    "_build_context_bar_actions_late",
    "_build_command_bar_primary_actions_late",
    "_build_command_bar_secondary_actions_late",
    "_build_command_bar",
    "_build_command_bar_primary_actions",
    "_build_command_bar_secondary_actions",
}
_FORBIDDEN_OWNERSHIP = {
    "__init__",
    "on_show",
    "on_hide",
    "set_navigation",
    "_build_shell",
    "_ensure_top_bar_actions_for_atomic_reveal",
    "_add_ram_variant",
    "_duplicate_ram_variant",
    "_rename_ram_variant",
    "_clear_page_draft",
    "_refresh_inventory",
    "_run_structure_dry_run",
    "_try_atomic_reveal",
}


class _FakePackable:
    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        self.master = master
        self.kwargs = dict(kwargs)
        self.pack_kwargs: dict[str, Any] | None = None
        self.children: list[Any] = []

    def pack(self, **kwargs: Any) -> "_FakePackable":
        self.pack_kwargs = dict(kwargs)
        return self

    def pack_propagate(self, _value: bool) -> None:
        return None

    def winfo_children(self) -> list[Any]:
        return list(self.children)

    def destroy(self) -> None:
        return None

    def configure(self, **kwargs: Any) -> None:
        self.kwargs.update(kwargs)


class _FakeSpan:
    def __init__(self, _name: str) -> None:
        pass

    def __enter__(self) -> "_FakeSpan":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _TopBarHarness(GicleeFrameTopBarMixin):
    def __init__(self, *, on_back: Any = None) -> None:
        self._on_back = on_back
        self._context_bar_row = None
        self._context_bar_actions_slot = None
        self._context_bar_actions_placeholder = None
        self._context_bar_back_slot = None
        self._context_bar_back_placeholder = None
        self._command_bar_inner = None
        self._command_bar_primary_slot = None
        self._command_bar_primary_placeholder = None
        self._command_bar_secondary_slot = None
        self._command_bar_secondary_placeholder = None
        self._top_meta_label = None
        self._change_count_label = None
        self._panel_status_label = None
        self._working_variant_menu = None
        self._back_button = None
        self._top_bar_actions_late_started = False
        self._top_bar_actions_late_done = False
        self._after_calls: list[tuple[int, Any]] = []
        self._log_events: list[tuple[str, dict[str, Any]]] = []
        self._suppress_prewarm = False
        self._winfo_exists = True
        self._sync_menu_called = False
        self._atomic_reveal_trigger: str | None = None
        self._ram_calls: list[str] = []
        self._refresh_called = False
        self._dry_run_called = False

    def after(self, delay_ms: int, callback: Any) -> None:
        self._after_calls.append((delay_ms, callback))

    def winfo_exists(self) -> bool:
        return self._winfo_exists

    def _should_suppress_visible_prewarm(self) -> bool:
        return self._suppress_prewarm

    def _log_visible_prewarm_suppressed(self, *, job: str) -> None:
        self._log_events.append(("suppressed", {"job": job}))

    def _on_working_variant_selected(self, _value: str) -> None:
        return None

    def _handle_back(self) -> None:
        return None

    def _add_ram_variant(self) -> None:
        self._ram_calls.append("add")

    def _duplicate_ram_variant(self) -> None:
        self._ram_calls.append("duplicate")

    def _rename_ram_variant(self) -> None:
        self._ram_calls.append("rename")

    def _clear_page_draft(self) -> None:
        self._ram_calls.append("clear")

    def _refresh_inventory(self, *, warn_if_draft: bool) -> None:
        self._refresh_called = warn_if_draft

    def _run_structure_dry_run(self) -> None:
        self._dry_run_called = True

    def _sync_working_variant_menu(self) -> None:
        self._sync_menu_called = True

    def _schedule_atomic_reveal_check(self, *, trigger: str) -> None:
        self._atomic_reveal_trigger = trigger


def test_top_bar_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameTopBarMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameTopBarMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameTopBarMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }
    assert not (_FORBIDDEN_OWNERSHIP & set(GicleeFrameTopBarMixin.__dict__))


def test_top_bar_module_has_no_write_network_or_reverse_host_import() -> None:
    source = TOP_BAR_PATH.read_text(encoding="utf-8")
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
    ):
        assert forbidden_text not in source.lower()
    assert "after(" in source


def test_top_bar_public_boundary_contract() -> None:
    assert top_bar_module.__all__ == (
        "GicleeFrameTopBarMixin",
        "_BACK_LABEL",
        "_SHELL_STATUS_CHIP",
        "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS",
        "_GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS",
        "_GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS",
        "_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS",
    )
    assert _BACK_LABEL == "Wróć do huba"
    assert _SHELL_STATUS_CHIP == "RAM-only · bez zapisu"
    assert _BTN_HEIGHT == 28
    assert 0 <= _GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS < _GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS
    assert _GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS < _GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS
    assert _GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS <= _GF_TOP_BAR_ACTIONS_LATE_DEFER_MS


def test_top_bar_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
    assert GicleeFrameBrandPanelMixin in GicleeFrameView.__mro__
    assert GicleeFramePageReadinessMixin in GicleeFrameView.__mro__
    assert GicleeFrameStructureDryRunMixin in GicleeFrameView.__mro__
    assert GicleeFrameSafetyCardMixin in GicleeFrameView.__mro__
    assert GicleeFrameReadinessRowMixin in GicleeFrameView.__mro__
    assert GicleeFrameTopBarMixin in GicleeFrameView.__mro__
    assert GicleeFrameRamVariantMixin in GicleeFrameView.__mro__
    assert GicleeFrameSectionListShellMixin in GicleeFrameView.__mro__
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(GicleeFrameTopBarMixin, name)


def test_host_ownership_for_shell_and_adapters() -> None:
    for name in (
        "_build_shell",
        "_ensure_top_bar_actions_for_atomic_reveal",
        "set_navigation",
        "_handle_back",
        "_apply_edit_to_draft",
        "_refresh_inventory",
        "_schedule_atomic_reveal_check",
        "_try_atomic_reveal",
        "_should_suppress_visible_prewarm",
        "_log_visible_prewarm_suppressed",
    ):
        assert name in GicleeFrameView.__dict__


def test_context_bar_placeholder_uses_btn_height_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(top_bar_module.ctk, "CTkFrame", _FakePackable)
    monkeypatch.setattr(top_bar_module, "log_event", lambda *_a, **_k: None)

    harness = _TopBarHarness()
    harness._build_context_bar_actions_placeholder(_FakePackable())

    placeholder = harness._context_bar_actions_placeholder
    assert placeholder is not None
    assert placeholder.kwargs["width"] == 168
    assert placeholder.kwargs["height"] == _BTN_HEIGHT


def test_context_bar_back_placeholder_only_when_on_back_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(top_bar_module.ctk, "CTkFrame", _FakePackable)
    monkeypatch.setattr(top_bar_module, "log_event", lambda *_a, **_k: None)

    without_back = _TopBarHarness(on_back=None)
    without_back._build_context_bar_actions_placeholder(_FakePackable())
    assert without_back._context_bar_back_slot is None

    with_back = _TopBarHarness(on_back=object())
    with_back._build_context_bar_actions_placeholder(_FakePackable())
    assert with_back._context_bar_back_slot is not None
    assert with_back._context_bar_back_slot.kwargs["width"] == 112
    assert with_back._context_bar_back_slot.kwargs["height"] == _BTN_HEIGHT


def test_command_bar_slot_placeholders_and_captions(monkeypatch: pytest.MonkeyPatch) -> None:
    captions: list[str] = []
    buttons: list[tuple[str, Any]] = []

    def _card(_master: Any, **kwargs: Any) -> _FakePackable:
        return _FakePackable(**kwargs)

    def _caption(_master: Any, text: str) -> _FakePackable:
        captions.append(text)
        return _FakePackable()

    def _secondary(_master: Any, label: str, cmd: Any, **kwargs: Any) -> _FakePackable:
        buttons.append((label, cmd))
        return _FakePackable()

    monkeypatch.setattr(top_bar_module, "_make_gf_card", _card)
    monkeypatch.setattr(top_bar_module.ctk, "CTkFrame", _FakePackable)
    monkeypatch.setattr(top_bar_module, "_make_section_caption", _caption)
    monkeypatch.setattr(top_bar_module, "_make_secondary_button", _secondary)
    monkeypatch.setattr(top_bar_module, "span", _FakeSpan)
    monkeypatch.setattr(top_bar_module, "log_event", lambda *_a, **_k: None)

    harness = _TopBarHarness()
    harness._build_command_bar(_FakePackable())

    assert harness._command_bar_primary_placeholder is not None
    assert harness._command_bar_primary_placeholder.kwargs["height"] == 56
    assert harness._command_bar_secondary_placeholder is not None
    assert harness._command_bar_secondary_placeholder.kwargs["height"] == 56

    inner = harness._command_bar_inner
    assert inner is not None
    harness._build_command_bar_primary_actions(inner)
    harness._build_command_bar_secondary_actions(inner)

    assert captions == ["Warianty RAM", "Inventory i kontrola"]
    assert [label for label, _cmd in buttons] == [
        ADD_VARIANT_RAM_LABEL,
        DUPLICATE_VARIANT_LABEL,
        RENAME_VARIANT_LABEL,
        CLEAR_VARIANT_RAM_LABEL,
        REFRESH_INVENTORY_LABEL,
        CHECK_STRUCTURE_LABEL,
    ]

    inner_h = _TopBarHarness()
    inner_buttons: list[tuple[str, Any]] = []

    def _secondary_inner(_master: Any, label: str, cmd: Any, **kwargs: Any) -> _FakePackable:
        inner_buttons.append((label, cmd))
        return _FakePackable()

    monkeypatch.setattr(top_bar_module, "_make_secondary_button", _secondary_inner)
    inner_h._command_bar_primary_slot = _FakePackable()
    inner_h._command_bar_secondary_slot = _FakePackable()
    inner_h._build_command_bar_primary_actions(_FakePackable())
    inner_h._build_command_bar_secondary_actions(_FakePackable())
    for _label, cmd in inner_buttons:
        cmd()
    assert inner_h._ram_calls == ["add", "duplicate", "rename", "clear"]
    assert inner_h._refresh_called is True
    assert inner_h._dry_run_called is True


def test_schedule_top_bar_actions_late_build_staggered_order(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(top_bar_module, "log_event", lambda name, **_kwargs: events.append(name))

    harness = _TopBarHarness()
    harness._schedule_top_bar_actions_late_build()
    assert harness._top_bar_actions_late_started is True
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_TOP_BAR_ACTIONS_LATE_DEFER_MS

    harness._after_calls.clear()
    events.clear()
    harness._start_top_bar_actions_late_build()
    assert events == ["studio.gicleeframe.top_bar.actions_late_start"]
    assert [delay for delay, _cb in harness._after_calls] == [
        _GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS,
        _GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS,
        _GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS,
    ]


def test_secondary_lane_sets_done_syncs_menu_and_triggers_atomic_reveal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    monkeypatch.setattr(top_bar_module, "span", _FakeSpan)
    monkeypatch.setattr(
        top_bar_module,
        "log_event",
        lambda name, **_kwargs: events.append(name),
    )
    monkeypatch.setattr(top_bar_module.ctk, "CTkFrame", _FakePackable)
    monkeypatch.setattr(top_bar_module, "_make_section_caption", lambda *_a, **_k: _FakePackable())
    monkeypatch.setattr(
        top_bar_module,
        "_make_secondary_button",
        lambda *_a, **_k: _FakePackable(),
    )

    harness = _TopBarHarness()
    harness._command_bar_inner = _FakePackable()
    harness._command_bar_primary_slot = _FakePackable()
    harness._command_bar_secondary_slot = _FakePackable()
    harness._build_command_bar_secondary_actions_late()

    assert harness._top_bar_actions_late_done is True
    assert harness._sync_menu_called is True
    assert harness._atomic_reveal_trigger == "top_bar_actions"
    assert "studio.gicleeframe.top_bar.secondary_actions_late_done" in events
    assert "studio.gicleeframe.top_bar.actions_late_done" in events
    secondary_idx = events.index("studio.gicleeframe.top_bar.secondary_actions_late_done")
    done_idx = events.index("studio.gicleeframe.top_bar.actions_late_done")
    assert secondary_idx < done_idx


def test_late_lanes_honor_suppression_and_winfo_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(top_bar_module, "span", _FakeSpan)
    monkeypatch.setattr(top_bar_module, "log_event", lambda *_a, **_k: None)

    suppressed = _TopBarHarness()
    suppressed._suppress_prewarm = True
    suppressed._build_context_bar_actions_late()
    suppressed._build_command_bar_primary_actions_late()
    suppressed._build_command_bar_secondary_actions_late()
    assert suppressed._top_bar_actions_late_done is False
    assert suppressed._log_events == [
        ("suppressed", {"job": "top_bar.context_actions_late"}),
        ("suppressed", {"job": "top_bar.primary_actions_late"}),
        ("suppressed", {"job": "top_bar.secondary_actions_late"}),
    ]

    destroyed = _TopBarHarness()
    destroyed._winfo_exists = False
    destroyed._build_context_bar_actions_late()
    assert destroyed._top_bar_actions_late_done is False
