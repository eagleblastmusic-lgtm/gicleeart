"""Testy workflow Push Giclee Viewer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _init_git_repo(path: Path, *, branch: str = "master") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True, capture_output=True)


@pytest.fixture
def viewer_push_env(tmp_path, monkeypatch):
    from Komponenty.integracjagpt import config as cfg

    repo = tmp_path / "giclee-viewer"
    repo.mkdir()
    (repo / "README.md").write_text("# viewer\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "App.cs").write_text("class App {}\n", encoding="utf-8")

    _init_git_repo(repo)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    remote = tmp_path / "giclee-viewer-remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "master", str(remote)],
        check=True,
        capture_output=True,
    )

    monkeypatch.setattr(cfg, "GICLEE_VIEWER_DIR", repo)
    monkeypatch.setattr(
        cfg,
        "GICLEE_VIEWER_REMOTE_URL",
        str(remote),
    )
    return repo


def test_ensure_viewer_remote_adds_origin(viewer_push_env) -> None:
    from Komponenty.integracjagpt import giclee_viewer_push as gvp

    repo = viewer_push_env
    url = gvp.ensure_viewer_remote(repo, log=[])
    assert "giclee-viewer" in url
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "giclee-viewer" in proc.stdout


def test_dry_run_detects_unpushed_clean_tree(viewer_push_env) -> None:
    from Komponenty.integracjagpt import giclee_viewer_push as gvp

    repo = viewer_push_env
    gvp.ensure_viewer_remote(repo, log=[])
    report = gvp.dry_run_giclee_viewer_push(repo_dir=repo, log=[])
    assert not report.blocked
    assert not report.no_changes
    assert report.push_only
    assert report.unpushed_commits >= 1


def test_dry_run_detects_modified_source_file(viewer_push_env) -> None:
    from Komponenty.integracjagpt import giclee_viewer_push as gvp

    repo = viewer_push_env
    gvp.ensure_viewer_remote(repo, log=[])
    (repo / "src" / "App.cs").write_text("class App { /* edit */ }\n", encoding="utf-8")
    report = gvp.dry_run_giclee_viewer_push(repo_dir=repo, log=[])
    assert "src/App.cs" in report.commit_candidates
    assert not report.push_only


def test_dry_run_blocks_runtime_obj_path(viewer_push_env) -> None:
    from Komponenty.integracjagpt import giclee_viewer_push as gvp

    repo = viewer_push_env
    obj = repo / "src" / "GicleeViewer.App" / "obj" / "Debug"
    obj.mkdir(parents=True)
    (obj / "cache.txt").write_text("x\n", encoding="utf-8")
    report = gvp.dry_run_giclee_viewer_push(repo_dir=repo, log=[])
    rel = "src/GicleeViewer.App/obj/Debug/cache.txt"
    assert rel not in report.commit_candidates


def test_commit_and_push_viewer_push_only(viewer_push_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import giclee_viewer_push as gvp

    repo = viewer_push_env
    gvp.ensure_viewer_remote(repo, log=[])
    report = gvp.dry_run_giclee_viewer_push(repo_dir=repo, log=[])
    assert report.push_only
    assert report.initial_push

    pushed: list[list[str]] = []

    def fake_run_git(args, cwd, log=None):
        from Komponenty.integracjagpt.gicleeapp_push import _run_git as real_run

        if args[:2] in (["fetch", "origin"], ["push", "-u"], ["push", "origin"]):
            if args[0] == "push":
                pushed.append(list(args))
            class _Proc:
                returncode = 0
                stdout = ""
                stderr = ""

            return _Proc()
        return real_run(args, cwd, log=log)

    monkeypatch.setattr(gvp, "_run_git", fake_run_git)

    result = gvp.commit_and_push_giclee_viewer(report, repo_dir=repo, log=[])
    assert result.ok
    assert result.push_only
    assert result.pushed_commits >= 1
    assert pushed and pushed[0][:3] == ["push", "-u", "origin"]


def test_gui_has_giclee_viewer_push_button() -> None:
    from Komponenty.integracjagpt import gui

    source = Path(gui.__file__).read_text(encoding="utf-8")
    assert "_start_giclee_viewer_push" in source
    assert "Push Giclee Viewer do GitHub" in source
