"""Pomocnicze funkcje dla uruchomienia z PyInstaller (.exe).

Gdy aplikacja jest zamrozona, `sys.executable` wskazuje na GicleeApp.exe,
ktory **nie** obsluguje `python.exe -m Komponenty.xxx`. Komponenty uruchamiamy
osobnym interpreterem Pythona z PATH (lub ze zmiennej `GICLEE_PYTHON`).

Katalog roboczy dla subprocessow = katalog zawierajacy folder `Komponenty/`
(zwykle `sys._MEIPASS` po spakowaniu).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_bundle_root() -> Path:
    """Katalog projektu (cursor-api) widziany przez aplikacje.

    - Dev: folder nad `giclee_app/` (tam gdzie jest `Komponenty/`).
    - PyInstaller onefile/onedir: `sys._MEIPASS` (wypakowane pliki danych).
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    # giclee_app/runtime.py -> parents[1] = cursor-api
    return Path(__file__).resolve().parents[1]


def get_component_cwd() -> Path:
    """Working directory dla `python -m Komponenty.<x>`.

    Musi zawierac pakiet top-level `Komponenty/`.
    """
    return get_bundle_root()


def resolve_python_interpreter() -> tuple[list[str], str] | tuple[None, str]:
    """Zwraca argv-prefix do uruchomienia modulu (np. `['C:\\Python314\\python.exe']`).

    Gdy brak Pythona w PATH, zwraca (None, komunikat_bledu).
    """
    if not is_frozen():
        return [sys.executable], ""

    override = os.environ.get("GICLEE_PYTHON", "").strip().strip('"')
    if override:
        p = Path(override)
        if p.is_file():
            return [str(p.resolve())], ""
        return None, f"GICLEE_PYTHON wskazuje na nieistniejacy plik:\n{override}"

    # 1) python / python3 z PATH
    for name in ("python", "python3"):
        exe = shutil.which(name)
        if exe:
            return [exe], ""

    # 2) Windows: py -3
    py = shutil.which("py")
    if py:
        return [py, "-3"], ""

    return None, (
        "Nie znaleziono interpretera Pythona (python / py).\n\n"
        "Zainstaluj Pythona 3.11+ z python.org i zaznacz \"Add to PATH\",\n"
        "albo ustaw zmienna srodowiskowa GICLEE_PYTHON na pelna sciezke do python.exe"
    )
