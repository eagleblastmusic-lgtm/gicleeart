"""Boundary tests for the extracted GICLÉE FRAME F2 safety card."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui import gicleeframe_view_safety as safety_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
)
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import (
    GicleeFrameSafetyCardMixin,
    _SAFETY_CHECKLIST,
    _SAFETY_ROW_WRAPLENGTH,
    _SAFETY_TITLE,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
)
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)

ROOT = Path(__file__).resolve().parents[1]
SAFETY_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_safety.py"

_EXPECTED_METHODS = {"_build_safety_card"}
_EXPECTED_CHECKLIST = (
    ("RAM-only", "Zmiany tylko w pamięci sesji"),
    ("Brak zapisu motywu", "Panel nie zapisuje plików motywu"),
    ("Sync/deploy zablokowane", "Synchronizacja i wdrożenie wyłączone"),
    ("F3/F4 osobna decyzja", "Lokalny zapis i writer — po akceptacji"),
)
_FORBIDDEN_OWNERSHIP = {
    "__init__",
    "on_show",
    "on_hide",
    "set_navigation",
    "_build_control_column",
    "_build_control_structure_card",
    "_build_control_readiness_card",
    "_refresh_inventory",
    "_select_element",
    "_schedule_selection_populate",
    "_try_atomic_reveal",
    "_populate_editor",
}


class _FakePackable:
    def __init__(self) -> None:
        self.pack_calls: list[dict[str, object]] = []

    def pack(self, **kwargs: object) -> None:
        self.pack_calls.append(kwargs)


class _FakeLabel(_FakePackable):
    def __init__(self, parent: object, **kwargs: object) -> None:
        super().__init__()
        self.parent = parent
        self.kwargs = kwargs


def test_safety_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameSafetyCardMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameSafetyCardMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameSafetyCardMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }
    assert not (_FORBIDDEN_OWNERSHIP & set(GicleeFrameSafetyCardMixin.__dict__))


def test_safety_module_has_no_write_network_or_scheduler_ownership() -> None:
    source = SAFETY_PATH.read_text(encoding="utf-8")
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
        "after(",
        "after_idle(",
        "after_cancel(",
    ):
        assert forbidden_text not in source.lower()


def test_safety_public_boundary_contract() -> None:
    assert safety_module.__all__ == (
        "GicleeFrameSafetyCardMixin",
        "_SAFETY_TITLE",
        "_SAFETY_CHECKLIST",
        "_SAFETY_ROW_WRAPLENGTH",
    )
    assert _SAFETY_TITLE == "Bezpieczeństwo"
    assert _SAFETY_CHECKLIST == _EXPECTED_CHECKLIST
    assert _SAFETY_ROW_WRAPLENGTH == 276


def test_safety_card_preserves_layout_copy_and_row_order(monkeypatch) -> None:
    parent = object()
    card = _FakePackable()
    title_widget = _FakePackable()
    labels: list[_FakeLabel] = []
    card_calls: list[tuple[object, dict[str, object]]] = []
    title_calls: list[tuple[object, str]] = []
    row_calls: list[tuple[object, str, str, int]] = []

    def _fake_card(master: object, **kwargs: object) -> _FakePackable:
        card_calls.append((master, kwargs))
        return card

    def _fake_title(master: object, title: str) -> _FakePackable:
        title_calls.append((master, title))
        return title_widget

    def _fake_row(
        master: object,
        title: str,
        detail: str,
        *,
        wraplength: int,
    ) -> None:
        row_calls.append((master, title, detail, wraplength))

    def _fake_label(master: object, **kwargs: object) -> _FakeLabel:
        label = _FakeLabel(master, **kwargs)
        labels.append(label)
        return label

    monkeypatch.setattr(safety_module, "_make_gf_card", _fake_card)
    monkeypatch.setattr(safety_module, "_make_card_title", _fake_title)
    monkeypatch.setattr(safety_module, "_build_safety_row", _fake_row)
    monkeypatch.setattr(safety_module.ctk, "CTkLabel", _fake_label)

    GicleeFrameSafetyCardMixin()._build_safety_card(parent)

    assert card_calls == [(parent, {"variant": "panel_deep", "radius": 16})]
    assert card.pack_calls == [{"fill": "x"}]
    assert title_calls == [(card, _SAFETY_TITLE)]
    assert title_widget.pack_calls == [
        {"fill": "x", "padx": safety_module._CARD_PAD_X, "pady": (12, 8)}
    ]
    assert row_calls == [
        (card, title, detail, _SAFETY_ROW_WRAPLENGTH)
        for title, detail in _EXPECTED_CHECKLIST
    ]
    assert len(labels) == 1
    assert labels[0].parent is card
    assert labels[0].kwargs == {"text": "", "height": 4}
    assert labels[0].pack_calls == [{}]


def test_safety_mixin_is_wired_into_gicleeframe_view_mro() -> None:
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
    assert "_build_safety_card" not in GicleeFrameView.__dict__
    assert (
        GicleeFrameView._build_safety_card
        is GicleeFrameSafetyCardMixin._build_safety_card
    )
    assert "_build_control_column" in GicleeFrameView.__dict__
