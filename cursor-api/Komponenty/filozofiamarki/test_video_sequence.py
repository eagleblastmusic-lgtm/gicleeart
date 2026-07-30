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

from .gui import _before_after_texts_from_json, _config
from .registry import PAGE_ZONES
from .motion_config import (
    FIELD_TO_SETTING,
    load_motion_catalog,
    preset_values,
    validate_motion_settings,
)
from . import video_sequence
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
    assert "this.presentationGateEnabled" in runtime
    assert "this.awaitingSeekPresentation" in runtime
    assert "typeof this.video.requestVideoFrameCallback === 'function'" in runtime
    assert "Math.abs(frame - requestedFrame) <= 1" in runtime
    assert "dataset.awaitingPresentation" in runtime
    reverse_branch = runtime.index("if (targetMovedBackward)")
    forward_branch = runtime.index(
        "if (delta > 0 && !this.video.seeking)",
        reverse_branch,
    )
    assert reverse_branch < forward_branch
    assert "typeof api.setProgress === 'function'" in quote_portal
    assert "api.setProgress(wrotaRoot, pendingFilmProgress)" in quote_portal
    assert "video.seeking) return" in quote_portal


def test_parallax_text_crossfades_holds_and_exits_after_wrota() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime = (
        root / "assets" / "giclee-filozofia-quote-pin.js"
    ).read_text(encoding="utf-8")
    parallax = (
        root / "assets" / "giclee-fm-wrota-parallax.js"
    ).read_text(encoding="utf-8")
    styles = (
        root / "snippets" / "giclee-theme-inline-overrides.liquid"
    ).read_text(encoding="utf-8")

    assert "function cinematicTextProgress(afterFilm)" in runtime
    assert "applyParallaxText(phases.afterFilm || 0, forceSnap)" in runtime
    assert "var points = [0, 0.32, 0.68, 1, 1.42, 1.78, 2.14]" in runtime
    assert "setTextProgress: function (value)" in parallax
    assert "root.style.opacity = reveal.toFixed(4)" in parallax
    assert "W tym procesie traktuję je jak materię kulturową" in parallax
    assert "quote-window quote-window--secondary" in parallax
    assert "--fm-quote-gradient-top-depth: 170px" in styles
    assert "--fm-quote-gradient-top: 0px" in styles
    assert "top: 0;" in styles
    assert "center top," in styles
    assert "100% 170px," in styles
    assert "'--fm-quote-menu-edge'" in runtime
    assert "function syncQuoteGradientDock()" in runtime
    assert "visibleMenuEdge - stickyTop" in runtime
    assert "data-fm-gradient-menu-edge" in runtime
    assert "data-fm-gradient-top" in runtime
    assert "data-fm-gradient-edge" in runtime
    assert "data-fm-gradient-docked" in runtime
    assert "quote-aurora" in parallax
    assert "SECOND QUOTE ENTRANCE" in parallax
    assert "SECOND QUOTE HOLD / PIN" in parallax
    assert "SECOND QUOTE EXIT" in parallax
    assert "function syncBreathing(progress)" in parallax
    assert "scale: 1.025" in parallax
    assert "duration: 3.2" in parallax
    assert "repeat: -1" in parallax
    assert "yoyo: true" in parallax
    assert "data-fm-cinematic-breathing" in parallax
    assert "progress >= hold[0]" in parallax
    assert "progress < hold[1]" in parallax
    assert "--fm-wrota-parallax-duration: 3.6" in styles


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
    assert "Dodaj tło Bottom…" in gui_src
    assert "Dodaj tło Middle…" not in gui_src
    assert "_render_wrota_parallax_zone" in gui_src
    assert "Paralaksa tła (mysz, desktop)" in gui_src
    assert "fm_bg_parallax_enabled" in gui_src
    assert "_build_parallax_bg_panel" not in gui_src
    assert any(z.zone_id == "wrota_parallax" for z in PAGE_ZONES)
    parallax_zone = next(z for z in PAGE_ZONES if z.zone_id == "wrota_parallax")
    assert any(f.field_id == "fm_bg_parallax_enabled" for f in parallax_zone.fields)
    assert "assets/giclee-fm-parallax-bottom.webp" in _config().extra_deploy_relpaths
    assert "wrota_parallax" in _config().zone_content_builders


def test_quote_screen_background_asset_and_zone(component_tmp: Path) -> None:
    root = component_tmp / "theme"
    (root / "assets").mkdir(parents=True)
    source = component_tmp / "quote.webp"
    _write_webp(source, size=(640, 360))

    dest = video_sequence.replace_quote_bg(source, root=root)
    status = video_sequence.read_quote_bg_status(root=root)

    assert dest.name == "giclee-fm-quote-bg.webp"
    assert dest.is_file()
    assert status.exists is True
    assert status.width == 640
    assert status.height == 360
    assert "assets/giclee-fm-quote-bg.webp" in (
        video_sequence.quote_bg_deploy_relpaths(root=root)
    )

    video_sequence.clear_quote_bg(root=root)
    cleared = video_sequence.read_quote_bg_status(root=root)
    assert cleared.exists is False
    assert video_sequence.quote_bg_deploy_relpaths(root=root) == ()

    gui_src = Path(__file__).with_name("gui.py").read_text(encoding="utf-8")
    theme_root = Path(__file__).resolve().parents[3]
    quote_pin = (theme_root / "assets" / "giclee-filozofia-quote-pin.js").read_text(
        encoding="utf-8"
    )
    scripts = (theme_root / "snippets" / "scripts.liquid").read_text(encoding="utf-8")
    overrides = (
        theme_root / "snippets" / "giclee-theme-inline-overrides.liquid"
    ).read_text(encoding="utf-8")

    assert any(z.zone_id == "quote_screen" for z in PAGE_ZONES)
    assert "quote_screen" in _config().zone_content_builders
    assert "assets/giclee-fm-quote-bg.webp" in _config().extra_deploy_globs
    assert "Ekran cytatu" in gui_src
    assert "Dodaj tło…" in gui_src
    assert "_render_quote_screen_zone" in gui_src
    assert "Tło tekstu:" in gui_src
    assert "Górny separator — nad kreską:" in gui_src
    assert "Górny separator — pod kreską:" in gui_src
    assert "Dolny separator — nad kreską:" in gui_src
    assert "Dolny separator — pod kreską:" in gui_src
    assert 'id="giclee-fm-quote-bg-assets"' in scripts
    assert "giclee-fm-quote-bg.webp" in scripts
    assert "applyQuoteBackground" in quote_pin
    assert "applyQuoteBandOpacities" in quote_pin
    assert "has-fm-quote-bg" in quote_pin
    assert "has-fm-quote-bg" in overrides
    assert "--fm-quote-text-bg-opacity" in overrides
    assert "--fm-quote-divider-top-above-opacity" in overrides
    assert "--fm-quote-divider-top-below-opacity" in overrides
    assert "--fm-quote-divider-bottom-above-opacity" in overrides
    assert "--fm-quote-divider-bottom-below-opacity" in overrides
    zone = next(z for z in PAGE_ZONES if z.zone_id == "quote_screen")
    field_ids = {f.field_id for f in zone.fields}
    assert "fm_quote_text_bg_opacity" in field_ids
    assert "fm_quote_divider_top_above_opacity" in field_ids
    assert "fm_quote_divider_top_below_opacity" in field_ids
    assert "fm_quote_divider_bottom_above_opacity" in field_ids
    assert "fm_quote_divider_bottom_below_opacity" in field_ids
    assert "fm_quote_bg_parallax_enabled" in field_ids
    section_liquid = (theme_root / "sections" / "section.liquid").read_text(
        encoding="utf-8"
    )
    assert 'id="giclee-fm-quote-screen-settings"' in section_liquid
    assert "fm_quote_text_bg_opacity" in section_liquid
    assert "fm_quote_divider_top_above_opacity" in section_liquid
    assert "dividerTopAboveOpacity" in section_liquid


def test_wrota_parallax_uses_only_bottom_and_removes_tresc_3d() -> None:
    root = Path(__file__).resolve().parents[3]
    media = (root / "snippets" / "media.liquid").read_text(encoding="utf-8")
    css = (
        root / "assets" / "giclee-fm-wrota-parallax.css"
    ).read_text(encoding="utf-8")
    runtime = (
        root / "assets" / "giclee-filozofia-quote-pin.js"
    ).read_text(encoding="utf-8")
    parallax = (
        root / "assets" / "giclee-fm-wrota-parallax.js"
    ).read_text(encoding="utf-8")
    scripts = (root / "snippets" / "scripts.liquid").read_text(encoding="utf-8")

    assert not any(zone.zone_id == "tresc_3d" for zone in PAGE_ZONES)
    assert "tresc3d" not in media.lower()
    assert "tresc3d" not in css.lower()
    assert "tresc3d" not in runtime.lower()
    assert "assets.middle" not in parallax
    assert "giclee-fm-parallax-middle" not in parallax
    assert "giclee-fm-parallax-middle" not in scripts
    assert '"bottom"' in scripts
    deploy = video_sequence.parallax_deploy_relpaths(root=root)
    assert "assets/giclee-fm-parallax-bottom.webp" in deploy
    assert not any("middle" in path or "config" in path for path in deploy)


def test_before_after_gallery_assets_and_slot_validation(component_tmp: Path) -> None:
    root = component_tmp / "theme"
    (root / "assets").mkdir(parents=True)
    source = component_tmp / "przed.png"
    Image.new("RGB", (2401, 654), (30, 50, 80)).save(source, "PNG")

    dest = video_sequence.replace_before_after_image(
        source,
        index=2,
        side="before",
        root=root,
    )
    status = video_sequence.read_before_after_status(
        2,
        "before",
        root=root,
    )

    assert dest.name == "giclee-fm-before-after-02-before.webp"
    assert status.exists is True
    assert status.width == 2401
    assert status.height == 654
    assert status.rel_path in video_sequence.before_after_deploy_relpaths(root=root)
    display_rel = video_sequence.before_after_display_asset_relpath(2, "before")
    display_path = root / display_rel
    assert display_path.is_file()
    assert display_rel in video_sequence.before_after_deploy_relpaths(root=root)
    with Image.open(display_path) as display:
        assert display.width == video_sequence.BEFORE_AFTER_DISPLAY_MAX_WIDTH
        assert display.width * display.height <= (
            video_sequence.BEFORE_AFTER_DISPLAY_MAX_PIXELS
        )
    with pytest.raises(ValueError):
        video_sequence.before_after_asset_relpath(0, "before")
    with pytest.raises(ValueError):
        video_sequence.before_after_asset_relpath(1, "lewa")


def test_before_after_gallery_is_variant_field_and_scroll_runtime() -> None:
    root = Path(__file__).resolve().parents[3]
    zone = next(z for z in PAGE_ZONES if z.zone_id == "before_after_gallery")
    field = next(f for f in zone.fields if f.field_id == "before_after_count")
    fields = {item.field_id: item for item in zone.fields}
    gallery = (root / "assets" / "giclee-fm-before-after.js").read_text(
        encoding="utf-8"
    )
    gallery_css = (root / "assets" / "giclee-fm-before-after.css").read_text(
        encoding="utf-8"
    )
    quote_pin = (root / "assets" / "giclee-filozofia-quote-pin.js").read_text(
        encoding="utf-8"
    )
    parallax = (root / "assets" / "giclee-fm-wrota-parallax.js").read_text(
        encoding="utf-8"
    )
    media = (root / "snippets" / "media.liquid").read_text(encoding="utf-8")
    scripts = (root / "snippets" / "scripts.liquid").read_text(encoding="utf-8")
    gui = Path(__file__).with_name("gui.py").read_text(encoding="utf-8")
    page_scroll = (root / "assets" / "giclee-page-smooth-scroll.js").read_text(
        encoding="utf-8"
    )

    assert zone.label == "Przed i po"
    assert zone.section_key == "media_with_content_Wrota"
    assert zone.settings_only is True
    assert field.path[-1] == "before_after_count"
    assert field.max_value == 12
    assert fields["before_after_motion_blur"].path[-1] == "before_after_motion_blur"
    assert fields["before_after_film_grain"].path[-1] == "before_after_film_grain"
    assert fields["before_after_bg_transparent"].path[-1] == "before_after_bg_transparent"
    assert fields["before_after_preserve_prev_bg"].path[-1] == "before_after_preserve_prev_bg"
    assert fields["before_after_bg_radial_opacity"].path[-1] == "before_after_bg_radial_opacity"
    assert fields["before_after_bg_linear_opacity"].path[-1] == "before_after_bg_linear_opacity"
    assert fields["before_after_texts_json"].path[-1] == "before_after_texts_json"
    assert "before_after_gallery" in _config().zone_content_builders
    assert "assets/giclee-fm-before-after.js" in _config().extra_deploy_relpaths
    assert "assets/giclee-fm-before-after.css" in _config().extra_deploy_relpaths
    assert "assets/giclee-fm-before-after-*.webp" in _config().extra_deploy_globs
    assert 'id="giclee-fm-before-after-data"' in media
    assert "giclee-fm-before-after-" in media
    assert '"motionBlur"' in media
    assert '"filmGrain"' in media
    assert '"bgTransparent"' in media
    assert '"bgRadialOpacity"' in media
    assert '"bgLinearOpacity"' in media
    assert '"preservePrevBg"' in media
    assert '"textsJson"' in media
    assert '"beforeDisplay"' in media
    assert '"afterDisplay"' in media
    assert "-before-display.webp" in media
    assert "-after-display.webp" in media
    assert "giclee-fm-before-after.js" in scripts
    assert "giclee-fm-before-after.css" in scripts
    assert "setGalleryProgress" in parallax
    assert "getGalleryDurationVh" in parallax
    assert "--fm-wrota-gallery-duration" in quote_pin
    assert "applyBeforeAfterGallery" in quote_pin
    assert "phases.gallery" in quote_pin
    assert "setProgress: setProgress" in gallery
    assert "var local = clamp(" in gallery
    assert "Math.floor(local * slides.length)" in gallery
    assert "setActive(target, reducedMotion, false)" in gallery
    assert "durationVh: 0.6 + slides.length * 0.8 + 0.6 + 0.6" in gallery
    assert "var ENTER_END = 0.6 / durationVh;" in gallery
    assert "var EXIT_START = (0.6 + slides.length * 0.8) / durationVh;" in gallery
    assert "onGalleryWheel" not in gallery
    assert "wheelLocked" not in gallery
    assert "event.stopImmediatePropagation()" not in gallery
    assert "data-gallery-active-index" in gallery
    assert 'loading="eager"' in gallery
    assert 'loading="lazy"' in gallery
    assert 'decoding="async"' in gallery
    assert "function ensureCardsAround(index)" in gallery
    assert "image.src = source" in gallery
    assert "slide.beforeDisplay || slide.before" in gallery
    assert "slide.afterDisplay || slide.after" in gallery
    assert "Math.abs(progress - lastProgress) < 0.0005" in gallery
    assert "is-nearby" in gallery
    assert "absolute > 1" in gallery
    assert "motionBlur ? 'blur(' + pose.blur + 'px)' : 'none'" in gallery
    assert "before_after_texts_json" in gui
    assert "Wspólne napisy galerii" in gui
    assert "Efekt smużenia podczas zmiany kart" in gui
    assert "Animowane filmowe ziarno" in gui
    assert "Przezroczystość tła" in gui
    assert "Zachowaj winietę i efekty tła z poprzedniego ekranu" in gui
    assert "Radialny blob:" in gui
    assert "Liniowy gradient:" in gui
    assert "filmGrain: data.filmGrain !== false" in gallery
    assert "bgTransparent: data.bgTransparent !== false" in gallery
    assert "preservePrevBg: data.preservePrevBg !== false" in gallery
    assert "--fm-ba-radial-opacity" in gallery
    assert "--fm-ba-linear-opacity" in gallery_css
    assert "is-film-grain-off" in gallery
    assert "is-gallery-overlay" in parallax
    assert "preservePrevBg" in parallax
    assert "readParallaxEnabled" in parallax
    assert (
        "setListening(parallaxEnabled && reveal > 0.02 && !reducedMotion)"
        in parallax
    )
    assert "giclee-fm-wrota-parallax-config" in media
    assert "fm_bg_parallax_enabled" in media
    assert "Math.abs(nextProgress - pendingFilmProgress) < 0.0005" in quote_pin
    assert "if (seekFilm(filmShown)) wakeScrub();" in quote_pin
    assert "hold: function ()" not in page_scroll
    assert "release: function ()" not in page_scroll
    assert "pointerdown" in gallery
    assert "aria-valuenow" in gallery
    assert "object-fit: cover" in gallery_css
    assert ".comparison-card" in gallery_css
    assert "contain: layout paint style" in gallery_css
    assert ".comparison-card.is-nearby" in gallery_css
    assert "width: 300%" not in gallery_css
    assert "height: 300%" not in gallery_css
    assert ".split-handle" in gallery_css
    assert ".before-layer img {\n  filter: none;" in gallery_css
    assert "grayscale(0.85)" not in gallery_css


def test_before_after_gallery_text_defaults_and_overrides() -> None:
    defaults = _before_after_texts_from_json("")
    assert defaults["brand"] == "Before / After Archive"
    assert defaults["beforeLabel"] == "Before"
    assert len(defaults["slides"]) == video_sequence.BEFORE_AFTER_MAX_ITEMS
    assert defaults["slides"][0]["title"] == "Porównanie 1"

    custom = _before_after_texts_from_json(
        json.dumps(
            {
                "brand": "Archiwum konserwacji",
                "beforeLabel": "Przed",
                "slides": [
                    {
                        "title": "Portret",
                        "location": "Warszawa",
                        "type": "Renowacja",
                    }
                ],
            }
        )
    )
    assert custom["brand"] == "Archiwum konserwacji"
    assert custom["beforeLabel"] == "Przed"
    assert custom["slides"][0] == {
        "title": "Portret",
        "location": "Warszawa",
        "type": "Renowacja",
    }


def test_scroll_story_text_pin_controls() -> None:
    root = Path(__file__).resolve().parents[3]
    media = (root / "snippets" / "media.liquid").read_text(encoding="utf-8")
    scrub = (root / "assets" / "giclee-scroll-scrub-video.js").read_text(
        encoding="utf-8"
    )
    schema = (
        root / "blocks" / "_media-without-appearance.liquid"
    ).read_text(encoding="utf-8")
    registry = (Path(__file__).resolve().parent / "registry.py").read_text(
        encoding="utf-8"
    )

    assert '"id": "scroll_intro_pin_vh"' in schema
    assert '"id": "scroll_intro_fade_start_vh"' in schema
    assert '"id": "scroll_outro_appear_percent"' in schema
    assert '"id": "scroll_outro_pin_vh"' in schema
    assert "scroll_intro_pin_vh" in registry
    assert "scroll_intro_fade_start_vh" in registry
    assert "scroll_outro_appear_percent" in registry
    assert "scroll_outro_pin_vh" in registry
    assert 'data-intro-pin-vh="' in media
    assert 'data-intro-fade-start-vh="' in media
    assert 'data-outro-appear-percent="' in media
    assert 'data-outro-pin-vh="' in media
    assert "--scroll-intro-story" in media
    assert "--scroll-outro-story" in media
    assert "introPinVh" in scrub
    assert "introFadeStartVh" in scrub
    assert "vhToPx" in scrub
    assert "introFadeTriggerPx" in scrub
    assert "outroAppearPercent" in scrub
    assert "outroPinVh" in scrub
    assert "updateStory(" in scrub
    assert "DEFAULT_INTRO_PIN_VH" in scrub
    assert "INTRO_EXIT_PROGRESS" not in scrub
