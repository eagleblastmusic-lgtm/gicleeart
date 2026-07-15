"""Kanoniczny composition root klasycznego launchera GicleeApp."""

from __future__ import annotations

from . import launcher as _launcher
from .dragdrop_category_launcher import DragDropCategoryGicleeApp


LauncherApp = DragDropCategoryGicleeApp


def main() -> None:
    """Uruchamia produkcyjny klasyczny launcher przez jawny factory root."""

    _launcher.main(app_factory=LauncherApp)


__all__ = ["LauncherApp", "main"]
