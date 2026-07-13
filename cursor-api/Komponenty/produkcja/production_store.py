"""External persistence paths shared by all Produkcja entry points.

Mutable order state belongs to the user profile, not to the source checkout.
Reads prefer Local AppData and retain a read-only legacy fallback. Writes always
target Local AppData unless a caller explicitly overrides a module-level path.
"""

from __future__ import annotations

from pathlib import Path

from giclee_app.app_paths import data_path

_RELATIVE_DIR = "Komponenty/produkcja/dane"
LEGACY_DATA_DIR = Path(__file__).resolve().parent / "dane"


def _safe_filename(filename: str) -> str:
    name = str(filename).strip()
    if not name or Path(name).name != name or name in {".", ".."}:
        raise ValueError(f"Unsafe production data filename: {filename!r}")
    return name


def _store(filename: str):
    name = _safe_filename(filename)
    return data_path(
        f"{_RELATIVE_DIR}/{name}",
        legacy=LEGACY_DATA_DIR / name,
    )


def read_path(filename: str) -> Path:
    """Return the external-first path for a production data file."""

    return _store(filename).read_path()


def write_path(filename: str) -> Path:
    """Return the Local AppData destination for a production data file."""

    return _store(filename).write_path


def data_directory() -> Path:
    """Return the external production data directory without creating it."""

    return write_path(".directory-sentinel").parent


def orders_read_path() -> Path:
    return read_path("zamowienia.json")


def orders_write_path() -> Path:
    return write_path("zamowienia.json")


def sync_state_read_path() -> Path:
    return read_path("sync_state.json")


def sync_state_write_path() -> Path:
    return write_path("sync_state.json")


def archive_read_path(year: int) -> Path:
    return read_path(f"archive_{int(year)}.json")


def archive_write_path(year: int) -> Path:
    return write_path(f"archive_{int(year)}.json")


def archive_read_paths() -> list[Path]:
    """List external and legacy archives with external files taking precedence."""

    selected: dict[str, Path] = {}
    external_dir = data_directory()
    if external_dir.is_dir():
        for path in external_dir.glob("archive_*.json"):
            selected[path.name] = path

    if LEGACY_DATA_DIR.is_dir():
        for path in LEGACY_DATA_DIR.glob("archive_*.json"):
            selected.setdefault(path.name, path)

    return [selected[name] for name in sorted(selected)]


__all__ = [
    "LEGACY_DATA_DIR",
    "archive_read_path",
    "archive_read_paths",
    "archive_write_path",
    "data_directory",
    "orders_read_path",
    "orders_write_path",
    "read_path",
    "sync_state_read_path",
    "sync_state_write_path",
    "write_path",
]
