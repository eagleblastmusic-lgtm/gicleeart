"""STUDIO-ISOLATION-2/3: availability and stability channel contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.app_profile import (
    CLASSIC_PROFILE,
    STUDIO_PREVIEW_PROFILE,
    STUDIO_PROFILE,
    app_profile_context,
)
from giclee_app.component_loader import (
    DEFAULT_COMPONENT_AVAILABILITY,
    DEFAULT_COMPONENT_STABILITY,
    INVALID_COMPONENT_STABILITY_FALLBACK,
    Component,
    discover_components,
)
from giclee_app.studio.component_index import StudioComponentIndex


def _write_component(root: Path, folder: str, manifest: dict | None = None) -> Path:
    component_dir = root / folder
    component_dir.mkdir()
    (component_dir / "__main__.py").write_text("", encoding="utf-8")
    if manifest is not None:
        (component_dir / "component.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
    return component_dir


def _component(folder: str, *, availability: tuple[str, ...], stability: str = "stable") -> Component:
    return Component(
        folder_name=folder,
        package_path=Path("/fake") / folder,
        name=folder,
        description="",
        availability=availability,
        stability=stability,
    )


def _build_index(components: list[Component], *, profile=None) -> StudioComponentIndex:  # noqa: ANN001
    with patch("giclee_app.studio.component_index.find_components_dir", return_value=Path("/fake")):
        with patch("giclee_app.studio.component_index.discover_components", return_value=components):
            return StudioComponentIndex.build(profile=profile)


def test_manifest_without_channel_fields_preserves_existing_behavior(tmp_path: Path) -> None:
    _write_component(tmp_path, "legacy_default", {"name": "Legacy default"})

    [component] = discover_components(tmp_path, include_hidden=True)

    assert component.availability == DEFAULT_COMPONENT_AVAILABILITY
    assert component.stability == DEFAULT_COMPONENT_STABILITY
    assert component.is_available_in("classic")
    assert component.is_available_in("studio_preview")
    assert component.is_available_in("studio")


def test_manifest_parses_canonical_availability_and_stability(tmp_path: Path) -> None:
    _write_component(
        tmp_path,
        "preview_only",
        {
            "availability": ["studio_preview", "classic", "studio_preview", "unknown"],
            "stability": "PREVIEW",
            "custom": "kept",
        },
    )

    [component] = discover_components(tmp_path, include_hidden=True)

    assert component.availability == ("classic", "studio_preview")
    assert component.stability == "preview"
    assert component.extras == {"custom": "kept"}


def test_explicit_invalid_availability_is_fail_closed(tmp_path: Path) -> None:
    _write_component(
        tmp_path,
        "invalid_availability",
        {"availability": ["unknown"], "stability": "stable"},
    )

    [component] = discover_components(tmp_path, include_hidden=True)

    assert component.availability == ()
    assert not component.is_available_in("classic")
    assert not component.is_available_in("studio_preview")
    assert not component.is_available_in("studio")


def test_invalid_stability_degrades_to_experimental(tmp_path: Path) -> None:
    _write_component(
        tmp_path,
        "invalid_stability",
        {"stability": "production-ish"},
    )

    [component] = discover_components(tmp_path, include_hidden=True)

    assert component.stability == INVALID_COMPONENT_STABILITY_FALLBACK
    assert component.stability == "experimental"


def test_preview_index_filters_components_by_profile() -> None:
    components = [
        _component("all", availability=("classic", "studio_preview", "studio")),
        _component("classic_only", availability=("classic",)),
        _component("preview_only", availability=("studio_preview",), stability="preview"),
    ]

    index = _build_index(components, profile=STUDIO_PREVIEW_PROFILE)

    assert index.profile_id == "studio_preview"
    assert [c.folder_name for c in index.all_components] == [
        "all",
        "classic_only",
        "preview_only",
    ]
    assert [c.folder_name for c in index.available_components] == ["all", "preview_only"]
    assert set(index.by_folder) == {"all", "preview_only"}
    assert index.availability_counts() == (3, 2, 2)


def test_classic_profile_can_build_a_distinct_index_contract() -> None:
    components = [
        _component("classic_only", availability=("classic",)),
        _component("preview_only", availability=("studio_preview",)),
    ]

    index = _build_index(components, profile=CLASSIC_PROFILE)

    assert index.profile_id == "classic"
    assert set(index.by_folder) == {"classic_only"}


def test_production_studio_requires_availability_and_stable_channel() -> None:
    components = [
        _component("stable_studio", availability=("studio",), stability="stable"),
        _component("preview_studio", availability=("studio",), stability="preview"),
        _component("experimental_studio", availability=("studio",), stability="experimental"),
        _component("legacy_studio", availability=("studio",), stability="legacy"),
        _component("stable_preview_only", availability=("studio_preview",), stability="stable"),
    ]

    index = _build_index(components, profile=STUDIO_PROFILE)

    assert index.profile_id == "studio"
    assert set(index.by_folder) == {"stable_studio"}
    assert index.availability_counts() == (5, 1, 1)


def test_preview_accepts_nonstable_channels() -> None:
    components = [
        _component("preview", availability=("studio_preview",), stability="preview"),
        _component("experimental", availability=("studio_preview",), stability="experimental"),
        _component("legacy", availability=("studio_preview",), stability="legacy"),
    ]

    index = _build_index(components, profile=STUDIO_PREVIEW_PROFILE)

    assert set(index.by_folder) == {"preview", "experimental", "legacy"}


def test_default_index_uses_scoped_profile_or_preview_fallback() -> None:
    components = [
        _component("stable_studio", availability=("studio",), stability="stable"),
        _component("preview_only", availability=("studio_preview",), stability="preview"),
    ]

    fallback = _build_index(components)
    assert fallback.profile_id == STUDIO_PREVIEW_PROFILE.profile_id
    assert set(fallback.by_folder) == {"preview_only"}

    with app_profile_context(STUDIO_PROFILE):
        production = _build_index(components)

    assert production.profile_id == STUDIO_PROFILE.profile_id
    assert set(production.by_folder) == {"stable_studio"}
