"""Synchronizacja lustra motywu → folder git (.gpt_mirror) i push na GitHub."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .config import (
    GPT_RECORDING_DESKTOP_REL,
    GPT_RECORDING_MOBILE_REL,
    MIRROR_DIR,
    MIRROR_INCLUDE_DIRS,
    MIRROR_INCLUDE_FILES,
    MIRROR_MAX_FILE_BYTES,
    MIRROR_SKIP_DIR_NAMES,
    MIRROR_SKIP_SUFFIXES,
    THEME_ROOT,
    GptConfig,
)
from .review_session import (
    CROSS_REPO_REVIEW_NOTE,
    DUAL_REPO_ROUTING_THEME,
    GITHUB_CONNECTOR_NOTE,
    RELATED_GICLEEAPP_SECTION,
    WORKING_TREE_NOTE,
    ReviewSession,
    SOURCE_NOTE,
)
from .record import find_review_demo_recording

MIRROR_GENERATED_ROOT = frozenset({"SYNC_NOTES.md", "GPT_README.md", "REVIEW_MANIFEST.json"})


@dataclass
class SyncResult:
    copied: list[str] = field(default_factory=list)
    skipped_large: list[str] = field(default_factory=list)
    removed_stale: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class PushResult:
    committed: bool
    commit_sha: str = ""
    message: str = ""
    sync: SyncResult | None = None


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_source_paths(theme_root: Path | None = None) -> list[Path]:
    root = theme_root or THEME_ROOT
    paths: list[Path] = []
    for rel in MIRROR_INCLUDE_DIRS:
        src = root / rel
        if src.is_dir() or src.is_file():
            paths.append(src)
    for rel in MIRROR_INCLUDE_FILES:
        src = root / rel
        if src.is_file():
            paths.append(src)
    return paths


def _should_skip_path(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if path.suffix.lower() in MIRROR_SKIP_SUFFIXES:
        return True
    for part in path.parts:
        if part in MIRROR_SKIP_DIR_NAMES:
            return True
    return False


def _mirror_rel(path: Path, theme_root: Path) -> str:
    return path.relative_to(theme_root).as_posix()


def _is_protected_mirror_path(path: Path, mirror: Path) -> bool:
    """Nigdy nie usuwaj `.git/` ani plików poza lustrem."""
    try:
        rel = path.relative_to(mirror)
    except ValueError:
        return True
    return bool(rel.parts) and rel.parts[0] == ".git"


def sync_theme_to_mirror(
    mirror_dir: Path | None = None,
    *,
    theme_root: Path | None = None,
    session: ReviewSession | None = None,
    snapshot_commit: str | None = None,
    log: list[str] | None = None,
) -> SyncResult:
    """Kopiuje allowlist z dysku motywu do lustra git."""
    root = theme_root or THEME_ROOT
    mirror = mirror_dir or MIRROR_DIR
    mirror.mkdir(parents=True, exist_ok=True)
    result = SyncResult()
    lines = log if log is not None else []

    expected_rels: set[str] = set()

    def copy_tree(src_dir: Path) -> None:
        for item in sorted(src_dir.rglob("*")):
            if item.is_dir():
                continue
            if _should_skip_path(item):
                continue
            rel = _mirror_rel(item, root)
            expected_rels.add(rel)
            try:
                size = item.stat().st_size
            except OSError as exc:
                result.errors.append(f"{rel}: {exc}")
                continue
            if size > MIRROR_MAX_FILE_BYTES:
                result.skipped_large.append(rel)
                lines.append(f"POMINIĘTO (za duży): {rel} ({size // (1024 * 1024)} MB)")
                continue
            dest = mirror / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            prev_hash = _file_hash(dest) if dest.is_file() else None
            shutil.copy2(item, dest)
            new_hash = _file_hash(dest)
            if prev_hash != new_hash:
                result.copied.append(rel)
                lines.append(f"Skopiowano: {rel}")

    for rel in MIRROR_INCLUDE_DIRS:
        src = root / rel
        if src.is_dir():
            copy_tree(src)
        elif not src.exists():
            result.errors.append(f"Brak katalogu: {rel}")

    for rel in MIRROR_INCLUDE_FILES:
        src = root / rel
        if not src.is_file():
            continue
        expected_rels.add(rel)
        dest = mirror / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        prev_hash = _file_hash(dest) if dest.is_file() else None
        shutil.copy2(src, dest)
        new_hash = _file_hash(dest)
        if prev_hash != new_hash:
            result.copied.append(rel)
            lines.append(f"Skopiowano: {rel}")

    for existing in list(mirror.rglob("*")):
        if existing.is_dir():
            continue
        if _is_protected_mirror_path(existing, mirror):
            continue
        if existing.parent.resolve() == mirror.resolve() and existing.name in MIRROR_GENERATED_ROOT:
            continue
        if existing.name in {"SYNC_NOTES.md", "GPT_README.md", "REVIEW_MANIFEST.json"}:
            continue
        try:
            rel = existing.relative_to(mirror).as_posix()
        except ValueError:
            continue
        if rel not in expected_rels:
            existing.unlink()
            result.removed_stale.append(rel)
            lines.append(f"Usunięto z lustra: {rel}")

    write_review_artifacts(
        mirror,
        result,
        session=session,
        theme_root=root,
        snapshot_commit=snapshot_commit,
    )
    return result


def write_review_artifacts(
    mirror_dir: Path,
    sync: SyncResult,
    *,
    session: ReviewSession | None = None,
    theme_root: Path | None = None,
    snapshot_commit: str | None = None,
) -> None:
    write_sync_notes(
        mirror_dir,
        sync,
        session=session,
        theme_root=theme_root,
        snapshot_commit=snapshot_commit,
    )
    write_gpt_readme(mirror_dir)
    write_review_manifest(
        mirror_dir,
        sync,
        session=session,
        snapshot_commit=snapshot_commit,
    )


def write_sync_notes(
    mirror_dir: Path,
    sync: SyncResult,
    *,
    session: ReviewSession | None = None,
    theme_root: Path | None = None,
    snapshot_commit: str | None = None,
) -> Path:
    root = theme_root or THEME_ROOT
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    sess = session or ReviewSession()
    lines = [
        "# Sync notes (auto-generated)",
        "",
        f"**Timestamp:** {now}",
        f"**Source:** `{root}`",
        "",
        "> " + WORKING_TREE_NOTE,
        "",
        "**Uwaga:** snapshot jest kopią lokalnego working tree motywu Shopify. "
        "`changed_files` oznacza pliki zaktualizowane w paczce review, "
        "nie pełny diff względem main/live.",
        "",
        "## Cel review / sesji",
        "",
        sess.review_goal if sess.review_goal else "_(nie podano)_",
        "",
    ]
    if snapshot_commit:
        lines.extend([f"**Snapshot commit:** `{snapshot_commit}`", ""])
    lines.extend([
        "## Trasy nagrane",
        "",
    ])
    if sess.routes_recorded:
        lines.extend(f"- `{r}`" for r in sess.routes_recorded)
    else:
        lines.append("- _(brak nagrań w tej sesji)_")
    lines.extend(["", "## Co GPT ma ocenić", ""])
    if sess.review_goal:
        lines.append(f"- {sess.review_goal}")
    else:
        lines.append("- Ogólny review snapshotu motywu (kod + UX jeśli są nagrania).")
    lines.extend(["", "## Znane problemy", ""])
    if sess.known_issues:
        lines.extend(f"- {issue}" for issue in sess.known_issues)
    else:
        lines.append("- _(brak)_")
    lines.extend(["", "## Skopiowano / zaktualizowano", ""])
    if sync.copied:
        lines.extend(f"- `{p}`" for p in sync.copied)
    else:
        lines.append("- _(brak zmian w plikach)_")
    lines.extend(["", "## Pominięto (za duże)", ""])
    if sync.skipped_large:
        lines.extend(f"- `{p}`" for p in sync.skipped_large)
    else:
        lines.append("- _(brak)_")
    lines.extend(["", RELATED_GICLEEAPP_SECTION, ""])
    path = mirror_dir / "SYNC_NOTES.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_gpt_readme(mirror_dir: Path) -> Path:
    text = f"""# GicleeArt — snapshot motywu dla Custom GPT

To repo jest **lustrem read-only** motywu Shopify (bez `cursor-api/`, backupów, `.env`).

> {WORKING_TREE_NOTE}

## Dla Custom GPT

- **Rola:** architekt + code reviewer + ocena UX (nagrania / PNG w `docs/review-demos/`).
- **Indeks sesji:** `REVIEW_MANIFEST.json` + `SYNC_NOTES.md`.
- **Review wizualny:** `latest-desktop.webm`, `latest-mobile.webm`, `latest-*.png`, `console-errors.txt`.

Workflow: GPT planuje → user wkleja prompt do Cursor → push z GicleeApp → GPT ocenia.

## Jak interpretować snapshot

Ten snapshot jest kopią lokalnego working tree motywu Shopify. Nie musi odpowiadać ostatniemu commitowi głównego repo ani stanowi live/production.

GPT powinien traktować snapshot jako paczkę review, a nie jako źródło prawdy o produkcji.

## changed_files

Pole `changed_files` w `REVIEW_MANIFEST.json` oznacza pliki zaktualizowane podczas synchronizacji lustra na podstawie porównania hashy przed/po kopiowaniu.

To **nie** jest pełny git diff względem głównego repo, master/main ani produkcji.

## snapshot_commit

Pole `snapshot_commit` jest dostępne tylko po pushu do repo snapshot.

W trybie **Review package only** może mieć wartość `null`, ponieważ paczka została wygenerowana lokalnie i nie została jeszcze wypchnięta do GitHuba.

## recordings / screenshots / console_errors

Manifest może zawierać standardowe ścieżki do plików webm, PNG i console log.

Te pliki istnieją tylko wtedy, gdy w danej sesji wykonano nagranie / review package z nagrywaniem.

Jeśli wykonano tylko sync bez nagrania, GPT **nie** powinien zakładać, że webm/PNG/console log faktycznie istnieją.

## routes_recorded

W Fazie A `routes_recorded` zwykle zawiera tylko ostatnią nagraną trasę, najczęściej `/`.

Wiele tras będzie dopiero elementem późniejszej fazy.

## console-errors.txt

`console-errors.txt` zawiera błędy i warningi zebrane przez Playwright podczas nagrania.

Nie obejmuje ręcznego testowania strony w przeglądarce ani błędów zauważonych poza Playwrightem.

## commit timezone

Commit message może używać czasu UTC. Przy sesjach wieczornych data/godzina może różnić się od lokalnej strefy czasu w Polsce.

## snapshot_commit a HEAD

Pole `snapshot_commit` jest zapisywane tuż przed `git commit --amend`. Jeśli różni się od SHA ostatniego commita na branchu, **użyj SHA z pusha / `git log -1`** jako punktu review — to commit zawierający aktualny manifest i snapshot.

{RELATED_GICLEEAPP_SECTION}

{CROSS_REPO_REVIEW_NOTE}

{DUAL_REPO_ROUTING_THEME}

{GITHUB_CONNECTOR_NOTE}
"""
    path = mirror_dir / "GPT_README.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_review_manifest(
    mirror_dir: Path,
    sync: SyncResult,
    *,
    session: ReviewSession | None = None,
    snapshot_commit: str | None = None,
) -> Path:
    import json

    sess = session or ReviewSession()
    created = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    demos_dir = mirror_dir / "docs" / "review-demos"
    desktop_rec = find_review_demo_recording(demos_dir, "desktop")
    mobile_rec = find_review_demo_recording(demos_dir, "mobile")
    payload = {
        "snapshot_type": "local_working_tree_theme_snapshot",
        "created_at": created,
        "snapshot_commit": snapshot_commit,
        "review_goal": sess.review_goal,
        "source_note": SOURCE_NOTE,
        "changed_files": list(sync.copied),
        "routes_recorded": list(sess.routes_recorded),
        "recordings": {
            "desktop": desktop_rec or GPT_RECORDING_DESKTOP_REL,
            "mobile": mobile_rec or GPT_RECORDING_MOBILE_REL,
        },
        "screenshots": {
            "desktop": "docs/review-demos/latest-desktop.png",
            "mobile": "docs/review-demos/latest-mobile.png",
        },
        "console_errors": "docs/review-demos/console-errors.txt",
        "known_issues": list(sess.known_issues),
    }
    path = mirror_dir / "REVIEW_MANIFEST.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _amend_with_review_artifacts(
    mirror: Path,
    sync: SyncResult,
    sess: ReviewSession,
    *,
    snapshot_commit: str | None,
    log: list[str],
) -> None:
    write_review_artifacts(
        mirror,
        sync,
        session=sess,
        snapshot_commit=snapshot_commit,
    )
    _run_git(["add", "SYNC_NOTES.md", "GPT_README.md", "REVIEW_MANIFEST.json"], mirror, log)
    amend = _run_git(["commit", "--amend", "--no-edit"], mirror, log)
    if amend.returncode != 0:
        log.append("Uwaga: nie udało się zaktualizować manifestu w commicie (amend).")


def _finalize_manifest_snapshot_commit(
    mirror: Path,
    sync: SyncResult,
    sess: ReviewSession,
    log: list[str],
) -> str:
    """Po pierwszym commicie: 2× zapis manifestu + amend (SHA po amendzie)."""
    sha_proc = _run_git(["rev-parse", "HEAD"], mirror, log)
    sha = (sha_proc.stdout or "").strip()
    _amend_with_review_artifacts(mirror, sync, sess, snapshot_commit=sha or None, log=log)
    sha_proc = _run_git(["rev-parse", "HEAD"], mirror, log)
    sha = (sha_proc.stdout or "").strip()
    _amend_with_review_artifacts(mirror, sync, sess, snapshot_commit=sha or None, log=log)
    sha_proc = _run_git(["rev-parse", "HEAD"], mirror, log)
    return (sha_proc.stdout or "").strip()


def _verify_manifest_snapshot_commit(mirror: Path, head_sha: str, log: list[str]) -> None:
    import json

    show = _run_git(["show", f"{head_sha}:REVIEW_MANIFEST.json"], mirror, log)
    if show.returncode != 0:
        return
    try:
        data = json.loads(show.stdout or "")
    except json.JSONDecodeError:
        return
    manifest_sha = (data.get("snapshot_commit") or "").strip()
    if manifest_sha and manifest_sha != head_sha:
        log.append(
            f"Uwaga: snapshot_commit ({manifest_sha[:12]}) != HEAD ({head_sha[:12]}). "
            "Dla review użyj SHA pusha."
        )
    elif manifest_sha == head_sha:
        log.append(f"Manifest snapshot_commit OK: {head_sha[:12]}")


def _run_git(args: list[str], cwd: Path, log: list[str]) -> subprocess.CompletedProcess[str]:
    mirror_root = cwd.resolve()
    log.append(f"$ git -C {mirror_root} {' '.join(args)}")
    proc = subprocess.run(
        ["git", "-C", str(mirror_root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout.strip():
        log.append(proc.stdout.strip())
    if proc.stderr.strip():
        log.append(proc.stderr.strip())
    return proc


def _assert_mirror_git(mirror: Path, cfg: GptConfig, log: list[str]) -> None:
    if not (mirror / ".git").is_dir():
        raise RuntimeError(
            f"Brak .git w {mirror} — lustro uszkodzone. "
            "Usuń folder .gpt_mirror i uruchom push ponownie."
        )
    top = _run_git(["rev-parse", "--show-toplevel"], mirror, log)
    if top.returncode != 0:
        raise RuntimeError("Lustro git nie odpowiada.")
    actual = Path((top.stdout or "").strip()).resolve()
    expected = mirror.resolve()
    if actual != expected:
        raise RuntimeError(
            f"Git wskazuje {actual}, oczekiwano lustra {expected}. "
            "Operacja przerwana — nie commitujemy głównego repo."
        )
    remote = _run_git(["remote", "get-url", "origin"], mirror, log)
    url = (remote.stdout or "").strip()
    want = (cfg.remote_url or "").strip().removesuffix(".git")
    if url and want and want not in url.replace(".git", ""):
        raise RuntimeError(f"Zły remote lustra: {url} (oczekiwano {cfg.remote_url})")


def ensure_mirror_clone(cfg: GptConfig, log: list[str] | None = None) -> Path:
    """Przygotuj `.gpt_mirror/` — clone lub init."""
    lines = log if log is not None else []
    mirror = MIRROR_DIR
    remote = (cfg.remote_url or "").strip()
    if not remote:
        raise ValueError("Ustaw URL repo GPT w konfiguracji (remote_url).")

    if (mirror / ".git").is_dir():
        proc = _run_git(["remote", "get-url", "origin"], mirror, lines)
        if proc.returncode != 0 or remote not in (proc.stdout or ""):
            _run_git(["remote", "set-url", "origin", remote], mirror, lines)
        return mirror

    # Uszkodzone lustro (np. skasowany .git) — usuń i utwórz od nowa.
    if mirror.exists():
        lines.append("Lustro bez .git — czyszczę i inicjuję od nowa.")
        shutil.rmtree(mirror)
    mirror.parent.mkdir(parents=True, exist_ok=True)

    clone = subprocess.run(
        ["git", "clone", "--branch", cfg.branch, remote, str(mirror)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines.append(f"$ git clone --branch {cfg.branch} …")
    if clone.stdout.strip():
        lines.append(clone.stdout.strip())
    if clone.stderr.strip():
        lines.append(clone.stderr.strip())

    if clone.returncode == 0:
        return mirror

    lines.append("Clone nieudany — inicjuję puste lustro git.")
    mirror.mkdir(parents=True, exist_ok=True)
    _run_git(["init"], mirror, lines)
    _run_git(["remote", "add", "origin", remote], mirror, lines)
    _run_git(["checkout", "-B", cfg.branch], mirror, lines)
    return mirror


def build_review_package(
    session: ReviewSession,
    *,
    include_recordings: bool = False,
    prefer_local: bool = True,
    scroll_seconds: float = 22.0,
    wait_hero_seconds: float = 3.0,
    log: list[str] | None = None,
) -> SyncResult:
    """Sync lustra + opcjonalnie nagrania, bez pusha."""
    from .record import record_preview
    from .review_session import route_from_url

    lines = log if log is not None else []
    if include_recordings:
        rec = record_preview(
            prefer_local=prefer_local,
            scroll_seconds=scroll_seconds,
            wait_hero_seconds=wait_hero_seconds,
            log=lines,
        )
        if rec.ok:
            session.routes_recorded = [route_from_url(rec.url_used)]
        else:
            lines.append(f"Nagranie pominięte: {rec.message}")

    mirror = MIRROR_DIR
    mirror.mkdir(parents=True, exist_ok=True)
    result = sync_theme_to_mirror(mirror, session=session, log=lines)
    lines.append(f"Paczka review: {mirror.resolve()}")
    return result


def push_mirror_to_github(
    cfg: GptConfig,
    session: ReviewSession | None = None,
    *,
    include_recordings: bool = False,
    commit_message: str | None = None,
    log: list[str] | None = None,
) -> PushResult:
    lines = log if log is not None else []
    sess = session or ReviewSession()
    mirror = ensure_mirror_clone(cfg, lines)

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
            sess.routes_recorded = [route_from_url(rec.url_used)]
        else:
            lines.append(f"Nagranie pominięte: {rec.message}")

    sync = sync_theme_to_mirror(mirror, session=sess, log=lines)
    _assert_mirror_git(mirror, cfg, lines)

    _run_git(["add", "-A"], mirror, lines)
    status = _run_git(["status", "--porcelain"], mirror, lines)
    if not (status.stdout or "").strip():
        lines.append("Brak zmian do commita.")
        return PushResult(committed=False, message="Brak zmian", sync=sync)

    msg = commit_message or sess.commit_message()
    commit = _run_git(["commit", "-m", msg], mirror, lines)
    if commit.returncode != 0:
        return PushResult(
            committed=False,
            message=commit.stderr or "Commit failed",
            sync=sync,
        )

    sha_proc = _run_git(["rev-parse", "HEAD"], mirror, lines)
    sha = (sha_proc.stdout or "").strip()

    sha = _finalize_manifest_snapshot_commit(mirror, sync, sess, lines)
    _verify_manifest_snapshot_commit(mirror, sha, lines)

    push = _run_git(["push", "-u", "origin", cfg.branch], mirror, lines)
    if push.returncode != 0:
        push = _run_git(["push", "--set-upstream", "origin", cfg.branch], mirror, lines)

    if push.returncode != 0:
        return PushResult(
            committed=True,
            commit_sha=sha,
            message=push.stderr or "Push failed — sprawdź auth GitHub",
            sync=sync,
        )

    lines.append(f"Push OK: {sha[:12]}")
    return PushResult(committed=True, commit_sha=sha, message="OK", sync=sync)
