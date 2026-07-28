"""Wdrożenia: Shopify theme push + bezpieczny git push gicleeart.git."""

from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .config import (
    GITHUB_DEFAULT_BRANCH,
    GITHUB_REMOTE_URL,
    RUNTIME_DENYLIST_BASENAMES,
    RUNTIME_DENYLIST_DIR_NAMES,
    RUNTIME_DENYLIST_PREFIXES,
    SHOPIFY_DEV,
    SHOPIFY_LIVE,
)

OnLine = Callable[[str], None]

# Windows cmdline ~8k + mniej wyścigów o index.lock niż 1×git add na plik.
_GIT_ADD_BATCH_SIZE = 80

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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass
class GitStatus:
    branch: str = ""
    remote_url: str = ""
    dirty: bool = False
    changed_files: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class BranchSyncStatus:
    ok: bool = True
    ahead: int = 0
    behind: int = 0
    diverged: bool = False
    message: str = ""
    pulled: bool = False


@dataclass
class GithubAuditReport:
    branch: str = ""
    remote_url: str = ""
    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    deletable_files: list[str] = field(default_factory=list)
    commit_candidates: list[str] = field(default_factory=list)
    diff_stat: str = ""
    secret_hits: list[str] = field(default_factory=list)
    runtime_hits: list[str] = field(default_factory=list)
    branch_status: BranchSyncStatus = field(default_factory=BranchSyncStatus)
    blocked: bool = False
    no_changes: bool = False
    push_only: bool = False
    unpushed_commits: int = 0
    commit_message: str = ""
    error: str = ""

    def format_report(self) -> list[str]:
        lines = ["=== Push główne repo gicleeart — audyt ==="]
        if self.error:
            lines.append(f"BŁĄD: {self.error}")
            return lines
        lines.append(f"Remote: {self.remote_url or '(brak)'}")
        bs = self.branch_status
        if bs.message:
            lines.append(f"Branch: {bs.message}")
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
            if len(self.deleted_files) > 40:
                lines.append(f"  … i {len(self.deleted_files) - 40} więcej")
        if self.runtime_hits:
            lines.append(f"Runtime / poza commitem ({len(self.runtime_hits)}):")
            lines.extend(f"  ⚠ {h}" for h in self.runtime_hits[:40])
        if self.secret_hits:
            lines.append("SEKRETY — commit zablokowany:")
            lines.extend(f"  ✖ {h}" for h in self.secret_hits)
        if self.diff_stat.strip():
            lines.append("")
            lines.append("diff --stat:")
            lines.extend(self.diff_stat.strip().splitlines())
        lines.append("")
        lines.append(f"Kandydaci do commita: {len(self.commit_candidates)}")
        if self.push_only:
            lines.append(f"Lokalne commity do wypchnięcia: {self.unpushed_commits}")
        if self.blocked:
            lines.append("")
            lines.append("WORKFLOW ZATRZYMANY — napraw blokady przed pushem.")
        elif self.no_changes:
            lines.append("")
            lines.append("Brak zmian do bezpiecznego commita.")
        elif self.push_only:
            lines.append("")
            lines.append("Working tree jest czysty — potwierdź push istniejących lokalnych commitów.")
        else:
            lines.append("")
            lines.append(f"Proponowany commit: {self.commit_message}")
            lines.append("Potwierdź push w oknie dialogowym.")
        return lines


@dataclass
class PushOutcome:
    ok: bool
    message: str = ""
    detail_lines: list[str] = field(default_factory=list)
    commit_sha: str = ""
    committed_files: list[str] = field(default_factory=list)


def _emit(on_line: OnLine | None, line: str) -> None:
    if on_line:
        on_line(line)


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    on_line: OnLine | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    _emit(on_line, "$ " + " ".join(cmd))
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
            _emit(on_line, line)
    return proc


def _git_err_text(proc: subprocess.CompletedProcess[str]) -> str:
    return (proc.stderr or proc.stdout or "").strip()


def _is_index_lock_error(text: str) -> bool:
    return "index.lock" in text.lower()


def _clear_stale_index_lock(cwd: Path, *, on_line: OnLine | None = None) -> bool:
    """Usuń porzucony index.lock (np. po przerwaniu poprzedniego git add)."""
    lock = cwd / ".git" / "index.lock"
    if not lock.is_file():
        return False
    try:
        age_s = time.time() - lock.stat().st_mtime
    except OSError:
        return False
    if age_s < 2.0:
        return False
    try:
        lock.unlink()
        _emit(on_line, f"Usunięto stale index.lock (wiek {age_s:.1f}s)")
        return True
    except OSError as exc:
        _emit(on_line, f"Nie udało się usunąć index.lock: {exc}")
        return False


def _git_add_paths(
    paths: list[str],
    *,
    cwd: Path,
    on_line: OnLine | None = None,
) -> subprocess.CompletedProcess[str] | None:
    """Stage paths in batches — fewer index.lock races than per-file add."""
    cleaned = [_norm_rel(p) for p in paths if _norm_rel(p)]
    if not cleaned:
        return None
    for i in range(0, len(cleaned), _GIT_ADD_BATCH_SIZE):
        batch = cleaned[i : i + _GIT_ADD_BATCH_SIZE]
        proc = _run_git(["add", "--", *batch], cwd=cwd, on_line=on_line)
        if proc.returncode == 0:
            continue
        err = _git_err_text(proc)
        if _is_index_lock_error(err):
            time.sleep(0.4)
            _clear_stale_index_lock(cwd, on_line=on_line)
            proc = _run_git(["add", "--", *batch], cwd=cwd, on_line=on_line)
            if proc.returncode == 0:
                continue
        return proc
    return None


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


def assert_github_remote(remote_url: str) -> None:
    u = remote_url.rstrip("/").lower()
    if not remote_url.strip():
        raise ValueError("Brak skonfigurowanego remote origin.")
    if "gicleeart-gpt" in u:
        raise ValueError(
            f"remote wskazuje gicleeart-gpt zamiast głównego gicleeart: {remote_url}"
        )
    if "gicleeapp" in u:
        raise ValueError(f"remote wskazuje gicleeapp zamiast gicleeart: {remote_url}")
    normalized = u
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    elif normalized.startswith("ssh://git@github.com/"):
        normalized = "https://github.com/" + normalized.removeprefix("ssh://git@github.com/")
    normalized = normalized.removesuffix(".git").rstrip("/")
    if normalized != "https://github.com/eagleblastmusic-lgtm/gicleeart":
        raise ValueError(
            f"remote musi wskazywać eagleblastmusic-lgtm/gicleeart.git: {remote_url}"
        )


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


def inspect_branch_sync(
    root: Path,
    branch: str,
    *,
    pull_ff_only: bool = False,
    on_line: OnLine | None = None,
) -> BranchSyncStatus:
    fetch = _run_git(["fetch", "origin", branch], cwd=root, on_line=on_line)
    if fetch.returncode != 0:
        return BranchSyncStatus(ok=False, message="git fetch origin nie powiódł się.")

    sb = _run_git(["status", "-sb"], cwd=root, on_line=on_line)
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
        pull = _run_git(["pull", "--ff-only", "origin", branch], cwd=root, on_line=on_line)
        if pull.returncode != 0:
            return BranchSyncStatus(
                ok=False,
                behind=behind,
                message="git pull --ff-only nie powiódł się — zatrzymaj workflow.",
            )
        pulled = True
        sb = _run_git(["status", "-sb"], cwd=root, on_line=on_line)
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


def _assignment_value(line: str) -> str:
    if "=" not in line:
        return ""
    return line.split("=", 1)[1].strip().strip('"').strip("'")


def _skip_secret_scan(rel: str) -> bool:
    n = _norm_rel(rel)
    return n.startswith("tests/") or "/tests/" in n or n.startswith("cursor-api/tests/")


def _is_runtime_path(rel: str) -> bool:
    n = _norm_rel(rel).rstrip("/")
    if not n:
        return True
    if n == ".env" or n.startswith(".env."):
        return True
    name = Path(n).name
    if name.startswith(".env"):
        return True
    if name in RUNTIME_DENYLIST_BASENAMES:
        return True
    parts = Path(n).parts
    if any(p in RUNTIME_DENYLIST_DIR_NAMES for p in parts):
        return True
    for prefix in RUNTIME_DENYLIST_PREFIXES:
        p = prefix.rstrip("/")
        if n == p or n.startswith(prefix):
            return True
    if name.endswith((".log", ".tmp", ".temp", ".mp4")):
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
        path = _strip_git_path(ln[3:].strip())
        if " -> " in path:
            path = _strip_git_path(path.split(" -> ", 1)[1].strip())
        if code == "??":
            new_files.append(path)
        elif code[0] == "D" or code[1] == "D":
            deleted.append(path)
        else:
            modified.append(path)
    return new_files, modified, deleted


def default_commit_message() -> str:
    ts = datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M")
    return f"Pushe: sync {ts}"


def read_git_status(*, on_line: OnLine | None = None) -> GitStatus:
    root = repo_root()
    if not (root / ".git").exists():
        return GitStatus(error="Brak repozytorium git w katalogu motywu.")

    branch_proc = _run_git(["branch", "--show-current"], cwd=root, on_line=on_line)
    branch = (branch_proc.stdout or "").strip() or GITHUB_DEFAULT_BRANCH

    remote_proc = _run_git(["remote", "get-url", "origin"], cwd=root, on_line=on_line)
    remote_url = (remote_proc.stdout or "").strip()

    status_proc = _run_git(["status", "--porcelain"], cwd=root, on_line=on_line)
    lines = [ln for ln in (status_proc.stdout or "").splitlines() if ln.strip()]
    changed = [_strip_git_path(ln[3:].strip()) if len(ln) > 3 else ln for ln in lines]

    return GitStatus(
        branch=branch,
        remote_url=remote_url,
        dirty=bool(lines),
        changed_files=changed,
    )


def audit_repo_for_github_push(
    *,
    commit_message: str | None = None,
    on_line: OnLine | None = None,
) -> GithubAuditReport:
    root = repo_root()
    report = GithubAuditReport()

    if not (root / ".git").exists():
        report.error = "Brak repozytorium git w katalogu motywu."
        report.blocked = True
        return report

    branch_proc = _run_git(["branch", "--show-current"], cwd=root, on_line=on_line)
    branch = (branch_proc.stdout or "").strip() or GITHUB_DEFAULT_BRANCH
    report.branch = branch

    remote_proc = _run_git(["remote", "get-url", "origin"], cwd=root, on_line=on_line)
    remote_url = (remote_proc.stdout or "").strip()
    report.remote_url = remote_url

    try:
        assert_github_remote(remote_url)
    except ValueError as exc:
        report.error = str(exc)
        report.blocked = True
        return report

    status_proc = _run_git(["status", "--short"], cwd=root, on_line=on_line)
    porcelain = [ln for ln in (status_proc.stdout or "").splitlines() if ln.strip()]
    report.new_files, report.modified_files, report.deleted_files = _parse_porcelain(porcelain)

    stat_proc = _run_git(["diff", "--stat"], cwd=root, on_line=on_line)
    report.diff_stat = (stat_proc.stdout or "").strip()

    all_changed = report.new_files + report.modified_files
    candidates: list[str] = []

    for rel in all_changed:
        n = _norm_rel(rel)
        if _is_runtime_path(n):
            report.runtime_hits.append(n)
            continue
        if _skip_secret_scan(n):
            candidates.append(n)
            continue
        hits = scan_file_secrets(root / n, rel=n)
        if hits:
            report.secret_hits.extend(hits)
            continue
        candidates.append(n)

    report.commit_candidates = sorted(set(candidates))
    report.deletable_files = sorted(set(report.deleted_files))

    if report.secret_hits:
        report.blocked = True

    report.branch_status = inspect_branch_sync(
        root, branch, pull_ff_only=False, on_line=on_line
    )
    if not report.branch_status.ok:
        report.error = report.branch_status.message
        report.blocked = True
    elif report.branch_status.diverged:
        report.error = report.branch_status.message
        report.blocked = True

    msg = (commit_message or "").strip()
    report.commit_message = msg or default_commit_message()

    if not report.commit_candidates and not report.deletable_files:
        if report.branch_status.ahead > 0:
            report.push_only = True
            report.unpushed_commits = report.branch_status.ahead
        else:
            report.no_changes = True
    elif not report.commit_candidates and report.deletable_files:
        report.no_changes = False

    return report


def dry_run_github_push(
    *,
    commit_message: str | None = None,
    on_line: OnLine | None = None,
) -> GithubAuditReport:
    _emit(on_line, "=== Dry-run: główne repo gicleeart ===")
    _emit(on_line, f"Repozytorium: {repo_root()}")
    return audit_repo_for_github_push(commit_message=commit_message, on_line=on_line)


def commit_and_push_github(
    report: GithubAuditReport,
    *,
    include_deletions: bool = False,
    on_line: OnLine | None = None,
) -> PushOutcome:
    if report.blocked:
        return PushOutcome(ok=False, message="Workflow zablokowany — napraw audyt.")
    if report.no_changes:
        return PushOutcome(ok=True, message="Brak zmian do wysłania na GitHub.")

    root = repo_root()
    branch = (report.branch or GITHUB_DEFAULT_BRANCH).strip()

    if report.push_only:
        try:
            assert_github_remote(report.remote_url)
        except ValueError as exc:
            return PushOutcome(ok=False, message=str(exc))

        branch_status = inspect_branch_sync(root, branch, pull_ff_only=True, on_line=on_line)
        if not branch_status.ok:
            return PushOutcome(ok=False, message=branch_status.message)

        push = _run_git(["push", "origin", branch], cwd=root, on_line=on_line)
        if push.returncode != 0:
            err = (push.stderr or push.stdout or "").strip()
            return PushOutcome(
                ok=False,
                message=err or "git push nie powiódł się — sprawdź auth GitHub.",
            )

        sha_proc = _run_git(["rev-parse", "HEAD"], cwd=root, on_line=on_line)
        sha = (sha_proc.stdout or "").strip()
        return PushOutcome(
            ok=True,
            message=(
                f"GitHub OK ({report.unpushed_commits} lokalnych commitów → "
                f"origin/{branch}, {sha[:12] if sha else '?'})."
            ),
            commit_sha=sha,
        )

    if not report.commit_candidates and not (include_deletions and report.deletable_files):
        return PushOutcome(ok=True, message="Brak bezpiecznych plików do commita.")

    _emit(on_line, "=== Commit + push gicleeart ===")

    try:
        assert_github_remote(report.remote_url)
    except ValueError as exc:
        return PushOutcome(ok=False, message=str(exc))

    branch_status = inspect_branch_sync(root, branch, pull_ff_only=True, on_line=on_line)
    if not branch_status.ok:
        return PushOutcome(ok=False, message=branch_status.message)

    paths_to_stage = list(report.commit_candidates)
    if include_deletions:
        paths_to_stage.extend(report.deletable_files)

    if not paths_to_stage:
        return PushOutcome(ok=False, message="Brak ścieżek do git add.")

    cleaned_paths: list[str] = []
    for rel in paths_to_stage:
        rel_clean = _norm_rel(rel)
        if _is_runtime_path(rel_clean):
            return PushOutcome(
                ok=False,
                message=f"Ścieżka runtime poza commitem: {rel_clean}",
            )
        cleaned_paths.append(rel_clean)

    add_err = _git_add_paths(cleaned_paths, cwd=root, on_line=on_line)
    if add_err is not None:
        detail = _git_err_text(add_err)
        return PushOutcome(
            ok=False,
            message=f"git add nie powiodło się: {detail or 'nieznany błąd git'}",
        )

    msg = report.commit_message or default_commit_message()
    commit = _run_git(["commit", "-m", msg], cwd=root, on_line=on_line)
    if commit.returncode != 0:
        err = (commit.stderr or commit.stdout or "").strip()
        return PushOutcome(ok=False, message=err or "git commit nie powiódł się.")

    sha_proc = _run_git(["rev-parse", "HEAD"], cwd=root, on_line=on_line)
    sha = (sha_proc.stdout or "").strip()

    push = _run_git(["push", "origin", branch], cwd=root, on_line=on_line)
    if push.returncode != 0:
        push2 = _run_git(
            ["push", "--set-upstream", "origin", branch],
            cwd=root,
            on_line=on_line,
        )
        if push2.returncode != 0:
            err = (push2.stderr or push2.stdout or "").strip()
            return PushOutcome(
                ok=False,
                message=err or "git push nie powiódł się — sprawdź auth GitHub.",
                commit_sha=sha,
                committed_files=paths_to_stage,
            )

    short = sha[:12] if sha else "?"
    return PushOutcome(
        ok=True,
        message=f"GitHub OK ({short} → origin/{branch}, {len(paths_to_stage)} plików).",
        commit_sha=sha,
        committed_files=paths_to_stage,
    )


def push_shopify(
    target: dict[str, object],
    *,
    on_line: OnLine | None = None,
) -> PushOutcome:
    from Komponenty.stronaglowna.service import deploy_theme, theme_root

    env = str(target.get("environment") or "development")
    allow_live = bool(target.get("allow_live"))
    label = str(target.get("label") or env)

    _emit(on_line, f"=== Shopify: {label} ===")
    _emit(on_line, f"Katalog motywu: {theme_root()}")
    _emit(on_line, f"shopify theme push --environment {env}" + (" --allow-live" if allow_live else ""))

    lines: list[str] = []

    def capture(line: str) -> None:
        lines.append(line)
        _emit(on_line, line)

    try:
        code = deploy_theme(
            environment=env,
            allow_live=allow_live,
            on_line=capture,
        )
    except FileNotFoundError as exc:
        return PushOutcome(ok=False, message=str(exc), detail_lines=lines)
    except OSError as exc:
        return PushOutcome(ok=False, message=str(exc), detail_lines=lines)

    if code == 0:
        return PushOutcome(ok=True, message=f"Motyw wdrożony ({label}).", detail_lines=lines)
    return PushOutcome(
        ok=False,
        message=f"shopify theme push zakończone kodem {code}.",
        detail_lines=lines,
    )


def push_shopify_dev(*, on_line: OnLine | None = None) -> PushOutcome:
    return push_shopify(SHOPIFY_DEV, on_line=on_line)


def push_shopify_live(*, on_line: OnLine | None = None) -> PushOutcome:
    return push_shopify(SHOPIFY_LIVE, on_line=on_line)
