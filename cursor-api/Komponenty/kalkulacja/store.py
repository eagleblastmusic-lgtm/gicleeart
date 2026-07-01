"""Wczytywanie i zapis danych kalkulatora (JSON w data/)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"


def data_dir() -> Path:
    return _DATA_DIR


def _read(name: str) -> Any:
    path = _DATA_DIR / name
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write(name: str, payload: Any) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    (_DATA_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_materials() -> list[dict[str, Any]]:
    return _read("materials.json") or []


def save_materials(rows: list[dict[str, Any]]) -> None:
    _write("materials.json", rows)


def load_helpers() -> dict[str, dict[str, float | None]]:
    return _read("helpers.json") or {}


def load_price_table() -> list[dict[str, Any]]:
    return _read("price_table.json") or []


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
