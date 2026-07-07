"""Manual scenario wizard for Performance Agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from tools.performance_agent.models import ManualSession, ScenarioDefinition, ScenarioRun
from tools.performance_agent.profiles import AppProfile
from tools.performance_agent.questionnaire import QuestionnaireIO, SimpleIO, ask_scenario, answers_from_dict
from tools.performance_agent.report.generator import make_report_dir
from tools.performance_agent.timeutil import duration_ms_between, utc_now_iso


class WizardIO(Protocol):
    def input(self, prompt: str) -> str: ...
    def print(self, text: str) -> None: ...


@dataclass
class WizardConfig:
    auto_answers: dict[str, dict] | None = None
    skip_scenarios: set[str] | None = None
    quit_after_scenario: str | None = None


def _append_agent_event(session: ManualSession, event: dict) -> None:
    session.agent_events.append(event)
    path = session.report_dir / "agent_events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _emit(
    session: ManualSession,
    event_name: str,
    **fields: object,
) -> None:
    payload: dict[str, object] = {"ts": utc_now_iso(), "event": event_name}
    payload.update(fields)
    _append_agent_event(session, payload)


def print_intro(
    profile: AppProfile,
    io: WizardIO,
    *,
    studio_launched: bool = False,
    studio_pid: int | None = None,
) -> bool:
    io.print("=== Performance Agent — manual wizard ===\n")
    if studio_launched:
        pid_text = f" (PID {studio_pid})" if studio_pid else ""
        io.print(f"Studio uruchomione przez Performance Agent{pid_text}.")
        io.print("Env ustawione automatycznie:")
        for key, value in profile.studio_env_hints.items():
            io.print(f"  {key}={value}")
    else:
        io.print("Uruchom Studio samodzielnie:")
        io.print("  python -m giclee_app.studio_preview\n")
        io.print("Ustaw env przed startem Studio:")
        for key, value in profile.studio_env_hints.items():
            io.print(f"  {key}={value}")
    io.print("")
    answer = io.input("Kontynuować wizard? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _format_scenario_display(
    io: WizardIO,
    scenario: ScenarioDefinition,
    *,
    index: int,
    total: int,
) -> None:
    io.print(f"\n[{index}/{total}] {scenario.display_title}")

    if scenario.click_path:
        io.print("\nCo kliknąć:")
        for step_no, step in enumerate(scenario.click_path, start=1):
            io.print(f"  {step_no}. {step}")

    if scenario.goal:
        io.print(f"\nCel: {scenario.goal}")

    if scenario.observe:
        io.print("\nCo obserwować:")
        for item in scenario.observe:
            io.print(f"  - {item}")

    if scenario.success_hint:
        io.print("\nKiedy nacisnąć Enter:")
        io.print(f"  {scenario.success_hint}")

    if scenario.expected_event_patterns:
        patterns = ", ".join(scenario.expected_event_patterns)
        io.print(f"\nOczekiwane sygnały w logu:\n  {patterns}")


def _scenario_action(
    io: WizardIO,
    scenario: ScenarioDefinition,
    *,
    index: int = 1,
    total: int = 1,
) -> str:
    _format_scenario_display(io, scenario, index=index, total=total)
    io.print("")
    action = io.input("Enter=start | s=skip | q=quit: ").strip().lower()
    if action in {"s", "skip"}:
        return "skip"
    if action in {"q", "quit"}:
        return "quit"
    return "run"


def run_scenario(
    session: ManualSession,
    scenario: ScenarioDefinition,
    io: WizardIO,
    config: WizardConfig | None = None,
    *,
    index: int = 1,
    total: int = 1,
) -> str:
    """Run one scenario. Returns: continue | quit."""
    config = config or WizardConfig()
    action = "skip" if config.skip_scenarios and scenario.id in config.skip_scenarios else _scenario_action(
        io, scenario, index=index, total=total
    )

    if action == "quit":
        run = ScenarioRun(
            scenario_id=scenario.id,
            scenario_name=scenario.display_title,
            completed=False,
            skipped=False,
        )
        session.scenarios.append(run)
        _emit(session, "agent.scenario.quit_requested", scenario_id=scenario.id)
        return "quit"

    if action == "skip":
        run = ScenarioRun(
            scenario_id=scenario.id,
            scenario_name=scenario.display_title,
            completed=False,
            skipped=True,
        )
        session.scenarios.append(run)
        _emit(
            session,
            "agent.scenario.skipped",
            scenario_id=scenario.id,
            scenario_name=scenario.display_title,
        )
        return "continue"

    start_ts = utc_now_iso()
    _emit(
        session,
        "agent.scenario.start",
        scenario_id=scenario.id,
        scenario_name=scenario.display_title,
    )
    io.print("Wykonaj kroki powyżej w Studio, poczekaj zgodnie z instrukcją, potem naciśnij Enter.")
    io.print("(Scenariusz zostanie porównany z logiem performance po zakończeniu sesji.)")
    io.input("[Enter] scenariusz zakończony: ")

    end_ts = utc_now_iso()
    duration = duration_ms_between(start_ts, end_ts)

    q_io: QuestionnaireIO = io  # type: ignore[assignment]
    if config.auto_answers and scenario.id in config.auto_answers:
        qa = answers_from_dict(config.auto_answers[scenario.id])
        qa.setdefault("scenario_id", scenario.id)
        qa.setdefault("scenario_name", scenario.display_title)
        qa.setdefault("skipped", False)
    else:
        qa = ask_scenario(scenario.id, scenario.display_title, q_io, skipped=False)

    answers = qa.get("answers", {})
    run = ScenarioRun(
        scenario_id=scenario.id,
        scenario_name=scenario.display_title,
        start_ts=start_ts,
        end_ts=end_ts,
        duration_ms=duration,
        completed=True,
        skipped=False,
        answers=answers,
    )
    session.scenarios.append(run)

    _emit(
        session,
        "agent.scenario.end",
        scenario_id=scenario.id,
        scenario_name=scenario.display_title,
        duration_ms=duration,
    )
    for question_id, value in answers.items():
        _emit(
            session,
            "agent.question.answer",
            scenario_id=scenario.id,
            question_id=question_id,
            answer=value,
            note=answers.get("note", ""),
        )

    if config.quit_after_scenario == scenario.id:
        return "quit"
    return "continue"


def run_wizard(
    profile: AppProfile,
    *,
    report_dir: Path | None = None,
    log_path: Path | None = None,
    io: WizardIO | None = None,
    config: WizardConfig | None = None,
    studio_launched: bool = False,
    studio_pid: int | None = None,
    session_mode: str = "manual",
    session: ManualSession | None = None,
) -> ManualSession:
    if io is None:
        io = SimpleIO(input_fn=input, print_fn=print)  # type: ignore[assignment]

    out_dir = report_dir or (session.report_dir if session else make_report_dir(profile))
    out_dir.mkdir(parents=True, exist_ok=True)

    resolved_log = profile.resolve_log_path(log_path)

    if session is None:
        session = ManualSession(
            profile_id=profile.id,
            report_dir=out_dir,
            started_at=utc_now_iso(),
            log_path=resolved_log,
            session_mode=session_mode,  # type: ignore[arg-type]
            studio_pid=studio_pid,
        )
        _emit(session, "agent.session.start", profile_id=profile.id, log_path=str(resolved_log))
    else:
        session.studio_pid = studio_pid or session.studio_pid

    if not print_intro(profile, io, studio_launched=studio_launched, studio_pid=studio_pid):
        session.status = "quit_early"
        session.ended_at = utc_now_iso()
        _emit(session, "agent.session.cancelled", reason="intro_declined")
        return session

    total = len(profile.manual_scenarios)
    for index, scenario in enumerate(profile.manual_scenarios, start=1):
        result = run_scenario(session, scenario, io, config=config, index=index, total=total)
        if result == "quit":
            session.status = "quit_early"
            break
    else:
        session.status = "completed"

    session.ended_at = utc_now_iso()
    _emit(session, "agent.session.end", status=session.status)
    return session
