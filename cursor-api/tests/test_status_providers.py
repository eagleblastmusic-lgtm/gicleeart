"""Testy status_providers — crash-safe, read-only."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio import status_providers
from giclee_app.studio.status_providers import StatusResult


def test_shopify_status_no_crash() -> None:
    st = status_providers.shopify_status()
    assert isinstance(st, StatusResult)
    assert isinstance(st.label, str)
    assert "accessToken" not in st.detail
    assert "token" not in st.detail.lower() or st.ok is False


def test_theme_dev_status_no_crash() -> None:
    st = status_providers.theme_dev_status()
    assert isinstance(st, StatusResult)


def test_github_and_gpt_mock() -> None:
    gh = status_providers.github_status()
    gpt = status_providers.gpt_snapshot_status()
    assert gh.ok is None
    assert gpt.ok is None


def test_component_counts_non_negative() -> None:
    total, visible = status_providers.component_counts()
    assert total >= 0
    assert visible >= 0
    assert visible <= total


def test_activity_log_lines_list() -> None:
    lines = status_providers.activity_log_lines(3)
    assert isinstance(lines, list)


def test_production_orders_count_safe() -> None:
    count = status_providers.production_orders_count()
    assert count is None or count >= 0


def test_refresh_all_topbar_keys() -> None:
    data = status_providers.refresh_all_topbar()
    assert set(data.keys()) == {"shopify", "theme_dev", "github", "gpt_snapshot"}
