from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.repository_safety.snapshot import (
    DEFAULT_MANIFEST_PATH,
    build_snapshot_plan,
    execute_snapshot_copy,
)


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "master"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)


def _source_tree(tmp_path: Path) -> Path:
    source = tmp_path / "cursor-api"
    (source / "giclee_app").mkdir(parents=True)
    (source / "giclee_app" / "__init__.py").write_text('__version__ = "2.0.0"\n', encoding="utf-8")
    (source / "giclee_app" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "Komponenty" / "integracjagpt" / "data").mkdir(parents=True)
    (source / "Komponenty" / "integracjagpt" / "data" / "gpt_config.json").write_text(
        '{"token":"private"}\n', encoding="utf-8"
    )
    (source / "Komponenty" / "example").mkdir(parents=True)
    (source / "Komponenty" / "example" / "settings.example.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (source / ".gpt_mirror").mkdir()
    (source / ".gpt_mirror" / "ignored.txt").write_text("ignored", encoding="utf-8")
    _git_init(source)
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(["git", "commit", "-m", "source"], cwd=source, check=True, capture_output=True)
    return source


def test_snapshot_plan_uses_allowlist_and_records_skips(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    staging = tmp_path / "staging"

    plan = build_snapshot_plan(source, staging)

    assert plan.ok
    assert "giclee_app/app.py" in plan.included_paths
    assert "Komponenty/example/settings.example.json" in plan.included_paths
    skipped = {item.path: item.rule_id for item in plan.skipped_paths}
    assert skipped["Komponenty/integracjagpt/data/gpt_config.json"] == "LOCAL_CONFIG_RUNTIME"
    assert skipped[".gpt_mirror/ignored.txt"] == "GENERATED_ARTIFACT"
    assert plan.application_version == "2.0.0"
    assert len(plan.source_git_sha) == 40
    assert len(plan.tree_sha256) == 64


def test_snapshot_copy_preserves_protected_and_writes_manifest(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    (source / "README.md").write_text("source readme\n", encoding="utf-8")
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "README.md").write_text("staging readme\n", encoding="utf-8")

    plan = build_snapshot_plan(source, staging)
    result = execute_snapshot_copy(plan)

    assert result.ok
    assert (staging / "README.md").read_text(encoding="utf-8") == "staging readme\n"
    assert (staging / "giclee_app" / "app.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not (staging / "Komponenty" / "integracjagpt" / "data" / "gpt_config.json").exists()
    manifest = json.loads((staging / DEFAULT_MANIFEST_PATH).read_text(encoding="utf-8"))
    assert manifest["source_git_sha"] == plan.source_git_sha
    assert manifest["application_version"] == "2.0.0"
    assert manifest["cursor_api_tree_sha256"] == plan.tree_sha256
    assert manifest["security_data_scan"]["ok"] is True


def test_snapshot_plan_blocks_secret_in_allowed_source(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    (source / "giclee_app" / "bad.py").write_text(
        'TOKEN = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', encoding="utf-8"
    )

    plan = build_snapshot_plan(source, tmp_path / "staging")
    result = execute_snapshot_copy(plan)

    assert not plan.ok
    assert any(item.rule_id == "SECRET_CONTENT" for item in plan.blockers)
    assert not result.ok
    assert not (tmp_path / "staging" / "giclee_app" / "app.py").exists()


def test_tree_hash_changes_with_content_not_staging(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    staging = tmp_path / "staging"
    staging.mkdir()
    first = build_snapshot_plan(source, staging)
    (staging / "unrelated.txt").write_text("staging only", encoding="utf-8")
    second = build_snapshot_plan(source, staging)
    assert first.tree_sha256 == second.tree_sha256

    (source / "giclee_app" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    third = build_snapshot_plan(source, staging)
    assert third.tree_sha256 != first.tree_sha256


def test_snapshot_manifest_is_idempotent_when_source_is_unchanged(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    staging = tmp_path / "staging"

    first_plan = build_snapshot_plan(source, staging)
    first_result = execute_snapshot_copy(first_plan)
    manifest_path = staging / DEFAULT_MANIFEST_PATH
    first_text = manifest_path.read_text(encoding="utf-8")

    second_plan = build_snapshot_plan(source, staging)
    second_result = execute_snapshot_copy(second_plan)
    second_text = manifest_path.read_text(encoding="utf-8")

    assert first_result.manifest_written
    assert not second_result.manifest_written
    assert DEFAULT_MANIFEST_PATH in second_result.unchanged
    assert first_text == second_text


def test_snapshot_reports_stale_tracked_staging_paths_without_deleting(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    staging = tmp_path / "staging"
    staging.mkdir()
    _git_init(staging)
    (staging / "obsolete.py").write_text("OLD = True\n", encoding="utf-8")
    (staging / "README.md").write_text("protected\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=staging, check=True)
    subprocess.run(["git", "commit", "-m", "staging"], cwd=staging, check=True, capture_output=True)

    plan = build_snapshot_plan(source, staging)
    result = execute_snapshot_copy(plan)

    stale = {item.path: item for item in plan.stale_paths}
    assert "obsolete.py" in stale
    assert "README.md" not in stale
    assert (staging / "obsolete.py").read_text(encoding="utf-8") == "OLD = True\n"
    assert result.ok
    manifest = json.loads((staging / DEFAULT_MANIFEST_PATH).read_text(encoding="utf-8"))
    assert manifest["stale_file_count"] == 1
    assert manifest["stale_paths"][0]["path"] == "obsolete.py"
