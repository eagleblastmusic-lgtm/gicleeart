"""Testy workflow Push GicleeArt-GPT (motyw → .gpt_mirror → gicleeart-gpt)."""

from __future__ import annotations

import inspect
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


def _write_mirror_baseline(mirror: Path) -> None:
    for rel in ("GPT_README.md", "SYNC_NOTES.md", "REVIEW_MANIFEST.json", "sections/a.liquid"):
        p = mirror / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"baseline:{rel}", encoding="utf-8")


@pytest.fixture
def gicleeart_env(tmp_path, monkeypatch):
    from Komponenty.integracjagpt import config as cfg
    from Komponenty.integracjagpt import mirror as mir
    from Komponenty.integracjagpt.config import GptConfig

    theme = tmp_path / "theme"
    mirror = tmp_path / "mirror"
    theme.mkdir()
    mirror.mkdir()

    for rel in ("sections", "assets", "docs/review-demos"):
        (theme / rel).mkdir(parents=True)
    (theme / "sections" / "hero.liquid").write_text("hero", encoding="utf-8")

    _init_git_repo(
        mirror,
        remote="https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git",
    )
    _write_mirror_baseline(mirror)

    monkeypatch.setattr(cfg, "THEME_ROOT", theme)
    monkeypatch.setattr(mir, "THEME_ROOT", theme)
    monkeypatch.setattr(cfg, "MIRROR_DIR", mirror)
    monkeypatch.setattr(mir, "MIRROR_DIR", mirror)

    gpt_cfg = GptConfig(remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git")
    subprocess.run(["git", "add", "-A"], cwd=mirror, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "test baseline"],
        cwd=mirror,
        check=True,
        capture_output=True,
    )

    return theme, mirror, gpt_cfg


def test_remote_must_be_gicleeart_gpt(gicleeart_env) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    _, _, gpt_cfg = gicleeart_env
    gap.validate_mirror_config(gpt_cfg)

    bad = gpt_cfg
    bad.remote_url = "https://github.com/eagleblastmusic-lgtm/other-repo.git"
    with pytest.raises(ValueError, match="gicleeart-gpt"):
        gap.validate_mirror_config(bad)


def test_remote_gicleeapp_rejected(gicleeart_env) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    _, mirror, gpt_cfg = gicleeart_env
    subprocess.run(
        ["git", "remote", "set-url", "origin", "https://github.com/eagleblastmusic-lgtm/gicleeapp.git"],
        cwd=mirror,
        check=True,
        capture_output=True,
    )
    gpt_cfg.remote_url = "https://github.com/eagleblastmusic-lgtm/gicleeapp.git"

    with pytest.raises(ValueError, match="gicleeapp"):
        gap.validate_mirror_config(gpt_cfg)


def test_module_does_not_import_gicleeapp_push() -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    source = inspect.getsource(gap)
    assert "gicleeapp_push" not in source


def test_workflow_does_not_touch_gicleeapp_staging(gicleeart_env) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    source = inspect.getsource(gap)
    assert "_gicleeapp_staging" not in source
    assert "GICLEEAPP_STAGING" not in source


def test_workflow_does_not_shopify_push(gicleeart_env) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    source = inspect.getsource(gap)
    for token in ("shopify theme push", "theme push", "shopify_push", "Komponenty.pushe"):
        assert token not in source


def test_dry_run_does_not_commit(gicleeart_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap
    from Komponenty.integracjagpt.mirror import SyncResult
    from Komponenty.integracjagpt.review_session import ReviewSession

    theme, mirror, gpt_cfg = gicleeart_env
    (theme / "sections" / "new.liquid").write_text("new", encoding="utf-8")

    commits: list[list[str]] = []

    def fake_run_git(args, cwd, log=None):
        if args[:2] == ["commit", "-m"]:
            commits.append(args)
        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        return P()

    monkeypatch.setattr(gap, "mirror_run_git", fake_run_git)
    monkeypatch.setattr(
        gap,
        "sync_theme_to_mirror",
        lambda *a, **k: SyncResult(copied=["sections/new.liquid"]),
    )
    monkeypatch.setattr(gap, "ensure_mirror_clone", lambda *a, **k: mirror)

    session = ReviewSession(review_goal="dry-run only")
    report = gap.dry_run_gicleeart_gpt_push(gpt_cfg, session, log=[])
    assert not commits
    assert isinstance(report, gap.GicleeArtGptAuditReport)


def test_secret_scan_blocks_commit(gicleeart_env) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    _, mirror, gpt_cfg = gicleeart_env
    bad = mirror / "sections" / "evil.liquid"
    bad.write_text('token = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', encoding="utf-8")

    from Komponenty.integracjagpt.review_session import ReviewSession

    report = gap.audit_mirror_repo(mirror, gpt_cfg, ReviewSession(), log=[])
    assert report.blocked
    assert report.secret_hits


def test_tests_directory_secrets_ignored(gicleeart_env) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    _, mirror, _ = gicleeart_env
    test_file = mirror / "tests" / "fixture.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\nSHOPIFY_API_KEY=\n',
        encoding="utf-8",
    )

    assert not gap.scan_file_secrets(test_file, rel="tests/fixture.py")
    assert gap._skip_secret_scan("tests/fixture.py")


def test_diverged_branch_blocks_audit(gicleeart_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap
    from Komponenty.integracjagpt.review_session import ReviewSession

    _, mirror, gpt_cfg = gicleeart_env

    monkeypatch.setattr(
        gap,
        "inspect_mirror_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(
            ok=False,
            diverged=True,
            ahead=1,
            behind=1,
            message="Branch rozjechany",
        ),
    )

    report = gap.audit_mirror_repo(mirror, gpt_cfg, ReviewSession(), log=[])
    assert report.blocked
    assert report.branch_status.diverged


def test_no_changes_no_empty_commit(gicleeart_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap
    from Komponenty.integracjagpt.review_session import ReviewSession

    _, mirror, gpt_cfg = gicleeart_env
    commits: list[list[str]] = []

    def fake_run_git(args, cwd, log=None):
        if args[:2] == ["commit", "-m"]:
            commits.append(args)

        class P:
            returncode = 0
            stdout = "abc123\n" if args[:2] == ["rev-parse", "HEAD"] else ""
            stderr = ""

        return P()

    monkeypatch.setattr(gap, "mirror_run_git", fake_run_git)
    monkeypatch.setattr(gap, "ensure_mirror_clone", lambda *a, **k: mirror)
    monkeypatch.setattr(gap, "validate_mirror_config", lambda *a, **k: None)
    monkeypatch.setattr(
        gap,
        "inspect_mirror_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )

    report = gap.GicleeArtGptAuditReport(no_changes=True)
    result = gap.commit_and_push_gicleeart_gpt(report, gpt_cfg, ReviewSession(), log=[])
    assert result.ok
    assert not commits


def test_explicit_git_add_not_all(gicleeart_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap
    from Komponenty.integracjagpt.mirror import SyncResult
    from Komponenty.integracjagpt.review_session import ReviewSession

    _, mirror, gpt_cfg = gicleeart_env
    calls: list[list[str]] = []

    def fake_run_git(args, cwd, log=None):
        calls.append(args)

        class P:
            returncode = 0
            stdout = "abc123def456\n" if args[:2] == ["rev-parse", "HEAD"] else "ok\n"
            stderr = ""

        return P()

    monkeypatch.setattr(gap, "mirror_run_git", fake_run_git)
    monkeypatch.setattr(gap, "ensure_mirror_clone", lambda *a, **k: mirror)
    monkeypatch.setattr(gap, "validate_mirror_config", lambda *a, **k: None)
    monkeypatch.setattr(
        gap,
        "inspect_mirror_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )
    monkeypatch.setattr(
        gap,
        "_finalize_manifest_snapshot_commit",
        lambda *a, **k: "abc123def456",
    )
    monkeypatch.setattr(gap, "_verify_manifest_snapshot_commit", lambda *a, **k: None)

    report = gap.GicleeArtGptAuditReport(
        commit_candidates=["sections/a.liquid", "sections/b.liquid"],
        commit_message="review: test 2026-07-05 12:00",
        sync=SyncResult(),
    )
    result = gap.commit_and_push_gicleeart_gpt(report, gpt_cfg, ReviewSession(), log=[])
    assert result.ok
    add_calls = [c for c in calls if c and c[0] == "add"]
    assert add_calls
    assert all("--" in c for c in add_calls)
    assert not any(c == ["add", "-A"] for c in add_calls)
    assert not any(c == ["add", "."] for c in add_calls)


def test_no_git_add_all_in_module_source() -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap

    source = inspect.getsource(gap)
    assert '["add", "-A"]' not in source
    assert '["add", "."]' not in source


def test_gui_old_push_removed_or_redirected() -> None:
    from Komponenty.integracjagpt import gui

    source = inspect.getsource(gui)
    assert "push_mirror_to_github" not in source
    assert "_run_push" not in source
    assert "Push → GPT GitHub" not in source
    assert "Push GicleeArt-GPT do GitHub" in source


def test_full_cycle_uses_secured_gicleeart_flow() -> None:
    from Komponenty.integracjagpt import gui

    full_cycle = inspect.getsource(gui.IntegracjaGptApp._run_full_cycle)
    prepare = inspect.getsource(gui.IntegracjaGptApp._finish_full_cycle_prepare)
    assert "push_mirror_to_github" not in full_cycle
    assert "push_mirror_to_github" not in prepare
    assert "skip_sync=True" in prepare
    assert "_start_gicleeart_gpt_push" in prepare


def test_manifest_finalize_and_verify_called(gicleeart_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap
    from Komponenty.integracjagpt.mirror import SyncResult
    from Komponenty.integracjagpt.review_session import ReviewSession

    _, mirror, gpt_cfg = gicleeart_env
    finalize_calls: list[tuple] = []
    verify_calls: list[tuple] = []

    def fake_finalize(mirror_p, sync, sess, log):
        finalize_calls.append((mirror_p, sync, sess))
        return "deadbeef1234"

    def fake_verify(mirror_p, sha, log):
        verify_calls.append((mirror_p, sha))

    def fake_run_git(args, cwd, log=None):
        class P:
            returncode = 0
            stdout = "deadbeef1234\n" if args[:2] == ["rev-parse", "HEAD"] else ""
            stderr = ""

        return P()

    monkeypatch.setattr(gap, "mirror_run_git", fake_run_git)
    monkeypatch.setattr(gap, "ensure_mirror_clone", lambda *a, **k: mirror)
    monkeypatch.setattr(gap, "validate_mirror_config", lambda *a, **k: None)
    monkeypatch.setattr(
        gap,
        "inspect_mirror_branch_sync",
        lambda *a, **k: gap.BranchSyncStatus(ok=True, message="main...origin/main"),
    )
    monkeypatch.setattr(gap, "_finalize_manifest_snapshot_commit", fake_finalize)
    monkeypatch.setattr(gap, "_verify_manifest_snapshot_commit", fake_verify)

    report = gap.GicleeArtGptAuditReport(
        commit_candidates=["sections/a.liquid"],
        commit_message="review: manifest test 2026-07-05 12:00",
        sync=SyncResult(),
    )
    result = gap.commit_and_push_gicleeart_gpt(report, gpt_cfg, ReviewSession(), log=[])
    assert result.ok
    assert len(finalize_calls) == 1
    assert len(verify_calls) == 1
    assert verify_calls[0][1] == "deadbeef1234"


def test_commit_message_from_review_session(gicleeart_env) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap
    from Komponenty.integracjagpt.review_session import ReviewSession

    session = ReviewSession(review_goal="header menu fix")
    msg = gap._commit_message_for(session)
    assert msg.startswith("review: header menu fix")


def test_dry_run_report_includes_deletions_and_stale(gicleeart_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import gicleeart_gpt_push as gap
    from Komponenty.integracjagpt.mirror import SyncResult
    from Komponenty.integracjagpt.review_session import ReviewSession

    _, mirror, gpt_cfg = gicleeart_env
    sync = SyncResult(copied=["sections/hero.liquid"], removed_stale=["sections/old.liquid"])

    monkeypatch.setattr(gap, "ensure_mirror_clone", lambda *a, **k: mirror)
    monkeypatch.setattr(gap, "sync_theme_to_mirror", lambda *a, **k: sync)

    report = gap.dry_run_gicleeart_gpt_push(
        gpt_cfg,
        ReviewSession(review_goal="report"),
        skip_sync=True,
        sync_result=sync,
        log=[],
    )
    lines = report.format_report()
    assert any("stale" in ln.lower() or "Usunięte" in ln for ln in lines)
