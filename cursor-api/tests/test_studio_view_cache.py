"""Testy view cache — reuse dashboard i hubów bez destroy/create."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.launcher_studio import GicleeAppStudio


def _studio_app() -> GicleeAppStudio:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    app = GicleeAppStudio()
    app.withdraw()
    app.update_idletasks()
    app.update()
    return app


def _flush_view_mounts(app: GicleeAppStudio, *, key: str | None = None) -> None:
    import time

    deadline = time.time() + 5.0
    while time.time() < deadline:
        app.update_idletasks()
        app.update()
        if key is None or key in app._view_cache:
            return
    if key is not None and key not in app._view_cache:
        raise AssertionError(f"View {key!r} not mounted after deferred factory")


def test_view_cache_reuses_dashboard() -> None:
    app = _studio_app()
    try:
        app._show_dashboard()
        first = app._view_cache["dashboard"]
        app._show_hub("products")
        app._show_dashboard()
        second = app._view_cache["dashboard"]
        assert first is second
    finally:
        app.destroy()


def test_view_cache_reuses_hub_per_category() -> None:
    app = _studio_app()
    try:
        app._show_hub("products")
        _flush_view_mounts(app, key="hub:products")
        first = app._view_cache["hub:products"]
        app._show_hub("theme")
        _flush_view_mounts(app, key="hub:theme")
        app._show_hub("products")
        second = app._view_cache["hub:products"]
        assert first is second
    finally:
        app.destroy()


def test_launcher_has_view_cache_not_clear_content_on_nav() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    assert "_view_cache" in text
    assert "_show_view" in text
    assert "grid_remove" in text
    assert "_clear_content" not in text
