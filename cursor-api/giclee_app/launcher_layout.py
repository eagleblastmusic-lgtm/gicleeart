"""Personalizacja siatki kafelków GicleeApp — sekcje i widoczność."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .component_loader import Component

SECTION_OTHER = "Inne"

DEFAULT_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Administracja produktu",
        [
            "dodajobraz", "aktualizujopis", "zmienceny", "wyborszablonu", "zmietytuly", "tytulyai",
            "nazwijobraz", "pobierzobraz", "squoosh", "print_optimize", "mockup", "infoplikow", "przedpo",
        ],
    ),
    ("Administracja strony", ["wzorzecszablonu", "stronaproduktu", "karuzela", "tldobio", "stronaglowna"]),
    ("Zamowienia", ["obrazy", "produkcja", "passepartout"]),
    ("Finanse", ["finanse", "kalkulacja"]),
    ("Marketing", ["blog", "socialmedia", "zadania", "cenyMarketing", "analytics"]),
    ("Narzedzia pomocnicze", ["limity", "planer", "notatnik", "bazapromptow", "stronyzobrazami", "stronydozycia", "poczta", "sklep"]),
]


def _layout_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "launcher_layout.json"


def section_titles(sections: list[tuple[str, list[str]]] | None = None) -> list[str]:
    src = sections or DEFAULT_SECTIONS
    titles = [t for t, _ in src]
    if SECTION_OTHER not in titles:
        titles.append(SECTION_OTHER)
    return titles


def _default_section_for(folder: str) -> str:
    for title, folders in DEFAULT_SECTIONS:
        if folder in folders:
            return title
    return SECTION_OTHER


@dataclass
class TileLayoutEntry:
    folder: str
    section: str
    visible: bool
    sort_key: int = 0


@dataclass
class LauncherLayout:
    entries: dict[str, TileLayoutEntry] = field(default_factory=dict)
    section_order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "section_order": self.section_order,
            "entries": {
                folder: {
                    "section": e.section,
                    "visible": e.visible,
                    "sort_key": e.sort_key,
                }
                for folder, e in self.entries.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LauncherLayout:
        raw = data.get("entries") if isinstance(data.get("entries"), dict) else {}
        entries: dict[str, TileLayoutEntry] = {}
        for folder, row in raw.items():
            if not isinstance(row, dict):
                continue
            entries[str(folder)] = TileLayoutEntry(
                folder=str(folder),
                section=str(row.get("section") or _default_section_for(str(folder))),
                visible=bool(row.get("visible")),
                sort_key=int(row.get("sort_key") or 0),
            )
        order = data.get("section_order")
        section_order = [str(x) for x in order] if isinstance(order, list) else []
        return cls(entries=entries, section_order=section_order)


def load_layout() -> LauncherLayout:
    path = _layout_path()
    if not path.is_file():
        return LauncherLayout()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return LauncherLayout.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return LauncherLayout()


def save_layout(layout: LauncherLayout) -> None:
    path = _layout_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(layout.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_default_layout(
    all_components: list[Component],
    *,
    normally_visible: set[str],
) -> LauncherLayout:
    """Układ startowy z DEFAULT_SECTIONS + widoczność jak bez personalizacji."""
    entries: dict[str, TileLayoutEntry] = {}
    sort_key = 0
    for _title, folders in DEFAULT_SECTIONS:
        for folder in folders:
            entries[folder] = TileLayoutEntry(
                folder=folder,
                section=_title,
                visible=folder in normally_visible,
                sort_key=sort_key,
            )
            sort_key += 1
    for comp in all_components:
        if comp.folder_name in entries:
            continue
        entries[comp.folder_name] = TileLayoutEntry(
            folder=comp.folder_name,
            section=_default_section_for(comp.folder_name),
            visible=comp.folder_name in normally_visible,
            sort_key=sort_key,
        )
        sort_key += 1
    return LauncherLayout(
        entries=entries,
        section_order=section_titles(DEFAULT_SECTIONS),
    )


def merge_layout(
    saved: LauncherLayout,
    all_components: list[Component],
    *,
    normally_visible: set[str],
) -> LauncherLayout:
    """Uzupełnia brakujące komponenty; zachowuje zapisane preferencje."""
    if not saved.entries:
        return build_default_layout(all_components, normally_visible=normally_visible)

    merged = LauncherLayout(
        entries=dict(saved.entries),
        section_order=list(saved.section_order) or section_titles(DEFAULT_SECTIONS),
    )
    max_key = max((e.sort_key for e in merged.entries.values()), default=-1)
    for comp in all_components:
        if comp.folder_name in merged.entries:
            continue
        max_key += 1
        merged.entries[comp.folder_name] = TileLayoutEntry(
            folder=comp.folder_name,
            section=_default_section_for(comp.folder_name),
            visible=comp.folder_name in normally_visible,
            sort_key=max_key,
        )
    for title in section_titles(DEFAULT_SECTIONS):
        if title not in merged.section_order:
            merged.section_order.append(title)
    return merged


def is_tile_visible(folder: str, layout: LauncherLayout, *, normally_visible: set[str]) -> bool:
    entry = layout.entries.get(folder)
    if entry is not None:
        return entry.visible
    return folder in normally_visible


def resolve_sections(
    all_components: list[Component],
    layout: LauncherLayout,
    *,
    normally_visible: set[str],
) -> list[tuple[str, list[Component]]]:
    """Sekcje z kafelkami widocznymi wg układu użytkownika."""
    buckets: dict[str, list[tuple[int, Component]]] = {}

    for comp in all_components:
        if not is_tile_visible(comp.folder_name, layout, normally_visible=normally_visible):
            continue
        entry = layout.entries.get(comp.folder_name)
        section = entry.section if entry else _default_section_for(comp.folder_name)
        sort_key = entry.sort_key if entry else 10_000 + comp.order
        buckets.setdefault(section, []).append((sort_key, comp))

    order = layout.section_order or section_titles(DEFAULT_SECTIONS)
    seen: set[str] = set()
    sections: list[tuple[str, list[Component]]] = []
    for title in order:
        seen.add(title)
        items = buckets.pop(title, [])
        if not items:
            continue
        comps = [c for _, c in sorted(items, key=lambda x: (x[0], x[1].name.lower()))]
        sections.append((title, comps))

    for title in sorted(buckets.keys(), key=lambda t: (t != SECTION_OTHER, t.lower())):
        items = buckets[title]
        if not items:
            continue
        comps = [c for _, c in sorted(items, key=lambda x: (x[0], x[1].name.lower()))]
        sections.append((title, comps))

    return sections
