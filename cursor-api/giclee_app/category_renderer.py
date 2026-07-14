"""Callback-driven Tk renderer ekranów kategorii klasycznego launchera."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import tkinter as tk

from .component_loader import Component
from .launcher_grid_layout import TileGridSpec, place_tile


@dataclass(frozen=True)
class CategoryRendererConfig:
    """Stałe wizualnego układu ekranów kategorii."""

    app_title: str
    version: str
    columns: int
    tile_pad_x: int
    tile_pad_y: int

    def tile_grid_spec(self, *, row_offset: int = 1) -> TileGridSpec:
        return TileGridSpec(
            columns=self.columns,
            row_offset=row_offset,
            padx=self.tile_pad_x,
            pady=self.tile_pad_y,
            sticky="",
        )


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

    grid_spec = config.tile_grid_spec(row_offset=1)
    for index, (title, components) in enumerate(sections):
        tile = build_category_tile(parent, title, len(components))
        place_tile(tile, index, grid_spec)


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

    grid_spec = config.tile_grid_spec(row_offset=1)
    for index, component in enumerate(components):
        tile = build_component_tile(parent, component)
        place_tile(tile, index, grid_spec)
