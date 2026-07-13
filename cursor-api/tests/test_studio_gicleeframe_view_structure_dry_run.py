"""Boundary tests for the extracted GICLÉE FRAME F2 structure dry-run panel."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_page_draft import STRUCTURE_EMPTY_STATE
from giclee_app.ui import gicleeframe_view_structure_dry_run as structure_module
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
    _STRUCTURE_DRY_RUN_WRAPLENGTH,
)

ROOT = Path(__file__).resolve().parents[1]
STRUCTURE_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_structure_dry_run.py"
)

_EXPECTED_METHODS = {
    "_build_control_structure_card",
    "_reset_structure_dry_run_display",
    "_run_structure_dry_run",
}

_FORBIDDEN_OWNERSHIP = {
    "__init__",
    "on_show",
    "on_hide",
    "set_navigation",
    "_build_control_column",
    "_build_safety_card",
    "_refresh_inventory",
    "_fill_page_readiness",
    "_select_element",
    "_schedule_selection_populate",
    "_try_atomic_reveal",
    "_populate_editor",
}


class _FakeLabel:
    def __init__(self) -> None:
        self.configured: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.configured.update(kwargs)


def test_structure_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameStructureDryRunMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameStructureDryRunMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameStructureDryRunMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }
    assert not (_FORBIDDEN_OWNERSHIP & set(GicleeFrameStructureDryRunMixin.__dict__))


def test_structure_module_has_no_write_network_or_scheduler_ownership() -> None:
    source = STRUCTURE_PATH.read_text(encoding="utf-8")
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


def test_structure_public_boundary_contract() -> None:
    assert structure_module.__all__ == (
        "GicleeFrameStructureDryRunMixin",
        "_STRUCTURE_DRY_RUN_WRAPLENGTH",
    )
    assert _STRUCTURE_DRY_RUN_WRAPLENGTH == 292


def test_structure_reset_preserves_empty_state_and_muted_color() -> None:
    mixin = GicleeFrameStructureDryRunMixin()
    label = _FakeLabel()
    mixin._structure_dry_label = label

    mixin._reset_structure_dry_run_display()

    assert label.configured == {
        "text": STRUCTURE_EMPTY_STATE,
        "text_color": structure_module.theme.TextMuted,
    }


def test_structure_dry_run_preserves_pipeline_and_status(monkeypatch) -> None:
    mixin = GicleeFrameStructureDryRunMixin()
    inventory = object()
    draft = object()
    dry = SimpleNamespace(status_badge="dry-run gotowy")
    ready = object()
    label = _FakeLabel()
    readiness_calls: list[object] = []
    status_calls: list[str] = []
    refresh_calls: list[bool] = []

    mixin._inventory = inventory
    mixin._page_draft = draft
    mixin._structure_dry_label = label
    mixin._fill_page_readiness = readiness_calls.append
    mixin._on_status = status_calls.append
    mixin._refresh_inventory = lambda *, warn_if_draft: refresh_calls.append(
        warn_if_draft
    )

    monkeypatch.setattr(
        structure_module,
        "build_page_structure_dry_run",
        lambda inv, page_draft: dry
        if (inv is inventory and page_draft is draft)
        else None,
    )
    monkeypatch.setattr(
        structure_module,
        "evaluate_gicleeframe_page_readiness",
        lambda inv, result: ready
        if (inv is inventory and result is dry)
        else None,
    )
    monkeypatch.setattr(
        structure_module,
        "format_structure_dry_run_summary",
        lambda result: "structure" if result is dry else "unexpected",
    )
    monkeypatch.setattr(
        structure_module,
        "format_page_readiness_block",
        lambda result: "readiness" if result is ready else "unexpected",
    )

    mixin._run_structure_dry_run()

    assert refresh_calls == []
    assert label.configured == {
        "text": "structure\n\nreadiness",
        "text_color": structure_module.theme.TextPrimary,
    }
    assert readiness_calls == [ready]
    assert status_calls == ["dry-run gotowy"]


def test_structure_dry_run_refreshes_only_when_inventory_is_missing(
    monkeypatch,
) -> None:
    mixin = GicleeFrameStructureDryRunMixin()
    inventory = object()
    draft = object()
    dry = SimpleNamespace(status_badge="ok")
    ready = object()
    refresh_calls: list[bool] = []

    mixin._inventory = None
    mixin._page_draft = draft
    mixin._structure_dry_label = None
    mixin._fill_page_readiness = lambda _ready: None
    mixin._on_status = None

    def _refresh(*, warn_if_draft: bool) -> None:
        refresh_calls.append(warn_if_draft)
        mixin._inventory = inventory

    mixin._refresh_inventory = _refresh
    monkeypatch.setattr(
        structure_module,
        "build_page_structure_dry_run",
        lambda inv, page_draft: dry,
    )
    monkeypatch.setattr(
        structure_module,
        "evaluate_gicleeframe_page_readiness",
        lambda inv, result: ready,
    )
    monkeypatch.setattr(
        structure_module,
        "format_structure_dry_run_summary",
        lambda result: "structure",
    )
    monkeypatch.setattr(
        structure_module,
        "format_page_readiness_block",
        lambda result: "readiness",
    )

    mixin._run_structure_dry_run()

    assert refresh_calls == [False]


def test_structure_dry_run_stops_when_refresh_still_has_no_inventory(
    monkeypatch,
) -> None:
    mixin = GicleeFrameStructureDryRunMixin()
    mixin._inventory = None
    mixin._page_draft = object()
    mixin._structure_dry_label = None
    mixin._fill_page_readiness = lambda _ready: None
    mixin._on_status = None
    mixin._refresh_inventory = lambda *, warn_if_draft: None

    called = False

    def _unexpected_build(inv, draft):
        nonlocal called
        called = True
        return object()

    monkeypatch.setattr(
        structure_module,
        "build_page_structure_dry_run",
        _unexpected_build,
    )

    mixin._run_structure_dry_run()

    assert called is False
