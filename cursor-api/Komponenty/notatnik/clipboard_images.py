"""Bezpieczne helpery grafik osadzanych w notatkach Markdown."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal
from urllib.parse import unquote

ASSETS_DIR_NAME = ".assets"
SUPPORTED_IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
}

_IMAGE_TOKEN_RE = re.compile(r"!\[([^\]]*)\]\(([^)\r\n]+)\)")
_IMAGE_LINE_RE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)\r\n]+)\)\s*$")

RenderSegmentKind = Literal["markdown", "image"]


def _normalise_target(raw_target: str) -> str:
    target = unquote((raw_target or "").strip())
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    return target


def _is_remote_target(target: str) -> bool:
    lowered = target.casefold()
    return (
        "://" in target
        or lowered.startswith("data:")
        or lowered.startswith("mailto:")
        or lowered.startswith("#")
    )


def resolve_local_image(
    note_path: Path,
    raw_target: str,
    notes_dir: Path,
    *,
    require_exists: bool = True,
) -> Path | None:
    """Rozwiazuje lokalny obraz tylko wtedy, gdy pozostaje w katalogu Notatnika."""
    target = _normalise_target(raw_target)
    if not target or _is_remote_target(target):
        return None

    candidate = Path(target.replace("/", os.sep))
    if not candidate.is_absolute():
        candidate = Path(note_path).parent / candidate

    try:
        resolved = candidate.resolve()
        root = Path(notes_dir).resolve()
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None

    if resolved.suffix.casefold() not in SUPPORTED_IMAGE_SUFFIXES:
        return None
    if require_exists and not resolved.is_file():
        return None
    return resolved


def make_asset_destination(
    notes_dir: Path,
    *,
    now: datetime | None = None,
    token: str | None = None,
) -> Path:
    """Tworzy unikalna docelowa sciezke PNG w ukrytym katalogu `.assets`."""
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
    unique = (token or uuid.uuid4().hex[:8]).strip() or uuid.uuid4().hex[:8]
    return Path(notes_dir) / ASSETS_DIR_NAME / f"paste-{timestamp}-{unique}.png"


def markdown_image_reference(note_path: Path, image_path: Path, alt: str = "Wklejona grafika") -> str:
    """Buduje przenosny, wzgledny zapis Markdown dla grafiki."""
    relative = os.path.relpath(Path(image_path), start=Path(note_path).parent)
    relative_posix = Path(relative).as_posix()
    clean_alt = (alt or "Grafika").replace("]", "").strip() or "Grafika"
    return f"![{clean_alt}]({relative_posix})"


def iter_render_segments(content: str) -> Iterator[tuple[RenderSegmentKind, str, str]]:
    """Dzieli Markdown na zwykle fragmenty i samodzielne linie z obrazami."""
    markdown_buffer: list[str] = []

    def flush() -> Iterator[tuple[RenderSegmentKind, str, str]]:
        if markdown_buffer:
            yield "markdown", "".join(markdown_buffer), ""
            markdown_buffer.clear()

    for line in content.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        match = _IMAGE_LINE_RE.match(stripped)
        if match:
            yield from flush()
            yield "image", match.group(1), match.group(2)
            if line.endswith(("\n", "\r")):
                yield "markdown", "\n", ""
        else:
            markdown_buffer.append(line)
    yield from flush()


def rewrite_local_image_links_for_move(
    content: str,
    old_note_path: Path,
    new_note_path: Path,
    notes_dir: Path,
) -> str:
    """Zachowuje lokalne odwolania do grafik po przeniesieniu notatki."""
    if Path(old_note_path).parent.resolve() == Path(new_note_path).parent.resolve():
        return content

    def replace(match: re.Match[str]) -> str:
        alt, raw_target = match.group(1), match.group(2)
        absolute = resolve_local_image(
            old_note_path,
            raw_target,
            notes_dir,
            require_exists=False,
        )
        if absolute is None:
            return match.group(0)
        relative = os.path.relpath(absolute, start=Path(new_note_path).parent)
        return f"![{alt}]({Path(relative).as_posix()})"

    return _IMAGE_TOKEN_RE.sub(replace, content)


__all__ = [
    "ASSETS_DIR_NAME",
    "SUPPORTED_IMAGE_SUFFIXES",
    "iter_render_segments",
    "make_asset_destination",
    "markdown_image_reference",
    "resolve_local_image",
    "rewrite_local_image_links_for_move",
]
