"""Kontrakt dwóch głównych przycisków repozytoriów w Integracji z GPT."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUI_PATH = ROOT / "cursor-api" / "Komponenty" / "integracjagpt" / "gui.py"


def test_repository_panel_names_exact_targets_and_branches() -> None:
    source = GUI_PATH.read_text(encoding="utf-8")

    for text in (
        "Repozytoria GitHub GicleeArt",
        "Repo główne",
        "eagleblastmusic-lgtm/gicleeart  •  branch master",
        "Sprawdź i push do repo głównego",
        "Repo robocze GPT",
        "eagleblastmusic-lgtm/gicleeart-gpt  •  branch main",
        "Sprawdź i push do repo roboczego GPT",
    ):
        assert text in source


def test_main_repo_button_reuses_bounded_pushe_workflow() -> None:
    source = GUI_PATH.read_text(encoding="utf-8")

    assert "command=self._start_main_repo_push" in source
    assert "from Komponenty.pushe.service import dry_run_github_push" in source
    assert "from Komponenty.pushe.service import commit_and_push_github" in source
    assert "include_deletions=include_deletions" in source
    assert "on_line=lines.append" in source


def test_working_repo_button_keeps_snapshot_workflow() -> None:
    source = GUI_PATH.read_text(encoding="utf-8")

    assert "command=self._start_gicleeart_gpt_push" in source
    assert "dry_run_gicleeart_gpt_push" in source
    assert "commit_and_push_gicleeart_gpt" in source


def test_component_page_has_vertical_scroll_and_mousewheel_support() -> None:
    source = GUI_PATH.read_text(encoding="utf-8")

    assert "from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas" in source
    assert "def _build_scrollable_root" in source
    assert 'orient="vertical", command=canvas.yview' in source
    assert "canvas.configure(yscrollcommand=scrollbar.set)" in source
    assert 'canvas.create_window((0, 0), window=content, anchor="nw")' in source
    assert "bind_mousewheel_to_canvas(canvas, content)" in source
    assert "page = self._build_scrollable_root()" in source
