from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from tools.repository_safety.policy import classify_path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "repository_safety" / "STAGE_1F_TRACKED_CLEANUP_ALLOWLIST.json"
RUNBOOK_PATH = ROOT / "scripts" / "repository-safety-local-cleanup-validation.ps1"
MARKER = "# --- Stage 1F.1: verified local-data cleanup allowlist ---"
TIMESTAMP_ONLY_LEGACY_PATH = (
    "Komponenty/dokumentysprzedazy/dane/orders_sync_state.json"
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _paths() -> list[str]:
    return [str(item["path"]) for item in _manifest()["paths"]]


def _git(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cleanup_manifest_is_exact_deterministic_allowlist() -> None:
    manifest = _manifest()
    items = manifest["paths"]
    paths = [str(item["path"]) for item in items]

    assert manifest["schema_version"] == 1
    assert manifest["stage"] == "1F.1"
    assert manifest["base_sha"] == "d10fe0060e70f659083db33f0c93a72dbdfe2f6c"
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths)) == 111
    assert manifest["migratable_paths"] == 109
    assert manifest["generated_paths"] == 2
    assert Counter(str(item["classification"]) for item in items) == {
        "BACKUP": 36,
        "CACHE": 3,
        "GENERATED": 2,
        "PRIVATE": 23,
        "RUNTIME": 46,
        "SECRET": 1,
    }


def test_cleanup_manifest_matches_central_policy() -> None:
    for item in _manifest()["paths"]:
        decision = classify_path(str(item["path"]))
        assert decision.classification is not None
        assert decision.classification.value == item["classification"]
        assert decision.tracked_allowed is False
        assert bool(item["copy_required"]) is (decision.migration_bucket is not None)


def test_cleanup_paths_are_not_tracked() -> None:
    result = _git("ls-files", "-z")
    assert result.returncode == 0, result.stderr
    tracked = {path for path in result.stdout.split("\0") if path}
    overlap = sorted(tracked.intersection(_paths()))
    assert overlap == []


def test_cleanup_paths_are_ignored_exactly() -> None:
    paths = _paths()
    expected = [path.encode("utf-8") for path in paths]
    nul_input = b"\0".join(expected) + b"\0"
    result = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "check-ignore",
            "--no-index",
            "-z",
            "--stdin",
        ],
        input=nul_input,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    ignored = [entry for entry in result.stdout.split(b"\0") if entry]
    assert ignored == expected

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert gitignore.count(MARKER) == 1
    for path in paths:
        assert f"/{path}\n" in gitignore


def test_cleanup_validation_runs_repository_safety_from_tool_root() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    audit_command = "& python -m tools.repository_safety audit"
    migration_command = "& python -m tools.repository_safety migrate"

    assert runbook.count(audit_command) == 1
    assert runbook.count(migration_command) == 1

    for command in (audit_command, migration_command):
        command_index = runbook.index(command)
        push_index = runbook.rfind("Push-Location $ToolRoot", 0, command_index)
        pop_index = runbook.find("Pop-Location", command_index)
        assert push_index >= 0
        assert pop_index > command_index


def test_cleanup_validation_accepts_only_timestamp_only_legacy_drift() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert TIMESTAMP_ONLY_LEGACY_PATH in _paths()
    assert runbook.count(TIMESTAMP_ONLY_LEGACY_PATH) == 1
    assert "$timestampOnlyLegacyDriftPaths" in runbook
    assert "$migrationExitCode -notin @(0, 1)" in runbook
    assert "if ([bool]$migration.blocked)" not in runbook

    assert "ls-files --error-unmatch -- $path" in runbook
    assert "diff --cached --quiet -- $path" in runbook
    assert "diff --quiet -- $path" in runbook
    assert "diff --unified=0 -- $path" in runbook
    assert "$changedLines.Count -ne 2" in runbook
    assert "last_sync_iso" in runbook

    assert "$expectedStateKeys" in runbook
    assert "pending_order_ids" in runbook
    assert "notified_order_ids" in runbook
    assert "Get-NormalizedIdList" in runbook
    assert "[DateTimeOffset]::Parse(" in runbook
    assert "$sourceTimestamp -le $destinationTimestamp" in runbook

    assert "Accepted timestamp-only legacy drift" in runbook
    assert "Destination-authoritative AppData drift" not in runbook
    assert "tests/test_stage1e_external_stores_8_sales_sync_artifacts.py" in runbook


def test_order_sync_authoritative_store_contract_remains_appdata_first() -> None:
    source = (
        ROOT / "Komponenty" / "dokumentysprzedazy" / "orders_sync.py"
    ).read_text(encoding="utf-8")

    assert "_SYNC_STATE = data_path(" in source
    assert TIMESTAMP_ONLY_LEGACY_PATH in source
    assert "return _SYNC_STATE.write_path if for_write else _SYNC_STATE.read_path()" in source
    assert "atomic_write_text(" in source


def test_tracked_tree_audit_matches_explicit_monorepo_baseline_after_cleanup() -> None:
    baseline_path = (
        ROOT
        / "docs"
        / "repository_safety"
        / "STAGE_1G_MONOREPO_REMAINING_BLOCKERS.json"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="gicleeapp-stage1g-audit-") as temp_dir:
        report_path = Path(temp_dir) / "audit.json"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.repository_safety",
                "audit",
                "--repo",
                str(ROOT),
                "--json-out",
                str(report_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode in {0, 1}, result.stdout + result.stderr
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["error"] == ""

        def normalized(finding: dict[str, object]) -> dict[str, object]:
            return {
                "severity": str(finding.get("severity", "")),
                "rule_id": str(finding.get("rule_id", "")),
                "path": str(finding.get("path", "")).replace("\\", "/"),
                "message": str(finding.get("message", "")),
                "line": finding.get("line"),
            }

        def sort_key(finding: dict[str, object]) -> tuple[object, ...]:
            return (
                finding["severity"],
                finding["rule_id"],
                finding["path"],
                finding["message"],
                finding["line"] if finding["line"] is not None else -1,
            )

        blockers = sorted(
            (
                normalized(finding)
                for finding in report["findings"]
                if finding["severity"] == "BLOCKER"
            ),
            key=sort_key,
        )
        warnings = sorted(
            (
                normalized(finding)
                for finding in report["findings"]
                if finding["severity"] == "WARNING"
            ),
            key=sort_key,
        )
        assert blockers == baseline["blockers"]
        assert warnings == baseline["warnings"]
        assert report["blocker_count"] == baseline["remaining_blocker_count"]
        assert report["warning_count"] == baseline["remaining_warning_count"]
