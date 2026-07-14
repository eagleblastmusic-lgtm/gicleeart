"""Dwupoziomowa nawigacja kategorii dla klasycznego launchera GicleeApp."""

from __future__ import annotations

from dataclasses import dataclass
import time
import tkinter as tk
from typing import Any

from . import launcher as _launcher
from .category_navigation import CategoryViewKind, resolve_category_navigation
from .category_renderer import (
    CategoryRendererConfig,
    render_category_components as render_category_components_view,
    render_category_index as render_category_index_view,
    render_empty_state,
)
from .component_loader import Component


@dataclass(frozen=True)
class CategoryAppearance:
    """Warstwa prezentacyjna kafelka kategorii."""

    icon: str
    description: str
    color: str
    display_title: str | None = None


_CATEGORY_APPEARANCES: dict[str, CategoryAppearance] = {
    "Administracja produktu": CategoryAppearance(
        icon="🖼️",
        description="Produkty, obrazy, ceny, opisy i przygotowanie plików.",
        color="#496A9B",
    ),
    "Administracja strony": CategoryAppearance(
        icon="🧭",
        description="Strony Shopify, układy, sekcje i elementy sklepu.",
        color="#6F5A98",
    ),
    "Zamowienia": CategoryAppearance(
        icon="📦",
        description="Realizacja zamówień, produkcja i przygotowanie oprawy.",
        color="#9A673F",
        display_title="Zamówienia",
    ),
    "Finanse": CategoryAppearance(
        icon="💰",
        description="Księgowość, dokumenty sprzedaży i kalkulacja kosztów.",
        color="#44775D",
    ),
    "Marketing": CategoryAppearance(
        icon="📣",
        description="Treści, social media, analityka i planowanie działań.",
        color="#9A5667",
    ),
    "Narzedzia pomocnicze": CategoryAppearance(
        icon="🛠️",
        description="Codzienna praca, notatki, integracje i narzędzia techniczne.",
        color="#526C80",
        display_title="Narzędzia pomocnicze",
    ),
    "Inne": CategoryAppearance(
        icon="•••",
        description="Pozostałe komponenty i własne przypisania.",
        color="#68707A",
    ),
}
_DEFAULT_CATEGORY_APPEARANCE = CategoryAppearance(
    icon="▦",
    description="Komponenty przypisane do tej kategorii.",
    color="#5F6874",
)


def category_appearance(title: str) -> CategoryAppearance:
    """Zwraca wygląd znanej kategorii albo neutralny fallback dla własnej nazwy."""

    return _CATEGORY_APPEARANCES.get(title, _DEFAULT_CATEGORY_APPEARANCE)


def category_display_title(title: str) -> str:
    """Tytuł prezentacyjny; wewnętrzny identyfikator sekcji pozostaje bez zmian."""

    appearance = category_appearance(title)
    return appearance.display_title or title


def category_count_text(count: int) -> str:
    """Polska etykieta liczby komponentów."""

    count = max(0, int(count))
    if count == 1:
        suffix = "komponent"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        suffix = "komponenty"
    else:
        suffix = "komponentów"
    return f"{count} {suffix}"


def category_map(
    sections: list[tuple[str, list[Component]]],
) -> dict[str, list[Component]]:
    """Buduje stabilną mapę tytuł → widoczne komponenty."""

    return {title: list(components) for title, components in sections}


class CategoryGicleeApp(_launcher.GicleeApp):
    """Launcher: ekran kategorii → ekran komponentów wybranej kategorii."""

    def __init__(self, root: tk.Tk) -> None:
        self._active_section: str | None = None
        self._subtitle_widget: tk.Widget | None = None
        super().__init__(root)

    def _build_ui(self) -> None:
        super()._build_ui()
        self._subtitle_widget = self._find_widget_with_text(
            self.root,
            "Wybierz komponent, ktory chcesz uruchomic",
        )
        self.root.bind("<Escape>", self._on_category_back, add="+")
        self.root.bind("<Alt-Left>", self._on_category_back, add="+")
        self.root.bind("<BackSpace>", self._on_category_back, add="+")

    def _find_widget_with_text(self, parent: tk.Misc, expected: str) -> tk.Widget | None:
        for child in parent.winfo_children():
            try:
                if child.cget("text") == expected:
                    return child
            except (tk.TclError, TypeError):
                pass
            found = self._find_widget_with_text(child, expected)
            if found is not None:
                return found
        return None

    def _set_subtitle(self, text: str) -> None:
        if self._subtitle_widget is None:
            return
        try:
            self._subtitle_widget.configure(text=text)
        except tk.TclError:
            self._subtitle_widget = None

    def _render_tiles(self) -> None:
        self._tile_hover_clearers.clear()
        for child in list(self.tiles_frame.winfo_children()):
            child.destroy()

        for column in range(_launcher._TILES_PER_ROW):
            self.tiles_frame.columnconfigure(column, weight=1, uniform="tiles")

        plan = resolve_category_navigation(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
            active_section=self._active_section,
        )
        self._active_section = plan.active_section

        if plan.kind is CategoryViewKind.NO_COMPONENTS:
            self._set_subtitle("Brak wykrytych komponentów")
            self._render_empty(
                "Brak komponentow.\n\n"
                f"Dodaj nowy komponent jako podkatalog w:\n{self.components_dir}\n\n"
                "Komponent powinien zawierac plik __main__.py.\n"
                "Opcjonalny component.json definiuje nazwe, opis, ikonke i kolor."
            )
            return

        if plan.kind is CategoryViewKind.NO_VISIBLE_SECTIONS:
            self._set_subtitle("Brak widocznych komponentów")
            self._render_empty(
                "Brak widocznych kafelkow.\n\n"
                "Kliknij „Opcje” w gornym pasku, aby wlaczyc komponenty\n"
                "i przypisac je do sekcji."
            )
            return

        if plan.kind is CategoryViewKind.CATEGORY_INDEX:
            self._render_category_index([
                (title, list(components))
                for title, components in plan.sections
            ])
            return

        if plan.active_section is None:
            raise RuntimeError("Category navigation plan has no active section")
        self._render_category_components(
            plan.active_section,
            list(plan.active_components),
        )

    def _category_renderer_config(self) -> CategoryRendererConfig:
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

    def _render_category_index(
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

    def _render_category_components(
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

    def _build_category_tile(
        self,
        parent: tk.Misc,
        title: str,
        count: int,
    ) -> tk.Frame:
        appearance = category_appearance(title)
        bg_normal = "#ffffff"
        bg_hover = "#eef1f6"

        outer = tk.Frame(
            parent,
            bg=bg_normal,
            bd=0,
            highlightthickness=1,
            highlightbackground="#dcdce2",
            highlightcolor="#dcdce2",
            width=_launcher._TILE_W,
            height=_launcher._TILE_H,
        )
        outer.pack_propagate(False)

        accent = tk.Frame(outer, bg=appearance.color, width=7)
        accent.pack(side="left", fill="y")

        body = tk.Frame(outer, bg=bg_normal)
        body.pack(side="left", fill="both", expand=True, padx=15, pady=13)

        top = tk.Frame(body, bg=bg_normal)
        top.pack(fill="x")
        tk.Label(
            top,
            text=appearance.icon,
            bg=bg_normal,
            fg="#222",
            font=("Segoe UI Emoji", 20, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            top,
            text=category_count_text(count),
            bg=bg_normal,
            fg="#777",
            font=("Segoe UI", 9),
            anchor="e",
        ).pack(side="right", pady=(5, 0))

        tk.Label(
            body,
            text=category_display_title(title),
            bg=bg_normal,
            fg="#222",
            font=("Segoe UI", 13, "bold"),
            justify="left",
            anchor="w",
            wraplength=_launcher._TILE_W - 50,
        ).pack(fill="x", pady=(8, 0))
        tk.Label(
            body,
            text=appearance.description,
            bg=bg_normal,
            fg="#5d5d65",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=_launcher._TILE_W - 50,
        ).pack(fill="x", pady=(5, 0))

        tk.Frame(body, bg=bg_normal).pack(fill="both", expand=True)
        tk.Label(
            body,
            text="Otwórz kategorię  →",
            bg=bg_normal,
            fg=appearance.color,
            font=("Segoe UI", 9, "bold"),
            anchor="e",
        ).pack(fill="x")

        background_widgets: list[tk.Widget] = []

        def collect(widget: tk.Widget) -> None:
            if widget is accent:
                return
            background_widgets.append(widget)
            for child in widget.winfo_children():
                collect(child)

        collect(outer)

        def set_hover(active: bool) -> None:
            new_bg = bg_hover if active else bg_normal
            for widget in background_widgets:
                try:
                    widget.configure(bg=new_bg)
                except tk.TclError:
                    pass

        self._tile_hover_clearers.append(lambda: set_hover(False))

        def on_enter(_event: object) -> None:
            if time.monotonic() < self._suppress_tile_hover_until:
                return
            set_hover(True)

        def on_leave(_event: object) -> None:
            if time.monotonic() < self._suppress_tile_hover_until:
                return
            try:
                px, py = outer.winfo_pointerxy()
                ox, oy = outer.winfo_rootx(), outer.winfo_rooty()
                ow, oh = outer.winfo_width(), outer.winfo_height()
            except tk.TclError:
                return
            if ox <= px < ox + ow and oy <= py < oy + oh:
                return
            set_hover(False)

        def open_category(_event: object = None, selected: str = title) -> None:
            self._open_category(selected)

        def bind_recursive(widget: tk.Widget) -> None:
            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget.bind("<Button-1>", open_category, add="+")
            try:
                widget.configure(cursor="hand2")
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(outer)
        return outer

    def _open_category(self, title: str) -> None:
        self._active_section = title
        self._render_tiles()
        self._finish_navigation_render()
        self.status_var.set(f"{category_display_title(title)}: wybierz komponent")

    def _show_category_index(self) -> None:
        self._active_section = None
        self._render_tiles()
        self._finish_navigation_render()
        self.status_var.set("Wybierz kategorię")

    def _finish_navigation_render(self) -> None:
        self._sync_tiles_canvas_scroll()
        try:
            self.canvas.yview_moveto(0)
        except tk.TclError:
            pass
        self.root.after_idle(self._focus_tiles_canvas)

    def _on_category_back(self, _event: Any = None) -> str | None:
        if self._active_section is None:
            return None
        if not self.tiles_view.winfo_ismapped():
            return None
        self._show_category_index()
        return "break"


def main() -> None:
    """Uruchamia bazowy launcher z klasą nawigacji kategorii."""

    _launcher.main(app_factory=CategoryGicleeApp)


if __name__ == "__main__":
    main()
