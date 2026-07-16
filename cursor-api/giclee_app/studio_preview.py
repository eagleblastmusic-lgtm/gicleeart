"""Entrypoint GicleeApp Studio Preview.

Uruchomienie (z cursor-api/):
    pip install -r requirements-dev.txt
    python -m giclee_app.studio_preview

Klasyczny launcher (bez zmian):
    python -m giclee_app
"""

from __future__ import annotations

import sys


def main() -> None:
    try:
        import customtkinter as ctk  # noqa: F401
    except ImportError:
        print(
            "Brak pakietu customtkinter.\n"
            "Zainstaluj zależności dev: pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    import customtkinter as ctk

    ctk.set_appearance_mode("dark")

    # Spójna paleta Studio (dark premium + złoty akcent) zamiast domyślnego
    # niebieskiego "dark-blue" — widgety bez jawnych kolorów dziedziczą Studio look.
    from pathlib import Path

    _theme_json = Path(__file__).resolve().parent / "ui" / "studio_ctk_theme.json"
    if _theme_json.is_file():
        ctk.set_default_color_theme(str(_theme_json))
    else:
        ctk.set_default_color_theme("dark-blue")

    from giclee_app.app_profile import STUDIO_PREVIEW_PROFILE
    from giclee_app.launcher_studio import GicleeAppStudio

    app = GicleeAppStudio(profile=STUDIO_PREVIEW_PROFILE)
    app.mainloop()


if __name__ == "__main__":
    main()
