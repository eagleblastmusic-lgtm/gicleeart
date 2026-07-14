from __future__ import annotations

from pathlib import Path

ROOT = Path("cursor-api")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


renderer_path = ROOT / "giclee_app" / "category_renderer.py"
renderer_path.write_text(
    '''"""Callback-driven Tk renderer ekranów kategorii klasycznego launchera."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import tkinter as tk

from .component_loader import Component


@dataclass(frozen=True)
class CategoryRendererConfig:
    """Stałe wizualnego układu ekranów kategorii."""

    app_title: str
    version: str
    columns: int
    tile_pad_x: int
    tile_pad_y: int


CategoryTileBuilder = Callable[[tk.Misc, str, int], tk.Frame]
ComponentTileBuilder = Callable[[tk.Misc, Component], tk.Frame]
TextSetter = Callable[[str], None]
TitleFormatter = Callable[[str], str]
CountFormatter = Callable[[int], str]


def render_empty_state(
    parent: tk.Misc,
    message: str,
    *,
    columns: int,
) -> None:
    """Renderuje pusty stan bez znajomości klasy launchera."""

    empty = tk.Label(
        parent,
        text=message,
        bg="#f4f4f7",
        fg="#666",
        font=("Segoe UI", 10),
        justify="center",
        pady=40,
    )
    empty.grid(
        row=0,
        column=0,
        columnspan=columns,
        sticky="nsew",
    )


def render_category_index(
    *,
    root: tk.Misc,
    parent: tk.Misc,
    sections: Sequence[tuple[str, Sequence[Component]]],
    config: CategoryRendererConfig,
    set_subtitle: TextSetter,
    build_category_tile: CategoryTileBuilder,
) -> None:
    """Renderuje indeks kategorii przez jawny hook budowy kafelka."""

    root.title(f"{config.app_title} · v{config.version}")
    set_subtitle("Wybierz kategorię")
    intro = tk.Frame(parent, bg="#f4f4f7")
    intro.grid(
        row=0,
        column=0,
        columnspan=config.columns,
        sticky="ew",
        padx=18,
        pady=(16, 10),
    )
    tk.Label(
        intro,
        text="Kategorie",
        bg="#f4f4f7",
        fg="#222",
        font=("Segoe UI", 18, "bold"),
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        intro,
        text="Wybierz obszar pracy. Komponenty pojawią się dopiero po otwarciu kategorii.",
        bg="#f4f4f7",
        fg="#666",
        font=("Segoe UI", 10),
        anchor="w",
    ).pack(fill="x", pady=(3, 0))

    for index, (title, components) in enumerate(sections):
        row, column = divmod(index, config.columns)
        tile = build_category_tile(parent, title, len(components))
        tile.grid(
            row=row + 1,
            column=column,
            padx=config.tile_pad_x,
            pady=config.tile_pad_y,
            sticky="",
        )


def render_category_components(
    *,
    root: tk.Misc,
    parent: tk.Misc,
    title: str,
    components: Sequence[Component],
    config: CategoryRendererConfig,
    set_subtitle: TextSetter,
    show_category_index: Callable[[], None],
    build_component_tile: ComponentTileBuilder,
    display_title: TitleFormatter,
    count_text: CountFormatter,
) -> None:
    """Renderuje ekran komponentów przez jawny hook budowy kafelka."""

    visible_title = display_title(title)
    root.title(
        f"{config.app_title} · {visible_title} · v{config.version}"
    )
    set_subtitle(f"{visible_title} — wybierz komponent")

    nav = tk.Frame(parent, bg="#f4f4f7")
    nav.grid(
        row=0,
        column=0,
        columnspan=config.columns,
        sticky="ew",
        padx=12,
        pady=(12, 12),
    )
    nav.columnconfigure(1, weight=1)

    back = tk.Button(
        nav,
        text="← Wszystkie kategorie",
        command=show_category_index,
        bg="#ffffff",
        fg="#333",
        activebackground="#eceff4",
        activeforeground="#111",
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground="#d7d9df",
        padx=12,
        pady=7,
        cursor="hand2",
        font=("Segoe UI", 9, "bold"),
    )
    back.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 14))

    tk.Label(
        nav,
        text=visible_title,
        bg="#f4f4f7",
        fg="#222",
        font=("Segoe UI", 18, "bold"),
        anchor="w",
    ).grid(row=0, column=1, sticky="ew")
    tk.Label(
        nav,
        text=count_text(len(components)),
        bg="#f4f4f7",
        fg="#6a6a72",
        font=("Segoe UI", 10),
        anchor="w",
    ).grid(row=1, column=1, sticky="ew", pady=(2, 0))

    for index, component in enumerate(components):
        row, column = divmod(index, config.columns)
        tile = build_component_tile(parent, component)
        tile.grid(
            row=row + 1,
            column=column,
            padx=config.tile_pad_x,
            pady=config.tile_pad_y,
            sticky="",
        )
''',
    encoding="utf-8",
)

launcher_path = ROOT / "giclee_app" / "category_launcher.py"
replace_once(
    launcher_path,
    "from .category_navigation import CategoryViewKind, resolve_category_navigation\n"
    "from .component_loader import Component\n",
    "from .category_navigation import CategoryViewKind, resolve_category_navigation\n"
    "from .category_renderer import (\n"
    "    CategoryRendererConfig,\n"
    "    render_category_components as render_category_components_view,\n"
    "    render_category_index as render_category_index_view,\n"
    "    render_empty_state,\n"
    ")\n"
    "from .component_loader import Component\n",
)

old_empty = '''    def _render_empty(self, message: str) -> None:
        empty = tk.Label(
            self.tiles_frame,
            text=message,
            bg="#f4f4f7",
            fg="#666",
            font=("Segoe UI", 10),
            justify="center",
            pady=40,
        )
        empty.grid(
            row=0,
            column=0,
            columnspan=_launcher._TILES_PER_ROW,
            sticky="nsew",
        )
'''
new_empty = '''    def _category_renderer_config(self) -> CategoryRendererConfig:
        return CategoryRendererConfig(
            app_title=_launcher.APP_TITLE,
            version=_launcher.__version__,
            columns=_launcher._TILES_PER_ROW,
            tile_pad_x=_launcher._TILE_PAD_X,
            tile_pad_y=_launcher._TILE_PAD_Y,
        )

    def _render_empty(self, message: str) -> None:
        render_empty_state(
            self.tiles_frame,
            message,
            columns=_launcher._TILES_PER_ROW,
        )
'''
replace_once(launcher_path, old_empty, new_empty)

old_index = '''    def _render_category_index(
        self,
        sections: list[tuple[str, list[Component]]],
    ) -> None:
        self.root.title(f"{_launcher.APP_TITLE} · v{_launcher.__version__}")
        self._set_subtitle("Wybierz kategorię")
        intro = tk.Frame(self.tiles_frame, bg="#f4f4f7")
        intro.grid(
            row=0,
            column=0,
            columnspan=_launcher._TILES_PER_ROW,
            sticky="ew",
            padx=18,
            pady=(16, 10),
        )
        tk.Label(
            intro,
            text="Kategorie",
            bg="#f4f4f7",
            fg="#222",
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            intro,
            text="Wybierz obszar pracy. Komponenty pojawią się dopiero po otwarciu kategorii.",
            bg="#f4f4f7",
            fg="#666",
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", pady=(3, 0))

        for index, (title, components) in enumerate(sections):
            row, column = divmod(index, _launcher._TILES_PER_ROW)
            tile = self._build_category_tile(
                self.tiles_frame,
                title,
                len(components),
            )
            tile.grid(
                row=row + 1,
                column=column,
                padx=_launcher._TILE_PAD_X,
                pady=_launcher._TILE_PAD_Y,
                sticky="",
            )
'''
new_index = '''    def _render_category_index(
        self,
        sections: list[tuple[str, list[Component]]],
    ) -> None:
        render_category_index_view(
            root=self.root,
            parent=self.tiles_frame,
            sections=sections,
            config=self._category_renderer_config(),
            set_subtitle=self._set_subtitle,
            build_category_tile=self._build_category_tile,
        )
'''
replace_once(launcher_path, old_index, new_index)

old_components = '''    def _render_category_components(
        self,
        title: str,
        components: list[Component],
    ) -> None:
        display_title = category_display_title(title)
        self.root.title(
            f"{_launcher.APP_TITLE} · {display_title} · v{_launcher.__version__}"
        )
        self._set_subtitle(f"{display_title} — wybierz komponent")

        nav = tk.Frame(self.tiles_frame, bg="#f4f4f7")
        nav.grid(
            row=0,
            column=0,
            columnspan=_launcher._TILES_PER_ROW,
            sticky="ew",
            padx=12,
            pady=(12, 12),
        )
        nav.columnconfigure(1, weight=1)

        back = tk.Button(
            nav,
            text="← Wszystkie kategorie",
            command=self._show_category_index,
            bg="#ffffff",
            fg="#333",
            activebackground="#eceff4",
            activeforeground="#111",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#d7d9df",
            padx=12,
            pady=7,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        back.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 14))

        tk.Label(
            nav,
            text=display_title,
            bg="#f4f4f7",
            fg="#222",
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")
        tk.Label(
            nav,
            text=category_count_text(len(components)),
            bg="#f4f4f7",
            fg="#6a6a72",
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(2, 0))

        for index, comp in enumerate(components):
            row, column = divmod(index, _launcher._TILES_PER_ROW)
            tile = self._build_tile(self.tiles_frame, comp)
            tile.grid(
                row=row + 1,
                column=column,
                padx=_launcher._TILE_PAD_X,
                pady=_launcher._TILE_PAD_Y,
                sticky="",
            )
'''
new_components = '''    def _render_category_components(
        self,
        title: str,
        components: list[Component],
    ) -> None:
        render_category_components_view(
            root=self.root,
            parent=self.tiles_frame,
            title=title,
            components=components,
            config=self._category_renderer_config(),
            set_subtitle=self._set_subtitle,
            show_category_index=self._show_category_index,
            build_component_tile=self._build_tile,
            display_title=category_display_title,
            count_text=category_count_text,
        )
'''
replace_once(launcher_path, old_components, new_components)


test_path = ROOT / "tests" / "test_launcher_category_renderer.py"
test_path.write_text(
    r'''"""Testy LC-2B: callback-driven renderer kategorii."""

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
''',
    encoding="utf-8",
)

launcher_docs = ROOT / "giclee_app" / "docs" / "launcher.md"
replace_once(
    launcher_docs,
    "**LC-2A navigation model:** `category_navigation.py` rozstrzyga czysty, niemutowalny plan ekranu kategorii. `CategoryGicleeApp` nadal odpowiada za istniejące widgety Tk, hooki renderera, fokus, scroll i statusy.\n",
    "**LC-2A navigation model:** `category_navigation.py` rozstrzyga czysty, niemutowalny plan ekranu kategorii. `CategoryGicleeApp` nadal odpowiada za istniejące widgety Tk, hooki renderera, fokus, scroll i statusy.\n\n"
    "**LC-2B category renderer:** `category_renderer.py` buduje puste stany, indeks i ekran komponentów przez jawne callbacki. Metody `CategoryGicleeApp` pozostają wrapperami, a Styled i DnD nadal dostarczają własne hooki kafelków.\n",
)

contract = ROOT / "giclee_app" / "docs" / "launcher-composition-lc2b-contract.md"
replace_once(
    contract,
    "**Status:** fresh reconnaissance · contract freeze  ",
    "**Status:** LC-2B implemented",
)
