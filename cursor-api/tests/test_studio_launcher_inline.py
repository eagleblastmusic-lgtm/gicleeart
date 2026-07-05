"""Regresja lifecycle inline → hub w launcher_studio."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_return_from_inline_calls_show_hub_and_clears_stack() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    return_block = text.split("def _return_from_inline")[1].split("\n    def ")[0]
    assert "_show_hub(category)" in return_block
    assert "_inline_stack.clear()" in return_block
    assert "_destroy_inline_host" in return_block


def test_show_view_does_not_hide_target_before_on_show() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    show_view = text.split("def _show_view")[1].split("\n    def ")[0]
    assert "except_key=key" in show_view or "_hide_cached_views(except_key=" in show_view


@pytest.mark.skipif(
    not __import__("os").environ.get("DISPLAY") and sys.platform != "win32",
    reason="needs display",
)
def test_return_from_inline_restores_hub_tiles() -> None:
    import customtkinter as ctk

    from giclee_app.component_loader import Component
    from giclee_app.launcher_studio import GicleeAppStudio

    ctk.set_appearance_mode("dark")
    app = GicleeAppStudio()
    app.withdraw()

    hub_key = "hub:theme"
    app._show_hub("theme")
    hub = app._view_cache[hub_key]
    app.update_idletasks()
    app.update()

    comp = Component(
        folder_name="gicleeframe",
        package_path=Path("/fake/gicleeframe"),
        name="Giclée Frame",
        description="",
        mode="inline",
    )
    with patch.object(app, "_apply_inline_window_size"), patch(
        "giclee_app.ui.inline_host.importlib.import_module"
    ) as mock_import:
        mock_import.return_value = MagicMock(
            build_view=lambda parent, on_back: __import__("tkinter").Frame(parent)
        )
        app._show_inline_component(comp, "theme")

    assert app._inline_host is not None

    app._return_from_inline()
    deadline = __import__("time").time() + 5.0
    while not hub._cards_fully_built and __import__("time").time() < deadline:  # noqa: SLF001
        app.update_idletasks()
        app.update()

    assert app._inline_host is None
    assert app._inline_stack == []
    assert hub.winfo_ismapped()
    assert app._topbar._breadcrumb.cget("text") == "Strona / Motyw"  # noqa: SLF001
    assert app._status_var.get() == "Wrócono do huba"
    assert hub._cards_fully_built  # noqa: SLF001
    assert len(hub._cards) > 0  # noqa: SLF001

    app.destroy()
