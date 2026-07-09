"""Wczytywanie trybów pracy i kombinacji z plików JSON."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"

CATEGORY_COLORS: dict[str, str] = {
    "UI": "#1e88e5",
    "Motion": "#7b1fa2",
    "Cursor": "#00897b",
    "Shopify": "#6d4c41",
    "GicleeApp": "#3949ab",
    "Performance": "#e65100",
    "Copy": "#c2185b",
    "AI Prompt": "#00796b",
    "Medical": "#5d4037",
}


@dataclass(frozen=True)
class WorkMode:
    id: str
    number: int
    name: str
    aliases: tuple[str, ...]
    category: str
    purpose: str
    focus: str
    when_to_use: str
    sample_command: str
    simplest: str
    search_text: str

    @property
    def short_label(self) -> str:
        return self.aliases[0] if self.aliases else self.name

    @property
    def category_color(self) -> str:
        return CATEGORY_COLORS.get(self.category, "#546e7a")


@dataclass(frozen=True)
class Combination:
    id: str
    name: str
    mode_ids: tuple[str, ...]
    best_for: str
    delivers: str
    usage_example: str
    note: str
    prompt_short: str
    prompt_full: str


@dataclass(frozen=True)
class WorkModeCatalog:
    version: int
    source: str
    modes: tuple[WorkMode, ...]
    combinations: tuple[Combination, ...]
    by_id: dict[str, WorkMode]

    def mode(self, mode_id: str) -> WorkMode | None:
        return self.by_id.get(mode_id)

    def modes_for_ids(self, mode_ids: list[str]) -> list[WorkMode]:
        out: list[WorkMode] = []
        for mode_id in mode_ids:
            mode = self.by_id.get(mode_id)
            if mode is not None:
                out.append(mode)
        return out


def data_dir() -> Path:
    return _DATA_DIR


def _norm(text: Any) -> str:
    return str(text or "").strip()


def _mode_from_row(row: dict[str, Any]) -> WorkMode:
    aliases = row.get("aliases") or []
    if not isinstance(aliases, list):
        aliases = []
    alias_tuple = tuple(str(a).strip() for a in aliases if str(a).strip())
    return WorkMode(
        id=_norm(row["id"]),
        number=int(row["number"]),
        name=_norm(row["name"]),
        aliases=alias_tuple,
        category=_norm(row["category"]),
        purpose=_norm(row["purpose"]),
        focus=_norm(row["focus"]),
        when_to_use=_norm(row["when_to_use"]),
        sample_command=_norm(row["sample_command"]),
        simplest=_norm(row["simplest"]),
        search_text=_norm(row.get("search_text") or ""),
    )


def _combination_from_row(row: dict[str, Any]) -> Combination:
    mode_ids = row.get("mode_ids") or []
    if not isinstance(mode_ids, list):
        mode_ids = []
    return Combination(
        id=_norm(row["id"]),
        name=_norm(row["name"]),
        mode_ids=tuple(str(m).strip() for m in mode_ids if str(m).strip()),
        best_for=_norm(row["best_for"]),
        delivers=_norm(row["delivers"]),
        usage_example=_norm(row["usage_example"]),
        note=_norm(row["note"]),
        prompt_short=_norm(row["prompt_short"]),
        prompt_full=_norm(row["prompt_full"]),
    )


def load_catalog() -> WorkModeCatalog:
    modes_path = _DATA_DIR / "work_modes.json"
    combos_path = _DATA_DIR / "combinations.json"
    if not modes_path.is_file():
        raise FileNotFoundError(f"Brak pliku danych: {modes_path}")
    if not combos_path.is_file():
        raise FileNotFoundError(f"Brak pliku danych: {combos_path}")

    modes_data = json.loads(modes_path.read_text(encoding="utf-8"))
    combos_data = json.loads(combos_path.read_text(encoding="utf-8"))

    modes = tuple(_mode_from_row(row) for row in modes_data.get("modes", []))
    by_id = {mode.id: mode for mode in modes}
    combinations = tuple(
        _combination_from_row(row) for row in combos_data.get("combinations", [])
    )
    return WorkModeCatalog(
        version=int(modes_data.get("version") or 1),
        source=_norm(modes_data.get("source")),
        modes=modes,
        combinations=combinations,
        by_id=by_id,
    )


def filter_modes(
    catalog: WorkModeCatalog,
    *,
    query: str = "",
    category: str = "Wszystkie",
) -> list[WorkMode]:
    q = _norm(query).casefold()
    cat = _norm(category)
    out: list[WorkMode] = []
    for mode in catalog.modes:
        if cat and cat != "Wszystkie" and mode.category != cat:
            continue
        if q:
            hay = mode.search_text.casefold()
            if q not in hay and q not in mode.name.casefold():
                continue
        out.append(mode)
    return out


def all_categories(catalog: WorkModeCatalog) -> list[str]:
    seen: dict[str, None] = {}
    for mode in catalog.modes:
        seen.setdefault(mode.category, None)
    return ["Wszystkie", *sorted(seen.keys())]


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("_", text.casefold().strip())
    return slug.strip("_")
