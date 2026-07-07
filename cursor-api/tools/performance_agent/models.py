"""Shared dataclasses for Performance Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SessionStatus = Literal["completed", "quit_early", "in_progress"]
SessionMode = Literal["manual", "run"]


@dataclass(frozen=True)
class ScenarioDefinition:
    id: str
    display_title: str
    click_path: tuple[str, ...] = ()
    goal: str = ""
    observe: tuple[str, ...] = ()
    success_hint: str = ""
    expected_event_patterns: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        """Read-only alias for legacy code paths (questionnaire, ScenarioRun)."""
        return self.display_title

    @property
    def instruction(self) -> str:
        """Legacy fallback — flattened structured fields for old consumers."""
        parts: list[str] = []
        if self.click_path:
            parts.extend(self.click_path)
        if self.goal:
            parts.append(self.goal)
        if self.observe:
            parts.extend(self.observe)
        if self.success_hint:
            parts.append(self.success_hint)
        return "\n".join(parts)


@dataclass
class ScenarioRun:
    scenario_id: str
    scenario_name: str
    start_ts: str | None = None
    end_ts: str | None = None
    duration_ms: float | None = None
    completed: bool = False
    skipped: bool = False
    answers: dict[str, Any] = field(default_factory=dict)

    @property
    def display_title(self) -> str:
        """Human-readable title stored in scenario_name at runtime."""
        return self.scenario_name

    def to_timeline_row(self, *, log_coverage_status: str = "") -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "display_title": self.scenario_name,
            "start_ts": self.start_ts or "",
            "end_ts": self.end_ts or "",
            "duration_ms": "" if self.duration_ms is None else round(self.duration_ms, 2),
            "completed": self.completed,
            "skipped": self.skipped,
            "log_coverage_status": log_coverage_status,
            "smoothness_score": self.answers.get("smoothness_score", ""),
            "main_complaint": self.answers.get("main_complaint", ""),
            "note": self.answers.get("note", ""),
        }


@dataclass
class ManualSession:
    profile_id: str
    report_dir: Path
    started_at: str
    log_path: Path
    scenarios: list[ScenarioRun] = field(default_factory=list)
    agent_events: list[dict[str, Any]] = field(default_factory=list)
    status: SessionStatus = "in_progress"
    log_missing: bool = False
    ended_at: str | None = None
    session_mode: SessionMode = "manual"
    studio_pid: int | None = None
    studio_left_running: bool = False
    studio_start_failed: bool = False
    log_lifecycle: dict[str, Any] | None = None

    def completed_scenarios(self) -> list[ScenarioRun]:
        return [s for s in self.scenarios if s.completed and not s.skipped]

    def to_questions_answers_dict(self) -> dict[str, Any]:
        return {
            "mode": self.session_mode,
            "profile_id": self.profile_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "log_missing": self.log_missing,
            "scenarios": [
                {
                    "scenario_id": run.scenario_id,
                    "scenario_name": run.scenario_name,
                    "display_title": run.scenario_name,
                    "skipped": run.skipped,
                    "completed": run.completed,
                    "start_ts": run.start_ts,
                    "end_ts": run.end_ts,
                    "answers": run.answers,
                }
                for run in self.scenarios
            ],
        }
