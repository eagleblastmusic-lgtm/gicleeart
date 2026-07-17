"""Kanoniczny composition root klasycznego launchera GicleeApp."""

from __future__ import annotations

from . import launcher as _launcher
from .cached_navigation_launcher import CachedNavigationGicleeApp


LauncherApp = CachedNavigationGicleeApp


def main() -> None:
    """Uruchamia produkcyjny klasyczny launcher przez jawny factory root."""

    _launcher.main(app_factory=LauncherApp)


__all__ = ["LauncherApp", "main"]
