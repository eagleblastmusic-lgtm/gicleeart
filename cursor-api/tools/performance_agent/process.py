"""Studio subprocess launcher for Performance Agent."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Protocol

from tools.performance_agent.profiles import AppProfile
from tools.performance_agent.timeutil import utc_now_iso

_STARTUP_GRACE_SECONDS = 1.5
_TERMINATE_WAIT_SECONDS = 5.0


class ProcessIO(Protocol):
    def input(self, prompt: str) -> str: ...
    def print(self, text: str) -> None: ...


@dataclass
class StudioProcess:
    popen: subprocess.Popen[bytes] | subprocess.Popen
    pid: int
    command: list[str]
    started_at: str

    def is_running(self) -> bool:
        return self.popen.poll() is None


def _build_env(profile: AppProfile) -> dict[str, str]:
    env = os.environ.copy()
    env.update(profile.launch_config.env)
    for key in profile.launch_config.env_unset:
        env.pop(key, None)
    return env


def launch_studio(profile: AppProfile) -> StudioProcess:
    launch = profile.launch_config
    command = list(launch.command)
    kwargs: dict = {
        "cwd": str(launch.working_dir),
        "env": _build_env(profile),
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]

    popen = subprocess.Popen(command, **kwargs)
    return StudioProcess(
        popen=popen,
        pid=popen.pid,
        command=command,
        started_at=utc_now_iso(),
    )


def wait_startup_grace(proc: StudioProcess, seconds: float = _STARTUP_GRACE_SECONDS) -> bool:
    """Return True if process still running after grace period."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not proc.is_running():
            return False
        time.sleep(0.1)
    return proc.is_running()


def shutdown_studio(
    proc: StudioProcess,
    io: ProcessIO,
    *,
    ask_kill: bool = True,
) -> int | None:
    """Terminate Studio; prompt before kill if still alive after 5s."""
    if not proc.is_running():
        return proc.popen.poll()

    proc.popen.terminate()
    deadline = time.monotonic() + _TERMINATE_WAIT_SECONDS
    while time.monotonic() < deadline:
        code = proc.popen.poll()
        if code is not None:
            return code
        time.sleep(0.1)

    if not proc.is_running():
        return proc.popen.poll()

    if ask_kill:
        answer = io.input(
            f"Studio (PID {proc.pid}) nadal działa po terminate. Użyć kill()? [y/N]: "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            io.print("Pozostawiono Studio bez kill().")
            return None

    proc.popen.kill()
    return proc.popen.wait(timeout=5)


def prompt_shutdown_studio(proc: StudioProcess, io: ProcessIO) -> bool:
    """Ask whether to close Studio. Returns True if shutdown was requested."""
    if not proc.is_running():
        io.print(f"Studio (PID {proc.pid}) nie działa już.")
        return False
    answer = io.input(
        f"\nZakończyć proces Studio (PID {proc.pid})?\n"
        "  y) zamknij Studio\n"
        "  n) zostaw otwarte [default]: "
    ).strip().lower()
    return answer in {"y", "yes"}
