"""Izolacja Studio Preview — stan, logi, entrypointy, brak side effects."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.app_paths import data_path, local_root, log_path
from giclee_app.app_profile import CLASSIC_PROFILE, STUDIO_PREVIEW_PROFILE
from giclee_app.component_loader import Component
from giclee_app.studio import perf
from giclee_app.studio.state import LEGACY_STATE_PATH, StudioState, default_state_path


ROOT = Path(__file__).resolve().parents[1] / "giclee_app"

FORBIDDEN_CLASSIC_SIDE_EFFECTS = (
    "giclee_app.launcher",
    "giclee_app.launcher_app",
    "giclee_app.launcher_background_services",
    "Komponenty.produkcja.orders_sync",
    "Komponenty._shared.backup",
    "Komponenty.socialmedia.cykl.meta_publisher",
    "Komponenty.dokumentysprzedazy.orders_sync",
)


def _imports_in_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _make_comp(folder: str) -> Component:
    return Component(
        folder_name=folder,
        package_path=Path(f"/fake/{folder}"),
        name=folder.title(),
        description="",
        mode="subprocess",
        order=0,
    )


def test_main_does_not_import_launcher_studio() -> None:
    imports = _imports_in_file(ROOT / "__main__.py")
    assert "giclee_app.launcher_studio" not in imports
    assert "launcher_studio" not in imports
    text = (ROOT / "__main__.py").read_text(encoding="utf-8")
    assert "launcher_studio" not in text
    assert "studio_preview" not in text


def test_studio_preview_entrypoint_wires_preview_profile() -> None:
    text = (ROOT / "studio_preview.py").read_text(encoding="utf-8")
    assert "STUDIO_PREVIEW_PROFILE" in text
    assert "GicleeAppStudio(profile=STUDIO_PREVIEW_PROFILE)" in text
    imports = _imports_in_file(ROOT / "studio_preview.py")
    for forbidden in FORBIDDEN_CLASSIC_SIDE_EFFECTS:
        assert not any(
            imp == forbidden or imp.startswith(forbidden + ".") for imp in imports
        )


def test_profile_and_path_modules_import_without_creating_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    roaming = tmp_path / "roaming-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))

    from giclee_app.app_paths import local_root, roaming_root
    from giclee_app.app_profile import STUDIO_PREVIEW_PROFILE
    from giclee_app.studio.state import default_state_path

    _ = local_root()
    _ = roaming_root()
    _ = default_state_path(STUDIO_PREVIEW_PROFILE)

    assert not local.exists()
    assert not roaming.exists()
    assert not (local.parent / "GicleeStudioPreview").exists()


def test_preview_state_does_not_touch_legacy_or_classic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    legacy = tmp_path / "legacy_studio_state.json"
    legacy.write_text(
        json.dumps({"version": 1, "recent": [], "pinned": ["legacy-only"]}),
        encoding="utf-8",
    )
    legacy_before = legacy.read_bytes()

    classic_state = data_path(
        "studio/studio_state.json",
        app_name=CLASSIC_PROFILE.state_namespace,
    ).write_path
    classic_state.parent.mkdir(parents=True, exist_ok=True)
    classic_state.write_text(
        json.dumps({"version": 1, "recent": [], "pinned": ["classic-only"]}),
        encoding="utf-8",
    )
    classic_before = classic_state.read_bytes()

    path = default_state_path(STUDIO_PREVIEW_PROFILE)
    state = StudioState.load(path)
    state.record_launch(_make_comp("preview-comp"))
    state.toggle_pin("preview-comp")
    state.save()

    assert path.is_file()
    assert path != classic_state
    assert path != LEGACY_STATE_PATH
    assert path != legacy
    assert json.loads(path.read_text(encoding="utf-8"))["pinned"] == ["preview-comp"]
    assert classic_state.read_bytes() == classic_before
    assert legacy.read_bytes() == legacy_before


def test_corrupt_preview_state_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "studio_state.json"
    path.write_text("{not-json", encoding="utf-8")
    state = StudioState.load(path)
    assert state.recent == []
    assert state.pinned == []


def test_studio_perf_uses_preview_namespace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")

    preview_log = (
        local.parent / "GicleeStudioPreview" / "logs" / "giclee_app" / "studio_perf.log"
    )
    classic_log = local / "logs" / "giclee_app" / "studio_perf.log"
    classic_log.parent.mkdir(parents=True, exist_ok=True)
    classic_log.write_text("classic-keep\n", encoding="utf-8")
    classic_before = classic_log.read_bytes()

    monkeypatch.setattr(perf, "_DEFAULT_LOG_PATH", preview_log)
    monkeypatch.setattr(perf, "_LOG_PATH", preview_log)

    perf.log_event("isolation.check", value=1)

    assert preview_log.is_file()
    assert classic_log.read_bytes() == classic_before
    assert preview_log != classic_log


def test_component_business_logs_stay_on_classic_namespace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    from giclee_app.component_logs import component_log_write_path

    path = component_log_write_path("demo_component")
    assert path == local / "logs" / "components" / "demo_component.log"
    assert local_root() == local
    assert "GicleeStudioPreview" not in str(path)


def test_classic_launcher_log_contract_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "local-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    classic = log_path("giclee_app/studio_perf.log").write_path
    assert classic == local / "logs" / "giclee_app" / "studio_perf.log"
