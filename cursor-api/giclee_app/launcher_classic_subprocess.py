"""Adapter klasycznego startu komponentu w osobnym procesie (subprocess)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TextIO

from .component_loader import Component
from .component_logs import component_log_write_path
from .runtime import get_component_cwd, resolve_python_interpreter


class ClassicSubprocessOutcome(str, Enum):
    STARTED = "started"
    NO_PYTHON = "no_python"
    ERROR = "error"


@dataclass(frozen=True)
class ClassicSubprocessStart:
    outcome: ClassicSubprocessOutcome
    message: str = ""
    proc: subprocess.Popen[Any] | None = None
    log_file: TextIO | None = None


def start_classic_component_subprocess(
    comp: Component,
    *,
    logs_dir: Path,
) -> ClassicSubprocessStart:
    """Uruchamia komponent jako klasyczny subprocess.

    Zwraca strukturalny wynik bez modyfikowania stanu aplikacji.
    Nie dodaje procesu do listy, nie uruchamia wątku i nie aktualizuje statusu.
    """
    cwd = get_component_cwd()
    prefix, py_err = resolve_python_interpreter()

    if prefix is None:
        return ClassicSubprocessStart(
            ClassicSubprocessOutcome.NO_PYTHON,
            message=py_err,
        )

    cmd = [*prefix, "-m", comp.module_path]

    log_path = component_log_write_path(comp.folder_name, logs_dir=logs_dir)
    log_f: TextIO | None = None
    try:
        log_f = open(log_path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        log_f.write(
            f"\n\n========== {datetime.now().isoformat()} start ==========\n"
        )
        log_f.flush()
    except OSError:
        log_f = None

    try:
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            cwd=str(cwd),
            stdout=log_f or subprocess.DEVNULL,
            stderr=subprocess.STDOUT if log_f else subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except OSError as exc:
        if log_f is not None:
            try:
                log_f.close()
            except OSError:
                pass
        return ClassicSubprocessStart(
            ClassicSubprocessOutcome.ERROR,
            message=str(exc),
        )

    return ClassicSubprocessStart(
        ClassicSubprocessOutcome.STARTED,
        proc=proc,
        log_file=log_f,
    )


__all__ = [
    "ClassicSubprocessOutcome",
    "ClassicSubprocessStart",
    "start_classic_component_subprocess",
]
