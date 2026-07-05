"""Lokalny stan GicleeApp Studio — recent, pinned (runtime JSON)."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..component_loader import Component

STATE_VERSION = 1
MAX_RECENT = 10
MAX_PINNED = 20

_DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / "logs" / "studio_state.json"


@dataclass
class RecentEntry:
    folder_name: str
    name: str
    mode: str
    at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "folder_name": self.folder_name,
            "name": self.name,
            "mode": self.mode,
            "at": self.at,
        }

    @classmethod
    def from_dict(cls, row: object) -> RecentEntry | None:
        if not isinstance(row, dict):
            return None
        folder = str(row.get("folder_name") or "").strip()
        if not folder:
            return None
        return cls(
            folder_name=folder,
            name=str(row.get("name") or folder),
            mode=str(row.get("mode") or "subprocess"),
            at=str(row.get("at") or ""),
        )


@dataclass
class StudioState:
    recent: list[RecentEntry] = field(default_factory=list)
    pinned: list[str] = field(default_factory=list)
    _path: Path = field(default_factory=lambda: _DEFAULT_STATE_PATH, repr=False)
    _dirty: bool = field(default=False, repr=False)

    @classmethod
    def load(cls, path: Path | None = None) -> StudioState:
        target = path or _DEFAULT_STATE_PATH
        state = cls(_path=target)
        if not target.is_file():
            return state
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return state
            if int(raw.get("version", 0)) != STATE_VERSION:
                return state
            recent_raw = raw.get("recent")
            if isinstance(recent_raw, list):
                for row in recent_raw[:MAX_RECENT]:
                    entry = RecentEntry.from_dict(row)
                    if entry is not None:
                        state.recent.append(entry)
            pinned_raw = raw.get("pinned")
            if isinstance(pinned_raw, list):
                seen: set[str] = set()
                for item in pinned_raw:
                    folder = str(item or "").strip()
                    if folder and folder not in seen:
                        state.pinned.append(folder)
                        seen.add(folder)
                        if len(state.pinned) >= MAX_PINNED:
                            break
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return cls(_path=target)
        return state

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": STATE_VERSION,
                "recent": [e.to_dict() for e in self.recent[:MAX_RECENT]],
                "pinned": list(self.pinned[:MAX_PINNED]),
            }
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._path)
            self._dirty = False
        except OSError:
            pass

    def record_launch(self, comp: Component) -> None:
        entry = RecentEntry(
            folder_name=comp.folder_name,
            name=comp.name,
            mode=comp.mode,
            at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        self.recent = [e for e in self.recent if e.folder_name != comp.folder_name]
        self.recent.insert(0, entry)
        self.recent = self.recent[:MAX_RECENT]
        self._dirty = True

    def toggle_pin(self, folder_name: str) -> bool:
        folder = folder_name.strip()
        if not folder:
            return False
        if folder in self.pinned:
            self.pinned = [f for f in self.pinned if f != folder]
            self._dirty = True
            return False
        if len(self.pinned) >= MAX_PINNED:
            self.pinned = self.pinned[1:]
        self.pinned.append(folder)
        self._dirty = True
        return True

    def is_pinned(self, folder_name: str) -> bool:
        return folder_name in self.pinned

    def prune(self, valid_folders: Iterable[str]) -> bool:
        valid = set(valid_folders)
        new_recent = [e for e in self.recent if e.folder_name in valid]
        new_pinned = [f for f in self.pinned if f in valid]
        changed = new_recent != self.recent or new_pinned != self.pinned
        if changed:
            self.recent = new_recent
            self.pinned = new_pinned
            self._dirty = True
        return changed

    def recent_folder_order(self) -> list[str]:
        return [e.folder_name for e in self.recent]

    def sorted_components(self, comps: list[Component]) -> list[Component]:
        if not comps:
            return []
        pin_rank = {f: i for i, f in enumerate(self.pinned)}
        recent_rank = {f: i for i, f in enumerate(self.recent_folder_order())}

        def sort_key(c: Component) -> tuple[int, int, int, int, int, str]:
            p = pin_rank.get(c.folder_name, 9999)
            r = recent_rank.get(c.folder_name, 9999)
            return (
                0 if p < 9999 else 1,
                p,
                0 if r < 9999 else 1,
                r,
                c.order,
                c.name.lower(),
            )

        return sorted(comps, key=sort_key)
