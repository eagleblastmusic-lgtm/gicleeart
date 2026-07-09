"""Podglad klatek wideo (ffmpeg) dla Bazy Promptow."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from Komponenty._shared.subprocess_win import no_console_kwargs

MAX_PLAYBACK_FPS = 30.0
MIN_PLAYBACK_FPS = 12.0
MAX_SEGMENT_FRAMES = 300


@dataclass
class SegmentPlayback:
    images: list[object]
    fps: float
    temp_dir: Path | None = None


def resolve_ffmpeg_exe() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:
        return None


def resolve_ffprobe_exe() -> str | None:
    found = shutil.which("ffprobe")
    if found:
        return found
    ffmpeg = resolve_ffmpeg_exe()
    if not ffmpeg:
        return None
    candidate = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix else "ffprobe")
    return str(candidate) if candidate.is_file() else None


def probe_video_duration(source: Path) -> float | None:
    ffprobe = resolve_ffprobe_exe()
    if not ffprobe or not source.is_file():
        return None
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, **no_console_kwargs())
    if proc.returncode != 0:
        return None
    try:
        value = float((proc.stdout or "").strip())
    except ValueError:
        return None
    return value if value > 0 else None


def probe_video_fps(source: Path) -> float | None:
    ffprobe = resolve_ffprobe_exe()
    if not ffprobe or not source.is_file():
        return None
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, **no_console_kwargs())
    if proc.returncode != 0:
        return None
    raw = (proc.stdout or "").strip()
    if not raw or raw == "0/0":
        return None
    if "/" in raw:
        num, den = raw.split("/", 1)
        try:
            value = float(num) / float(den)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    else:
        try:
            value = float(raw)
        except ValueError:
            return None
    return value if value > 0 else None


def playback_fps_for_segment(duration_sec: float, source: Path) -> tuple[float, int]:
    duration = max(0.1, float(duration_sec))
    fps = probe_video_fps(source) or 24.0
    fps = min(MAX_PLAYBACK_FPS, max(MIN_PLAYBACK_FPS, fps))
    frame_count = max(2, int(duration * fps))
    if frame_count > MAX_SEGMENT_FRAMES:
        fps = MAX_SEGMENT_FRAMES / duration
        frame_count = MAX_SEGMENT_FRAMES
    return fps, frame_count


def boomerang_frame_indices(frame_count: int) -> list[int]:
    """Indeksy klatek: do przodu, potem do tylu (bez powtorki skrajnych)."""
    if frame_count <= 0:
        return []
    if frame_count == 1:
        return [0]
    forward = list(range(frame_count))
    backward = list(range(frame_count - 2, 0, -1))
    return forward + backward


def extract_video_poster(
    source: Path,
    dest: Path,
    *,
    width: int = 240,
    height: int = 180,
    start_sec: float = 0.4,
) -> bool:
    ffmpeg = resolve_ffmpeg_exe()
    if not ffmpeg or not source.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(max(0.0, start_sec)),
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, **no_console_kwargs())
    return proc.returncode == 0 and dest.is_file()


def _pil_images_from_paths(paths: list[Path], *, width: int) -> list[object]:
    try:
        from PIL import Image
    except ImportError:
        return []
    images: list[object] = []
    size = (width, int(width * 0.75))
    for frame_path in paths:
        if not frame_path.is_file():
            continue
        try:
            img = Image.open(frame_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            images.append(img.copy())
        except Exception:
            continue
    return images


def _load_segment_opencv(
    source: Path,
    *,
    start_sec: float,
    end_sec: float,
    width: int,
) -> SegmentPlayback | None:
    try:
        import cv2
        from PIL import Image
    except ImportError:
        return None

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    fps = min(MAX_PLAYBACK_FPS, max(MIN_PLAYBACK_FPS, float(fps)))
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, start_sec) * 1000.0)
    end_ms = max(0.0, end_sec) * 1000.0
    thumb = (width, int(width * 0.75))
    images: list[object] = []
    while cap.get(cv2.CAP_PROP_POS_MSEC) < end_ms and len(images) < MAX_SEGMENT_FRAMES:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img.thumbnail(thumb, Image.Resampling.LANCZOS)
        images.append(img)
    cap.release()
    if len(images) < 1:
        return None
    return SegmentPlayback(images=images, fps=fps)


def _load_segment_ffmpeg(
    source: Path,
    *,
    start_sec: float,
    end_sec: float,
    width: int,
) -> SegmentPlayback | None:
    ffmpeg = resolve_ffmpeg_exe()
    if not ffmpeg or not source.is_file():
        return None

    start = max(0.0, float(start_sec))
    end = max(start + 0.1, float(end_sec))
    duration = end - start
    fps, frame_count = playback_fps_for_segment(duration, source)

    temp_dir = Path(tempfile.mkdtemp(prefix="bazapromptow-vid-"))
    pattern = str(temp_dir / "frame_%04d.jpg")
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start),
        "-i",
        str(source),
        "-t",
        str(duration),
        "-vf",
        f"fps={fps:.3f},scale={width}:-2",
        "-frames:v",
        str(frame_count),
        pattern,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, **no_console_kwargs())
    frames = sorted(temp_dir.glob("frame_*.jpg"))
    images = _pil_images_from_paths(frames, width=width)
    if proc.returncode != 0 or len(images) < 1:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None
    return SegmentPlayback(images=images, fps=fps, temp_dir=temp_dir)


def load_segment_playback(
    source: Path,
    *,
    start_sec: float,
    end_sec: float,
    width: int = 240,
) -> SegmentPlayback | None:
    """Laduje klatki fragmentu wideo do plywnego odtwarzania (OpenCV lub ffmpeg)."""
    if not source.is_file():
        return None
    opencv = _load_segment_opencv(
        source,
        start_sec=start_sec,
        end_sec=end_sec,
        width=width,
    )
    if opencv is not None:
        return opencv
    return _load_segment_ffmpeg(
        source,
        start_sec=start_sec,
        end_sec=end_sec,
        width=width,
    )


def extract_video_preview_frames(
    source: Path,
    *,
    start_sec: float = 0.0,
    end_sec: float = 3.0,
    count: int = 12,
    width: int = 240,
) -> tuple[Path, list[Path]]:
    """Zwraca (katalog tymczasowy, lista klatek jpg w zadanym zakresie czasu)."""
    ffmpeg = resolve_ffmpeg_exe()
    if not ffmpeg or not source.is_file():
        return Path(tempfile.mkdtemp(prefix="bazapromptow-vid-")), []

    start = max(0.0, float(start_sec))
    end = max(start + 0.1, float(end_sec))
    duration = end - start
    fps, frame_count = playback_fps_for_segment(duration, source)

    temp_dir = Path(tempfile.mkdtemp(prefix="bazapromptow-vid-"))
    pattern = str(temp_dir / "frame_%02d.jpg")
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start),
        "-i",
        str(source),
        "-t",
        str(duration),
        "-vf",
        f"fps={fps:.3f},scale={width}:-2",
        "-frames:v",
        str(frame_count),
        pattern,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, **no_console_kwargs())
    frames = sorted(temp_dir.glob("frame_*.jpg"))
    if proc.returncode != 0 or len(frames) < 1:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return Path(tempfile.mkdtemp(prefix="bazapromptow-vid-")), []
    return temp_dir, frames
