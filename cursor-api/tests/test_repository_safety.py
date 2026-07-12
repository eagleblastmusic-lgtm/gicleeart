from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from tools.repository_safety.audit import _secret_findings, audit_tracked_tree
from tools.repository_safety.migration import build_migration_report
from tools.repository_safety.policy import DataClass, classify_path


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "test")


def _track_all(path: Path) -> None:
    _git(path, "add", "-A")
    _git(path, "commit", "-m", "test")


def test_policy_prioritizes_examples_over_secret_patterns() -> None:
    example = classify_path("Komponenty/integracjagpt/data/gpt_config.example.json")
    secret = classify_path("Komponenty/integracjagpt/data/gpt_config.json")

    assert example.classification is DataClass.EXAMPLE
    assert example.tracked_allowed
    assert example.sync_allowed
    assert secret.classification is DataClass.RUNTIME
    assert not secret.tracked_allowed
    assert secret.migration_bucket == "config"


def test_policy_blocks_unknown_root_artifact() -> None:
    decision = classify_path("10.0.0")
    assert decision.classification is DataClass.GENERATED
    assert not decision.tracked_allowed

    unknown = classify_path("mystery.binary")
    assert unknown.classification is None
    assert unknown.rule_id == "UNCLASSIFIED_BLOCKED"


def test_audit_scans_all_tracked_files_and_detects_runtime_and_pii(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    source = repo / "giclee_app" / "ok.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    runtime = repo / "Komponenty" / "produkcja" / "dane" / "zamowienia.json"
    runtime.parent.mkdir(parents=True)
    runtime.write_text(json.dumps({"client": "Jan", "email": "jan@example.com"}), encoding="utf-8")
    _track_all(repo)

    report = audit_tracked_tree(repo)

    assert report.tracked_files == 2
    assert not report.ok
    rule_ids = {finding.rule_id for finding in report.blockers}
    assert "PRIVATE_USER_DATA" in rule_ids
    assert "PII_DATA_COLUMNS" in rule_ids
    assert not any(finding.path == "giclee_app/ok.py" for finding in report.blockers)


def test_audit_allows_clean_source_and_safe_example(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    source = repo / "tools" / "worker.py"
    source.parent.mkdir(parents=True)
    source.write_text("def run():\n    return 1\n", encoding="utf-8")
    example = repo / "Komponenty" / "demo" / "data" / "config.example.json"
    example.parent.mkdir(parents=True)
    example.write_text('{"email": "example@example.com"}\n', encoding="utf-8")
    _track_all(repo)

    report = audit_tracked_tree(repo)

    assert report.ok
    assert not report.blockers


def test_named_secret_scanner_ignores_identifier_and_runtime_lookups() -> None:
    text = "\n".join(
        [
            "api_key=api_key,",
            "password = gmail_imap_password()",
            "password = file_password",
            "const API_KEY = String(process.env.SHOPIFY_API_KEY || '')",
        ]
    )

    assert not tuple(_secret_findings("giclee_app/credentials.py", text))


def test_named_secret_scanner_blocks_real_quoted_literal() -> None:
    findings = tuple(
        _secret_findings(
            "giclee_app/credentials.py",
            'password = "S3cretValue123"\n',
        )
    )

    assert len(findings) == 1
    assert "NAMED_SECRET_LITERAL" in findings[0].message


def test_named_secret_scanner_ignores_placeholders_and_environment_templates() -> None:
    text = "\n".join(
        [
            'password = "changeme"',
            'api_key = "your_api_key"',
            'client_secret: "${CLIENT_SECRET}"',
            'refresh_token = "<refresh-token>"',
        ]
    )

    assert not tuple(_secret_findings("giclee_app/config.py", text))


def test_named_secret_scanner_ignores_credential_names_inside_ui_strings() -> None:
    text = "\n".join(
        [
            'ttk.Label(frame, text="Nowy SERPAPI_KEY:").pack(anchor="w")',
            'ttk.Label(frame, text="SMITHSONIAN_API_KEY:").pack(anchor="w")',
            'ttk.Label(frame, text="Nowy GEMINI_API_KEY:").pack(anchor="w")',
        ]
    )

    assert not tuple(_secret_findings("giclee_app/dialog.py", text))


def test_secret_scanner_skips_test_script_outside_tests_directory() -> None:
    findings = tuple(
        _secret_findings(
            "mockup-order-worker/scripts/test_resend.py",
            'password = "S3cretValue123"\n',
        )
    )

    assert not findings


def test_strong_token_format_still_blocks() -> None:
    findings = tuple(
        _secret_findings(
            "giclee_app/config.py",
            'token = "ghp_abcdefghijklmnopqrstuvwxyz123456"\n',
        )
    )

    assert len(findings) == 1
    assert "GITHUB_TOKEN" in findings[0].message


def test_migration_dry_run_does_not_copy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    source = repo / "Komponenty" / "integracjagpt" / "data" / "gpt_config.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"local": true}\n', encoding="utf-8")
    _track_all(repo)
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"

    report = build_migration_report(
        repo,
        local_app_data=local,
        roaming_app_data=roaming,
    )

    assert not report.blocked
    assert report.dry_run
    assert report.profile == "all"
    assert len(report.items) == 1
    assert report.items[0].status == "planned"
    assert not Path(report.items[0].destination).exists()
    assert source.exists()


def test_migration_copy_is_hash_verified_and_keeps_source(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    source = repo / "Komponenty" / "_shared" / "data" / "activity_log.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text('{"event": "test"}\n', encoding="utf-8")
    _track_all(repo)
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"

    report = build_migration_report(
        repo,
        execute_copy=True,
        profile="archive",
        local_app_data=local,
        roaming_app_data=roaming,
    )

    assert not report.blocked
    assert report.copied_count == 1
    item = report.items[0]
    destination = Path(item.destination)
    assert destination.exists()
    assert source.exists()
    assert item.source_sha256 == item.destination_sha256
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == item.source_sha256


def test_migration_conflict_blocks_all_copy_and_never_overwrites(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    first = repo / "Komponenty" / "integracjagpt" / "data" / "gpt_config.json"
    second = repo / "Komponenty" / "_shared" / "data" / "activity_log.jsonl"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("source-config", encoding="utf-8")
    second.write_text("source-log", encoding="utf-8")
    _track_all(repo)
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    conflict = roaming / "GicleeArt" / "GicleeApp" / "config" / first.relative_to(repo)
    conflict.parent.mkdir(parents=True)
    conflict.write_text("different", encoding="utf-8")

    report = build_migration_report(
        repo,
        execute_copy=True,
        profile="critical",
        local_app_data=local,
        roaming_app_data=roaming,
    )

    assert report.blocked
    assert any(item.status == "conflict" for item in report.items)
    log_destination = local / "GicleeArt" / "GicleeApp" / "logs" / second.relative_to(repo)
    assert not log_destination.exists()
    assert conflict.read_text(encoding="utf-8") == "different"
    assert first.exists() and second.exists()
