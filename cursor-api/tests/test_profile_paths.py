"""Ścieżki profili — klasyczny kontrakt vs namespace Studio Preview."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.app_paths import APP_NAME, data_path, local_root, log_path, roaming_root
from giclee_app.app_profile import CLASSIC_PROFILE, STUDIO_PREVIEW_PROFILE
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


def test_preview_namespace_is_sibling_of_classic_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    preview_root = local_root(app_name=STUDIO_PREVIEW_PROFILE.state_namespace)
    assert preview_root == local.parent / "GicleeStudioPreview"
    assert preview_root != local


def test_studio_state_uses_preview_namespace_not_classic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    preview_state = default_state_path(STUDIO_PREVIEW_PROFILE)
    classic_collision = data_path(
        "studio/studio_state.json",
        app_name=CLASSIC_PROFILE.state_namespace,
    ).write_path

    assert preview_state == (
        local.parent / "GicleeStudioPreview" / "data" / "studio" / "studio_state.json"
    )
    assert preview_state != classic_collision
    assert classic_collision == local / "data" / "studio" / "studio_state.json"
    assert preview_state != LEGACY_STATE_PATH


def test_helper_paths_do_not_create_directories_on_resolve(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    state_path = studio_state_store(STUDIO_PREVIEW_PROFILE).write_path
    perf_path = studio_perf_store(STUDIO_PREVIEW_PROFILE).write_path
    classic_log = log_path("giclee_app/launcher.log").write_path

    assert not state_path.exists()
    assert not state_path.parent.exists()
    assert not perf_path.exists()
    assert not perf_path.parent.exists()
    assert not classic_log.exists()
    assert not local.exists()
