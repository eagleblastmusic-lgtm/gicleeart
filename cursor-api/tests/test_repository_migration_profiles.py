from __future__ import annotations

import subprocess
from pathlib import Path

from tools.repository_safety.migration import build_migration_report


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo_with_profiles(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")

    files = {
        ".env": "SECRET=value\n",
        "Komponenty/notatnik/notatki/note.md": "private\n",
        "Komponenty/stronaglowna/data/variants/home1/index.json": "{}\n",
        "giclee_app/data/launcher_shortcuts.json": "{}\n",
        "logs/component.log": "log\n",
        "Komponenty/faq/data/backups/page.json": "{}\n",
        "Komponenty/blog/data/articles_cache.json": "{}\n",
        ".pytest_cache/v/cache/nodeids": "[]\n",
    }
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(repo, "add", "-f", "-A")
    _git(repo, "commit", "-m", "fixtures")
    return repo


def _sources(report) -> set[str]:
    return {item.source for item in report.items}


def test_dry_run_all_reports_every_migratable_profile(tmp_path: Path) -> None:
    repo = _repo_with_profiles(tmp_path)
    report = build_migration_report(
        repo,
        profile="all",
        local_app_data=tmp_path / "local",
        roaming_app_data=tmp_path / "roaming",
    )

    assert not report.blocked
    assert report.profile == "all"
    assert _sources(report) == {
        ".env",
        "Komponenty/notatnik/notatki/note.md",
        "Komponenty/stronaglowna/data/variants/home1/index.json",
        "giclee_app/data/launcher_shortcuts.json",
        "logs/component.log",
        "Komponenty/faq/data/backups/page.json",
        "Komponenty/blog/data/articles_cache.json",
    }
    assert ".pytest_cache/v/cache/nodeids" not in _sources(report)


def test_critical_profile_excludes_logs_backups_and_cache(tmp_path: Path) -> None:
    repo = _repo_with_profiles(tmp_path)
    report = build_migration_report(
        repo,
        profile="critical",
        local_app_data=tmp_path / "local",
        roaming_app_data=tmp_path / "roaming",
    )

    assert _sources(report) == {
        ".env",
        "Komponenty/notatnik/notatki/note.md",
        "Komponenty/stronaglowna/data/variants/home1/index.json",
        "giclee_app/data/launcher_shortcuts.json",
    }


def test_archive_and_cache_profiles_are_disjoint(tmp_path: Path) -> None:
    repo = _repo_with_profiles(tmp_path)
    archive = build_migration_report(
        repo,
        profile="archive",
        local_app_data=tmp_path / "local",
        roaming_app_data=tmp_path / "roaming",
    )
    cache = build_migration_report(
        repo,
        profile="cache",
        local_app_data=tmp_path / "local",
        roaming_app_data=tmp_path / "roaming",
    )

    assert _sources(archive) == {
        "logs/component.log",
        "Komponenty/faq/data/backups/page.json",
    }
    assert _sources(cache) == {"Komponenty/blog/data/articles_cache.json"}
    assert _sources(archive).isdisjoint(_sources(cache))


def test_copy_all_is_forbidden_before_destination_creation(tmp_path: Path) -> None:
    repo = _repo_with_profiles(tmp_path)
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"

    report = build_migration_report(
        repo,
        execute_copy=True,
        profile="all",
        local_app_data=local,
        roaming_app_data=roaming,
    )

    assert report.blocked
    assert report.items == []
    assert "profile 'all' is forbidden" in report.errors[0]
    assert not local.exists()
    assert not roaming.exists()


def test_unknown_profile_is_blocked(tmp_path: Path) -> None:
    repo = _repo_with_profiles(tmp_path)
    report = build_migration_report(
        repo,
        profile="everything",
        local_app_data=tmp_path / "local",
        roaming_app_data=tmp_path / "roaming",
    )

    assert report.blocked
    assert report.items == []
    assert "Unknown migration profile" in report.errors[0]
