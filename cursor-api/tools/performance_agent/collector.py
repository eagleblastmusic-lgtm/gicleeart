"""Log collector — snapshot studio_perf.log into report bundle."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CollectionResult:
    source_log: Path
    raw_log: Path
    events_jsonl: Path
    file_size_bytes: int
    line_count: int


def collect_log(source_log: Path, report_dir: Path) -> CollectionResult:
    if not source_log.exists():
        raise FileNotFoundError(f"Performance log not found: {source_log}")
    if not source_log.is_file():
        raise ValueError(f"Performance log is not a file: {source_log}")

    report_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = report_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_log = raw_dir / "studio_perf.log"
    events_jsonl = report_dir / "events.jsonl"

    shutil.copy2(source_log, raw_log)
    shutil.copy2(source_log, events_jsonl)

    text = source_log.read_text(encoding="utf-8")
    line_count = len(text.splitlines()) if text else 0
    file_size_bytes = source_log.stat().st_size

    return CollectionResult(
        source_log=source_log,
        raw_log=raw_log,
        events_jsonl=events_jsonl,
        file_size_bytes=file_size_bytes,
        line_count=line_count,
    )
