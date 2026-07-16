"""Focused tests for runtime app profiles (STUDIO-ISOLATION-1/3)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.app_profile import (
    CLASSIC_PROFILE,
    PROFILES,
    STUDIO_PREVIEW_PROFILE,
    STUDIO_PROFILE,
    app_profile_context,
    current_profile,
    get_profile,
)


def test_all_profiles_have_distinct_runtime_identity() -> None:
    profiles = (CLASSIC_PROFILE, STUDIO_PREVIEW_PROFILE, STUDIO_PROFILE)
    assert len({p.profile_id for p in profiles}) == 3
    assert len({p.state_namespace for p in profiles}) == 3
    assert len({p.log_namespace for p in profiles}) == 3


def test_preview_identity() -> None:
    assert STUDIO_PREVIEW_PROFILE.profile_id == "studio_preview"
    assert STUDIO_PREVIEW_PROFILE.display_name == "Giclée Studio Preview"
    assert STUDIO_PREVIEW_PROFILE.channel == "preview"
    assert STUDIO_PREVIEW_PROFILE.is_preview is True
    assert "Giclée Studio Preview" in STUDIO_PREVIEW_PROFILE.window_title
    assert "PREVIEW" in STUDIO_PREVIEW_PROFILE.window_title


def test_classic_identity() -> None:
    assert CLASSIC_PROFILE.profile_id == "classic"
    assert CLASSIC_PROFILE.is_preview is False
    assert CLASSIC_PROFILE.channel == "stable"
    assert CLASSIC_PROFILE.state_namespace == "GicleeApp"
    assert CLASSIC_PROFILE.log_namespace == "GicleeApp"


def test_production_studio_identity_and_policy() -> None:
    assert STUDIO_PROFILE.profile_id == "studio"
    assert STUDIO_PROFILE.display_name == "Giclée Studio"
    assert STUDIO_PROFILE.channel == "stable"
    assert STUDIO_PROFILE.is_preview is False
    assert STUDIO_PROFILE.state_namespace == "GicleeStudio"
    assert STUDIO_PROFILE.log_namespace == "GicleeStudio"
    assert STUDIO_PROFILE.window_title == "Giclée Studio"
    assert STUDIO_PROFILE.allowed_component_stability == ("stable",)
    assert STUDIO_PROFILE.allows_component_stability("stable")
    assert not STUDIO_PROFILE.allows_component_stability("preview")
    assert not STUDIO_PROFILE.allows_component_stability("experimental")
    assert not STUDIO_PROFILE.allows_component_stability("legacy")


def test_preview_and_classic_accept_all_stability_channels() -> None:
    for profile in (CLASSIC_PROFILE, STUDIO_PREVIEW_PROFILE):
        for stability in ("stable", "preview", "experimental", "legacy"):
            assert profile.allows_component_stability(stability)


def test_profiles_are_frozen() -> None:
    try:
        CLASSIC_PROFILE.profile_id = "mutated"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("AppProfile must be immutable")


def test_get_profile_registry() -> None:
    assert get_profile("classic") is CLASSIC_PROFILE
    assert get_profile("studio_preview") is STUDIO_PREVIEW_PROFILE
    assert get_profile("studio") is STUDIO_PROFILE
    assert set(PROFILES) == {"classic", "studio_preview", "studio"}


def test_profile_context_is_scoped_and_restored() -> None:
    assert current_profile() is CLASSIC_PROFILE
    with app_profile_context(STUDIO_PROFILE):
        assert current_profile() is STUDIO_PROFILE
        with app_profile_context(STUDIO_PREVIEW_PROFILE):
            assert current_profile() is STUDIO_PREVIEW_PROFILE
        assert current_profile() is STUDIO_PROFILE
    assert current_profile() is CLASSIC_PROFILE
