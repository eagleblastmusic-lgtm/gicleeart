"""Bezpieczny push snapshotu cursor-api → staging gicleeapp → GitHub."""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from tools.repository_safety.audit import TrackedTreeAuditReport, audit_tracked_tree
from tools.repository_safety.policy import classify_path
from tools.repository_safety.snapshot import (
    DEFAULT_MANIFEST_PATH,
    build_snapshot_plan,
    execute_snapshot_copy,
)

from .config import (
    CURSOR_API_DIR,
    GICLEEAPP_BRANCH,
    GICLEEAPP_COMMIT_MESSAGE,
    GICLEEAPP_NEVER_OVERWRITE,
    GICLEEAPP_REMOTE_URL,
    GICLEEAPP_REVIEW_ONLY_FILES,
    GICLEEAPP_RUNTIME_DENYLIST,
    GICLEEAPP_RUNTIME_DENYLIST_GLOBS,
    GICLEEAPP_RUNTIME_DENYLIST_PREFIXES,
    GICLEEAPP_RUNTIME_ROOT_GLOBS,
    GICLEEAPP_STAGING_DIR,
    GICLEEAPP_SYNC_SKIP_DIR_NAMES,
    GICLEEAPP_SYNC_SKIP_FILE_NAMES,
    GICLEEAPP_SYNC_SKIP_REL_PREFIXES,
    GICLEEAPP_THEME_PATH_PREFIXES,
)

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

_ENV_TEMPLATE_NAMES = frozenset({
    ".env.example",
    "env.example",
    ".env.sample",
})

_STAGING_JUNK_DIR_NAMES = frozenset({
    "gpt_mirror",
    "vscode",
    "pytest_cache",
})

_GIT_ADD_BATCH_SIZE = 100


@dataclass
class GicleeAppSyncResult:
    copied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    protected: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    manifest_path: str = ""
    source_git_sha: str = ""
    tree_sha256: str = ""
    included_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors and not self.blockers


@dataclass
class BranchSyncStatus:
    ok: bool = True
    ahead: int = 0
    behind: int = 0
    diverged: bool = False
    message: str = ""
    pulled: bool = False


@dataclass
class GicleeAppAuditReport:
    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    deletable_files: list[str] = field(default_factory=list)
    blocked_deletions: list[str] = field(default_factory=list)
    commit_candidates: list[str] = field(default_factory=list)
    diff_stat: str = ""
    secret_hits: list[str] = field(default_factory=list)
    runtime_hits: list[str] = field(default_factory=list)
    tracked_tree_blockers: list[str] = field(default_factory=list)
    tracked_tree_warnings: list[str] = field(default_factory=list)
    theme_related_changes: list[str] = field(default_factory=list)
    branch_status: BranchSyncStatus = field(default_factory=BranchSyncStatus)
    blocked: bool = False
    no_changes: bool = False
    commit_message: str = GICLEEAPP_COMMIT_MESSAGE
    sync: GicleeAppSyncResult | None = None
    error: str = ""

    def format_report(self) -> list[str]:
        lines = ["=== Push GicleeApp — audyt ==="]
        if self.error:
            lines.append(f"BŁĄD: {self.error}")
        if self.sync:
            lines.append(f"Allowlista: {self.sync.included_count} plików źródłowych")
            lines.append(f"Skopiowano: {len(self.sync.copied)} plików")
            if self.sync.unchanged:
                lines.append(f"Bez zmian: {len(self.sync.unchanged)}")
            if self.sync.skipped:
                lines.append(f"Pominięto (polityka): {len(self.sync.skipped)}")
            if self.sync.protected:
                lines.append(f"Chronione w stagingu: {len(self.sync.protected)}")
            if self.sync.manifest_path:
                lines.append(f"Manifest: {self.sync.manifest_path}")
            if self.sync.tree_sha256:
                lines.append(f"Tree SHA-256: {self.sync.tree_sha256}")
            if self.sync.blockers:
                lines.append("Blokady snapshotu:")
                lines.extend(f"  ✖ {item}" for item in self.sync.blockers[:40])
        bs = self.branch_status
        if bs.message:
            lines.append(f"Branch: {bs.message}")
        if self.tracked_tree_blockers:
            lines.append("")
            lines.append("TRACKED TREE — blokady:")
            lines.extend(f"  ✖ {item}" for item in self.tracked_tree_blockers[:80])
        if self.tracked_tree_warnings:
            lines.append("")
            lines.append("TRACKED TREE — ostrzeżenia:")
            lines.extend(f"  ⚠ {item}" for item in self.tracked_tree_warnings[:40])
        lines.append("")
        lines.append(f"Nowe ({len(self.new_files)}):")
        lines.extend(f"  + {p}" for p in self.new_files[:40])
        if len(self.new_files) > 40:
            lines.append(f"  … i {len(self.new_files) - 40} więcej")
        lines.append(f"Zmienione ({len(self.modified_files)}):")
        lines.extend(f"  M {p}" for p in self.modified_files[:40])
        if len(self.modified_files) > 40:
            lines.append(f"  … i {len(self.modified_files) - 40} więcej")
        if self.deleted_files:
            lines.append(f"Usunięte ({len(self.deleted_files)}):")
            lines.extend(f"  D {p}" for p in self.deleted_files[:40])
        if self.deletable_files:
            lines.append(f"Do ewentualnego usunięcia w commicie ({len(self.deletable_files)}):")
            lines.extend(f"  D {p}" for p in self.deletable_files[:40])
        if self.blocked_deletions:
            lines.append("Usunięcia zablokowane (review-only):")
            lines.extend(f"  ! {p}" for p in self.blocked_deletions)
        if self.diff_stat.strip():
            lines.append("")
            lines.append("diff --stat:")
            lines.extend(self.diff_stat.strip().splitlines())
        lines.append("")
        lines.append(f"Kandydaci do commita: {len(self.commit_candidates)}")
        if self.runtime_hits:
            lines.append("Runtime / poza commitem (wykluczone):")
            lines.extend(f"  ⚠ {h}" for h in self.runtime_hits)
        if self.secret_hits:
            lines.append("SEKRETY — commit zablokowany:")
            lines.extend(f"  ✖ {h}" for h in self.secret_hits)
        if self.theme_related_changes:
            lines.append("")
            lines.append("Uwaga: zmiany mogą wymagać osobnego snapshotu/review w gicleeart-gpt:")
            lines.extend(f"  → {p}" for p in self.theme_related_changes[:12])
        if self.blocked:
            lines.append("")
            lines.append("WORKFLOW ZATRZYMANY — napraw blokady przed pushem.")
        elif self.no_changes:
            lines.append("")
            lines.append("Brak zmian — gicleeapp jest aktualne.")
        else:
            lines.append("")
            lines.append(f"Proponowany commit: {self.commit_message}")
            lines.append("Potwierdź push w oknie dialogowym.")
        return lines


@dataclass
class GicleeAppPushResult:
    ok: bool
    commit_sha: str = ""
    committed_files: list[str] = field(default_factory=list)
    message: str = ""
    starter_sync_message: str = ""
    starter_sync_updated_files: list[str] = field(default_factory=list)


def _log(lines: OnLine, msg: str) -> None:
    if lines is not None:
        lines.append(msg)


def _run_git(args: list[str], cwd: Path, *, log: OnLine = None) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    _log(log, "$ " + " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip():
            _log(log, line)
    return proc


def _strip_git_path(path: str) -> str:
    """Usuwa cudzysłowy z git status --porcelain (ścieżki ze spacjami)."""
    p = path.strip()
    if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
        p = p[1:-1]
    return p.strip()


def _norm_rel(path: str | Path) -> str:
    p = _strip_git_path(str(path))
    p = Path(p).as_posix()
    if p.startswith("./"):
        return p[2:]
    return p


def _expand_path_entries(staging: Path, rel: str) -> list[str]:
    """Rozwiń wpis katalogu z git status do konkretnych plików."""
    n = _norm_rel(rel).rstrip("/")
    full = staging / n
    if not full.is_dir():
        return [n]
    expanded: list[str] = []
    for file_path in sorted(full.rglob("*")):
        if not file_path.is_file():
            continue
        child = _norm_rel(file_path.relative_to(staging))
        if _git_ignored(staging, child):
            continue
        expanded.append(child)
    return expanded or [n]


def _is_review_only(rel: str) -> bool:
    return _norm_rel(rel) in GICLEEAPP_REVIEW_ONLY_FILES


def _should_skip_sync(rel: str) -> bool:
    """Legacy compatibility helper; policy-driven snapshot is authoritative."""
    n = _norm_rel(rel)
    if not n:
        return True
    parts = Path(n).parts
    if any(p in GICLEEAPP_SYNC_SKIP_DIR_NAMES for p in parts):
        return True
    name = Path(n).name
    if name in GICLEEAPP_SYNC_SKIP_FILE_NAMES:
        return True
    if name.startswith(".env") or name in {"env", "env.example"}:
        return True
    for prefix in GICLEEAPP_SYNC_SKIP_REL_PREFIXES:
        if n.startswith(prefix.lstrip("/")) or n == prefix.rstrip("/"):
            return True
    return _is_root_scratch_path(n)


def _is_root_scratch_path(rel: str) -> bool:
    n = _norm_rel(rel).rstrip("/")
    if not n:
        return False
    parts = Path(n).parts
    if len(parts) == 1:
        return any(fnmatch.fnmatch(parts[0], pat) for pat in GICLEEAPP_RUNTIME_ROOT_GLOBS)
    return fnmatch.fnmatch(parts[0], "_tmp_*") or parts[0] in ("_test_out", "_czesc7_parts")


def _assert_gicleeapp_remote(remote_url: str) -> None:
    u = remote_url.rstrip("/").lower()
    if "gicleeapp" not in u:
        raise ValueError(f"origin nie wskazuje gicleeapp: {remote_url}")
    if "gicleeart-gpt" in u:
        raise ValueError(f"origin wskazuje gicleeart-gpt zamiast gicleeapp: {remote_url}")


def validate_staging_repo(staging_dir: Path | None = None, *, log: OnLine = None) -> None:
    staging = staging_dir or GICLEEAPP_STAGING_DIR
    if not staging.is_dir():
        raise FileNotFoundError(f"Brak katalogu staging: {staging}")
    if not (staging / ".git").is_dir():
        raise FileNotFoundError(f"Staging nie jest repozytorium git: {staging}")
    remote_proc = _run_git(["remote", "get-url", "origin"], staging, log=log)
    remote = (remote_proc.stdout or "").strip()
    if remote_proc.returncode != 0 or not remote:
        raise ValueError("Staging nie ma skonfigurowanego remote origin.")
    _assert_gicleeapp_remote(remote)
    branch_proc = _run_git(["branch", "--show-current"], staging, log=log)
    branch = (branch_proc.stdout or "").strip()
    if branch and branch != GICLEEAPP_BRANCH:
        _log(log, f"Uwaga: aktywny branch {branch!r}, oczekiwany {GICLEEAPP_BRANCH!r}")


def merge_staging_gitignore(source_dir: Path, staging_dir: Path, *, log: OnLine = None) -> bool:
    """Temporary compatibility merge; staging .gitignore remains protected from replacement."""
    src_file = source_dir / ".gitignore"
    dst_file = staging_dir / ".gitignore"
    if not src_file.is_file() or not dst_file.is_file():
        return False
    existing = dst_file.read_text(encoding="utf-8").splitlines()
    existing_set = {ln.strip() for ln in existing if ln.strip() and not ln.strip().startswith("#")}
    added: list[str] = []
    for raw in src_file.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped in existing_set:
            continue
        added.append(line)
        existing_set.add(stripped)
    if not added:
        return False
    new_content = dst_file.read_text(encoding="utf-8").rstrip() + "\n\n"
    new_content += "# --- reguły dopisane z cursor-api (auto merge) ---\n"
    new_content += "\n".join(added) + "\n"
    dst_file.write_text(new_content, encoding="utf-8")
    _log(log, f"Rozszerzono .gitignore stagingu (+{len(added)} reguł)")
    return True


def safe_sync_to_staging(
    source_dir: Path | None = None,
    staging_dir: Path | None = None,
    *,
    log: OnLine = None,
) -> GicleeAppSyncResult:
    source = source_dir or CURSOR_API_DIR
    staging = staging_dir or GICLEEAPP_STAGING_DIR
    result = GicleeAppSyncResult(manifest_path=DEFAULT_MANIFEST_PATH)
    if not source.is_dir():
        result.errors.append(f"Brak źródła: {source}")
        return result
    staging.mkdir(parents=True, exist_ok=True)

    plan = build_snapshot_plan(
        source,
        staging,
        protected_paths=GICLEEAPP_NEVER_OVERWRITE,
    )
    result.source_git_sha = plan.source_git_sha
    result.tree_sha256 = plan.tree_sha256
    result.included_count = len(plan.included_paths)
    result.skipped = [item.path for item in plan.skipped_paths]
    result.blockers = [
        f"{item.rule_id} {item.path}" + (f":{item.line}" if item.line is not None else "")
        for item in plan.blockers
    ]
    if plan.errors:
        result.errors.extend(plan.errors)
    if not plan.ok:
        if not result.errors:
            result.errors.append("Snapshot allowlist zawiera blokady — niczego nie skopiowano.")
        return result

    copied = execute_snapshot_copy(plan)
    result.copied = list(copied.copied)
    result.unchanged = list(copied.unchanged)
    result.protected = list(copied.protected)
    result.errors.extend(copied.errors)
    if copied.manifest_written:
        result.copied.append(plan.manifest_path)
    merge_staging_gitignore(source, staging, log=log)
    return result


def _parse_branch_tracking(status_line: str) -> tuple[int, int, bool]:
    ahead = behind = 0
    if "[" not in status_line:
        return ahead, behind, False
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
    return ahead, behind, ahead > 0 and behind > 0


def inspect_branch_sync(
    staging_dir: Path,
    *,
    pull_ff_only: bool = False,
    log: OnLine = None,
) -> BranchSyncStatus:
    fetch = _run_git(["fetch", "origin", GICLEEAPP_BRANCH], staging_dir, log=log)
    if fetch.returncode != 0:
        return BranchSyncStatus(ok=False, message="git fetch origin nie powiódł się.")
    sb = _run_git(["status", "-sb"], staging_dir, log=log)
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
        pull = _run_git(["pull", "--ff-only", "origin", GICLEEAPP_BRANCH], staging_dir, log=log)
        if pull.returncode != 0:
            return BranchSyncStatus(
                ok=False,
                ahead=ahead,
                behind=behind,
                message="git pull --ff-only nie powiódł się — zatrzymaj workflow.",
            )
        pulled = True
        sb = _run_git(["status", "-sb"], staging_dir, log=log)
        first = (sb.stdout or "").splitlines()[0] if sb.stdout else ""
        ahead, behind, diverged = _parse_branch_tracking(first)
    msg = f"{GICLEEAPP_BRANCH}...origin/{GICLEEAPP_BRANCH}"
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


def _git_ignored(staging_dir: Path, rel: str) -> bool:
    return _run_git(["check-ignore", "-q", "--", rel], staging_dir).returncode == 0


def _assignment_value(line: str) -> str:
    return line.split("=", 1)[1].strip().strip('"').strip("'") if "=" in line else ""


def _is_env_template_line(rel_s: str, line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    if Path(rel_s).name.lower() not in _ENV_TEMPLATE_NAMES:
        return False
    value = _assignment_value(line)
    return not value or len(value) < 8


def _is_runtime_path(rel: str) -> bool:
    n = _norm_rel(rel).rstrip("/")
    if n in GICLEEAPP_RUNTIME_DENYLIST:
        return True
    for prefix in GICLEEAPP_RUNTIME_DENYLIST_PREFIXES:
        p = prefix.rstrip("/")
        if n == p or n.startswith(prefix):
            return True
    if any(fnmatch.fnmatch(n, pattern) for pattern in GICLEEAPP_RUNTIME_DENYLIST_GLOBS):
        return True
    if _is_root_scratch_path(n):
        return True
    name = Path(n).name
    if name in _ENV_TEMPLATE_NAMES or name in {
        "env", "env.example", "gitignore", "shopify_session.json", "graphqlrc.js", "npmrc"
    }:
        return True
    if name.startswith(".env"):
        return True
    if any(part in _STAGING_JUNK_DIR_NAMES for part in Path(n).parts):
        return True
    if name.endswith((".log", ".db", ".zip")) and "example" not in name:
        if "gpt_config.example" not in n and "kpir_settings.example" not in n:
            return True
    decision = classify_path(n)
    return not decision.tracked_allowed


def _skip_secret_scan(rel: str) -> bool:
    n = _norm_rel(rel)
    return n.startswith("tests/") or "/tests/" in n


def _is_secret_test_fixture(path: str, line: str) -> bool:
    if _skip_secret_scan(path):
        return True
    if "test_" not in path and not path.startswith("tests/"):
        return False
    fixtures = ("secret-from-obs", "secret.json", "test-secret", '"secret"', "no secret")
    return any(item in line for item in fixtures)


def scan_file_secrets(path: Path, *, rel: str = "") -> list[str]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    hits: list[str] = []
    rel_s = rel or path.as_posix()
    for line_no, line in enumerate(text.splitlines(), 1):
        if rel_s.endswith(".gitignore") and line.strip().startswith("#"):
            continue
        if _is_env_template_line(rel_s, line):
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line) and not _is_secret_test_fixture(rel_s, line):
                hits.append(f"{rel_s}:{line_no}: {label}")
        for marker in LOOSE_SECRET_MARKERS:
            if marker not in line or _is_secret_test_fixture(rel_s, line):
                continue
            value = _assignment_value(line)
            if value and len(value) >= 8:
                hits.append(f"{rel_s}:{line_no}: {marker}")
    return hits


def _git_add_paths(
    staging: Path,
    paths: list[str],
    *,
    log: OnLine = None,
) -> subprocess.CompletedProcess[str] | None:
    normalized = [_norm_rel(path) for path in paths]
    for index in range(0, len(normalized), _GIT_ADD_BATCH_SIZE):
        batch = normalized[index : index + _GIT_ADD_BATCH_SIZE]
        add = _run_git(["add", "--", *batch], staging, log=log)
        if add.returncode != 0:
            return add
    return None


def _verify_staged_paths(staging: Path, allowed_paths: list[str], *, log: OnLine = None) -> list[str]:
    allowed = {_norm_rel(path) for path in allowed_paths}
    proc = _run_git(["diff", "--cached", "--name-only"], staging, log=log)
    staged = [_norm_rel(path) for path in (proc.stdout or "").splitlines() if path.strip()]
    return [path for path in staged if _is_runtime_path(path) or path not in allowed]


def _unstage_all(staging: Path, *, log: OnLine = None) -> None:
    _run_git(["reset", "HEAD"], staging, log=log)


def _parse_porcelain(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    new_files: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for line in lines:
        if len(line) < 4:
            continue
        code = line[:2]
        path = _strip_git_path(line[3:].strip())
        if " -> " in path:
            path = _strip_git_path(path.split(" -> ", 1)[1].strip())
        if code == "??":
            new_files.append(path)
        elif code[0] == "D" or code[1] == "D":
            deleted.append(path)
        else:
            modified.append(path)
    return new_files, modified, deleted


def _format_tracked_finding(finding) -> str:
    location = finding.path if finding.line is None else f"{finding.path}:{finding.line}"
    return f"{finding.rule_id} {location} — {finding.message}"


def _apply_tracked_tree_report(report: GicleeAppAuditReport, tracked: TrackedTreeAuditReport) -> None:
    if tracked.error:
        report.error = tracked.error
        report.blocked = True
    report.tracked_tree_blockers = [_format_tracked_finding(item) for item in tracked.blockers]
    report.tracked_tree_warnings = [_format_tracked_finding(item) for item in tracked.warnings]
    if report.tracked_tree_blockers:
        report.blocked = True
        if not report.error:
            report.error = (
                f"Pełny audyt git ls-files wykrył {len(report.tracked_tree_blockers)} blokad. "
                "Najpierw wykonaj migrację i usuń dane runtime z trackingu."
            )


def audit_staging_repo(
    staging_dir: Path | None = None,
    *,
    log: OnLine = None,
) -> GicleeAppAuditReport:
    staging = staging_dir or GICLEEAPP_STAGING_DIR
    report = GicleeAppAuditReport()
    try:
        validate_staging_repo(staging, log=log)
    except (FileNotFoundError, ValueError) as exc:
        report.error = str(exc)
        report.blocked = True
        return report

    report.branch_status = inspect_branch_sync(staging, pull_ff_only=False, log=log)
    if report.branch_status.diverged:
        report.blocked = True
        report.error = report.branch_status.message
        return report

    _apply_tracked_tree_report(report, audit_tracked_tree(staging))

    status_proc = _run_git(["status", "--short"], staging, log=log)
    porcelain = [line for line in (status_proc.stdout or "").splitlines() if line.strip()]
    report.new_files, report.modified_files, report.deleted_files = _parse_porcelain(porcelain)
    for path in report.deleted_files:
        if _is_review_only(path):
            report.blocked_deletions.append(path)
    report.deletable_files = [path for path in report.deleted_files if not _is_review_only(path)]
    report.diff_stat = (_run_git(["diff", "--stat"], staging, log=log).stdout or "").strip()
    _run_git(["diff", "--name-status"], staging, log=log)

    candidates: list[str] = []
    for rel in report.new_files + report.modified_files:
        for path in _expand_path_entries(staging, rel):
            if _git_ignored(staging, path):
                continue
            if _is_runtime_path(path):
                report.runtime_hits.append(path)
                continue
            if _skip_secret_scan(path):
                candidates.append(path)
                continue
            hits = scan_file_secrets(staging / path, rel=path)
            if hits:
                report.secret_hits.extend(hits)
                continue
            candidates.append(path)
            if any(path.startswith(prefix) for prefix in GICLEEAPP_THEME_PATH_PREFIXES):
                report.theme_related_changes.append(path)

    report.commit_candidates = sorted(set(candidates))
    if report.secret_hits:
        report.blocked = True
    if not report.commit_candidates and not report.deletable_files:
        report.no_changes = True
    return report


def dry_run_gicleeapp_push(
    *,
    source_dir: Path | None = None,
    staging_dir: Path | None = None,
    log: OnLine = None,
) -> GicleeAppAuditReport:
    staging = staging_dir or GICLEEAPP_STAGING_DIR
    report = GicleeAppAuditReport()
    try:
        validate_staging_repo(staging, log=log)
    except (FileNotFoundError, ValueError) as exc:
        report.error = str(exc)
        report.blocked = True
        return report

    _log(log, "=== Allowlist sync cursor-api → staging ===")
    sync = safe_sync_to_staging(source_dir, staging, log=log)
    report.sync = sync
    if not sync.ok:
        report.error = "; ".join(sync.errors or sync.blockers)
        report.blocked = True
        return report

    audit = audit_staging_repo(staging, log=log)
    for name in (
        "new_files", "modified_files", "deleted_files", "deletable_files",
        "blocked_deletions", "commit_candidates", "secret_hits", "runtime_hits",
        "tracked_tree_blockers", "tracked_tree_warnings", "theme_related_changes",
    ):
        setattr(report, name, list(getattr(audit, name)))
    report.diff_stat = audit.diff_stat
    report.branch_status = audit.branch_status
    report.blocked = audit.blocked
    report.no_changes = audit.no_changes
    report.error = audit.error
    return report


def _precommit_tracked_tree_gate(staging: Path) -> str:
    tracked = audit_tracked_tree(staging)
    if tracked.error:
        return tracked.error
    if not tracked.blockers:
        return ""
    preview = "; ".join(_format_tracked_finding(item) for item in tracked.blockers[:5])
    extra = f" (+{len(tracked.blockers) - 5} więcej)" if len(tracked.blockers) > 5 else ""
    return f"Pełny audyt tracked tree zablokował push: {preview}{extra}"


def commit_and_push_gicleeapp(
    report: GicleeAppAuditReport,
    *,
    staging_dir: Path | None = None,
    include_deletions: bool = False,
    commit_message: str | None = None,
    log: OnLine = None,
) -> GicleeAppPushResult:
    if report.blocked:
        return GicleeAppPushResult(ok=False, message="Workflow zablokowany — napraw audyt.")
    if report.no_changes:
        return GicleeAppPushResult(ok=True, message="Brak zmian — gicleeapp jest aktualne.")
    if not report.commit_candidates and not (include_deletions and report.deletable_files):
        return GicleeAppPushResult(ok=True, message="Brak bezpiecznych plików do commita.")

    staging = staging_dir or GICLEEAPP_STAGING_DIR
    try:
        validate_staging_repo(staging, log=log)
    except (FileNotFoundError, ValueError) as exc:
        return GicleeAppPushResult(ok=False, message=str(exc))
    branch_status = inspect_branch_sync(staging, pull_ff_only=True, log=log)
    if not branch_status.ok:
        return GicleeAppPushResult(ok=False, message=branch_status.message)

    tracked_gate = _precommit_tracked_tree_gate(staging)
    if tracked_gate:
        return GicleeAppPushResult(ok=False, message=tracked_gate)

    paths_to_stage: list[str] = []
    for rel in report.commit_candidates:
        paths_to_stage.extend(_expand_path_entries(staging, rel))
    if include_deletions:
        paths_to_stage.extend(report.deletable_files)
    paths_to_stage = sorted({_norm_rel(path) for path in paths_to_stage})
    if not paths_to_stage:
        return GicleeAppPushResult(ok=False, message="Brak ścieżek do git add.")
    for rel in paths_to_stage:
        if _is_runtime_path(rel):
            return GicleeAppPushResult(ok=False, message=f"Ścieżka runtime poza commitem: {rel}")

    add_err = _git_add_paths(staging, paths_to_stage, log=log)
    if add_err is not None:
        _unstage_all(staging, log=log)
        return GicleeAppPushResult(
            ok=False,
            message=f"git add nie powiódł się: {(add_err.stderr or add_err.stdout or '').strip()}",
        )
    blocked_staged = _verify_staged_paths(staging, paths_to_stage, log=log)
    if blocked_staged:
        _unstage_all(staging, log=log)
        preview = ", ".join(blocked_staged[:8])
        extra = f" (+{len(blocked_staged) - 8} więcej)" if len(blocked_staged) > 8 else ""
        return GicleeAppPushResult(
            ok=False,
            message=f"Staging zawiera niedozwolone ścieżki — push przerwany: {preview}{extra}",
        )

    msg = (commit_message or report.commit_message or GICLEEAPP_COMMIT_MESSAGE).strip()
    commit = _run_git(["commit", "-m", msg], staging, log=log)
    if commit.returncode != 0:
        return GicleeAppPushResult(
            ok=False,
            message=(commit.stderr or commit.stdout or "").strip() or "git commit nie powiódł się.",
        )
    sha = (_run_git(["rev-parse", "HEAD"], staging, log=log).stdout or "").strip()
    push = _run_git(["push", "origin", GICLEEAPP_BRANCH], staging, log=log)
    if push.returncode != 0:
        return GicleeAppPushResult(
            ok=False,
            commit_sha=sha,
            committed_files=paths_to_stage,
            message=(push.stderr or push.stdout or "").strip() or "git push nie powiódł się — sprawdź auth GitHub.",
        )

    status_line = (_run_git(["status", "-sb"], staging, log=log).stdout or "").strip()
    _log(log, f"Push OK: {sha[:12]}")
    starter_sync_message = ""
    starter_updated: list[str] = []
    try:
        from .starter_checkpoint import sync_starter_files_after_gicleeapp_push

        sync = sync_starter_files_after_gicleeapp_push(
            gicleeapp_sha=sha,
            commit_message=msg,
            log=log,
        )
        starter_sync_message = sync.message
        starter_updated = list(sync.updated_files)
        if sync.errors:
            _log(log, f"GPT starter sync: {'; '.join(sync.errors)}")
        elif sync.updated_files:
            _log(log, starter_sync_message)
    except Exception as exc:  # noqa: BLE001
        starter_sync_message = f"GPT starter sync pominięty: {exc}"
        _log(log, starter_sync_message)

    base_message = f"GicleeApp zaktualizowane — {sha[:12]} ({status_line})"
    if starter_sync_message and starter_updated:
        base_message = f"{base_message} | {starter_sync_message}"
    return GicleeAppPushResult(
        ok=True,
        commit_sha=sha,
        committed_files=paths_to_stage,
        message=base_message,
        starter_sync_message=starter_sync_message,
        starter_sync_updated_files=starter_updated,
    )
