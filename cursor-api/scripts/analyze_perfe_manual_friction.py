"""Analyze PERF-E manual friction capture from studio_perf.log."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "giclee_app" / "logs" / "studio_perf.log"

CLICK = "studio.gicleeframe.selection.click"
IMMEDIATE = "studio.gicleeframe.selection.immediate_ready"
POPULATE_DONE = "studio.gicleeframe.selection.populate.done"
EDITOR_SHELL = "studio.gicleeframe.editor.shell_ready_after_click"
PAGE_CTX_SHELL = "studio.gicleeframe.page_context.shell_ready"
PAGE_CTX_DONE = "studio.gicleeframe.page_context.done"
PREVIEW_DONE = "studio.gicleeframe.preview.update.done"
LAYER_NAV_DONE = "studio.gicleeframe.layer_nav.update.done"
CHILDREN_DONE = "studio.gicleeframe.children.update.done"
JOBS_CANCELLED = "studio.gicleeframe.selection.jobs_cancelled"

BACKGROUND_JOBS = (
    "identity_prewarm",
    "rows_prewarm",
    "control.structure",
    "control.late_cards",
    "section_list.incremental",
    "scroll_upgrade",
)


@dataclass
class ClickRow:
    index: int
    scenario: str
    element_type: str
    immediate_ready_ms: float | None = None
    editor_shell_ms: float | None = None
    page_context_shell_ms: float | None = None
    populate_done_ms: float | None = None
    page_context_ms: float | None = None
    preview_ms: float | None = None
    layer_nav_ms: float | None = None
    children_ms: float | None = None
    jobs_cancelled: int = 0
    background_jobs: list[str] = field(default_factory=list)
    slow_events: list[str] = field(default_factory=list)


def _load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _scenario_at(index: int, markers: list[tuple[int, str]]) -> str:
    scenario = "enter"
    for marker_index, scenario_id in markers:
        if marker_index <= index:
            scenario = scenario_id
    return scenario


def _first_after(
    events: list[dict[str, Any]],
    start: int,
    end: int,
    name: str,
    *,
    element_id: str | None = None,
) -> dict[str, Any] | None:
    for event in events[start:end]:
        if event.get("event") != name:
            continue
        if element_id is not None and event.get("element_id") != element_id:
            continue
        return event
    return None


def _max_since_click(events: list[dict[str, Any]], start: int, end: int, name: str) -> float | None:
    values = [
        float(event["since_click_ms"])
        for event in events[start:end]
        if event.get("event") == name and event.get("since_click_ms") is not None
    ]
    return max(values) if values else None


def _background_between(events: list[dict[str, Any]], start: int, end: int) -> list[str]:
    found: list[str] = []
    for event in events[start:end]:
        text = json.dumps(event, ensure_ascii=False)
        for job in BACKGROUND_JOBS:
            if job in text and job not in found:
                found.append(job)
    return found


def _slow_between(events: list[dict[str, Any]], start: int, end: int, threshold: float) -> list[str]:
    slow: list[str] = []
    for event in events[start:end]:
        elapsed = event.get("elapsed_ms")
        since = event.get("since_click_ms")
        ms = elapsed if elapsed is not None else since
        if ms is not None and float(ms) > threshold:
            slow.append(f"{event.get('event')}={ms}ms")
    return slow


def parse(events: list[dict[str, Any]]) -> list[ClickRow]:
    markers = [
        (i, str(e.get("scenario", "?")))
        for i, e in enumerate(events)
        if e.get("event") == "verify.scenario_marker"
    ]
    click_indices = [i for i, e in enumerate(events) if e.get("event") == CLICK]
    rows: list[ClickRow] = []

    for idx, click_i in enumerate(click_indices):
        click = events[click_i]
        element_id = str(click.get("element_id", ""))
        next_i = click_indices[idx + 1] if idx + 1 < len(click_indices) else len(events)
        generation = int(click.get("generation", click.get("selection_generation_next", 0)))

        immediate = _first_after(events, click_i, next_i, IMMEDIATE, element_id=element_id)
        editor_shell = _first_after(events, click_i, next_i, EDITOR_SHELL, element_id=element_id)
        page_ctx_shell = _first_after(events, click_i, next_i, PAGE_CTX_SHELL, element_id=element_id)
        populate = _first_after(events, click_i, next_i, POPULATE_DONE, element_id=element_id)
        page_ctx = _first_after(events, click_i, next_i, PAGE_CTX_DONE, element_id=element_id)
        preview = _first_after(events, click_i, next_i, PREVIEW_DONE)
        layer_nav = _first_after(events, click_i, next_i, LAYER_NAV_DONE)
        children = _first_after(events, click_i, next_i, CHILDREN_DONE)
        cancelled = _first_after(events, click_i, next_i, JOBS_CANCELLED)

        sel_cancel = int(cancelled.get("selection_jobs_cancelled", 0)) if cancelled else 0
        page_cancel = int(cancelled.get("page_context_jobs_cancelled", 0)) if cancelled else 0

        rows.append(
            ClickRow(
                index=idx + 1,
                scenario=_scenario_at(click_i, markers),
                element_type=str(click.get("element_type", "")),
                immediate_ready_ms=float(immediate["since_click_ms"])
                if immediate and immediate.get("since_click_ms") is not None
                else None,
                editor_shell_ms=float(editor_shell["since_click_ms"])
                if editor_shell and editor_shell.get("since_click_ms") is not None
                else None,
                page_context_shell_ms=float(page_ctx_shell["since_click_ms"])
                if page_ctx_shell and page_ctx_shell.get("since_click_ms") is not None
                else None,
                populate_done_ms=float(populate["since_click_ms"])
                if populate and populate.get("since_click_ms") is not None
                else None,
                page_context_ms=_max_since_click(events, click_i, next_i, PAGE_CTX_DONE),
                preview_ms=float(preview["since_click_ms"])
                if preview and preview.get("since_click_ms") is not None
                else None,
                layer_nav_ms=float(layer_nav["since_click_ms"])
                if layer_nav and layer_nav.get("since_click_ms") is not None
                else None,
                children_ms=float(children["since_click_ms"])
                if children and children.get("since_click_ms") is not None
                else None,
                jobs_cancelled=sel_cancel + page_cancel,
                background_jobs=_background_between(events, click_i, next_i),
                slow_events=_slow_between(events, click_i, next_i, 50.0),
            )
        )
        _ = generation
    return rows


def _fmt(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "—"


def print_report(rows: list[ClickRow], events: list[dict[str, Any]]) -> None:
    print("=== PERF-E CLICK TABLE ===")
    header = (
        "click",
        "scenario",
        "type",
        "imm",
        "editor_shell",
        "pc_shell",
        "pop",
        "page_ctx",
        "preview",
        "layer",
        "children",
        "cancel",
        "bg_jobs",
    )
    print("\t".join(header))
    for row in rows:
        print(
            "\t".join(
                [
                    str(row.index),
                    row.scenario,
                    row.element_type or "?",
                    _fmt(row.immediate_ready_ms),
                    _fmt(row.editor_shell_ms),
                    _fmt(row.page_context_shell_ms),
                    _fmt(row.populate_done_ms),
                    _fmt(row.page_context_ms),
                    _fmt(row.preview_ms),
                    _fmt(row.layer_nav_ms),
                    _fmt(row.children_ms),
                    str(row.jobs_cancelled),
                    ",".join(row.background_jobs) or "—",
                ]
            )
        )

    def _stats(values: list[float | None]) -> str:
        nums = [v for v in values if v is not None]
        if not nums:
            return "—"
        return f"min={min(nums):.1f} avg={sum(nums)/len(nums):.1f} max={max(nums):.1f} n={len(nums)}"

    print("\n=== AGGREGATES ===")
    print(f"immediate_ready: {_stats([r.immediate_ready_ms for r in rows])}")
    print(f"editor_shell: {_stats([r.editor_shell_ms for r in rows])}")
    print(f"page_context_shell: {_stats([r.page_context_shell_ms for r in rows])}")
    print(f"populate.done: {_stats([r.populate_done_ms for r in rows])}")
    print(f"page_context.done: {_stats([r.page_context_ms for r in rows])}")
    print(f"preview.done: {_stats([r.preview_ms for r in rows])}")
    print(f"layer_nav.done: {_stats([r.layer_nav_ms for r in rows])}")
    print(f"children.done: {_stats([r.children_ms for r in rows])}")
    print(f"jobs_cancelled total: {sum(r.jobs_cancelled for r in rows)}")

    over50 = _slow_between(events, 0, len(events), 50.0)
    over100 = _slow_between(events, 0, len(events), 100.0)
    print(f"\n=== EVENTS > 50ms ({len(over50)}) ===")
    for item in over50[:40]:
        print(item)
    print(f"\n=== EVENTS > 100ms ({len(over100)}) ===")
    for item in over100[:25]:
        print(item)

    # slowest clicks by populate
    by_pop = sorted(
        [r for r in rows if r.populate_done_ms is not None],
        key=lambda r: r.populate_done_ms or 0,
        reverse=True,
    )[:5]
    print("\n=== SLOWEST populate.done (since click) ===")
    for row in by_pop:
        print(
            f"#{row.index} {row.element_type} scenario={row.scenario} "
            f"pop={row.populate_done_ms:.1f}ms imm={_fmt(row.immediate_ready_ms)} "
            f"bg={','.join(row.background_jobs) or '—'}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args()
    if not args.log.exists():
        print(f"Missing log: {args.log}", file=sys.stderr)
        return 1
    events = _load(args.log)
    rows = parse(events)
    print_report(rows, events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
