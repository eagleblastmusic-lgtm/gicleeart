"""Bezpieczny push Giclee Viewer → eagleblastmusic-lgtm/giclee-viewer na GitHub."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    GICLEE_VIEWER_BRANCH,
    GICLEE_VIEWER_COMMIT_MESSAGE,
    GICLEE_VIEWER_DIR,
    GICLEE_VIEWER_REMOTE_URL,
    GICLEE_VIEWER_RUNTIME_DIR_NAMES,
    GICLEE_VIEWER_RUNTIME_FILE_SUFFIXES,
)
from .gicleeapp_push import (
    BranchSyncStatus,
    _parse_branch_tracking,
    _run_git,
    scan_file_secrets,
)

OnLine = list[str] | None

_GIT_ADD_BATCH_SIZE = 100


@dataclass
class GicleeViewerAuditReport:
    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    deletable_files: list[str] = field(default_factory=list)
    commit_candidates: list[str] = field(default_factory=list)
    diff_stat: str = ""
    secret_hits: list[str] = field(default_factory=list)
    runtime_hits: list[str] = field(default_factory=list)
    branch_status: BranchSyncStatus = field(default_factory=BranchSyncStatus)
    unpushed_commits: int = 0
    push_only: bool = False
    initial_push: bool = False
    blocked: bool = False
    no_changes: bool = False
    commit_message: str = GICLEE_VIEWER_COMMIT_MESSAGE
    error: str = ""

    def format_report(self) -> list[str]:
        lines = ["=== Push Giclee Viewer — audyt ==="]
        if self.error:
            lines.append(f"BŁĄD: {self.error}")
            return lines
        bs = self.branch_status
        if bs.message:
            lines.append(f"Branch: {bs.message}")
        if self.unpushed_commits:
            lines.append(f"Commity lokalne do wypchnięcia: {self.unpushed_commits}")
        if self.initial_push:
            lines.append("Pierwszy push — repo GitHub jest puste (brak brancha na origin).")
        lines.append("")
        lines.append(f"Nowe ({len(self.new_files)}):")
        lines.extend(f"  + {p}" for p in self.new_files[:40])
        lines.append(f"Zmienione ({len(self.modified_files)}):")
        lines.extend(f"  M {p}" for p in self.modified_files[:40])
        if self.deleted_files:
            lines.append(f"Usunięte (git) ({len(self.deleted_files)}):")
            lines.extend(f"  D {p}" for p in self.deleted_files[:40])
        if self.diff_stat.strip():
            lines.append("")
            lines.append("diff --stat:")
            lines.extend(self.diff_stat.strip().splitlines())
        lines.append("")
        lines.append(f"Kandydaci do commita: {len(self.commit_candidates)}")
        if self.runtime_hits:
            lines.append("Runtime / poza commitem:")
            lines.extend(f"  ⚠ {h}" for h in self.runtime_hits[:20])
        if self.secret_hits:
            lines.append("SEKRETY — commit zablokowany:")
            lines.extend(f"  ✖ {h}" for h in self.secret_hits)
        if self.blocked:
            lines.append("")
            lines.append("WORKFLOW ZATRZYMANY — napraw blokady przed pushem.")
        elif self.no_changes:
            lines.append("")
            lines.append("Brak zmian — giclee-viewer jest aktualne na GitHub.")
        elif self.push_only:
            lines.append("")
            lines.append("Working tree clean — push istniejących commitów (bez nowego commita).")
            lines.append("Potwierdź push w oknie dialogowym.")
        else:
            lines.append("")
            lines.append(f"Proponowany commit: {self.commit_message}")
            lines.append("Potwierdź push w oknie dialogowym.")
        return lines


@dataclass
class GicleeViewerPushResult:
    ok: bool
    commit_sha: str = ""
    committed_files: list[str] = field(default_factory=list)
    pushed_commits: int = 0
    push_only: bool = False
    message: str = ""


def _log(lines: OnLine, msg: str) -> None:
    if lines is not None:
        lines.append(msg)


def _norm_rel(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("./")


def _assert_giclee_viewer_remote(remote_url: str) -> None:
    u = remote_url.rstrip("/").lower()
    if "giclee-viewer" not in u:
        raise ValueError(f"origin musi wskazywać giclee-viewer: {remote_url}")
    if "gicleeapp" in u or "gicleeart" in u:
        raise ValueError(f"origin wskazuje złe repo: {remote_url}")


def ensure_viewer_remote(
    repo_dir: Path | None = None,
    *,
    log: OnLine = None,
) -> str:
    repo = repo_dir or GICLEE_VIEWER_DIR
    proc = _run_git(["remote", "get-url", "origin"], repo, log=log)
    remote = (proc.stdout or "").strip()
    if proc.returncode == 0 and remote:
        _assert_giclee_viewer_remote(remote)
        return remote
    _log(log, f"Brak origin — dodaję {GICLEE_VIEWER_REMOTE_URL}")
    add = _run_git(["remote", "add", "origin", GICLEE_VIEWER_REMOTE_URL], repo, log=log)
    if add.returncode != 0:
        raise RuntimeError("Nie udało się dodać remote origin dla giclee-viewer.")
    return GICLEE_VIEWER_REMOTE_URL


def validate_viewer_repo(
    repo_dir: Path | None = None,
    *,
    log: OnLine = None,
) -> Path:
    repo = repo_dir or GICLEE_VIEWER_DIR
    if not repo.is_dir():
        raise FileNotFoundError(f"Brak katalogu Giclee Viewer: {repo}")
    if not (repo / ".git").is_dir():
        raise FileNotFoundError(f"Giclee Viewer nie jest repozytorium git: {repo}")
    ensure_viewer_remote(repo, log=log)
    branch_proc = _run_git(["branch", "--show-current"], repo, log=log)
    branch = (branch_proc.stdout or "").strip()
    if branch and branch != GICLEE_VIEWER_BRANCH:
        _log(log, f"Uwaga: aktywny branch {branch!r}, oczekiwany {GICLEE_VIEWER_BRANCH!r}")
    return repo


def remote_branch_exists(repo: Path, *, log: OnLine = None) -> bool:
    ls = _run_git(["ls-remote", "--heads", "origin", GICLEE_VIEWER_BRANCH], repo, log=log)
    return ls.returncode == 0 and bool((ls.stdout or "").strip())


def inspect_viewer_branch_sync(
    repo: Path,
    *,
    pull_ff_only: bool = False,
    require_fetch: bool = False,
    log: OnLine = None,
) -> BranchSyncStatus:
    if not remote_branch_exists(repo, log=log):
        _log(
            log,
            f"Origin nie ma jeszcze brancha {GICLEE_VIEWER_BRANCH} — pierwszy push (fetch/pull pominięte).",
        )
        return BranchSyncStatus(
            ok=True,
            message=f"{GICLEE_VIEWER_BRANCH} (pierwszy push — remote bez brancha)",
        )

    fetch = _run_git(["fetch", "origin", GICLEE_VIEWER_BRANCH], repo, log=log)
    if fetch.returncode != 0:
        if require_fetch or pull_ff_only:
            return BranchSyncStatus(ok=False, message="git fetch origin nie powiódł się.")
        _log(log, "Uwaga: git fetch origin nie powiódł się — kontynuuję z lokalnym statusem.")

    sb = _run_git(["status", "-sb"], repo, log=log)
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
        pull = _run_git(
            ["pull", "--ff-only", "origin", GICLEE_VIEWER_BRANCH],
            repo,
            log=log,
        )
        if pull.returncode != 0:
            return BranchSyncStatus(
                ok=False,
                ahead=ahead,
                behind=behind,
                message="git pull --ff-only nie powiódł się — zatrzymaj workflow.",
            )
        pulled = True
        sb = _run_git(["status", "-sb"], repo, log=log)
        first = (sb.stdout or "").splitlines()[0] if sb.stdout else ""
        ahead, behind, diverged = _parse_branch_tracking(first)

    msg = f"{GICLEE_VIEWER_BRANCH}...origin/{GICLEE_VIEWER_BRANCH}"
    if ahead:
        msg += f" [ahead {ahead}]"
    if behind:
        msg += f" [behind {behind}]"
    if pulled:
        msg += " (po ff-only pull)"

    return BranchSyncStatus(
        ok=True,
        ahead=ahead,
        behind=0 if pulled else behind,
        message=msg,
        pulled=pulled,
    )


def count_unpushed_commits(repo: Path, *, log: OnLine = None) -> int:
    ls = _run_git(["ls-remote", "--heads", "origin", GICLEE_VIEWER_BRANCH], repo, log=log)
    if ls.returncode != 0 or not (ls.stdout or "").strip():
        count_proc = _run_git(["rev-list", "--count", GICLEE_VIEWER_BRANCH], repo, log=log)
        try:
            return int((count_proc.stdout or "0").strip())
        except ValueError:
            return 0
    count_proc = _run_git(
        ["rev-list", "--count", f"origin/{GICLEE_VIEWER_BRANCH}..HEAD"],
        repo,
        log=log,
    )
    try:
        return int((count_proc.stdout or "0").strip())
    except ValueError:
        return 0


def _parse_porcelain(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    new_files: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for ln in lines:
        if len(ln) < 4:
            continue
        code = ln[:2]
        path = ln[3:].strip().strip('"')
        path = _norm_rel(path)
        if " -> " in path:
            path = _norm_rel(path.split(" -> ", 1)[1].strip().strip('"'))
        if code == "??":
            new_files.append(path)
        elif code[0] == "D" or code[1] == "D":
            deleted.append(path)
        else:
            modified.append(path)
    return new_files, modified, deleted


def _is_runtime_viewer_path(rel: str) -> bool:
    n = _norm_rel(rel).rstrip("/")
    if not n:
        return True
    parts = Path(n).parts
    lowered = {p.lower() for p in parts}
    if lowered & {name.lower() for name in GICLEE_VIEWER_RUNTIME_DIR_NAMES}:
        return True
    if any(part in GICLEE_VIEWER_RUNTIME_DIR_NAMES for part in parts):
        return True
    name = Path(n).name
    if name in {".DS_Store", "Thumbs.db", "desktop.ini"}:
        return True
    if any(name.endswith(suffix) for suffix in GICLEE_VIEWER_RUNTIME_FILE_SUFFIXES):
        return True
    if name.startswith("~$"):
        return True
    return False


def _git_ignored(repo: Path, rel: str) -> bool:
    proc = _run_git(["check-ignore", "-q", "--", rel], repo)
    return proc.returncode == 0


def audit_viewer_repo(
    repo_dir: Path | None = None,
    *,
    log: OnLine = None,
) -> GicleeViewerAuditReport:
    report = GicleeViewerAuditReport()
    try:
        repo = validate_viewer_repo(repo_dir, log=log)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        report.error = str(exc)
        report.blocked = True
        return report

    report.branch_status = inspect_viewer_branch_sync(repo, log=log)
    if not report.branch_status.ok:
        report.error = report.branch_status.message
        report.blocked = True
        return report

    report.unpushed_commits = count_unpushed_commits(repo, log=log)
    report.initial_push = report.unpushed_commits > 0 and not remote_branch_exists(repo, log=log)

    porcelain = _run_git(["status", "--porcelain"], repo, log=log)
    new_all, modified_all, deleted_all = _parse_porcelain(
        (porcelain.stdout or "").splitlines()
    )

    report.new_files = sorted(new_all)
    report.modified_files = sorted(modified_all)
    report.deleted_files = sorted(deleted_all)
    report.deletable_files = list(report.deleted_files)

    candidates: list[str] = []
    for rel in report.new_files + report.modified_files:
        if _is_runtime_viewer_path(rel):
            report.runtime_hits.append(rel)
            continue
        if _git_ignored(repo, rel):
            report.runtime_hits.append(rel)
            continue
        full = repo / rel
        if not full.is_file():
            continue
        hits = scan_file_secrets(full, rel=rel)
        if hits:
            report.secret_hits.extend(hits)
            continue
        candidates.append(rel)

    report.commit_candidates = sorted(set(candidates))

    if report.secret_hits:
        report.blocked = True

    if report.commit_candidates or report.deletable_files:
        paths = report.commit_candidates + report.deletable_files
        stat = _run_git(["diff", "--stat", "--"] + paths, repo, log=log)
        report.diff_stat = (stat.stdout or "").strip()

    if report.commit_candidates or report.deletable_files:
        report.push_only = False
        report.no_changes = False
    elif report.unpushed_commits > 0:
        report.push_only = True
        report.no_changes = False
    else:
        report.no_changes = True

    return report


def dry_run_giclee_viewer_push(
    *,
    repo_dir: Path | None = None,
    log: OnLine = None,
) -> GicleeViewerAuditReport:
    return audit_viewer_repo(repo_dir, log=log)


def _git_add_paths(repo: Path, paths: list[str], *, log: OnLine = None) -> subprocess.CompletedProcess[str] | None:
    if not paths:
        return None
    for i in range(0, len(paths), _GIT_ADD_BATCH_SIZE):
        batch = paths[i : i + _GIT_ADD_BATCH_SIZE]
        proc = _run_git(["add", "--", *batch], repo, log=log)
        if proc.returncode != 0:
            return proc
    return None


def _unstage_all(repo: Path, *, log: OnLine = None) -> None:
    _run_git(["reset", "HEAD"], repo, log=log)


def _verify_staged_paths(repo: Path, expected: list[str], *, log: OnLine = None) -> list[str]:
    proc = _run_git(["diff", "--cached", "--name-only"], repo, log=log)
    staged = {_norm_rel(p) for p in (proc.stdout or "").splitlines() if p.strip()}
    expected_set = {_norm_rel(p) for p in expected}
    extra = sorted(staged - expected_set)
    blocked = [p for p in extra if _is_runtime_viewer_path(p)]
    blocked.extend(p for p in extra if p not in blocked)
    return blocked


def commit_and_push_giclee_viewer(
    report: GicleeViewerAuditReport,
    *,
    repo_dir: Path | None = None,
    include_deletions: bool = False,
    commit_message: str | None = None,
    log: OnLine = None,
) -> GicleeViewerPushResult:
    if report.blocked:
        return GicleeViewerPushResult(ok=False, message="Workflow zablokowany — napraw audyt.")
    if report.no_changes:
        return GicleeViewerPushResult(ok=True, message="Brak zmian — giclee-viewer jest aktualne.")

    try:
        repo = validate_viewer_repo(repo_dir, log=log)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        return GicleeViewerPushResult(ok=False, message=str(exc))

    remote_has_branch = remote_branch_exists(repo, log=log)
    branch_status = inspect_viewer_branch_sync(
        repo,
        pull_ff_only=remote_has_branch,
        require_fetch=remote_has_branch,
        log=log,
    )
    if not branch_status.ok:
        return GicleeViewerPushResult(ok=False, message=branch_status.message)

    sha = ""
    paths_to_stage: list[str] = []
    push_only = report.push_only and not report.commit_candidates and not (
        include_deletions and report.deletable_files
    )

    if not push_only:
        paths_to_stage = list(report.commit_candidates)
        if include_deletions:
            paths_to_stage.extend(report.deletable_files)
        paths_to_stage = sorted({_norm_rel(p) for p in paths_to_stage})

        if not paths_to_stage:
            return GicleeViewerPushResult(ok=False, message="Brak ścieżek do git add.")

        for rel in paths_to_stage:
            if _is_runtime_viewer_path(rel):
                return GicleeViewerPushResult(
                    ok=False,
                    message=f"Ścieżka runtime poza commitem: {rel}",
                )

        add_err = _git_add_paths(repo, paths_to_stage, log=log)
        if add_err is not None:
            _unstage_all(repo, log=log)
            return GicleeViewerPushResult(
                ok=False,
                message=f"git add nie powiódł się: {(add_err.stderr or add_err.stdout or '').strip()}",
            )

        blocked_staged = _verify_staged_paths(repo, paths_to_stage, log=log)
        if blocked_staged:
            _unstage_all(repo, log=log)
            preview = ", ".join(blocked_staged[:8])
            extra = f" (+{len(blocked_staged) - 8} więcej)" if len(blocked_staged) > 8 else ""
            return GicleeViewerPushResult(
                ok=False,
                message=f"Staging zawiera niedozwolone ścieżki — push przerwany: {preview}{extra}",
            )

        msg = (commit_message or report.commit_message or GICLEE_VIEWER_COMMIT_MESSAGE).strip()
        commit = _run_git(["commit", "-m", msg], repo, log=log)
        if commit.returncode != 0:
            err = (commit.stderr or commit.stdout or "").strip()
            return GicleeViewerPushResult(ok=False, message=err or "git commit nie powiódł się.")

    sha_proc = _run_git(["rev-parse", "HEAD"], repo, log=log)
    sha = (sha_proc.stdout or "").strip()
    unpushed_before = count_unpushed_commits(repo, log=log)

    push = _run_git(["push", "-u", "origin", GICLEE_VIEWER_BRANCH], repo, log=log)
    if push.returncode != 0:
        err = (push.stderr or push.stdout or "").strip()
        return GicleeViewerPushResult(
            ok=False,
            commit_sha=sha,
            committed_files=paths_to_stage,
            message=err or "git push nie powiódł się — sprawdź auth GitHub.",
        )

    final_status = _run_git(["status", "-sb"], repo, log=log)
    status_line = (final_status.stdout or "").strip()
    _log(log, f"Push OK: {sha[:12]}")

    if push_only:
        msg = f"Giclee Viewer wypchnięte ({unpushed_before} commitów) — {sha[:12]} ({status_line})"
    else:
        msg = f"Giclee Viewer zaktualizowane — {sha[:12]} ({status_line})"

    return GicleeViewerPushResult(
        ok=True,
        commit_sha=sha,
        committed_files=paths_to_stage,
        pushed_commits=unpushed_before if push_only else max(unpushed_before, 1),
        push_only=push_only,
        message=msg,
    )
