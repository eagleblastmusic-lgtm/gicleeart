"""Automated 6G.5-S.2B selection verify scenarios (headless-ish).

Runs scenarios A–E against GICLÉE FRAME with GICLEE_STUDIO_PERF=1, then
prints analyzer output.

Manual GUI equivalent: see analyze_gicleeframe_selection_perf.py docstring.

    py -3 scripts/smoke_6g5s2a_selection_verify.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "giclee_app" / "logs" / "studio_perf.log"
ANALYZER = ROOT / "scripts" / "analyze_gicleeframe_selection_perf.py"


def _prepare_env() -> None:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.environ["GICLEE_STUDIO_PERF"] = "1"
    for env_name in (
        "GICLEE_STUDIO_IDLE_PREWARM",
        "GICLEE_ASSET_LAB_AUTO_FULL_CARDS",
    ):
        os.environ.pop(env_name, None)
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        pass


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


def _find_id_by_type(view: object, element_type: str) -> str | None:
    merged = getattr(view, "_merged", [])
    for item in merged:
        if getattr(item, "element_type", None) == element_type:
            return str(getattr(item, "element_id", ""))
    return None


def _find_distinct_ids(view: object, count: int = 5) -> list[str]:
    merged = getattr(view, "_merged", [])
    seen_types: set[str] = set()
    ids: list[str] = []
    for item in merged:
        etype = str(getattr(item, "element_type", ""))
        eid = str(getattr(item, "element_id", ""))
        if not eid or etype in seen_types:
            continue
        if etype in {"divider", "media_section", "image", "section_legacy", "section"}:
            seen_types.add(etype)
            ids.append(eid)
        if len(ids) >= count:
            break
    return ids


def _click(view: object, element_id: str) -> None:
    view._on_section_row_click(element_id)  # noqa: SLF001
    _pump(view, 0.35)


def _open_gicleeframe(app: object) -> object:
    app._show_hub("theme")  # noqa: SLF001
    _wait_until(app, lambda: True, timeout=2.0)
    app._show_gicleeframe_shell("theme")  # noqa: SLF001
    _wait_until(app, lambda: "gicleeframe" in getattr(app, "_view_cache", {}), timeout=20.0)
    view = app._view_cache["gicleeframe"]  # noqa: SLF001
    _pump(app, 0.2)
    return view


def _run_scenario_a(app: object, view: object) -> None:
    _marker("A")
    _wait_until(
        app,
        lambda: bool(getattr(view, "_section_list_scroll_upgrade_done", False)),
        timeout=35.0,
    )
    _pump(app, 0.3)
    sequence_types = ["divider", "media_section", "image", "section_legacy", "divider"]
    for etype in sequence_types:
        eid = _find_id_by_type(view, etype)
        if eid:
            _click(view, eid)
    _pump(app, 1.5)


def _run_scenario_b(app: object) -> None:
    _marker("B")
    app._view_cache.pop("gicleeframe", None)  # noqa: SLF001
    view = _open_gicleeframe(app)

    clicked = False
    deadline = time.perf_counter() + 8.0
    while time.perf_counter() < deadline:
        static_lane = getattr(view, "_section_list_static_lane", None) is not None
        scroll_done = bool(getattr(view, "_section_list_scroll_upgrade_done", False))
        row_ids = list(getattr(view, "_section_row_ids", []))
        if static_lane and not scroll_done and len(row_ids) >= 2:
            view._on_section_row_click(row_ids[0])  # noqa: SLF001
            clicked = True
            break
        _pump(app, 0.005)

    if not clicked:
        row_ids = list(getattr(view, "_section_row_ids", []))
        if row_ids:
            view._on_section_row_click(row_ids[0])  # noqa: SLF001
    _pump(app, 2.0)


def _run_scenario_c(app: object, view: object) -> None:
    _marker("C")
    ids = _find_distinct_ids(view, count=5)
    for eid in ids:
        view._on_section_row_click(eid)  # noqa: SLF001
        _pump(view, 0.015)
    _pump(app, 1.2)


def _run_scenario_d(app: object, view: object) -> None:
    _marker("D")
    for etype in ("divider", "media_section"):
        first = _find_id_by_type(view, etype)
        other = _find_id_by_type(view, "image" if etype == "divider" else "divider")
        if first:
            _click(view, first)
        if other:
            _click(view, other)
        if first:
            _click(view, first)
        _pump(app, 1.0)


def _run_scenario_e(app: object) -> None:
    _marker("E")
    app._view_cache.pop("gicleeframe", None)  # noqa: SLF001
    view = _open_gicleeframe(app)
    _wait_until(app, lambda: len(getattr(view, "_section_row_ids", [])) >= 1, timeout=20.0)
    # Target click window 0.8-1.5s after visual enter.
    enter_mono = getattr(view, "_visual_enter_mono", None)
    if enter_mono is not None:
        while time.perf_counter() - enter_mono < 1.0:
            _pump(app, 0.01)
    row_ids = list(getattr(view, "_section_row_ids", []))
    if row_ids:
        view._on_section_row_click(row_ids[min(1, len(row_ids) - 1)])  # noqa: SLF001
    _pump(app, 2.0)


def main() -> int:
    _prepare_env()

    import customtkinter as ctk

    from giclee_app.launcher_studio import GicleeAppStudio

    ctk.set_appearance_mode("dark")
    app = GicleeAppStudio()
    app.withdraw()

    try:
        view = _open_gicleeframe(app)
        _run_scenario_a(app, view)
        _run_scenario_c(app, view)
        _run_scenario_d(app, view)
        _run_scenario_b(app)
        _run_scenario_e(app)
    finally:
        app.destroy()

    if not LOG_PATH.exists():
        print("FAIL: studio_perf.log not created", file=sys.stderr)
        return 1

    result = subprocess.run(
        [sys.executable, str(ANALYZER), "--log", str(LOG_PATH)],
        check=False,
        text=True,
        encoding="utf-8",
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
