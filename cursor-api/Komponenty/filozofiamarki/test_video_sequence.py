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


def test_component_deploy_includes_frame_sequence(
    component_tmp: Path, monkeypatch
) -> None:
    tmp_path = component_tmp
    root = tmp_path / "theme"
    assets = root / "assets"
    assets.mkdir(parents=True)
    _write_webp(assets / "giclee-philosophy-v3-frame-000.webp")
    _write_webp(assets / "giclee-philosophy-v3-frame-001.webp")
    _write_webp(assets / "giclee-philosophy-1080-frame-000.webp")
    monkeypatch.setattr(service_base, "theme_root", lambda: root)

    paths = service_base.component_deploy_relpaths(_config())

    assert "assets/giclee-philosophy-v3-frame-000.webp" in paths
    assert "assets/giclee-philosophy-v3-frame-001.webp" in paths
    assert "assets/giclee-philosophy-1080-frame-000.webp" in paths
    assert "assets/giclee-philosophy-v3-manifest.json" in paths
    assert "assets/giclee-philosophy-1080-manifest.json" in paths
    assert "snippets/media.liquid" in paths


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
    assert manifest["codec"] == "h264"
    assert manifest["hasAlpha"] is False
    assert manifest["alphaMode"] == "none"
    assert manifest["sourceHasAlpha"] is True
    assert manifest["alphaLostDuringConversion"] is True
    assert manifest["backgroundMode"] == "color"
    assert manifest["keyframeInterval"] == 1
    assert manifest["intraOnly"] is True


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
