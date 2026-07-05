"""Nagranie podglądu strony (Playwright) → docs/review-demos/ lub data/nagrania/."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from Komponenty.stronaglowna.home_features import HOMEPAGE_URL, PREVIEW_QUERY, preview_url
from Komponenty.stronaglowna.service import theme_dev_http_ready, theme_dev_port_open

from .config import (
    GPT_RECORDING_DESKTOP,
    GPT_RECORDING_DESKTOP_REL,
    GPT_RECORDING_MOBILE,
    GPT_RECORDING_MOBILE_REL,
    REVIEW_DEMOS_DIR,
    THEME_ROOT,
    VIDEOS_DIR,
)

VIDEO_SUFFIXES: frozenset[str] = frozenset({".webm", ".mp4", ".mov", ".mkv"})


@dataclass
class RecordResult:
    ok: bool
    desktop_path: Path | None = None
    mobile_path: Path | None = None
    output_dir: Path | None = None
    url_used: str = ""
    message: str = ""


def _slug_session_label(label: str, *, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w\-]+", "-", label.strip().lower(), flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:max_len]


def make_video_session_dir(*, session_label: str = "") -> Path:
    """Nowy podfolder na nagranie: data/nagrania/YYYYMMDD-HHMMSS[-cel]."""
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    slug = _slug_session_label(session_label)
    name = f"{stamp}-{slug}" if slug else stamp
    path = VIDEOS_DIR / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_record_url(*, prefer_local: bool = True) -> tuple[str, str | None]:
    """Zwraca (url, error_message)."""
    if prefer_local:
        local = preview_url(local=True)
        if theme_dev_port_open() and theme_dev_http_ready(url=local):
            return local, None
        return local, (
            "Theme dev nie działa na 127.0.0.1:9292.\n"
            "Uruchom «Theme dev…» w GicleeApp albo wyłącz «Preferuj localhost»."
        )
    live = f"{HOMEPAGE_URL.rstrip('/')}/?{PREVIEW_QUERY}"
    return live, None


def record_preview(
    *,
    prefer_local: bool = True,
    scroll_seconds: float = 55.0,
    wait_hero_seconds: float = 4.0,
    out_dir: Path | None = None,
    desktop_only: bool = False,
    log: list[str] | None = None,
) -> RecordResult:
    lines = log if log is not None else []
    url, err = resolve_record_url(prefer_local=prefer_local)
    if err and prefer_local:
        return RecordResult(ok=False, url_used=url, message=err)

    script = THEME_ROOT / "scripts" / "gpt-record-preview.mjs"
    if not script.is_file():
        return RecordResult(
            ok=False,
            message=f"Brak skryptu: {script}",
        )

    node = shutil.which("node")
    if not node:
        return RecordResult(ok=False, message="Nie znaleziono `node` w PATH.")

    target = out_dir or REVIEW_DEMOS_DIR
    target.mkdir(parents=True, exist_ok=True)
    if target == REVIEW_DEMOS_DIR:
        purge_review_demo_videos(log=lines)

    cmd = [
        node,
        str(script),
        "--url",
        url,
        "--out-dir",
        str(target),
        "--scroll-seconds",
        str(scroll_seconds),
        "--wait-hero",
        str(wait_hero_seconds),
    ]
    if desktop_only:
        cmd.append("--desktop-only")
    lines.append("$ " + " ".join(cmd))

    proc = subprocess.run(
        cmd,
        cwd=str(THEME_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout.strip():
        lines.extend(proc.stdout.strip().splitlines())
    if proc.stderr.strip():
        lines.extend(proc.stderr.strip().splitlines())

    desktop = target / "latest-desktop.webm"
    mobile = target / "latest-mobile.webm"

    if proc.returncode != 0:
        hint = ""
        if "Cannot find package 'playwright'" in (proc.stderr or ""):
            hint = "\nUruchom w korzeniu motywu: npm install && npx playwright install chromium"
        return RecordResult(
            ok=False,
            url_used=url,
            output_dir=target,
            message=f"Nagranie nieudane (kod {proc.returncode}).{hint}",
        )

    if not desktop.is_file():
        return RecordResult(
            ok=False,
            url_used=url,
            output_dir=target,
            message="Skrypt zakończony, ale brak latest-desktop.webm",
        )

    lines.append(f"Folder: {target.resolve()}")
    lines.append(f"Zapisano: {desktop}")
    if mobile.is_file():
        lines.append(f"Zapisano: {mobile}")

    return RecordResult(
        ok=True,
        desktop_path=desktop,
        mobile_path=mobile if mobile.is_file() else None,
        output_dir=target,
        url_used=url,
        message="OK",
    )


def record_video_to_disk(
    *,
    prefer_local: bool = True,
    scroll_seconds: float = 55.0,
    wait_hero_seconds: float = 4.0,
    session_label: str = "",
    log: list[str] | None = None,
) -> RecordResult:
    """Nagranie do osobnego folderu data/nagrania/ (nie nadpisuje review-demos)."""
    out_dir = make_video_session_dir(session_label=session_label)
    return record_preview(
        prefer_local=prefer_local,
        scroll_seconds=scroll_seconds,
        wait_hero_seconds=wait_hero_seconds,
        out_dir=out_dir,
        desktop_only=True,
        log=log,
    )


def find_review_demo_recording(demos_dir: Path, label: str) -> str | None:
    """Ścieżka względem korzenia motywu/lustra — kanoniczne nazwy dla GPT."""
    if not demos_dir.is_dir():
        return None
    canonical = GPT_RECORDING_DESKTOP if label == "desktop" else GPT_RECORDING_MOBILE
    if (demos_dir / canonical).is_file():
        return f"docs/review-demos/{canonical}"
    for ext in sorted(VIDEO_SUFFIXES):
        name = f"latest-{label}{ext}"
        if (demos_dir / name).is_file():
            return f"docs/review-demos/{name}"
    return None


def _remove_old_latest_videos(label: str) -> None:
    for old in REVIEW_DEMOS_DIR.glob(f"latest-{label}.*"):
        if old.suffix.lower() in VIDEO_SUFFIXES:
            old.unlink(missing_ok=True)


def purge_review_demo_videos(*, log: list[str] | None = None) -> int:
    """Usuwa poprzednie pliki wideo latest-* z docs/review-demos/."""
    lines = log if log is not None else []
    if not REVIEW_DEMOS_DIR.is_dir():
        return 0
    removed = 0
    for path in REVIEW_DEMOS_DIR.glob("latest-*"):
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES:
            path.unlink(missing_ok=True)
            lines.append(f"Usunięto poprzednie: {path.name}")
            removed += 1
    return removed


def purge_directory_videos(directory: Path, *, log: list[str] | None = None) -> int:
    """Nie używać na szerokich folderach użytkownika (Videos, Desktop…).

    Historycznie wywołanie z OBS kasowało rekursywnie cały katalog nagrań OBS —
    gdy OBS miał ustawione ``C:\\Users\\…\\Videos``, usuwało wszystkie filmy użytkownika.
    Zostawione jako no-op; wybór pliku opiera się na ``since=started_at``.
    """
    lines = log if log is not None else []
    if directory.is_dir():
        lines.append(
            f"Pominięto czyszczenie katalogu OBS ({directory}) — tylko review-demos/latest-*."
        )
    return 0


def import_manual_review_videos(
    desktop_source: Path,
    mobile_source: Path | None = None,
    *,
    log: list[str] | None = None,
) -> dict[str, Path]:
    """Kopiuje ręczne nagrania użytkownika do docs/review-demos/."""
    lines = log if log is not None else []
    desktop_source = desktop_source.expanduser().resolve()
    if not desktop_source.is_file():
        raise FileNotFoundError(f"Brak pliku desktop: {desktop_source}")

    ext = desktop_source.suffix.lower()
    if ext not in VIDEO_SUFFIXES:
        raise ValueError(f"Nieobsługiwany format desktop ({ext}). Użyj: webm, mp4, mov, mkv.")

    REVIEW_DEMOS_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}

    _remove_old_latest_videos("desktop")
    desktop_dest = REVIEW_DEMOS_DIR / GPT_RECORDING_DESKTOP
    shutil.copy2(desktop_source, desktop_dest)
    out["desktop"] = desktop_dest
    lines.append(f"Desktop → {GPT_RECORDING_DESKTOP_REL} (Custom GPT)")

    if mobile_source is not None:
        mobile_source = mobile_source.expanduser().resolve()
        if not mobile_source.is_file():
            raise FileNotFoundError(f"Brak pliku mobile: {mobile_source}")
        mext = mobile_source.suffix.lower()
        if mext not in VIDEO_SUFFIXES:
            raise ValueError(f"Nieobsługiwany format mobile ({mext}).")
        _remove_old_latest_videos("mobile")
        mobile_dest = REVIEW_DEMOS_DIR / GPT_RECORDING_MOBILE
        shutil.copy2(mobile_source, mobile_dest)
        out["mobile"] = mobile_dest
        lines.append(f"Mobile → {GPT_RECORDING_MOBILE_REL} (Custom GPT)")

    return out
