"""Analyze GICLÉE FRAME selection perf from studio_perf.log (6G.5-S.2B verify).

Usage (from cursor-api/):
    py -3 scripts/analyze_gicleeframe_selection_perf.py
    py -3 scripts/analyze_gicleeframe_selection_perf.py --log giclee_app/logs/studio_perf.log
    py -3 scripts/analyze_gicleeframe_selection_perf.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "giclee_app" / "logs" / "studio_perf.log"

CLICK_EVENT = "studio.gicleeframe.selection.click"
SCENARIO_MARKER = "verify.scenario_marker"

EDITOR_SEGMENTS: list[tuple[str, str]] = [
    ("ensure_identity_ms", "studio.gicleeframe.selection.editor.ensure_identity"),
    ("ensure_rows_ms", "studio.gicleeframe.selection.editor.ensure_rows"),
    ("preview_ms", "studio.gicleeframe.selection.editor.preview"),
    ("fields_ms", "studio.gicleeframe.selection.editor.fields"),
    ("layer_nav_ms", "studio.gicleeframe.selection.editor.layer_nav"),
    ("children_ms", "studio.gicleeframe.selection.editor.children"),
]

STALE_EVENTS = {
    "studio.gicleeframe.populate_editor.deferred_stale",
    "studio.gicleeframe.populate_editor.deferred_missing_or_stale",
    "studio.gicleeframe.selection.page_context.stale",
    "studio.gicleeframe.page_context.stable_defer_stale",
    "studio.gicleeframe.page_context.deferred_stale",
}


@dataclass
class ClickRow:
    index: int
    scenario: str
    generation: int
    element_id: str
    element_type: str
    static_lane: bool | None
    scroll_ready: bool | None
    perceived_ready_logged: bool | None
    click_since_enter_ms: float | None
    click_to_highlight_ms: float | None
    click_to_populate_enter_ms: float | None
    ensure_identity_ms: float | None = None
    ensure_rows_ms: float | None = None
    preview_ms: float | None = None
    fields_ms: float | None = None
    layer_nav_ms: float | None = None
    children_ms: float | None = None
    populate_done_since_click_ms: float | None = None
    page_context_done_since_click_ms: float | None = None
    cancelled_selection_jobs: int = 0
    cancelled_page_context_jobs: int = 0
    background_deferred_for_selection: int = 0
    stale_or_missing: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "scenario": self.scenario,
            "generation": self.generation,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "static_lane": self.static_lane,
            "scroll_ready": self.scroll_ready,
            "perceived_ready_logged": self.perceived_ready_logged,
            "click_since_enter_ms": self.click_since_enter_ms,
            "click_to_highlight_ms": self.click_to_highlight_ms,
            "click_to_populate_enter_ms": self.click_to_populate_enter_ms,
            "ensure_identity_ms": self.ensure_identity_ms,
            "ensure_rows_ms": self.ensure_rows_ms,
            "preview_ms": self.preview_ms,
            "fields_ms": self.fields_ms,
            "layer_nav_ms": self.layer_nav_ms,
            "children_ms": self.children_ms,
            "populate_done_since_click_ms": self.populate_done_since_click_ms,
            "page_context_done_since_click_ms": self.page_context_done_since_click_ms,
            "cancelled_selection_jobs": self.cancelled_selection_jobs,
            "cancelled_page_context_jobs": self.cancelled_page_context_jobs,
            "background_deferred_for_selection": self.background_deferred_for_selection,
            "stale_or_missing": self.stale_or_missing,
            "flags": self.flags,
        }


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing perf log: {path}")
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _scenario_for_index(event_index: int, markers: list[tuple[int, str]]) -> str:
    scenario = "?"
    for marker_index, scenario_id in markers:
        if marker_index <= event_index:
            scenario = scenario_id
    return scenario


def _first_after(
    events: list[dict[str, Any]],
    start_index: int,
    *,
    event_name: str,
    generation: int | None = None,
    element_id: str | None = None,
) -> dict[str, Any] | None:
    for event in events[start_index:]:
        if event.get("event") != event_name:
            continue
        if generation is not None and event.get("generation") != generation:
            continue
        if element_id is not None and event.get("element_id") != element_id:
            continue
        return event
    return None


def _collect_stale_for_generation(
    events: list[dict[str, Any]],
    start_index: int,
    end_index: int,
    generation: int,
) -> list[str]:
    found: list[str] = []
    for event in events[start_index:end_index]:
        name = str(event.get("event", ""))
        if name not in STALE_EVENTS:
            continue
        if event.get("generation") == generation or event.get("current_generation") == generation:
            found.append(name)
    return found


def parse_clicks(events: list[dict[str, Any]]) -> list[ClickRow]:
    markers = [
        (index, str(event.get("scenario", "?")))
        for index, event in enumerate(events)
        if event.get("event") == SCENARIO_MARKER
    ]

    click_indices = [i for i, event in enumerate(events) if event.get("event") == CLICK_EVENT]
    rows: list[ClickRow] = []

    for row_index, click_idx in enumerate(click_indices):
        click = events[click_idx]
        generation = int(click.get("selection_generation_next", 0))
        element_id = str(click.get("element_id", ""))
        next_click_idx = click_indices[row_index + 1] if row_index + 1 < len(click_indices) else len(events)

        start_evt = _first_after(
            events,
            click_idx,
            event_name="studio.gicleeframe.selection.start",
            generation=generation,
            element_id=element_id,
        )
        element_type = str(start_evt.get("element_type", "")) if start_evt else ""

        highlight = _first_after(
            events,
            click_idx,
            event_name="studio.gicleeframe.selection.immediate_highlight_done",
            generation=generation,
            element_id=element_id,
        )
        populate_enter = _first_after(
            events,
            click_idx,
            event_name="studio.gicleeframe.selection.populate_enter",
            generation=generation,
            element_id=element_id,
        )
        populate_done = _first_after(
            events,
            click_idx,
            event_name="studio.gicleeframe.selection.populate_done",
            generation=generation,
            element_id=element_id,
        )
        page_context_done = _first_after(
            events,
            click_idx,
            event_name="studio.gicleeframe.selection.page_context.populate_done",
            generation=generation,
            element_id=element_id,
        )

        cancelled = _first_after(
            events,
            click_idx,
            event_name="studio.gicleeframe.selection.jobs_cancelled",
            generation=generation,
        )

        deferred_for_selection = sum(
            1
            for event in events[click_idx:next_click_idx]
            if event.get("event") == "studio.gicleeframe.background.deferred_for_selection"
            and event.get("generation") == generation
        )

        row = ClickRow(
            index=row_index + 1,
            scenario=_scenario_for_index(click_idx, markers),
            generation=generation,
            element_id=element_id,
            element_type=element_type,
            static_lane=click.get("static_lane"),
            scroll_ready=click.get("scroll_ready"),
            perceived_ready_logged=click.get("perceived_ready_logged"),
            click_since_enter_ms=_as_float(click.get("since_enter_ms")),
            click_to_highlight_ms=_as_float(highlight.get("since_click_ms")) if highlight else None,
            click_to_populate_enter_ms=_as_float(populate_enter.get("since_click_ms")) if populate_enter else None,
            populate_done_since_click_ms=_as_float(populate_done.get("since_click_ms")) if populate_done else None,
            page_context_done_since_click_ms=_as_float(page_context_done.get("since_click_ms"))
            if page_context_done
            else None,
            cancelled_selection_jobs=int(cancelled.get("selection_jobs_cancelled", 0)) if cancelled else 0,
            cancelled_page_context_jobs=int(cancelled.get("page_context_jobs_cancelled", 0)) if cancelled else 0,
            background_deferred_for_selection=deferred_for_selection,
            stale_or_missing=_collect_stale_for_generation(events, click_idx, next_click_idx, generation),
        )

        for attr, event_name in EDITOR_SEGMENTS:
            segment = _first_after(
                events,
                click_idx,
                event_name=event_name,
                generation=generation,
                element_id=element_id,
            )
            if segment is not None:
                setattr(row, attr, _as_float(segment.get("elapsed_ms")))

        if row.populate_done_since_click_ms is None and generation == max(
            int(events[i].get("selection_generation_next", 0))
            for i in click_indices
            if i <= click_idx
        ):
            row.flags.append("missing_populate_done")

        rows.append(row)

    return rows


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _fmt(value: float | int | bool | None, width: int = 8) -> str:
    if value is None:
        return "-".rjust(width)
    if isinstance(value, bool):
        return ("Y" if value else "N").rjust(width)
    if isinstance(value, float):
        return f"{value:.1f}".rjust(width)
    return str(value).rjust(width)


def format_table(rows: list[ClickRow]) -> str:
    headers = [
        "#",
        "scen",
        "gen",
        "type",
        "static",
        "scroll",
        "perc",
        "clk_enter",
        "->hl",
        "->pop_ent",
        "id_ms",
        "rows_ms",
        "prev_ms",
        "fld_ms",
        "nav_ms",
        "ch_ms",
        "pop_done",
        "ctx_done",
        "canc",
        "yield",
        "stale",
    ]
    lines = [" | ".join(headers), "-" * (len(headers) * 9)]

    for row in rows:
        stale = ",".join(
            name.split(".")[-1]
            for name in row.stale_or_missing[:2]
        )
        if len(row.stale_or_missing) > 2:
            stale += "+"
        canc = row.cancelled_selection_jobs + row.cancelled_page_context_jobs
        yield_count = row.background_deferred_for_selection
        lines.append(
            " | ".join(
                [
                    _fmt(row.index, 2),
                    row.scenario[:4].ljust(4),
                    _fmt(row.generation, 3),
                    (row.element_type or "?")[:12].ljust(12),
                    _fmt(row.static_lane, 6),
                    _fmt(row.scroll_ready, 6),
                    _fmt(row.perceived_ready_logged, 4),
                    _fmt(row.click_since_enter_ms, 9),
                    _fmt(row.click_to_highlight_ms, 4),
                    _fmt(row.click_to_populate_enter_ms, 8),
                    _fmt(row.ensure_identity_ms, 5),
                    _fmt(row.ensure_rows_ms, 7),
                    _fmt(row.preview_ms, 7),
                    _fmt(row.fields_ms, 6),
                    _fmt(row.layer_nav_ms, 6),
                    _fmt(row.children_ms, 5),
                    _fmt(row.populate_done_since_click_ms, 8),
                    _fmt(row.page_context_done_since_click_ms, 8),
                    _fmt(canc if canc else None, 4),
                    _fmt(yield_count if yield_count else None, 5),
                    stale or "-",
                ]
            )
        )
    return "\n".join(lines)


def _rows_for_scenario(rows: list[ClickRow], scenario: str) -> list[ClickRow]:
    return [row for row in rows if row.scenario == scenario]


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 2)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def analyze_scenarios(events: list[dict[str, Any]], rows: list[ClickRow]) -> dict[str, Any]:
    report: dict[str, Any] = {}

    # Scenario A — first clicks after full ready
    scenario_a = _rows_for_scenario(rows, "A")
    a_after_scroll = [r for r in scenario_a if r.scroll_ready is True]
    report["A"] = {
        "clicks": len(scenario_a),
        "after_scroll_ready": len(a_after_scroll),
        "ensure_identity_ok": all((r.ensure_identity_ms or 0) <= 2 for r in a_after_scroll) if a_after_scroll else None,
        "ensure_rows_under_10ms": all((r.ensure_rows_ms or 999) < 10 for r in a_after_scroll) if a_after_scroll else None,
        "first_divider_populate_done_ms": next(
            (r.populate_done_since_click_ms for r in a_after_scroll if r.element_type == "divider"),
            None,
        ),
        "media_section_populate_done_ms": next(
            (r.populate_done_since_click_ms for r in a_after_scroll if r.element_type == "media_section"),
            None,
        ),
        "verdict": None,
    }
    a = report["A"]
    if a_after_scroll:
        a["verdict"] = (
            a["ensure_identity_ok"]
            and a["ensure_rows_under_10ms"]
            and (a["first_divider_populate_done_ms"] or 999) <= 120
            and (a["media_section_populate_done_ms"] or 999) <= 120
        )

    # Scenario B — early click before scroll upgrade
    scenario_b = _rows_for_scenario(rows, "B")
    preserved = [e for e in events if e.get("event") == "studio.gicleeframe.selection.preserved_after_inventory_light"]
    repopulate = [
        e for e in events if e.get("event") == "studio.gicleeframe.selection.repopulate_after_inventory_scheduled"
    ]
    stale_missing = [
        e for e in events if e.get("event") == "studio.gicleeframe.populate_editor.deferred_missing_or_stale"
    ]
    b_early = [r for r in scenario_b if r.static_lane is True and r.scroll_ready is False]
    report["B"] = {
        "early_clicks": len(b_early),
        "preserved_events": len(preserved),
        "repopulate_events": len(repopulate),
        "deferred_missing_or_stale": len(stale_missing),
        "early_click_populate_done": [r.populate_done_since_click_ms for r in b_early if r.populate_done_since_click_ms],
        "verdict": len(b_early) > 0 and not stale_missing and any(r.populate_done_since_click_ms for r in b_early),
    }

    # Scenario C — rapid clicking
    scenario_c = _rows_for_scenario(rows, "C")
    last_gen = max((r.generation for r in scenario_c), default=0)
    last_row = next((r for r in reversed(scenario_c) if r.generation == last_gen), None)
    stale_final_populate = [
        r
        for r in scenario_c
        if r.generation != last_gen and r.populate_done_since_click_ms is not None and r.stale_or_missing
    ]
    report["C"] = {
        "rapid_clicks": len(scenario_c),
        "cancelled_total": sum(r.cancelled_selection_jobs + r.cancelled_page_context_jobs for r in scenario_c),
        "last_generation": last_gen,
        "last_has_populate_done": bool(last_row and last_row.populate_done_since_click_ms),
        "older_generations_with_populate_done": len(
            [r for r in scenario_c if r.generation != last_gen and r.populate_done_since_click_ms]
        ),
        "verdict": bool(
            scenario_c
            and last_row
            and last_row.populate_done_since_click_ms
            and len([r for r in scenario_c if r.generation != last_gen and r.populate_done_since_click_ms]) == 0
        ),
    }

    # Scenario D — page context first vs second use
    scenario_d = _rows_for_scenario(rows, "D")
    by_type: dict[str, list[float | None]] = {}
    for row in scenario_d:
        by_type.setdefault(row.element_type, []).append(row.page_context_done_since_click_ms)
    ctx_compare: dict[str, Any] = {}
    for etype, values in by_type.items():
        nums = [v for v in values if v is not None]
        if len(nums) >= 2:
            ctx_compare[etype] = {
                "first_ms": nums[0],
                "second_ms": nums[1],
                "delta_ms": round(nums[0] - nums[1], 2),
                "first_use_slow": nums[0] >= 300 and nums[1] < nums[0] * 0.6,
            }
    report["D"] = {
        "comparisons": ctx_compare,
        "page_context_first_use_problem": any(v.get("first_use_slow") for v in ctx_compare.values()),
        "verdict": bool(ctx_compare),
    }

    # Scenario E — click during late background work (~0.8–1.5s after enter)
    scenario_e = _rows_for_scenario(rows, "E")
    late_control = [
        e
        for e in events
        if e.get("event")
        in {
            "studio.gicleeframe.control.deferred_readiness_late",
            "studio.gicleeframe.control.deferred_safety_late",
        }
    ]
    e_outliers = [
        r
        for r in scenario_e
        if (r.click_to_populate_enter_ms or 0) > 80 or (r.populate_done_since_click_ms or 0) > 150
    ]
    report["E"] = {
        "clicks": len(scenario_e),
        "click_since_enter_ms": [r.click_since_enter_ms for r in scenario_e],
        "populate_done_ms": [r.populate_done_since_click_ms for r in scenario_e],
        "late_control_events": len(late_control),
        "outliers": len(e_outliers),
        "verdict": len(scenario_e) > 0 and len(e_outliers) == 0,
    }

    # Global S.2A / S.2B checks
    all_rows_ms = [r.ensure_rows_ms for r in rows if r.ensure_rows_ms is not None]
    populate_enter_ms = [r.click_to_populate_enter_ms for r in rows if r.click_to_populate_enter_ms is not None]
    after_scroll = [r for r in rows if r.scroll_ready is True]
    populate_enter_after_scroll = [
        r.click_to_populate_enter_ms for r in after_scroll if r.click_to_populate_enter_ms is not None
    ]
    report["global"] = {
        "total_clicks": len(rows),
        "ensure_rows_median_ms": _median(all_rows_ms),
        "ensure_rows_max_ms": max(all_rows_ms) if all_rows_ms else None,
        "ensure_rows_under_10ms_all": all(v < 10 for v in all_rows_ms) if all_rows_ms else None,
        "populate_enter_median_ms": _median(populate_enter_ms),
        "populate_enter_max_ms": max(populate_enter_ms) if populate_enter_ms else None,
        "populate_enter_after_scroll_median_ms": _median(populate_enter_after_scroll),
        "populate_enter_after_scroll_max_ms": max(populate_enter_after_scroll)
        if populate_enter_after_scroll
        else None,
        "populate_enter_under_50ms_after_scroll": all(v < 50 for v in populate_enter_after_scroll)
        if populate_enter_after_scroll
        else None,
        "populate_enter_outliers_over_120ms": len(
            [v for v in populate_enter_after_scroll if v > 120]
        ),
        "background_deferred_total": sum(
            1 for event in events if event.get("event") == "studio.gicleeframe.background.deferred_for_selection"
        ),
        "priority_start_events": sum(
            1 for event in events if event.get("event") == "studio.gicleeframe.selection.priority_start"
        ),
    }

    # Recommendation heuristic
    ctx_slow = report["D"].get("page_context_first_use_problem")
    preview_slow = any((r.preview_ms or 0) > 30 for r in a_after_scroll)
    populate_slow = not report["global"].get("populate_enter_under_50ms_after_scroll", True)
    late_outliers = report["E"].get("outliers", 0) > 0
    rows_slow = not report["global"].get("ensure_rows_under_10ms_all", True)

    if rows_slow:
        rec = "E: ensure_rows still above 10ms - revisit rows warmup (S.2A follow-up)"
    elif populate_slow:
        rec = "F: S.2B populate_enter still above 50ms after scroll ready"
    elif ctx_slow:
        rec = "B: S.2B page context first-use polish"
    elif preview_slow:
        rec = "C: S.2C preview polish"
    elif late_outliers:
        rec = "D: R.1 control late work polish"
    elif report["A"].get("verdict") and report["B"].get("verdict") and report["C"].get("verdict"):
        rec = "A: STOP / checkpoint — selection path meets S.2B verify criteria"
    else:
        rec = "Review per-scenario verdicts; mixed signals"

    report["recommendation"] = rec
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze GICLÉE FRAME selection perf log")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="Path to studio_perf.log")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text report")
    args = parser.parse_args()

    try:
        events = load_events(args.log)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    rows = parse_clicks(events)
    report = analyze_scenarios(events, rows)

    if args.json:
        print(
            json.dumps(
                {"clicks": [row.to_dict() for row in rows], "report": report},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"Log: {args.log}")
    print(f"Clicks parsed: {len(rows)}")
    print()
    print(format_table(rows))
    print()
    print("--- scenario verdicts ---")
    for key in ("A", "B", "C", "D", "E"):
        section = report.get(key, {})
        verdict = section.get("verdict")
        label = "PASS" if verdict else ("FAIL" if verdict is False else "N/A")
        print(f"{key}: {label}  {json.dumps(section, ensure_ascii=False)}")
    print()
    print("--- global S.2A / S.2B ---")
    print(json.dumps(report["global"], ensure_ascii=False, indent=2))
    print()
    print("Recommendation:", report["recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
