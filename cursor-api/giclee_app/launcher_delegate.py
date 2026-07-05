"""Uruchamianie komponentów ze Studio — subprocess/url tylko, bez side effects launchera."""

from __future__ import annotations

import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from giclee_app.component_loader import Component
from giclee_app.runtime import get_component_cwd, resolve_python_interpreter

_LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

INLINE_MESSAGE = (
    "Ten komponent inline powinien otworzyć się w Studio. "
    "Jeśli widzisz ten komunikat, uruchom go z Component Hub "
    "albo użyj klasycznego launchera jako fallbacku."
)


class LaunchOutcome(str, Enum):
    OK = "ok"
    BLOCKED_INLINE = "blocked_inline"
    ERROR = "error"
    NO_PYTHON = "no_python"
    NO_URL = "no_url"


@dataclass(frozen=True)
class LaunchResult:
    outcome: LaunchOutcome
    message: str = ""
    pid: int | None = None


def component_log_path(comp: Component) -> Path:
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return _LOGS_DIR / f"{comp.folder_name}.log"


def build_subprocess_cmd(comp: Component) -> tuple[list[str] | None, str]:
    prefix, py_err = resolve_python_interpreter()
    if prefix is None:
        return None, py_err
    return [*prefix, "-m", comp.module_path], ""


def _watch_proc(proc: subprocess.Popen[Any], name: str, log_f: Any) -> None:
    rc = proc.wait()
    if log_f is not None:
        try:
            log_f.write(
                f"\n========== {datetime.now().isoformat()} exit code {rc} ==========\n"
            )
            log_f.flush()
            log_f.close()
        except OSError:
            pass


def launch(comp: Component, *, on_status: Any = None) -> LaunchResult:
    """Uruchamia komponent — bez importu launcher.GicleeApp."""
    if comp.mode == "url":
        url = (comp.url or "").strip()
        if not url:
            return LaunchResult(LaunchOutcome.NO_URL, "Brak URL w component.json")
        try:
            webbrowser.open(url)
            msg = f"Otwarto w przeglądarce: {url}"
            if callable(on_status):
                on_status(msg)
            return LaunchResult(LaunchOutcome.OK, msg)
        except Exception as exc:  # noqa: BLE001
            return LaunchResult(LaunchOutcome.ERROR, str(exc))

    if comp.mode == "inline":
        return LaunchResult(LaunchOutcome.BLOCKED_INLINE, INLINE_MESSAGE)

    cmd, py_err = build_subprocess_cmd(comp)
    if cmd is None:
        return LaunchResult(LaunchOutcome.NO_PYTHON, py_err)

    cwd = get_component_cwd()
    log_path = component_log_path(comp)
    log_f = None
    try:
        log_f = open(log_path, "a", encoding="utf-8", buffering=1)
        log_f.write(f"\n\n========== {datetime.now().isoformat()} start (studio) ==========\n")
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
        if log_f:
            try:
                log_f.close()
            except OSError:
                pass
        return LaunchResult(LaunchOutcome.ERROR, str(exc))

    msg = f"Uruchomiono: {comp.name} (PID {proc.pid})"
    if callable(on_status):
        on_status(msg)
    threading.Thread(
        target=_watch_proc, args=(proc, comp.name, log_f), daemon=True,
    ).start()
    return LaunchResult(LaunchOutcome.OK, msg, pid=proc.pid)


def open_component_folder(comp: Component) -> None:
    path = comp.package_path
    if not path.is_dir():
        return
    try:
        if sys.platform.startswith("win"):
            import os

            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])  # noqa: S607
        else:
            subprocess.Popen(["xdg-open", str(path)])  # noqa: S607
    except OSError:
        pass
