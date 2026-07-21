"""Auto-sync plików startowych GPT po udanym Push GicleeApp."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import config

MARKER_START = "<!-- gpt-starter:gicleeapp-push:start -->"
MARKER_END = "<!-- gpt-starter:gicleeapp-push:end -->"

_MARKER_BLOCK_RE = re.compile(
    re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
    re.DOTALL,
)
_VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')

# Jedyny plik dynamicznego checkpointu. Wersjonowane Instructions, indeks i
# Wiadomość początkowa są źródłami ręcznie kontrolowanymi i nie mogą być
# nadpisywane jako efekt uboczny pushu aplikacji.
_STARTER_FILES_WITH_MARKERS: tuple[str, ...] = (
    "CURRENT_APP_STATE.md",
)

_MASTER_INDEX_FILE = config.GPT_MASTER_INDEX_FILE


@dataclass
class MonorepoGitStatus:
    origin_short: str = ""
    origin_subject: str = ""
    local_commits: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class StarterCheckpointSyncResult:
    ok: bool = True
    updated_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    version: str = ""
    gicleeapp_sha_short: str = ""

    @property
    def message(self) -> str:
        if self.errors:
            return "; ".join(self.errors)
        if not self.updated_files:
            return "Brak zmian w plikach startowych GPT."
        names = ", ".join(self.updated_files)
        return (
            f"Pliki startowe GPT: zaktualizowano {names} "
            f"(gicleeapp v{self.version} @ {self.gicleeapp_sha_short})."
        )


@dataclass(frozen=True)
class GicleeAppPushCheckpointContext:
    version: str
    gicleeapp_sha: str
    commit_message: str
    pushed_at: datetime
    monorepo: MonorepoGitStatus

    @property
    def gicleeapp_sha_short(self) -> str:
        return self.gicleeapp_sha[:7] if self.gicleeapp_sha else ""

    @property
    def pushed_at_label(self) -> str:
        return self.pushed_at.strftime("%Y-%m-%d %H:%M UTC")


def read_app_version(source_dir: Path | None = None) -> str:
    root = source_dir or config.CURSOR_API_DIR
    init_py = root / "giclee_app" / "__init__.py"
    if not init_py.is_file():
        raise FileNotFoundError(f"Brak pliku wersji: {init_py}")
    match = _VERSION_RE.search(init_py.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Nie znaleziono __version__ w {init_py}")
    return match.group(1)


def read_monorepo_git_status(theme_root: Path | None = None) -> MonorepoGitStatus:
    root = theme_root or config.THEME_ROOT
    if not (root / ".git").is_dir():
        return MonorepoGitStatus()

    def _git(args: list[str]) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            return ""
        return (proc.stdout or "").strip()

    origin_short = _git(["rev-parse", "--short", "origin/master"])
    origin_subject = _git(["log", "-1", "--format=%s", "origin/master"])
    local_lines = _git(["log", "origin/master..HEAD", "--format=%h %s"]).splitlines()
    local_commits = [
        (line.split(" ", 1)[0], line.split(" ", 1)[1])
        for line in local_lines
        if line.strip() and " " in line
    ]
    return MonorepoGitStatus(
        origin_short=origin_short,
        origin_subject=origin_subject,
        local_commits=local_commits,
    )


def build_checkpoint_context(
    *,
    gicleeapp_sha: str,
    commit_message: str,
    source_dir: Path | None = None,
    theme_root: Path | None = None,
    pushed_at: datetime | None = None,
) -> GicleeAppPushCheckpointContext:
    return GicleeAppPushCheckpointContext(
        version=read_app_version(source_dir),
        gicleeapp_sha=gicleeapp_sha.strip(),
        commit_message=(commit_message or "Refresh GicleeApp repository snapshot").strip(),
        pushed_at=pushed_at or datetime.now(timezone.utc),
        monorepo=read_monorepo_git_status(theme_root),
    )


def _local_monorepo_lines(ctx: GicleeAppPushCheckpointContext) -> list[str]:
    if not ctx.monorepo.local_commits:
        return []
    lines = ["Lokalne commity monorepo (nie na origin/master, push pending):"]
    for short_sha, subject in ctx.monorepo.local_commits[:8]:
        lines.append(f"- `{short_sha}` {subject}")
    if len(ctx.monorepo.local_commits) > 8:
        lines.append(f"- … i {len(ctx.monorepo.local_commits) - 8} więcej")
    return lines


def _branch_status_lines(ctx: GicleeAppPushCheckpointContext) -> list[str]:
    lines = [
        (
            f"- **GitHub gicleeapp:** v{ctx.version} / `main` @ "
            f"`{ctx.gicleeapp_sha_short}` "
            f"(auto-sync po Push GicleeApp, {ctx.pushed_at_label})"
        )
    ]
    if ctx.monorepo.origin_short:
        origin_tail = ctx.monorepo.origin_subject or "origin/master"
        lines.append(
            f"- **monorepo origin/master:** `{ctx.monorepo.origin_short}` — {origin_tail}"
        )
    else:
        lines.append("- **monorepo origin/master:** n/d (brak danych git lokalnie)")
    if ctx.monorepo.local_commits:
        lines.append(
            "- **lokalnie monorepo:** dodatkowe commity względem origin/master — "
            "push pending (nie zakładać push monorepo bez potwierdzenia użytkownika)"
        )
        for short_sha, subject in ctx.monorepo.local_commits[:5]:
            lines.append(f"  - `{short_sha}` {subject}")
    return lines


def render_current_app_state_block(ctx: GicleeAppPushCheckpointContext) -> str:
    lines = [
        f"GicleeApp Studio v{ctx.version}",
        "",
        "GitHub / aktualna wersja aplikacji (`eagleblastmusic-lgtm/gicleeapp`):",
        (
            f"v{ctx.version} — zgodnie z `cursor-api/giclee_app/__init__.py` "
            "i `cursor-api/package.json`"
        ),
        (
            f"Ostatni push GicleeApp: `{ctx.gicleeapp_sha_short}` na `main` "
            f"({ctx.pushed_at_label}) — {ctx.commit_message}"
        ),
        "",
    ]
    if ctx.monorepo.origin_short:
        lines.extend(
            [
                "Monorepo origin/master (projekt / docs):",
                f"{ctx.monorepo.origin_short} {ctx.monorepo.origin_subject}".rstrip(),
                "",
            ]
        )
    local_lines = _local_monorepo_lines(ctx)
    if local_lines:
        lines.extend(local_lines)
        lines.append("")

    lines.extend(
        [
            "Branch status:",
            *_branch_status_lines(ctx),
            "",
            "GPT starter files:",
            (
                f"auto-sync po Push GicleeApp {ctx.pushed_at_label} "
                f"(gicleeapp `{ctx.gicleeapp_sha_short}`, v{ctx.version}; paczka v40; "
                "źródło = ten folder, nie ZIP)"
            ),
            "",
            "Recent context:",
            (
                f"- **GitHub gicleeapp:** v{ctx.version} / `main` @ "
                f"`{ctx.gicleeapp_sha_short}` — auto-sync po Push GicleeApp"
            ),
        ]
    )

    for short_sha, subject in ctx.monorepo.local_commits[:3]:
        if "perf-agent" in subject.lower() or "performance agent" in subject.lower():
            lines.append(
                f"- **Performance Agent** — lokalny commit monorepo `{short_sha}`; "
                "push monorepo pending (nie mylić z pushem gicleeapp)"
            )
            break

    lines.append(
        "- Local runtime/untracked still outside commit and remote "
        "(working tree hygiene pending)"
    )
    return "\n".join(lines)


def render_compact_checkpoint_block(ctx: GicleeAppPushCheckpointContext) -> str:
    """Kompatybilny renderer historyczny; nie jest już zapisywany automatycznie."""
    return "\n".join(
        [
            (
                "Repo kanoniczne: `eagleblastmusic-lgtm/gicleeapp` "
                "(monorepo `gicleeart`, branch `master`, app w `cursor-api/`)"
            ),
            "",
            (
                f"GitHub / aktualna wersja aplikacji: **v{ctx.version}** "
                "(`giclee_app/__init__.py`, `package.json`)"
            ),
            (
                f"Ostatni push GicleeApp: `{ctx.gicleeapp_sha_short}` na `main` "
                f"({ctx.pushed_at_label}) — {ctx.commit_message}"
            ),
        ]
    )


def render_wiadomosc_block(ctx: GicleeAppPushCheckpointContext) -> str:
    """Kompatybilny renderer historyczny; nie jest już zapisywany automatycznie."""
    return "\n".join(
        [
            f"- GicleeApp Studio v{ctx.version}",
            "",
            (
                f"- Ostatni push GicleeApp: {ctx.gicleeapp_sha_short} na main "
                f"({ctx.pushed_at_label}) — {ctx.commit_message}"
            ),
        ]
    )


def _wrap_marker_block(body: str) -> str:
    return f"{MARKER_START}\n{body.rstrip()}\n{MARKER_END}"


def _replace_marker_block(text: str, body: str) -> str | None:
    wrapped = _wrap_marker_block(body)
    if MARKER_START in text and MARKER_END in text:
        return _MARKER_BLOCK_RE.sub(wrapped, text, count=1)
    return None


def _update_master_index_version_lines(
    text: str,
    ctx: GicleeAppPushCheckpointContext,
) -> str:
    """Historyczny helper pozostawiony dla zgodności importów; brak auto-zapisu."""
    updated = re.sub(
        r"GicleeApp Studio v[\d.]+",
        f"GicleeApp Studio v{ctx.version}",
        text,
        count=1,
    )
    return re.sub(
        r"checkpoint v[\d.]+;",
        f"checkpoint v{ctx.version};",
        updated,
        count=1,
    )


def sync_starter_files_after_gicleeapp_push(
    *,
    gicleeapp_sha: str,
    commit_message: str,
    starter_dir: Path | None = None,
    source_dir: Path | None = None,
    theme_root: Path | None = None,
    pushed_at: datetime | None = None,
    log: list[str] | None = None,
) -> StarterCheckpointSyncResult:
    result = StarterCheckpointSyncResult()
    root = starter_dir or config.GPT_STARTER_DIR

    if not root.is_dir():
        result.ok = False
        result.errors.append(f"Brak folderu plików startowych GPT: {root}")
        return result

    try:
        ctx = build_checkpoint_context(
            gicleeapp_sha=gicleeapp_sha,
            commit_message=commit_message,
            source_dir=source_dir,
            theme_root=theme_root,
            pushed_at=pushed_at,
        )
    except (FileNotFoundError, ValueError) as exc:
        result.ok = False
        result.errors.append(str(exc))
        return result

    result.version = ctx.version
    result.gicleeapp_sha_short = ctx.gicleeapp_sha_short

    renderers = {
        "CURRENT_APP_STATE.md": render_current_app_state_block,
    }

    for rel_name in _STARTER_FILES_WITH_MARKERS:
        path = root / rel_name
        if not path.is_file():
            result.skipped_files.append(rel_name)
            continue

        original = path.read_text(encoding="utf-8")
        updated = _replace_marker_block(original, renderers[rel_name](ctx))
        if updated is None:
            result.skipped_files.append(rel_name)
            if log is not None:
                log.append(f"GPT starter: pominięto {rel_name} (brak markerów auto-sync)")
            continue

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            result.updated_files.append(rel_name)
            if log is not None:
                log.append(f"GPT starter: zaktualizowano {rel_name}")

    return result
