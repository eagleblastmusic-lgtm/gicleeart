"""Testy InlineHostView — import, build_view, error states."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import Component
from giclee_app.ui.inline_host import InlineHostView, _short_error


def _make_comp(folder: str = "testinline") -> Component:
    return Component(
        folder_name=folder,
        package_path=Path(f"/fake/{folder}"),
        name="Test Inline",
        description="",
        mode="inline",
    )


def test_short_error_truncates() -> None:
    err = _short_error(ValueError("x" * 200))
    assert "ValueError" in err
    assert len(err) <= 140


def test_inline_host_source_no_forbidden_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "inline_host.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        for forbidden in (
            "giclee_app.launcher",
            "Komponenty.produkcja.orders_sync",
            "Komponenty._shared.backup",
        ):
            assert not (imp == forbidden or imp.startswith(forbidden + "."))


def test_inline_host_missing_build_view_shows_error() -> None:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    comp = _make_comp()
    mod = SimpleNamespace()
    opened = MagicMock()
    try:
        with patch("giclee_app.ui.inline_host.importlib.import_module", return_value=mod):
            host = InlineHostView(root, comp, on_back=lambda: None, on_opened=opened)
            root.update_idletasks()
            assert host.load_ok is False
            opened.assert_not_called()
    finally:
        root.destroy()


def test_inline_host_build_exception_no_opened() -> None:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    comp = _make_comp()

    def bad_builder(parent, on_back):  # noqa: ANN001
        raise RuntimeError("boom")

    mod = SimpleNamespace(build_view=bad_builder)
    opened = MagicMock()
    try:
        with patch("giclee_app.ui.inline_host.importlib.import_module", return_value=mod):
            host = InlineHostView(root, comp, on_back=lambda: None, on_opened=opened)
            root.update_idletasks()
            assert host.load_ok is False
            opened.assert_not_called()
    finally:
        root.destroy()


def test_inline_host_success_calls_on_opened() -> None:
    import customtkinter as ctk
    import tkinter as tk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    comp = _make_comp()

    def ok_builder(parent, on_back):  # noqa: ANN001
        frame = tk.Frame(parent)
        return frame

    mod = SimpleNamespace(build_view=ok_builder)
    opened = MagicMock()
    try:
        with patch("giclee_app.ui.inline_host.importlib.import_module", return_value=mod):
            host = InlineHostView(root, comp, on_back=lambda: None, on_opened=opened)
            root.update_idletasks()
            assert host.load_ok is True
            opened.assert_called_once_with(comp)
    finally:
        root.destroy()
