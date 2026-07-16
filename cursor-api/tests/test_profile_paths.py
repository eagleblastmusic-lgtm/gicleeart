"""Ścieżki profili — classic, Studio Preview i produkcyjne Studio."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.app_paths import APP_NAME, data_path, local_root, log_path, roaming_root
from giclee_app.app_profile import (
    CLASSIC_PROFILE,
    STUDIO_PREVIEW_PROFILE,
    STUDIO_PROFILE,
    app_profile_context,
)
from giclee_app.studio.perf import studio_perf_store
from giclee_app.studio.state import LEGACY_STATE_PATH, default_state_path, studio_state_store


def test_classic_roots_unchanged_with_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    roaming = tmp_path / "roaming-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))

    assert local_root() == local
    assert roaming_root() == roaming
    assert local_root(app_name=CLASSIC_PROFILE.state_namespace) == local
    assert local_root(app_name=APP_NAME) == local


def test_studio_namespaces_are_distinct_siblings_of_classic_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    preview_root = local_root(app_name=STUDIO_PREVIEW_PROFILE.state_namespace)
    studio_root = local_root(app_name=STUDIO_PROFILE.state_namespace)

    assert preview_root == local.parent / "GicleeStudioPreview"
    assert studio_root == local.parent / "GicleeStudio"
    assert len({local, preview_root, studio_root}) == 3


def test_studio_states_use_separate_namespaces(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    preview_state = default_state_path(STUDIO_PREVIEW_PROFILE)
    production_state = default_state_path(STUDIO_PROFILE)
    classic_collision = data_path(
        "studio/studio_state.json",
        app_name=CLASSIC_PROFILE.state_namespace,
    ).write_path

    assert preview_state == (
        local.parent / "GicleeStudioPreview" / "data" / "studio" / "studio_state.json"
    )
    assert production_state == (
        local.parent / "GicleeStudio" / "data" / "studio" / "studio_state.json"
    )
    assert len({preview_state, production_state, classic_collision}) == 3
    assert classic_collision == local / "data" / "studio" / "studio_state.json"
    assert preview_state != LEGACY_STATE_PATH
    assert production_state != LEGACY_STATE_PATH


def test_perf_store_honors_explicit_and_scoped_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    explicit_preview = studio_perf_store(STUDIO_PREVIEW_PROFILE).write_path
    explicit_studio = studio_perf_store(STUDIO_PROFILE).write_path

    with app_profile_context(STUDIO_PROFILE):
        scoped_studio = studio_perf_store().write_path

    assert explicit_preview == (
        local.parent / "GicleeStudioPreview" / "logs" / "giclee_app" / "studio_perf.log"
    )
    assert explicit_studio == (
        local.parent / "GicleeStudio" / "logs" / "giclee_app" / "studio_perf.log"
    )
    assert scoped_studio == explicit_studio


def test_helper_paths_do_not_create_directories_on_resolve(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    preview_state = studio_state_store(STUDIO_PREVIEW_PROFILE).write_path
    production_state = studio_state_store(STUDIO_PROFILE).write_path
    preview_perf = studio_perf_store(STUDIO_PREVIEW_PROFILE).write_path
    production_perf = studio_perf_store(STUDIO_PROFILE).write_path
    classic_log = log_path("giclee_app/launcher.log").write_path

    for path in (
        preview_state,
        production_state,
        preview_perf,
        production_perf,
        classic_log,
    ):
        assert not path.exists()
        assert not path.parent.exists()
    assert not local.exists()
