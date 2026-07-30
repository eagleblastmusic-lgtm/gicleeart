from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from Komponenty._shared.theme_page_editor import service_base
from Komponenty._shared.theme_page_editor.service_base import validate_template_paths

from .gui import _config
from .registry import PAGE_ZONES
from .motion_config import (
    FIELD_TO_SETTING,
    load_motion_catalog,
    preset_values,
    validate_motion_settings,
)
from . import video_sequence
from .video_sequence import PARALLAX_MIDDLE_WEBM_REL


def _write_webp(path: Path, *, size: tuple[int, int] = (640, 360)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, (255, 255, 255, 128)).save(path, "WEBP", quality=80)


@pytest.fixture
def component_tmp() -> Path:
    path = Path(__file__).resolve().parent / f".test-video-{uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        if path.is_dir() and path.parent == Path(__file__).resolve().parent:
            shutil.rmtree(path)


def test_registry_matches_current_template() -> None:
    root = Path(__file__).resolve().parents[3]
    raw = (root / "templates" / "page.filozofia-marki.json").read_text(
        encoding="utf-8"
    )
    if raw.lstrip().startswith("/*"):
        raw = raw.split("*/", 1)[1]
    template = json.loads(raw)

    assert validate_template_paths(template, PAGE_ZONES) == []


def test_replace_video_sequence_builds_manifest_and_backup(
    component_tmp: Path, monkeypatch
) -> None:
    tmp_path = component_tmp
    root = tmp_path / "theme"
    assets = root / "assets"
    assets.mkdir(parents=True)
    _write_webp(assets / "giclee-philosophy-v3-frame-000.webp")
    _write_webp(assets / "giclee-philosophy-v3-frame-005.webp")
    (assets / "giclee-philosophy-v3-manifest.json").write_text(
        json.dumps(
            {
                "frameCount": 2,
                "width": 640,
                "height": 360,
                "prefix": "giclee-philosophy-v3-frame-",
                "digits": 3,
                "extension": ".webp",
            }
        ),
        encoding="utf-8",
    )
    source = tmp_path / "nowy-film.webm"
    source.write_bytes(b"video")

    def fake_export(
        _source: Path,
        output_pattern: Path,
        *,
        fps: int,
        width: int,
        height: int,
        composite_black: bool,
    ) -> None:
        assert fps == 60
        assert width == 1280
        assert height == 720
        assert composite_black is False
        for index in range(3):
            name = output_pattern.name.replace("%03d", f"{index:03d}")
            _write_webp(output_pattern.parent / name)

    monkeypatch.setattr(video_sequence, "_run_ffmpeg_export", fake_export)
    result = video_sequence.replace_video_sequence(
        source,
        quality="720p",
        root=root,
        backup_dir=tmp_path / "backups",
    )

    assert result.quality == "720p"
    assert result.status.frame_count == 3
    assert result.status.fps == 60
    assert result.status.has_alpha is True
    assert result.source_path.name == "giclee-philosophy-scroll-source.webm"
    assert not (assets / "giclee-philosophy-v3-frame-005.webp").exists()

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["frameCount"] == 3
    assert manifest["quality"] == "720p"
    assert manifest["source"] == result.source_path.name
    assert manifest["fps"] == 60
    assert manifest["codec"] == "webp"
    assert manifest["pixelFormat"] == "rgba"
    assert manifest["hasAlpha"] is True
    assert manifest["alphaMode"] == "straight"
    assert manifest["preserveAlpha"] is True
    assert manifest["alphaLostDuringConversion"] is False

    assert result.backup_path is not None
    with zipfile.ZipFile(result.backup_path) as archive:
        assert (
            "assets/giclee-philosophy-v3-frame-005.webp" in archive.namelist()
        )


def test_component_deploy_includes_only_active_scroll_videos(
    component_tmp: Path, monkeypatch
) -> None:
    tmp_path = component_tmp
    root = tmp_path / "theme"
    assets = root / "assets"
    assets.mkdir(parents=True)
    template_dir = root / "templates"
    template_dir.mkdir(parents=True)
    (template_dir / "page.filozofia-marki.json").write_text(
        json.dumps(
            {
                "sections": {
                    "a": {
                        "blocks": {
                            "b1": {
                                "settings": {
                                    "media_type": "scroll_video",
                                    "scroll_video_asset": "giclee-philosophy-frames",
                                    "scroll_video_engine": "video",
                                    "scroll_video_container": "mp4",
                                    "scroll_video_quality": "1080p",
                                }
                            }
                        }
                    },
                    "w": {
                        "blocks": {
                            "b2": {
                                "settings": {
                                    "media_type": "scroll_video",
                                    "scroll_video_asset": "giclee-philosophy-wrota",
                                    "scroll_video_engine": "video",
                                    "scroll_video_container": "mp4",
                                    "scroll_video_quality": "1080p",
                                }
                            }
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(service_base, "theme_root", lambda: root)
    monkeypatch.setattr(video_sequence, "theme_root", lambda: root)

    paths = service_base.component_deploy_relpaths(_config())

    assert "assets/giclee-philosophy-scroll-1080.mp4" in paths
    assert "assets/giclee-philosophy-wrota-scroll-1080.mp4" in paths
    assert "assets/giclee-philosophy-scroll-720.mp4" not in paths
    assert "assets/giclee-philosophy-wrota-scroll-720.mp4" not in paths
    assert "assets/giclee-philosophy-scroll-1080.webm" not in paths
    assert not any("frame-" in path for path in paths)
    assert "snippets/media.liquid" in paths


def test_selected_library_video_is_activated_in_stable_runtime_slot(
    component_tmp: Path,
) -> None:
    root = component_tmp / "theme"
    assets = root / "assets"
    templates = root / "templates"
    assets.mkdir(parents=True)
    templates.mkdir(parents=True)
    library_video = assets / (
        "giclee-scroll-library-philosophy-1080p-webm-test.webm"
    )
    library_poster = assets / (
        "giclee-scroll-library-philosophy-1080p-webm-test-poster.webp"
    )
    library_manifest = assets / (
        "giclee-scroll-library-philosophy-1080p-webm-test-manifest.json"
    )
    library_video.write_bytes(b"selected-webm")
    _write_webp(library_poster, size=(1920, 1080))
    library_manifest.write_text(
        json.dumps(
            {
                "version": 3,
                "mode": "video",
                "family": "philosophy",
                "quality": "1080p",
                "container": "webm",
                "video": library_video.name,
                "poster": library_poster.name,
                "frameCount": 210,
                "fps": 60,
                "width": 1920,
                "height": 1080,
                "hasAlpha": True,
                "codec": "vp9",
            }
        ),
        encoding="utf-8",
    )
    selected = video_sequence.NativeVideoAsset(
        family="philosophy",
        quality="1080p",
        container="webm",
        video=library_video.name,
        poster=library_poster.name,
        manifest=library_manifest.name,
        frame_count=210,
        fps=60,
        width=1920,
        height=1080,
        has_alpha=True,
        codec="vp9",
        total_bytes=library_video.stat().st_size,
    )
    (templates / "page.filozofia-marki.json").write_text(
        json.dumps(
            {
                "sections": {
                    "a": {
                        "blocks": {
                            "b": {
                                "settings": {
                                    "media_type": "scroll_video",
                                    "scroll_video_asset": "giclee-philosophy-frames",
                                    "scroll_video_engine": "video",
                                    "scroll_video_container": "webm",
                                    "scroll_video_quality": "1080p",
                                    "scroll_video_source": selected.source_spec,
                                }
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    changed = video_sequence.activate_selected_video_sources(root)

    runtime_video = assets / "giclee-philosophy-scroll-1080.webm"
    runtime_manifest = assets / "giclee-philosophy-webm-1080-manifest.json"
    assert runtime_video.read_bytes() == b"selected-webm"
    assert runtime_manifest in changed
    manifest = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    assert manifest["video"] == runtime_video.name
    assert manifest["activatedFrom"] == library_video.name
    assert manifest["hasAlpha"] is True


def test_dynamic_video_choices_filter_container_quality_and_family(
    component_tmp: Path,
) -> None:
    root = component_tmp / "theme"
    assets = root / "assets"
    assets.mkdir(parents=True)
    video = assets / "giclee-scroll-library-philosophy-1080p-webm-a.webm"
    poster = assets / "giclee-scroll-library-philosophy-1080p-webm-a-poster.webp"
    manifest = assets / "giclee-scroll-library-philosophy-1080p-webm-a-manifest.json"
    video.write_bytes(b"webm")
    _write_webp(poster, size=(1920, 1080))
    manifest.write_text(
        json.dumps(
            {
                "mode": "video",
                "family": "philosophy",
                "quality": "1080p",
                "container": "webm",
                "video": video.name,
                "poster": poster.name,
                "frameCount": 210,
                "fps": 60,
                "width": 1920,
                "height": 1080,
                "hasAlpha": True,
                "codec": "vp9",
            }
        ),
        encoding="utf-8",
    )

    choices = video_sequence.native_video_source_choices(
        {
            "scroll_video_engine": "video",
            "scroll_video_container": "webm",
            "scroll_video_quality": "1080p",
        },
        family="philosophy",
        root=root,
    )

    assert len(choices) == 1
    assert video.name in choices[0][1]
    selected_spec = next(value for value, label in choices if video.name in label)
    parsed = video_sequence.parse_native_video_source_spec(selected_spec)
    assert parsed["video"] == video.name
    assert parsed["manifest"] == manifest.name


def test_dynamic_video_choices_show_runtime_and_library_copy_once(
    component_tmp: Path,
) -> None:
    root = component_tmp / "theme"
    assets = root / "assets"
    assets.mkdir(parents=True)
    runtime_video = assets / "giclee-film-scroll-shared-720.webm"
    runtime_poster = assets / "giclee-film-scroll-shared-720-poster.webp"
    runtime_manifest = assets / "giclee-film-scroll-shared-webm-720-manifest.json"
    library_video = (
        assets
        / "giclee-scroll-library-shared-720p-webm-cosmic-transition-9d90ba170b.webm"
    )
    library_poster = (
        assets
        / "giclee-scroll-library-shared-720p-webm-cosmic-transition-9d90ba170b-poster.webp"
    )
    library_manifest = (
        assets
        / "giclee-scroll-library-shared-720p-webm-cosmic-transition-9d90ba170b-manifest.json"
    )
    runtime_video.write_bytes(b"same-webm")
    library_video.write_bytes(b"same-webm")
    _write_webp(runtime_poster, size=(1280, 720))
    _write_webp(library_poster, size=(1280, 720))
    common = {
        "mode": "video",
        "family": "shared",
        "quality": "720p",
        "container": "webm",
        "frameCount": 192,
        "fps": 24,
        "width": 1280,
        "height": 720,
        "hasAlpha": False,
        "codec": "vp9",
        "source": runtime_video.name,
        "generatedAt": "2026-07-29T17:06:40+00:00",
    }
    runtime_manifest.write_text(
        json.dumps(
            {
                **common,
                "video": runtime_video.name,
                "poster": runtime_poster.name,
                "activatedFrom": library_video.name,
            }
        ),
        encoding="utf-8",
    )
    library_manifest.write_text(
        json.dumps(
            {
                **common,
                "video": library_video.name,
                "poster": library_poster.name,
                "libraryAsset": True,
            }
        ),
        encoding="utf-8",
    )
    values = {
        "scroll_video_engine": "video",
        "scroll_video_container": "webm",
        "scroll_video_quality": "720p",
    }

    choices = video_sequence.native_video_source_choices(
        values,
        family="shared",
        root=root,
    )

    assert len(choices) == 1
    assert choices[0][0] == ""
    assert library_video.name in choices[0][1]
    assert runtime_video.name not in choices[0][1]

    listed_assets = video_sequence.list_native_video_assets(
        family="shared",
        container="webm",
        quality="720p",
        root=root,
    )
    library_asset = next(
        item for item in listed_assets if item.video == library_video.name
    )
    runtime_asset = next(
        item for item in listed_assets if item.video == runtime_video.name
    )
    selected_choices = video_sequence.native_video_source_choices(
        {**values, "scroll_video_source": library_asset.source_spec},
        family="shared",
        root=root,
    )
    assert selected_choices == ((library_asset.source_spec, library_asset.label),)

    legacy_choices = video_sequence.native_video_source_choices(
        {**values, "scroll_video_source": runtime_asset.source_spec},
        family="shared",
        root=root,
    )
    assert legacy_choices == ((runtime_asset.source_spec, library_asset.label),)


def test_replace_video_variants_builds_both_qualities(
    component_tmp: Path, monkeypatch
) -> None:
    tmp_path = component_tmp
    root = tmp_path / "theme"
    (root / "assets").mkdir(parents=True)
    source = tmp_path / "full-hd.webm"
    source.write_bytes(b"video")
    widths: list[int] = []

    def fake_export(
        _source: Path,
        output_pattern: Path,
        *,
        fps: int,
        width: int,
        height: int,
        composite_black: bool,
    ) -> None:
        widths.append(width)
        assert fps == 60
        assert height == (720 if width == 1280 else 1080)
        assert composite_black is False
        for index in range(2):
            name = output_pattern.name.replace("%03d", f"{index:03d}")
            _write_webp(output_pattern.parent / name, size=(width, height))

    monkeypatch.setattr(video_sequence, "_run_ffmpeg_export", fake_export)
    result = video_sequence.replace_video_variants(
        source,
        root=root,
        backup_dir=tmp_path / "backups",
    )

    assert widths == [1280, 1920]
    assert tuple(item.quality for item in result.variants) == ("720p", "1080p")
    assert result.variants[0].status.width == 1280
    assert result.variants[1].status.width == 1920
    assert result.variants[1].manifest_path.name == (
        "giclee-philosophy-1080-manifest.json"
    )
    assert json.loads(
        result.variants[1].manifest_path.read_text(encoding="utf-8")
    )["extension"] == ".webp"


def test_replace_native_video_builds_selected_quality(
    component_tmp: Path, monkeypatch
) -> None:
    root = component_tmp / "theme"
    (root / "assets").mkdir(parents=True)
    source = component_tmp / "film.webm"
    source.write_bytes(b"video")

    monkeypatch.setattr(
        video_sequence,
        "_run_ffmpeg_native_video",
        lambda _source, destination, **_kwargs: destination.write_bytes(b"mp4"),
    )
    monkeypatch.setattr(
        video_sequence,
        "_run_ffmpeg_poster",
        lambda _source, destination, **_kwargs: _write_webp(
            destination, size=(1280, 720)
        ),
    )
    monkeypatch.setattr(video_sequence, "_probe_frame_count", lambda _path: 210)

    result = video_sequence.replace_native_video(
        source,
        quality="720p",
        root=root,
        backup_dir=component_tmp / "backups",
    )

    assert result.status.frame_count == 210
    assert result.status.width == 1280
    assert result.video_path.name == "giclee-philosophy-scroll-720.mp4"
    assert result.poster_path.name == "giclee-philosophy-video-720-poster.webp"
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["mode"] == "video"
    assert manifest["quality"] == "720p"
    assert manifest["container"] == "mp4"
    assert manifest["mimeType"] == "video/mp4"
    assert manifest["passthrough"] is False
    assert manifest["codec"] == "h264"
    assert manifest["hasAlpha"] is False
    assert manifest["alphaMode"] == "none"
    assert manifest["sourceHasAlpha"] is True
    assert manifest["alphaLostDuringConversion"] is True
    assert manifest["backgroundMode"] == "color"
    assert manifest["keyframeInterval"] == 1
    assert manifest["intraOnly"] is True


def test_ready_webm_is_copied_without_conversion_and_preserves_alpha(
    component_tmp: Path, monkeypatch
) -> None:
    root = component_tmp / "theme"
    (root / "assets").mkdir(parents=True)
    source = component_tmp / "gotowy-720.webm"
    source.write_bytes(b"ready-webm")
    metadata = video_sequence.VideoMetadata(
        width=1280,
        height=720,
        fps=60.0,
        frame_count=210,
        duration=3.5,
        codec="vp9",
        pixel_format="yuva420p",
        has_alpha=True,
        alpha_mode="straight",
    )
    monkeypatch.setattr(
        video_sequence,
        "_probe_video_metadata",
        lambda _path: metadata,
    )
    monkeypatch.setattr(
        video_sequence,
        "_probe_keyframe_profile",
        lambda _path: (1, True),
    )
    monkeypatch.setattr(
        video_sequence,
        "_run_ffmpeg_native_video",
        lambda *_args, **_kwargs: pytest.fail(
            "Gotowy WebM nie może zostać ponownie zakodowany."
        ),
    )
    monkeypatch.setattr(
        video_sequence,
        "_run_ffmpeg_poster",
        lambda _source, destination, **_kwargs: _write_webp(
            destination, size=(1280, 720)
        ),
    )

    result = video_sequence.replace_native_video(
        source,
        quality="720p",
        container="webm",
        root=root,
        backup_dir=component_tmp / "backups",
    )

    assert result.container == "webm"
    assert result.video_path.name == "giclee-philosophy-scroll-720.webm"
    assert result.video_path.read_bytes() == b"ready-webm"
    assert result.source_path == result.video_path
    assert result.status.has_alpha is True
    assert result.status.intra_only is True
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["container"] == "webm"
    assert manifest["mimeType"] == "video/webm"
    assert manifest["passthrough"] is True
    assert manifest["codec"] == "vp9"
    assert manifest["hasAlpha"] is True
    assert manifest["alphaLostDuringConversion"] is False
    assert manifest["backgroundMode"] == "transparent"
    assert manifest["fullSourceFrameUse"] is True
    assert manifest["keyframeInterval"] == 1
    assert manifest["intraOnly"] is True
    assert list(
        (root / "assets").glob(
            "giclee-scroll-library-philosophy-720p-webm-*.webm"
        )
    )


def test_motion_catalog_is_complete_and_registry_uses_all_values() -> None:
    catalog = load_motion_catalog()
    assert tuple(catalog["presets"]) == (
        "direct",
        "product",
        "smooth",
        "cinematic",
        "soft-inertia",
        "dynamic",
        "heavy-camera",
        "luxury",
    )
    assert catalog["recommended"] == {"video": "luxury", "frames": "luxury"}
    required = set(FIELD_TO_SETTING)
    for preset in catalog["presets"].values():
        assert required <= set(preset)
        assert 0.25 <= float(preset["speed"]) <= 3
        assert 0 <= int(preset["smoothingMs"]) <= 1000
        assert 0 <= int(preset["lagMs"]) <= 500
        assert 0 <= int(preset["inertia"]) <= 100
        assert 0 <= int(preset["damping"]) <= 100
        assert 0 <= int(preset["materialStart"]) < int(preset["materialEnd"]) <= 100

    registered = dict(preset_values())
    for preset_id, preset in catalog["presets"].items():
        assignments = dict(registered[preset_id])
        for source_key, setting_id in FIELD_TO_SETTING.items():
            assert assignments[setting_id] == preset[source_key]


def test_current_motion_settings_validate_and_invalid_bezier_is_rejected() -> None:
    root = Path(__file__).resolve().parents[3]
    raw = (root / "templates" / "page.filozofia-marki.json").read_text(
        encoding="utf-8"
    )
    template = json.loads(raw.split("*/", 1)[1])
    settings = template["sections"]["media_with_content_D7REjd"]["blocks"][
        "media"
    ]["settings"]
    assert validate_motion_settings(settings) == []

    invalid = dict(settings)
    invalid["scroll_motion_bezier"] = "1.5,foo,0,1"
    invalid["scroll_motion_material_start"] = 90
    invalid["scroll_motion_material_end"] = 10
    errors = validate_motion_settings(invalid)
    assert any("Bézier" in error for error in errors)
    assert any("koniec musi być większy" in error for error in errors)


def test_runtime_has_one_central_raf_and_no_delayed_scroll_queue() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime = (root / "assets" / "giclee-scroll-scrub-video.js").read_text(
        encoding="utf-8"
    )
    assert runtime.count("requestAnimationFrame(") == 1
    assert "class CentralScheduler" in runtime
    assert "class MotionState" in runtime
    assert "class ScrollFrameCanvas" in runtime
    assert "class ScrollNativeVideo" in runtime
    assert "setTimeout(" not in runtime
    assert "setInterval(" not in runtime
    assert runtime.count("'scroll',") == 1
    assert "requestVideoFrameCallback" in runtime
    assert "premultiplyAlpha: 'premultiply'" in runtime
    assert "globalCompositeOperation = 'copy'" in runtime
    assert "uniqueFramesLastSecond" in runtime
    assert "const monotonicProgress" in runtime
    assert "interpolation !== 'spring'" in runtime
    assert "tailPacingSteps" in runtime
    assert "const sourceFrameMs" in runtime
    assert "this.container === 'webm'" in runtime
    assert "manifest.hasAlpha !== true" in runtime


def test_quote_portal_uses_central_scrub_scheduler_for_webm() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime = (root / "assets" / "giclee-scroll-scrub-video.js").read_text(
        encoding="utf-8"
    )
    quote_portal = (
        root / "assets" / "giclee-filozofia-quote-pin.js"
    ).read_text(encoding="utf-8")

    assert "setExternalProgress" in runtime
    assert "setProgress," in runtime
    assert "this.interFrameWebm" in runtime
    assert "startSequentialPlayback" in runtime
    assert "MAX_SEQUENTIAL_WEBM_CATCHUP_SECONDS = 0.32" in runtime
    assert "ALPHA_WEBM_MAX_SEQUENTIAL_CATCHUP_SECONDS = 1.25" in runtime
    assert "ALPHA_WEBM_MIN_PLAYBACK_RATE = 0.25" in runtime
    assert "ALPHA_WEBM_MAX_PLAYBACK_RATE = 1" in runtime
    assert "maxSequentialCatchupSeconds()" in runtime
    assert "presentedTime()" in runtime
    assert "const alphaSource = this.sourceMetadata.hasAlpha === true" in runtime
    assert "const catchupWindow = 0.14" in runtime
    assert "requestVideoFrameCallback" in runtime
    assert "deferredForwardSeeks" in runtime
    assert "presentationRecoverySeeks" in runtime
    assert "maxTargetDriftMs" in runtime
    assert "prewarmAlphaWebm" in runtime
    assert "buffered-alpha-blob" in runtime
    assert "buffered-preview-blob" in runtime
    assert "localPreviewHost" in runtime
    assert "this.sourceDelivery = 'native-url'" in runtime
    assert "this.lastLargeForwardSeekTarget" in runtime
    reverse_branch = runtime.index("if (targetMovedBackward)")
    forward_branch = runtime.index(
        "if (delta > 0 && !this.video.seeking)",
        reverse_branch,
    )
    assert reverse_branch < forward_branch
    assert "typeof api.setProgress === 'function'" in quote_portal
    assert "api.setProgress(wrotaRoot, pendingFilmProgress)" in quote_portal
    assert "video.seeking) return" in quote_portal


def test_film_scroll_has_one_ai_contract_covering_gicleeapp() -> None:
    root = Path(__file__).resolve().parents[3]
    contract = (root / "docs" / "Film-scroll.md").read_text(encoding="utf-8")
    legacy_guide = (
        root / "docs" / "Film-scroll-AI-Integration-Guide.md"
    ).read_text(encoding="utf-8")
    agent_router = (root / "AGENTS.md").read_text(encoding="utf-8")

    for required in (
        "Kontrakt polecenia „wstaw moduł Film-scroll”",
        "Definition of done",
        "TemplateZone",
        "ASSET_FAMILIES",
        "after_template_save",
        "scroll_story_wrota",
        "Dodaj „Scroll Film”…",
        "Charakter odtwarzania",
        "WebM pozostaje WebM",
    ):
        assert required in contract
    assert "jedynym źródłem prawdy" in legacy_guide.lower()
    assert len(legacy_guide) < 1_500
    assert "docs/Film-scroll.md" in agent_router
    assert "nową widoczną sekcję" in agent_router


def test_philosophy_motion_is_collapsible_inside_scroll_story() -> None:
    story = next(zone for zone in PAGE_ZONES if zone.zone_id == "scroll_story")

    assert not any(zone.zone_id == "scroll_motion" for zone in PAGE_ZONES)
    assert not any(zone.zone_id == "scroll_alpha" for zone in PAGE_ZONES)
    assert story.label == "Animacja przewijana"
    assert story.preset_field_id == "scroll_motion_preset"
    assert story.recommended_preset_value == "luxury"

    motion_fields = tuple(
        field
        for field in story.fields
        if field.field_id.startswith("scroll_motion_")
    )
    assert motion_fields
    assert all(field.group_id == "film_scroll_motion" for field in motion_fields)
    assert all(
        field.group_label == "Charakter odtwarzania"
        for field in motion_fields
    )
    assert all(field.group_collapsed is True for field in motion_fields)

    background_fields = tuple(
        field
        for field in story.fields
        if field.field_id.startswith("scroll_background_")
        or field.field_id in {
            "scroll_preserve_alpha",
            "scroll_alpha_diagnostics",
            "scroll_force_transparent",
        }
    )
    assert background_fields
    assert all(
        field.group_id == "film_scroll_background"
        for field in background_fields
    )
    assert all(
        field.group_label == "Ustawienia tła"
        for field in background_fields
    )
    assert all(field.group_collapsed is True for field in background_fields)


def test_wrota_motion_is_collapsible_inside_portal_story() -> None:
    story = next(
        zone for zone in PAGE_ZONES if zone.zone_id == "scroll_story_wrota"
    )

    assert not any(zone.zone_id == "scroll_motion_wrota" for zone in PAGE_ZONES)
    assert story.label == "Portal Wrota — animacja"
    assert story.preset_field_id == "scroll_motion_preset"
    assert story.recommended_preset_value == "luxury"

    motion_fields = tuple(
        field
        for field in story.fields
        if field.field_id.startswith("scroll_motion_")
    )
    assert motion_fields
    assert all(
        field.group_id == "film_scroll_motion_wrota"
        for field in motion_fields
    )
    assert all(
        field.group_label == "Charakter odtwarzania"
        for field in motion_fields
    )
    assert all(field.group_collapsed is True for field in motion_fields)
    assert all(
        field.path
        and len(field.path) > 1
        and field.path[1] == "media_with_content_Wrota"
        for field in motion_fields
    )


def test_webm_container_is_wired_through_liquid_schema_and_deploy() -> None:
    root = Path(__file__).resolve().parents[3]
    snippet = (root / "snippets" / "media.liquid").read_text(encoding="utf-8")
    schema = (
        root / "blocks" / "_media-without-appearance.liquid"
    ).read_text(encoding="utf-8")
    gui = (
        root / "cursor-api" / "Komponenty" / "filozofiamarki" / "gui.py"
    ).read_text(encoding="utf-8")
    sequence = (
        root / "cursor-api" / "Komponenty" / "filozofiamarki" / "video_sequence.py"
    ).read_text(encoding="utf-8")

    assert "scroll_video_container" in snippet
    assert "giclee-philosophy-scroll-1080.webm" in snippet
    assert 'type="{{ scroll_native_mime }}"' in snippet
    assert '"id": "scroll_video_container"' in schema
    assert "Gotowy WebM — bez konwersji" in gui
    assert "active_scroll_video_deploy_relpaths" in gui
    assert "sync_scroll_video_shopifyignore" in sequence


def test_page_scroll_modes_include_responsive_smooth_and_local_lenis() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime = (root / "assets" / "giclee-page-smooth-scroll.js").read_text(
        encoding="utf-8"
    )
    schema = (
        root / "sections" / "giclee-page-scroll-config.liquid"
    ).read_text(encoding="utf-8")
    registry = (
        root / "cursor-api" / "Komponenty" / "filozofiamarki" / "registry.py"
    ).read_text(encoding="utf-8")
    gui_shell = (
        root
        / "cursor-api"
        / "Komponenty"
        / "_shared"
        / "theme_page_editor"
        / "gui_shell.py"
    ).read_text(encoding="utf-8")

    assert (root / "assets" / "lenis.min.js").is_file()
    assert (root / "assets" / "lenis.css").is_file()
    assert "{{ 'lenis.css' | asset_url | stylesheet_tag }}" in schema
    assert '"{{ \'lenis.min.js\' | asset_url }}"' in schema
    assert schema.index("lenis.min.js") < schema.index(
        "giclee-page-smooth-scroll.js"
    )
    assert "GICLEE_PAGE_SCROLL_CONFIG" in schema
    assert '"value": "lenis"' in schema
    assert '"id": "scroll_smoothness"' in schema
    assert '("lenis", "Lenis")' in registry
    assert '"scroll_smoothness"' in registry
    assert '"scroll_lenis_preset"' in registry
    assert 'group_id="lenis_settings"' in registry
    assert 'group_label="Ustawienia Lenis"' in registry
    assert "FieldGroupVariantLibrary(" in registry
    assert 'storage_filename="lenis-scroll-variants.json"' in registry
    assert 'state["rendered_field_groups"] = set()' in gui_shell
    assert "open_field_groups" in gui_shell
    assert 'text="Nowy wariant…"' in gui_shell
    assert 'text="Zapisz wybrany"' in gui_shell
    assert 'text="Zmień nazwę…"' in gui_shell
    assert "new window.Lenis" in runtime
    assert "function lenisSettings()" in runtime
    assert "wheelMultiplier: settings.wheelMultiplier" in runtime
    assert "lerp: settings.lerp" in runtime
    assert "overscroll: settings.overscroll" in runtime
    assert "stopInertiaOnNavigate: settings.stopInertiaOnNavigate" in runtime
    assert "FOLLOW_TAU_MS = clamp(190 - SCROLL_SMOOTHNESS * 1.55" in runtime
    assert "MAX_TARGET_LEAD_PX = clamp(" in runtime


def test_replace_parallax_layer_copies_webp(component_tmp: Path) -> None:
    root = component_tmp / "theme"
    (root / "assets").mkdir(parents=True)
    source = component_tmp / "bottom.webp"
    _write_webp(source, size=(128, 72))

    dest = video_sequence.replace_parallax_layer(
        source, layer="bottom", root=root
    )
    status = video_sequence.read_parallax_layer_status("bottom", root=root)

    assert dest.name == "giclee-fm-parallax-bottom.webp"
    assert dest.is_file()
    assert status.exists is True
    assert status.width == 128
    assert status.height == 72
    assert "assets/giclee-fm-parallax-bottom.webp" in (
        video_sequence.parallax_deploy_relpaths(root=root)
    )
    gui_src = Path(__file__).with_name("gui.py").read_text(encoding="utf-8")
    assert "Dodaj tło Middle…" in gui_src
    assert "_render_wrota_parallax_zone" in gui_src
    assert "_build_parallax_bg_panel" not in gui_src
    assert any(z.zone_id == "wrota_parallax" for z in PAGE_ZONES)
    assert "assets/giclee-fm-parallax-bottom.webp" in _config().extra_deploy_relpaths
    assert "wrota_parallax" in _config().zone_content_builders


def test_replace_parallax_middle_webm(component_tmp: Path) -> None:
    root = component_tmp / "theme"
    assets = root / "assets"
    assets.mkdir(parents=True)
    webm = component_tmp / "middle.webm"
    webm.write_bytes(b"fake-webm")

    dest = video_sequence.replace_parallax_layer(webm, layer="middle", root=root)
    status = video_sequence.read_parallax_layer_status("middle", root=root)
    cfg = video_sequence.read_parallax_config(root=root)

    assert dest.name == "giclee-fm-parallax-middle.webm"
    assert dest.is_file()
    assert status.kind == "webm"
    assert cfg["middleKind"] == "webm"
    assert PARALLAX_MIDDLE_WEBM_REL in video_sequence.parallax_deploy_relpaths(
        root=root
    )


def test_wrota_before_after_keeps_full_images_and_has_drag_slider() -> None:
    root = Path(__file__).resolve().parents[3]
    media = (root / "snippets" / "media.liquid").read_text(encoding="utf-8")
    css = (
        root / "assets" / "giclee-fm-wrota-parallax.css"
    ).read_text(encoding="utf-8")
    runtime = (
        root / "assets" / "giclee-filozofia-quote-pin.js"
    ).read_text(encoding="utf-8")

    image_rule = css[
        css.index(".giclee-fm-tresc3d__image")
        : css.index(".giclee-fm-tresc3d__label")
    ]

    assert media.count("data-fm-tresc3d-slider") == 2
    assert 'type="range"' in media
    assert 'aria-label="Porównaj obraz przed i po"' in media
    assert "object-fit: contain" in image_rule
    assert "object-fit: cover" not in image_rule
    assert (
        "max-width: min(100%, 68rem, var(--compare-viewport-width, 68rem))"
        in css
    )
    assert "aspect-ratio: var(--compare-aspect" in css
    assert "background: transparent" in css
    assert ".giclee-fm-tresc3d__handle-line" in css
    assert ".giclee-fm-tresc3d__handle-grip" in css
    assert "function initTresc3dComparisons()" in runtime
    assert "source.naturalWidth + ' / ' + source.naturalHeight" in runtime
    assert "'--compare-viewport-width'" in runtime
    assert "new ResizeObserver(syncViewportSize)" in runtime
    assert "media.style.setProperty('--compare'" in runtime
    assert "initTresc3dComparisons();" in runtime
