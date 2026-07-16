"""Focused tests for runtime app profiles (STUDIO-ISOLATION-1)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.app_profile import (
    CLASSIC_PROFILE,
    PROFILES,
    STUDIO_PREVIEW_PROFILE,
    get_profile,
)


def test_classic_and_preview_are_distinct() -> None:
    assert CLASSIC_PROFILE.profile_id != STUDIO_PREVIEW_PROFILE.profile_id
    assert CLASSIC_PROFILE.state_namespace != STUDIO_PREVIEW_PROFILE.state_namespace
    assert CLASSIC_PROFILE.log_namespace != STUDIO_PREVIEW_PROFILE.log_namespace


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


def test_profiles_are_frozen() -> None:
    try:
        CLASSIC_PROFILE.profile_id = "mutated"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("AppProfile must be immutable")


def test_get_profile_registry() -> None:
    assert get_profile("classic") is CLASSIC_PROFILE
    assert get_profile("studio_preview") is STUDIO_PREVIEW_PROFILE
    assert "studio" not in PROFILES
