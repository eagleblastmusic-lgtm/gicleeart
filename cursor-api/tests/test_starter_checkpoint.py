"""Testy auto-sync plików startowych GPT po Push GicleeApp."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _init_git_repo(path: Path, *, branch: str = "master") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True, capture_output=True)


@pytest.fixture
def starter_env(tmp_path, monkeypatch):
    from Komponenty.integracjagpt import config as cfg
    from Komponenty.integracjagpt import starter_checkpoint as sc

    source = tmp_path / "cursor-api"
    starter = tmp_path / "Pliki startowe dla GPT"
    theme = tmp_path / "monorepo"
    source.mkdir()
    starter.mkdir()
    theme.mkdir()

    (source / "giclee_app").mkdir()
    (source / "giclee_app" / "__init__.py").write_text(
        '__version__ = "1.41.2"\n',
        encoding="utf-8",
    )

    for name in sc._STARTER_FILES_WITH_MARKERS:
        (starter / name).write_text(
            f"# Title\n\n{sc.MARKER_START}\nPLACEHOLDER\n{sc.MARKER_END}\n\nTail\n",
            encoding="utf-8",
        )
    (starter / sc._MASTER_INDEX_FILE).write_text(
        "GicleeApp Studio v1.40.1\nAktualny checkpoint GicleeApp Studio: old\n",
        encoding="utf-8",
    )

    _init_git_repo(theme)
    (theme / "README.md").write_text("root\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=theme, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "root"], cwd=theme, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "master"], cwd=theme, check=True, capture_output=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/master", "HEAD"],
        cwd=theme,
        check=True,
        capture_output=True,
    )
    (theme / "local-only.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "local-only.txt"], cwd=theme, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat(perf-agent): add guided performance audit workflow"],
        cwd=theme,
        check=True,
        capture_output=True,
    )

    monkeypatch.setattr(cfg, "CURSOR_API_DIR", source)
    monkeypatch.setattr(cfg, "GPT_STARTER_DIR", starter)
    monkeypatch.setattr(cfg, "THEME_ROOT", theme)

    return source, starter, theme


def test_read_app_version(starter_env) -> None:
    from Komponenty.integracjagpt import starter_checkpoint as sc

    source, _, _ = starter_env
    assert sc.read_app_version(source) == "1.41.2"


def test_sync_starter_files_after_gicleeapp_push(starter_env) -> None:
    from Komponenty.integracjagpt import starter_checkpoint as sc

    source, starter, theme = starter_env
    result = sc.sync_starter_files_after_gicleeapp_push(
        gicleeapp_sha="abc1234567890",
        commit_message="Refresh GicleeApp repository snapshot",
        starter_dir=starter,
        source_dir=source,
        theme_root=theme,
        pushed_at=datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc),
    )

    assert result.ok
    assert result.version == "1.41.2"
    assert result.gicleeapp_sha_short == "abc1234"
    assert result.updated_files == ["CURRENT_APP_STATE.md"]

    current = (starter / "CURRENT_APP_STATE.md").read_text(encoding="utf-8")
    assert sc.MARKER_START in current
    assert "GicleeApp Studio v1.41.2" in current
    assert "`abc1234`" in current
    assert "Refresh GicleeApp repository snapshot" in current
    assert "feat(perf-agent)" in current
    assert "paczka v40" in current

    master = (starter / sc._MASTER_INDEX_FILE).read_text(encoding="utf-8")
    assert "v1.40.1" in master
    assert "abc1234" not in master
