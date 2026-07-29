from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from .field_group_variants import (
    create_library_variant,
    delete_library_variant,
    load_variant_library,
    rename_library_variant,
    update_library_variant,
)


FIELDS = ("lerp", "wheel", "overscroll")


def test_named_variants_full_lifecycle() -> None:
    with tempfile.TemporaryDirectory(
        prefix="lenis-variants-",
        dir=Path(__file__).resolve().parent,
    ) as temporary:
        path = Path(temporary) / "lenis-scroll-variants.json"
        first = create_library_variant(
            path,
            name="Miękki",
            values={"lerp": 0.12, "wheel": 0.9, "overscroll": True, "ignored": 1},
            controlled_field_ids=FIELDS,
        )
        second = create_library_variant(
            path,
            name="Szybki",
            values={"lerp": 0.35, "wheel": 1.1, "overscroll": False},
            controlled_field_ids=FIELDS,
        )

        rows = load_variant_library(path, controlled_field_ids=FIELDS)
        assert [row["name"] for row in rows] == ["Miękki", "Szybki"]
        assert "ignored" not in rows[0]["values"]

        updated = update_library_variant(
            path,
            variant_id=first["id"],
            values={"lerp": 0.18, "wheel": 0.95, "overscroll": True},
            controlled_field_ids=FIELDS,
        )
        assert updated["values"]["lerp"] == 0.18

        renamed = rename_library_variant(
            path,
            variant_id=second["id"],
            name="Dynamiczny",
            controlled_field_ids=FIELDS,
        )
        assert renamed["name"] == "Dynamiczny"

        delete_library_variant(
            path,
            variant_id=first["id"],
            controlled_field_ids=FIELDS,
        )
        rows = load_variant_library(path, controlled_field_ids=FIELDS)
        assert [(row["id"], row["name"]) for row in rows] == [
            (second["id"], "Dynamiczny")
        ]
        assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1


def test_variant_names_are_unique_case_insensitively() -> None:
    with tempfile.TemporaryDirectory(
        prefix="lenis-variants-",
        dir=Path(__file__).resolve().parent,
    ) as temporary:
        path = Path(temporary) / "lenis-scroll-variants.json"
        create_library_variant(
            path,
            name="Galeria",
            values={"lerp": 0.2},
            controlled_field_ids=FIELDS,
        )
        with pytest.raises(ValueError, match="już istnieje"):
            create_library_variant(
                path,
                name="galeria",
                values={"lerp": 0.3},
                controlled_field_ids=FIELDS,
            )
