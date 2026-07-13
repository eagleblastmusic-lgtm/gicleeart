"""Bezpieczne domyślne ścieżki workspace komponentu Print Optimize.

Własne zdjęcia testowe, pobrane pary Whitewall i raporty kalibracji są
workspace'em użytkownika. Domyślny workspace należy do Local AppData, a
historyczne katalogi w checkoutcie pozostają nietknięte i nie są automatycznie
migrowane ani łączone z nową lokalizacją.
"""

from __future__ import annotations

from pathlib import Path

from giclee_app.app_paths import data_path

COMPONENT_DIR = Path(__file__).resolve().parent
DATA_DIR = COMPONENT_DIR / "data"

_LEGACY_TEST_PHOTOS_DIR = DATA_DIR / "test_photos"
_LEGACY_WW_PAIRS_DIR = DATA_DIR / "ww_pairs"
_RUNTIME_ROOT = "Komponenty/print_optimize/data"


def _runtime_default(leaf: str, *, legacy: Path) -> Path:
    return data_path(f"{_RUNTIME_ROOT}/{leaf}", legacy=legacy).write_path


_DEFAULT_TEST_PHOTOS_DIR = _runtime_default("test_photos", legacy=_LEGACY_TEST_PHOTOS_DIR)
_DEFAULT_WW_PAIRS_DIR = _runtime_default("ww_pairs", legacy=_LEGACY_WW_PAIRS_DIR)

# Publiczne stałe pozostają kompatybilnymi punktami override dla testów i
# narzędzi. Ich wartości domyślne są już poza checkoutem.
TEST_PHOTOS_DIR = _DEFAULT_TEST_PHOTOS_DIR
WW_PAIRS_DIR = _DEFAULT_WW_PAIRS_DIR

_DIRECTORY_CONSTANTS = {
    "TEST_PHOTOS_DIR": (
        "TEST_PHOTOS_DIR",
        "_DEFAULT_TEST_PHOTOS_DIR",
        "_LEGACY_TEST_PHOTOS_DIR",
        "test_photos",
    ),
    "WW_PAIRS_DIR": (
        "WW_PAIRS_DIR",
        "_DEFAULT_WW_PAIRS_DIR",
        "_LEGACY_WW_PAIRS_DIR",
        "ww_pairs",
    ),
}


def _explicit_directory_override(
    constant_name: str,
    *,
    for_write: bool,
) -> Path | None:
    """Zwróć bieżący jawny override katalogu, jeżeli jest aktywny."""

    name = str(constant_name).strip()
    try:
        current_name, default_name, _legacy_name, _leaf = _DIRECTORY_CONSTANTS[name]
    except KeyError as exc:
        raise ValueError(f"Niebezpieczna stała katalogu Print Optimize: {constant_name!r}") from exc

    try:
        current = Path(globals()[current_name])
        default = Path(globals()[default_name])
    except KeyError as exc:  # pragma: no cover - chronione statyczną mapą
        raise RuntimeError(f"Niepełne mapowanie katalogu Print Optimize: {name}") from exc

    if current == default:
        return None
    if for_write:
        current.mkdir(parents=True, exist_ok=True)
    return current


def _workspace_dir(constant_name: str, *, for_write: bool) -> Path:
    override = _explicit_directory_override(constant_name, for_write=for_write)
    if override is not None:
        return override

    _current_name, _default_name, legacy_name, leaf = _DIRECTORY_CONSTANTS[constant_name]
    path = _runtime_default(leaf, legacy=Path(globals()[legacy_name]))
    if for_write:
        path.mkdir(parents=True, exist_ok=True)
    return path


def test_photos_dir(*, for_write: bool = False) -> Path:
    """Zwróć katalog własnych zdjęć testowych bez automatycznej migracji legacy."""

    return _workspace_dir("TEST_PHOTOS_DIR", for_write=for_write)


def ww_pairs_dir(*, for_write: bool = False) -> Path:
    """Zwróć katalog par Whitewall i raportów kalibracji."""

    return _workspace_dir("WW_PAIRS_DIR", for_write=for_write)


def ensure_data_dirs() -> None:
    """Utwórz wyłącznie aktywne, zapisywalne katalogi workspace."""

    test_photos_dir(for_write=True)
    ww_pairs_dir(for_write=True)


__all__ = [
    "COMPONENT_DIR",
    "DATA_DIR",
    "TEST_PHOTOS_DIR",
    "WW_PAIRS_DIR",
    "ensure_data_dirs",
    "test_photos_dir",
    "ww_pairs_dir",
]
