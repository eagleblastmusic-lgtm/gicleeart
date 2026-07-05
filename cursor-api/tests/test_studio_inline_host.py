"""Testy InlineHostView — import, build_view, error states, F3.1 polish."""

from __future__ import annotations

import ast
import sys
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import Component
from giclee_app.ui.inline_host import (
    InlineHostView,
    _invoke_build_view,
    _sanitize_error_text,
    _short_error,
    _supports_on_open_component,
)


def _make_comp(folder: str = "testinline", **extras: object) -> Component:
    return Component(
        folder_name=folder,
        package_path=Path(f"/fake/{folder}"),
        name="Test Inline",
        description="",
        mode="inline",
        extras=dict(extras),
    )


def test_short_error_truncates() -> None:
    err = _short_error(ValueError("x" * 200))
    assert "ValueError" in err
    assert len(err) <= 140


def test_short_error_masks_secrets() -> None:
    err = _short_error(ValueError("token=abc"))
    assert "abc" not in err
    assert "ValueError" in err
    assert "redacted" in err.lower() or "token" in err.lower()


def test_sanitize_error_text_masks_authorization_bearer() -> None:
    out = _sanitize_error_text("Authorization: Bearer abc123")
    assert "abc123" not in out
    assert "redacted" in out.lower()


def test_sanitize_error_text_masks_bearer_only() -> None:
    out = _sanitize_error_text("Bearer abc123")
    assert "abc123" not in out
    assert "redacted" in out.lower()


def test_short_error_masks_authorization_bearer() -> None:
    err = _short_error(ValueError("Authorization: Bearer abc123"))
    assert "abc123" not in err
    assert "ValueError" in err


def test_short_error_masks_token_equals() -> None:
    err = _short_error(ValueError("token=abc123"))
    assert "abc123" not in err
    assert "ValueError" in err


def test_sanitize_error_text_masks_common_keys() -> None:
    raw = "failed secret=xyz password=123 api_key=foo"
    out = _sanitize_error_text(raw)
    assert "xyz" not in out
    assert "123" not in out
    assert "foo" not in out
    assert "redacted" in out


def test_supports_on_open_component_signature() -> None:
    def two_arg(parent, on_back):  # noqa: ANN001
        pass

    def three_kw(parent, on_back, on_open_component=None):  # noqa: ANN001
        pass

    def kwargs_builder(parent, on_back, **kwargs):  # noqa: ANN001
        pass

    assert _supports_on_open_component(two_arg) is False
    assert _supports_on_open_component(three_kw) is True
    assert _supports_on_open_component(kwargs_builder) is True


def test_invoke_build_view_two_arg() -> None:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    calls: list[int] = []

    def builder(parent, on_back):  # noqa: ANN001
        calls.append(2)
        return tk.Frame(parent)

    mount = tk.Frame(root)
    _invoke_build_view(builder, mount, lambda: None)
    assert calls == [2]
    root.destroy()


def test_invoke_build_view_three_kw() -> None:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    calls: list[str] = []

    def builder(parent, on_back, on_open_component=None):  # noqa: ANN001
        calls.append("3")
        return tk.Frame(parent)

    mount = tk.Frame(root)
    _invoke_build_view(builder, mount, lambda: None)
    assert calls == ["3"]
    root.destroy()


def test_invoke_build_view_kwargs() -> None:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()

    def builder(parent, on_back, **kwargs):  # noqa: ANN001
        assert "on_open_component" in kwargs
        return tk.Frame(parent)

    mount = tk.Frame(root)
    _invoke_build_view(builder, mount, lambda: None)
    root.destroy()


def test_inline_host_internal_typeerror_no_opened() -> None:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    comp = _make_comp()

    def bad_builder(parent, on_back):  # noqa: ANN001
        raise TypeError("inner type mismatch")

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

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    comp = _make_comp()

    def ok_builder(parent, on_back):  # noqa: ANN001
        return tk.Frame(parent)

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


def test_restore_geometry_only_when_inline_resized() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    restore_block = text.split("def _restore_window_geometry")[1].split("\n    def ")[0]
    assert "WindowDefault" not in restore_block
    assert "_geometry_before_inline" in restore_block
    apply_block = text.split("def _apply_inline_window_size")[1].split("\n    def ")[0]
    assert "_geometry_before_inline = self.geometry()" in apply_block
