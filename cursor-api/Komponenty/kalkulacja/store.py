"""Wczytywanie i zapis danych kalkulatora poza repozytorium."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import AppPath, atomic_write_text, config_path, data_path

_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_DATA_DIR = _LEGACY_DATA_DIR

_DATA_FILES = {
    "materials.json": data_path(
        "Komponenty/kalkulacja/data/materials.json",
        legacy=_LEGACY_DATA_DIR / "materials.json",
    ),
    "helpers.json": data_path(
        "Komponenty/kalkulacja/data/helpers.json",
        legacy=_LEGACY_DATA_DIR / "helpers.json",
    ),
    "price_table.json": data_path(
        "Komponenty/kalkulacja/data/price_table.json",
        legacy=_LEGACY_DATA_DIR / "price_table.json",
    ),
    "cost_lines.json": data_path(
        "Komponenty/kalkulacja/data/cost_lines.json",
        legacy=_LEGACY_DATA_DIR / "cost_lines.json",
    ),
    "sales_mix.json": data_path(
        "Komponenty/kalkulacja/data/sales_mix.json",
        legacy=_LEGACY_DATA_DIR / "sales_mix.json",
    ),
    "settings.json": config_path(
        "Komponenty/kalkulacja/data/settings.json",
        legacy=_LEGACY_DATA_DIR / "settings.json",
    ),
    "wood_defaults.json": config_path(
        "Komponenty/kalkulacja/data/wood_defaults.json",
        legacy=_LEGACY_DATA_DIR / "wood_defaults.json",
    ),
}


def _spec(name: str) -> AppPath:
    try:
        return _DATA_FILES[name]
    except KeyError as exc:
        raise ValueError(f"Nieznany plik kalkulatora: {name}") from exc


def _read_path(name: str) -> Path:
    if Path(_DATA_DIR) != _LEGACY_DATA_DIR:
        return Path(_DATA_DIR) / name
    return _spec(name).read_path()


def _write_path(name: str) -> Path:
    if Path(_DATA_DIR) != _LEGACY_DATA_DIR:
        return Path(_DATA_DIR) / name
    return _spec(name).write_path


def data_dir() -> Path:
    """Zwraca zewnętrzny katalog danych kalkulatora.

    Ustawienia mają osobny katalog roaming/config i powinny być zapisywane
    przez funkcje ``save_*`` zamiast przez bezpośrednie łączenie ścieżek.
    """

    if Path(_DATA_DIR) != _LEGACY_DATA_DIR:
        return Path(_DATA_DIR)
    return _spec("materials.json").write_path.parent


def _read(name: str) -> Any:
    path = _read_path(name)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write(name: str, payload: Any) -> None:
    atomic_write_text(
        _write_path(name),
        json.dumps(payload, ensure_ascii=False, indent=2),
    )


def load_materials() -> list[dict[str, Any]]:
    return _read("materials.json") or []


def save_materials(rows: list[dict[str, Any]]) -> None:
    _write("materials.json", rows)


def load_helpers() -> dict[str, dict[str, float | None]]:
    return _read("helpers.json") or {}


def save_helpers(rows: dict[str, dict[str, float | None]]) -> None:
    _write("helpers.json", rows)


def load_price_table() -> list[dict[str, Any]]:
    return _read("price_table.json") or []


def save_price_table(rows: list[dict[str, Any]]) -> None:
    _write("price_table.json", rows)


def load_cost_lines() -> list[dict[str, Any]]:
    return _read("cost_lines.json") or []


def save_cost_lines(rows: list[dict[str, Any]]) -> None:
    _write("cost_lines.json", rows)


def load_settings() -> dict[str, Any]:
    return _read("settings.json") or {
        "profile": "20X20",
        "frame_type": "STANDARDOWA",
        "default_markup_pct": 250,
        "default_production_minutes": 45,
        "wood_origin": "stolarz24",
        "frames_per_day": 1.0,
        "frames_per_day_mode": "manual",
        "work_hours_per_day": 8.0,
        "work_days_per_month": 22.0,
        "variant_pricing": {},
        "variant_production_minutes": {},
    }


def save_settings(settings: dict[str, Any]) -> None:
    _write("settings.json", settings)


def load_sales_mix() -> list[dict[str, Any]]:
    from .calculator import normalize_sales_mix

    return normalize_sales_mix(_read("sales_mix.json") or [])


def save_sales_mix(rows: list[dict[str, Any]]) -> None:
    from .calculator import sales_mix_for_store

    _write("sales_mix.json", sales_mix_for_store(rows))


def load_wood_defaults() -> dict[str, Any]:
    return _read("wood_defaults.json") or {
        "price_per_meter": 7.5,
        "profile": "20X20",
        "species": "SOSNA",
        "format": "A4",
        "shipping": 25,
        "max_batch": 30,
    }


def save_wood_defaults(payload: dict[str, Any]) -> None:
    _write("wood_defaults.json", payload)
