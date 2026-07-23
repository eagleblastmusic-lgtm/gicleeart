"""Testy bezpiecznego GitHub push w komponencie Pushe."""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _init_git_repo(path: Path, *, remote: str = "", branch: str = "master") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True, capture_output=True)
    if remote:
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=path, check=True, capture_output=True)


@pytest.fixture
def pushe_env(tmp_path, monkeypatch):
    from Komponenty.pushe import service as svc

    root = tmp_path / "repo"
    root.mkdir()
    (root / "sections").mkdir()
    (root / "sections" / "hero.liquid").write_text("hero", encoding="utf-8")
    (root / "cursor-api").mkdir()
    (root / "cursor-api" / "readme.txt").write_text("api", encoding="utf-8")

    _init_git_repo(
        root,
        remote="https://github.com/eagleblastmusic-lgtm/gicleeart.git",
    )
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)

    monkeypatch.setattr(svc, "repo_root", lambda: root)
    return root


def test_github_remote_must_be_gicleeart(pushe_env) -> None:
    from Komponenty.pushe.service import assert_github_remote

    assert_github_remote("https://github.com/eagleblastmusic-lgtm/gicleeart.git")
    assert_github_remote("git@github.com:eagleblastmusic-lgtm/gicleeart.git")


def test_github_remote_rejects_similar_repo_name(pushe_env) -> None:
    from Komponenty.pushe.service import assert_github_remote

    with pytest.raises(ValueError, match="musi wskazywać"):
        assert_github_remote("https://github.com/eagleblastmusic-lgtm/gicleeart-backup.git")

    with pytest.raises(ValueError, match="musi wskazywać"):
        assert_github_remote("https://github.com/inna-organizacja/gicleeart.git")


def test_remote_gicleeart_gpt_blocked(pushe_env) -> None:
    from Komponenty.pushe.service import assert_github_remote

    with pytest.raises(ValueError, match="gicleeart-gpt"):
        assert_github_remote("https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git")


def test_remote_gicleeapp_blocked(pushe_env) -> None:
    from Komponenty.pushe.service import assert_github_remote

    with pytest.raises(ValueError, match="gicleeapp"):
        assert_github_remote("https://github.com/eagleblastmusic-lgtm/gicleeapp.git")


def test_gicleeart_gpt_rejected_before_gicleeart_substring(pushe_env) -> None:
    """gicleeart-gpt zawiera 'gicleeart' — guard musi odrzucić wcześniej."""
    from Komponenty.pushe.service import assert_github_remote

    with pytest.raises(ValueError, match="gicleeart-gpt"):
        assert_github_remote("git@github.com:eagleblastmusic-lgtm/gicleeart-gpt.git")


def test_dry_run_does_not_commit_or_push(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    root = pushe_env
    (root / "sections" / "new.liquid").write_text("new", encoding="utf-8")

    git_calls: list[list[str]] = []

    def fake_run_git(args, *, cwd, on_line=None):
        git_calls.append(args)
        if args[:2] == ["commit", "-m"] or args[:1] == ["push"]:
            pytest.fail("dry-run nie powinien commitować ani pushować")

        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        if args == ["branch", "--show-current"]:
            P.stdout = "master\n"
        elif args == ["remote", "get-url", "origin"]:
            P.stdout = "https://github.com/eagleblastmusic-lgtm/gicleeart.git\n"
        elif args[:2] == ["fetch", "origin"]:
            P.stdout = ""
        elif args == ["status", "-sb"]:
            P.stdout = "## master\n"
        elif args == ["status", "--short"]:
            P.stdout = "?? sections/new.liquid\n"
        elif args[:2] == ["diff", "--stat"]:
            P.stdout = ""
        return P()

    monkeypatch.setattr(svc, "_run_git", fake_run_git)
    report = svc.dry_run_github_push(on_line=None)
    assert isinstance(report, svc.GithubAuditReport)
    assert not any(a[:1] == ["push"] or a[:2] == ["commit", "-m"] for a in git_calls)


def test_no_git_add_all_in_service_source() -> None:
    from Komponenty.pushe import service as svc

    source = inspect.getsource(svc)
    assert '["add", "-A"]' not in source
    assert '["add", "."]' not in source
    assert "git add -A" not in source
    assert "git add ." not in source


def test_explicit_git_add_paths(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    root = pushe_env
    calls: list[list[str]] = []

    def fake_run_git(args, *, cwd, on_line=None):
        calls.append(args)

        class P:
            returncode = 0
            stdout = "abc123def456\n" if args[:2] == ["rev-parse", "HEAD"] else "ok\n"
            stderr = ""

        return P()

    monkeypatch.setattr(svc, "_run_git", fake_run_git)
    monkeypatch.setattr(
        svc,
        "inspect_branch_sync",
        lambda *a, **k: svc.BranchSyncStatus(ok=True, message="master...origin/master"),
    )

    report = svc.GithubAuditReport(
        branch="master",
        remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart.git",
        commit_candidates=["sections/hero.liquid"],
        commit_message="test commit",
    )
    result = svc.commit_and_push_github(report, on_line=None)
    assert result.ok
    add_calls = [c for c in calls if len(c) >= 3 and c[0] == "add" and c[1] == "--"]
    assert add_calls == [["add", "--", "sections/hero.liquid"]]
    assert not any("-A" in c for c in calls)


def test_secret_blocks_commit(pushe_env) -> None:
    from Komponenty.pushe import service as svc

    root = pushe_env
    bad = root / "sections" / "evil.liquid"
    bad.write_text('token = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', encoding="utf-8")

    report = svc.audit_repo_for_github_push(on_line=None)
    assert report.blocked
    assert report.secret_hits


def test_tests_directory_secrets_ignored(pushe_env) -> None:
    from Komponenty.pushe import service as svc

    root = pushe_env
    test_file = root / "cursor-api" / "tests" / "fixture.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\n',
        encoding="utf-8",
    )

    assert not svc.scan_file_secrets(test_file, rel="cursor-api/tests/fixture.py")
    assert svc._skip_secret_scan("cursor-api/tests/fixture.py")


def test_runtime_paths_excluded_from_candidates(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    root = pushe_env
    backup_rel = "cursor-api/Komponenty/stronaglowna/data/backups/index-test.json"
    backup_file = root / backup_rel
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.write_text("{}", encoding="utf-8")
    subprocess.run(["git", "add", "--", backup_rel], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "track backup"], cwd=root, check=True, capture_output=True)
    backup_file.write_text('{"v":2}', encoding="utf-8")

    monkeypatch.setattr(
        svc,
        "inspect_branch_sync",
        lambda *a, **k: svc.BranchSyncStatus(ok=True, message="master"),
    )

    report = svc.audit_repo_for_github_push(on_line=None)
    assert backup_rel in report.runtime_hits
    assert backup_rel in report.modified_files
    assert backup_rel not in report.commit_candidates


def test_is_runtime_path_unit() -> None:
    from Komponenty.pushe.service import _is_runtime_path

    assert _is_runtime_path(".env")
    assert _is_runtime_path(".env.local")
    assert _is_runtime_path("cursor-api/Komponenty/stronaglowna/data/backups/index.json")
    assert _is_runtime_path("Pliki startowe dla GPT/readme.md")
    assert _is_runtime_path("orders_sync_state.json")
    assert not _is_runtime_path("sections/hero.liquid")


def test_parse_porcelain_strips_quotes() -> None:
    from Komponenty.pushe import service as svc

    new, modified, deleted = svc._parse_porcelain(['?? "Pliki startowe dla GPT/"'])
    assert new == ["Pliki startowe dla GPT/"]
    assert svc._is_runtime_path(new[0])


def test_quoted_runtime_dir_not_in_candidates(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    root = pushe_env
    gpt_dir = root / "Pliki startowe dla GPT"
    gpt_dir.mkdir()
    (gpt_dir / "readme.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(
        svc,
        "inspect_branch_sync",
        lambda *a, **k: svc.BranchSyncStatus(ok=True, message="master"),
    )

    def fake_run_git(args, *, cwd, on_line=None):
        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        if args == ["status", "--short"]:
            P.stdout = '?? "Pliki startowe dla GPT/"\n'
        elif args[:2] == ["diff", "--stat"]:
            P.stdout = ""
        elif args == ["branch", "--show-current"]:
            P.stdout = "master\n"
        elif args == ["remote", "get-url", "origin"]:
            P.stdout = "https://github.com/eagleblastmusic-lgtm/gicleeart.git\n"
        elif args[:2] == ["fetch", "origin"]:
            pass
        elif args == ["status", "-sb"]:
            P.stdout = "## master\n"
        return P()

    monkeypatch.setattr(svc, "_run_git", fake_run_git)
    report = svc.audit_repo_for_github_push(on_line=None)
    assert any("Pliki startowe dla GPT" in h for h in report.runtime_hits)
    assert not any("Pliki startowe" in p for p in report.commit_candidates)


def test_diverged_branch_blocks_audit(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    monkeypatch.setattr(
        svc,
        "inspect_branch_sync",
        lambda *a, **k: svc.BranchSyncStatus(
            ok=False,
            diverged=True,
            ahead=1,
            behind=1,
            message="Branch rozjechany",
        ),
    )

    report = svc.audit_repo_for_github_push(on_line=None)
    assert report.blocked
    assert report.branch_status.diverged


def test_behind_branch_uses_ff_only_pull_on_commit(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    pull_calls: list[list[str]] = []

    def fake_inspect(root, branch, *, pull_ff_only=False, on_line=None):
        if pull_ff_only:
            pull_calls.append(["pull", "--ff-only", "origin", branch])
            return svc.BranchSyncStatus(ok=True, message="master (po ff-only pull)", pulled=True)
        return svc.BranchSyncStatus(ok=True, behind=2, message="master [behind 2]")

    monkeypatch.setattr(svc, "inspect_branch_sync", fake_inspect)
    monkeypatch.setattr(
        svc,
        "_run_git",
        lambda args, *, cwd, on_line=None: type(
            "P",
            (),
            {"returncode": 0, "stdout": "sha\n", "stderr": ""},
        )(),
    )

    report = svc.GithubAuditReport(
        branch="master",
        remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart.git",
        commit_candidates=["sections/hero.liquid"],
        commit_message="msg",
    )
    svc.commit_and_push_github(report, on_line=None)
    assert pull_calls == [["pull", "--ff-only", "origin", "master"]]


def test_no_changes_no_empty_commit(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    commits: list[list[str]] = []

    def fake_run_git(args, *, cwd, on_line=None):
        if args[:2] == ["commit", "-m"]:
            commits.append(args)

        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        return P()

    monkeypatch.setattr(svc, "_run_git", fake_run_git)

    report = svc.GithubAuditReport(
        branch="master",
        remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart.git",
        no_changes=True,
    )
    result = svc.commit_and_push_github(report, on_line=None)
    assert result.ok
    assert not commits


def test_push_only_sends_existing_local_commits_without_empty_commit(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    calls: list[list[str]] = []

    def fake_run_git(args, *, cwd, on_line=None):
        calls.append(args)

        class P:
            returncode = 0
            stdout = (
                "1234567890abcdef1234567890abcdef12345678\n"
                if args == ["rev-parse", "HEAD"]
                else ""
            )
            stderr = ""

        return P()

    monkeypatch.setattr(svc, "_run_git", fake_run_git)
    monkeypatch.setattr(
        svc,
        "inspect_branch_sync",
        lambda *args, **kwargs: svc.BranchSyncStatus(ok=True, ahead=2),
    )
    report = svc.GithubAuditReport(
        branch="master",
        remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart.git",
        push_only=True,
        unpushed_commits=2,
    )

    result = svc.commit_and_push_github(report)

    assert result.ok
    assert ["push", "origin", "master"] in calls
    assert not any(call[:1] in (["add"], ["commit"]) for call in calls)


def test_module_does_not_import_integracjagpt_push() -> None:
    from Komponenty.pushe import service as svc

    source = inspect.getsource(svc)
    assert "gicleeart_gpt_push" not in source
    assert "gicleeapp_push" not in source
    assert "integracjagpt" not in source


def test_wrong_remote_blocks_audit(pushe_env) -> None:
    from Komponenty.pushe import service as svc

    subprocess.run(
        ["git", "remote", "set-url", "origin", "https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git"],
        cwd=pushe_env,
        check=True,
        capture_output=True,
    )

    report = svc.audit_repo_for_github_push(on_line=None)
    assert report.blocked
    assert "gicleeart-gpt" in report.error


def test_deletions_not_staged_without_include_deletions(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    calls: list[list[str]] = []

    def fake_run_git(args, *, cwd, on_line=None):
        calls.append(args)

        class P:
            returncode = 0
            stdout = "abc\n" if args[:2] == ["rev-parse", "HEAD"] else ""
            stderr = ""

        return P()

    monkeypatch.setattr(svc, "_run_git", fake_run_git)
    monkeypatch.setattr(
        svc,
        "inspect_branch_sync",
        lambda *a, **k: svc.BranchSyncStatus(ok=True, message="ok"),
    )

    report = svc.GithubAuditReport(
        branch="master",
        remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart.git",
        commit_candidates=["sections/hero.liquid"],
        deletable_files=["sections/old.liquid"],
        commit_message="msg",
    )
    svc.commit_and_push_github(report, include_deletions=False, on_line=None)
    staged = [c[2] for c in calls if len(c) >= 3 and c[0] == "add" and c[1] == "--"]
    assert "sections/old.liquid" not in staged


def test_deletions_staged_when_include_deletions(pushe_env, monkeypatch) -> None:
    from Komponenty.pushe import service as svc

    calls: list[list[str]] = []

    def fake_run_git(args, *, cwd, on_line=None):
        calls.append(args)

        class P:
            returncode = 0
            stdout = "abc\n" if args[:2] == ["rev-parse", "HEAD"] else ""
            stderr = ""

        return P()

    monkeypatch.setattr(svc, "_run_git", fake_run_git)
    monkeypatch.setattr(
        svc,
        "inspect_branch_sync",
        lambda *a, **k: svc.BranchSyncStatus(ok=True, message="ok"),
    )

    report = svc.GithubAuditReport(
        branch="master",
        remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart.git",
        commit_candidates=["sections/hero.liquid"],
        deletable_files=["sections/old.liquid"],
        commit_message="msg",
    )
    svc.commit_and_push_github(report, include_deletions=True, on_line=None)
    staged = [c[2] for c in calls if len(c) >= 3 and c[0] == "add" and c[1] == "--"]
    assert "sections/old.liquid" in staged
