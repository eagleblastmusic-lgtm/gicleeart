"""Planowanie i wykonywanie bezpiecznego przenoszenia plikow (dry-run + execute)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

COMPONENT_NAME = "segregatorplikow"


class DuplicatePolicy(str, Enum):
    RENAME = "rename"
    SKIP = "skip"
    CANCEL = "cancel"
    # REPLACE — tylko po jawnej per-plikowej zgodzie w dialogu (nie w batch auto)
    REPLACE = "replace"


class PlanStatus(str, Enum):
    OK = "ok"
    DUPLICATE = "duplicate"
    MISSING_SRC = "missing_src"
    MISSING_DEST_DIR = "missing_dest_dir"
    SKIP = "skip"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class MovePlanItem:
    src: Path
    dest: Path
    status: PlanStatus = PlanStatus.OK
    resolved_dest: Path | None = None
    error: str = ""
    allow_replace: bool = False

    @property
    def effective_dest(self) -> Path | None:
        return self.resolved_dest or self.dest

    @property
    def ready_to_move(self) -> bool:
        if self.status in (PlanStatus.SKIP, PlanStatus.CANCELLED, PlanStatus.ERROR):
            return False
        if self.status == PlanStatus.MISSING_SRC:
            return False
        if self.status == PlanStatus.MISSING_DEST_DIR:
            return False
        if self.effective_dest is None:
            return False
        if self.status == PlanStatus.DUPLICATE and not self.allow_replace:
            return self.resolved_dest is not None and self.resolved_dest != self.dest
        return self.status in (PlanStatus.OK, PlanStatus.DUPLICATE)


@dataclass
class MovePlan:
    items: list[MovePlanItem] = field(default_factory=list)
    dest_dir: Path | None = None
    tile_name: str = ""
    cancelled: bool = False

    @property
    def movable_count(self) -> int:
        return sum(1 for i in self.items if i.ready_to_move)

    @property
    def blocked_count(self) -> int:
        return sum(1 for i in self.items if not i.ready_to_move and i.status != PlanStatus.SKIP)


@dataclass
class MoveResult:
    src: Path
    dest: Path | None
    success: bool
    message: str = ""


def filter_file_paths(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Rozdziela pliki od folderow. MVP: foldery nie sa przenoszone."""
    files: list[Path] = []
    dirs: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        try:
            p = raw.resolve()
        except OSError:
            p = raw
        if p in seen:
            continue
        seen.add(p)
        if p.is_dir():
            dirs.append(p)
        elif p.is_file():
            files.append(p)
        else:
            # Nieistniejacy — traktuj jak plik do walidacji w planie
            files.append(raw)
    return files, dirs


def auto_rename_path(dest_dir: Path, filename: str) -> Path:
    """plik.jpg -> plik (1).jpg -> plik (2).jpg ..."""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    n = 1
    while True:
        candidate = dest_dir / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def plan_moves(
    sources: list[Path],
    dest_dir: Path,
    *,
    tile_name: str = "",
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.RENAME,
    per_file_replace: dict[Path, bool] | None = None,
) -> MovePlan:
    """Buduje plan operacji (dry-run) — bez shutil.move."""
    plan = MovePlan(dest_dir=dest_dir, tile_name=tile_name)
    replace_map = per_file_replace or {}

    if duplicate_policy == DuplicatePolicy.CANCEL:
        plan.cancelled = True
        for src in sources:
            plan.items.append(
                MovePlanItem(
                    src=src,
                    dest=dest_dir / src.name,
                    status=PlanStatus.CANCELLED,
                    error="Operacja anulowana przez uzytkownika",
                )
            )
        return plan

    if not dest_dir.is_dir():
        for src in sources:
            plan.items.append(
                MovePlanItem(
                    src=src,
                    dest=dest_dir / src.name,
                    status=PlanStatus.MISSING_DEST_DIR,
                    error=f"Folder docelowy nie istnieje: {dest_dir}",
                )
            )
        return plan

    for src in sources:
        try:
            resolved_src = src.resolve()
        except OSError:
            resolved_src = src

        dest = dest_dir / resolved_src.name
        item = MovePlanItem(src=resolved_src, dest=dest)

        if not resolved_src.is_file():
            item.status = PlanStatus.MISSING_SRC
            item.error = f"Plik zrodlowy nie istnieje: {resolved_src}"
            plan.items.append(item)
            continue

        if dest.exists():
            item.status = PlanStatus.DUPLICATE
            if duplicate_policy == DuplicatePolicy.SKIP:
                item.status = PlanStatus.SKIP
                item.error = "Plik docelowy juz istnieje — pominiety"
            elif duplicate_policy == DuplicatePolicy.RENAME:
                item.resolved_dest = auto_rename_path(dest_dir, resolved_src.name)
                item.status = PlanStatus.OK
            elif duplicate_policy == DuplicatePolicy.REPLACE:
                if replace_map.get(resolved_src, False):
                    item.resolved_dest = dest
                    item.allow_replace = True
                    item.status = PlanStatus.DUPLICATE
                else:
                    item.status = PlanStatus.SKIP
                    item.error = "Wymaga potwierdzenia zastapienia — nie wybrano"
            else:
                item.status = PlanStatus.SKIP
                item.error = "Nieznana polityka duplikatu"
        else:
            item.resolved_dest = dest
            item.status = PlanStatus.OK

        plan.items.append(item)

    return plan


def execute_moves(plan: MovePlan) -> list[MoveResult]:
    """Wykonuje shutil.move tylko dla pozycji ready_to_move. Nigdy nie wywolywac bez potwierdzenia UI."""
    results: list[MoveResult] = []
    if plan.cancelled:
        return results

    for item in plan.items:
        if not item.ready_to_move:
            if item.status == PlanStatus.SKIP:
                results.append(
                    MoveResult(
                        src=item.src,
                        dest=None,
                        success=False,
                        message=item.error or "Pominiety",
                    )
                )
            continue

        target = item.effective_dest
        if target is None:
            results.append(
                MoveResult(
                    src=item.src,
                    dest=None,
                    success=False,
                    message="Brak sciezki docelowej",
                )
            )
            continue

        if item.allow_replace and target.exists():
            try:
                target.unlink()
            except OSError as e:
                results.append(
                    MoveResult(
                        src=item.src,
                        dest=target,
                        success=False,
                        message=f"Nie mozna zastapic istniejacego pliku: {e}",
                    )
                )
                continue

        try:
            shutil.move(str(item.src), str(target))
            results.append(
                MoveResult(src=item.src, dest=target, success=True, message="Przeniesiono")
            )
        except PermissionError as e:
            results.append(
                MoveResult(
                    src=item.src,
                    dest=target,
                    success=False,
                    message=f"Brak uprawnien: {e}",
                )
            )
        except FileNotFoundError as e:
            results.append(
                MoveResult(
                    src=item.src,
                    dest=target,
                    success=False,
                    message=f"Plik nie znaleziony: {e}",
                )
            )
        except OSError as e:
            results.append(
                MoveResult(
                    src=item.src,
                    dest=target,
                    success=False,
                    message=f"Blad przenoszenia: {e}",
                )
            )

    return results
