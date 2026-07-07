from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.parser.giclee_studio import parse_giclee_studio_log
from tools.performance_agent.parser.heuristics import detect_heuristics
from tools.performance_agent.parser.jsonl_loader import load_jsonl
from tools.performance_agent.profiles import Budgets


def _write_log(tmp_path: Path, rows: list[dict]) -> Path:
    log = tmp_path / "studio_perf.log"
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log


def test_load_jsonl_parses_fields_and_malformed(tmp_path: Path) -> None:
    log = tmp_path / "perf.log"
    log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-07-07T12:00:00+00:00",
                        "event": "studio.gicleeframe.selection.click",
                        "elapsed_ms": 12.5,
                        "since_click_ms": 3.0,
                        "module": "preview",
                        "stage": "shell",
                        "element_id": "sec-1",
                        "generation": 2,
                    }
                ),
                "not-json",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    load = load_jsonl(log)
    assert load.total_lines == 3
    assert load.malformed_lines == 2
    assert len(load.events) == 1

    event = load.events[0]
    assert event.line_no == 1
    assert event.event == "studio.gicleeframe.selection.click"
    assert event.elapsed_ms == 12.5
    assert event.since_click_ms == 3.0
    assert event.module == "preview"
    assert event.stage == "shell"
    assert event.generation == 2


def test_top_slow_events(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {"event": "studio.dashboard.build.critical", "elapsed_ms": 50},
            {"event": "studio.gicleeframe.build_shell", "elapsed_ms": 250},
            {"event": "studio.hub.visual.full_ready", "elapsed_ms": 90},
        ],
    )
    result = parse_giclee_studio_log(log)
    assert result.metrics.total_events == 3
    assert result.metrics.slow_events[0].event == "studio.gicleeframe.build_shell"
    assert result.metrics.slow_events[0].severity == "major"
    assert len(result.metrics.slow_events) == 2


def test_event_prefix_grouping(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {"event": "studio.dashboard.visual.visible_ready"},
            {"event": "studio.hub.visual.visible_ready"},
            {"event": "studio.gicleeframe.details_shell.applied"},
            {"event": "studio.gicleeframe.visual.perceived_ready"},
            {"event": "studio.show_view.deferred_factory"},
            {"event": "other.event"},
        ],
    )
    result = parse_giclee_studio_log(log)
    counts = result.metrics.event_counts_by_prefix
    assert counts["studio.dashboard"] == 1
    assert counts["studio.hub"] == 1
    assert counts["studio.gicleeframe.details"] == 1
    assert counts["studio.gicleeframe"] == 1
    assert counts["studio.show_view"] == 1
    assert counts["other"] == 1


def test_heuristic_skeleton_before_reveal_lower_priority(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {"event": "studio.gicleeframe.control.skeleton_enter", "elapsed_ms": 10},
            {"event": "studio.gicleeframe.atomic_reveal.revealed", "since_enter_ms": 100},
        ],
    )
    load = load_jsonl(log)
    heuristics = detect_heuristics(load.events, Budgets())
    before = next(s for s in heuristics.suspects if s.line_no == 1)
    assert before.id == "SKELETON_LAYOUT_SUSPECT"
    assert before.priority == "P2"
    assert before.phase == "before_reveal"


def test_heuristic_skeleton_after_reveal_higher_priority(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {"event": "studio.gicleeframe.atomic_reveal.revealed", "since_enter_ms": 100},
            {"event": "studio.gicleeframe.section_list.scroll_upgrade", "elapsed_ms": 40},
        ],
    )
    load = load_jsonl(log)
    heuristics = detect_heuristics(load.events, Budgets())
    scroll = next(s for s in heuristics.suspects if "scroll_upgrade" in (s.event or ""))
    assert scroll.priority in {"P0", "P1"}
    assert scroll.phase in {"after_reveal", "after_click"}


def test_heuristic_skeleton_suspect(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [{"event": "studio.gicleeframe.editor.skeleton_ready", "elapsed_ms": 10}],
    )
    load = load_jsonl(log)
    heuristics = detect_heuristics(load.events, Budgets())
    assert any(s.id == "SKELETON_LAYOUT_SUSPECT" for s in heuristics.suspects)


def test_heuristic_visible_work_after_reveal(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {"event": "studio.gicleeframe.visual.perceived_ready", "since_enter_ms": 100},
            {"event": "studio.gicleeframe.section_list.scroll_upgrade", "elapsed_ms": 40},
        ],
    )
    load = load_jsonl(log)
    heuristics = detect_heuristics(load.events, Budgets())
    assert any(s.id == "VISIBLE_WORK_AFTER_REVEAL" for s in heuristics.suspects)


def test_heuristic_details_slow_major(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {
                "event": "studio.gicleeframe.details_module.applied",
                "since_request_ms": 750,
            }
        ],
    )
    load = load_jsonl(log)
    heuristics = detect_heuristics(load.events, Budgets())
    assert any(s.id == "DETAILS_CTA_SLOW" and s.priority == "P0" for s in heuristics.suspects)


def test_heuristic_full_auto_details_regression(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {"event": "studio.gicleeframe.details_shell.applied", "since_request_ms": 50},
            {"event": "studio.gicleeframe.preview.update.done", "since_request_ms": 120},
        ],
    )
    load = load_jsonl(log)
    heuristics = detect_heuristics(load.events, Budgets())
    assert any(s.id == "FULL_AUTO_DETAILS_REGRESSION" for s in heuristics.suspects)


def test_heuristic_cache_followed_by_populate(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        [
            {
                "event": "studio.gicleeframe.details_module.cache_hit",
                "cache_hit": True,
            },
            {"event": "studio.gicleeframe.selection.populate_done", "elapsed_ms": 30},
        ],
    )
    load = load_jsonl(log)
    heuristics = detect_heuristics(load.events, Budgets())
    assert any(s.id == "CACHE_UX_CONFLICT" for s in heuristics.suspects)
