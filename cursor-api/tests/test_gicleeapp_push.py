"""Testy workflow Push GicleeApp."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _init_git_repo(path: Path, *, remote: str = "", branch: str = "main") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True, capture_output=True)
    if remote:
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=path, check=True, capture_output=True)


def _write_review_only(staging: Path) -> None:
    from Komponenty.integracjagpt.config import GICLEEAPP_REVIEW_ONLY_FILES

    for rel in GICLEEAPP_REVIEW_ONLY_FILES:
        p = staging / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"review-only:{rel}", encoding="utf-8")


@pytest.fixture
def gicleeapp_env(tmp_path, monkeypatch):
    from Komponenty.integracjagpt import config as cfg

    source = tmp_path / "cursor-api"
    staging = tmp_path / "staging"
    starter = tmp_path / "Pliki startowe dla GPT"
    theme = tmp_path / "monorepo"
    source.mkdir()
    staging.mkdir()
    starter.mkdir()
    theme.mkdir()

    _init_git_repo(
        staging,
        remote="https://github.com/eagleblastmusic-lgtm/gicleeapp.git",
    )
    (staging / ".gitignore").write_text(".env\n__pycache__/\n", encoding="utf-8")
    (staging / "README.md").write_text("staging readme", encoding="utf-8")
    _write_review_only(staging)

    (source / "giclee_app").mkdir()
    (source / "giclee_app" / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    (source / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")

    monkeypatch.setattr(cfg, "CURSOR_API_DIR", source)
    monkeypatch.setattr(cfg, "GICLEEAPP_STAGING_DIR", staging)
    monkeypatch.setattr(cfg, "GPT_STARTER_DIR", starter)
    monkeypatch.setattr(cfg, "THEME_ROOT", theme)

    subprocess.run(["git", "add", "-A"], cwd=staging, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "test baseline"],
        cwd=staging,
        check=True,
        capture_output=True,
    )

    return source, staging


def test_sync_preserves_review_only_files(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap
    from Komponenty.integracjagpt.config import GICLEEAPP_REVIEW_ONLY_FILES

    source, staging = gicleeapp_env
    before = {(staging / rel).read_text(encoding="utf-8") for rel in GICLEEAPP_REVIEW_ONLY_FILES}

    (source / "GPT_README.md").write_text("mono overwrite attempt", encoding="utf-8")
    gap.safe_sync_to_staging(source, staging)

    after = {(staging / rel).read_text(encoding="utf-8") for rel in GICLEEAPP_REVIEW_ONLY_FILES}
    assert before == after


def test_sync_does_not_overwrite_staging_gitignore(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    source, staging = gicleeapp_env
    staging_ignore = staging / ".gitignore"
    original = staging_ignore.read_text(encoding="utf-8")
    staging_ignore.write_text(original + "\n# staging-only-rule\nKomponenty/staging/extra/\n", encoding="utf-8")

    gap.safe_sync_to_staging(source, staging)

    merged = staging_ignore.read_text(encoding="utf-8")
    assert "staging-only-rule" in merged
    assert "Komponenty/staging/extra/" in merged


def test_runtime_files_excluded_from_candidates(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env
    runtime = staging / "Komponenty" / "integracjagpt" / "data"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "gpt_config.json").write_text('{"token":"x"}', encoding="utf-8")
    (staging / "giclee_app").mkdir(parents=True, exist_ok=True)
    (staging / "giclee_app" / "changed.py").write_text("x = 1\n", encoding="utf-8")

    report = gap.audit_staging_repo(staging, log=[])
    assert "Komponenty/integracjagpt/data/gpt_config.json" in report.runtime_hits
    assert any("giclee_app" in c for c in report.commit_candidates)


def test_secret_scan_blocks_commit(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env
    bad = staging / "Komponenty" / "evil.py"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text('API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', encoding="utf-8")

    report = gap.audit_staging_repo(staging, log=[])
    assert report.blocked
    assert report.secret_hits


def test_audit_ignores_fake_secrets_in_test_files(tmp_path) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    test_file = tmp_path / "tests" / "test_gicleeapp_push.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\nSHOPIFY_API_KEY=\n',
        encoding="utf-8",
    )

    assert not gap.scan_file_secrets(test_file, rel="tests/test_gicleeapp_push.py")
    assert gap._skip_secret_scan("tests/test_gicleeapp_push.py")


def test_remote_must_be_gicleeapp(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env
    subprocess.run(
        ["git", "remote", "set-url", "origin", "https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git"],
        cwd=staging,
        check=True,
        capture_output=True,
    )

    with pytest.raises(ValueError, match="gicleeapp"):
        gap.validate_staging_repo(staging)


def test_does_not_touch_gpt_mirror(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    source, staging = gicleeapp_env
    mirror = source / ".gpt_mirror"
    mirror.mkdir()
    (mirror / "GPT_README.md").write_text("mirror", encoding="utf-8")
    (source / "package.json").write_text("{}", encoding="utf-8")

    result = gap.safe_sync_to_staging(source, staging)
    assert not (staging / ".gpt_mirror").exists()
    assert not any(".gpt_mirror" in p for p in result.copied)


def test_explicit_git_add_not_all(gicleeapp_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env
    calls: list[list[str]] = []

    def fake_run_git(args, cwd, log=None):
        calls.append(args)

        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        if args[:2] == ["rev-parse", "HEAD"]:
            P.stdout = "abc123\n"
        elif args[:3] == ["diff", "--cached", "--name-only"]:
            P.stdout = "giclee_app/__init__.py\npackage.json\n"
        return P()

    monkeypatch.setattr(gap, "_run_git", fake_run_git)
    monkeypatch.setattr(gap, "validate_staging_repo", lambda *a, **k: None)
    monkeypatch.setattr(
        gap,
        "inspect_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )

    report = gap.GicleeAppAuditReport(
        commit_candidates=["giclee_app/__init__.py", "package.json"],
        commit_message="Refresh GicleeApp repository snapshot",
    )
    result = gap.commit_and_push_gicleeapp(report, staging_dir=staging, log=[])
    assert result.ok
    add_calls = [c for c in calls if c and c[0] == "add"]
    assert add_calls
    assert all("--" in c for c in add_calls)
    assert not any(c == ["add", "-A"] for c in add_calls)
    assert not any(c == ["add", "."] for c in add_calls)
    staged_paths = [p for c in add_calls for p in c[2:]]
    assert "giclee_app/__init__.py" in staged_paths
    assert "package.json" in staged_paths


def test_commit_and_push_triggers_starter_sync(gicleeapp_env, monkeypatch, tmp_path) -> None:
    from Komponenty.integracjagpt import config as cfg
    from Komponenty.integracjagpt import gicleeapp_push as gap
    from Komponenty.integracjagpt import starter_checkpoint as sc

    _, staging = gicleeapp_env
    starter = Path(cfg.GPT_STARTER_DIR)
    (starter / "CURRENT_APP_STATE.md").write_text(
        f"# Current App State\n\n{sc.MARKER_START}\nold\n{sc.MARKER_END}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "GPT_STARTER_DIR", starter)

    def fake_run_git(args, cwd, log=None):
        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        if args[:2] == ["rev-parse", "HEAD"]:
            P.stdout = "deadbeefcafe\n"
        elif args[:3] == ["diff", "--cached", "--name-only"]:
            P.stdout = "giclee_app/__init__.py\n"
        return P()

    monkeypatch.setattr(gap, "_run_git", fake_run_git)
    monkeypatch.setattr(gap, "validate_staging_repo", lambda *a, **k: None)
    monkeypatch.setattr(
        gap,
        "inspect_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )

    report = gap.GicleeAppAuditReport(
        commit_candidates=["giclee_app/__init__.py"],
        commit_message="Refresh GicleeApp repository snapshot",
    )
    result = gap.commit_and_push_gicleeapp(report, staging_dir=staging, log=[])
    assert result.ok
    assert result.starter_sync_updated_files
    updated = (starter / "CURRENT_APP_STATE.md").read_text(encoding="utf-8")
    assert "deadbee" in updated


def test_no_changes_detected(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env
    report = gap.audit_staging_repo(staging, log=[])
    assert report.no_changes
    assert not report.blocked


def test_behind_remote_requires_ff_only(gicleeapp_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env

    def fake_inspect(staging_dir, *, pull_ff_only=False, log=None):
        if pull_ff_only:
            return gap.BranchSyncStatus(
                ok=False,
                behind=2,
                message="git pull --ff-only nie powiódł się — zatrzymaj workflow.",
            )
        return gap.BranchSyncStatus(ok=True, behind=2, message="main...origin/main [behind 2]")

    monkeypatch.setattr(gap, "inspect_branch_sync", fake_inspect)
    monkeypatch.setattr(gap, "validate_staging_repo", lambda *a, **k: None)

    report = gap.GicleeAppAuditReport(commit_candidates=["a.py"])
    result = gap.commit_and_push_gicleeapp(report, staging_dir=staging, log=[])
    assert not result.ok
    assert "ff-only" in result.message


def test_diverged_branch_blocks_audit(gicleeapp_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env

    monkeypatch.setattr(
        gap,
        "inspect_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(
            ok=False,
            diverged=True,
            ahead=1,
            behind=1,
            message="Branch rozjechany",
        ),
    )

    report = gap.audit_staging_repo(staging, log=[])
    assert report.blocked
    assert report.branch_status.diverged


def test_blocked_deletions_review_only(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap
    from Komponenty.integracjagpt.config import GICLEEAPP_REVIEW_ONLY_FILES

    _, staging = gicleeapp_env
    review_path = staging / GICLEEAPP_REVIEW_ONLY_FILES[0]
    review_path.unlink()

    report = gap.audit_staging_repo(staging, log=[])
    assert GICLEEAPP_REVIEW_ONLY_FILES[0] in report.blocked_deletions
    assert GICLEEAPP_REVIEW_ONLY_FILES[0] not in report.deletable_files


def test_commit_message_default(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap
    from Komponenty.integracjagpt.config import GICLEEAPP_COMMIT_MESSAGE

    report = gap.GicleeAppAuditReport()
    assert report.commit_message == GICLEEAPP_COMMIT_MESSAGE


def test_env_example_placeholders_do_not_block(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "env.example").write_text(
        "SHOPIFY_API_KEY=\nSHOPIFY_API_SECRET=\n",
        encoding="utf-8",
    )

    hits = gap.scan_file_secrets(staging / "env.example", rel="env.example")
    assert not hits


def test_staging_junk_paths_are_runtime(tmp_path) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    for rel in ("env", "env.example", "gpt_mirror/", "shopify_session.json", "README.md"):
        assert gap._is_runtime_path(rel)


def test_dry_run_report_format(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    source, staging = gicleeapp_env
    (source / "package.json").write_text('{"name":"cursor-api"}\n', encoding="utf-8")

    report = gap.dry_run_gicleeapp_push(source_dir=source, staging_dir=staging, log=[])
    lines = report.format_report()
    assert any("audyt" in ln.lower() for ln in lines)


def test_scratch_paths_are_runtime() -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    for rel in (
        "_tmp_foo.png",
        "_test_helper.py",
        "_test_squoosh.jpg",
        "_build_czesc7.py",
        "czesc5_julien_dupre_17-20.json",
        "czesc6_jusepe_ribera_21.json",
        "czesc7_van_gogh_25-28.json",
        "tmp_getty.txt",
        "tmp_getty_row.json",
        "_tmp_dims/original.jpg",
        "_test_out/mockup_test.webp",
    ):
        assert gap._is_runtime_path(rel), rel


def test_print_optimize_data_is_runtime() -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    assert gap._is_runtime_path("Komponenty/print_optimize/data/test_photos/foo.jpg")
    assert gap._is_runtime_path("Komponenty/print_optimize/data/ww_pairs/index.json")


def test_staged_runtime_paths_block_commit(gicleeapp_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env
    reset_calls: list[list[str]] = []

    def fake_run_git(args, cwd, log=None):
        if args[:2] == ["reset", "HEAD"]:
            reset_calls.append(args)

        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        if args[:3] == ["diff", "--cached", "--name-only"]:
            P.stdout = "Komponenty/_shared/data/activity_log.jsonl\ngiclee_app/__init__.py\n"
        return P()

    monkeypatch.setattr(gap, "_run_git", fake_run_git)
    monkeypatch.setattr(gap, "validate_staging_repo", lambda *a, **k: None)
    monkeypatch.setattr(
        gap,
        "inspect_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )

    report = gap.GicleeAppAuditReport(commit_candidates=["giclee_app/__init__.py"])
    result = gap.commit_and_push_gicleeapp(report, staging_dir=staging, log=[])
    assert not result.ok
    assert "niedozwolone" in result.message
    assert reset_calls


def test_known_component_runtime_paths_blocked() -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    blocked = (
        "Komponenty/stronaglowna/data/variants/home8/index.json",
        "Komponenty/stronaglowna/data/variants/home8/settings.json",
        "Komponenty/tldobio/data/collections.json",
        "Komponenty/tldobio/data/foo.jpg",
        "Komponenty/tldobio/data/foo.jpeg",
        "Komponenty/tldobio/data/foo.png",
        "Komponenty/tldobio/data/foo.webp",
        "Komponenty/integracjagpt/data/gpt_config.json",
        "Komponenty/dokumentysprzedazy/dane/orders_sync_state.json",
        "Komponenty/kpir/dane/kpir_settings.json",
        "Komponenty/stronaglowna/data/backups/index-20260706.json",
        "Komponenty/wspolpraca/data/variants/manifest.json",
        "Komponenty/wspolpraca/data/variants/ws1/page.wspolpraca.json",
    )
    for rel in blocked:
        assert gap._is_runtime_path(rel), rel

    allowed = (
        "Komponenty/stronaglowna/service.py",
        "Komponenty/katalog/data/variants/ka1/collection.json",
        "giclee_app/studio/katalog_data_map.py",
    )
    for rel in allowed:
        assert not gap._is_runtime_path(rel), rel


def test_expand_path_entries_expands_untracked_directory(gicleeapp_env) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env
    data_dir = staging / "Komponenty" / "katalog" / "data" / "variants" / "ka1"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "collection.json").write_text("{}", encoding="utf-8")

    expanded = gap._expand_path_entries(staging, "Komponenty/katalog/data")
    assert "Komponenty/katalog/data/variants/ka1/collection.json" in expanded


def test_staged_extra_paths_block_commit(gicleeapp_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeapp_push as gap

    _, staging = gicleeapp_env

    def fake_run_git(args, cwd, log=None):
        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        if args[:3] == ["diff", "--cached", "--name-only"]:
            P.stdout = "giclee_app/__init__.py\nunexpected/evil.py\n"
        return P()

    monkeypatch.setattr(gap, "_run_git", fake_run_git)
    monkeypatch.setattr(gap, "validate_staging_repo", lambda *a, **k: None)
    monkeypatch.setattr(
        gap,
        "inspect_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )

    report = gap.GicleeAppAuditReport(commit_candidates=["giclee_app/__init__.py"])
    result = gap.commit_and_push_gicleeapp(report, staging_dir=staging, log=[])
    assert not result.ok
    assert "unexpected/evil.py" in result.message
