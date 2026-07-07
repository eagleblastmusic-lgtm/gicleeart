"""Session orchestration for Performance Agent."""

from __future__ import annotations

from pathlib import Path

from tools.performance_agent.collector import CollectionResult, collect_log
from tools.performance_agent.log_lifecycle import (
    LogLifecycleMode,
    apply_log_lifecycle,
    archive_root,
    prompt_log_lifecycle_mode,
)
from tools.performance_agent.models import ManualSession
from tools.performance_agent.parser.giclee_studio import parse_for_profile
from tools.performance_agent.process import (
    launch_studio,
    prompt_shutdown_studio,
    shutdown_studio,
    wait_startup_grace,
)
from tools.performance_agent.profiles import AppProfile, get_profile
from tools.performance_agent.report.generator import ReportBundle, generate_report, make_report_dir
from tools.performance_agent.timeutil import utc_now_iso
from tools.performance_agent.wizard import WizardConfig, WizardIO, _emit, run_wizard


def _finalize_report(
    profile: AppProfile,
    session: ManualSession,
    report_dir: Path,
) -> ReportBundle:
    source_log = session.log_path
    collection: CollectionResult | None = None
    parse = None

    if source_log.exists():
        collection = collect_log(source_log, report_dir)
        parse = parse_for_profile(collection.events_jsonl, profile)
    else:
        session.log_missing = True

    return generate_report(
        profile=profile,
        collection=collection,
        parse=parse,
        report_dir=report_dir,
        session=session,
    )


def run_manual(
    *,
    profile_id: str = "giclee_studio",
    log_path: Path | None = None,
    output_dir: Path | None = None,
    io: WizardIO | None = None,
    config: WizardConfig | None = None,
) -> ReportBundle:
    profile = get_profile(profile_id)
    report_dir = output_dir or make_report_dir(profile)

    session = run_wizard(
        profile,
        report_dir=report_dir,
        log_path=log_path,
        io=io,
        config=config,
        session_mode="manual",
    )

    return _finalize_report(profile, session, report_dir)


def run_with_studio(
    *,
    profile_id: str = "giclee_studio",
    log_path: Path | None = None,
    output_dir: Path | None = None,
    io: WizardIO | None = None,
    config: WizardConfig | None = None,
    lifecycle_mode: LogLifecycleMode | None = None,
) -> ReportBundle:
    profile = get_profile(profile_id)
    report_dir = output_dir or make_report_dir(profile)
    report_dir.mkdir(parents=True, exist_ok=True)

    if io is None:
        from tools.performance_agent.questionnaire import SimpleIO

        io = SimpleIO(input_fn=input, print_fn=print)  # type: ignore[assignment]

    resolved_log = profile.resolve_log_path(log_path)
    mode = lifecycle_mode or prompt_log_lifecycle_mode(io)
    lifecycle_result = apply_log_lifecycle(
        resolved_log,
        mode,
        archive_dir=archive_root(profile.resolve_output_root()),
    )

    session = ManualSession(
        profile_id=profile.id,
        report_dir=report_dir,
        started_at=utc_now_iso(),
        log_path=resolved_log,
        session_mode="run",
        log_lifecycle=lifecycle_result.to_dict(),
    )
    _emit(
        session,
        "agent.log_lifecycle.applied",
        mode=lifecycle_result.mode,
        archived_to=str(lifecycle_result.archived_to) if lifecycle_result.archived_to else None,
    )

    studio_proc = None
    studio_start_failed = False
    try:
        studio_proc = launch_studio(profile)
        session.studio_pid = studio_proc.pid
        _emit(
            session,
            "agent.studio.launched",
            pid=studio_proc.pid,
            command=studio_proc.command,
        )

        if not wait_startup_grace(studio_proc):
            studio_start_failed = True
            session.studio_start_failed = True
            exit_code = studio_proc.popen.poll()
            io.print(
                f"\nWARNING: Studio (PID {studio_proc.pid}) zakończyło się zaraz po starcie "
                f"(exit={exit_code}). Kontynuuję wizard — raport będzie partial.\n"
            )
            _emit(
                session,
                "agent.studio.start_failed",
                pid=studio_proc.pid,
                exit_code=exit_code,
            )
    except OSError as exc:
        studio_start_failed = True
        session.studio_start_failed = True
        io.print(f"\nWARNING: Nie udało się uruchomić Studio: {exc}")
        io.print("Kontynuuję wizard — raport będzie partial.\n")
        _emit(session, "agent.studio.launch_error", error=str(exc))

    session = run_wizard(
        profile,
        report_dir=report_dir,
        log_path=resolved_log,
        io=io,
        config=config,
        studio_launched=studio_proc is not None and not studio_start_failed,
        studio_pid=session.studio_pid,
        session_mode="run",
        session=session,
    )

    if studio_proc is not None and studio_proc.is_running():
        if prompt_shutdown_studio(studio_proc, io):
            exit_code = shutdown_studio(studio_proc, io)
            _emit(session, "agent.studio.shutdown", pid=studio_proc.pid, exit_code=exit_code)
            session.studio_left_running = False
        else:
            _emit(session, "agent.studio.left_running", pid=studio_proc.pid)
            session.studio_left_running = True
    elif studio_proc is not None:
        _emit(
            session,
            "agent.studio.ended_before_shutdown",
            pid=studio_proc.pid,
            exit_code=studio_proc.popen.poll(),
        )

    session.log_lifecycle = lifecycle_result.to_dict()
    session.studio_start_failed = studio_start_failed

    return _finalize_report(profile, session, report_dir)
