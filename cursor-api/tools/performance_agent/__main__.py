"""CLI entrypoint for Performance Agent."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from tools.performance_agent import __version__
from tools.performance_agent.clipboard import (
    ClipboardCopyError,
    copy_text_to_clipboard,
    describe_clipboard_support,
)
from tools.performance_agent.collector import collect_log
from tools.performance_agent.parser.giclee_studio import parse_for_profile
from tools.performance_agent.profiles import get_profile, list_profiles
from tools.performance_agent.report.analyzer import (
    ReportComparison,
    analyze_report_dir,
    compare_report_bundles,
    format_report_analysis,
    format_report_comparison,
    resolve_report_dir,
)
from tools.performance_agent.report.generator import generate_report, make_report_dir
from tools.performance_agent.report.insights import (
    build_cursor_prompt,
    build_hotspot_summary,
    build_timeline_summary,
    format_hotspot_summary,
    format_timeline_summary,
)
from tools.performance_agent.report.coverage import (
    build_coverage_prompt,
    build_coverage_summary,
    build_run_playbook,
    build_scenario_checklist,
    format_coverage_summary,
    format_scenario_checklist,
)
from tools.performance_agent.report.history import (
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    build_analysis_prompt_with_history,
    build_report_history,
    build_trend_summary,
    compare_baseline_to_latest,
    format_baseline_candidate,
    format_baseline_comparison,
    format_report_history,
    format_trend_summary,
    select_baseline_candidate,
    validate_history_limit,
)
from tools.performance_agent.report.index import (
    CopyBlockNotFoundError,
    ReportIndexEntry,
    discover_report_dirs,
    evaluate_report_health,
    extract_copy_for_chatgpt,
    format_doctor_status,
    format_latest_report,
    format_no_reports_message,
    format_open_latest_paths,
    format_prepare_chatgpt_prep,
    format_report_health,
    format_report_list,
    summarize_report_bundle,
)
from tools.performance_agent.runner import run_manual, run_with_studio


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="performance_agent",
        description="Performance Agent — audit tooling for GicleeApp Studio",
    )
    parser.add_argument(
        "--profile",
        default="giclee_studio",
        help=f"App profile (default: giclee_studio). Known: {', '.join(list_profiles())}",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse existing perf log and generate report bundle (PA-1A)",
    )
    mode.add_argument(
        "--manual",
        action="store_true",
        help="Manual scenario wizard + UX questionnaire (PA-1B)",
    )
    mode.add_argument(
        "--wizard",
        action="store_true",
        help="Alias for --manual",
    )
    mode.add_argument(
        "--run",
        action="store_true",
        help="Launch Studio subprocess + manual wizard (PA-1C)",
    )
    mode.add_argument(
        "--launch",
        action="store_true",
        help="Alias for --run",
    )
    mode.add_argument(
        "--latest",
        action="store_true",
        help="Inspect the newest report bundle without running Studio (PA-1D)",
    )
    mode.add_argument(
        "--list-reports",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="List N newest report bundles (default: 10) without running Studio (PA-1D)",
    )
    mode.add_argument(
        "--chatgpt-latest",
        action="store_true",
        help="Print COPY FOR CHATGPT block from the newest report bundle (PA-1E)",
    )
    mode.add_argument(
        "--health-latest",
        action="store_true",
        help="Assess readiness of the newest report bundle for analysis (PA-1G)",
    )
    mode.add_argument(
        "--prepare-chatgpt-latest",
        action="store_true",
        help=(
            "Health-gated COPY FOR CHATGPT block copy to clipboard with operator output (PA-1I)"
        ),
    )
    mode.add_argument(
        "--open-latest",
        action="store_true",
        help="Open newest report directory in Explorer (read-only, PA-1I)",
    )
    mode.add_argument(
        "--doctor",
        action="store_true",
        help="Show read-only Performance Agent status (PA-1I)",
    )
    mode.add_argument(
        "--analyze-latest",
        action="store_true",
        help="Local diagnostic analysis of the newest report bundle (read-only, PA-2A)",
    )
    mode.add_argument(
        "--analyze-report",
        metavar="PATH",
        type=Path,
        help="Local diagnostic analysis of a specific report bundle (read-only, PA-2A)",
    )
    mode.add_argument(
        "--compare-latest",
        action="store_true",
        help="Compare the two newest report bundles (read-only, PA-2A)",
    )
    mode.add_argument(
        "--compare-reports",
        nargs=2,
        metavar=("OLD", "NEW"),
        type=Path,
        help="Compare two report bundles by path (read-only, PA-2A)",
    )
    mode.add_argument(
        "--hotspots-latest",
        action="store_true",
        help="Show slow-event hotspots from the newest report bundle (read-only, PA-2B)",
    )
    mode.add_argument(
        "--hotspots-report",
        metavar="PATH",
        type=Path,
        help="Show slow-event hotspots for a specific report bundle (read-only, PA-2B)",
    )
    mode.add_argument(
        "--timeline-latest",
        action="store_true",
        help="Show scenario timeline insights from the newest bundle (read-only, PA-2B)",
    )
    mode.add_argument(
        "--timeline-report",
        metavar="PATH",
        type=Path,
        help="Show scenario timeline insights for a specific bundle (read-only, PA-2B)",
    )
    mode.add_argument(
        "--cursor-prompt-latest",
        action="store_true",
        help="Print a health-aware Cursor review prompt for the newest bundle (read-only, PA-2B)",
    )
    mode.add_argument(
        "--cursor-prompt-report",
        metavar="PATH",
        type=Path,
        help="Print a health-aware Cursor review prompt for a specific bundle (read-only, PA-2B)",
    )
    mode.add_argument(
        "--copy-cursor-prompt-latest",
        action="store_true",
        help="Copy the health-aware Cursor review prompt to clipboard (read-only, PA-2B)",
    )
    mode.add_argument(
        "--history",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Show table of N newest report bundles with health (default: 10, PA-2C)",
    )
    mode.add_argument(
        "--trend-latest",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Show metric trend across N newest bundles (default: 10, PA-2C)",
    )
    mode.add_argument(
        "--baseline-candidate",
        action="store_true",
        help="Show best baseline bundle for performance comparison (read-only, PA-2C)",
    )
    mode.add_argument(
        "--compare-baseline-latest",
        action="store_true",
        help="Compare baseline candidate against newest bundle (read-only, PA-2C)",
    )
    mode.add_argument(
        "--copy-analysis-prompt-latest",
        action="store_true",
        help=(
            "Copy wide Cursor analysis prompt with history/trend/baseline to clipboard "
            "(read-only, PA-2C)"
        ),
    )
    mode.add_argument(
        "--coverage-latest",
        action="store_true",
        help="Show coverage recovery diagnosis for the newest bundle (read-only, PA-3A)",
    )
    mode.add_argument(
        "--coverage-report",
        metavar="PATH",
        type=Path,
        help="Show coverage recovery diagnosis for a specific bundle (read-only, PA-3A)",
    )
    mode.add_argument(
        "--scenario-checklist",
        action="store_true",
        help="Show scenario checklist for a full guided run (read-only, PA-3A)",
    )
    mode.add_argument(
        "--run-playbook",
        action="store_true",
        help="Show full-run operator playbook (read-only, PA-3A)",
    )
    mode.add_argument(
        "--coverage-prompt-latest",
        action="store_true",
        help=(
            "Print Cursor prompt for coverage/instrumentation recovery "
            "(read-only, PA-3A)"
        ),
    )
    mode.add_argument(
        "--copy-coverage-prompt-latest",
        action="store_true",
        help="Copy coverage recovery Cursor prompt to clipboard (read-only, PA-3A)",
    )
    parser.add_argument(
        "--clip",
        action="store_true",
        help="Copy COPY FOR CHATGPT block to Windows clipboard (requires --chatgpt-latest, PA-1F)",
    )
    parser.add_argument(
        "--health-gate",
        action="store_true",
        help=(
            "Check latest bundle health before printing/copying COPY FOR CHATGPT block "
            "(requires --chatgpt-latest, PA-1H)"
        ),
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Override log path (default: profile default_log_path)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output report directory",
    )
    return parser


def _fetch_latest_entry(profile_id: str) -> tuple[Path, ReportIndexEntry] | None:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        return None
    latest_dir = report_dirs[0]
    return latest_dir, summarize_report_bundle(latest_dir)


def _fetch_report_entries(
    profile_id: str,
    limit: int,
) -> tuple[Path, list[ReportIndexEntry]]:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        return output_root, []
    entries = [summarize_report_bundle(path) for path in report_dirs[:limit]]
    return output_root, entries


def open_report_directory(report_dir: Path) -> None:
    """Open *report_dir* in the system file manager (Windows-first)."""
    if sys.platform != "win32":
        raise OSError("Opening in file manager is only supported on Windows.")
    os.startfile(str(report_dir))


def run_parse_only(
    *,
    profile_id: str,
    log_path: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    profile = get_profile(profile_id)
    source_log = profile.resolve_log_path(log_path)
    report_dir = output_dir or make_report_dir(profile)

    collection = collect_log(source_log, report_dir)
    parse = parse_for_profile(collection.events_jsonl, profile)
    bundle = generate_report(
        profile=profile,
        collection=collection,
        parse=parse,
        report_dir=report_dir,
        session=None,
    )
    return bundle.report_dir


def run_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    print(format_latest_report(entry))
    return 0


def run_chatgpt_latest(
    *,
    profile_id: str,
    clip: bool = False,
    health_gate: bool = False,
) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    latest_dir = report_dirs[0]

    if health_gate:
        entry = summarize_report_bundle(latest_dir)
        health = evaluate_report_health(entry)
        if health.status in ("NEEDS_RERUN", "BROKEN"):
            print(format_report_health(health), file=sys.stderr)
            return 2
        if health.status == "PARTIAL":
            print(
                "WARNING: Health gate status PARTIAL — report can be reviewed, "
                "but scenario coverage is weak.",
                file=sys.stderr,
            )
        elif health.status == "READY":
            print("Health gate: READY", file=sys.stderr)

    report_md = latest_dir / "report.md"
    if not report_md.is_file():
        print(f"ERROR: report.md missing in {latest_dir}", file=sys.stderr)
        return 1

    try:
        block = extract_copy_for_chatgpt(report_md)
    except CopyBlockNotFoundError as exc:
        print(f"ERROR: COPY FOR CHATGPT block not found in {report_md}: {exc}", file=sys.stderr)
        return 1

    payload = block if block.endswith("\n") else f"{block}\n"
    if clip:
        try:
            copy_text_to_clipboard(payload)
        except ClipboardCopyError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print("COPY FOR CHATGPT block copied to clipboard.")
        return 0

    sys.stdout.buffer.write(payload.encode("utf-8"))
    return 0


def run_health_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    health = evaluate_report_health(entry)
    print(format_report_health(health))
    return 0


def run_list_reports(*, profile_id: str, limit: int) -> int:
    if limit < 1:
        print("ERROR: --list-reports limit must be >= 1", file=sys.stderr)
        return 1

    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entries = [summarize_report_bundle(path) for path in report_dirs[:limit]]
    print(format_report_list(entries))
    return 0


def run_prepare_chatgpt_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    latest = _fetch_latest_entry(profile_id)
    if latest is None:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    latest_dir, entry = latest
    health = evaluate_report_health(entry)
    if health.status in ("NEEDS_RERUN", "BROKEN"):
        print(format_report_health(health), file=sys.stderr)
        print("COPY FOR CHATGPT block was not copied.", file=sys.stderr)
        return 2

    report_md = latest_dir / "report.md"
    if not report_md.is_file():
        print(f"ERROR: report.md missing in {latest_dir}", file=sys.stderr)
        return 1

    try:
        block = extract_copy_for_chatgpt(report_md)
    except CopyBlockNotFoundError as exc:
        print(f"ERROR: COPY FOR CHATGPT block not found in {report_md}: {exc}", file=sys.stderr)
        return 1

    payload = block if block.endswith("\n") else f"{block}\n"
    try:
        copy_text_to_clipboard(payload)
    except ClipboardCopyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(format_prepare_chatgpt_prep(health.status))
    return 0


def run_open_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    latest = _fetch_latest_entry(profile_id)
    if latest is None:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    latest_dir, _entry = latest
    print(format_open_latest_paths(latest_dir))

    if sys.platform != "win32":
        print(
            "Opening in file manager is only supported on Windows. Paths printed above.",
            file=sys.stderr,
        )
        return 0

    try:
        open_report_directory(latest_dir)
    except OSError as exc:
        print(f"ERROR: Could not open report directory: {exc}", file=sys.stderr)
        return 1

    return 0


def run_analyze_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    analysis = analyze_report_dir(report_dirs[0])
    print(format_report_analysis(analysis))
    return 0


def run_analyze_report(*, path: Path) -> int:
    analysis = analyze_report_dir(path)
    print(format_report_analysis(analysis))
    return 0


def run_compare_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if len(report_dirs) < 2:
        print(
            "Need at least 2 report bundles to compare.\n"
            f"Found: {len(report_dirs)} under {output_root.resolve()}",
        )
        return 0

    old_entry = summarize_report_bundle(report_dirs[1])
    new_entry = summarize_report_bundle(report_dirs[0])
    comparison = compare_report_bundles(old_entry, new_entry)
    print(format_report_comparison(comparison))
    return 0


def run_compare_reports(*, old_path: Path, new_path: Path) -> int:
    old_dir = resolve_report_dir(old_path)
    new_dir = resolve_report_dir(new_path)
    old_entry = summarize_report_bundle(old_dir)
    new_entry = summarize_report_bundle(new_dir)
    comparison = compare_report_bundles(old_entry, new_entry)
    print(format_report_comparison(comparison))
    return 0


def run_hotspots_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    print(format_hotspot_summary(build_hotspot_summary(entry)))
    return 0


def run_hotspots_report(*, path: Path) -> int:
    bundle_dir = resolve_report_dir(path)
    entry = summarize_report_bundle(bundle_dir)
    print(format_hotspot_summary(build_hotspot_summary(entry)))
    return 0


def run_timeline_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    print(format_timeline_summary(build_timeline_summary(entry)))
    return 0


def run_timeline_report(*, path: Path) -> int:
    bundle_dir = resolve_report_dir(path)
    entry = summarize_report_bundle(bundle_dir)
    print(format_timeline_summary(build_timeline_summary(entry)))
    return 0


def run_cursor_prompt_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    comparison: ReportComparison | None = None
    if len(report_dirs) >= 2:
        old_entry = summarize_report_bundle(report_dirs[1])
        comparison = compare_report_bundles(old_entry, entry)

    workspace_root = output_root.parent.parent
    print(build_cursor_prompt(entry, workspace_root=workspace_root, comparison=comparison))
    return 0


def run_cursor_prompt_report(*, path: Path) -> int:
    bundle_dir = resolve_report_dir(path)
    entry = summarize_report_bundle(bundle_dir)
    print(build_cursor_prompt(entry))
    return 0


def run_history(*, profile_id: str, limit: int) -> int:
    validate_history_limit(limit)
    output_root, entries = _fetch_report_entries(profile_id, limit)
    if not entries:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    summary = build_report_history(entries, limit=limit)
    print(format_report_history(summary, output_root=output_root, profile_id=profile_id))
    return 0


def run_trend_latest(*, profile_id: str, limit: int) -> int:
    validate_history_limit(limit)
    output_root, entries = _fetch_report_entries(profile_id, limit)
    if not entries:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    trend = build_trend_summary(entries, limit=limit)
    print(format_trend_summary(trend))
    return 0


def run_baseline_candidate(*, profile_id: str) -> int:
    output_root, entries = _fetch_report_entries(profile_id, MAX_HISTORY_LIMIT)
    if not entries:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    candidate = select_baseline_candidate(entries)
    latest = entries[0]
    print(format_baseline_candidate(candidate, latest=latest))
    return 0


def run_compare_baseline_latest(*, profile_id: str) -> int:
    output_root, entries = _fetch_report_entries(profile_id, MAX_HISTORY_LIMIT)
    if not entries:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    result = compare_baseline_to_latest(entries)
    print(format_baseline_comparison(result))
    return 0


def run_copy_analysis_prompt_latest(*, profile_id: str) -> int:
    output_root, entries = _fetch_report_entries(profile_id, MAX_HISTORY_LIMIT)
    if not entries:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    workspace_root = output_root.parent.parent
    prompt = build_analysis_prompt_with_history(
        entries,
        limit=min(DEFAULT_HISTORY_LIMIT, len(entries)),
        workspace_root=workspace_root,
    )
    payload = prompt if prompt.endswith("\n") else f"{prompt}\n"
    try:
        copy_text_to_clipboard(payload)
    except ClipboardCopyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Performance analysis prompt copied to clipboard.")
    return 0


def run_coverage_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    print(format_coverage_summary(build_coverage_summary(entry)))
    return 0


def run_coverage_report(*, path: Path) -> int:
    bundle_dir = resolve_report_dir(path)
    entry = summarize_report_bundle(bundle_dir)
    print(format_coverage_summary(build_coverage_summary(entry)))
    return 0


def run_scenario_checklist(*, profile_id: str) -> int:
    items = build_scenario_checklist(profile_id)
    print(format_scenario_checklist(items, profile_id=profile_id))
    return 0


def run_run_playbook(*, profile_id: str) -> int:
    print(build_run_playbook(profile_id))
    return 0


def run_coverage_prompt_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    workspace_root = output_root.parent.parent
    print(build_coverage_prompt(entry, workspace_root=workspace_root))
    return 0


def run_copy_coverage_prompt_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    workspace_root = output_root.parent.parent
    prompt = build_coverage_prompt(entry, workspace_root=workspace_root)
    payload = prompt if prompt.endswith("\n") else f"{prompt}\n"
    try:
        copy_text_to_clipboard(payload)
    except ClipboardCopyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Coverage recovery prompt copied to clipboard.")
    return 0


def run_copy_cursor_prompt_latest(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    if not report_dirs:
        print(format_no_reports_message(output_root=output_root, profile_id=profile_id))
        return 0

    entry = summarize_report_bundle(report_dirs[0])
    comparison: ReportComparison | None = None
    if len(report_dirs) >= 2:
        old_entry = summarize_report_bundle(report_dirs[1])
        comparison = compare_report_bundles(old_entry, entry)

    workspace_root = output_root.parent.parent
    prompt = build_cursor_prompt(entry, workspace_root=workspace_root, comparison=comparison)
    payload = prompt if prompt.endswith("\n") else f"{prompt}\n"
    try:
        copy_text_to_clipboard(payload)
    except ClipboardCopyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Cursor performance review prompt copied to clipboard.")
    return 0


def run_doctor(*, profile_id: str) -> int:
    profile = get_profile(profile_id)
    output_root = profile.resolve_output_root()
    report_dirs = discover_report_dirs(output_root, profile_id)
    latest_bundle_name: str | None = None
    latest_health_status = None
    if report_dirs:
        entry = summarize_report_bundle(report_dirs[0])
        latest_bundle_name = entry.dir_name
        latest_health_status = evaluate_report_health(entry).status

    default_log = profile.resolve_log_path(None)
    print(
        format_doctor_status(
            version=__version__,
            profile_id=profile_id,
            output_root=output_root,
            output_root_exists=output_root.is_dir(),
            report_bundle_count=len(report_dirs),
            latest_bundle_name=latest_bundle_name,
            latest_health_status=latest_health_status,
            default_log_exists=default_log.is_file(),
            clipboard_support=describe_clipboard_support(),
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.clip and not args.chatgpt_latest:
        print("ERROR: --clip can only be used with --chatgpt-latest", file=sys.stderr)
        return 1

    if args.health_gate and not args.chatgpt_latest:
        print("ERROR: --health-gate can only be used with --chatgpt-latest", file=sys.stderr)
        return 1

    if args.latest:
        try:
            return run_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.list_reports is not None:
        try:
            return run_list_reports(profile_id=args.profile, limit=args.list_reports)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.chatgpt_latest:
        try:
            return run_chatgpt_latest(
                profile_id=args.profile,
                clip=args.clip,
                health_gate=args.health_gate,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.health_latest:
        try:
            return run_health_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.prepare_chatgpt_latest:
        try:
            return run_prepare_chatgpt_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.open_latest:
        try:
            return run_open_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.doctor:
        try:
            return run_doctor(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.analyze_latest:
        try:
            return run_analyze_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.analyze_report is not None:
        try:
            return run_analyze_report(path=args.analyze_report)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.compare_latest:
        try:
            return run_compare_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.compare_reports is not None:
        try:
            return run_compare_reports(
                old_path=args.compare_reports[0],
                new_path=args.compare_reports[1],
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.hotspots_latest:
        try:
            return run_hotspots_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.hotspots_report is not None:
        try:
            return run_hotspots_report(path=args.hotspots_report)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.timeline_latest:
        try:
            return run_timeline_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.timeline_report is not None:
        try:
            return run_timeline_report(path=args.timeline_report)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.cursor_prompt_latest:
        try:
            return run_cursor_prompt_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.cursor_prompt_report is not None:
        try:
            return run_cursor_prompt_report(path=args.cursor_prompt_report)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.copy_cursor_prompt_latest:
        try:
            return run_copy_cursor_prompt_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.history is not None:
        try:
            return run_history(profile_id=args.profile, limit=args.history)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.trend_latest is not None:
        try:
            return run_trend_latest(profile_id=args.profile, limit=args.trend_latest)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.baseline_candidate:
        try:
            return run_baseline_candidate(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.compare_baseline_latest:
        try:
            return run_compare_baseline_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.copy_analysis_prompt_latest:
        try:
            return run_copy_analysis_prompt_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.coverage_latest:
        try:
            return run_coverage_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.coverage_report is not None:
        try:
            return run_coverage_report(path=args.coverage_report)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.scenario_checklist:
        return run_scenario_checklist(profile_id=args.profile)

    if args.run_playbook:
        return run_run_playbook(profile_id=args.profile)

    if args.coverage_prompt_latest:
        try:
            return run_coverage_prompt_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.copy_coverage_prompt_latest:
        try:
            return run_copy_coverage_prompt_latest(profile_id=args.profile)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    manual_mode = args.manual or args.wizard
    run_mode = args.run or args.launch

    if not args.parse_only and not manual_mode and not run_mode:
        parser.print_help()
        print(
            "\nExamples:\n"
            "  python -m tools.performance_agent --parse-only\n"
            "  python -m tools.performance_agent --manual\n"
            "  python -m tools.performance_agent --run\n"
            "  python -m tools.performance_agent --latest\n"
            "  python -m tools.performance_agent --list-reports 5\n"
            "  python -m tools.performance_agent --chatgpt-latest\n"
            "  python -m tools.performance_agent --chatgpt-latest --clip\n"
            "  python -m tools.performance_agent --health-latest\n"
            "  python -m tools.performance_agent --chatgpt-latest --health-gate\n"
            "  python -m tools.performance_agent --chatgpt-latest --clip --health-gate\n"
            "  python -m tools.performance_agent --prepare-chatgpt-latest\n"
            "  python -m tools.performance_agent --open-latest\n"
            "  python -m tools.performance_agent --doctor\n"
            "  python -m tools.performance_agent --analyze-latest\n"
            "  python -m tools.performance_agent --analyze-report reports/performance/<bundle>\n"
            "  python -m tools.performance_agent --compare-latest\n"
            "  python -m tools.performance_agent --compare-reports <old> <new>\n"
            "  python -m tools.performance_agent --hotspots-latest\n"
            "  python -m tools.performance_agent --hotspots-report reports/performance/<bundle>\n"
            "  python -m tools.performance_agent --timeline-latest\n"
            "  python -m tools.performance_agent --timeline-report reports/performance/<bundle>\n"
            "  python -m tools.performance_agent --cursor-prompt-latest\n"
            "  python -m tools.performance_agent --copy-cursor-prompt-latest\n"
            "  python -m tools.performance_agent --history\n"
            "  python -m tools.performance_agent --history 10\n"
            "  python -m tools.performance_agent --trend-latest\n"
            "  python -m tools.performance_agent --trend-latest 10\n"
            "  python -m tools.performance_agent --baseline-candidate\n"
            "  python -m tools.performance_agent --compare-baseline-latest\n"
            "  python -m tools.performance_agent --copy-analysis-prompt-latest\n"
            "  python -m tools.performance_agent --coverage-latest\n"
            "  python -m tools.performance_agent --coverage-report reports/performance/<bundle>\n"
            "  python -m tools.performance_agent --scenario-checklist\n"
            "  python -m tools.performance_agent --run-playbook\n"
            "  python -m tools.performance_agent --coverage-prompt-latest\n"
            "  python -m tools.performance_agent --copy-coverage-prompt-latest",
            file=sys.stderr,
        )
        return 2

    try:
        if run_mode:
            bundle = run_with_studio(
                profile_id=args.profile,
                log_path=args.log,
                output_dir=args.output,
            )
            report_dir = bundle.report_dir
            if bundle.raw_log is None:
                print(
                    "WARNING: performance log missing — partial report generated.",
                    file=sys.stderr,
                )
            if bundle.summary_json.exists():
                import json

                summary = json.loads(bundle.summary_json.read_text(encoding="utf-8"))
                if summary.get("studio", {}).get("start_failed"):
                    print(
                        "WARNING: Studio failed to start or exited early — partial report.",
                        file=sys.stderr,
                    )
        elif manual_mode:
            bundle = run_manual(
                profile_id=args.profile,
                log_path=args.log,
                output_dir=args.output,
            )
            report_dir = bundle.report_dir
            if bundle.raw_log is None:
                print(
                    "WARNING: performance log missing — partial report generated (UX only).",
                    file=sys.stderr,
                )
        else:
            report_dir = run_parse_only(
                profile_id=args.profile,
                log_path=args.log,
                output_dir=args.output,
            )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Report bundle: {report_dir}")
    print("  report.md")
    print("  summary.json")
    if manual_mode or run_mode:
        print("  agent_events.jsonl")
        print("  scenario_timeline.csv")
        print("  questions_answers.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
