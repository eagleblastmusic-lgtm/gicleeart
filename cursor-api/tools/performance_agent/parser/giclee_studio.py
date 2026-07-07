"""GicleeApp Studio log parser orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tools.performance_agent.parser.heuristics import HeuristicsResult, detect_heuristics
from tools.performance_agent.parser.jsonl_loader import LoadResult, PerfEvent, load_jsonl
from tools.performance_agent.parser.metrics import MetricsResult, compute_metrics
from tools.performance_agent.profiles import AppProfile, Budgets


@dataclass
class ParseResult:
    events: list[PerfEvent]
    load: LoadResult
    metrics: MetricsResult
    heuristics: HeuristicsResult
    budgets: Budgets = field(default_factory=Budgets)

    def to_summary_dict(self, *, profile_id: str, source_log: Path, report_dir: Path) -> dict:
        return {
            "profile_id": profile_id,
            "source_log": str(source_log),
            "report_dir": str(report_dir),
            "total_events": self.metrics.total_events,
            "malformed_lines": self.metrics.malformed_lines,
            "event_counts_by_prefix": self.metrics.event_counts_by_prefix,
            "slow_event_count": len(self.metrics.slow_events),
            "suspect_count": len(self.heuristics.suspects),
            "metrics": self.metrics.to_dict(),
            "heuristics": self.heuristics.to_dict(),
            "readiness_timeline": [entry.to_dict() for entry in self.metrics.readiness_timeline],
            "budgets": {
                "slow_event_warning_ms": self.budgets.slow_event_warning_ms,
                "slow_event_major_ms": self.budgets.slow_event_major_ms,
                "details_cta_warning_ms": self.budgets.details_cta_warning_ms,
                "details_cta_major_ms": self.budgets.details_cta_major_ms,
            },
        }


def parse_giclee_studio_log(path: Path, *, budgets: Budgets | None = None) -> ParseResult:
    load = load_jsonl(path)
    active_budgets = budgets or Budgets()
    metrics = compute_metrics(load.events, malformed_lines=load.malformed_lines, budgets=active_budgets)
    heuristics = detect_heuristics(load.events, active_budgets)
    return ParseResult(
        events=load.events,
        load=load,
        metrics=metrics,
        heuristics=heuristics,
        budgets=active_budgets,
    )


def parse_for_profile(path: Path, profile: AppProfile) -> ParseResult:
    return parse_giclee_studio_log(path, budgets=profile.budgets)
