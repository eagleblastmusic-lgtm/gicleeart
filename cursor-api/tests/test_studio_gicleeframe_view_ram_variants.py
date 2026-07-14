"""Boundary tests for the extracted GICLÉE FRAME RAM variant workflow subsystem."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_page_draft import (
    GicleeFramePageDraft,
    PAGE_SOURCE_FILE,
    RAM_ONLY_STATUS,
    RENAME_VARIANT_LABEL,
    VARIANT_ENV_DEV,
    working_variant_menu_label,
)
from giclee_app.ui import gicleeframe_view_ram_variants as ram_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
)
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
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin

ROOT = Path(__file__).resolve().parents[1]
RAM_VARIANTS_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_ram_variants.py"

_EXPECTED_METHODS = {
    "_sync_working_variant_menu",
    "_on_working_variant_selected",
    "_update_top_bar",
    "_add_ram_variant",
    "_duplicate_ram_variant",
    "_rename_ram_variant",
    "_clear_page_draft",
}

_FORBIDDEN_OWNERSHIP = {
    "__init__",
    "on_show",
    "on_hide",
    "set_navigation",
    "_build_shell",
    "_refresh_inventory",
    "_refresh_inventory_light",
    "_apply_edit_to_draft",
    "_render_section_menu",
    "_populate_editor",
    "_reset_structure_dry_run_display",
    "_schedule_atomic_reveal_check",
    "_try_atomic_reveal",
}

_HOST_OWNERSHIP = {
    "_build_shell",
    "_ensure_top_bar_actions_for_atomic_reveal",
    "_apply_edit_to_draft",
    "_refresh_inventory",
    "_schedule_atomic_reveal_check",
    "_try_atomic_reveal",
}


class _FakeMenu:
    def __init__(self) -> None:
        self.values: list[str] = []
        self.active: str | None = None
        self.configure_calls: list[dict[str, Any]] = []

    def configure(self, **kwargs: Any) -> None:
        self.configure_calls.append(dict(kwargs))
        if "values" in kwargs:
            self.values = list(kwargs["values"])

    def set(self, value: str) -> None:
        self.active = value


class _FakeLabel:
    def __init__(self) -> None:
        self.text: str | None = None

    def configure(self, **kwargs: Any) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])


class _RamVariantHarness(GicleeFrameRamVariantMixin):
    def __init__(self) -> None:
        self._page_draft = GicleeFramePageDraft()
        self._inventory: Any = None
        self._merged: list[Any] = []
        self._merged_by_id: dict[str, Any] = {}
        self._selected_id: str | None = None
        self._working_variant_menu: _FakeMenu | None = None
        self._working_variant_map: dict[str, str] = {}
        self._top_meta_label: _FakeLabel | None = None
        self._change_count_label: _FakeLabel | None = None
        self._structure_dry_label: object | None = None
        self._on_status: Any = None
        self._set_merged_calls: list[Any] = []
        self._render_section_menu_calls = 0
        self._populate_editor_calls: list[Any] = []
        self._reset_structure_calls = 0
        self._refresh_calls: list[bool] = []

    def _set_merged(self, merged: Any) -> None:
        self._set_merged_calls.append(merged)
        if isinstance(merged, list):
            self._merged = merged
            self._merged_by_id = {
                getattr(item, "element_id", ""): item for item in merged
            }

    def _render_section_menu(self) -> None:
        self._render_section_menu_calls += 1

    def _populate_editor(self, merged: Any) -> None:
        self._populate_editor_calls.append(merged)

    def _reset_structure_dry_run_display(self) -> None:
        self._reset_structure_calls += 1

    def _refresh_inventory(self, *, warn_if_draft: bool) -> None:
        self._refresh_calls.append(warn_if_draft)


def _inventory(*, variant_id: str = "gf1", live_variant_id: str = "gf1") -> SimpleNamespace:
    return SimpleNamespace(
        variant_id=variant_id,
        live_variant_id=live_variant_id,
        elements=[],
    )


def test_ram_variant_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameRamVariantMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameRamVariantMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameRamVariantMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }
    assert not (_FORBIDDEN_OWNERSHIP & set(GicleeFrameRamVariantMixin.__dict__))


def test_ram_variant_module_has_no_write_network_scheduler_or_reverse_host_import() -> None:
    source = RAM_VARIANTS_PATH.read_text(encoding="utf-8")
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
        "after(",
        "after_idle(",
        "after_cancel(",
    ):
        assert forbidden_text not in source.lower()


def test_ram_variant_public_boundary_contract() -> None:
    assert ram_module.__all__ == ("GicleeFrameRamVariantMixin",)


def test_ram_variant_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
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
        assert getattr(GicleeFrameView, name) is getattr(GicleeFrameRamVariantMixin, name)


def test_host_ownership_for_shell_and_adapters() -> None:
    for name in _HOST_OWNERSHIP:
        assert name in GicleeFrameView.__dict__


def test_sync_working_variant_menu_noop_without_widget() -> None:
    harness = _RamVariantHarness()
    harness._working_variant_menu = None
    harness._working_variant_map = {"old": "v1"}

    harness._sync_working_variant_menu()

    assert harness._working_variant_map == {"old": "v1"}


def test_sync_working_variant_menu_rebuilds_map_and_selects_active_label() -> None:
    harness = _RamVariantHarness()
    menu = _FakeMenu()
    harness._working_variant_menu = menu
    second = harness._page_draft.add_variant(name="Wariant 2")
    harness._page_draft.switch_variant(second.variant_id)

    harness._sync_working_variant_menu()

    active_label = working_variant_menu_label(harness._page_draft.active_variant())
    assert menu.values == [
        working_variant_menu_label(v)
        for v in harness._page_draft.variants.values()
    ]
    assert harness._working_variant_map[active_label] == second.variant_id
    assert menu.active == active_label


def test_sync_working_variant_menu_falls_back_to_first_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from giclee_app.studio.gicleeframe_page_draft import (
        working_variant_menu_label as real_label,
    )

    harness = _RamVariantHarness()
    menu = _FakeMenu()
    harness._working_variant_menu = menu
    harness._page_draft.add_variant(name="Wariant 2")
    harness._sync_working_variant_menu()
    first_label = menu.values[0]
    pair_count = len(harness._page_draft.variant_names())
    call_count = 0

    def _orphan_active_label(variant: Any) -> str:
        nonlocal call_count
        call_count += 1
        if call_count > pair_count:
            return "orphan label"
        return real_label(variant)

    monkeypatch.setattr(ram_module, "working_variant_menu_label", _orphan_active_label)

    harness._sync_working_variant_menu()

    assert menu.active == first_label


def test_on_working_variant_selected_noop_for_unknown_label() -> None:
    harness = _RamVariantHarness()
    harness._working_variant_menu = _FakeMenu()
    status_calls: list[str] = []
    harness._on_status = status_calls.append
    harness._sync_working_variant_menu()
    before = harness._page_draft.active_variant_id

    harness._on_working_variant_selected("unknown label")

    assert harness._page_draft.active_variant_id == before
    assert harness._render_section_menu_calls == 0
    assert harness._set_merged_calls == []


def test_on_working_variant_selected_preserves_existing_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _RamVariantHarness()
    harness._inventory = _inventory()
    harness._working_variant_menu = _FakeMenu()
    harness._sync_working_variant_menu()
    merged = SimpleNamespace(element_id="el-1")
    harness._merged_by_id = {"el-1": merged}
    harness._selected_id = "el-1"
    status_calls: list[str] = []
    harness._on_status = status_calls.append
    target_label = next(iter(harness._working_variant_map))
    monkeypatch.setattr(
        ram_module,
        "merge_inventory_with_draft",
        lambda _inv, _draft: [merged],
    )

    harness._on_working_variant_selected(target_label)

    assert harness._render_section_menu_calls == 1
    assert harness._populate_editor_calls == [merged]
    assert harness._selected_id == "el-1"
    assert status_calls == [
        f"Wariant roboczy: {harness._page_draft.draft_name} · {RAM_ONLY_STATUS}"
    ]


def test_on_working_variant_selected_clears_missing_selection() -> None:
    harness = _RamVariantHarness()
    harness._inventory = _inventory()
    harness._working_variant_menu = _FakeMenu()
    harness._sync_working_variant_menu()
    harness._selected_id = "missing"
    harness._merged_by_id = {}

    harness._on_working_variant_selected(next(iter(harness._working_variant_map)))

    assert harness._selected_id is None
    assert harness._populate_editor_calls == []


def test_on_working_variant_selected_skips_inventory_merge_when_missing() -> None:
    harness = _RamVariantHarness()
    harness._inventory = None
    harness._working_variant_menu = _FakeMenu()
    harness._sync_working_variant_menu()

    harness._on_working_variant_selected(next(iter(harness._working_variant_map)))

    assert harness._set_merged_calls == []


def test_update_top_bar_sets_source_metadata_and_change_count() -> None:
    harness = _RamVariantHarness()
    harness._inventory = _inventory(variant_id="gf1", live_variant_id="gf1")
    harness._top_meta_label = _FakeLabel()
    harness._change_count_label = _FakeLabel()
    harness._working_variant_menu = _FakeMenu()
    harness._page_draft.set_patch("el-1", visible=False)

    harness._update_top_bar()

    assert harness._top_meta_label.text == (
        f"gf1 ({VARIANT_ENV_DEV}) · {PAGE_SOURCE_FILE}"
    )
    assert harness._change_count_label.text == f"Zmiany: {harness._page_draft.draft_edit_count()}"


def test_update_top_bar_without_inventory_uses_dash_source() -> None:
    harness = _RamVariantHarness()
    harness._inventory = None
    harness._top_meta_label = _FakeLabel()
    harness._working_variant_menu = _FakeMenu()

    harness._update_top_bar()

    assert harness._top_meta_label.text == f"— · {PAGE_SOURCE_FILE}"


def test_add_ram_variant_resets_selection_and_refreshes_inventory() -> None:
    harness = _RamVariantHarness()
    harness._selected_id = "el-1"
    harness._structure_dry_label = object()
    status_calls: list[str] = []
    harness._on_status = status_calls.append
    before_count = len(harness._page_draft.variants)

    harness._add_ram_variant()

    assert len(harness._page_draft.variants) == before_count + 1
    assert harness._selected_id is None
    assert harness._reset_structure_calls == 1
    assert harness._refresh_calls == [False]
    assert status_calls == [
        f"Dodano wariant RAM: {harness._page_draft.draft_name} · nic nie zapisano"
    ]


def test_duplicate_ram_variant_merges_updates_top_bar_and_renders_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _RamVariantHarness()
    harness._inventory = _inventory()
    harness._top_meta_label = _FakeLabel()
    harness._change_count_label = _FakeLabel()
    harness._working_variant_menu = _FakeMenu()
    harness._selected_id = "el-1"
    status_calls: list[str] = []
    harness._on_status = status_calls.append
    merge_calls: list[tuple[Any, Any]] = []

    def _merge(inv: Any, draft: Any) -> list[Any]:
        merge_calls.append((inv, draft))
        return []

    monkeypatch.setattr(ram_module, "merge_inventory_with_draft", _merge)

    harness._duplicate_ram_variant()

    assert harness._selected_id is None
    assert len(merge_calls) == 1
    assert merge_calls[0][0] is harness._inventory
    assert merge_calls[0][1] is harness._page_draft
    assert harness._render_section_menu_calls == 1
    assert harness._refresh_calls == []
    assert status_calls == [
        f"Zduplikowano wariant: {harness._page_draft.draft_name} · nic nie zapisano"
    ]


def test_rename_ram_variant_applies_trimmed_name_and_updates_top_bar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _RamVariantHarness()
    harness._top_meta_label = _FakeLabel()
    harness._change_count_label = _FakeLabel()
    harness._working_variant_menu = _FakeMenu()
    status_calls: list[str] = []
    harness._on_status = status_calls.append

    class _FakeDialog:
        def __init__(self, *, text: str, title: str) -> None:
            assert text == "Nowa nazwa wariantu roboczego (tylko pamięć):"
            assert title == RENAME_VARIANT_LABEL

        def get_input(self) -> str:
            return "  Nowa nazwa  "

    monkeypatch.setattr(ram_module.ctk, "CTkInputDialog", _FakeDialog)

    harness._rename_ram_variant()

    assert harness._page_draft.draft_name == "Nowa nazwa"
    assert harness._refresh_calls == []
    assert harness._render_section_menu_calls == 0
    assert status_calls == ["Zmieniono nazwę wariantu: Nowa nazwa"]


@pytest.mark.parametrize("dialog_value", [None, "", "   "])
def test_rename_ram_variant_noop_for_cancel_blank_or_whitespace(
    monkeypatch: pytest.MonkeyPatch,
    dialog_value: str | None,
) -> None:
    harness = _RamVariantHarness()
    before_name = harness._page_draft.draft_name
    status_calls: list[str] = []
    harness._on_status = status_calls.append

    class _FakeDialog:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def get_input(self) -> str | None:
            return dialog_value

    monkeypatch.setattr(ram_module.ctk, "CTkInputDialog", _FakeDialog)

    harness._rename_ram_variant()

    assert harness._page_draft.draft_name == before_name
    assert status_calls == []


def test_clear_page_draft_resets_selection_and_refreshes_inventory() -> None:
    harness = _RamVariantHarness()
    harness._selected_id = "el-1"
    harness._structure_dry_label = object()
    harness._page_draft.set_patch("el-1", visible=False)
    status_calls: list[str] = []
    harness._on_status = status_calls.append

    harness._clear_page_draft()

    assert harness._page_draft.draft_edit_count() == 0
    assert harness._selected_id is None
    assert harness._reset_structure_calls == 1
    assert harness._refresh_calls == [False]
    assert status_calls == [
        f"Wyczyszczono wariant RAM: {harness._page_draft.draft_name} · nic nie zapisano"
    ]
