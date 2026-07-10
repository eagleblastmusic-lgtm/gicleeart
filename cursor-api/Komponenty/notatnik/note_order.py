"""Trwala, lokalna kolejnosc notatek Markdown w komponencie Notatnik."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Iterable

ORDER_FILE_NAME = ".note_order.json"
ORDER_VERSION = 1


class NoteOrderStore:
    """Przechowuje reczna kolejnosc plikow ``.md`` osobno dla kazdego rozdzialu.

    Metadane sa lokalne i nie zmieniaja nazw, sciezek ani tresci notatek.
    Brakujacy albo uszkodzony JSON daje bezpieczny fallback alfabetyczny.
    """

    def __init__(self, notes_dir: Path, *, filename: str = ORDER_FILE_NAME) -> None:
        self.notes_dir = Path(notes_dir).resolve()
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.notes_dir / filename
        self._chapters = self._load()

    @staticmethod
    def _valid_note_name(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        name = value.strip()
        if not name or name.startswith("."):
            return None
        if Path(name).name != name or Path(name).suffix.lower() != ".md":
            return None
        return name

    @staticmethod
    def _valid_chapter_key(value: object) -> str | None:
        if value == ".":
            return "."
        if not isinstance(value, str) or not value.strip():
            return None
        raw = value.replace("\\", "/").strip("/")
        parts = PurePosixPath(raw).parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            return None
        return "/".join(parts)

    def _load(self) -> dict[str, list[str]]:
        if not self.path.is_file():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict) or not isinstance(raw.get("chapters"), dict):
            return {}

        chapters: dict[str, list[str]] = {}
        for key_raw, names_raw in raw["chapters"].items():
            key = self._valid_chapter_key(key_raw)
            if key is None or not isinstance(names_raw, list):
                continue
            seen: set[str] = set()
            names: list[str] = []
            for item in names_raw:
                name = self._valid_note_name(item)
                if name is not None and name not in seen:
                    seen.add(name)
                    names.append(name)
            if names:
                chapters[key] = names
        return chapters

    def reload(self) -> None:
        self._chapters = self._load()

    def chapter_key(self, directory: Path) -> str:
        resolved = Path(directory).resolve()
        try:
            relative = resolved.relative_to(self.notes_dir)
        except ValueError as exc:
            raise ValueError(f"Rozdzial jest poza katalogiem Notatnika: {directory}") from exc
        if relative == Path("."):
            return "."
        return relative.as_posix()

    @staticmethod
    def _normalise(saved: Iterable[str], existing: Iterable[str]) -> list[str]:
        current: list[str] = []
        seen_current: set[str] = set()
        for value in existing:
            name = NoteOrderStore._valid_note_name(value)
            if name is not None and name not in seen_current:
                seen_current.add(name)
                current.append(name)

        current_set = set(current)
        result: list[str] = []
        seen: set[str] = set()
        for value in saved:
            name = NoteOrderStore._valid_note_name(value)
            if name is not None and name in current_set and name not in seen:
                seen.add(name)
                result.append(name)

        result.extend(sorted((name for name in current if name not in seen), key=str.casefold))
        return result

    def ordered_names(self, directory: Path, existing_names: Iterable[str]) -> list[str]:
        key = self.chapter_key(directory)
        result = self._normalise(self._chapters.get(key, []), existing_names)
        self._chapters[key] = result
        return list(result)

    def position(self, directory: Path, filename: str, existing_names: Iterable[str]) -> tuple[int, int] | None:
        ordered = self.ordered_names(directory, existing_names)
        try:
            return ordered.index(filename), len(ordered)
        except ValueError:
            return None

    def can_move(self, directory: Path, filename: str, delta: int, existing_names: Iterable[str]) -> bool:
        position = self.position(directory, filename, existing_names)
        if position is None or delta not in {-1, 1}:
            return False
        index, count = position
        target = index + delta
        return 0 <= target < count

    def _write(self, chapters: dict[str, list[str]]) -> None:
        payload = {
            "version": ORDER_VERSION,
            "chapters": {key: value for key, value in sorted(chapters.items()) if value},
        }
        temp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        try:
            temp.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temp.replace(self.path)
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _commit(self, chapters: dict[str, list[str]]) -> None:
        self._write(chapters)
        self._chapters = chapters

    def move(self, directory: Path, filename: str, delta: int, existing_names: Iterable[str]) -> bool:
        if delta not in {-1, 1}:
            return False
        key = self.chapter_key(directory)
        ordered = self._normalise(self._chapters.get(key, []), existing_names)
        try:
            index = ordered.index(filename)
        except ValueError:
            return False
        target = index + delta
        if target < 0 or target >= len(ordered):
            return False
        ordered[index], ordered[target] = ordered[target], ordered[index]
        chapters = deepcopy(self._chapters)
        chapters[key] = ordered
        self._commit(chapters)
        return True

    def append_note(self, path: Path) -> None:
        key = self.chapter_key(path.parent)
        name = self._valid_note_name(path.name)
        if name is None:
            return
        chapters = deepcopy(self._chapters)
        existing = [item.name for item in path.parent.iterdir() if item.is_file() and item.suffix.lower() == ".md"]
        order = [item for item in self._normalise(chapters.get(key, []), existing) if item != name]
        order.append(name)
        chapters[key] = order
        self._commit(chapters)

    def rename_note(self, old_path: Path, new_path: Path) -> None:
        old_key = self.chapter_key(old_path.parent)
        new_key = self.chapter_key(new_path.parent)
        old_name = old_path.name
        new_name = self._valid_note_name(new_path.name)
        if new_name is None:
            return
        chapters = deepcopy(self._chapters)
        old_order = list(chapters.get(old_key, []))
        if old_key == new_key:
            replaced = False
            new_order: list[str] = []
            for item in old_order:
                if item == old_name and not replaced:
                    new_order.append(new_name)
                    replaced = True
                elif item != new_name:
                    new_order.append(item)
            if not replaced:
                new_order.append(new_name)
            chapters[old_key] = new_order
        else:
            chapters[old_key] = [item for item in old_order if item != old_name]
            existing_target = [
                item.name
                for item in new_path.parent.iterdir()
                if item.is_file() and item.suffix.lower() == ".md"
            ]
            target = [
                item
                for item in self._normalise(chapters.get(new_key, []), existing_target)
                if item != new_name
            ]
            target.append(new_name)
            chapters[new_key] = target
        self._commit(chapters)

    def remove_note(self, path: Path) -> None:
        key = self.chapter_key(path.parent)
        chapters = deepcopy(self._chapters)
        chapters[key] = [item for item in chapters.get(key, []) if item != path.name]
        self._commit(chapters)

    def rename_chapter(self, old_path: Path, new_path: Path) -> None:
        old_key = self.chapter_key(old_path)
        new_key = self.chapter_key(new_path)
        chapters = deepcopy(self._chapters)
        updated: dict[str, list[str]] = {}
        prefix = old_key + "/"
        for key, order in chapters.items():
            if key == old_key:
                updated[new_key] = order
            elif key.startswith(prefix):
                updated[new_key + key[len(old_key):]] = order
            else:
                updated[key] = order
        self._commit(updated)

    def remove_chapter(self, path: Path) -> None:
        key = self.chapter_key(path)
        prefix = key + "/"
        chapters = {
            chapter: order
            for chapter, order in deepcopy(self._chapters).items()
            if chapter != key and not chapter.startswith(prefix)
        }
        self._commit(chapters)
