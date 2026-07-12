from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://github.com/eagleblastmusic-lgtm/gicleeapp.git",
        ],
        cwd=path,
        check=True,
    )


def _write_review_only(staging: Path) -> None:
    from Komponenty.integracjagpt.config import GICLEEAPP_REVIEW_ONLY_FILES

    for rel in GICLEEAPP_REVIEW_ONLY_FILES:
        path = staging / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"review-only:{rel}", encoding="utf-8")


@pytest.fixture
def allowlist_env(tmp_path: Path, monkeypatch):
    from Komponenty.integracjagpt import gicleeapp_push as gap

    source = tmp_path / "cursor-api"
    staging = tmp_path / "staging"
    source.mkdir()
    staging.mkdir()
    _init_git_repo(staging)

    (staging / ".gitignore").write_text(".env\n__pycache__/\n", encoding="utf-8")
    (staging / "README.md").write_text("staging readme", encoding="utf-8")
    _write_review_only(staging)

    (source / "giclee_app").mkdir()
    (source / "giclee_app" / "__init__.py").write_text(
        '__version__ = "2.0.0"\n', encoding="utf-8"
    )
    (source / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")

    subprocess.run(["git", "add", "-A"], cwd=staging, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=staging,
        check=True,
        capture_output=True,
    )

    monkeypatch.setattr(
        gap,
        "inspect_branch_sync",
        lambda *args, **kwargs: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )
    return gap, source, staging


def test_allowlist_sync_excludes_runtime_and_writes_stable_manifest(allowlist_env) -> None:
    gap, source, staging = allowlist_env
    (source / "giclee_app" / "changed.py").write_text("VALUE = 1\n", encoding="utf-8")
    runtime = source / "Komponenty" / "integracjagpt" / "data"
    runtime.mkdir(parents=True)
    (runtime / "gpt_config.json").write_text('{"token":"private"}\n', encoding="utf-8")

    first = gap.safe_sync_to_staging(source, staging)
    manifest = staging / first.manifest_path
    first_manifest = manifest.read_text(encoding="utf-8")
    second = gap.safe_sync_to_staging(source, staging)

    assert first.ok
    assert second.ok
    assert (staging / "giclee_app" / "changed.py").is_file()
    assert not (staging / "Komponenty" / "integracjagpt" / "data" / "gpt_config.json").exists()
    assert "Komponenty/integracjagpt/data/gpt_config.json" in first.skipped
    assert first.tree_sha256
    assert first.manifest_path in second.unchanged
    assert manifest.read_text(encoding="utf-8") == first_manifest


def test_allowlist_sync_preserves_review_only_files(allowlist_env) -> None:
    gap, source, staging = allowlist_env
    original = (staging / "README.md").read_text(encoding="utf-8")
    (source / "README.md").write_text("source overwrite attempt", encoding="utf-8")

    result = gap.safe_sync_to_staging(source, staging)

    assert result.ok
    assert (staging / "README.md").read_text(encoding="utf-8") == original
    assert "README.md" in result.protected


def test_allowlist_secret_blocker_prevents_all_copy(allowlist_env) -> None:
    gap, source, staging = allowlist_env
    (source / "giclee_app" / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "giclee_app" / "bad.py").write_text(
        'TOKEN = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', encoding="utf-8"
    )

    result = gap.safe_sync_to_staging(source, staging)

    assert not result.ok
    assert result.blockers
    assert not (staging / "giclee_app" / "safe.py").exists()
    assert not (staging / "giclee_app" / "bad.py").exists()


def test_audit_blocks_runtime_already_tracked_in_repository(allowlist_env) -> None:
    gap, _, staging = allowlist_env
    runtime = staging / "Komponenty" / "_shared" / "data" / "activity_log.jsonl"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("{}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", "--", runtime.relative_to(staging).as_posix()],
        cwd=staging,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "tracked runtime fixture"],
        cwd=staging,
        check=True,
        capture_output=True,
    )

    report = gap.audit_staging_repo(staging, log=[])

    assert report.blocked
    assert report.tracked_tree_blockers
    assert any("activity_log.jsonl" in item for item in report.tracked_tree_blockers)


def test_commit_rechecks_full_tracked_tree_after_ff_only(allowlist_env, monkeypatch) -> None:
    gap, _, staging = allowlist_env
    monkeypatch.setattr(gap, "_precommit_tracked_tree_gate", lambda *_: "blocked after pull")
    report = gap.GicleeAppAuditReport(commit_candidates=["giclee_app/changed.py"])

    result = gap.commit_and_push_gicleeapp(report, staging_dir=staging, log=[])

    assert not result.ok
    assert "blocked after pull" in result.message
