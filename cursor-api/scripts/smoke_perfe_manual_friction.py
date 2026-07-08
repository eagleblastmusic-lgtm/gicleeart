"""PERF-E manual friction capture — automated headless equivalent.

Mirrors the manual scenario from PERF-E:
  1. Open Studio → GICLÉE FRAME
  2. Wait 1s
  3. 10 section clicks at normal pace
  4. 10 section clicks fast
  5. Special types: divider, media_section, image child, text child, legacy

    py -3 scripts/smoke_perfe_manual_friction.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "giclee_app" / "logs" / "studio_perf.log"


def _prepare_env() -> None:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.environ["GICLEE_STUDIO_PERF"] = "1"
    os.environ["GICLEE_STUDIO_IDLE_PREWARM"] = "0"
    if LOG_PATH.exists():
        LOG_PATH.unlink()


def _pump(app: object, seconds: float = 0.05) -> None:
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        app.update_idletasks()  # type: ignore[attr-defined]
        app.update()  # type: ignore[attr-defined]


def _wait_until(app: object, predicate: Callable[[], bool], *, timeout: float = 30.0, step: float = 0.02) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return True
        _pump(app, step)
    return False


def _marker(scenario: str) -> None:
    from giclee_app.studio.perf import log_event

    log_event("verify.scenario_marker", scenario=scenario)


def _click(view: object, element_id: str, *, pace: float = 0.35) -> None:
    view._on_section_row_click(element_id)  # noqa: SLF001
    _pump(view, pace)


def _open_gicleeframe(app: object) -> object:
    app._show_hub("theme")  # noqa: SLF001
    _wait_until(app, lambda: True, timeout=2.0)
    app._show_gicleeframe_shell("theme")  # noqa: SLF001
    _wait_until(app, lambda: "gicleeframe" in getattr(app, "_view_cache", {}), timeout=25.0)
    view = app._view_cache["gicleeframe"]  # noqa: SLF001
    _pump(app, 0.2)
    return view


def _row_ids(view: object) -> list[str]:
    return list(getattr(view, "_section_row_ids", []))


def _find_by_type(view: object, element_type: str) -> str | None:
    for item in getattr(view, "_merged", []):
        if getattr(item, "element_type", None) == element_type:
            return str(getattr(item, "element_id", ""))
    return None


def _find_child(view: object, element_type: str) -> str | None:
    for item in getattr(view, "_merged", []):
        if getattr(item, "element_type", None) == element_type and getattr(item, "group", "") in {
            "jumbo",
            "body",
            "image",
        }:
            return str(getattr(item, "element_id", ""))
    return None


def main() -> int:
    _prepare_env()

    import customtkinter as ctk

    from giclee_app.launcher_studio import GicleeAppStudio

    ctk.set_appearance_mode("dark")
    app = GicleeAppStudio()
    app.withdraw()

    try:
        view = _open_gicleeframe(app)
        _wait_until(
            app,
            lambda: len(_row_ids(view)) >= 3,
            timeout=30.0,
        )
        _pump(app, 1.0)

        _marker("PERF-E-normal")
        rows = _row_ids(view)
        normal_targets = (rows * 4)[:10]
        for eid in normal_targets:
            _click(view, eid, pace=0.35)

        _marker("PERF-E-fast")
        fast_rows = _row_ids(view)
        fast_targets = (fast_rows[::-1] * 4)[:10]
        for eid in fast_targets:
            _click(view, eid, pace=0.02)
        _pump(app, 1.5)

        _marker("PERF-E-special")
        special_sequence: list[str] = []
        for finder, etype in (
            (_find_by_type, "divider"),
            (_find_by_type, "media_section"),
            (_find_child, "image"),
            (_find_child, "jumbo"),
            (_find_by_type, "section_legacy"),
        ):
            eid = finder(view, etype)
            if eid:
                special_sequence.append(eid)
        for eid in special_sequence:
            _click(view, eid, pace=0.4)
        _pump(app, 2.0)
    finally:
        app.destroy()

    if not LOG_PATH.exists():
        print("FAIL: studio_perf.log not created", file=sys.stderr)
        return 1

    analyzer = ROOT / "scripts" / "analyze_perfe_manual_friction.py"
    if analyzer.exists():
        import subprocess

        result = subprocess.run(
            [sys.executable, str(analyzer), "--log", str(LOG_PATH)],
            check=False,
            text=True,
            encoding="utf-8",
        )
        return result.returncode
    print(f"Log written: {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
