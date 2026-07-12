"""Copy-only migration planner for tracked local/runtime data.

The migrator never deletes or overwrites source files. Copy execution is allowed
only after every destination has passed a conflict preflight and an explicit
non-aggregate migration profile has been selected.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .audit import list_tracked_files
from .policy import DataClass, PolicyDecision, classify_path, normalize_repo_path


MIGRATION_PROFILES = ("all", "critical", "archive", "cache")


@dataclass
class MigrationItem:
    source: str
    destination: str
    classification: str
    rule_id: str
    bucket: str
    source_sha256: str
    destination_sha256: str = ""
    status: str = "planned"
    message: str = ""


@dataclass
class MigrationReport:
    repo_root: str
    dry_run: bool
    profile: str = "all"
    items: list[MigrationItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.errors) or any(item.status == "conflict" for item in self.items)

    @property
    def copied_count(self) -> int:
        return sum(item.status == "copied" for item in self.items)

    @property
    def verified_existing_count(self) -> int:
        return sum(item.status == "verified_existing" for item in self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_root": self.repo_root,
            "dry_run": self.dry_run,
            "profile": self.profile,
            "blocked": self.blocked,
            "item_count": len(self.items),
            "copied_count": self.copied_count,
            "verified_existing_count": self.verified_existing_count,
            "errors": list(self.errors),
            "items": [asdict(item) for item in self.items],
        }

    def format_text(self) -> str:
        mode = "DRY-RUN" if self.dry_run else "COPY"
        lines = [
            f"=== Repository data migration ({mode}) ===",
            f"Repository: {self.repo_root}",
            f"Profile: {self.profile}",
            f"Items: {len(self.items)}",
            f"Blocked: {'YES' if self.blocked else 'NO'}",
        ]
        for error in self.errors:
            lines.append(f"ERROR: {error}")
        for item in self.items:
            lines.append(
                f"[{item.status}] {item.classification} {item.source} -> {item.destination}"
            )
            if item.message:
                lines.append(f"  {item.message}")
        return "\n".join(lines) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_local_app_data() -> Path | None:
    raw = os.environ.get("LOCALAPPDATA")
    return Path(raw) if raw else None


def _default_roaming_app_data() -> Path | None:
    raw = os.environ.get("APPDATA")
    return Path(raw) if raw else None


def resolve_bucket_roots(
    *,
    local_app_data: Path | None = None,
    roaming_app_data: Path | None = None,
) -> dict[str, Path]:
    local = local_app_data or _default_local_app_data()
    roaming = roaming_app_data or _default_roaming_app_data()
    if local is None:
        raise ValueError("LOCALAPPDATA is unavailable; provide --local-app-data explicitly.")
    if roaming is None:
        raise ValueError("APPDATA is unavailable; provide --roaming-app-data explicitly.")
    local_base = local / "GicleeArt" / "GicleeApp"
    roaming_base = roaming / "GicleeArt" / "GicleeApp"
    return {
        "data": local_base / "data",
        "backups": local_base / "backups",
        "logs": local_base / "logs",
        "config": roaming_base / "config",
    }


def _candidate_paths(repo_root: Path, *, tracked_only: bool) -> list[str]:
    if tracked_only:
        return list_tracked_files(repo_root)
    paths: list[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        paths.append(normalize_repo_path(path.relative_to(repo_root)))
    return sorted(paths)


def _profile_includes(decision: PolicyDecision, profile: str) -> bool:
    if not decision.requires_migration or decision.classification is None:
        return False
    if profile == "all":
        return True
    if profile == "critical":
        return decision.classification in {DataClass.SECRET, DataClass.PRIVATE} or (
            decision.classification is DataClass.RUNTIME
            and decision.migration_bucket in {"data", "config"}
        )
    if profile == "archive":
        return decision.classification is DataClass.BACKUP or (
            decision.classification is DataClass.RUNTIME
            and decision.migration_bucket == "logs"
        )
    if profile == "cache":
        return decision.classification is DataClass.CACHE
    return False


def build_migration_report(
    repo_root: Path,
    *,
    execute_copy: bool = False,
    tracked_only: bool = True,
    profile: str = "all",
    local_app_data: Path | None = None,
    roaming_app_data: Path | None = None,
) -> MigrationReport:
    root = repo_root.resolve()
    normalized_profile = profile.strip().lower()
    report = MigrationReport(
        repo_root=str(root),
        dry_run=not execute_copy,
        profile=normalized_profile,
    )
    if normalized_profile not in MIGRATION_PROFILES:
        report.errors.append(
            f"Unknown migration profile {profile!r}; choose one of: {', '.join(MIGRATION_PROFILES)}."
        )
        return report
    if execute_copy and normalized_profile == "all":
        report.errors.append(
            "Copy with profile 'all' is forbidden. Select --profile critical, archive or cache explicitly."
        )
        return report

    try:
        bucket_roots = resolve_bucket_roots(
            local_app_data=local_app_data,
            roaming_app_data=roaming_app_data,
        )
        candidates = _candidate_paths(root, tracked_only=tracked_only)
    except (ValueError, RuntimeError) as exc:
        report.errors.append(str(exc))
        return report

    preflight: list[tuple[MigrationItem, Path, Path]] = []
    for rel in candidates:
        decision = classify_path(rel)
        if not _profile_includes(decision, normalized_profile):
            continue
        source = root / rel
        if not source.is_file():
            report.errors.append(f"Tracked migration source is missing: {rel}")
            continue
        bucket = decision.migration_bucket or "data"
        destination = bucket_roots[bucket] / Path(rel)
        source_hash = sha256_file(source)
        item = MigrationItem(
            source=rel,
            destination=str(destination),
            classification=decision.classification.value,
            rule_id=decision.rule_id,
            bucket=bucket,
            source_sha256=source_hash,
        )

        if destination.exists():
            if not destination.is_file():
                item.status = "conflict"
                item.message = "Destination exists and is not a file; no copy will be attempted."
            else:
                destination_hash = sha256_file(destination)
                item.destination_sha256 = destination_hash
                if destination_hash == source_hash:
                    item.status = "verified_existing"
                    item.message = "Destination already contains an identical verified copy."
                else:
                    item.status = "conflict"
                    item.message = "Destination exists with different content; overwrite is forbidden."
        report.items.append(item)
        preflight.append((item, source, destination))

    if report.blocked or not execute_copy:
        return report

    for item, source, destination in preflight:
        if item.status == "verified_existing":
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, destination)
            destination_hash = sha256_file(destination)
        except OSError as exc:
            item.status = "error"
            item.message = str(exc)
            report.errors.append(f"{item.source}: {exc}")
            break
        item.destination_sha256 = destination_hash
        if destination_hash != item.source_sha256:
            item.status = "error"
            item.message = "SHA-256 mismatch after copy. Source remains untouched."
            report.errors.append(f"Hash verification failed: {item.source}")
            break
        item.status = "copied"
        item.message = "Copied and SHA-256 verified; source was not deleted."

    return report


def write_migration_json(report: MigrationReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
