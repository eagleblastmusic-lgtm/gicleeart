"""External component logs shared by the classic launcher and Studio delegate."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from giclee_app.app_paths import log_path

_LOG_RELATIVE_DIR = "components"
LEGACY_COMPONENT_LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
DEFAULT_COMPONENT_LOGS_DIR = log_path(
    f"{_LOG_RELATIVE_DIR}/component.log",
).write_path.parent

_WINDOWS_INVALID_FILENAME_CHARS = frozenset('<>:"/\\|?*')
_WINDOWS_RESERVED_FILENAME_STEMS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)


def _filename(folder_name: str) -> str:
    """Return a portable log filename for one component directory name."""

    if not isinstance(folder_name, str):
        raise ValueError(f"Unsafe component folder name: {folder_name!r}")

    name = folder_name.strip()
    windows_path = PureWindowsPath(name)
    if (
        not name
        or name in {".", ".."}
        or PurePosixPath(name).name != name
        or windows_path.name != name
        or any(ord(char) < 32 for char in name)
        or any(char in _WINDOWS_INVALID_FILENAME_CHARS for char in name)
        or name.endswith(".")
        or name.split(".", 1)[0].upper() in _WINDOWS_RESERVED_FILENAME_STEMS
    ):
        raise ValueError(f"Unsafe component folder name: {folder_name!r}")

    return f"{name}.log"


def _store(folder_name: str):
    filename = _filename(folder_name)
    return log_path(
        f"{_LOG_RELATIVE_DIR}/{filename}",
        legacy=LEGACY_COMPONENT_LOGS_DIR / filename,
    )


def component_log_read_path(
    folder_name: str,
    *,
    logs_dir: Path | None = None,
) -> Path:
    """Return external-first read path without creating directories."""

    current = DEFAULT_COMPONENT_LOGS_DIR if logs_dir is None else Path(logs_dir)
    if current != DEFAULT_COMPONENT_LOGS_DIR:
        return current / _filename(folder_name)
    return _store(folder_name).read_path()


def component_log_write_path(
    folder_name: str,
    *,
    logs_dir: Path | None = None,
) -> Path:
    """Return append/truncate path, seeding legacy history once when needed."""

    current = DEFAULT_COMPONENT_LOGS_DIR if logs_dir is None else Path(logs_dir)
    if current != DEFAULT_COMPONENT_LOGS_DIR:
        current.mkdir(parents=True, exist_ok=True)
        return current / _filename(folder_name)
    return _store(folder_name).seed_from_legacy()


__all__ = [
    "DEFAULT_COMPONENT_LOGS_DIR",
    "LEGACY_COMPONENT_LOGS_DIR",
    "component_log_read_path",
    "component_log_write_path",
]
