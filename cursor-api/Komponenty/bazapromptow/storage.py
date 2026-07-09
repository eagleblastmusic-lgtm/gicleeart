"""Trwaly zapis promptow w JSON."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
PROMPTS_FILE = DATA_DIR / "prompts.json"
CONTEXT_IMAGES_DIR = DATA_DIR / "context_images"
CONTEXT_FILES_DIR = DATA_DIR / "context_files"
CONTEXT_VIDEOS_DIR = DATA_DIR / "context_videos"
CONTEXT_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
CONTEXT_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v", ".wmv"}
CONTEXT_FILE_BLOCKED_SUFFIXES = {
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".msi",
    ".scr",
    ".pif",
    ".vbs",
    ".wsf",
    ".dll",
}
MAX_CONTEXT_FILE_BYTES = 50 * 1024 * 1024
MAX_CONTEXT_VIDEO_BYTES = 200 * 1024 * 1024

HOVER_PREVIEW_IMAGE = "image"
HOVER_PREVIEW_VIDEO = "video"
HOVER_PREVIEW_KINDS = {HOVER_PREVIEW_IMAGE, HOVER_PREVIEW_VIDEO}
MIN_VIDEO_PREVIEW_SEGMENT_SEC = 0.2
DEFAULT_VIDEO_PREVIEW_END_SEC = 3.0

FOLDER_ALL = "__all__"
FOLDER_UNCATEGORIZED = "__none__"
DEFAULT_FOLDER_ID = "strona-glowna"
DEFAULT_FOLDER_LABEL = "Strona Główna"


@dataclass
class FolderEntry:
    id: str
    label: str
    sort_key: int = 0
    parent_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "sort_key": self.sort_key,
        }
        if self.parent_id.strip():
            row["parent_id"] = self.parent_id
        return row

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> FolderEntry:
        return cls(
            id=str(row.get("id") or uuid.uuid4().hex[:12]),
            label=str(row.get("label") or "").strip(),
            sort_key=int(row.get("sort_key") or 0),
            parent_id=str(row.get("parent_id") or "").strip(),
        )


@dataclass
class PromptEntry:
    id: str
    label: str
    text: str
    sort_key: int = 0
    context: str = ""
    folder_id: str = ""
    context_images: list[str] = field(default_factory=list)
    context_files: list[str] = field(default_factory=list)
    context_videos: list[str] = field(default_factory=list)
    context_hover_preview: str = HOVER_PREVIEW_IMAGE
    context_video_preview_start_sec: float = 0.0
    context_video_preview_end_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "text": self.text,
            "sort_key": self.sort_key,
        }
        if self.context.strip():
            row["context"] = self.context
        if self.folder_id.strip():
            row["folder_id"] = self.folder_id
        if self.context_images:
            row["context_images"] = list(self.context_images)
        if self.context_files:
            row["context_files"] = list(self.context_files)
        if self.context_videos:
            row["context_videos"] = list(self.context_videos)
        preview = self.context_hover_preview.strip().lower()
        if preview in HOVER_PREVIEW_KINDS and preview != HOVER_PREVIEW_IMAGE:
            row["context_hover_preview"] = preview
        if self.context_video_preview_start_sec > 0:
            row["context_video_preview_start_sec"] = round(self.context_video_preview_start_sec, 2)
        if self.context_video_preview_end_sec > 0:
            row["context_video_preview_end_sec"] = round(self.context_video_preview_end_sec, 2)
        return row

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> PromptEntry:
        raw_images = row.get("context_images")
        context_images: list[str] = []
        if isinstance(raw_images, list):
            context_images = [str(x).strip() for x in raw_images if str(x).strip()]
        raw_files = row.get("context_files")
        context_files: list[str] = []
        if isinstance(raw_files, list):
            context_files = [str(x).strip() for x in raw_files if str(x).strip()]
        raw_videos = row.get("context_videos")
        context_videos: list[str] = []
        if isinstance(raw_videos, list):
            context_videos = [str(x).strip() for x in raw_videos if str(x).strip()]
        preview = str(row.get("context_hover_preview") or HOVER_PREVIEW_IMAGE).strip().lower()
        if preview not in HOVER_PREVIEW_KINDS:
            preview = HOVER_PREVIEW_IMAGE
        try:
            start_sec = float(row.get("context_video_preview_start_sec") or 0.0)
        except (TypeError, ValueError):
            start_sec = 0.0
        try:
            end_sec = float(row.get("context_video_preview_end_sec") or 0.0)
        except (TypeError, ValueError):
            end_sec = 0.0
        return cls(
            id=str(row.get("id") or uuid.uuid4().hex[:12]),
            label=str(row.get("label") or "").strip(),
            text=str(row.get("text") or ""),
            sort_key=int(row.get("sort_key") or 0),
            context=str(row.get("context") or ""),
            folder_id=str(row.get("folder_id") or "").strip(),
            context_images=context_images,
            context_files=context_files,
            context_videos=context_videos,
            context_hover_preview=preview,
            context_video_preview_start_sec=max(0.0, start_sec),
            context_video_preview_end_sec=max(0.0, end_sec),
        )


@dataclass
class PromptStore:
    prompts: list[PromptEntry] = field(default_factory=list)
    folders: list[FolderEntry] = field(default_factory=list)

    def sorted(self) -> list[PromptEntry]:
        return sorted(self.prompts, key=lambda p: (p.sort_key, p.label.lower()))

    def sorted_folders(self) -> list[FolderEntry]:
        return self.folder_tree_rows()

    def folder_children(self, parent_id: str = "") -> list[FolderEntry]:
        return sorted(
            [f for f in self.folders if f.parent_id == parent_id],
            key=lambda f: (f.sort_key, f.label.lower()),
        )

    def folder_tree_rows(self) -> list[FolderEntry]:
        return [folder for folder, _depth in self.folder_tree_with_depth()]

    def folder_tree_with_depth(self) -> list[tuple[FolderEntry, int]]:
        rows: list[tuple[FolderEntry, int]] = []

        def walk(parent_id: str, depth: int) -> None:
            for folder in self.folder_children(parent_id):
                rows.append((folder, depth))
                walk(folder.id, depth + 1)

        walk("", 0)
        return rows

    def descendant_folder_ids(self, folder_id: str) -> set[str]:
        ids = {folder_id}
        for child in self.folder_children(folder_id):
            ids |= self.descendant_folder_ids(child.id)
        return ids

    def is_descendant_of(self, folder_id: str, ancestor_id: str) -> bool:
        if not folder_id or not ancestor_id:
            return False
        current = folder_id
        visited: set[str] = set()
        while current:
            if current == ancestor_id:
                return True
            if current in visited:
                return False
            visited.add(current)
            folder = self.find_folder(current)
            if not folder:
                return False
            current = folder.parent_id
        return False

    def folder_path_label(self, folder_id: str) -> str:
        folder = self.find_folder(folder_id)
        if not folder:
            return folder_id
        parts = [folder.label]
        current = folder.parent_id
        visited: set[str] = set()
        while current:
            if current in visited:
                break
            visited.add(current)
            parent = self.find_folder(current)
            if not parent:
                break
            parts.insert(0, parent.label)
            current = parent.parent_id
        return " / ".join(parts)

    def normalize_folders(self) -> None:
        valid_ids = {f.id for f in self.folders}
        for folder in self.folders:
            if folder.parent_id and folder.parent_id not in valid_ids:
                folder.parent_id = ""
            if folder.parent_id == folder.id:
                folder.parent_id = ""

    def find_folder(self, folder_id: str) -> FolderEntry | None:
        for folder in self.folders:
            if folder.id == folder_id:
                return folder
        return None

    def prompts_in_view(self, view_id: str) -> list[PromptEntry]:
        prompts = self.sorted()
        if view_id == FOLDER_ALL:
            return prompts
        if view_id == FOLDER_UNCATEGORIZED:
            return [p for p in prompts if not p.folder_id]
        return [p for p in prompts if p.folder_id == view_id]

    def count_in_view(self, view_id: str) -> int:
        return len(self.prompts_in_view(view_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 3,
            "folders": [f.to_dict() for f in self.folder_tree_rows()],
            "prompts": [p.to_dict() for p in self.prompts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptStore:
        raw_prompts = data.get("prompts") if isinstance(data.get("prompts"), list) else []
        prompts: list[PromptEntry] = []
        for row in raw_prompts:
            if isinstance(row, dict):
                prompts.append(PromptEntry.from_dict(row))

        raw_folders = data.get("folders") if isinstance(data.get("folders"), list) else []
        folders: list[FolderEntry] = []
        for row in raw_folders:
            if isinstance(row, dict):
                folders.append(FolderEntry.from_dict(row))

        store = cls(prompts=prompts, folders=folders)
        store.normalize_folders()
        return ensure_default_folders(store)


def default_folder() -> FolderEntry:
    return FolderEntry(id=DEFAULT_FOLDER_ID, label=DEFAULT_FOLDER_LABEL, sort_key=0)


def ensure_default_folders(store: PromptStore) -> PromptStore:
    if not any(f.id == DEFAULT_FOLDER_ID for f in store.folders):
        store.folders.append(default_folder())
    return store


def load_prompts() -> PromptStore:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROMPTS_FILE.is_file():
        return ensure_default_folders(PromptStore())
    try:
        data = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return PromptStore.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return ensure_default_folders(PromptStore())


def save_prompts(store: PromptStore) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_FILE.write_text(
        json.dumps(store.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def new_prompt_id() -> str:
    return uuid.uuid4().hex[:12]


def next_sort_key(store: PromptStore) -> int:
    if not store.prompts:
        return 0
    return max(p.sort_key for p in store.prompts) + 1


def next_folder_sort_key(store: PromptStore, parent_id: str = "") -> int:
    siblings = store.folder_children(parent_id)
    if not siblings:
        return 0
    return max(f.sort_key for f in siblings) + 1


def new_folder_id() -> str:
    return uuid.uuid4().hex[:12]


def normalize_video_preview_range(
    start_sec: float,
    end_sec: float,
    *,
    duration: float | None = None,
) -> tuple[float, float]:
    """Zwraca (start, end) w sekundach; end=0 oznacza domyslny koniec od startu."""
    start = max(0.0, float(start_sec))
    if end_sec <= 0:
        end = start + DEFAULT_VIDEO_PREVIEW_END_SEC
    else:
        end = float(end_sec)
    if duration is not None and duration > 0:
        end = min(end, duration)
    if end <= start:
        end = start + MIN_VIDEO_PREVIEW_SEGMENT_SEC
        if duration is not None and duration > 0:
            end = min(end, duration)
    if end <= start:
        end = start + MIN_VIDEO_PREVIEW_SEGMENT_SEC
    return round(start, 2), round(end, 2)


def context_image_path(rel_path: str) -> Path:
    return DATA_DIR / rel_path.replace("\\", "/")


def context_file_path(rel_path: str) -> Path:
    return context_image_path(rel_path)


def _validate_context_file_source(source: Path) -> None:
    if not source.is_file():
        raise ValueError(f"Plik nie istnieje: {source}")
    suffix = source.suffix.lower()
    if suffix in CONTEXT_FILE_BLOCKED_SUFFIXES:
        raise ValueError(f"Niedozwolony typ pliku: {suffix}")
    if suffix in CONTEXT_VIDEO_SUFFIXES:
        raise ValueError("To jest film — użyj sekcji «Filmiki kontekstu».")
    size = source.stat().st_size
    if size > MAX_CONTEXT_FILE_BYTES:
        raise ValueError(
            f"Plik jest za duży ({size // (1024 * 1024)} MB, limit {MAX_CONTEXT_FILE_BYTES // (1024 * 1024)} MB)",
        )


def _validate_context_video_source(source: Path) -> None:
    if not source.is_file():
        raise ValueError(f"Plik nie istnieje: {source}")
    suffix = source.suffix.lower()
    if suffix not in CONTEXT_VIDEO_SUFFIXES:
        allowed = ", ".join(sorted(CONTEXT_VIDEO_SUFFIXES))
        raise ValueError(f"Nieobsługiwany format wideo. Dozwolone: {allowed}")
    size = source.stat().st_size
    if size > MAX_CONTEXT_VIDEO_BYTES:
        raise ValueError(
            f"Film jest za duży ({size // (1024 * 1024)} MB, limit {MAX_CONTEXT_VIDEO_BYTES // (1024 * 1024)} MB)",
        )


def import_context_image(prompt_id: str, source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix not in CONTEXT_IMAGE_SUFFIXES:
        allowed = ", ".join(sorted(CONTEXT_IMAGE_SUFFIXES))
        raise ValueError(f"Nieobsługiwany format obrazu. Dozwolone: {allowed}")
    if not source.is_file():
        raise ValueError(f"Plik nie istnieje: {source}")
    dest_dir = CONTEXT_IMAGES_DIR / prompt_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{uuid.uuid4().hex[:12]}{suffix}"
    rel = f"context_images/{prompt_id}/{dest_name}"
    dest = context_image_path(rel)
    shutil.copy2(source, dest)
    return rel


def import_context_image_pil(prompt_id: str, image: object) -> str:
    """Zapisuje obraz PIL jako PNG w katalogu kontekstu promptu."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Brak Pillow — zainstaluj: pip install Pillow") from exc

    if not isinstance(image, Image.Image):
        raise TypeError("Oczekiwano obrazu PIL.Image")
    dest_dir = CONTEXT_IMAGES_DIR / prompt_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{uuid.uuid4().hex[:12]}.png"
    rel = f"context_images/{prompt_id}/{dest_name}"
    dest = context_image_path(rel)
    to_save = image
    if to_save.mode not in ("RGB", "RGBA", "L"):
        to_save = to_save.convert("RGB")
    to_save.save(dest, format="PNG")
    return rel


def import_context_file(prompt_id: str, source: Path) -> str:
    _validate_context_file_source(source)
    suffix = source.suffix.lower()
    if suffix in CONTEXT_IMAGE_SUFFIXES:
        raise ValueError("To jest grafika — użyj sekcji «Grafiki kontekstu».")
    dest_dir = CONTEXT_FILES_DIR / prompt_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem[:48] or "plik"
    safe_stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    dest_name = f"{safe_stem}_{uuid.uuid4().hex[:8]}{suffix or '.bin'}"
    rel = f"context_files/{prompt_id}/{dest_name}"
    dest = context_file_path(rel)
    shutil.copy2(source, dest)
    return rel


def import_context_video(prompt_id: str, source: Path) -> str:
    _validate_context_video_source(source)
    suffix = source.suffix.lower()
    dest_dir = CONTEXT_VIDEOS_DIR / prompt_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{uuid.uuid4().hex[:12]}{suffix}"
    rel = f"context_videos/{prompt_id}/{dest_name}"
    dest = context_video_path(rel)
    shutil.copy2(source, dest)
    try:
        from .media_preview import extract_video_poster

        extract_video_poster(dest, context_video_poster_path(rel))
    except Exception:
        pass
    return rel


def delete_context_image_file(rel_path: str) -> None:
    path = context_image_path(rel_path)
    if path.is_file():
        path.unlink(missing_ok=True)
    prompt_dir = path.parent
    if prompt_dir.is_dir() and prompt_dir != CONTEXT_IMAGES_DIR:
        try:
            next(prompt_dir.iterdir())
        except StopIteration:
            prompt_dir.rmdir()


def delete_context_file(rel_path: str) -> None:
    path = context_file_path(rel_path)
    if path.is_file():
        path.unlink(missing_ok=True)
    prompt_dir = path.parent
    if prompt_dir.is_dir() and prompt_dir != CONTEXT_FILES_DIR:
        try:
            next(prompt_dir.iterdir())
        except StopIteration:
            prompt_dir.rmdir()


def context_video_path(rel_path: str) -> Path:
    return context_file_path(rel_path)


def context_video_poster_path(video_rel: str) -> Path:
    video = context_video_path(video_rel)
    return video.with_name(f"{video.stem}_poster.jpg")


def delete_context_video_file(rel_path: str) -> None:
    path = context_video_path(rel_path)
    poster = context_video_poster_path(rel_path)
    if poster.is_file():
        poster.unlink(missing_ok=True)
    if path.is_file():
        path.unlink(missing_ok=True)
    prompt_dir = path.parent
    if prompt_dir.is_dir() and prompt_dir != CONTEXT_VIDEOS_DIR:
        try:
            next(prompt_dir.iterdir())
        except StopIteration:
            prompt_dir.rmdir()


def delete_prompt_context_videos(prompt_id: str, videos: list[str] | None = None) -> None:
    if videos:
        for rel in videos:
            delete_context_video_file(rel)
    prompt_dir = CONTEXT_VIDEOS_DIR / prompt_id
    if prompt_dir.is_dir():
        shutil.rmtree(prompt_dir, ignore_errors=True)


def delete_prompt_context_images(prompt_id: str, images: list[str] | None = None) -> None:
    if images:
        for rel in images:
            delete_context_image_file(rel)
    prompt_dir = CONTEXT_IMAGES_DIR / prompt_id
    if prompt_dir.is_dir():
        shutil.rmtree(prompt_dir, ignore_errors=True)


def delete_prompt_context_files(prompt_id: str, files: list[str] | None = None) -> None:
    if files:
        for rel in files:
            delete_context_file(rel)
    prompt_dir = CONTEXT_FILES_DIR / prompt_id
    if prompt_dir.is_dir():
        shutil.rmtree(prompt_dir, ignore_errors=True)


def delete_prompt_context_attachments(
    prompt_id: str,
    *,
    images: list[str] | None = None,
    files: list[str] | None = None,
    videos: list[str] | None = None,
) -> None:
    delete_prompt_context_images(prompt_id, images)
    delete_prompt_context_files(prompt_id, files)
    delete_prompt_context_videos(prompt_id, videos)


def sync_context_images(saved: list[str], desired: list[str]) -> None:
    saved_set = set(saved)
    desired_set = set(desired)
    for rel in saved_set - desired_set:
        delete_context_image_file(rel)


def sync_context_files(saved: list[str], desired: list[str]) -> None:
    saved_set = set(saved)
    desired_set = set(desired)
    for rel in saved_set - desired_set:
        delete_context_file(rel)


def sync_context_videos(saved: list[str], desired: list[str]) -> None:
    saved_set = set(saved)
    desired_set = set(desired)
    for rel in saved_set - desired_set:
        delete_context_video_file(rel)
