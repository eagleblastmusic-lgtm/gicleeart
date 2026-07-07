from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_does_not_call_on_show_synchronously_from_build() -> None:
    path = ROOT / "giclee_app" / "ui" / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    init_block = text.split("def __init__", 1)[1].split("\n    def ", 1)[0]

    assert "self.on_show()" not in init_block
    assert "_build_critical_shell" in text
    assert "_schedule_initial_refresh" in text
    assert "after(" in text


def test_dashboard_defers_theme_and_git_status() -> None:
    path = ROOT / "giclee_app" / "ui" / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    assert "_refresh_theme_status_deferred" in text
    assert "_refresh_git_status_deferred" in text
    assert "_schedule_theme_status_check" in text
    assert "_THEME_STATUS_DELAY_MS" in text
    assert "_GIT_STATUS_DELAY_MS" in text
    assert text.index("_THEME_STATUS_DELAY_MS") < text.index("_GIT_STATUS_DELAY_MS")


def test_status_providers_cache_git_and_shorten_theme_timeout() -> None:
    path = ROOT / "giclee_app" / "studio" / "status_providers.py"
    text = path.read_text(encoding="utf-8")

    assert "_THEME_DEV_TIMEOUT_SECONDS" in text
    assert "theme_dev_port_open(timeout=_THEME_DEV_TIMEOUT_SECONDS)" in text
    assert "_GITHUB_STATUS_CACHE_TTL_SECONDS" in text
    assert "_github_status_cache" in text
    assert "time.monotonic()" in text


def test_dashboard_has_deferred_status_perf_spans() -> None:
    path = ROOT / "giclee_app" / "ui" / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    assert "studio.dashboard.on_show.fast" in text
    assert "studio.dashboard.status.theme_dev.scheduled" in text
    assert "studio.dashboard.status.theme_dev.deferred" in text
    assert "studio.dashboard.status.theme_dev.done" in text
    assert "studio.dashboard.status.git.deferred" in text


def test_dashboard_uses_async_first_paint_and_deferred_sections() -> None:
    path = ROOT / "giclee_app" / "ui" / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    assert "uses_async_first_paint = True" in text
    assert "studio.dashboard.build.critical" in text
    assert "studio.dashboard.build.visible" in text
    assert "studio.dashboard.build.deferred" in text
    assert "studio.dashboard.visual.skeleton_ready" in text
    assert "studio.dashboard.visual.visible_ready" in text
    assert "studio.dashboard.visual.full_ready" in text
