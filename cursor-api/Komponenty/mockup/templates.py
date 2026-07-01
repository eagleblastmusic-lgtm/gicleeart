"""Wczytywanie szablonow mockupow (ramki + pole A4)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DATA_FILE = Path(__file__).resolve().parent / "data" / "templates.json"

MOCKUP_ALL_VARIANTS_LABEL = "Wszystkie warianty"


def mockup_set_choices(sets: list["MockupSet"]) -> list[str]:
    if not sets:
        return []
    return [MOCKUP_ALL_VARIANTS_LABEL] + [s.name for s in sets]


def resolve_mockup_sets(sets: list["MockupSet"], choice: str) -> list["MockupSet"]:
    name = (choice or "").strip()
    if not sets:
        return []
    if name == MOCKUP_ALL_VARIANTS_LABEL or not name:
        return list(sets)
    for s in sets:
        if s.name == name:
            return [s]
    return list(sets)


@dataclass(frozen=True)
class MockupTemplate:
    id: str
    name: str
    path: Path
    orientation: str  # portrait | landscape
    slot: tuple[int, int, int, int]  # x, y, w, h


@dataclass(frozen=True)
class MockupSet:
    id: str
    name: str
    name_suffix: str  # np. CZB, CZCZ — dopisywane po (mockup) w nazwie pliku
    templates: tuple[MockupTemplate, ...]


def _load_raw() -> dict:
    if not DATA_FILE.is_file():
        return {"sets": []}
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def list_mockup_sets() -> list[MockupSet]:
    raw = _load_raw()
    out: list[MockupSet] = []
    for s in raw.get("sets") or []:
        templates: list[MockupTemplate] = []
        for t in s.get("templates") or []:
            fname = str(t.get("file") or "").strip()
            if not fname:
                continue
            path = ASSETS_DIR / fname
            slot_raw = t.get("slot") or [0, 0, 0, 0]
            slot = tuple(int(v) for v in slot_raw[:4])  # type: ignore[assignment]
            templates.append(
                MockupTemplate(
                    id=str(t.get("id") or fname),
                    name=str(t.get("name") or fname),
                    path=path,
                    orientation=str(t.get("orientation") or "portrait"),
                    slot=slot,  # type: ignore[arg-type]
                )
            )
        if templates:
            out.append(
                MockupSet(
                    id=str(s.get("id") or "set"),
                    name=str(s.get("name") or "Mockup"),
                    name_suffix=str(s.get("name_suffix") or "").strip().upper(),
                    templates=tuple(templates),
                )
            )
    return out


def template_for_orientation(
    mockup_set: MockupSet,
    *,
    width: int,
    height: int,
) -> MockupTemplate:
    """Wybiera szablon pion/poziom wg proporcji obrazu."""
    if width <= 0 or height <= 0:
        raise ValueError("Nieprawidlowy rozmiar obrazu.")
    want = "landscape" if width >= height else "portrait"
    for tpl in mockup_set.templates:
        if tpl.orientation == want:
            return tpl
    return mockup_set.templates[0]
