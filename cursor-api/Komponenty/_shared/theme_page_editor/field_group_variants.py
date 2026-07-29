"""Trwała biblioteka nazwanych wariantów dla grup pól edytora."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any


_FORMAT_VERSION = 1


def _empty_library() -> dict[str, Any]:
    return {"version": _FORMAT_VERSION, "variants": []}


def _normalize_values(
    values: dict[str, Any],
    controlled_field_ids: tuple[str, ...],
) -> dict[str, Any]:
    allowed = set(controlled_field_ids)
    normalized = {
        str(key): value
        for key, value in values.items()
        if str(key) in allowed
    }
    # Warianty muszą pozostać prostym JSON-em, niezależnym od obiektów Tk.
    return json.loads(json.dumps(normalized, ensure_ascii=False))


def load_variant_library(
    path: Path,
    *,
    controlled_field_ids: tuple[str, ...],
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    rows = payload.get("variants") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []

    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        variant_id = str(row.get("id") or "").strip()
        name = str(row.get("name") or "").strip()
        values = row.get("values")
        folded = name.casefold()
        if (
            not variant_id
            or not name
            or not isinstance(values, dict)
            or variant_id in seen_ids
            or folded in seen_names
        ):
            continue
        seen_ids.add(variant_id)
        seen_names.add(folded)
        result.append(
            {
                "id": variant_id,
                "name": name,
                "values": _normalize_values(values, controlled_field_ids),
            }
        )
    return result


def save_variant_library(path: Path, variants: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": _FORMAT_VERSION, "variants": variants}
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}-",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def create_library_variant(
    path: Path,
    *,
    name: str,
    values: dict[str, Any],
    controlled_field_ids: tuple[str, ...],
) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Nazwa wariantu nie może być pusta.")
    variants = load_variant_library(
        path,
        controlled_field_ids=controlled_field_ids,
    )
    if any(row["name"].casefold() == clean_name.casefold() for row in variants):
        raise ValueError(f"Wariant «{clean_name}» już istnieje.")
    row = {
        "id": uuid.uuid4().hex,
        "name": clean_name,
        "values": _normalize_values(values, controlled_field_ids),
    }
    variants.append(row)
    save_variant_library(path, variants)
    return row


def update_library_variant(
    path: Path,
    *,
    variant_id: str,
    values: dict[str, Any],
    controlled_field_ids: tuple[str, ...],
) -> dict[str, Any]:
    variants = load_variant_library(
        path,
        controlled_field_ids=controlled_field_ids,
    )
    for row in variants:
        if row["id"] == variant_id:
            row["values"] = _normalize_values(values, controlled_field_ids)
            save_variant_library(path, variants)
            return row
    raise ValueError("Wybrany wariant już nie istnieje.")


def rename_library_variant(
    path: Path,
    *,
    variant_id: str,
    name: str,
    controlled_field_ids: tuple[str, ...],
) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Nazwa wariantu nie może być pusta.")
    variants = load_variant_library(
        path,
        controlled_field_ids=controlled_field_ids,
    )
    if any(
        row["id"] != variant_id
        and row["name"].casefold() == clean_name.casefold()
        for row in variants
    ):
        raise ValueError(f"Wariant «{clean_name}» już istnieje.")
    for row in variants:
        if row["id"] == variant_id:
            row["name"] = clean_name
            save_variant_library(path, variants)
            return row
    raise ValueError("Wybrany wariant już nie istnieje.")


def delete_library_variant(
    path: Path,
    *,
    variant_id: str,
    controlled_field_ids: tuple[str, ...],
) -> None:
    variants = load_variant_library(
        path,
        controlled_field_ids=controlled_field_ids,
    )
    remaining = [row for row in variants if row["id"] != variant_id]
    if len(remaining) == len(variants):
        raise ValueError("Wybrany wariant już nie istnieje.")
    save_variant_library(path, remaining)


__all__ = [
    "create_library_variant",
    "delete_library_variant",
    "load_variant_library",
    "rename_library_variant",
    "save_variant_library",
    "update_library_variant",
]
