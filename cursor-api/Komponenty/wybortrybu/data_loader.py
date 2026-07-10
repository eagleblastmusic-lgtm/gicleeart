"""Wczytywanie trybów pracy i kombinacji z plików JSON (schema v2)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_DATA_DIR = Path(__file__).resolve().parent / "data"

SHOPIFY_SNAPSHOT_MODE_ID = "analyst_shopify_snapshot"
FORMAL_FAMILIES: frozenset[str] = frozenset({"analyst", "shopify"})

CATEGORY_COLORS: dict[str, str] = {
    "Analyst": "#00897b",
    "Shopify": "#6d4c41",
    "AI Prompt": "#00796b",
    "Workflow": "#3949ab",
    "Legacy": "#5d4037",
    "UI": "#1e88e5",
    "Motion": "#7b1fa2",
    "Cursor": "#00897b",
    "GicleeApp": "#3949ab",
    "Performance": "#e65100",
    "Copy": "#c2185b",
    "Medical": "#5d4037",
}


@dataclass(frozen=True)
class ActivationProfile:
    id: str
    label: str
    command: str
    description: str = ""


@dataclass(frozen=True)
class Foundation:
    id: str
    order: int
    name: str
    source_file: str
    purpose: str
    aliases: tuple[str, ...]
    search_text: str

    @property
    def selectable(self) -> bool:
        return False


@dataclass(frozen=True)
class WorkMode:
    id: str
    order: int
    family: str
    selectable: bool
    name: str
    short_label: str
    category: str
    source_file: str
    aliases: tuple[str, ...]
    purpose: str
    focus: str
    when_to_use: str
    activation_profiles: tuple[ActivationProfile, ...]
    requires: tuple[str, ...]
    related_mode_ids: tuple[str, ...]
    distinction_note: str
    search_text: str

    @property
    def category_color(self) -> str:
        return CATEGORY_COLORS.get(self.category, "#546e7a")

    @property
    def default_profile(self) -> ActivationProfile:
        return self.activation_profiles[0]

    def profile(self, profile_id: str | None = None) -> ActivationProfile:
        if profile_id:
            for profile in self.activation_profiles:
                if profile.id == profile_id:
                    return profile
        return self.default_profile

    @property
    def is_formal(self) -> bool:
        return self.family in FORMAL_FAMILIES


@dataclass(frozen=True)
class Combination:
    id: str
    name: str
    mode_ids: tuple[str, ...]
    best_for: str
    delivers: str
    usage_example: str
    note: str


@dataclass(frozen=True)
class WorkModeCatalog:
    schema_version: int
    knowledge_pack: str
    catalog_source: str
    foundations: tuple[Foundation, ...]
    modes: tuple[WorkMode, ...]
    combinations: tuple[Combination, ...]
    by_id: dict[str, WorkMode]
    foundation_by_id: dict[str, Foundation]

    def mode(self, mode_id: str) -> WorkMode | None:
        return self.by_id.get(mode_id)

    def foundation(self, foundation_id: str) -> Foundation | None:
        return self.foundation_by_id.get(foundation_id)

    def modes_for_ids(self, mode_ids: list[str]) -> list[WorkMode]:
        out: list[WorkMode] = []
        for mode_id in mode_ids:
            mode = self.by_id.get(mode_id)
            if mode is not None:
                out.append(mode)
        return out

    def formal_modes(self) -> tuple[WorkMode, ...]:
        return tuple(m for m in self.modes if m.is_formal)

    def modes_by_family(self, family: str) -> tuple[WorkMode, ...]:
        return tuple(m for m in self.modes if m.family == family and m.selectable)


def data_dir() -> Path:
    return _DATA_DIR


def _norm(text: Any) -> str:
    return str(text or "").strip()


def _aliases(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(a).strip() for a in raw if str(a).strip())


def _profiles(raw: Any) -> tuple[ActivationProfile, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("Tryb wymaga co najmniej jednego activation_profile")
    out: list[ActivationProfile] = []
    seen: set[str] = set()
    for row in raw:
        if not isinstance(row, dict):
            continue
        pid = _norm(row.get("id"))
        if not pid or pid in seen:
            raise ValueError(f"Duplikat lub brak id profilu aktywacji: {row!r}")
        seen.add(pid)
        command = _norm(row.get("command"))
        if not command:
            raise ValueError(f"Profil {pid} wymaga pola command")
        out.append(
            ActivationProfile(
                id=pid,
                label=_norm(row.get("label")) or pid,
                command=command,
                description=_norm(row.get("description")),
            )
        )
    return tuple(out)


def _build_search_text(*parts: str) -> str:
    return " ".join(p for p in parts if p)


def _foundation_from_row(row: dict[str, Any]) -> Foundation:
    aliases = _aliases(row.get("aliases"))
    source_file = _norm(row.get("source_file"))
    name = _norm(row.get("name"))
    purpose = _norm(row.get("purpose"))
    return Foundation(
        id=_norm(row["id"]),
        order=int(row["order"]),
        name=name,
        source_file=source_file,
        purpose=purpose,
        aliases=aliases,
        search_text=_build_search_text(name, *aliases, purpose, source_file),
    )


def _mode_from_row(row: dict[str, Any]) -> WorkMode:
    aliases = _aliases(row.get("aliases"))
    profiles = _profiles(row.get("activation_profiles"))
    requires_raw = row.get("requires") or []
    related_raw = row.get("related_mode_ids") or []
    if not isinstance(requires_raw, list):
        requires_raw = []
    if not isinstance(related_raw, list):
        related_raw = []
    name = _norm(row["name"])
    short_label = _norm(row.get("short_label")) or name
    category = _norm(row["category"])
    source_file = _norm(row.get("source_file"))
    purpose = _norm(row["purpose"])
    focus = _norm(row["focus"])
    when_to_use = _norm(row["when_to_use"])
    distinction = _norm(row.get("distinction_note"))
    commands = " ".join(p.command for p in profiles)
    return WorkMode(
        id=_norm(row["id"]),
        order=int(row["order"]),
        family=_norm(row["family"]),
        selectable=bool(row.get("selectable", True)),
        name=name,
        short_label=short_label,
        category=category,
        source_file=source_file,
        aliases=aliases,
        purpose=purpose,
        focus=focus,
        when_to_use=when_to_use,
        activation_profiles=profiles,
        requires=tuple(str(r).strip() for r in requires_raw if str(r).strip()),
        related_mode_ids=tuple(str(r).strip() for r in related_raw if str(r).strip()),
        distinction_note=distinction,
        search_text=_build_search_text(
            name,
            short_label,
            *aliases,
            category,
            source_file,
            commands,
            purpose,
            focus,
            when_to_use,
            distinction,
        ),
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
    )


def _validate_catalog(
    foundations: tuple[Foundation, ...],
    modes: tuple[WorkMode, ...],
    combinations: tuple[Combination, ...],
) -> None:
    all_ids: dict[str, str] = {}
    for foundation in foundations:
        if foundation.id in all_ids:
            raise ValueError(f"Duplikat id: {foundation.id}")
        all_ids[foundation.id] = "foundation"
    for mode in modes:
        if mode.id in all_ids:
            raise ValueError(f"Duplikat id: {mode.id}")
        all_ids[mode.id] = "mode"

    mode_ids = {m.id for m in modes}
    for mode in modes:
        for req in mode.requires:
            if req not in mode_ids:
                raise ValueError(f"Tryb {mode.id}: nieznane requires -> {req}")
        for rel in mode.related_mode_ids:
            if rel not in mode_ids:
                raise ValueError(f"Tryb {mode.id}: nieznane related_mode_ids -> {rel}")

    formal = [m for m in modes if m.is_formal]
    if len(formal) != 17:
        raise ValueError(f"Oczekiwano 17 formalnych trybów, jest {len(formal)}")
    analyst_count = sum(1 for m in formal if m.family == "analyst")
    shopify_count = sum(1 for m in formal if m.family == "shopify")
    if analyst_count != 8 or shopify_count != 9:
        raise ValueError(
            f"Nieprawidłowy podział formalnych trybów: analyst={analyst_count}, shopify={shopify_count}"
        )

    for combo in combinations:
        if not combo.mode_ids:
            raise ValueError(f"Kombinacja {combo.id} nie ma trybów")
        for mid in combo.mode_ids:
            if mid not in mode_ids:
                raise ValueError(f"Kombinacja {combo.name}: nieznany tryb {mid}")


def load_catalog() -> WorkModeCatalog:
    modes_path = _DATA_DIR / "work_modes.json"
    combos_path = _DATA_DIR / "combinations.json"
    if not modes_path.is_file():
        raise FileNotFoundError(f"Brak pliku danych: {modes_path}")
    if not combos_path.is_file():
        raise FileNotFoundError(f"Brak pliku danych: {combos_path}")

    modes_data = json.loads(modes_path.read_text(encoding="utf-8"))
    combos_data = json.loads(combos_path.read_text(encoding="utf-8"))

    schema_version = int(modes_data.get("schema_version") or 0)
    if schema_version != 2:
        raise ValueError(f"Nieobsługiwana schema_version w work_modes.json: {schema_version}")

    combo_schema = int(combos_data.get("schema_version") or 0)
    if combo_schema != 2:
        raise ValueError(f"Nieobsługiwana schema_version w combinations.json: {combo_schema}")

    foundations = tuple(
        _foundation_from_row(row) for row in modes_data.get("foundations", [])
    )
    modes = tuple(_mode_from_row(row) for row in modes_data.get("modes", []))
    combinations = tuple(
        _combination_from_row(row) for row in combos_data.get("combinations", [])
    )

    _validate_catalog(foundations, modes, combinations)

    by_id = {mode.id: mode for mode in modes}
    foundation_by_id = {f.id: f for f in foundations}
    return WorkModeCatalog(
        schema_version=schema_version,
        knowledge_pack=_norm(modes_data.get("knowledge_pack")),
        catalog_source=_norm(modes_data.get("catalog_source")),
        foundations=foundations,
        modes=modes,
        combinations=combinations,
        by_id=by_id,
        foundation_by_id=foundation_by_id,
    )


def resolve_modes_with_dependencies(
    catalog: WorkModeCatalog,
    mode_ids: list[str],
    *,
    profile_map: dict[str, str] | None = None,
) -> tuple[list[WorkMode], dict[str, str]]:
    """Zwraca tryby posortowane według order z auto-zależnościami (Shopify Snapshot max 1×)."""
    profile_map = profile_map or {}
    selected: list[str] = []
    seen: set[str] = set()

    def _add(mode_id: str) -> None:
        if mode_id in seen:
            return
        mode = catalog.mode(mode_id)
        if mode is None:
            return
        seen.add(mode_id)
        for req in mode.requires:
            _add(req)
        if mode.family == "shopify" and mode.id != SHOPIFY_SNAPSHOT_MODE_ID:
            _add(SHOPIFY_SNAPSHOT_MODE_ID)
        selected.append(mode_id)

    for mode_id in mode_ids:
        _add(mode_id)

    order_index = {m.id: m.order for m in catalog.modes}
    selected.sort(key=lambda mid: order_index.get(mid, 999))
    modes = catalog.modes_for_ids(selected)
    resolved_profiles = {m.id: profile_map.get(m.id, m.default_profile.id) for m in modes}
    return modes, resolved_profiles


def filter_modes(
    catalog: WorkModeCatalog,
    *,
    query: str = "",
    category: str = "Wszystkie",
    family: str | None = None,
) -> list[WorkMode]:
    q = _norm(query).casefold()
    cat = _norm(category)
    out: list[WorkMode] = []
    for mode in catalog.modes:
        if not mode.selectable:
            continue
        if family and mode.family != family:
            continue
        if cat and cat != "Wszystkie" and mode.category != cat:
            continue
        if q:
            hay = mode.search_text.casefold()
            if q not in hay and q not in mode.name.casefold():
                continue
        out.append(mode)
    out.sort(key=lambda m: m.order)
    return out


def all_categories(catalog: WorkModeCatalog, *, family: str | None = None) -> list[str]:
    seen: dict[str, None] = {}
    for mode in catalog.modes:
        if not mode.selectable:
            continue
        if family and mode.family != family:
            continue
        seen.setdefault(mode.category, None)
    return ["Wszystkie", *sorted(seen.keys())]


FamilyFilter = Literal["analyst", "shopify", "workflow", "legacy"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("_", text.casefold().strip())
    return slug.strip("_")
