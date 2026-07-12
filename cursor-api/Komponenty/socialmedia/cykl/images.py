"""Image management for the Social Media cycle."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import storage

ACCEPTED_EXTS = (".jpg", ".jpeg", ".png", ".webp")
_MOCKUP_RE = re.compile(r"mockup", re.IGNORECASE)
_PL_MAP = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ",
)


def slugify(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    v = v.translate(_PL_MAP)
    v = re.sub(r"[^A-Za-z0-9]+", "-", v).strip("-").lower()
    return v or ""


@dataclass
class ImageSet:
    main: str = ""
    zooms: list[str] = field(default_factory=list)
    mockup: str = ""
    other: list[str] = field(default_factory=list)

    def has_main(self) -> bool:
        return bool(self.main)

    def has_any_zoom(self) -> bool:
        return len(self.zooms) > 0

    def has_mockup(self) -> bool:
        return bool(self.mockup)

    def all_for_ig_carousel(self) -> list[str]:
        out: list[str] = []
        if self.main:
            out.append(self.main)
        out.extend(sorted(self.zooms))
        if self.mockup:
            out.append(self.mockup)
        return out


def painting_dir_rel(artist_handle: str, painting_handle: str) -> str:
    ah = artist_handle or "unknown"
    ph = painting_handle or "unknown"
    return f"{ah}/{ph}"


def painting_dir_abs(
    artist_handle: str,
    painting_handle: str,
    *,
    for_write: bool = False,
) -> Path:
    rel = painting_dir_rel(artist_handle, painting_handle)
    return storage.images_dir(for_write=for_write) / rel


def ensure_painting_dir(artist_handle: str, painting_handle: str) -> Path:
    p = painting_dir_abs(artist_handle, painting_handle, for_write=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_images_for(artist_handle: str, painting_handle: str) -> ImageSet:
    p = painting_dir_abs(artist_handle, painting_handle)
    out = ImageSet()
    if not p.is_dir():
        return out
    rel_prefix = painting_dir_rel(artist_handle, painting_handle)
    for f in sorted(p.iterdir()):
        if not f.is_file() or f.suffix.lower() not in ACCEPTED_EXTS:
            continue
        name = f.name
        stem = f.stem
        rel = f"{rel_prefix}/{name}"
        if _MOCKUP_RE.search(stem):
            if not out.mockup:
                out.mockup = rel
            else:
                out.other.append(rel)
            continue
        if stem.lower() == "main":
            if not out.main:
                out.main = rel
            else:
                out.other.append(rel)
            continue
        out.zooms.append(rel)
    return out


def resolve_abs(rel_path: str, *, for_write: bool = False) -> Path:
    return storage.images_dir(for_write=for_write) / rel_path


def copy_into(
    source: Path,
    artist_handle: str,
    painting_handle: str,
    *,
    role: str = "zoom",
    target_name: str | None = None,
) -> str:
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in ACCEPTED_EXTS:
        raise ValueError(f"Niedozwolone rozszerzenie: {source.suffix} (akceptowane: {ACCEPTED_EXTS})")

    target_dir = ensure_painting_dir(artist_handle, painting_handle)

    if target_name is None:
        if role == "main":
            target_name = f"main{source.suffix.lower()}"
        elif role == "mockup":
            stem = source.stem
            if not _MOCKUP_RE.search(stem):
                stem = f"{stem}_MOCKUP"
            target_name = f"{stem}{source.suffix.lower()}"
        else:
            target_name = source.name

    target = target_dir / target_name
    if role == "zoom" and target.exists() and target.resolve() != source.resolve():
        i = 1
        stem = Path(target_name).stem
        ext = Path(target_name).suffix
        while True:
            candidate = target_dir / f"{stem} ({i}){ext}"
            if not candidate.exists():
                target = candidate
                break
            i += 1

    if source.resolve() != target.resolve():
        shutil.copy2(source, target)

    return f"{painting_dir_rel(artist_handle, painting_handle)}/{target.name}"


def delete_image(rel_path: str) -> bool:
    if not rel_path:
        return False
    # Deletion is allowed only in the external writable image root. A legacy
    # source-tree fallback is never removed by Stage 1E.
    p = resolve_abs(rel_path, for_write=True)
    try:
        if p.is_file():
            p.unlink()
            return True
    except OSError:
        return False
    return False


@dataclass
class MissingReport:
    item_id: str
    artist: str
    title_pl: str
    scheduled_at: str
    has_main: bool
    zooms_count: int
    has_mockup: bool

    def missing_labels(self) -> list[str]:
        out: list[str] = []
        if not self.has_main:
            out.append("main")
        if self.zooms_count == 0:
            out.append("min 1 zoom")
        if not self.has_mockup:
            out.append("MOCKUP")
        return out


def missing_report(items: list[storage.CykleItem]) -> list[MissingReport]:
    reports: list[MissingReport] = []
    for it in items:
        if it.status in ("done", "skipped"):
            continue
        im = list_images_for(it.artist_handle, it.painting_handle)
        reports.append(
            MissingReport(
                item_id=it.id,
                artist=it.artist,
                title_pl=it.painting_title_pl,
                scheduled_at=it.scheduled_at,
                has_main=im.has_main() or bool(it.product_image_url),
                zooms_count=len(im.zooms),
                has_mockup=im.has_mockup(),
            )
        )
    return reports


def sync_item_images(item: storage.CykleItem) -> None:
    im = list_images_for(item.artist_handle, item.painting_handle)
    item.image_main = im.main
    item.image_zooms = sorted(im.zooms)
    item.image_mockup = im.mockup

    def _is_empty(main: str, zooms: list[str], mockup: str) -> bool:
        return not (main or zooms or mockup)

    if _is_empty(item.image_fb_main, item.image_fb_zooms, item.image_fb_mockup):
        item.image_fb_main = im.main
        item.image_fb_zooms = sorted(im.zooms)
        item.image_fb_mockup = im.mockup

    if _is_empty(item.image_ig_main, item.image_ig_zooms, item.image_ig_mockup):
        item.image_ig_main = im.main
        item.image_ig_zooms = sorted(im.zooms)
        item.image_ig_mockup = im.mockup

    if not item.image_ig_main and item.image_ig_pl:
        old = list(item.image_ig_pl)
        if old:
            item.image_ig_main = old[0]
            last = old[-1] if len(old) > 1 else ""
            if last and "mockup" in last.lower():
                item.image_ig_mockup = last
                item.image_ig_zooms = old[1:-1]
            else:
                item.image_ig_zooms = old[1:]
    if not item.image_fb_main and item.image_fb_pl:
        item.image_fb_main = item.image_fb_pl


def open_images_folder() -> Path:
    return storage.images_dir()
