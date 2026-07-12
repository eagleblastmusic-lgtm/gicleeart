"""CLI for repository safety audit, migration, runtime-write inventory and snapshot tooling."""

from __future__ import annotations

import argparse
from pathlib import Path

from .audit import audit_tracked_tree, write_json_report
from .migration import MIGRATION_PROFILES, build_migration_report, write_migration_json
from .runtime_writes import audit_runtime_writes, write_runtime_write_json
from .snapshot import (
    build_snapshot_plan,
    execute_snapshot_copy,
    write_snapshot_plan_json,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repository_safety",
        description="GicleeApp repository data-safety audit, migration and snapshot tooling.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit every path returned by git ls-files.")
    audit.add_argument("--repo", type=Path, default=Path.cwd())
    audit.add_argument("--json-out", type=Path)
    audit.add_argument("--max-binary-mb", type=int, default=10)

    runtime_writes_parser = subparsers.add_parser(
        "runtime-writes",
        help="Inventory Python writes whose targets are derived from the source checkout.",
    )
    runtime_writes_parser.add_argument("--repo", type=Path, default=Path.cwd())
    runtime_writes_parser.add_argument("--json-out", type=Path)
    runtime_writes_parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Return exit code 1 when review findings are present. Default is diagnostic.",
    )

    migrate = subparsers.add_parser(
        "migrate",
        help="Plan or execute a copy-only migration of tracked runtime/private data.",
    )
    migrate.add_argument("--repo", type=Path, default=Path.cwd())
    migrate.add_argument(
        "--copy",
        action="store_true",
        help=(
            "Execute copy after conflict-free preflight. Requires an explicit non-all "
            "--profile. Default is dry-run."
        ),
    )
    migrate.add_argument(
        "--profile",
        choices=MIGRATION_PROFILES,
        default="all",
        help=(
            "Selection profile: all (dry-run only), critical (secrets/private/active state), "
            "archive (backups/logs), or cache (regenerable data)."
        ),
    )
    migrate.add_argument(
        "--include-untracked",
        action="store_true",
        help="Also discover untracked runtime files. Default scans git ls-files only.",
    )
    migrate.add_argument("--local-app-data", type=Path)
    migrate.add_argument("--roaming-app-data", type=Path)
    migrate.add_argument("--json-out", type=Path)

    snapshot = subparsers.add_parser(
        "snapshot",
        help="Plan or execute an allowlist-based source snapshot to a staging directory.",
    )
    snapshot.add_argument("--source", type=Path, default=Path.cwd())
    snapshot.add_argument("--staging", type=Path, required=True)
    snapshot.add_argument(
        "--copy",
        action="store_true",
        help="Copy approved source files and write the manifest. Default is dry-run.",
    )
    snapshot.add_argument("--json-out", type=Path)
    snapshot.add_argument("--max-binary-mb", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "audit":
        report = audit_tracked_tree(
            args.repo,
            max_binary_bytes=max(1, args.max_binary_mb) * 1024 * 1024,
        )
        print(report.format_text(), end="")
        if args.json_out:
            write_json_report(report, args.json_out)
        return 0 if report.ok else 1

    if args.command == "runtime-writes":
        report = audit_runtime_writes(args.repo)
        print(report.format_text(), end="")
        if args.json_out:
            write_runtime_write_json(report, args.json_out)
        if report.parse_errors:
            return 1
        return 1 if args.fail_on_findings and report.findings else 0

    if args.command == "migrate":
        report = build_migration_report(
            args.repo,
            execute_copy=args.copy,
            tracked_only=not args.include_untracked,
            profile=args.profile,
            local_app_data=args.local_app_data,
            roaming_app_data=args.roaming_app_data,
        )
        print(report.format_text(), end="")
        if args.json_out:
            write_migration_json(report, args.json_out)
        return 1 if report.blocked else 0

    plan = build_snapshot_plan(
        args.source,
        args.staging,
        max_binary_bytes=max(1, args.max_binary_mb) * 1024 * 1024,
    )
    print(plan.format_text(), end="")
    if args.json_out:
        write_snapshot_plan_json(plan, args.json_out)
    if not args.copy:
        return 0 if plan.ok else 1

    result = execute_snapshot_copy(plan)
    print(
        "Copy result: "
        f"copied={len(result.copied)} "
        f"unchanged={len(result.unchanged)} "
        f"protected={len(result.protected)} "
        f"manifest={'yes' if result.manifest_written else 'no'}"
    )
    for error in result.errors:
        print(f"ERROR: {error}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
