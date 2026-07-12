"""Allowlist-based snapshot planning and copy for the GicleeApp repository.

This module is intentionally independent from Git push orchestration. It builds a
deterministic snapshot from paths approved by the central repository-safety policy,
performs a content scan, and can copy the approved files to a staging directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .audit import (
    TEXT_SUFFIXES,
    _large_binary_finding,
    _pii_findings,
    _read_text_for_scan,
    _secret_findings,
)
from .policy import classify_path, normalize_repo_path


DEFAULT_MANIFEST_PATH = "docs/repository_safety/GICLEEAPP_SNAPSHOT_MANIFEST.json"
DEFAULT_PROTECTED_PATHS = frozenset(
    {
        ".gitignore",
        "README.md",
        "GPT_README.md",
        "SYNC_NOTES.md",
        "REVIEW_MANIFEST.json",
        "docs/GPT_KNOWLEDGE_PACK.md",
        "docs/SHOPIFY_THEME_INTEGRATION.md",
        "docs/UI_REDESIGN_PLAN.md",
    }
)


@dataclass(frozen=True)
class SkippedPath:
    path: str
    rule_id: str
    classification: str | None
    reason: str


@dataclass(frozen=True)
class SnapshotFinding:
    severity: str
    rule_id: str
    path: str
    message: str
    line: int | None = None


@dataclass
class SnapshotPlan:
    source_root: str
    staging_root: str
    source_git_sha: str
    application_version: str
    manifest_path: str
    included_paths: list[str] = field(default_factory=list)
    skipped_paths: list[SkippedPath] = field(default_factory=list)
    stale_paths: list[SkippedPath] = field(default_factory=list)
    protected_paths: list[str] = field(default_factory=list)
    findings: list[SnapshotFinding] = field(default_factory=list)
    tree_sha256: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def blockers(self) -> list[SnapshotFinding]:
        return [item for item in self.findings if item.severity == "BLOCKER"]

    @property
    def ok(self) -> bool:
        return not self.errors and not self.blockers

    def to_manifest_dict(self, *, generated_at_utc: str | None = None) -> dict[str, object]:
        return {
            "schema_version": 1,
            "snapshot_type": "gicleeapp_allowlist_snapshot",
            "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat(),
            "source_git_sha": self.source_git_sha,
            "application_version": self.application_version,
            "cursor_api_tree_sha256": self.tree_sha256,
            "manifest_path": self.manifest_path,
            "included_file_count": len(self.included_paths),
            "included_paths": list(self.included_paths),
            "skipped_file_count": len(self.skipped_paths),
            "skipped_paths": [asdict(item) for item in self.skipped_paths],
            "stale_file_count": len(self.stale_paths),
            "stale_paths": [asdict(item) for item in self.stale_paths],
            "protected_paths": list(self.protected_paths),
            "security_data_scan": {
                "ok": self.ok,
                "error_count": len(self.errors),
                "blocker_count": len(self.blockers),
                "finding_count": len(self.findings),
                "findings": [asdict(item) for item in self.findings],
            },
        }

    def format_text(self) -> str:
        lines = [
            "=== GicleeApp allowlist snapshot ===",
            f"Source: {self.source_root}",
            f"Staging: {self.staging_root}",
            f"Source Git SHA: {self.source_git_sha or '(unavailable)'}",
            f"Application version: {self.application_version or '(unavailable)'}",
            f"Included: {len(self.included_paths)}",
            f"Skipped: {len(self.skipped_paths)}",
            f"Stale in staging (retained): {len(self.stale_paths)}",
            f"Protected: {len(self.protected_paths)}",
            f"Blockers: {len(self.blockers)}",
            f"Tree SHA-256: {self.tree_sha256}",
        ]
        for error in self.errors:
            lines.append(f"ERROR: {error}")
        for finding in self.findings:
            location = finding.path if finding.line is None else f"{finding.path}:{finding.line}"
            lines.append(
                f"[{finding.severity}] {finding.rule_id} {location} — {finding.message}"
            )
        return "\n".join(lines) + "\n"


@dataclass
class SnapshotCopyResult:
    plan: SnapshotPlan
    copied: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    protected: list[str] = field(default_factory=list)
    manifest_written: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.plan.ok and not self.errors


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(source_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return (proc.stdout or "").strip() if proc.returncode == 0 else ""


def _application_version(source_root: Path) -> str:
    version_file = source_root / "giclee_app" / "__init__.py"
    try:
        text = version_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1).strip() if match else ""


def _iter_files(source_root: Path) -> Iterable[tuple[str, Path]]:
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        rel = normalize_repo_path(path.relative_to(source_root).as_posix())
        yield rel, path


def _scan_included_file(
    rel: str,
    path: Path,
    *,
    max_text_scan_bytes: int,
    max_binary_bytes: int,
) -> list[SnapshotFinding]:
    findings: list[SnapshotFinding] = []
    large = _large_binary_finding(rel, path, max_binary_bytes)
    if large is not None:
        findings.append(SnapshotFinding(**asdict(large)))

    suffix = path.suffix.lower()
    if suffix not in TEXT_SUFFIXES and path.name not in {
        ".gitignore",
        ".gitattributes",
        "Makefile",
    }:
        return findings

    text = _read_text_for_scan(path, max_text_scan_bytes)
    if text is None:
        return findings
    findings.extend(SnapshotFinding(**asdict(item)) for item in _secret_findings(rel, text))
    findings.extend(SnapshotFinding(**asdict(item)) for item in _pii_findings(rel, text))
    return findings


def _tracked_staging_paths(staging_root: Path) -> list[str]:
    if not (staging_root / ".git").is_dir():
        return []
    raw = _git_value(staging_root, "ls-files", "-z")
    return sorted(
        normalize_repo_path(item)
        for item in raw.split("\0")
        if item.strip()
    )


def _discover_stale_paths(plan: SnapshotPlan, staging_root: Path) -> list[SkippedPath]:
    expected = set(plan.included_paths)
    expected.update(plan.protected_paths)
    expected.add(plan.manifest_path)
    stale: list[SkippedPath] = []
    for rel in _tracked_staging_paths(staging_root):
        if rel in expected:
            continue
        decision = classify_path(rel)
        classification = decision.classification.value if decision.classification else None
        stale.append(
            SkippedPath(
                path=rel,
                rule_id="STALE_STAGING_PATH",
                classification=classification,
                reason=(
                    f"{decision.rule_id}: tracked staging path is absent from the current "
                    "allowlist snapshot; retained for explicit review, never auto-deleted."
                ),
            )
        )
    return stale


def build_snapshot_plan(
    source_root: Path,
    staging_root: Path,
    *,
    protected_paths: Iterable[str] = DEFAULT_PROTECTED_PATHS,
    manifest_path: str = DEFAULT_MANIFEST_PATH,
    max_text_scan_bytes: int = 2 * 1024 * 1024,
    max_binary_bytes: int = 10 * 1024 * 1024,
) -> SnapshotPlan:
    source = source_root.resolve()
    staging = staging_root.resolve()
    manifest_rel = normalize_repo_path(manifest_path)
    protected = sorted({normalize_repo_path(path) for path in protected_paths})
    plan = SnapshotPlan(
        source_root=str(source),
        staging_root=str(staging),
        source_git_sha=_git_value(source, "rev-parse", "HEAD"),
        application_version=_application_version(source),
        manifest_path=manifest_rel,
        protected_paths=protected,
    )
    if not source.is_dir():
        plan.errors.append(f"Source directory does not exist: {source}")
        return plan

    digest = hashlib.sha256()
    for rel, path in _iter_files(source):
        if rel == manifest_rel:
            plan.skipped_paths.append(
                SkippedPath(
                    rel,
                    "SNAPSHOT_MANIFEST_REGENERATED",
                    "GENERATED",
                    "The snapshot manifest is regenerated from the current source tree.",
                )
            )
            continue

        decision = classify_path(rel)
        if not decision.sync_allowed:
            classification = decision.classification.value if decision.classification else None
            plan.skipped_paths.append(
                SkippedPath(rel, decision.rule_id, classification, decision.reason)
            )
            continue

        plan.included_paths.append(rel)
        file_hash = _sha256_file(path)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\0")
        plan.findings.extend(
            _scan_included_file(
                rel,
                path,
                max_text_scan_bytes=max_text_scan_bytes,
                max_binary_bytes=max_binary_bytes,
            )
        )

    plan.included_paths.sort()
    plan.skipped_paths.sort(key=lambda item: item.path)
    plan.stale_paths = _discover_stale_paths(plan, staging)
    plan.findings.sort(
        key=lambda item: (
            0 if item.severity == "BLOCKER" else 1,
            item.path,
            item.rule_id,
            item.line or 0,
        )
    )
    plan.tree_sha256 = digest.hexdigest()
    return plan


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".giclee-sync-tmp")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _manifest_payload_without_timestamp(payload: dict[str, object]) -> dict[str, object]:
    comparable = dict(payload)
    comparable.pop("generated_at_utc", None)
    return comparable


def _stable_manifest_payload(plan: SnapshotPlan, target: Path) -> tuple[dict[str, object], bool]:
    fresh = plan.to_manifest_dict()
    if not target.is_file():
        return fresh, True
    try:
        existing = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return fresh, True
    if not isinstance(existing, dict):
        return fresh, True
    if _manifest_payload_without_timestamp(existing) != _manifest_payload_without_timestamp(fresh):
        return fresh, True
    timestamp = existing.get("generated_at_utc")
    if isinstance(timestamp, str) and timestamp.strip():
        fresh["generated_at_utc"] = timestamp
    return fresh, False


def execute_snapshot_copy(plan: SnapshotPlan) -> SnapshotCopyResult:
    result = SnapshotCopyResult(plan=plan)
    if not plan.ok:
        result.errors.append("Snapshot plan contains blockers or errors; no files copied.")
        return result

    source = Path(plan.source_root)
    staging = Path(plan.staging_root)
    protected = set(plan.protected_paths)
    for rel in plan.included_paths:
        if rel in protected:
            result.protected.append(rel)
            continue
        src = source / rel
        dst = staging / rel
        try:
            if dst.is_file() and _sha256_file(src) == _sha256_file(dst):
                result.unchanged.append(rel)
                continue
            _atomic_copy(src, dst)
            result.copied.append(rel)
        except OSError as exc:
            result.errors.append(f"{rel}: {exc}")
            return result

    manifest_target = staging / plan.manifest_path
    try:
        manifest_target.parent.mkdir(parents=True, exist_ok=True)
        manifest_payload, needs_write = _stable_manifest_payload(plan, manifest_target)
        if needs_write:
            temporary = manifest_target.with_name(manifest_target.name + ".tmp")
            temporary.write_text(
                json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, manifest_target)
            result.manifest_written = True
        else:
            result.unchanged.append(plan.manifest_path)
    except OSError as exc:
        result.errors.append(f"{plan.manifest_path}: {exc}")
    return result


def write_snapshot_plan_json(plan: SnapshotPlan, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(plan.to_manifest_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
