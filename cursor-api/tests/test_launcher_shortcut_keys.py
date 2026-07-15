"""Testy neutralnego kontraktu klawiszy skrótów launchera."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from giclee_app.launcher_shortcut_keys import (
    normalize_shortcut_key,
    shortcut_virtual_key,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a", "a"),
        (" Z ", "z"),
        ("0", "0"),
        ("9", "9"),
        ("f1", "f1"),
        ("F12", "f12"),
        ("f01", "f1"),
        ("", None),
        (" ", None),
        ("f0", None),
        ("f13", None),
        ("ą", None),
        ("٧", None),
        ("f١", None),
        ("ctrl+a", None),
    ],
)
def test_normalize_shortcut_key(value: object, expected: str | None) -> None:
    assert normalize_shortcut_key(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a", ord("A")),
        ("Z", ord("Z")),
        ("0", ord("0")),
        ("9", ord("9")),
        ("f1", 0x70),
        ("F12", 0x7B),
        ("f01", 0x70),
        ("ą", None),
        ("٧", None),
        ("f١", None),
        ("f13", None),
    ],
)
def test_shortcut_virtual_key(value: object, expected: int | None) -> None:
    assert shortcut_virtual_key(value) == expected


def test_contract_module_has_no_platform_ui_or_io_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_shortcut_keys.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "tkinter" not in imports
    assert "ctypes" not in imports
    assert "os" not in imports
    assert "json" not in imports
    assert "pathlib" not in imports
    assert not any(name.startswith("Komponenty") for name in imports)
