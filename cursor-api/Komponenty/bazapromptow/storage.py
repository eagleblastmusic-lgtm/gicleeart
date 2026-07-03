"""Trwaly zapis promptow w JSON."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
PROMPTS_FILE = DATA_DIR / "prompts.json"


@dataclass
class PromptEntry:
    id: str
    label: str
    text: str
    sort_key: int = 0
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "text": self.text,
            "sort_key": self.sort_key,
        }
        if self.context.strip():
            row["context"] = self.context
        return row

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> PromptEntry:
        return cls(
            id=str(row.get("id") or uuid.uuid4().hex[:12]),
            label=str(row.get("label") or "").strip(),
            text=str(row.get("text") or ""),
            sort_key=int(row.get("sort_key") or 0),
            context=str(row.get("context") or ""),
        )


@dataclass
class PromptStore:
    prompts: list[PromptEntry] = field(default_factory=list)

    def sorted(self) -> list[PromptEntry]:
        return sorted(self.prompts, key=lambda p: (p.sort_key, p.label.lower()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "prompts": [p.to_dict() for p in self.prompts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptStore:
        raw = data.get("prompts") if isinstance(data.get("prompts"), list) else []
        prompts: list[PromptEntry] = []
        for row in raw:
            if isinstance(row, dict):
                prompts.append(PromptEntry.from_dict(row))
        return cls(prompts=prompts)


def load_prompts() -> PromptStore:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROMPTS_FILE.is_file():
        return PromptStore()
    try:
        data = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return PromptStore.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return PromptStore()


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
