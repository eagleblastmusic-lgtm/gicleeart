"""Log lifecycle management before performance audit runs."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from tools.performance_agent.timeutil import utc_now

LogLifecycleMode = Literal["clear", "keep", "copy_only"]


@dataclass(frozen=True)
class LogLifecycleResult:
    mode: LogLifecycleMode
    log_path: Path
    original_log_existed: bool
    archived_to: Path | None
    cleared: bool

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "log_path": str(self.log_path),
            "original_log_existed": self.original_log_existed,
            "archived_to": str(self.archived_to) if self.archived_to else None,
            "cleared": self.cleared,
        }


class LifecycleIO(Protocol):
    def input(self, prompt: str) -> str: ...
    def print(self, text: str) -> None: ...


def archive_root(output_root: Path) -> Path:
    return output_root / "_archive"


def _archive_path(archive_dir: Path) -> Path:
    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir / f"{stamp}_studio_perf.log"


def apply_log_lifecycle(
    log_path: Path,
    mode: LogLifecycleMode,
    *,
    archive_dir: Path,
) -> LogLifecycleResult:
    existed = log_path.exists() and log_path.is_file()
    archived_to: Path | None = None
    cleared = False

    if mode == "keep":
        return LogLifecycleResult(
            mode=mode,
            log_path=log_path,
            original_log_existed=existed,
            archived_to=None,
            cleared=False,
        )

    if existed:
        archived_to = _archive_path(archive_dir)
        if mode == "clear":
            shutil.move(str(log_path), str(archived_to))
            cleared = True
        elif mode == "copy_only":
            shutil.copy2(log_path, archived_to)
            cleared = False

    if mode == "clear" and not existed:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    return LogLifecycleResult(
        mode=mode,
        log_path=log_path,
        original_log_existed=existed,
        archived_to=archived_to,
        cleared=cleared,
    )


def prompt_log_lifecycle_mode(io: LifecycleIO) -> LogLifecycleMode:
    io.print("\nLog lifecycle przed testem:")
    io.print("  1) clear     — archiwizuj i wyczyść (rekomendowane) [default]")
    io.print("  2) keep      — zostaw stary log")
    io.print("  3) copy_only — skopiuj do archiwum, nie czyść")
    choice = io.input("Wybór [1/2/3]: ").strip().lower()
    if choice in {"", "1", "clear", "c"}:
        return "clear"
    if choice in {"2", "keep", "k"}:
        return "keep"
    if choice in {"3", "copy_only", "copy"}:
        return "copy_only"
    io.print("Nieznany wybór — używam clear.")
    return "clear"
