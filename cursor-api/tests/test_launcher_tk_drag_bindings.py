"""Testy LC-3F: rekursywne bindingi Tk dla drag-and-drop launchera."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from giclee_app import dragdrop_category_launcher as dnd
from giclee_app import launcher_tk_drag_bindings as bindings


class FakeWidget:
    def __init__(
        self,
        name: str,
        *,
        children: list["FakeWidget"] | None = None,
        fail_unbind: bool = False,
        fail_configure: bool = False,
        fail_bind_event: str | None = None,
    ) -> None:
        self.name = name
        self.children = children or []
        self.fail_unbind = fail_unbind
        self.fail_configure = fail_configure
        self.fail_bind_event = fail_bind_event
        self.calls: list[tuple[object, ...]] = []
        self._launcher_dnd_kind = None
        self._launcher_dnd_key = None

    def unbind(self, event: str) -> None:
        self.calls.append(("unbind", event))
        if self.fail_unbind:
            raise bindings.tk.TclError("unbind failed")

    def bind(self, event: str, callback, *, add: str):
        self.calls.append(("bind", event, callback, add))
        if event == self.fail_bind_event:
            raise bindings.tk.TclError("bind failed")
        return f"{self.name}:{event}"

    def configure(self, **kwargs: object) -> None:
        self.calls.append(("configure", kwargs))
        if self.fail_configure:
            raise bindings.tk.TclError("configure failed")

    def winfo_children(self) -> list["FakeWidget"]:
        self.calls.append(("children",))
        return list(self.children)


def _callbacks():
    def on_press(event):
        return f"press:{event}"

    def on_motion(event):
        return f"motion:{event}"

    def on_release(event):
        return f"release:{event}"

    return on_press, on_motion, on_release


def test_installs_exact_bindings_on_root_and_descendants_depth_first() -> None:
    grandchild = FakeWidget("grandchild")
    first = FakeWidget("first", children=[grandchild])
    second = FakeWidget("second")
    root = FakeWidget("root", children=[first, second])
    on_press, on_motion, on_release = _callbacks()

    bindings.install_tile_drag_bindings(
        root,
        on_press=on_press,
        on_motion=on_motion,
        on_release=on_release,
    )

    for widget in (root, first, grandchild, second):
        assert widget.calls[:5] == [
            ("unbind", "<Button-1>"),
            ("bind", "<ButtonPress-1>", on_press, "+"),
            ("bind", "<B1-Motion>", on_motion, "+"),
            ("bind", "<ButtonRelease-1>", on_release, "+"),
            ("configure", {"cursor": "hand2"}),
        ]
        assert widget.calls[5] == ("children",)

    # Naturalny DFS: dziecko pierwszego węzła jest obsłużone przed drugim rodzeństwem.
    first_children_index = first.calls.index(("children",))
    grandchild_unbind_index = grandchild.calls.index(("unbind", "<Button-1>"))
    second_unbind_index = second.calls.index(("unbind", "<Button-1>"))
    assert first_children_index == 5
    assert grandchild_unbind_index == 0
    assert second_unbind_index == 0


def test_unbind_and_cursor_tcl_errors_are_best_effort() -> None:
    child = FakeWidget("child")
    root = FakeWidget(
        "root",
        children=[child],
        fail_unbind=True,
        fail_configure=True,
    )
    on_press, on_motion, on_release = _callbacks()

    bindings.install_tile_drag_bindings(
        root,
        on_press=on_press,
        on_motion=on_motion,
        on_release=on_release,
    )

    assert ("bind", "<ButtonPress-1>", on_press, "+") in root.calls
    assert ("bind", "<B1-Motion>", on_motion, "+") in root.calls
    assert ("bind", "<ButtonRelease-1>", on_release, "+") in root.calls
    assert child.calls[0] == ("unbind", "<Button-1>")


def test_required_bind_failure_propagates_and_stops_partial_tree() -> None:
    child = FakeWidget("child")
    root = FakeWidget(
        "root",
        children=[child],
        fail_bind_event="<B1-Motion>",
    )
    on_press, on_motion, on_release = _callbacks()

    with pytest.raises(bindings.tk.TclError, match="bind failed"):
        bindings.install_tile_drag_bindings(
            root,
            on_press=on_press,
            on_motion=on_motion,
            on_release=on_release,
        )

    assert root.calls == [
        ("unbind", "<Button-1>"),
        ("bind", "<ButtonPress-1>", on_press, "+"),
        ("bind", "<B1-Motion>", on_motion, "+"),
    ]
    assert child.calls == []


def test_adapter_has_no_application_imports_or_dedup_mechanism() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_tk_drag_bindings.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name.startswith("giclee_app") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)
    assert "bind_class" not in source
    assert "bindtags" not in source
    assert "marker" not in source.lower()


def test_enable_tile_drag_keeps_metadata_registry_and_press_closure(monkeypatch) -> None:
    root = FakeWidget("root", children=[FakeWidget("child")])
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    app._dnd_tiles = []
    captured: dict[str, object] = {}
    activation: list[str] = []
    press_calls: list[tuple[object, ...]] = []

    def fake_install(tile, *, on_press, on_motion, on_release) -> None:
        captured.update(
            tile=tile,
            on_press=on_press,
            on_motion=on_motion,
            on_release=on_release,
        )

    monkeypatch.setattr(dnd, "install_tile_drag_bindings", fake_install)

    def on_press(event, tile, kind, key, activate):
        press_calls.append((event, tile, kind, key, activate))
        return "press-result"

    app._on_tile_press = on_press
    app._on_tile_motion = lambda event: "motion-result"
    app._on_tile_release = lambda event: "release-result"

    activate = lambda: activation.append("activated")
    app._enable_tile_drag(
        root,  # type: ignore[arg-type]
        kind="component",
        key="folder-a",
        activate=activate,
    )

    assert root._launcher_dnd_kind == "component"
    assert root._launcher_dnd_key == "folder-a"
    assert app._dnd_tiles == [root]
    assert captured["tile"] is root

    event = SimpleNamespace(x_root=11, y_root=22)
    assert captured["on_press"](event) == "press-result"  # type: ignore[operator]
    assert press_calls == [(event, root, "component", "folder-a", activate)]
    assert captured["on_motion"](event) == "motion-result"  # type: ignore[operator]
    assert captured["on_release"](event) == "release-result"  # type: ignore[operator]

    activate()
    assert activation == ["activated"]
    child = root.children[0]
    assert child._launcher_dnd_kind is None
    assert child._launcher_dnd_key is None


def test_dragdrop_source_delegates_binding_tree_only() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    enable = source.split("def _enable_tile_drag", 1)[1].split("\n    def ", 1)[0]

    assert "install_tile_drag_bindings(" in enable
    assert "_launcher_dnd_kind" in enable
    assert "_launcher_dnd_key" in enable
    assert "self._dnd_tiles.append(tile)" in enable
    assert "self._on_tile_press(" in enable
    assert "bind_recursive" not in enable
    assert '.bind("<B1-Motion>"' not in enable
    assert '.unbind("<Button-1>"' not in enable
