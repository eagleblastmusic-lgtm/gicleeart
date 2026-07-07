from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.profiles import Budgets, get_profile, list_profiles


def test_list_profiles_contains_giclee_studio() -> None:
    assert "giclee_studio" in list_profiles()


def test_giclee_studio_profile_defaults() -> None:
    profile = get_profile("giclee_studio")
    assert profile.id == "giclee_studio"
    assert profile.display_name == "GicleeApp Studio Preview"
    assert profile.default_log_path.as_posix() == "giclee_app/logs/studio_perf.log"
    assert profile.output_root.as_posix() == "reports/performance"
    assert profile.budgets.slow_event_warning_ms == 80
    assert profile.budgets.slow_event_major_ms == 200
    assert profile.budgets.details_cta_warning_ms == 300
    assert profile.budgets.details_cta_major_ms == 700
    assert len(profile.manual_scenarios) == 9
    gf_open = profile.scenario_by_id()["gf_open"]
    assert gf_open.display_title == "GICLÉE FRAME — pierwsze otwarcie"
    assert gf_open.name == gf_open.display_title
    assert len(gf_open.click_path) >= 1
    assert gf_open.success_hint
    assert gf_open.expected_event_patterns == ("studio.gicleeframe",)
    assert profile.launch_config.env["GICLEE_STUDIO_PERF"] == "1"
    assert "giclee_app.studio_preview" in " ".join(profile.launch_config.command)


def test_all_manual_scenarios_have_human_readable_fields() -> None:
    profile = get_profile("giclee_studio")
    for scenario in profile.manual_scenarios:
        assert scenario.display_title.strip(), f"{scenario.id} missing display_title"
        assert len(scenario.click_path) >= 1, f"{scenario.id} missing click_path"
        assert scenario.success_hint.strip(), f"{scenario.id} missing success_hint"
        assert scenario.goal.strip(), f"{scenario.id} missing goal"
        assert len(scenario.observe) >= 1, f"{scenario.id} missing observe"
        assert scenario.name == scenario.display_title
        assert scenario.instruction


def test_resolve_log_path_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = get_profile("giclee_studio")
    monkeypatch.setattr(
        "tools.performance_agent.profiles._REPO_ROOT",
        tmp_path,
    )
    custom = profile.resolve_log_path(Path("custom/perf.log"))
    assert custom == tmp_path / "custom" / "perf.log"


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        get_profile("does_not_exist")
