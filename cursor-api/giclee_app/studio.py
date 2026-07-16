"""Entrypoint produkcyjnego profilu Giclée Studio.

Uruchomienie (z cursor-api/):
    pip install -r requirements-dev.txt
    python -m giclee_app.studio

Profil produkcyjny używa osobnego namespace stanu/logów i dopuszcza wyłącznie
komponenty dostępne dla `studio` w kanale stabilności `stable`.
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

    from pathlib import Path

    theme_json = Path(__file__).resolve().parent / "ui" / "studio_ctk_theme.json"
    if theme_json.is_file():
        ctk.set_default_color_theme(str(theme_json))
    else:
        ctk.set_default_color_theme("dark-blue")

    from giclee_app.app_profile import STUDIO_PROFILE, app_profile_context

    with app_profile_context(STUDIO_PROFILE):
        from giclee_app.launcher_studio import GicleeAppStudio

        app = GicleeAppStudio(profile=STUDIO_PROFILE)
        app.mainloop()


if __name__ == "__main__":
    main()
