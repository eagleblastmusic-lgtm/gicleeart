"""Read-only kontrola zgodności plików źródłowych trybów z folderem GPT."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from Komponenty.integracjagpt.config import GPT_STARTER_DIR

from .data_loader import WorkModeCatalog

SourceStatus = Literal["current", "drift", "unavailable"]

_ANALYST_GLOB = "GICLEE_ANALYST_MODE_*.md"
_SHOPIFY_GLOB = "GICLEE_SHOPIFY_MODE_*.md"


@dataclass(frozen=True)
class SourceCheckResult:
    status: SourceStatus
    expected_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    unknown_files: tuple[str, ...]
    message: str


def _expected_source_files(catalog: WorkModeCatalog) -> tuple[str, ...]:
    files: list[str] = []
    seen: set[str] = set()
    for mode in catalog.formal_modes():
        sf = mode.source_file.strip()
        if sf and sf not in seen:
            seen.add(sf)
            files.append(sf)
    return tuple(sorted(files))


def _scan_mode_files(starter_dir: Path) -> set[str]:
    found: set[str] = set()
    if not starter_dir.is_dir():
        return found
    for pattern in (_ANALYST_GLOB, _SHOPIFY_GLOB):
        for path in starter_dir.glob(pattern):
            if path.is_file():
                found.add(path.name)
    return found


def check_knowledge_sources(
    catalog: WorkModeCatalog,
    starter_dir: Path | None = None,
) -> SourceCheckResult:
    """Porównuje formalne source_file z plikami w folderze startowym (read-only)."""
    root = starter_dir if starter_dir is not None else GPT_STARTER_DIR
    expected = _expected_source_files(catalog)

    if not root.is_dir():
        return SourceCheckResult(
            status="unavailable",
            expected_files=expected,
            missing_files=expected,
            unknown_files=(),
            message="Folder plików startowych niedostępny — katalog JSON nadal działa.",
        )

    on_disk = _scan_mode_files(root)
    expected_set = set(expected)
    missing = tuple(sorted(expected_set - on_disk))
    unknown = tuple(sorted(on_disk - expected_set))

    if missing or unknown:
        parts: list[str] = []
        if missing:
            parts.append(f"brakuje {len(missing)} plików")
        if unknown:
            parts.append(f"znaleziono {len(unknown)} nieznanych plików")
        return SourceCheckResult(
            status="drift",
            expected_files=expected,
            missing_files=missing,
            unknown_files=unknown,
            message="Rozbieżność źródeł v37: " + ", ".join(parts) + ".",
        )

    return SourceCheckResult(
        status="current",
        expected_files=expected,
        missing_files=(),
        unknown_files=(),
        message="Pliki źródłowe trybów zgodne z katalogiem v37.",
    )
