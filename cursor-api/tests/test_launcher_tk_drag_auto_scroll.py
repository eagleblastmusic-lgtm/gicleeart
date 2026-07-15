"""Testy LC-3I: pionowy auto-scroll Tk podczas drag-and-drop."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from giclee_app import launcher_tk_drag_auto_scroll as auto_scroll


class FakeCanvas:
    def __init__(
        self,
        *,
        top: int = 100,
        height: int = 200,
        fail_rooty: bool = False,
        fail_height: bool = False,
        fail_scroll: bool = False,
    ) -> None:
        self.top = top
        self.height = height
        self.fail_rooty = fail_rooty
        self.fail_height = fail_height
        self.fail_scroll = fail_scroll
        self.calls: list[tuple[object, ...]] = []

    def winfo_rooty(self) -> int:
        self.calls.append(("rooty",))
        if self.fail_rooty:
            raise auto_scroll.tk.TclError("rooty failed")
        return self.top

    def winfo_height(self) -> int:
        self.calls.append(("height",))
        if self.fail_height:
            raise auto_scroll.tk.TclError("height failed")
        return self.height

    def yview_scroll(self, amount: int, unit: str) -> None:
        self.calls.append(("scroll", amount, unit))
        if self.fail_scroll:
            raise auto_scroll.tk.TclError("scroll failed")


def _scroll_calls(canvas: FakeCanvas) -> list[tuple[object, ...]]:
    return [call for call in canvas.calls if call[0] == "scroll"]


def test_default_margin_is_exactly_42_px() -> None:
    assert auto_scroll.DRAG_AUTO_SCROLL_MARGIN_PX == 42


def test_upper_zone_scrolls_one_unit_up() -> None:
    canvas = FakeCanvas(top=100, height=200)
    auto_scroll.auto_scroll_drag(canvas, 141)  # type: ignore[arg-type]
    assert canvas.calls == [("rooty",), ("height",), ("scroll", -1, "units")]


def test_exact_upper_boundary_does_not_scroll() -> None:
    canvas = FakeCanvas(top=100, height=200)
    auto_scroll.auto_scroll_drag(canvas, 142)  # type: ignore[arg-type]
    assert _scroll_calls(canvas) == []


def test_lower_zone_scrolls_one_unit_down() -> None:
    canvas = FakeCanvas(top=100, height=200)
    auto_scroll.auto_scroll_drag(canvas, 259)  # type: ignore[arg-type]
    assert canvas.calls == [("rooty",), ("height",), ("scroll", 1, "units")]


def test_exact_lower_boundary_does_not_scroll() -> None:
    canvas = FakeCanvas(top=100, height=200)
    auto_scroll.auto_scroll_drag(canvas, 258)  # type: ignore[arg-type]
    assert _scroll_calls(canvas) == []


def test_middle_zone_does_not_scroll() -> None:
    canvas = FakeCanvas(top=100, height=200)
    auto_scroll.auto_scroll_drag(canvas, 200)  # type: ignore[arg-type]
    assert canvas.calls == [("rooty",), ("height",)]


def test_geometry_is_read_rooty_before_height() -> None:
    canvas = FakeCanvas()
    auto_scroll.auto_scroll_drag(canvas, 200)  # type: ignore[arg-type]
    assert canvas.calls[:2] == [("rooty",), ("height",)]


def test_rooty_tcl_error_stops_before_height_and_scroll() -> None:
    canvas = FakeCanvas(fail_rooty=True)
    auto_scroll.auto_scroll_drag(canvas, 0)  # type: ignore[arg-type]
    assert canvas.calls == [("rooty",)]


def test_height_tcl_error_stops_before_scroll() -> None:
    canvas = FakeCanvas(fail_height=True)
    auto_scroll.auto_scroll_drag(canvas, 0)  # type: ignore[arg-type]
    assert canvas.calls == [("rooty",), ("height",)]


def test_scroll_tcl_error_is_not_masked() -> None:
    canvas = FakeCanvas(fail_scroll=True)
    with pytest.raises(auto_scroll.tk.TclError, match="scroll failed"):
        auto_scroll.auto_scroll_drag(canvas, 0)  # type: ignore[arg-type]


def test_overlapping_zones_preserve_upper_if_priority() -> None:
    canvas = FakeCanvas(top=100, height=20)
    auto_scroll.auto_scroll_drag(canvas, 110)  # type: ignore[arg-type]
    assert _scroll_calls(canvas) == [("scroll", -1, "units")]


def test_at_most_one_scroll_occurs_per_event() -> None:
    canvas = FakeCanvas(top=100, height=1)
    auto_scroll.auto_scroll_drag(canvas, 100)  # type: ignore[arg-type]
    assert len(_scroll_calls(canvas)) == 1


def test_custom_margin_preserves_strict_boundaries() -> None:
    canvas = FakeCanvas(top=10, height=100)
    auto_scroll.auto_scroll_drag(canvas, 14, margin=5)  # type: ignore[arg-type]
    assert _scroll_calls(canvas) == [("scroll", -1, "units")]

    boundary = FakeCanvas(top=10, height=100)
    auto_scroll.auto_scroll_drag(boundary, 15, margin=5)  # type: ignore[arg-type]
    assert _scroll_calls(boundary) == []


def test_negative_margin_fails_before_widget_access() -> None:
    canvas = FakeCanvas()
    with pytest.raises(ValueError, match="non-negative"):
        auto_scroll.auto_scroll_drag(canvas, 0, margin=-1)  # type: ignore[arg-type]
    assert canvas.calls == []


def test_adapter_has_no_application_imports_or_widget_mutation() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_tk_drag_auto_scroll.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert imports == {"__future__", "tkinter"}
    assert "DragDropCategoryGicleeApp" not in source
    assert "_DragState" not in source
    assert "Komponenty" not in source
    assert ".configure(" not in source
    assert ".update(" not in source
    assert "update_idletasks" not in source
