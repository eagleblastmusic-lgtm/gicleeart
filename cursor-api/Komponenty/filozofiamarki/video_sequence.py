"""Bezpieczna podmiana filmu źródłowego i sekwencji WebP strony filozofii."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image

from giclee_app.app_paths import backup_path
from Komponenty._shared.subprocess_win import no_console_kwargs
from Komponenty.stronaglowna.service import resolve_ffmpeg_exe, theme_root


FRAME_DIGITS = 3
ALLOWED_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv"}
FRAME_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png"}
DEFAULT_FPS = 60
MAX_FRAMES = 999
BACKUP_LIMIT = 3
DEFAULT_FAMILY = "philosophy"


@dataclass(frozen=True)
class SequenceProfile:
    quality: str
    width: int
    height: int
    frame_prefix: str
    manifest_name: str
    extension: str
    composite_black: bool


@dataclass(frozen=True)
class AssetFamily:
    id: str
    source_prefix: str
    runtime_video: dict[str, str]
    runtime_poster: dict[str, str]
    video_manifest: dict[str, str]
    quality_profiles: dict[str, SequenceProfile]
    backup_prefix: str


ASSET_FAMILIES: dict[str, AssetFamily] = {
    "philosophy": AssetFamily(
        id="philosophy",
        source_prefix="giclee-philosophy-scroll-source",
        runtime_video={
            "720p": "giclee-philosophy-scroll-720.mp4",
            "1080p": "giclee-philosophy-scroll-1080.mp4",
        },
        runtime_poster={
            "720p": "giclee-philosophy-video-720-poster.webp",
            "1080p": "giclee-philosophy-video-1080-poster.webp",
        },
        video_manifest={
            "720p": "giclee-philosophy-video-720-manifest.json",
            "1080p": "giclee-philosophy-video-1080-manifest.json",
        },
        quality_profiles={
            "720p": SequenceProfile(
                quality="720p",
                width=1280,
                height=720,
                frame_prefix="giclee-philosophy-v3-frame-",
                manifest_name="giclee-philosophy-v3-manifest.json",
                extension=".webp",
                composite_black=False,
            ),
            "1080p": SequenceProfile(
                quality="1080p",
                width=1920,
                height=1080,
                frame_prefix="giclee-philosophy-1080-frame-",
                manifest_name="giclee-philosophy-1080-manifest.json",
                extension=".webp",
                composite_black=False,
            ),
        },
        backup_prefix="filozofia-video",
    ),
    "wrota": AssetFamily(
        id="wrota",
        source_prefix="giclee-philosophy-wrota-scroll-source",
        runtime_video={
            "720p": "giclee-philosophy-wrota-scroll-720.mp4",
            "1080p": "giclee-philosophy-wrota-scroll-1080.mp4",
        },
        runtime_poster={
            "720p": "giclee-philosophy-wrota-video-720-poster.webp",
            "1080p": "giclee-philosophy-wrota-video-1080-poster.webp",
        },
        video_manifest={
            "720p": "giclee-philosophy-wrota-video-720-manifest.json",
            "1080p": "giclee-philosophy-wrota-video-1080-manifest.json",
        },
        quality_profiles={
            "720p": SequenceProfile(
                quality="720p",
                width=1280,
                height=720,
                frame_prefix="giclee-philosophy-wrota-720-frame-",
                manifest_name="giclee-philosophy-wrota-720-manifest.json",
                extension=".webp",
                composite_black=False,
            ),
            "1080p": SequenceProfile(
                quality="1080p",
                width=1920,
                height=1080,
                frame_prefix="giclee-philosophy-wrota-1080-frame-",
                manifest_name="giclee-philosophy-wrota-1080-manifest.json",
                extension=".webp",
                composite_black=False,
            ),
        },
        backup_prefix="filozofia-wrota-video",
    ),
}

# Aliasy wsteczne — domyślna rodzina „philosophy”.
SOURCE_PREFIX = ASSET_FAMILIES["philosophy"].source_prefix
RUNTIME_VIDEO_NAMES = ASSET_FAMILIES["philosophy"].runtime_video
RUNTIME_POSTER_NAMES = ASSET_FAMILIES["philosophy"].runtime_poster
VIDEO_MANIFEST_NAMES = ASSET_FAMILIES["philosophy"].video_manifest
QUALITY_PROFILES = ASSET_FAMILIES["philosophy"].quality_profiles


def _family(family: str | None = None) -> AssetFamily:
    key = family or DEFAULT_FAMILY
    try:
        return ASSET_FAMILIES[key]
    except KeyError as exc:
        raise ValueError(
            f"Nieznana rodzina assetów: {key}. "
            f"Dozwolone: {', '.join(sorted(ASSET_FAMILIES))}."
        ) from exc


@dataclass(frozen=True)
class SequenceStatus:
    quality: str
    frame_count: int
    width: int
    height: int
    fps: int
    source: str
    total_bytes: int
    has_alpha: bool | None
    alpha_mode: str
    codec: str
    pixel_format: str
    source_fps: float | None
    source_frame_count: int | None
    source_has_alpha: bool | None
    full_source_frame_use: bool | None

    @property
    def duration_seconds(self) -> float:
        if not self.frame_count or not self.fps:
            return 0.0
        return self.frame_count / self.fps


@dataclass(frozen=True)
class ReplaceResult:
    quality: str
    status: SequenceStatus
    manifest_path: Path
    source_path: Path
    backup_path: Path | None


@dataclass(frozen=True)
class VariantsReplaceResult:
    variants: tuple[ReplaceResult, ...]
    source_path: Path
    backup_path: Path | None


@dataclass(frozen=True)
class NativeVideoStatus:
    quality: str
    frame_count: int
    width: int
    height: int
    fps: int
    total_bytes: int
    source: str
    has_alpha: bool
    alpha_mode: str
    codec: str
    pixel_format: str
    source_fps: float | None
    source_frame_count: int | None
    source_has_alpha: bool | None
    full_source_frame_use: bool | None
    background_mode: str

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / self.fps if self.frame_count and self.fps else 0.0


@dataclass(frozen=True)
class NativeVideoResult:
    quality: str
    status: NativeVideoStatus
    video_path: Path
    poster_path: Path
    manifest_path: Path
    source_path: Path
    backup_path: Path | None


@dataclass(frozen=True)
class VideoMetadata:
    width: int
    height: int
    fps: float | None
    frame_count: int | None
    duration: float | None
    codec: str
    pixel_format: str
    has_alpha: bool | None
    alpha_mode: str


def _assets_dir(root: Path | None = None) -> Path:
    return (root or theme_root()) / "assets"


def _profile(quality: str, family: str | None = None) -> SequenceProfile:
    profiles = _family(family).quality_profiles
    try:
        return profiles[quality]
    except KeyError as exc:
        raise ValueError("Jakość musi mieć wartość 720p albo 1080p.") from exc


def _frame_files(
    assets: Path,
    profile: SequenceProfile,
    *,
    all_extensions: bool = False,
) -> list[Path]:
    extension_pattern = (
        r"\.(?:webp|jpe?g|png)"
        if all_extensions
        else re.escape(profile.extension)
    )
    frame_re = re.compile(
        rf"^{re.escape(profile.frame_prefix)}"
        rf"(?P<index>\d{{{FRAME_DIGITS}}}){extension_pattern}$",
        re.IGNORECASE,
    )
    return sorted(
        path
        for path in assets.glob(f"{profile.frame_prefix}*")
        if path.is_file() and frame_re.fullmatch(path.name)
    )


def _alpha_state(path: Path) -> bool | None:
    try:
        with Image.open(path) as image:
            if "A" not in image.getbands():
                return False
            extrema = image.getchannel("A").getextrema()
            return bool(extrema and extrema[0] < 255)
    except (OSError, ValueError):
        return None


def _fraction(value: object) -> float | None:
    raw = str(value or "").strip()
    if not raw or raw in {"0/0", "N/A"}:
        return None
    try:
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            return float(numerator) / float(denominator)
        return float(raw)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _probe_video_metadata(video: Path) -> VideoMetadata:
    ffprobe = Path(resolve_ffmpeg_exe()).with_name("ffprobe.exe")
    process = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            (
                "stream=width,height,avg_frame_rate,r_frame_rate,nb_frames,"
                "nb_read_frames,duration,codec_name,pix_fmt:stream_tags=alpha_mode"
            ),
            "-of",
            "json",
            str(video),
        ],
        capture_output=True,
        text=True,
        **no_console_kwargs(),
    )
    if process.returncode != 0:
        return VideoMetadata(0, 0, None, None, None, "", "", None, "unknown")
    try:
        stream = (json.loads(process.stdout or "{}").get("streams") or [{}])[0]
    except (IndexError, TypeError, ValueError):
        stream = {}
    tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
    normalized_tags = {
        str(key).strip().lower(): value for key, value in (tags or {}).items()
    }
    alpha_tag = str(normalized_tags.get("alpha_mode") or "").strip().lower()
    pixel_format = str(stream.get("pix_fmt") or "")
    has_alpha = (
        True
        if alpha_tag in {"1", "true", "straight", "premultiplied"}
        or pixel_format.startswith(("rgba", "bgra", "argb", "abgr", "yuva", "gbrap"))
        else False
        if pixel_format
        else None
    )
    alpha_mode = (
        "premultiplied"
        if alpha_tag == "premultiplied"
        else "straight"
        if has_alpha
        else "none"
        if has_alpha is False
        else "unknown"
    )
    frame_raw = stream.get("nb_read_frames") or stream.get("nb_frames")
    try:
        frame_count = int(frame_raw) if str(frame_raw or "").isdigit() else None
    except (TypeError, ValueError):
        frame_count = None
    try:
        duration = float(stream.get("duration"))
    except (TypeError, ValueError):
        duration = None
    return VideoMetadata(
        width=int(stream.get("width") or 0),
        height=int(stream.get("height") or 0),
        fps=_fraction(stream.get("avg_frame_rate"))
        or _fraction(stream.get("r_frame_rate")),
        frame_count=frame_count,
        duration=duration,
        codec=str(stream.get("codec_name") or ""),
        pixel_format=pixel_format,
        has_alpha=has_alpha,
        alpha_mode=alpha_mode,
    )


def _generated_alpha_state(frames: list[Path]) -> bool | None:
    if not frames:
        return None
    indices = sorted({0, len(frames) // 2, len(frames) - 1})
    states = [_alpha_state(frames[index]) for index in indices]
    if any(value is True for value in states):
        return True
    if states and all(value is False for value in states):
        return False
    return None


def _full_source_frame_use(
    source: VideoMetadata,
    *,
    output_fps: int,
    output_frames: int,
) -> bool | None:
    if source.fps is None or source.frame_count is None:
        return None
    if abs(source.fps - output_fps) > 0.02:
        return False
    return source.frame_count == output_frames


def read_sequence_status(
    root: Path | None = None,
    *,
    quality: str = "720p",
    family: str | None = None,
) -> SequenceStatus:
    profile = _profile(quality, family)
    assets = _assets_dir(root)
    manifest_path = assets / profile.manifest_name
    manifest: dict[str, object] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            manifest = {}

    frames = _frame_files(assets, profile)
    first = frames[0] if frames else None
    width = int(manifest.get("width") or 0)
    height = int(manifest.get("height") or 0)
    if first and (not width or not height):
        try:
            with Image.open(first) as image:
                width, height = image.size
        except OSError:
            pass

    return SequenceStatus(
        quality=profile.quality,
        frame_count=len(frames),
        width=width,
        height=height,
        fps=int(manifest.get("fps") or DEFAULT_FPS),
        source=str(manifest.get("source") or ""),
        total_bytes=sum(path.stat().st_size for path in frames),
        has_alpha=(
            bool(manifest.get("hasAlpha"))
            if "hasAlpha" in manifest
            else _alpha_state(first) if first else None
        ),
        alpha_mode=str(manifest.get("alphaMode") or "unknown"),
        codec=str(manifest.get("codec") or "webp"),
        pixel_format=str(manifest.get("pixelFormat") or "rgba"),
        source_fps=(
            float(manifest["sourceFps"]) if manifest.get("sourceFps") is not None else None
        ),
        source_frame_count=(
            int(manifest["sourceFrameCount"])
            if manifest.get("sourceFrameCount") is not None
            else None
        ),
        source_has_alpha=(
            bool(manifest["sourceHasAlpha"])
            if manifest.get("sourceHasAlpha") is not None
            else None
        ),
        full_source_frame_use=(
            bool(manifest["fullSourceFrameUse"])
            if manifest.get("fullSourceFrameUse") is not None
            else None
        ),
    )


def read_native_video_status(
    root: Path | None = None,
    *,
    quality: str = "1080p",
    family: str | None = None,
) -> NativeVideoStatus:
    asset = _family(family)
    profile = _profile(quality, family)
    assets = _assets_dir(root)
    manifest_path = assets / asset.video_manifest[quality]
    manifest: dict[str, object] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            manifest = {}
    video = assets / asset.runtime_video[quality]
    poster = assets / asset.runtime_poster[quality]
    return NativeVideoStatus(
        quality=quality,
        frame_count=int(manifest.get("frameCount") or 0),
        width=int(manifest.get("width") or profile.width),
        height=int(manifest.get("height") or profile.height),
        fps=int(manifest.get("fps") or DEFAULT_FPS),
        total_bytes=sum(
            path.stat().st_size for path in (video, poster) if path.is_file()
        ),
        source=str(manifest.get("source") or ""),
        has_alpha=bool(manifest.get("hasAlpha", False)),
        alpha_mode=str(manifest.get("alphaMode") or "none"),
        codec=str(manifest.get("codec") or "h264"),
        pixel_format=str(manifest.get("pixelFormat") or "yuv420p"),
        source_fps=(
            float(manifest["sourceFps"]) if manifest.get("sourceFps") is not None else None
        ),
        source_frame_count=(
            int(manifest["sourceFrameCount"])
            if manifest.get("sourceFrameCount") is not None
            else None
        ),
        source_has_alpha=(
            bool(manifest["sourceHasAlpha"])
            if manifest.get("sourceHasAlpha") is not None
            else None
        ),
        full_source_frame_use=(
            bool(manifest["fullSourceFrameUse"])
            if manifest.get("fullSourceFrameUse") is not None
            else None
        ),
        background_mode=str(manifest.get("backgroundMode") or "color"),
    )


def _default_backup_dir() -> Path:
    marker = backup_path(
        "Komponenty/filozofiamarki/data/video-backups/.backup-root"
    )
    return marker.write_path.parent


def _create_backup(
    assets: Path,
    destination: Path,
    *,
    family: str | None = None,
) -> Path | None:
    asset = _family(family)
    files: list[Path] = []
    for profile in asset.quality_profiles.values():
        files.extend(_frame_files(assets, profile, all_extensions=True))
        manifest = assets / profile.manifest_name
        if manifest.is_file():
            files.append(manifest)
    for suffix in sorted(ALLOWED_VIDEO_SUFFIXES):
        candidate = assets / f"{asset.source_prefix}{suffix}"
        if candidate.is_file():
            files.append(candidate)
    if asset.id == "philosophy":
        legacy_source = assets / "giclee-philosophy-scroll.webm"
        if legacy_source.is_file():
            files.append(legacy_source)
    for quality in asset.quality_profiles:
        for name in (
            asset.runtime_video[quality],
            asset.runtime_poster[quality],
            asset.video_manifest[quality],
        ):
            candidate = assets / name
            if candidate.is_file():
                files.append(candidate)
    if not files:
        return None

    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    archive = destination / f"{asset.backup_prefix}-{stamp}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in dict.fromkeys(files):
            bundle.write(path, arcname=f"assets/{path.name}")

    backups = sorted(
        destination.glob(f"{asset.backup_prefix}-*.zip"), reverse=True
    )
    for stale in backups[BACKUP_LIMIT:]:
        stale.unlink(missing_ok=True)
    return archive


def _run_ffmpeg_export(
    source: Path,
    output_pattern: Path,
    *,
    fps: int,
    width: int,
    height: int = 720,
    composite_black: bool = False,
) -> None:
    command = [
        resolve_ffmpeg_exe(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if source.suffix.lower() == ".webm":
        command.extend(("-c:v", "libvpx-vp9"))
    command.extend(("-i", str(source), "-an"))
    if composite_black:
        command.extend(
            (
                "-filter_complex",
                (
                    f"color=c=black:s={width}x{height}:r={fps}[bg];"
                    f"[0:v]fps={fps},scale={width}:-2:flags=lanczos,"
                    "format=rgba[fg];[bg][fg]overlay=shortest=1:"
                    "format=auto,format=yuvj420p[out]"
                ),
                "-map",
                "[out]",
                "-fps_mode",
                "passthrough",
                "-c:v",
                "mjpeg",
                "-q:v",
                "2",
                "-frames:v",
                "1",
            )
        )
    else:
        command.extend(
            (
                "-vf",
                f"fps={fps},scale={width}:-2:flags=lanczos,format=rgba",
                "-fps_mode",
                "passthrough",
                "-c:v",
                "libwebp",
                "-lossless",
                "0",
                "-q:v",
                "95" if width >= 1920 else "82",
                "-compression_level",
                "5",
            )
        )
    command.extend(
        (
            "-start_number",
            "0",
            str(output_pattern),
        )
    )
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        **no_console_kwargs(),
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "").strip()
        raise RuntimeError(
            f"Nie udało się przygotować klatek WebP: {detail or process.returncode}"
        )


def _run_ffmpeg_native_video(
    source: Path,
    destination: Path,
    *,
    fps: int,
    width: int,
    height: int,
    crf: int = 10,
    x264_preset: str = "slow",
) -> None:
    command = [
        resolve_ffmpeg_exe(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if source.suffix.lower() == ".webm":
        command.extend(("-c:v", "libvpx-vp9"))
    command.extend(
        (
            "-i",
            str(source),
            "-filter_complex",
            (
                f"color=c=black:s={width}x{height}:r={fps}[bg];"
                f"[0:v]fps={fps},scale={width}:-2:flags=lanczos,"
                "format=rgba[fg];[bg][fg]overlay=shortest=1:"
                "format=auto,format=yuv420p[out]"
            ),
            "-map",
            "[out]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            x264_preset,
            "-crf",
            str(crf),
            "-g",
            "1",
            "-keyint_min",
            "1",
            "-sc_threshold",
            "0",
            "-movflags",
            "+faststart",
            str(destination),
        )
    )
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        **no_console_kwargs(),
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "").strip()
        raise RuntimeError(
            f"Nie udało się przygotować filmu scrollowanego: "
            f"{detail or process.returncode}"
        )


def _probe_frame_count(video: Path) -> int:
    ffprobe = Path(resolve_ffmpeg_exe()).with_name("ffprobe.exe")
    process = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(video),
        ],
        capture_output=True,
        text=True,
        **no_console_kwargs(),
    )
    if process.returncode != 0:
        raise RuntimeError("Nie udało się odczytać liczby klatek filmu 1080p.")
    try:
        return int(process.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Film 1080p nie zwrócił poprawnej liczby klatek.") from exc


def _run_ffmpeg_poster(
    source: Path,
    destination: Path,
    *,
    width: int,
) -> None:
    command = [
        resolve_ffmpeg_exe(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if source.suffix.lower() == ".webm":
        command.extend(("-c:v", "libvpx-vp9"))
    command.extend(
        (
            "-i",
            str(source),
            "-an",
            "-vf",
            f"scale={width}:-2:flags=lanczos,format=rgba",
            "-frames:v",
            "1",
            "-c:v",
            "libwebp",
            "-lossless",
            "0",
            "-q:v",
            "95",
            "-compression_level",
            "5",
            str(destination),
        )
    )
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        **no_console_kwargs(),
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "").strip()
        raise RuntimeError(
            f"Nie udało się przygotować postera filmu: "
            f"{detail or process.returncode}"
        )


def replace_native_video(
    source: Path,
    *,
    quality: str = "1080p",
    family: str | None = None,
    root: Path | None = None,
    backup_dir: Path | None = None,
    fps: int = DEFAULT_FPS,
    create_backup: bool = True,
) -> NativeVideoResult:
    asset = _family(family)
    profile = _profile(quality, family)
    source = Path(source).resolve()
    suffix = source.suffix.lower()
    if not source.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku: {source}")
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        raise ValueError("Obsługiwane formaty: MP4, WebM, MOV i MKV.")
    source_metadata = _probe_video_metadata(source)

    assets = _assets_dir(root)
    assets.mkdir(parents=True, exist_ok=True)
    staging = assets.parent / f".giclee-filozofia-video-{uuid4().hex}"
    staging.mkdir()
    try:
        staged_video = staging / asset.runtime_video[quality]
        staged_poster = staging / asset.runtime_poster[quality]
        _run_ffmpeg_native_video(
            source,
            staged_video,
            fps=fps,
            width=profile.width,
            height=profile.height,
            crf=10,
            x264_preset="slow",
        )
        _run_ffmpeg_poster(source, staged_poster, width=profile.width)
        frame_count = _probe_frame_count(staged_video)
        output_metadata = _probe_video_metadata(staged_video)
        poster_has_alpha = _alpha_state(staged_poster)
        source_has_alpha = (
            True
            if poster_has_alpha is True
            else source_metadata.has_alpha
        )
        if not frame_count or frame_count > MAX_FRAMES:
            raise RuntimeError(
                f"Film wygenerował {frame_count} klatek. Maksimum to {MAX_FRAMES}."
            )
        backup = (
            _create_backup(
                assets,
                backup_dir or _default_backup_dir(),
                family=family,
            )
            if create_backup
            else None
        )
        video_path = assets / asset.runtime_video[quality]
        poster_path = assets / asset.runtime_poster[quality]
        shutil.copy2(staged_video, video_path)
        shutil.copy2(staged_poster, poster_path)
        source_path = assets / f"{asset.source_prefix}{suffix}"
        if source.resolve() != source_path.resolve():
            shutil.copy2(source, source_path)
        elif not source_path.is_file():
            shutil.copy2(source, source_path)

        manifest = {
            "version": 2,
            "mode": "video",
            "family": asset.id,
            "quality": quality,
            "frameCount": frame_count,
            "width": profile.width,
            "height": profile.height,
            "fps": fps,
            "codec": output_metadata.codec or "h264",
            "pixelFormat": output_metadata.pixel_format or "yuv420p",
            "hasAlpha": False,
            "alphaMode": "none",
            "sourceFps": source_metadata.fps,
            "sourceFrameCount": source_metadata.frame_count,
            "sourceCodec": source_metadata.codec,
            "sourcePixelFormat": source_metadata.pixel_format,
            "sourceHasAlpha": source_has_alpha,
            "sourceAlphaMode": (
                source_metadata.alpha_mode
                if source_metadata.alpha_mode != "unknown"
                else "straight" if source_has_alpha else "none"
            ),
            "alphaLostDuringConversion": bool(source_has_alpha),
            "backgroundMode": "color",
            "backgroundValue": "#000000",
            "fallbackActive": bool(source_has_alpha),
            "keyframeInterval": 1,
            "intraOnly": True,
            "fullSourceFrameUse": _full_source_frame_use(
                source_metadata,
                output_fps=fps,
                output_frames=frame_count,
            ),
            "video": video_path.name,
            "poster": poster_path.name,
            "source": source_path.name,
            "generatedAt": datetime.now(UTC).isoformat(),
        }
        manifest_path = assets / asset.video_manifest[quality]
        pending = assets / f".{manifest_path.name}.tmp"
        pending.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        pending.replace(manifest_path)
    finally:
        if staging.is_dir() and staging.parent == assets.parent:
            shutil.rmtree(staging, ignore_errors=True)

    return NativeVideoResult(
        quality=quality,
        status=read_native_video_status(root, quality=quality, family=family),
        video_path=video_path,
        poster_path=poster_path,
        manifest_path=manifest_path,
        source_path=source_path,
        backup_path=backup,
    )


def replace_video_sequence(
    source: Path,
    *,
    quality: str = "720p",
    family: str | None = None,
    root: Path | None = None,
    backup_dir: Path | None = None,
    fps: int = DEFAULT_FPS,
    width: int | None = None,
    create_backup: bool = True,
) -> ReplaceResult:
    asset = _family(family)
    profile = _profile(quality, family)
    source = Path(source).resolve()
    suffix = source.suffix.lower()
    if not source.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku: {source}")
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        raise ValueError("Obsługiwane formaty: MP4, WebM, MOV i MKV.")
    if not 1 <= fps <= 60:
        raise ValueError("FPS musi mieścić się w zakresie 1–60.")
    target_width = width or profile.width
    if target_width < 320:
        raise ValueError("Szerokość klatek musi wynosić co najmniej 320 px.")
    source_metadata = _probe_video_metadata(source)

    assets = _assets_dir(root)
    assets.mkdir(parents=True, exist_ok=True)
    output_name = (
        f"{profile.frame_prefix}%0{FRAME_DIGITS}d{profile.extension}"
    )

    generated_dir = assets.parent / f".giclee-filozofia-frames-{uuid4().hex}"
    generated_dir.mkdir()
    try:
        _run_ffmpeg_export(
            source,
            generated_dir / output_name,
            fps=fps,
            width=target_width,
            height=profile.height,
            composite_black=profile.composite_black,
        )
        generated = _frame_files(generated_dir, profile)
        if not generated:
            raise RuntimeError("FFmpeg nie utworzył żadnej klatki.")
        sequence_frame_count = len(generated)
        if sequence_frame_count > MAX_FRAMES:
            raise RuntimeError(
                f"Film wygenerował {sequence_frame_count} klatek. Maksimum to {MAX_FRAMES} "
                "(około 16,6 s przy 60 FPS)."
            )

        with Image.open(generated[0]) as first:
            frame_width, frame_height = first.size
        generated_has_alpha = _generated_alpha_state(generated)
        source_has_alpha = (
            True
            if generated_has_alpha is True
            else source_metadata.has_alpha
        )
        if source_has_alpha is True and generated_has_alpha is not True:
            raise RuntimeError(
                "Źródło posiada kanał alfa, ale wygenerowana sekwencja go utraciła."
            )

        backup = (
            _create_backup(
                assets,
                backup_dir or _default_backup_dir(),
                family=family,
            )
            if create_backup
            else None
        )
        new_names = {path.name for path in generated}
        for frame in generated:
            shutil.copy2(frame, assets / frame.name)

        source_dest = assets / f"{asset.source_prefix}{suffix}"
        if source.resolve() != source_dest.resolve():
            shutil.copy2(source, source_dest)
        elif not source_dest.is_file():
            shutil.copy2(source, source_dest)

        manifest = {
            "version": 5,
            "family": asset.id,
            "frameCount": sequence_frame_count,
            "width": frame_width,
            "height": frame_height,
            "quality": profile.quality,
            "prefix": profile.frame_prefix,
            "digits": FRAME_DIGITS,
            "extension": profile.extension,
            "fps": fps,
            "codec": "webp",
            "pixelFormat": "rgba" if generated_has_alpha else "rgb",
            "hasAlpha": generated_has_alpha,
            "alphaMode": "straight" if generated_has_alpha else "none",
            "preserveAlpha": True,
            "backgroundMode": "transparent" if generated_has_alpha else "auto",
            "sourceFps": source_metadata.fps,
            "sourceFrameCount": source_metadata.frame_count,
            "sourceCodec": source_metadata.codec,
            "sourcePixelFormat": source_metadata.pixel_format,
            "sourceHasAlpha": source_has_alpha,
            "sourceAlphaMode": (
                source_metadata.alpha_mode
                if source_metadata.alpha_mode != "unknown"
                else "straight" if source_has_alpha else "none"
            ),
            "alphaLostDuringConversion": bool(
                source_has_alpha is True and generated_has_alpha is not True
            ),
            "fullSourceFrameUse": _full_source_frame_use(
                source_metadata,
                output_fps=fps,
                output_frames=sequence_frame_count,
            ),
            "source": source_dest.name,
            "generatedAt": datetime.now(UTC).isoformat(),
        }
        manifest_path = assets / profile.manifest_name
        pending_manifest = assets / f".{profile.manifest_name}.tmp"
        pending_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        pending_manifest.replace(manifest_path)

        for old_frame in _frame_files(
            assets,
            profile,
            all_extensions=True,
        ):
            if old_frame.name not in new_names:
                old_frame.unlink(missing_ok=True)
        for old_suffix in ALLOWED_VIDEO_SUFFIXES:
            old_source = assets / f"{asset.source_prefix}{old_suffix}"
            if old_source != source_dest:
                old_source.unlink(missing_ok=True)
    finally:
        if generated_dir.is_dir() and generated_dir.parent == assets.parent:
            shutil.rmtree(generated_dir, ignore_errors=True)

    status = read_sequence_status(root, quality=profile.quality, family=family)
    return ReplaceResult(
        quality=profile.quality,
        status=status,
        manifest_path=manifest_path,
        source_path=source_dest,
        backup_path=backup,
    )


def replace_video_variants(
    source: Path,
    *,
    family: str | None = None,
    root: Path | None = None,
    backup_dir: Path | None = None,
    fps: int = DEFAULT_FPS,
) -> VariantsReplaceResult:
    """Tworzy z jednego źródła zsynchronizowane warianty 720p i 1080p."""
    asset = _family(family)
    source = Path(source).resolve()
    assets = _assets_dir(root)
    assets.mkdir(parents=True, exist_ok=True)
    backup = _create_backup(
        assets, backup_dir or _default_backup_dir(), family=family
    )

    results: list[ReplaceResult] = []
    for quality in asset.quality_profiles:
        results.append(
            replace_video_sequence(
                source,
                quality=quality,
                family=family,
                root=root,
                backup_dir=backup_dir,
                fps=fps,
                create_backup=False,
            )
        )
    return VariantsReplaceResult(
        variants=tuple(results),
        source_path=results[-1].source_path,
        backup_path=backup,
    )


def format_status(status: SequenceStatus) -> str:
    if not status.frame_count:
        return f"Klatki WebP {status.quality}: brak przygotowanej sekwencji."
    size_mb = status.total_bytes / (1024 * 1024)
    alpha = (
        f"Wykryto kanał alfa ({status.alpha_mode})"
        if status.has_alpha is True
        else "kanał alfa: nie"
        if status.has_alpha is False
        else "kanał alfa: nieznany"
    )
    source_alpha = (
        "tak" if status.source_has_alpha is True
        else "nie" if status.source_has_alpha is False
        else "nieznana"
    )
    frame_use = (
        "wszystkie klatki źródła: tak"
        if status.full_source_frame_use is True
        else "wszystkie klatki źródła: nie"
        if status.full_source_frame_use is False
        else "wszystkie klatki źródła: brak dowodu"
    )
    source = status.source or "starsza sekwencja (brak informacji o źródle)"
    return (
        f"Klatki WebP {status.quality}: {status.frame_count} klatek · "
        f"{status.fps} FPS · "
        f"{status.width}×{status.height} · {status.duration_seconds:.2f} s · "
        f"{size_mb:.1f} MB · {alpha} · {status.codec}/{status.pixel_format}\n"
        f"Źródło: {source} · FPS: {status.source_fps or 'nieznany'} · "
        f"alfa: {source_alpha} · {frame_use}"
    )


def format_native_video_status(status: NativeVideoStatus) -> str:
    if not status.frame_count:
        return f"Film {status.quality}: brak przygotowanego pliku."
    size_mb = status.total_bytes / (1024 * 1024)
    source = status.source or "brak informacji o źródle"
    source_alpha = (
        "tak" if status.source_has_alpha is True
        else "nie" if status.source_has_alpha is False
        else "nieznana"
    )
    fallback = (
        "fallback tła aktywny"
        if status.source_has_alpha is True and not status.has_alpha
        else "fallback tła nieaktywny"
    )
    frame_use = (
        "wszystkie klatki źródła: tak"
        if status.full_source_frame_use is True
        else "wszystkie klatki źródła: nie"
        if status.full_source_frame_use is False
        else "wszystkie klatki źródła: brak dowodu"
    )
    return (
        f"Film {status.quality}: {status.frame_count} klatek · "
        f"{status.fps} FPS · {status.width}×{status.height} · "
        f"{status.duration_seconds:.2f} s · {size_mb:.1f} MB · "
        f"{status.codec}/{status.pixel_format} · alfa finalna: nie\n"
        f"Źródło: {source} · FPS: {status.source_fps or 'nieznany'} · "
        f"alfa: {source_alpha} · {fallback} ({status.background_mode}) · {frame_use}"
    )


__all__ = [
    "ASSET_FAMILIES",
    "NativeVideoResult",
    "NativeVideoStatus",
    "ReplaceResult",
    "SequenceStatus",
    "VariantsReplaceResult",
    "format_status",
    "format_native_video_status",
    "read_native_video_status",
    "read_sequence_status",
    "replace_native_video",
    "replace_video_sequence",
    "replace_video_variants",
]
