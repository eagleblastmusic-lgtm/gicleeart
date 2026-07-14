"""Testy LC-2B: callback-driven renderer kategorii."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from giclee_app import category_renderer
from giclee_app.category_renderer import (
    CategoryRendererConfig,
    render_category_components,
    render_category_index,
    render_empty_state,
)
from giclee_app.component_loader import Component


class _FakeWidget:
    def __init__(self, kind: str, *args: object, **kwargs: object) -> None:
        self.kind = kind
        self.args = args
        self.kwargs = kwargs
        self.grid_kwargs: dict[str, object] | None = None
        self.pack_kwargs: dict[str, object] | None = None
        self.columnconfigure_calls: list[tuple[int, dict[str, object]]] = []

    def grid(self, **kwargs: object) -> None:
        self.grid_kwargs = kwargs

    def pack(self, **kwargs: object) -> None:
        self.pack_kwargs = kwargs

    def columnconfigure(self, column: int, **kwargs: object) -> None:
        self.columnconfigure_calls.append((column, kwargs))


class _FakeRoot:
    def __init__(self) -> None:
        self.titles: list[str] = []

    def title(self, text: str) -> None:
        self.titles.append(text)


def _factory(kind: str, created: list[_FakeWidget]):
    def build(*args: object, **kwargs: object) -> _FakeWidget:
        widget = _FakeWidget(kind, *args, **kwargs)
        created.append(widget)
        return widget

    return build


def _config() -> CategoryRendererConfig:
    return CategoryRendererConfig(
        app_title="GicleeApp",
        version="9.9.9",
        columns=3,
        tile_pad_x=6,
        tile_pad_y=7,
    )


def _component(folder: str) -> Component:
    return Component(
        folder_name=folder,
        package_path=Path("/fake") / folder,
        name=folder,
        description="",
    )


def test_renderer_config_is_immutable() -> None:
    config = _config()
    with pytest.raises(FrozenInstanceError):
        config.columns = 4  # type: ignore[misc]


def test_empty_renderer_preserves_label_and_columnspan(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[_FakeWidget] = []
    monkeypatch.setattr(category_renderer.tk, "Label", _factory("label", created))
    parent = object()

    render_empty_state(parent, "Brak", columns=3)  # type: ignore[arg-type]

    assert len(created) == 1
    label = created[0]
    assert label.args == (parent,)
    assert label.kwargs["text"] == "Brak"
    assert label.kwargs["bg"] == "#f4f4f7"
    assert label.kwargs["justify"] == "center"
    assert label.grid_kwargs == {
        "row": 0,
        "column": 0,
        "columnspan": 3,
        "sticky": "nsew",
    }


def test_index_uses_explicit_category_hook_and_grid_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[_FakeWidget] = []
    monkeypatch.setattr(category_renderer.tk, "Frame", _factory("frame", created))
    monkeypatch.setattr(category_renderer.tk, "Label", _factory("label", created))
    root = _FakeRoot()
    parent = object()
    subtitles: list[str] = []
    tile_calls: list[tuple[object, str, int]] = []
    tiles: list[_FakeWidget] = []

    def build_category_tile(master: object, title: str, count: int) -> _FakeWidget:
        tile_calls.append((master, title, count))
        tile = _FakeWidget("category_tile")
        tiles.append(tile)
        return tile

    render_category_index(
        root=root,  # type: ignore[arg-type]
        parent=parent,  # type: ignore[arg-type]
        sections=[
            ("Pierwsza", [_component("a")]),
            ("Druga", [_component("b"), _component("c")]),
        ],
        config=_config(),
        set_subtitle=subtitles.append,
        build_category_tile=build_category_tile,  # type: ignore[arg-type]
    )

    assert root.titles == ["GicleeApp · v9.9.9"]
    assert subtitles == ["Wybierz kategorię"]
    assert tile_calls == [
        (parent, "Pierwsza", 1),
        (parent, "Druga", 2),
    ]
    assert tiles[0].grid_kwargs == {
        "row": 1,
        "column": 0,
        "padx": 6,
        "pady": 7,
        "sticky": "",
    }
    assert tiles[1].grid_kwargs == {
        "row": 1,
        "column": 1,
        "padx": 6,
        "pady": 7,
        "sticky": "",
    }
    assert any(widget.kwargs.get("text") == "Kategorie" for widget in created)


def test_component_screen_preserves_back_callback_and_component_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[_FakeWidget] = []
    monkeypatch.setattr(category_renderer.tk, "Frame", _factory("frame", created))
    monkeypatch.setattr(category_renderer.tk, "Label", _factory("label", created))
    monkeypatch.setattr(category_renderer.tk, "Button", _factory("button", created))
    root = _FakeRoot()
    parent = object()
    subtitles: list[str] = []
    back_calls: list[str] = []
    components = [_component("a"), _component("b"), _component("c"), _component("d")]
    tile_calls: list[tuple[object, Component]] = []
    tiles: list[_FakeWidget] = []

    def build_component_tile(master: object, component: Component) -> _FakeWidget:
        tile_calls.append((master, component))
        tile = _FakeWidget("component_tile")
        tiles.append(tile)
        return tile

    def go_back() -> None:
        back_calls.append("back")

    render_category_components(
        root=root,  # type: ignore[arg-type]
        parent=parent,  # type: ignore[arg-type]
        title="Wewnetrzna",
        components=components,
        config=_config(),
        set_subtitle=subtitles.append,
        show_category_index=go_back,
        build_component_tile=build_component_tile,  # type: ignore[arg-type]
        display_title=lambda value: f"Widoczna:{value}",
        count_text=lambda count: f"COUNT:{count}",
    )

    assert root.titles == ["GicleeApp · Widoczna:Wewnetrzna · v9.9.9"]
    assert subtitles == ["Widoczna:Wewnetrzna — wybierz komponent"]
    button = next(widget for widget in created if widget.kind == "button")
    assert button.kwargs["command"] is go_back
    command = button.kwargs["command"]
    assert callable(command)
    command()
    assert back_calls == ["back"]
    assert [component for _master, component in tile_calls] == components
    assert tiles[0].grid_kwargs["row"] == 1
    assert tiles[0].grid_kwargs["column"] == 0
    assert tiles[3].grid_kwargs["row"] == 2
    assert tiles[3].grid_kwargs["column"] == 0
    assert any(widget.kwargs.get("text") == "COUNT:4" for widget in created)


def test_renderer_import_boundary_is_narrow() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "category_renderer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    forbidden = {
        "launcher",
        "launcher_layout",
        "launcher_shortcuts",
        "dragdrop_category_launcher",
        "launcher_studio",
    }
    assert imports.isdisjoint(forbidden)


def test_category_launcher_wrappers_delegate_and_keep_extension_hooks() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "category_launcher.py"
    source = path.read_text(encoding="utf-8")
    empty_block = source.split("def _render_empty", 1)[1].split("\n    def ", 1)[0]
    index_block = source.split("def _render_category_index", 1)[1].split("\n    def ", 1)[0]
    components_block = source.split("def _render_category_components", 1)[1].split("\n    def ", 1)[0]

    assert "render_empty_state(" in empty_block
    assert "render_category_index_view(" in index_block
    assert "build_category_tile=self._build_category_tile" in index_block
    assert "render_category_components_view(" in components_block
    assert "build_component_tile=self._build_tile" in components_block
    assert "show_category_index=self._show_category_index" in components_block
    assert "def _render_tiles" in source
    assert "def _build_category_tile" in source
    assert "def _build_tile" not in source
