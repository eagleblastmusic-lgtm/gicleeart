"""CLI entrypoint for Performance Agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.performance_agent.collector import collect_log
from tools.performance_agent.parser.giclee_studio import parse_for_profile
from tools.performance_agent.profiles import get_profile, list_profiles
from tools.performance_agent.report.generator import generate_report, make_report_dir
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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    manual_mode = args.manual or args.wizard
    run_mode = args.run or args.launch

    if not args.parse_only and not manual_mode and not run_mode:
        parser.print_help()
        print(
            "\nExamples:\n"
            "  python -m tools.performance_agent --parse-only\n"
            "  python -m tools.performance_agent --manual\n"
            "  python -m tools.performance_agent --run",
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
