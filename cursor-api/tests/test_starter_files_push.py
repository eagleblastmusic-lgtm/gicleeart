"""Testy push plików startowych GPT → monorepo."""

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
def starter_push_env(tmp_path, monkeypatch):
    from Komponenty.integracjagpt import config as cfg
    from Komponenty.integracjagpt import starter_files_push as sfp
    from Komponenty.integracjagpt import zip_knowledge as zk

    theme = tmp_path / "monorepo"
    starter = theme / cfg.GPT_STARTER_REL_PREFIX
    theme.mkdir()
    starter.mkdir()

    for name in zk.CLEAN_PACK_V38_ACTIVE_FILES:
        (starter / name).write_text(f"# {name}\n", encoding="utf-8")
    (starter / cfg.GPT_START_MESSAGE_FILE).write_text("start\n", encoding="utf-8")
    (starter / cfg.GPT_STARTER_ZIP_NAME).write_bytes(b"PK\x03\x04")

    _init_git_repo(theme)
    (theme / "README.md").write_text("root\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=theme, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "root"], cwd=theme, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "master"], cwd=theme, check=True, capture_output=True)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/master", "HEAD"], cwd=theme, check=True, capture_output=True)

    monkeypatch.setattr(cfg, "THEME_ROOT", theme)
    monkeypatch.setattr(cfg, "GPT_STARTER_DIR", starter)

    return theme, starter


def test_starter_push_allowlist_includes_template_and_zip(starter_push_env) -> None:
    from Komponenty.integracjagpt import starter_files_push as sfp

    paths = sfp.starter_push_allowlist_rel_paths()
    assert "Pliki startowe dla GPT/GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md" in paths
    assert "Pliki startowe dla GPT/giclee_cursor_architect_knowledge_v38.zip" in paths
    assert "Pliki startowe dla GPT/Wiadomość początkowa.txt" in paths


def test_dry_run_detects_modified_starter_file(starter_push_env) -> None:
    from Komponenty.integracjagpt import starter_files_push as sfp

    theme, starter = starter_push_env
    current = starter / "CURRENT_APP_STATE.md"
    current.write_text("# updated\n", encoding="utf-8")

    report = sfp.dry_run_starter_files_push(theme_root=theme, rebuild_zip=False, log=[])
    assert not report.blocked
    assert not report.no_changes
    assert "Pliki startowe dla GPT/CURRENT_APP_STATE.md" in report.commit_candidates


def test_dry_run_ignores_non_allowlist_starter_file(starter_push_env) -> None:
    from Komponenty.integracjagpt import starter_files_push as sfp

    theme, starter = starter_push_env
    (starter / "GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md").write_text("old\n", encoding="utf-8")

    report = sfp.dry_run_starter_files_push(theme_root=theme, rebuild_zip=False, log=[])
    assert "Pliki startowe dla GPT/GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md" in report.outside_allowlist_hits
    assert "Pliki startowe dla GPT/GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md" not in report.commit_candidates


def test_commit_and_push_starter_files(starter_push_env, monkeypatch) -> None:
    from Komponenty.integracjagpt import starter_files_push as sfp

    theme, starter = starter_push_env
    (starter / "CURRENT_APP_STATE.md").write_text("# push me\n", encoding="utf-8")
    report = sfp.dry_run_starter_files_push(theme_root=theme, rebuild_zip=False, log=[])
    assert report.commit_candidates

    pushed: list[list[str]] = []

    def fake_run_git(args, cwd, log=None):
        from Komponenty.integracjagpt.gicleeapp_push import _run_git as real_run

        if args[:2] in (["fetch", "origin"], ["push", "origin"]):
            if args[:2] == ["push", "origin"]:
                pushed.append(list(args))

            class _Proc:
                returncode = 0
                stdout = ""
                stderr = ""

            return _Proc()
        return real_run(args, cwd, log=log)

    monkeypatch.setattr(sfp, "_run_git", fake_run_git)

    result = sfp.commit_and_push_starter_files(report, theme_root=theme, log=[])
    assert result.ok
    assert result.commit_sha
    assert "Pliki startowe dla GPT/CURRENT_APP_STATE.md" in result.committed_files
    assert pushed == [["push", "origin", "master"]]


def test_gui_has_starter_files_push_button() -> None:
    from Komponenty.integracjagpt import gui

    source = Path(gui.__file__).read_text(encoding="utf-8")
    assert "_start_starter_files_push" in source
    assert "Push pliki startowe GPT do GitHub" in source
