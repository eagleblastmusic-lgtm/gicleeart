"""Bezpieczna podmiana filmu źródłowego i sekwencji WebP strony filozofii."""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
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
    runtime_webm: dict[str, str]
    runtime_poster: dict[str, str]
    webm_poster: dict[str, str]
    video_manifest: dict[str, str]
    webm_manifest: dict[str, str]
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
        runtime_webm={
            "720p": "giclee-philosophy-scroll-720.webm",
            "1080p": "giclee-philosophy-scroll-1080.webm",
        },
        runtime_poster={
            "720p": "giclee-philosophy-video-720-poster.webp",
            "1080p": "giclee-philosophy-video-1080-poster.webp",
        },
        webm_poster={
            "720p": "giclee-philosophy-webm-720-poster.webp",
            "1080p": "giclee-philosophy-webm-1080-poster.webp",
        },
        video_manifest={
            "720p": "giclee-philosophy-video-720-manifest.json",
            "1080p": "giclee-philosophy-video-1080-manifest.json",
        },
        webm_manifest={
            "720p": "giclee-philosophy-webm-720-manifest.json",
            "1080p": "giclee-philosophy-webm-1080-manifest.json",
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
        runtime_webm={
            "720p": "giclee-philosophy-wrota-scroll-720.webm",
            "1080p": "giclee-philosophy-wrota-scroll-1080.webm",
        },
        runtime_poster={
            "720p": "giclee-philosophy-wrota-video-720-poster.webp",
            "1080p": "giclee-philosophy-wrota-video-1080-poster.webp",
        },
        webm_poster={
            "720p": "giclee-philosophy-wrota-webm-720-poster.webp",
            "1080p": "giclee-philosophy-wrota-webm-1080-poster.webp",
        },
        video_manifest={
            "720p": "giclee-philosophy-wrota-video-720-manifest.json",
            "1080p": "giclee-philosophy-wrota-video-1080-manifest.json",
        },
        webm_manifest={
            "720p": "giclee-philosophy-wrota-webm-720-manifest.json",
            "1080p": "giclee-philosophy-wrota-webm-1080-manifest.json",
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
RUNTIME_WEBM_NAMES = ASSET_FAMILIES["philosophy"].runtime_webm
RUNTIME_POSTER_NAMES = ASSET_FAMILIES["philosophy"].runtime_poster
WEBM_POSTER_NAMES = ASSET_FAMILIES["philosophy"].webm_poster
VIDEO_MANIFEST_NAMES = ASSET_FAMILIES["philosophy"].video_manifest
WEBM_MANIFEST_NAMES = ASSET_FAMILIES["philosophy"].webm_manifest
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
    container: str
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
    keyframe_interval: int | None
    intra_only: bool | None
    passthrough: bool

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / self.fps if self.frame_count and self.fps else 0.0


@dataclass(frozen=True)
class NativeVideoResult:
    quality: str
    container: str
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


@dataclass(frozen=True)
class NativeVideoAsset:
    family: str
    quality: str
    container: str
    video: str
    poster: str
    manifest: str
    frame_count: int
    fps: int
    width: int
    height: int
    has_alpha: bool | None
    codec: str
    total_bytes: int

    @property
    def source_spec(self) -> str:
        alpha = (
            "true"
            if self.has_alpha is True
            else "false"
            if self.has_alpha is False
            else "unknown"
        )
        values = (
            self.video,
            self.poster or "-",
            self.manifest or "-",
            str(self.frame_count or 0),
            str(self.fps or DEFAULT_FPS),
            str(self.width or 0),
            str(self.height or 0),
            alpha,
            self.codec or "unknown",
        )
        return "::".join(values)

    @property
    def label(self) -> str:
        size_mb = self.total_bytes / (1024 * 1024)
        alpha = " · alfa" if self.has_alpha is True else ""
        return (
            f"{self.video} — {self.width}×{self.height} · "
            f"{self.fps} FPS · {size_mb:.1f} MB{alpha}"
        )


def _native_asset_names(
    asset: AssetFamily,
    quality: str,
    container: str,
) -> tuple[str, str, str]:
    if container == "mp4":
        return (
            asset.runtime_video[quality],
            asset.runtime_poster[quality],
            asset.video_manifest[quality],
        )
    if container == "webm":
        return (
            asset.runtime_webm[quality],
            asset.webm_poster[quality],
            asset.webm_manifest[quality],
        )
    raise ValueError("Kontener filmu musi mieć wartość mp4 albo webm.")


def parse_native_video_source_spec(value: str | None) -> dict[str, str]:
    """Rozkoduj wybór biblioteki; obsługuje też starszą wartość = nazwa pliku."""

    raw = str(value or "").strip()
    if not raw:
        return {}
    parts = raw.split("::")
    names = (
        "video",
        "poster",
        "manifest",
        "frame_count",
        "fps",
        "width",
        "height",
        "has_alpha",
        "codec",
    )
    result = {
        name: parts[index].strip()
        for index, name in enumerate(names)
        if index < len(parts) and parts[index].strip() not in {"", "-"}
    }
    if "video" not in result:
        result["video"] = raw
    return result


PAGE_TEMPLATE_REL = "templates/page.filozofia-marki.json"
_SHOPIFYIGNORE_BEGIN = "# BEGIN giclee-filozofia-active-scroll-video"
_SHOPIFYIGNORE_END = "# END giclee-filozofia-active-scroll-video"


def _asset_id_to_family(asset_id: str) -> str:
    if "wrota" in str(asset_id):
        return "wrota"
    return "philosophy"


def iter_scroll_video_block_settings(
    root: Path | None = None,
) -> list[dict[str, str]]:
    """Odczytaj aktywne ustawienia scroll_video ze szablonu strony."""

    template_path = (root or theme_root()) / PAGE_TEMPLATE_REL
    raw = template_path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            raw = raw[end + 2 :]
    data = json.loads(raw)
    selections: list[dict[str, str]] = []
    for section in (data.get("sections") or {}).values():
        if not isinstance(section, dict):
            continue
        for block in (section.get("blocks") or {}).values():
            if not isinstance(block, dict):
                continue
            settings = block.get("settings") or {}
            if settings.get("media_type") != "scroll_video":
                continue
            asset_id = str(
                settings.get("scroll_video_asset") or "giclee-philosophy-frames"
            )
            quality = str(settings.get("scroll_video_quality") or "720p")
            if quality not in {"720p", "1080p"}:
                quality = "720p"
            container = str(settings.get("scroll_video_container") or "mp4")
            if container not in {"mp4", "webm"}:
                container = "mp4"
            engine = str(settings.get("scroll_video_engine") or "video")
            if engine not in {"video", "frames"}:
                engine = "video"
            selections.append(
                {
                    "family": _asset_id_to_family(asset_id),
                    "asset_id": asset_id,
                    "engine": engine,
                    "container": container,
                    "quality": quality,
                    "source_spec": str(
                        settings.get("scroll_video_source") or ""
                    ).strip(),
                }
            )
    return selections


def all_scroll_video_runtime_relpaths(
    root: Path | None = None,
) -> tuple[str, ...]:
    """Wszystkie możliwe pliki runtime filmów (mp4/webm + poster + manifest)."""

    paths: list[str] = []
    for asset in ASSET_FAMILIES.values():
        for quality in asset.quality_profiles:
            for container in ("mp4", "webm"):
                video, poster, manifest = _native_asset_names(
                    asset, quality, container
                )
                paths.extend(
                    (
                        f"assets/{video}",
                        f"assets/{poster}",
                        f"assets/{manifest}",
                    )
                )
            profile = asset.quality_profiles[quality]
            paths.append(f"assets/{profile.manifest_name}")
        paths.append(f"assets/{asset.source_prefix}.mp4")
        paths.append(f"assets/{asset.source_prefix}.webm")
    assets = _assets_dir(root)
    if assets.is_dir():
        for path in sorted(assets.glob("giclee-scroll-library-*")):
            if path.is_file() and path.suffix.lower() in {
                ".mp4",
                ".webm",
                ".webp",
                ".json",
            }:
                paths.append(f"assets/{path.name}")
    return tuple(dict.fromkeys(paths))


def active_scroll_video_deploy_relpaths(
    root: Path | None = None,
) -> tuple[str, ...]:
    """Tylko pliki aktywnego silnika/jakości/kontenera ze szablonu."""

    paths: list[str] = []
    for item in iter_scroll_video_block_settings(root):
        asset = _family(item["family"])
        if item["engine"] == "frames":
            profile = asset.quality_profiles[item["quality"]]
            paths.append(f"assets/{profile.manifest_name}")
            continue
        video, poster, manifest = _native_asset_names(
            asset, item["quality"], item["container"]
        )
        paths.extend(
            (
                f"assets/{video}",
                f"assets/{poster}",
                f"assets/{manifest}",
            )
        )
    return tuple(dict.fromkeys(paths))


def activate_selected_video_sources(
    root: Path | None = None,
) -> tuple[Path, ...]:
    """Skopiuj wybrane pozycje biblioteki do stabilnych slotów runtime."""

    theme = root or theme_root()
    assets = theme / "assets"
    changed: list[Path] = []
    for item in iter_scroll_video_block_settings(theme):
        if item["engine"] != "video":
            continue
        selected = parse_native_video_source_spec(item.get("source_spec"))
        if not selected.get("video"):
            continue
        asset = _family(item["family"])
        video_name, poster_name, manifest_name = _native_asset_names(
            asset,
            item["quality"],
            item["container"],
        )
        source_video = assets / selected["video"]
        if not source_video.is_file():
            raise FileNotFoundError(
                f"Wybrany plik biblioteki nie istnieje: {source_video.name}"
            )
        target_video = assets / video_name
        if source_video.resolve() != target_video.resolve():
            shutil.copy2(source_video, target_video)
            changed.append(target_video)

        source_poster_name = selected.get("poster", "")
        source_poster = assets / source_poster_name if source_poster_name else None
        target_poster = assets / poster_name
        if (
            source_poster
            and source_poster.is_file()
            and source_poster.resolve() != target_poster.resolve()
        ):
            shutil.copy2(source_poster, target_poster)
            changed.append(target_poster)

        source_manifest_name = selected.get("manifest", "")
        source_manifest = (
            assets / source_manifest_name if source_manifest_name else None
        )
        manifest: dict[str, object] = {}
        if source_manifest and source_manifest.is_file():
            try:
                manifest = json.loads(
                    source_manifest.read_text(encoding="utf-8")
                )
            except (OSError, TypeError, ValueError):
                manifest = {}
        alpha_raw = selected.get("has_alpha", "unknown")
        has_alpha = (
            True
            if alpha_raw == "true"
            else False
            if alpha_raw == "false"
            else manifest.get("hasAlpha")
        )
        manifest.update(
            {
                "version": max(3, int(manifest.get("version") or 3)),
                "mode": "video",
                "family": asset.id,
                "quality": item["quality"],
                "container": item["container"],
                "mimeType": (
                    "video/webm"
                    if item["container"] == "webm"
                    else "video/mp4"
                ),
                "video": target_video.name,
                "poster": target_poster.name,
                "frameCount": int(
                    selected.get("frame_count")
                    or manifest.get("frameCount")
                    or 0
                ),
                "fps": int(
                    selected.get("fps")
                    or manifest.get("fps")
                    or DEFAULT_FPS
                ),
                "width": int(
                    selected.get("width")
                    or manifest.get("width")
                    or _profile(item["quality"], asset.id).width
                ),
                "height": int(
                    selected.get("height")
                    or manifest.get("height")
                    or _profile(item["quality"], asset.id).height
                ),
                "hasAlpha": has_alpha,
                "codec": (
                    selected.get("codec")
                    or manifest.get("codec")
                    or ("vp9" if item["container"] == "webm" else "h264")
                ),
                "activatedFrom": source_video.name,
                "activatedAt": datetime.now(UTC).isoformat(),
            }
        )
        target_manifest = assets / manifest_name
        pending = assets / f".{target_manifest.name}.tmp"
        pending.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        pending.replace(target_manifest)
        changed.append(target_manifest)
    return tuple(dict.fromkeys(changed))


def apply_scroll_video_selection(root: Path | None = None) -> Path:
    """Aktywuj wybór biblioteki i odśwież filtrowanie theme dev/deploy."""

    theme = root or theme_root()
    activate_selected_video_sources(theme)
    sync_philosophy_scroll_bg_mode(root=theme)
    return sync_scroll_video_shopifyignore(theme)


def _load_page_template(path: Path) -> tuple[str, dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    header = ""
    body = raw
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            header = raw[: end + 2].rstrip() + "\n"
            body = raw[end + 2 :].lstrip()
    return header, json.loads(body)


def _write_page_template(path: Path, header: str, data: dict[str, Any]) -> None:
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(header + body if header else body, encoding="utf-8")


def sync_philosophy_scroll_bg_mode(*, root: Path | None = None) -> bool:
    """Gdy plik tła scrolla istnieje, a mode jest ``auto`` — ustaw ``asset``/``webm``.

    Po podmianie wideo zapis często wraca do ``auto`` i tło robi się czarne
    (silnik video + auto = #000). «Usuń tło» kasuje plik, więc nie promujemy wtedy.
    """

    theme = root or theme_root()
    template_path = theme / PAGE_TEMPLATE_REL
    if not template_path.is_file():
        return False

    webm_exists = (theme / PHILOSOPHY_SCROLL_BG_WEBM_REL).is_file()
    image_exists = (theme / PHILOSOPHY_SCROLL_BG_IMAGE_REL).is_file()
    if not webm_exists and not image_exists:
        return False
    desired = "webm" if webm_exists else "asset"

    header, data = _load_page_template(template_path)
    changed = False
    for section in (data.get("sections") or {}).values():
        if not isinstance(section, dict):
            continue
        for block in (section.get("blocks") or {}).values():
            if not isinstance(block, dict):
                continue
            settings = block.get("settings")
            if not isinstance(settings, dict):
                continue
            if settings.get("media_type") != "scroll_video":
                continue
            asset_id = str(settings.get("scroll_video_asset") or "")
            if "wrota" in asset_id:
                continue
            mode = str(settings.get("scroll_background_mode") or "auto").strip().lower()
            if mode not in {"", "auto"}:
                continue
            settings["scroll_background_mode"] = desired
            settings["scroll_background_value"] = ""
            changed = True

    if changed:
        _write_page_template(template_path, header, data)
    return changed


def active_scroll_video_frame_globs(
    root: Path | None = None,
) -> tuple[str, ...]:
    """Globy klatek WebP wyłącznie gdy aktywny silnik to frames."""

    globs: list[str] = []
    for item in iter_scroll_video_block_settings(root):
        if item["engine"] != "frames":
            continue
        profile = _family(item["family"]).quality_profiles[item["quality"]]
        globs.append(f"assets/{profile.frame_prefix}*.webp")
    return tuple(dict.fromkeys(globs))


def inactive_scroll_video_relpaths(root: Path | None = None) -> tuple[str, ...]:
    """Pliki runtime, których nie wolno syncować przy aktywnym wariancie."""

    active = set(active_scroll_video_deploy_relpaths(root))
    return tuple(
        path
        for path in all_scroll_video_runtime_relpaths(root)
        if path not in active
    )


def sync_scroll_video_shopifyignore(root: Path | None = None) -> Path:
    """Zaktualizuj .shopifyignore: ignoruj nieaktywne filmy scroll_video."""

    theme = root or theme_root()
    ignore_path = theme / ".shopifyignore"
    inactive = inactive_scroll_video_relpaths(theme)
    block_lines = [
        _SHOPIFYIGNORE_BEGIN,
        "# Auto: tylko aktywny wariant Film-scroll (Filozofia marki) idzie do theme sync",
        *[path for path in inactive],
        # Klatki WebP rodzin — sync tylko gdy silnik frames (patrz deploy globs)
        "assets/giclee-philosophy-v3-frame-*.webp",
        "assets/giclee-philosophy-1080-frame-*.webp",
        "assets/giclee-philosophy-wrota-720-frame-*.webp",
        "assets/giclee-philosophy-wrota-1080-frame-*.webp",
        _SHOPIFYIGNORE_END,
        "",
    ]
    # Jeśli frames jest aktywny, nie ignoruj jego globów.
    active_frame_globs = set(active_scroll_video_frame_globs(theme))
    block_lines = [
        line
        for line in block_lines
        if line not in active_frame_globs
    ]

    existing = (
        ignore_path.read_text(encoding="utf-8")
        if ignore_path.is_file()
        else ""
    )
    if _SHOPIFYIGNORE_BEGIN in existing and _SHOPIFYIGNORE_END in existing:
        before, rest = existing.split(_SHOPIFYIGNORE_BEGIN, 1)
        _mid, after = rest.split(_SHOPIFYIGNORE_END, 1)
        new_text = before.rstrip() + "\n\n" + "\n".join(block_lines) + after.lstrip("\n")
    else:
        # Usuń stare ręczne wpisy source / oversized z poprzedniej sesji
        cleaned_lines = []
        skip_prefixes = (
            "assets/giclee-philosophy-wrota-scroll-source",
            "assets/*-scroll-source",
            "assets/giclee-philosophy-wrota-scroll-720.mp4",
            "assets/giclee-philosophy-wrota-scroll-1080.mp4",
        )
        for line in existing.splitlines():
            if any(line.strip().startswith(prefix) for prefix in skip_prefixes):
                continue
            if "Assety > limitu Shopify" in line:
                continue
            cleaned_lines.append(line)
        new_text = "\n".join(cleaned_lines).rstrip() + "\n\n" + "\n".join(block_lines)

    ignore_path.write_text(new_text, encoding="utf-8", newline="\n")
    return ignore_path


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


_VIDEO_METADATA_CACHE: dict[tuple[str, int, int], VideoMetadata] = {}


def _cached_video_metadata(video: Path) -> VideoMetadata:
    stat = video.stat()
    key = (str(video.resolve()), stat.st_size, stat.st_mtime_ns)
    cached = _VIDEO_METADATA_CACHE.get(key)
    if cached is not None:
        return cached
    metadata = _probe_video_metadata(video)
    if len(_VIDEO_METADATA_CACHE) >= 128:
        _VIDEO_METADATA_CACHE.clear()
    _VIDEO_METADATA_CACHE[key] = metadata
    return metadata


def _video_name_family(filename: str) -> str | None:
    lowered = filename.lower()
    if "wrota" in lowered:
        return "wrota"
    if "philosophy" in lowered or "filozof" in lowered:
        return "philosophy"
    return None


def _quality_from_size(width: int, height: int) -> str | None:
    if width == 1920 and height == 1080:
        return "1080p"
    if width == 1280 and height == 720:
        return "720p"
    return None


def list_native_video_assets(
    *,
    family: str,
    container: str,
    quality: str,
    root: Path | None = None,
) -> tuple[NativeVideoAsset, ...]:
    """Zwróć wszystkie zgodne filmy z assets, także starsze i biblioteczne."""

    asset_family = _family(family)
    if container not in {"mp4", "webm"}:
        return ()
    if quality not in asset_family.quality_profiles:
        return ()
    assets = _assets_dir(root)
    if not assets.is_dir():
        return ()

    manifest_by_video: dict[str, tuple[str, dict[str, object]]] = {}
    for path in assets.glob("*manifest.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            continue
        if manifest.get("mode") != "video":
            continue
        video_name = str(manifest.get("video") or "").strip()
        if not video_name:
            continue
        manifest_family = str(
            manifest.get("family") or _video_name_family(video_name) or ""
        )
        if manifest_family != family:
            continue
        manifest_by_video[video_name] = (path.name, manifest)

    found: list[NativeVideoAsset] = []
    suffix = f".{container}"
    for video in sorted(assets.glob(f"*{suffix}"), key=lambda item: item.name.lower()):
        if not video.is_file():
            continue
        manifest_name = ""
        manifest: dict[str, object] = {}
        matched_manifest = manifest_by_video.get(video.name)
        if matched_manifest:
            manifest_name, manifest = matched_manifest
            item_family = str(manifest.get("family") or family)
        else:
            item_family = _video_name_family(video.name) or ""
        if item_family != family:
            continue

        needs_probe = not manifest or any(
            manifest.get(key) in (None, "")
            for key in (
                "width",
                "height",
                "frameCount",
                "fps",
                "codec",
                "hasAlpha",
            )
        )
        try:
            metadata = (
                _cached_video_metadata(video)
                if needs_probe
                else VideoMetadata(
                    width=0,
                    height=0,
                    fps=None,
                    frame_count=None,
                    duration=None,
                    codec="",
                    pixel_format="",
                    has_alpha=None,
                    alpha_mode="unknown",
                )
            )
        except OSError:
            continue
        width = int(manifest.get("width") or metadata.width or 0)
        height = int(manifest.get("height") or metadata.height or 0)
        item_quality = str(
            manifest.get("quality") or _quality_from_size(width, height) or ""
        )
        if item_quality != quality:
            continue
        frame_count = int(
            manifest.get("frameCount") or metadata.frame_count or 0
        )
        fps = int(
            round(float(manifest.get("fps") or metadata.fps or DEFAULT_FPS))
        )
        has_alpha_raw = manifest.get("hasAlpha", metadata.has_alpha)
        has_alpha = (
            bool(has_alpha_raw)
            if isinstance(has_alpha_raw, bool)
            else metadata.has_alpha
        )
        poster_name = str(manifest.get("poster") or "").strip()
        if not poster_name or not (assets / poster_name).is_file():
            _video_default, fallback_poster, _manifest_default = (
                _native_asset_names(asset_family, quality, container)
            )
            poster_name = (
                fallback_poster
                if (assets / fallback_poster).is_file()
                else ""
            )
        found.append(
            NativeVideoAsset(
                family=family,
                quality=quality,
                container=container,
                video=video.name,
                poster=poster_name,
                manifest=manifest_name,
                frame_count=frame_count,
                fps=fps,
                width=width,
                height=height,
                has_alpha=has_alpha,
                codec=str(manifest.get("codec") or metadata.codec or "unknown"),
                total_bytes=video.stat().st_size,
            )
        )
    return tuple(found)


def native_video_source_choices(
    values: dict[str, object],
    *,
    family: str,
    root: Path | None = None,
) -> tuple[tuple[str, str], ...]:
    """Opcje zależne od silnika, kontenera i jakości w edytorze GicleeApp."""

    if str(values.get("scroll_video_engine") or "video") != "video":
        return (("", "Klatki WebP — wybór filmu nieaktywny"),)
    container = str(values.get("scroll_video_container") or "mp4")
    quality = str(values.get("scroll_video_quality") or "720p")
    assets = list_native_video_assets(
        family=family,
        container=container,
        quality=quality,
        root=root,
    )
    default_video, _poster, _manifest = _native_asset_names(
        _family(family), quality, container
    )
    choices: list[tuple[str, str]] = [
        (
            "",
            f"Domyślny slot: {default_video}",
        )
    ]
    choices.extend((item.source_spec, item.label) for item in assets)
    return tuple(choices)


def _library_asset_base(
    source: Path,
    *,
    family: str,
    quality: str,
    container: str,
    video: Path,
) -> str:
    normalized = unicodedata.normalize("NFKD", source.stem)
    ascii_stem = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_stem.lower()).strip("-")
    slug = (slug or "film")[:42].rstrip("-")
    hasher = hashlib.sha256()
    with video.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()[:10]
    return (
        f"giclee-scroll-library-{family}-{quality}-{container}-"
        f"{slug}-{digest}"
    )


def _probe_keyframe_profile(video: Path) -> tuple[int | None, bool | None]:
    """Zwróć największy odstęp klatek kluczowych i informację GOP=1."""
    ffprobe = Path(resolve_ffmpeg_exe()).with_name("ffprobe.exe")
    process = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=key_frame",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        **no_console_kwargs(),
    )
    if process.returncode != 0:
        return None, None
    flags: list[int] = []
    for line in (process.stdout or "").splitlines():
        raw = line.strip().split(",", 1)[0]
        if raw in {"0", "1"}:
            flags.append(int(raw))
    if not flags:
        return None, None
    keyframes = [index for index, flag in enumerate(flags) if flag == 1]
    if not keyframes:
        return len(flags), False
    intervals = [
        right - left for left, right in zip(keyframes, keyframes[1:])
    ]
    tail_interval = len(flags) - keyframes[-1]
    max_interval = max([1, *intervals, tail_interval])
    return max_interval, all(flag == 1 for flag in flags)


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
    container: str = "mp4",
) -> NativeVideoStatus:
    asset = _family(family)
    profile = _profile(quality, family)
    assets = _assets_dir(root)
    video_name, poster_name, manifest_name = _native_asset_names(
        asset,
        quality,
        container,
    )
    manifest_path = assets / manifest_name
    manifest: dict[str, object] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            manifest = {}
    video = assets / video_name
    poster = assets / poster_name
    return NativeVideoStatus(
        quality=quality,
        container=container,
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
        keyframe_interval=(
            int(manifest["keyframeInterval"])
            if manifest.get("keyframeInterval") is not None
            else None
        ),
        intra_only=(
            bool(manifest["intraOnly"])
            if manifest.get("intraOnly") is not None
            else None
        ),
        passthrough=bool(manifest.get("passthrough", False)),
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
        native_names = (
            *_native_asset_names(asset, quality, "mp4"),
            *_native_asset_names(asset, quality, "webm"),
        )
        for name in native_names:
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
    source_codec: str | None = None,
) -> None:
    command = [
        resolve_ffmpeg_exe(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if (
        source.suffix.lower() == ".webm"
        and str(source_codec or "").lower() == "vp9"
    ):
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
    container: str = "mp4",
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
    if container not in {"mp4", "webm"}:
        raise ValueError("Kontener filmu musi mieć wartość mp4 albo webm.")
    if container == "webm" and suffix != ".webm":
        raise ValueError(
            "Tryb gotowego WebM przyjmuje wyłącznie plik z rozszerzeniem .webm."
        )
    source_metadata = _probe_video_metadata(source)
    if container == "webm" and (
        source_metadata.width != profile.width
        or source_metadata.height != profile.height
    ):
        raise ValueError(
            f"Gotowy WebM dla {quality} musi mieć dokładnie "
            f"{profile.width}×{profile.height} px; wykryto "
            f"{source_metadata.width}×{source_metadata.height} px. "
            "Wybierz właściwy slot jakości albo użyj konwersji MP4/WebP."
        )

    assets = _assets_dir(root)
    assets.mkdir(parents=True, exist_ok=True)
    staging = assets.parent / f".giclee-filozofia-video-{uuid4().hex}"
    staging.mkdir()
    try:
        video_name, poster_name, manifest_name = _native_asset_names(
            asset,
            quality,
            container,
        )
        staged_video = staging / video_name
        staged_poster = staging / poster_name
        if container == "webm":
            shutil.copy2(source, staged_video)
        else:
            _run_ffmpeg_native_video(
                source,
                staged_video,
                fps=fps,
                width=profile.width,
                height=profile.height,
                crf=10,
                x264_preset="slow",
            )
        _run_ffmpeg_poster(
            source,
            staged_poster,
            width=profile.width,
            source_codec=source_metadata.codec,
        )
        frame_count = (
            source_metadata.frame_count
            if container == "webm" and source_metadata.frame_count
            else _probe_frame_count(staged_video)
        )
        output_metadata = _probe_video_metadata(staged_video)
        poster_has_alpha = _alpha_state(staged_poster)
        source_has_alpha = (
            True
            if poster_has_alpha is True
            else source_metadata.has_alpha
        )
        output_has_alpha = (
            source_has_alpha is True if container == "webm" else False
        )
        output_fps = (
            int(round(source_metadata.fps))
            if container == "webm" and source_metadata.fps
            else fps
        )
        if not 1 <= output_fps <= 60:
            raise RuntimeError(
                f"Gotowy WebM ma {output_fps} FPS. Film-scroll obsługuje 1–60 FPS."
            )
        if not frame_count or frame_count > MAX_FRAMES:
            raise RuntimeError(
                f"Film zawiera {frame_count} klatek. Maksimum to {MAX_FRAMES}."
            )
        keyframe_interval, intra_only = (
            _probe_keyframe_profile(staged_video)
            if container == "webm"
            else (1, True)
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
        video_path = assets / video_name
        poster_path = assets / poster_name
        shutil.copy2(staged_video, video_path)
        shutil.copy2(staged_poster, poster_path)
        if container == "webm":
            source_path = video_path
        else:
            source_path = assets / f"{asset.source_prefix}{suffix}"
            if source.resolve() != source_path.resolve():
                shutil.copy2(source, source_path)
            elif not source_path.is_file():
                shutil.copy2(source, source_path)

        manifest = {
            "version": 3,
            "mode": "video",
            "family": asset.id,
            "quality": quality,
            "container": container,
            "mimeType": "video/webm" if container == "webm" else "video/mp4",
            "passthrough": container == "webm",
            "frameCount": frame_count,
            "width": profile.width,
            "height": profile.height,
            "fps": output_fps,
            "codec": output_metadata.codec or (
                source_metadata.codec if container == "webm" else "h264"
            ),
            "pixelFormat": output_metadata.pixel_format or (
                source_metadata.pixel_format
                if container == "webm"
                else "yuv420p"
            ),
            "hasAlpha": output_has_alpha,
            "alphaMode": (
                source_metadata.alpha_mode
                if output_has_alpha and source_metadata.alpha_mode != "unknown"
                else "straight" if output_has_alpha else "none"
            ),
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
                source_has_alpha and not output_has_alpha
            ),
            "backgroundMode": "transparent" if output_has_alpha else "color",
            "backgroundValue": "transparent" if output_has_alpha else "#000000",
            "fallbackActive": bool(source_has_alpha and not output_has_alpha),
            "keyframeInterval": keyframe_interval,
            "intraOnly": intra_only,
            "fullSourceFrameUse": (
                True
                if container == "webm"
                else _full_source_frame_use(
                    source_metadata,
                    output_fps=output_fps,
                    output_frames=frame_count,
                )
            ),
            "video": video_path.name,
            "poster": poster_path.name,
            "source": source_path.name,
            "generatedAt": datetime.now(UTC).isoformat(),
        }
        manifest_path = assets / manifest_name
        pending = assets / f".{manifest_path.name}.tmp"
        pending.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        pending.replace(manifest_path)

        # Biblioteka wersji: slot kanoniczny pozostaje dla kompatybilności,
        # a każdy unikalny materiał dostaje stabilny pakiet do późniejszego wyboru.
        library_base = _library_asset_base(
            source,
            family=asset.id,
            quality=quality,
            container=container,
            video=staged_video,
        )
        library_video = assets / f"{library_base}.{container}"
        library_poster = assets / f"{library_base}-poster.webp"
        library_manifest = assets / f"{library_base}-manifest.json"
        shutil.copy2(staged_video, library_video)
        shutil.copy2(staged_poster, library_poster)
        library_data = {
            **manifest,
            "video": library_video.name,
            "poster": library_poster.name,
            "sourceLabel": source.name,
            "libraryAsset": True,
        }
        library_pending = assets / f".{library_manifest.name}.tmp"
        library_pending.write_text(
            json.dumps(library_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        library_pending.replace(library_manifest)
    finally:
        if staging.is_dir() and staging.parent == assets.parent:
            shutil.rmtree(staging, ignore_errors=True)

    return NativeVideoResult(
        quality=quality,
        container=container,
        status=read_native_video_status(
            root,
            quality=quality,
            family=family,
            container=container,
        ),
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
        return (
            f"Film {status.container.upper()} {status.quality}: "
            "brak przygotowanego pliku."
        )
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
    alpha_final = "tak" if status.has_alpha else "nie"
    keyframes = (
        "GOP=1 — optymalny scrub"
        if status.intra_only is True
        else f"klatka kluczowa co maks. {status.keyframe_interval} kl."
        if status.keyframe_interval
        else "odstęp klatek kluczowych: brak danych"
    )
    passthrough = "bez konwersji" if status.passthrough else "po konwersji"
    return (
        f"Film {status.container.upper()} {status.quality}: "
        f"{status.frame_count} klatek · "
        f"{status.fps} FPS · {status.width}×{status.height} · "
        f"{status.duration_seconds:.2f} s · {size_mb:.1f} MB · "
        f"{status.codec}/{status.pixel_format} · alfa finalna: {alpha_final} · "
        f"{passthrough}\n"
        f"Źródło: {source} · FPS: {status.source_fps or 'nieznany'} · "
        f"alfa: {source_alpha} · {fallback} ({status.background_mode}) · "
        f"{frame_use} · {keyframes}"
    )


PARALLAX_IMAGE_SUFFIXES = {".webp", ".png", ".jpg", ".jpeg"}
PARALLAX_MIDDLE_MEDIA_SUFFIXES = PARALLAX_IMAGE_SUFFIXES | {".webm"}
PARALLAX_LAYERS: dict[str, str] = {
    "bottom": "assets/giclee-fm-parallax-bottom.webp",
    "middle": "assets/giclee-fm-parallax-middle.webp",
}
PARALLAX_MIDDLE_WEBM_REL = "assets/giclee-fm-parallax-middle.webm"
PARALLAX_CONFIG_REL = "assets/giclee-fm-parallax-config.json"


@dataclass(frozen=True)
class ParallaxLayerStatus:
    layer: str
    rel_path: str
    exists: bool
    width: int | None
    height: int | None
    size_bytes: int
    mtime_label: str
    kind: str = "image"


def parallax_layer_relpath(layer: str) -> str:
    key = str(layer or "").strip().lower()
    if key not in PARALLAX_LAYERS:
        raise ValueError(f"Nieznana warstwa paralaksy: {layer!r}")
    return PARALLAX_LAYERS[key]


def parallax_deploy_relpaths(*, root: Path | None = None) -> tuple[str, ...]:
    base = root or theme_root()
    paths = [
        *PARALLAX_LAYERS.values(),
        PARALLAX_CONFIG_REL,
        "assets/giclee-fm-wrota-parallax.js",
        "assets/giclee-fm-wrota-parallax.css",
    ]
    if (base / PARALLAX_MIDDLE_WEBM_REL).is_file():
        paths.append(PARALLAX_MIDDLE_WEBM_REL)
    return tuple(paths)


def read_parallax_config(*, root: Path | None = None) -> dict[str, str]:
    path = (root or theme_root()) / PARALLAX_CONFIG_REL
    if not path.is_file():
        return {"middleKind": "image"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"middleKind": "image"}
    kind = str(data.get("middleKind") or "image").strip().lower()
    if kind not in {"image", "webm"}:
        kind = "image"
    return {"middleKind": kind}


def write_parallax_config(
    *,
    middle_kind: str,
    root: Path | None = None,
) -> Path:
    kind = str(middle_kind or "image").strip().lower()
    if kind not in {"image", "webm"}:
        raise ValueError(f"Nieobsługiwany rodzaj Middle: {middle_kind!r}")
    path = (root or theme_root()) / PARALLAX_CONFIG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"middleKind": kind}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


PHILOSOPHY_SCROLL_BG_IMAGE_REL = "assets/giclee-philosophy-scroll-bg.webp"
PHILOSOPHY_SCROLL_BG_WEBM_REL = "assets/giclee-philosophy-scroll-bg.webm"
PHILOSOPHY_SCROLL_BG_SUFFIXES = {".webp", ".png", ".jpg", ".jpeg", ".webm"}


@dataclass(frozen=True)
class PhilosophyScrollBgStatus:
    kind: str
    rel_path: str
    exists: bool
    width: int | None
    height: int | None
    size_bytes: int
    mtime_label: str


def philosophy_scroll_bg_deploy_relpaths(
    *, root: Path | None = None
) -> tuple[str, ...]:
    base = root or theme_root()
    paths: list[str] = []
    if (base / PHILOSOPHY_SCROLL_BG_IMAGE_REL).is_file():
        paths.append(PHILOSOPHY_SCROLL_BG_IMAGE_REL)
    if (base / PHILOSOPHY_SCROLL_BG_WEBM_REL).is_file():
        paths.append(PHILOSOPHY_SCROLL_BG_WEBM_REL)
    return tuple(paths)


def read_philosophy_scroll_bg_status(
    *,
    kind: str | None = None,
    root: Path | None = None,
) -> PhilosophyScrollBgStatus:
    base = root or theme_root()
    resolved_kind = str(kind or "").strip().lower()
    if resolved_kind not in {"asset", "webm", "image"}:
        # Prefer webm if present, else image.
        if (base / PHILOSOPHY_SCROLL_BG_WEBM_REL).is_file():
            resolved_kind = "webm"
        elif (base / PHILOSOPHY_SCROLL_BG_IMAGE_REL).is_file():
            resolved_kind = "asset"
        else:
            resolved_kind = "none"
    if resolved_kind == "image":
        resolved_kind = "asset"

    if resolved_kind == "webm":
        rel_path = PHILOSOPHY_SCROLL_BG_WEBM_REL
    elif resolved_kind == "asset":
        rel_path = PHILOSOPHY_SCROLL_BG_IMAGE_REL
    else:
        return PhilosophyScrollBgStatus(
            kind="none",
            rel_path=PHILOSOPHY_SCROLL_BG_IMAGE_REL,
            exists=False,
            width=None,
            height=None,
            size_bytes=0,
            mtime_label="brak pliku",
        )

    path = base / rel_path
    if not path.is_file():
        return PhilosophyScrollBgStatus(
            kind=resolved_kind,
            rel_path=rel_path,
            exists=False,
            width=None,
            height=None,
            size_bytes=0,
            mtime_label="brak pliku",
        )

    width = height = None
    if resolved_kind == "asset":
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            pass
    else:
        try:
            meta = _probe_video_metadata(path)
            width, height = meta.width, meta.height
        except Exception:
            pass
    mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return PhilosophyScrollBgStatus(
        kind=resolved_kind,
        rel_path=rel_path,
        exists=True,
        width=width,
        height=height,
        size_bytes=path.stat().st_size,
        mtime_label=mtime,
    )


def format_philosophy_scroll_bg_status(status: PhilosophyScrollBgStatus) -> str:
    if status.kind == "none" or not status.exists:
        return "Tło scrolla: brak pliku"
    kind_label = "WebM + alfa" if status.kind == "webm" else "obraz"
    size_kb = status.size_bytes / 1024
    size = (
        f"{size_kb / 1024:.1f} MB"
        if size_kb >= 1024
        else f"{size_kb:.0f} KB"
    )
    dims = (
        f"{status.width}×{status.height}"
        if status.width and status.height
        else "rozmiar nieznany"
    )
    return (
        f"Tło scrolla ({kind_label}): {dims} · {size} · {status.mtime_label}\n"
        f"  {status.rel_path}"
    )


def replace_philosophy_scroll_bg(
    source: Path,
    *,
    root: Path | None = None,
) -> tuple[Path, str]:
    """Podmienia tło pierwszego Film-scroll (obraz → webp, WebM 1:1).

    Zwraca (dest_path, mode) gdzie mode to ``asset`` albo ``webm``.
    """
    source = Path(source)
    suffix = source.suffix.lower()
    if suffix not in PHILOSOPHY_SCROLL_BG_SUFFIXES:
        raise ValueError(
            "Wybierz plik WebP, PNG, JPG albo WebM z alfą "
            f"(otrzymano {source.suffix or 'bez rozszerzenia'})."
        )
    if not source.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku: {source}")

    base = root or theme_root()
    base.joinpath("assets").mkdir(parents=True, exist_ok=True)

    if suffix == ".webm":
        dest = base / PHILOSOPHY_SCROLL_BG_WEBM_REL
        shutil.copy2(source, dest)
        return dest, "webm"

    dest = base / PHILOSOPHY_SCROLL_BG_IMAGE_REL
    if suffix == ".webp":
        shutil.copy2(source, dest)
    else:
        with Image.open(source) as image:
            image.convert("RGB").save(dest, "WEBP", quality=90, method=6)
    return dest, "asset"


def clear_philosophy_scroll_bg(*, root: Path | None = None) -> None:
    base = root or theme_root()
    for rel in (PHILOSOPHY_SCROLL_BG_IMAGE_REL, PHILOSOPHY_SCROLL_BG_WEBM_REL):
        path = base / rel
        if path.is_file():
            path.unlink()


def read_parallax_layer_status(
    layer: str,
    *,
    root: Path | None = None,
) -> ParallaxLayerStatus:
    base = root or theme_root()
    cfg = read_parallax_config(root=base)
    kind = "image"
    rel_path = parallax_layer_relpath(layer)
    if layer == "middle" and cfg.get("middleKind") == "webm":
        kind = "webm"
        rel_path = PARALLAX_MIDDLE_WEBM_REL
    path = base / rel_path
    if not path.is_file():
        return ParallaxLayerStatus(
            layer=layer,
            rel_path=rel_path,
            exists=False,
            width=None,
            height=None,
            size_bytes=0,
            mtime_label="brak pliku",
            kind=kind,
        )
    width = height = None
    if kind == "image":
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            pass
    else:
        try:
            meta = _probe_video_metadata(path)
            width, height = meta.width, meta.height
        except Exception:
            pass
    mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return ParallaxLayerStatus(
        layer=layer,
        rel_path=rel_path,
        exists=True,
        width=width,
        height=height,
        size_bytes=path.stat().st_size,
        mtime_label=mtime,
        kind=kind,
    )


def format_parallax_layer_status(status: ParallaxLayerStatus) -> str:
    label = "Bottom" if status.layer == "bottom" else "Middle"
    kind_label = "WebM + alfa" if status.kind == "webm" else "obraz"
    if not status.exists:
        return f"{label} ({kind_label}): brak pliku ({status.rel_path})"
    size_kb = status.size_bytes / 1024
    size = (
        f"{size_kb / 1024:.1f} MB"
        if size_kb >= 1024
        else f"{size_kb:.0f} KB"
    )
    dims = (
        f"{status.width}×{status.height}"
        if status.width and status.height
        else "rozmiar nieznany"
    )
    return (
        f"{label} ({kind_label}): {dims} · {size} · {status.mtime_label}\n"
        f"  {status.rel_path}"
    )


def replace_parallax_layer(
    source: Path,
    *,
    layer: str,
    root: Path | None = None,
) -> Path:
    """Podmienia warstwę Bottom/Middle paralaksy po Wrotach (stała nazwa w assets)."""
    layer_key = str(layer or "").strip().lower()
    if layer_key not in PARALLAX_LAYERS:
        raise ValueError(f"Nieznana warstwa paralaksy: {layer!r}")

    source = Path(source)
    suffix = source.suffix.lower()
    allowed = (
        PARALLAX_MIDDLE_MEDIA_SUFFIXES
        if layer_key == "middle"
        else PARALLAX_IMAGE_SUFFIXES
    )
    if suffix not in allowed:
        raise ValueError(
            "Wybierz plik WebP, PNG lub JPG"
            + (" albo WebM z alfą" if layer_key == "middle" else "")
            + f" (otrzymano {source.suffix or 'bez rozszerzenia'})."
        )
    if not source.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku: {source}")

    base = root or theme_root()
    base.joinpath("assets").mkdir(parents=True, exist_ok=True)

    if layer_key == "middle" and suffix == ".webm":
        dest = base / PARALLAX_MIDDLE_WEBM_REL
        shutil.copy2(source, dest)
        write_parallax_config(middle_kind="webm", root=base)
        return dest

    rel_path = PARALLAX_LAYERS[layer_key]
    dest = base / rel_path
    if suffix == ".webp":
        shutil.copy2(source, dest)
    else:
        with Image.open(source) as image:
            converted = image.convert("RGBA" if layer_key == "middle" else "RGB")
            converted.save(dest, "WEBP", quality=90, method=6)

    if layer_key == "middle":
        write_parallax_config(middle_kind="image", root=base)
        webm = base / PARALLAX_MIDDLE_WEBM_REL
        if webm.is_file():
            webm.unlink()

    return dest


__all__ = [
    "ASSET_FAMILIES",
    "NativeVideoResult",
    "NativeVideoAsset",
    "NativeVideoStatus",
    "ParallaxLayerStatus",
    "ReplaceResult",
    "SequenceStatus",
    "VariantsReplaceResult",
    "activate_selected_video_sources",
    "active_scroll_video_deploy_relpaths",
    "active_scroll_video_frame_globs",
    "all_scroll_video_runtime_relpaths",
    "apply_scroll_video_selection",
    "format_parallax_layer_status",
    "format_philosophy_scroll_bg_status",
    "format_status",
    "format_native_video_status",
    "inactive_scroll_video_relpaths",
    "iter_scroll_video_block_settings",
    "list_native_video_assets",
    "native_video_source_choices",
    "parallax_deploy_relpaths",
    "parallax_layer_relpath",
    "parse_native_video_source_spec",
    "philosophy_scroll_bg_deploy_relpaths",
    "clear_philosophy_scroll_bg",
    "read_parallax_config",
    "read_parallax_layer_status",
    "read_philosophy_scroll_bg_status",
    "sync_philosophy_scroll_bg_mode",
    "read_native_video_status",
    "read_sequence_status",
    "replace_parallax_layer",
    "replace_philosophy_scroll_bg",
    "replace_native_video",
    "replace_video_sequence",
    "replace_video_variants",
    "sync_scroll_video_shopifyignore",
    "write_parallax_config",
]
