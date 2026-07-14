from __future__ import annotations

from pathlib import Path

ROOT = Path("cursor-api")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


model_path = ROOT / "giclee_app" / "category_navigation.py"
model_path.write_text(
    '''"""Czysty model trasy kategorii klasycznego launchera."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from .component_loader import Component
from .launcher_layout import LauncherLayout, resolve_sections


class CategoryViewKind(str, Enum):
    """Ekran, który powinien wyrenderować klasyczny launcher kategorii."""

    NO_COMPONENTS = "no_components"
    NO_VISIBLE_SECTIONS = "no_visible_sections"
    CATEGORY_INDEX = "category_index"
    CATEGORY_COMPONENTS = "category_components"


CategorySection = tuple[str, tuple[Component, ...]]


@dataclass(frozen=True)
class CategoryNavigationPlan:
    """Niemutowalny wynik rozstrzygnięcia aktualnej trasy kategorii."""

    kind: CategoryViewKind
    active_section: str | None
    sections: tuple[CategorySection, ...] = ()
    active_components: tuple[Component, ...] = ()


def resolve_category_navigation(
    all_components: Sequence[Component],
    layout: LauncherLayout,
    *,
    normally_visible: set[str],
    active_section: str | None,
) -> CategoryNavigationPlan:
    """Rozstrzyga ekran bez Tk, I/O i mutacji wejściowego stanu."""

    components = tuple(all_components)
    if not components:
        return CategoryNavigationPlan(
            kind=CategoryViewKind.NO_COMPONENTS,
            active_section=None,
        )

    resolved = resolve_sections(
        list(components),
        layout,
        normally_visible=normally_visible,
    )
    sections: tuple[CategorySection, ...] = tuple(
        (title, tuple(section_components))
        for title, section_components in resolved
    )
    if not sections:
        return CategoryNavigationPlan(
            kind=CategoryViewKind.NO_VISIBLE_SECTIONS,
            active_section=None,
        )

    by_title = dict(sections)
    normalized_active = active_section if active_section in by_title else None
    if normalized_active is None:
        return CategoryNavigationPlan(
            kind=CategoryViewKind.CATEGORY_INDEX,
            active_section=None,
            sections=sections,
        )

    return CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_COMPONENTS,
        active_section=normalized_active,
        sections=sections,
        active_components=by_title[normalized_active],
    )
''',
    encoding="utf-8",
)

launcher_path = ROOT / "giclee_app" / "category_launcher.py"
replace_once(
    launcher_path,
    "from . import launcher as _launcher\n"
    "from .component_loader import Component\n"
    "from .launcher_layout import resolve_sections\n",
    "from . import launcher as _launcher\n"
    "from .category_navigation import CategoryViewKind, resolve_category_navigation\n"
    "from .component_loader import Component\n",
)

old_render = '''        if not self._all_components:
            self._active_section = None
            self._set_subtitle("Brak wykrytych komponentów")
            self._render_empty(
                "Brak komponentow.\\n\\n"
                f"Dodaj nowy komponent jako podkatalog w:\\n{self.components_dir}\\n\\n"
                "Komponent powinien zawierac plik __main__.py.\\n"
                "Opcjonalny component.json definiuje nazwe, opis, ikonke i kolor."
            )
            return

        sections = resolve_sections(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
        )
        if not sections:
            self._active_section = None
            self._set_subtitle("Brak widocznych komponentów")
            self._render_empty(
                "Brak widocznych kafelkow.\\n\\n"
                "Kliknij „Opcje” w gornym pasku, aby wlaczyc komponenty\\n"
                "i przypisac je do sekcji."
            )
            return

        by_title = category_map(sections)
        if self._active_section not in by_title:
            self._active_section = None

        if self._active_section is None:
            self._render_category_index(sections)
        else:
            self._render_category_components(
                self._active_section,
                by_title[self._active_section],
            )
'''
new_render = '''        plan = resolve_category_navigation(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
            active_section=self._active_section,
        )
        self._active_section = plan.active_section

        if plan.kind is CategoryViewKind.NO_COMPONENTS:
            self._set_subtitle("Brak wykrytych komponentów")
            self._render_empty(
                "Brak komponentow.\\n\\n"
                f"Dodaj nowy komponent jako podkatalog w:\\n{self.components_dir}\\n\\n"
                "Komponent powinien zawierac plik __main__.py.\\n"
                "Opcjonalny component.json definiuje nazwe, opis, ikonke i kolor."
            )
            return

        if plan.kind is CategoryViewKind.NO_VISIBLE_SECTIONS:
            self._set_subtitle("Brak widocznych komponentów")
            self._render_empty(
                "Brak widocznych kafelkow.\\n\\n"
                "Kliknij „Opcje” w gornym pasku, aby wlaczyc komponenty\\n"
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
'''
replace_once(launcher_path, old_render, new_render)


test_path = ROOT / "tests" / "test_launcher_category_navigation_model.py"
test_path.write_text(
    '''"""Testy LC-2A: czysty model trasy kategorii."""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

from giclee_app.category_navigation import (
    CategoryViewKind,
    resolve_category_navigation,
)
from giclee_app.component_loader import Component
from giclee_app.launcher_layout import LauncherLayout, TileLayoutEntry


def _component(folder: str, name: str | None = None) -> Component:
    return Component(
        folder_name=folder,
        package_path=Path("/fake") / folder,
        name=name or folder,
        description="",
        order=0,
    )


def _layout(*entries: TileLayoutEntry, order: list[str] | None = None) -> LauncherLayout:
    return LauncherLayout(
        entries={entry.folder: entry for entry in entries},
        section_order=list(order or []),
    )


def test_no_components_returns_no_components_plan() -> None:
    plan = resolve_category_navigation(
        [],
        LauncherLayout(),
        normally_visible=set(),
        active_section="Missing",
    )

    assert plan.kind is CategoryViewKind.NO_COMPONENTS
    assert plan.active_section is None
    assert plan.sections == ()
    assert plan.active_components == ()


def test_existing_components_without_visible_sections_return_empty_visible_plan() -> None:
    comp = _component("a")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=False, sort_key=0),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [comp],
        layout,
        normally_visible={"a"},
        active_section="Pierwsza",
    )

    assert plan.kind is CategoryViewKind.NO_VISIBLE_SECTIONS
    assert plan.active_section is None
    assert plan.sections == ()


def test_missing_active_section_returns_category_index() -> None:
    comp = _component("a")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=0),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [comp],
        layout,
        normally_visible={"a"},
        active_section=None,
    )

    assert plan.kind is CategoryViewKind.CATEGORY_INDEX
    assert plan.active_section is None
    assert plan.sections == (("Pierwsza", (comp,)),)


def test_valid_active_section_returns_immutable_components_route() -> None:
    first = _component("a")
    second = _component("b")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=20),
        TileLayoutEntry(folder="b", section="Pierwsza", visible=True, sort_key=10),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [first, second],
        layout,
        normally_visible={"a", "b"},
        active_section="Pierwsza",
    )

    assert plan.kind is CategoryViewKind.CATEGORY_COMPONENTS
    assert plan.active_section == "Pierwsza"
    assert plan.sections == (("Pierwsza", (second, first)),)
    assert plan.active_components == (second, first)
    assert isinstance(plan.sections, tuple)
    assert isinstance(plan.active_components, tuple)


def test_invalid_or_now_hidden_active_section_returns_index() -> None:
    comp = _component("a")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=0),
        order=["Pierwsza"],
    )

    plan = resolve_category_navigation(
        [comp],
        layout,
        normally_visible={"a"},
        active_section="Usunięta",
    )

    assert plan.kind is CategoryViewKind.CATEGORY_INDEX
    assert plan.active_section is None
    assert plan.sections == (("Pierwsza", (comp,)),)


def test_section_and_component_order_matches_launcher_layout() -> None:
    a = _component("a")
    b = _component("b")
    c = _component("c")
    layout = _layout(
        TileLayoutEntry(folder="a", section="Druga", visible=True, sort_key=10),
        TileLayoutEntry(folder="b", section="Pierwsza", visible=True, sort_key=20),
        TileLayoutEntry(folder="c", section="Pierwsza", visible=True, sort_key=10),
        order=["Pierwsza", "Druga"],
    )

    plan = resolve_category_navigation(
        [a, b, c],
        layout,
        normally_visible={"a", "b", "c"},
        active_section=None,
    )

    assert plan.sections == (
        ("Pierwsza", (c, b)),
        ("Druga", (a,)),
    )


def test_resolver_does_not_mutate_inputs() -> None:
    comp = _component("a")
    components = [comp]
    visible = {"a"}
    layout = _layout(
        TileLayoutEntry(folder="a", section="Pierwsza", visible=True, sort_key=0),
        order=["Pierwsza"],
    )
    layout_before = deepcopy(layout.to_dict())
    components_before = list(components)
    visible_before = set(visible)

    resolve_category_navigation(
        components,
        layout,
        normally_visible=visible,
        active_section="Pierwsza",
    )

    assert layout.to_dict() == layout_before
    assert components == components_before
    assert visible == visible_before


def test_model_module_has_no_tk_or_ui_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "category_navigation.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name == "tkinter" or name.startswith("tkinter.") for name in imports)
    assert not any(name.startswith("giclee_app.ui") for name in imports)


def test_category_renderer_consumes_navigation_plan_and_keeps_hooks() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "category_launcher.py"
    source = path.read_text(encoding="utf-8")
    render_block = source.split("def _render_tiles", 1)[1].split("\n    def ", 1)[0]

    assert "resolve_category_navigation(" in render_block
    assert "CategoryViewKind.NO_COMPONENTS" in render_block
    assert "CategoryViewKind.NO_VISIBLE_SECTIONS" in render_block
    assert "CategoryViewKind.CATEGORY_INDEX" in render_block
    assert "Brak wykrytych komponentów" in render_block
    assert "Brak widocznych komponentów" in render_block
    assert "def _render_category_index" in source
    assert "def _render_category_components" in source
    assert "def _build_category_tile" in source
''',
    encoding="utf-8",
)

launcher_docs = ROOT / "giclee_app" / "docs" / "launcher.md"
replace_once(
    launcher_docs,
    "**LC-1 composition root:** warstwy klasycznego launchera przekazują finalną klasę jawnie do `launcher.main(app_factory=...)`. Entry point, MRO i zachowanie pozostają bez zmian, a runtime nie podmienia już globalnego `launcher.GicleeApp`.\n",
    "**LC-1 composition root:** warstwy klasycznego launchera przekazują finalną klasę jawnie do `launcher.main(app_factory=...)`. Entry point, MRO i zachowanie pozostają bez zmian, a runtime nie podmienia już globalnego `launcher.GicleeApp`.\n\n"
    "**LC-2A navigation model:** `category_navigation.py` rozstrzyga czysty, niemutowalny plan ekranu kategorii. `CategoryGicleeApp` nadal odpowiada za istniejące widgety Tk, hooki renderera, fokus, scroll i statusy.\n",
)

contract = ROOT / "giclee_app" / "docs" / "launcher-composition-lc2-contract.md"
replace_once(
    contract,
    "**Status:** fresh reconnaissance · LC-2A contract freeze  ",
    "**Status:** LC-2A implemented",
)
