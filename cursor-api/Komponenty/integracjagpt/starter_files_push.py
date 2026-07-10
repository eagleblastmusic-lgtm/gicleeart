"""Bezpieczny push plików startowych GPT → monorepo (origin/master)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    GPT_STARTER_DIR,
    GPT_STARTER_REL_PREFIX,
    GPT_STARTER_ZIP_NAME,
    GPT_START_MESSAGE_FILE,
    MONOREPO_BRANCH,
    STARTER_FILES_COMMIT_MESSAGE,
    THEME_ROOT,
)
from .gicleeapp_push import (
    BranchSyncStatus,
    _parse_branch_tracking,
    _run_git,
    scan_file_secrets,
)
from .zip_knowledge import CLEAN_PACK_V38_ACTIVE_FILES, build_starter_knowledge_zip

OnLine = list[str] | None

_GIT_ADD_BATCH_SIZE = 100


@dataclass
class StarterFilesAuditReport:
    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    deletable_files: list[str] = field(default_factory=list)
    commit_candidates: list[str] = field(default_factory=list)
    diff_stat: str = ""
    secret_hits: list[str] = field(default_factory=list)
    outside_allowlist_hits: list[str] = field(default_factory=list)
    branch_status: BranchSyncStatus = field(default_factory=BranchSyncStatus)
    blocked: bool = False
    no_changes: bool = False
    commit_message: str = STARTER_FILES_COMMIT_MESSAGE
    zip_rebuilt: bool = False
    error: str = ""

    def format_report(self) -> list[str]:
        lines = ["=== Push plików startowych GPT — audyt ==="]
        if self.error:
            lines.append(f"BŁĄD: {self.error}")
            return lines
        if self.zip_rebuilt:
            lines.append(f"ZIP przebudowany: {GPT_STARTER_REL_PREFIX}/{GPT_STARTER_ZIP_NAME}")
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
        if self.diff_stat.strip():
            lines.append("")
            lines.append("diff --stat:")
            lines.extend(self.diff_stat.strip().splitlines())
        lines.append("")
        lines.append(f"Kandydaci do commita: {len(self.commit_candidates)}")
        if self.outside_allowlist_hits:
            lines.append("Poza allowlistą (nie trafią do commita):")
            lines.extend(f"  ⚠ {h}" for h in self.outside_allowlist_hits[:20])
        if self.secret_hits:
            lines.append("SEKRETY — commit zablokowany:")
            lines.extend(f"  ✖ {h}" for h in self.secret_hits)
        if self.blocked:
            lines.append("")
            lines.append("WORKFLOW ZATRZYMANY — napraw blokady przed pushem.")
        elif self.no_changes:
            lines.append("")
            lines.append("Brak zmian w plikach startowych GPT — monorepo jest aktualne.")
        else:
            lines.append("")
            lines.append(f"Proponowany commit: {self.commit_message}")
            lines.append("Potwierdź push w oknie dialogowym.")
        return lines


@dataclass
class StarterFilesPushResult:
    ok: bool
    commit_sha: str = ""
    committed_files: list[str] = field(default_factory=list)
    message: str = ""


def _log(lines: OnLine, msg: str) -> None:
    if lines is not None:
        lines.append(msg)


def _norm_rel(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("./")


def starter_push_allowlist_rel_paths() -> list[str]:
    names: list[str] = list(CLEAN_PACK_V38_ACTIVE_FILES)
    for extra in (GPT_START_MESSAGE_FILE, GPT_STARTER_ZIP_NAME):
        if extra not in names:
            names.append(extra)
    return [f"{GPT_STARTER_REL_PREFIX}/{name}" for name in names]


def _allowlist_set() -> frozenset[str]:
    return frozenset(starter_push_allowlist_rel_paths())


def validate_monorepo_repo(
    theme_root: Path | None = None,
    *,
    log: OnLine = None,
) -> None:
    root = theme_root or THEME_ROOT
    if not root.is_dir():
        raise FileNotFoundError(f"Brak katalogu monorepo: {root}")
    if not (root / ".git").is_dir():
        raise FileNotFoundError(f"Monorepo nie jest repozytorium git: {root}")
    starter = root / GPT_STARTER_REL_PREFIX
    if not starter.is_dir():
        raise FileNotFoundError(f"Brak folderu plików startowych: {starter}")

    branch_proc = _run_git(["branch", "--show-current"], root, log=log)
    branch = (branch_proc.stdout or "").strip()
    if branch and branch != MONOREPO_BRANCH:
        _log(log, f"Uwaga: aktywny branch {branch!r}, oczekiwany {MONOREPO_BRANCH!r}")


def inspect_monorepo_branch_sync(
    theme_root: Path,
    *,
    pull_ff_only: bool = False,
    require_fetch: bool = False,
    log: OnLine = None,
) -> BranchSyncStatus:
    fetch = _run_git(["fetch", "origin", MONOREPO_BRANCH], theme_root, log=log)
    if fetch.returncode != 0:
        if require_fetch or pull_ff_only:
            return BranchSyncStatus(ok=False, message="git fetch origin nie powiódł się.")
        _log(log, "Uwaga: git fetch origin nie powiódł się — kontynuuję z lokalnym statusem.")

    sb = _run_git(["status", "-sb"], theme_root, log=log)
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
            ["pull", "--ff-only", "origin", MONOREPO_BRANCH],
            theme_root,
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
        sb = _run_git(["status", "-sb"], theme_root, log=log)
        first = (sb.stdout or "").splitlines()[0] if sb.stdout else ""
        ahead, behind, diverged = _parse_branch_tracking(first)

    msg = f"{MONOREPO_BRANCH}...origin/{MONOREPO_BRANCH}"
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


def _rebuild_starter_zip(
    starter_dir: Path | None = None,
    *,
    log: OnLine = None,
) -> bool:
    try:
        zip_path = build_starter_knowledge_zip(starter_dir)
        _log(log, f"Przebudowano ZIP: {zip_path.name}")
        return True
    except Exception as exc:  # noqa: BLE001 — raportuj, nie blokuj całego audytu
        _log(log, f"Nie udało się przebudować ZIP: {exc}")
        return False


def audit_starter_files_repo(
    theme_root: Path | None = None,
    *,
    rebuild_zip: bool = True,
    log: OnLine = None,
) -> StarterFilesAuditReport:
    root = theme_root or THEME_ROOT
    report = StarterFilesAuditReport()

    try:
        validate_monorepo_repo(root, log=log)
    except (FileNotFoundError, ValueError) as exc:
        report.error = str(exc)
        report.blocked = True
        return report

    allowlist = _allowlist_set()
    starter_dir = root / GPT_STARTER_REL_PREFIX

    if rebuild_zip:
        report.zip_rebuilt = _rebuild_starter_zip(starter_dir, log=log)

    report.branch_status = inspect_monorepo_branch_sync(root, log=log)
    if not report.branch_status.ok:
        report.error = report.branch_status.message
        report.blocked = True
        return report

    porcelain = _run_git(["status", "--porcelain"], root, log=log)
    new_all, modified_all, deleted_all = _parse_porcelain(
        (porcelain.stdout or "").splitlines()
    )

    prefix = GPT_STARTER_REL_PREFIX + "/"

    def _in_scope(rel: str) -> bool:
        n = _norm_rel(rel)
        return n.startswith(prefix)

    for rel in new_all + modified_all + deleted_all:
        if not _in_scope(rel):
            continue
        if rel not in allowlist:
            report.outside_allowlist_hits.append(rel)

    new_files = [r for r in new_all if r in allowlist]
    modified_files = [r for r in modified_all if r in allowlist]
    deleted_files = [r for r in deleted_all if r in allowlist]

    report.new_files = sorted(new_files)
    report.modified_files = sorted(modified_files)
    report.deleted_files = sorted(deleted_files)
    report.deletable_files = list(report.deleted_files)

    candidates: list[str] = []
    for rel in report.new_files + report.modified_files:
        full = root / rel
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
        stat = _run_git(["diff", "--stat", "--"] + paths, root, log=log)
        report.diff_stat = (stat.stdout or "").strip()

    if not report.commit_candidates and not report.deletable_files:
        report.no_changes = True

    return report


def dry_run_starter_files_push(
    *,
    theme_root: Path | None = None,
    rebuild_zip: bool = True,
    log: OnLine = None,
) -> StarterFilesAuditReport:
    return audit_starter_files_repo(
        theme_root,
        rebuild_zip=rebuild_zip,
        log=log,
    )


def _git_add_paths(root: Path, paths: list[str], *, log: OnLine = None) -> subprocess.CompletedProcess[str] | None:
    if not paths:
        return None
    for i in range(0, len(paths), _GIT_ADD_BATCH_SIZE):
        batch = paths[i : i + _GIT_ADD_BATCH_SIZE]
        proc = _run_git(["add", "--", *batch], root, log=log)
        if proc.returncode != 0:
            return proc
    return None


def _unstage_all(root: Path, *, log: OnLine = None) -> None:
    _run_git(["reset", "HEAD"], root, log=log)


def _verify_staged_paths(root: Path, expected: list[str], *, log: OnLine = None) -> list[str]:
    proc = _run_git(["diff", "--cached", "--name-only"], root, log=log)
    staged = {_norm_rel(p) for p in (proc.stdout or "").splitlines() if p.strip()}
    expected_set = {_norm_rel(p) for p in expected}
    extra = sorted(staged - expected_set)
    return extra


def commit_and_push_starter_files(
    report: StarterFilesAuditReport,
    *,
    theme_root: Path | None = None,
    include_deletions: bool = False,
    commit_message: str | None = None,
    log: OnLine = None,
) -> StarterFilesPushResult:
    if report.blocked:
        return StarterFilesPushResult(ok=False, message="Workflow zablokowany — napraw audyt.")
    if report.no_changes:
        return StarterFilesPushResult(ok=True, message="Brak zmian — pliki startowe GPT są aktualne.")
    if not report.commit_candidates and not (include_deletions and report.deletable_files):
        return StarterFilesPushResult(ok=True, message="Brak bezpiecznych plików do commita.")

    root = theme_root or THEME_ROOT

    try:
        validate_monorepo_repo(root, log=log)
    except (FileNotFoundError, ValueError) as exc:
        return StarterFilesPushResult(ok=False, message=str(exc))

    branch_status = inspect_monorepo_branch_sync(root, pull_ff_only=True, require_fetch=True, log=log)
    if not branch_status.ok:
        return StarterFilesPushResult(ok=False, message=branch_status.message)

    paths_to_stage: list[str] = list(report.commit_candidates)
    if include_deletions:
        paths_to_stage.extend(report.deletable_files)
    paths_to_stage = sorted({_norm_rel(p) for p in paths_to_stage})

    if not paths_to_stage:
        return StarterFilesPushResult(ok=False, message="Brak ścieżek do git add.")

    allowlist = _allowlist_set()
    for rel in paths_to_stage:
        if rel not in allowlist:
            return StarterFilesPushResult(
                ok=False,
                message=f"Ścieżka poza allowlistą starterów: {rel}",
            )

    add_err = _git_add_paths(root, paths_to_stage, log=log)
    if add_err is not None:
        _unstage_all(root, log=log)
        return StarterFilesPushResult(
            ok=False,
            message=f"git add nie powiódł się: {(add_err.stderr or add_err.stdout or '').strip()}",
        )

    blocked_staged = _verify_staged_paths(root, paths_to_stage, log=log)
    if blocked_staged:
        _unstage_all(root, log=log)
        preview = ", ".join(blocked_staged[:8])
        extra = f" (+{len(blocked_staged) - 8} więcej)" if len(blocked_staged) - 8 > 0 else ""
        return StarterFilesPushResult(
            ok=False,
            message=f"Staging zawiera niedozwolone ścieżki — push przerwany: {preview}{extra}",
        )

    msg = (commit_message or report.commit_message or STARTER_FILES_COMMIT_MESSAGE).strip()
    commit = _run_git(["commit", "-m", msg], root, log=log)
    if commit.returncode != 0:
        err = (commit.stderr or commit.stdout or "").strip()
        return StarterFilesPushResult(ok=False, message=err or "git commit nie powiódł się.")

    sha_proc = _run_git(["rev-parse", "HEAD"], root, log=log)
    sha = (sha_proc.stdout or "").strip()

    push = _run_git(["push", "origin", MONOREPO_BRANCH], root, log=log)
    if push.returncode != 0:
        err = (push.stderr or push.stdout or "").strip()
        return StarterFilesPushResult(
            ok=False,
            commit_sha=sha,
            committed_files=paths_to_stage,
            message=err or "git push nie powiódł się — sprawdź auth GitHub.",
        )

    final_status = _run_git(["status", "-sb"], root, log=log)
    status_line = (final_status.stdout or "").strip()
    _log(log, f"Push OK: {sha[:12]}")

    return StarterFilesPushResult(
        ok=True,
        commit_sha=sha,
        committed_files=paths_to_stage,
        message=f"Pliki startowe GPT na GitHub — {sha[:12]} ({status_line})",
    )
