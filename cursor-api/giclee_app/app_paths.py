"""External runtime paths for GicleeApp.

Runtime, private and mutable configuration files must not be written inside the
source checkout. During Stage 1E reads remain backward compatible: the
external AppData location wins, while the legacy repository path is consulted
only when the external file does not exist. All writes target AppData.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

APP_VENDOR = "GicleeArt"
APP_NAME = "GicleeApp"

Bucket = Literal["data", "config", "cache", "logs", "backups"]

_LOCAL_ROOT_ENV = "GICLEEAPP_LOCAL_ROOT"
_ROAMING_ROOT_ENV = "GICLEEAPP_ROAMING_ROOT"


def _normalized_relative(value: str | PurePosixPath) -> Path:
    raw = str(value).replace("\\", "/").strip().lstrip("/")
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"Unsafe runtime relative path: {value!r}")
    return Path(*parts)


def _default_windows_root(env_name: str, fallback_leaf: str) -> Path:
    configured = os.environ.get(env_name, "").strip()
    if configured:
        return Path(configured).expanduser()

    os_root_name = "LOCALAPPDATA" if env_name == _LOCAL_ROOT_ENV else "APPDATA"
    os_root = os.environ.get(os_root_name, "").strip()
    if os_root:
        return Path(os_root) / APP_VENDOR / APP_NAME

    # Non-Windows and stripped test environments still need a deterministic,
    # user-owned location outside the repository.
    return Path.home() / ".gicleeart" / APP_NAME / fallback_leaf


def local_root() -> Path:
    """Return the full Local AppData root for GicleeApp."""

    return _default_windows_root(_LOCAL_ROOT_ENV, "local")


def roaming_root() -> Path:
    """Return the full Roaming AppData root for GicleeApp."""

    return _default_windows_root(_ROAMING_ROOT_ENV, "roaming")


def bucket_root(bucket: Bucket) -> Path:
    if bucket == "config":
        return roaming_root() / "config"
    if bucket == "cache":
        # The accepted migration manifest stores cache-class files in the
        # Local AppData data bucket. Keep runtime resolution byte-for-byte
        # aligned with that destination contract.
        return local_root() / "data"
    return local_root() / bucket


@dataclass(frozen=True)
class AppPath:
    """A mutable application path with an optional read-only legacy fallback."""

    relative: str
    bucket: Bucket
    legacy_path: Path | None = None

    @property
    def write_path(self) -> Path:
        return bucket_root(self.bucket) / _normalized_relative(self.relative)

    def read_path(self) -> Path:
        """Prefer AppData; use the legacy source-tree file only when necessary."""

        external = self.write_path
        if external.exists():
            return external
        if self.legacy_path is not None and self.legacy_path.exists():
            return self.legacy_path
        return external

    def ensure_parent(self) -> Path:
        path = self.write_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def seed_from_legacy(self) -> Path:
        """Copy an existing legacy file once, without deleting the source.

        This is intended for append-only stores. Normal JSON stores should load
        through :meth:`read_path` and write the complete state to
        :attr:`write_path`.
        """

        target = self.write_path
        if target.exists():
            return target
        legacy = self.legacy_path
        if legacy is None or not legacy.is_file():
            return self.ensure_parent()
        atomic_write_bytes(target, legacy.read_bytes())
        return target


def data_path(relative: str, *, legacy: Path | None = None) -> AppPath:
    return AppPath(relative=relative, bucket="data", legacy_path=legacy)


def config_path(relative: str, *, legacy: Path | None = None) -> AppPath:
    return AppPath(relative=relative, bucket="config", legacy_path=legacy)


def cache_path(relative: str, *, legacy: Path | None = None) -> AppPath:
    return AppPath(relative=relative, bucket="cache", legacy_path=legacy)


def log_path(relative: str, *, legacy: Path | None = None) -> AppPath:
    return AppPath(relative=relative, bucket="logs", legacy_path=legacy)


def backup_path(relative: str, *, legacy: Path | None = None) -> AppPath:
    return AppPath(relative=relative, bucket="backups", legacy_path=legacy)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically replace *path* with bytes outside any legacy location."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Atomically replace *path* without ever writing to a legacy location."""

    atomic_write_bytes(path, text.encode(encoding))


__all__ = [
    "APP_NAME",
    "APP_VENDOR",
    "AppPath",
    "atomic_write_bytes",
    "atomic_write_text",
    "backup_path",
    "bucket_root",
    "cache_path",
    "config_path",
    "data_path",
    "local_root",
    "log_path",
    "roaming_root",
]
