"""Repeatable Hub → GICLÉE FRAME performance baseline (6G.5-O).

Manual equivalent (PowerShell, from cursor-api/):

    Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue
    cd C:\\Strona\\pusty\\cursor-api
    Remove-Item .\\giclee_app\\logs\\studio_perf.log -ErrorAction SilentlyContinue
    $env:GICLEE_STUDIO_PERF = "1"
    Remove-Item Env:\\GICLEE_STUDIO_IDLE_PREWARM -ErrorAction SilentlyContinue
    Remove-Item Env:\\GICLEE_ASSET_LAB_AUTO_FULL_CARDS -ErrorAction SilentlyContinue
    py -3 -m giclee_app.studio_preview

Automated headless baseline (same env + route, no GUI interaction):

    py -3 scripts/smoke_6g5o_hub_gicleeframe_baseline.py
    py -3 scripts/smoke_6g5o_hub_gicleeframe_baseline.py --runs 3
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "giclee_app" / "logs" / "studio_perf.log"

METRIC_SPECS: list[tuple[str, str, str]] = [
    ("build_shell", "studio.gicleeframe.build_shell", "elapsed_ms"),
    ("deferred_factory", "studio.show_view.deferred_factory", "elapsed_ms"),
    (
        "early_lane_queue_latency_ms",
        "studio.gicleeframe.sections_column.early_lane_enter",
        "queue_latency_ms",
    ),
    (
        "column_ready_for_rows",
        "studio.gicleeframe.section_list.column_ready_for_rows",
        "since_enter_ms",
    ),
    (
        "sections_column_deferred_shell",
        "studio.gicleeframe.build.sections_column.deferred.shell",
        "elapsed_ms",
    ),
    (
        "sections_column_deferred_extras",
        "studio.gicleeframe.build.sections_column.deferred.extras",
        "elapsed_ms",
    ),
    (
        "incremental_enter_queue_latency_ms",
        "studio.gicleeframe.section_list.incremental_enter",
        "queue_latency_ms",
    ),
    ("first_batch_rows", "studio.gicleeframe.section_list.first_batch.rows", "elapsed_ms"),
    (
        "first_visible_ready",
        "studio.gicleeframe.section_list.first_visible_ready",
        "since_enter_ms",
    ),
    ("perceived_ready", "studio.gicleeframe.visual.perceived_ready", "since_enter_ms"),
    (
        "full_ready_progressive",
        "studio.gicleeframe.visual.full_ready_progressive",
        "since_enter_ms",
    ),
]


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
            ["powershell", "-NoProfile", "-Command", "Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        pass


def _load_events() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        raise FileNotFoundError(f"Missing perf log: {LOG_PATH}")
    events: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _last_field(events: list[dict[str, Any]], event_name: str, field: str) -> float | None:
    for event in reversed(events):
        if event.get("event") == event_name:
            value = event.get(field)
            if value is not None:
                return float(value)
    return None


def _extract_run_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for key, event_name, field in METRIC_SPECS:
        metrics[key] = _last_field(events, event_name, field)

    marker = next((e for e in events if e.get("event") == "studio.gicleeframe.runtime_marker"), None)
    metrics["phase_marker"] = marker.get("phase_marker") if marker else None

    idletasks = [
        e
        for e in events
        if "update_idletasks" in str(e.get("event", ""))
        and e.get("view_class") == "GicleeFrameView"
    ]
    metrics["idletasks_skipped"] = any(
        e.get("event") == "studio.show_view.update_idletasks.skipped" for e in idletasks
    )
    metrics["idletasks_executed"] = any(
        e.get("event") == "studio.show_view.update_idletasks.executed" for e in idletasks
    )

    blob = json.dumps(events, ensure_ascii=False)
    metrics["tcl_error"] = "TclError" in blob
    metrics["extras_skipped_missing_slot"] = any(
        "extras_skipped_missing_slot" in str(e.get("event", "")) for e in events
    )
    return metrics


def _run_once(hub_wait_s: float, frame_wait_s: float) -> dict[str, Any]:
    _prepare_env()

    import customtkinter as ctk

    from giclee_app.launcher_studio import GicleeAppStudio

    ctk.set_appearance_mode("dark")
    app = GicleeAppStudio()
    app.withdraw()

    app._show_hub("theme")  # noqa: SLF001
    deadline = time.time() + hub_wait_s
    while time.time() < deadline:
        app.update_idletasks()
        app.update()

    app._show_gicleeframe_shell("theme")  # noqa: SLF001
    deadline = time.time() + frame_wait_s
    while time.time() < deadline:
        app.update_idletasks()
        app.update()

    app.destroy()
    return _extract_run_metrics(_load_events())


def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_keys = [spec[0] for spec in METRIC_SPECS]
    summary: dict[str, Any] = {"runs": len(runs)}
    for key in numeric_keys:
        values = [run[key] for run in runs if run.get(key) is not None]
        if not values:
            summary[key] = {"min": None, "median": None, "max": None}
            continue
        summary[key] = {
            "min": round(min(values), 2),
            "median": round(statistics.median(values), 2),
            "max": round(max(values), 2),
        }
    summary["phase_marker"] = runs[-1].get("phase_marker") if runs else None
    summary["idletasks_skipped_all"] = all(run.get("idletasks_skipped") for run in runs)
    summary["idletasks_executed_any"] = any(run.get("idletasks_executed") for run in runs)
    summary["tcl_error_any"] = any(run.get("tcl_error") for run in runs)
    summary["extras_skipped_any"] = any(run.get("extras_skipped_missing_slot") for run in runs)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="6G.5-O Hub → GICLÉE FRAME perf baseline")
    parser.add_argument("--runs", type=int, default=1, help="Number of sequential smoke runs")
    parser.add_argument("--hub-wait", type=float, default=8.0)
    parser.add_argument("--frame-wait", type=float, default=20.0)
    parser.add_argument(
        "--pause-between-runs",
        type=float,
        default=2.0,
        help="Seconds to wait between runs (reduces Tcl after() bleed)",
    )
    args = parser.parse_args()

    all_runs: list[dict[str, Any]] = []
    for index in range(1, args.runs + 1):
        if index > 1 and args.pause_between_runs > 0:
            time.sleep(args.pause_between_runs)
        print(f"--- run {index}/{args.runs} ---", flush=True)
        metrics = _run_once(args.hub_wait, args.frame_wait)
        all_runs.append(metrics)
        print(json.dumps(metrics, ensure_ascii=False, indent=2))

    if args.runs > 1:
        print("--- summary ---")
        print(json.dumps(_summarize_runs(all_runs), ensure_ascii=False, indent=2))

    last = all_runs[-1]
    checks = {
        "phase_marker": bool(last.get("phase_marker")),
        "idletasks_skipped": last.get("idletasks_skipped") is True,
        "idletasks_not_executed": last.get("idletasks_executed") is False,
        "early_lane_under_100ms": (last.get("early_lane_queue_latency_ms") or 999) < 100,
        "no_tcl_error": not last.get("tcl_error"),
        "no_extras_skipped": not last.get("extras_skipped_missing_slot"),
    }
    print("--- pass checks (last run) ---")
    for name, ok in checks.items():
        print(f"{name}: {'PASS' if ok else 'FAIL'}")

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
