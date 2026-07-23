"""Bezpieczny push snapshotu motywu → .gpt_mirror → gicleeart-gpt na GitHub."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    GICLEEART_GPT_FALLBACK_COMMIT_DESC,
    GICLEEART_GPT_REMOTE_URL,
    MIRROR_DIR,
    MIRROR_PROTECTED_DELETIONS,
    MIRROR_RUNTIME_DENYLIST,
    GptConfig,
)
from .mirror import (
    SyncResult,
    _assert_mirror_git,
    _finalize_manifest_snapshot_commit,
    _run_git as mirror_run_git,
    _verify_manifest_snapshot_commit,
    ensure_mirror_clone,
    sync_theme_to_mirror,
)
from .review_session import ReviewSession

OnLine = list[str] | None

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sk-api-key", re.compile(r"sk-[a-zA-Z0-9]{16,}")),
    ("ghp_", re.compile(r"ghp_[a-zA-Z0-9]{20,}")),
    ("github_pat_", re.compile(r"github_pat_[a-zA-Z0-9_]{20,}")),
    ("AIza", re.compile(r"AIza[a-zA-Z0-9_-]{20,}")),
    ("xoxb-", re.compile(r"xoxb-[a-zA-Z0-9-]{20,}")),
    ("access_token", re.compile(r"access_token\s*[:=]\s*['\"]?[a-zA-Z0-9._-]{8,}", re.I)),
    ("refresh_token", re.compile(r"refresh_token\s*[:=]\s*['\"]?[a-zA-Z0-9._-]{8,}", re.I)),
    ("client_secret", re.compile(r"client_secret\s*[:=]\s*['\"]?[a-zA-Z0-9._-]{8,}", re.I)),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
)

LOOSE_SECRET_MARKERS = frozenset({
    "SHOPIFY_API",
    "SHOPIFY_ACCESS",
    "SHOPIFY_TOKEN",
    "ADMIN_API_ACCESS_TOKEN",
})


@dataclass
class BranchSyncStatus:
    ok: bool = True
    ahead: int = 0
    behind: int = 0
    diverged: bool = False
    message: str = ""
    pulled: bool = False


@dataclass
class GicleeArtGptAuditReport:
    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    removed_stale: list[str] = field(default_factory=list)
    deletable_files: list[str] = field(default_factory=list)
    blocked_deletions: list[str] = field(default_factory=list)
    commit_candidates: list[str] = field(default_factory=list)
    diff_stat: str = ""
    secret_hits: list[str] = field(default_factory=list)
    runtime_hits: list[str] = field(default_factory=list)
    branch_status: BranchSyncStatus = field(default_factory=BranchSyncStatus)
    blocked: bool = False
    no_changes: bool = False
    commit_message: str = ""
    sync: SyncResult | None = None
    error: str = ""

    def format_report(self) -> list[str]:
        lines = ["=== Push GicleeArt-GPT — audyt ==="]
        if self.error:
            lines.append(f"BŁĄD: {self.error}")
            return lines
        if self.sync:
            lines.append(f"Skopiowano do lustra: {len(self.sync.copied)} plików")
            if self.sync.removed_stale:
                lines.append(f"Usunięto stale z lustra: {len(self.sync.removed_stale)}")
            if self.sync.skipped_large:
                lines.append(f"Pominięto (za duże): {len(self.sync.skipped_large)}")
        bs = self.branch_status
        if bs.message:
            lines.append(f"Branch: {bs.message}")
        lines.append("")
        lines.append(f"Nowe ({len(self.new_files)}):")
        lines.extend(f"  + {p}" for p in self.new_files[:40])
        lines.append(f"Zmienione ({len(self.modified_files)}):")
        lines.extend(f"  M {p}" for p in self.modified_files[:40])
        if self.deleted_files:
            lines.append(f"Usunięte (git) ({len(self.deleted_files)}):")
            lines.extend(f"  D {p}" for p in self.deleted_files[:40])
        if self.removed_stale:
            lines.append(f"Usunięte stale (sync) ({len(self.removed_stale)}):")
            lines.extend(f"  D {p}" for p in self.removed_stale[:40])
        if self.deletable_files:
            lines.append(f"Do ewentualnego usunięcia w commicie ({len(self.deletable_files)}):")
            lines.extend(f"  D {p}" for p in self.deletable_files[:40])
        if self.blocked_deletions:
            lines.append("Usunięcia zablokowane:")
            lines.extend(f"  ! {p}" for p in self.blocked_deletions)
        if self.diff_stat.strip():
            lines.append("")
            lines.append("diff --stat:")
            lines.extend(self.diff_stat.strip().splitlines())
        lines.append("")
        lines.append(f"Kandydaci do commita: {len(self.commit_candidates)}")
        if self.runtime_hits:
            lines.append("Runtime / poza commitem:")
            lines.extend(f"  ⚠ {h}" for h in self.runtime_hits)
        if self.secret_hits:
            lines.append("SEKRETY — commit zablokowany:")
            lines.extend(f"  ✖ {h}" for h in self.secret_hits)
        if self.blocked:
            lines.append("")
            lines.append("WORKFLOW ZATRZYMANY — napraw blokady przed pushem.")
        elif self.no_changes:
            lines.append("")
            lines.append("Brak zmian — gicleeart-gpt jest aktualne.")
        else:
            lines.append("")
            lines.append(f"Proponowany commit: {self.commit_message}")
            lines.append("Potwierdź push w oknie dialogowym.")
        return lines


@dataclass
class GicleeArtGptPushResult:
    ok: bool
    commit_sha: str = ""
    committed_files: list[str] = field(default_factory=list)
    message: str = ""


def _log(lines: OnLine, msg: str) -> None:
    if lines is not None:
        lines.append(msg)


def _norm_rel(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("./")


def _assert_gicleeart_gpt_remote(remote_url: str) -> None:
    u = remote_url.rstrip("/").lower()
    if "gicleeapp" in u:
        raise ValueError(f"remote_url wskazuje gicleeapp zamiast gicleeart-gpt: {remote_url}")
    if "gicleeart-gpt" not in u:
        raise ValueError(f"remote_url musi wskazywać gicleeart-gpt: {remote_url}")

    normalized = u
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    elif normalized.startswith("ssh://git@github.com/"):
        normalized = "https://github.com/" + normalized.removeprefix("ssh://git@github.com/")
    normalized = normalized.removesuffix(".git").rstrip("/")
    if normalized != "https://github.com/eagleblastmusic-lgtm/gicleeart-gpt":
        raise ValueError(
            "remote_url musi wskazywać dokładnie "
            f"eagleblastmusic-lgtm/gicleeart-gpt: {remote_url}"
        )


def validate_mirror_config(cfg: GptConfig, *, log: OnLine = None) -> None:
    remote = (cfg.remote_url or "").strip()
    if not remote:
        raise ValueError("Ustaw URL repo GPT (gicleeart-gpt) w konfiguracji.")
    _assert_gicleeart_gpt_remote(remote)
    _log(log, f"Remote OK: {remote}")


def _parse_branch_tracking(status_line: str) -> tuple[int, int, bool]:
    ahead = behind = 0
    diverged = False
    if "[" not in status_line:
        return ahead, behind, diverged
    bracket = status_line.split("[", 1)[1].split("]", 1)[0]
    for part in bracket.split(","):
        part = part.strip()
        if part.startswith("ahead "):
            try:
                ahead = int(part.split()[1])
            except (IndexError, ValueError):
                pass
        elif part.startswith("behind "):
            try:
                behind = int(part.split()[1])
            except (IndexError, ValueError):
                pass
    diverged = ahead > 0 and behind > 0
    return ahead, behind, diverged


def inspect_mirror_branch_sync(
    mirror: Path,
    branch: str,
    *,
    pull_ff_only: bool = False,
    log: OnLine = None,
) -> BranchSyncStatus:
    lines = log if log is not None else []

    fetch = mirror_run_git(["fetch", "origin", branch], mirror, lines)
    if fetch.returncode != 0:
        return BranchSyncStatus(ok=False, message="git fetch origin nie powiódł się.")

    sb = mirror_run_git(["status", "-sb"], mirror, lines)
    first = (sb.stdout or "").splitlines()[0] if sb.stdout else ""
    ahead, behind, diverged = _parse_branch_tracking(first)

    if diverged:
        return BranchSyncStatus(
            ok=False,
            ahead=ahead,
            behind=behind,
            diverged=True,
            message=f"Branch rozjechany z origin ({ahead} ahead, {behind} behind).",
        )

    pulled = False
    if pull_ff_only and behind > 0:
        pull = mirror_run_git(["pull", "--ff-only", "origin", branch], mirror, lines)
        if pull.returncode != 0:
            return BranchSyncStatus(
                ok=False,
                behind=behind,
                message="git pull --ff-only nie powiódł się — zatrzymaj workflow.",
            )
        pulled = True
        sb = mirror_run_git(["status", "-sb"], mirror, lines)
        first = (sb.stdout or "").splitlines()[0] if sb.stdout else ""
        ahead, behind, diverged = _parse_branch_tracking(first)

    msg = f"{branch}...origin/{branch}"
    if ahead:
        msg += f" [ahead {ahead}]"
    if behind:
        msg += f" [behind {behind}]"
    if pulled:
        msg += " (po ff-only pull)"

    return BranchSyncStatus(ok=not diverged, ahead=ahead, behind=0 if pulled else behind, message=msg, pulled=pulled)


def _git_ignored(mirror: Path, rel: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(mirror), "check-ignore", "-q", "--", rel],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _skip_secret_scan(rel: str) -> bool:
    n = _norm_rel(rel)
    return n.startswith("tests/") or "/tests/" in n


def _assignment_value(line: str) -> str:
    if "=" not in line:
        return ""
    return line.split("=", 1)[1].strip().strip('"').strip("'")


def _is_runtime_mirror_path(rel: str) -> bool:
    n = _norm_rel(rel).rstrip("/")
    if n in MIRROR_RUNTIME_DENYLIST:
        return True
    for prefix in MIRROR_RUNTIME_DENYLIST:
        if prefix.endswith("/") and n.startswith(prefix):
            return True
    name = Path(n).name
    if name.startswith(".env"):
        return True
    if n.startswith("cursor-api/"):
        return True
    return False


def scan_file_secrets(path: Path, *, rel: str = "") -> list[str]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    hits: list[str] = []
    rel_s = rel or path.as_posix()
    if _skip_secret_scan(rel_s):
        return hits

    for line_no, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("#"):
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append(f"{rel_s}:{line_no}: {label}")
        for marker in LOOSE_SECRET_MARKERS:
            if marker not in line:
                continue
            value = _assignment_value(line)
            if not value or len(value) < 8:
                continue
            hits.append(f"{rel_s}:{line_no}: {marker}")
    return hits


def _parse_porcelain(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    new_files: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for ln in lines:
        if len(ln) < 4:
            continue
        code = ln[:2]
        path = ln[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if code == "??":
            new_files.append(path)
        elif code[0] == "D" or code[1] == "D":
            deleted.append(path)
        else:
            modified.append(path)
    return new_files, modified, deleted


def _commit_message_for(session: ReviewSession) -> str:
    msg = session.commit_message().strip()
    if msg:
        return msg
    return GICLEEART_GPT_FALLBACK_COMMIT_DESC


def audit_mirror_repo(
    mirror: Path,
    cfg: GptConfig,
    session: ReviewSession,
    sync: SyncResult | None = None,
    *,
    log: OnLine = None,
) -> GicleeArtGptAuditReport:
    lines = log if log is not None else []
    report = GicleeArtGptAuditReport(sync=sync, commit_message=_commit_message_for(session))

    try:
        validate_mirror_config(cfg, log=lines)
        _assert_mirror_git(mirror, cfg, lines)
    except (ValueError, RuntimeError) as exc:
        report.error = str(exc)
        report.blocked = True
        return report

    branch = (cfg.branch or "main").strip()
    report.branch_status = inspect_mirror_branch_sync(mirror, branch, pull_ff_only=False, log=lines)
    if report.branch_status.diverged:
        report.blocked = True
        report.error = report.branch_status.message
        return report

    status_proc = mirror_run_git(["status", "--short"], mirror, lines)
    porcelain = [ln for ln in (status_proc.stdout or "").splitlines() if ln.strip()]
    report.new_files, report.modified_files, report.deleted_files = _parse_porcelain(porcelain)

    if sync and sync.removed_stale:
        report.removed_stale = list(sync.removed_stale)

    stat_proc = mirror_run_git(["diff", "--stat"], mirror, lines)
    report.diff_stat = (stat_proc.stdout or "").strip()
    mirror_run_git(["diff", "--name-status"], mirror, lines)

    all_deleted = set(report.deleted_files) | set(report.removed_stale)
    for path in all_deleted:
        if _norm_rel(path) in MIRROR_PROTECTED_DELETIONS:
            report.blocked_deletions.append(path)
    report.deletable_files = sorted(
        p for p in all_deleted if _norm_rel(p) not in MIRROR_PROTECTED_DELETIONS
    )

    all_changed = report.new_files + report.modified_files
    candidates: list[str] = []

    for rel in all_changed:
        n = _norm_rel(rel)
        if _git_ignored(mirror, n):
            continue
        if _is_runtime_mirror_path(n):
            report.runtime_hits.append(n)
            continue
        if _skip_secret_scan(n):
            candidates.append(n)
            continue
        hits = scan_file_secrets(mirror / n, rel=n)
        if hits:
            report.secret_hits.extend(hits)
            continue
        candidates.append(n)

    report.commit_candidates = sorted(set(candidates))

    if report.secret_hits:
        report.blocked = True

    if not report.commit_candidates and not report.deletable_files:
        report.no_changes = True

    return report


def dry_run_gicleeart_gpt_push(
    cfg: GptConfig,
    session: ReviewSession,
    *,
    skip_sync: bool = False,
    sync_result: SyncResult | None = None,
    include_recordings: bool = False,
    log: OnLine = None,
) -> GicleeArtGptAuditReport:
    lines = log if log is not None else []
    report = GicleeArtGptAuditReport()

    try:
        validate_mirror_config(cfg, log=lines)
    except ValueError as exc:
        report.error = str(exc)
        report.blocked = True
        return report

    mirror = ensure_mirror_clone(cfg, lines)

    sync = sync_result
    if not skip_sync:
        if include_recordings:
            from .record import record_preview
            from .review_session import route_from_url

            rec = record_preview(
                prefer_local=cfg.prefer_local_theme_dev,
                scroll_seconds=cfg.record_scroll_seconds,
                wait_hero_seconds=cfg.record_wait_hero_seconds,
                log=lines,
            )
            if rec.ok:
                session.routes_recorded = [route_from_url(rec.url_used)]
            else:
                lines.append(f"Nagranie pominięte: {rec.message}")

        _log(lines, "=== Sync motywu → .gpt_mirror ===")
        sync = sync_theme_to_mirror(mirror, session=session, log=lines)
        if not sync.ok:
            report.error = "; ".join(sync.errors)
            report.blocked = True
            report.sync = sync
            return report

    audit = audit_mirror_repo(mirror, cfg, session, sync, log=lines)
    return audit


def commit_and_push_gicleeart_gpt(
    report: GicleeArtGptAuditReport,
    cfg: GptConfig,
    session: ReviewSession,
    *,
    include_deletions: bool = False,
    log: OnLine = None,
) -> GicleeArtGptPushResult:
    if report.blocked:
        return GicleeArtGptPushResult(ok=False, message="Workflow zablokowany — napraw audyt.")
    if report.no_changes:
        return GicleeArtGptPushResult(ok=True, message="Brak zmian — gicleeart-gpt jest aktualne.")
    if not report.commit_candidates and not (include_deletions and report.deletable_files):
        return GicleeArtGptPushResult(ok=True, message="Brak bezpiecznych plików do commita.")

    lines = log if log is not None else []
    mirror = MIRROR_DIR
    branch = (cfg.branch or "main").strip()
    sync = report.sync or SyncResult()

    try:
        validate_mirror_config(cfg, log=lines)
        mirror = ensure_mirror_clone(cfg, lines)
        _assert_mirror_git(mirror, cfg, lines)
    except (ValueError, RuntimeError) as exc:
        return GicleeArtGptPushResult(ok=False, message=str(exc))

    branch_status = inspect_mirror_branch_sync(mirror, branch, pull_ff_only=True, log=lines)
    if not branch_status.ok:
        return GicleeArtGptPushResult(ok=False, message=branch_status.message)

    paths_to_stage = list(report.commit_candidates)
    if include_deletions:
        paths_to_stage.extend(report.deletable_files)

    if not paths_to_stage:
        return GicleeArtGptPushResult(ok=False, message="Brak ścieżek do git add.")

    for rel in paths_to_stage:
        add = mirror_run_git(["add", "--", rel], mirror, lines)
        if add.returncode != 0:
            return GicleeArtGptPushResult(ok=False, message=f"git add nie powiódł się: {rel}")

    msg = report.commit_message or _commit_message_for(session)
    commit = mirror_run_git(["commit", "-m", msg], mirror, lines)
    if commit.returncode != 0:
        err = (commit.stderr or commit.stdout or "").strip()
        return GicleeArtGptPushResult(ok=False, message=err or "git commit nie powiódł się.")

    sha = _finalize_manifest_snapshot_commit(mirror, sync, session, lines)
    _verify_manifest_snapshot_commit(mirror, sha, lines)

    push = mirror_run_git(["push", "-u", "origin", branch], mirror, lines)
    if push.returncode != 0:
        push = mirror_run_git(["push", "--set-upstream", "origin", branch], mirror, lines)
    if push.returncode != 0:
        err = (push.stderr or push.stdout or "").strip()
        return GicleeArtGptPushResult(
            ok=False,
            commit_sha=sha,
            committed_files=paths_to_stage,
            message=err or "git push nie powiódł się — sprawdź auth GitHub.",
        )

    final = mirror_run_git(["status", "-sb"], mirror, lines)
    status_line = (final.stdout or "").strip()
    _log(lines, f"Push OK: {sha[:12]}")
    return GicleeArtGptPushResult(
        ok=True,
        commit_sha=sha,
        committed_files=paths_to_stage,
        message=f"GicleeArt-GPT zaktualizowane — {sha[:12]} ({status_line})",
    )
