"""Diff, walidacja, backupy, skan sekcji, podgląd, deploy — Strona główna."""

from __future__ import annotations

import difflib
import json
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .registry import HOME_ZONES, SECTION_NAME_HINTS
from .service import (
    _backups_dir,
    index_template_path,
    kill_process_listening_on_port,
    load_zone_values,
    mobile_hero_path,
    path_get,
    settings_data_path,
    shopify_cli_popen,
    shopify_ref_label,
    theme_dev_http_ready,
    theme_dev_port_open,
    theme_root,
    validate_template_paths,
    zone_enabled,
)

PREVIEW_QUERY = "giclee_skip_splash=1&giclee_skip_notice=1"
HOMEPAGE_URL = "https://gicleeart.eu/"
THEME_DEV_URL = "http://127.0.0.1:9292/"

DEPLOY_TARGETS: dict[str, dict[str, Any]] = {
    "development": {
        "label": "Development (shopify.theme.toml)",
        "environment": "development",
        "allow_live": False,
        "hint": "Motyw «GicleeApp dev» (200713503068) — dedykowana piaskownica.",
    },
    "unpublished": {
        "label": "Kopia nieopublikowana",
        "environment": "unpublished",
        "allow_live": False,
        "hint": "Theme ID 199521829212 — kopia robocza na Shopify.",
    },
    "live": {
        "label": "Live (opublikowany motyw)",
        "environment": "live",
        "allow_live": True,
        "hint": "Theme ID 197314249052 — wymaga --allow-live.",
    },
}

_theme_dev_proc: subprocess.Popen[str] | None = None


@dataclass
class ChangeItem:
    category: str
    zone_label: str
    field_label: str
    detail: str = ""


@dataclass
class ChangeSummary:
    items: list[ChangeItem] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in self.items:
            out[item.category] = out.get(item.category, 0) + 1
        return out

    def headline(self) -> str:
        if not self.items:
            return "Brak zmian względem wczytanego stanu."
        parts: list[str] = []
        labels = {
            "image": "grafik",
            "heading": "nagłówków",
            "body": "treści",
            "text": "pól tekstowych",
            "bool": "ustawień",
            "site_notice": "site notice",
            "visibility": "widoczności sekcji",
        }
        for key, n in self.counts.items():
            label = labels.get(key, key)
            parts.append(f"{n} {label}")
        return "Zmieniono: " + ", ".join(parts) + "."


@dataclass
class ValidationIssue:
    level: str
    zone_label: str
    message: str


def _field_category(kind: str, field_id: str) -> str:
    if field_id.startswith("sn_"):
        return "site_notice"
    if kind in ("shopify_image", "shopify_video", "theme_asset"):
        return "image"
    if kind == "heading":
        return "heading"
    if kind == "body":
        return "body"
    if kind == "bool" or kind == "blocks_visible":
        return "bool" if kind == "bool" else "visibility"
    return "text"


def compute_changes(
    baseline_template: dict[str, Any],
    baseline_settings: dict[str, Any],
    pending_template: dict[str, Any],
    pending_settings: dict[str, Any],
) -> ChangeSummary:
    summary = ChangeSummary()
    for zone in HOME_ZONES:
        base_vals = load_zone_values(baseline_template, zone, settings=baseline_settings)
        new_vals = load_zone_values(pending_template, zone, settings=pending_settings)
        if not zone.settings_only and bool(base_vals.get("_enabled")) != bool(new_vals.get("_enabled")):
            summary.items.append(
                ChangeItem(
                    "visibility",
                    zone.label,
                    "Widoczność sekcji",
                    "wł." if new_vals.get("_enabled") else "wył.",
                )
            )
        for fld in zone.fields:
            old = base_vals.get(fld.field_id)
            new = new_vals.get(fld.field_id)
            if old == new:
                continue
            cat = _field_category(fld.kind, fld.field_id)
            detail = ""
            if cat == "image":
                detail = f"{shopify_ref_label(str(old))} → {shopify_ref_label(str(new))}"
            elif cat in ("heading", "body", "text", "site_notice"):
                o = str(old or "")[:40]
                n = str(new or "")[:40]
                detail = f"«{o}» → «{n}»" if o or n else ""
            elif cat == "visibility" and isinstance(old, bool) and isinstance(new, bool):
                detail = "wł." if new else "wył."
            summary.items.append(ChangeItem(cat, zone.label, fld.label, detail))
    return summary


def validate_homepage(
    template: dict[str, Any],
    settings: dict[str, Any],
    *,
    zone_values: dict[str, dict[str, Any]] | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for msg in validate_template_paths(template):
        issues.append(ValidationIssue("error", "Szablon", f"Brak pola w index.json: {msg}"))

    for zone in HOME_ZONES:
        if zone.settings_only:
            vals = (zone_values or {}).get(zone.zone_id) or load_zone_values(
                template, zone, settings=settings,
            )
            if vals.get("sn_enabled") and not str(vals.get("sn_message") or "").strip():
                issues.append(ValidationIssue("warn", zone.label, "Site notice włączony, ale treść pusta."))
            continue

        enabled = (zone_values or {}).get(zone.zone_id, {}).get("_enabled")
        if enabled is None:
            enabled = zone_enabled(template, zone)
        if not enabled:
            continue

        vals = (zone_values or {}).get(zone.zone_id) or load_zone_values(template, zone, settings=settings)
        headings = [f for f in zone.fields if f.kind == "heading"]
        bodies = [f for f in zone.fields if f.kind == "body"]
        has_heading = any(str(vals.get(f.field_id) or "").strip() for f in headings)
        has_body = any(str(vals.get(f.field_id) or "").strip() for f in bodies)
        if headings and bodies and not has_heading and not has_body:
            issues.append(ValidationIssue("error", zone.label, "Sekcja widoczna, ale brak nagłówka i treści."))

        for fld in zone.fields:
            if fld.kind not in ("shopify_image", "shopify_video", "theme_asset"):
                continue
            ref = str(vals.get(fld.field_id) or path_get(template, fld.path or ()) or "")
            if fld.kind == "theme_asset":
                if not mobile_hero_path().is_file():
                    issues.append(
                        ValidationIssue(
                            "warn",
                            zone.label,
                            "Brak pliku mobile hero — wgraj slajd mobile lub zapisz assets.",
                        )
                    )
            elif zone.zone_id == "hero" and fld.field_id in ("hero_desktop", "hero_desktop_video"):
                media = str(vals.get("hero_media_type") or "image").strip().lower()
                if media == "collage":
                    continue
                if fld.field_id == "hero_desktop_video" and media != "video":
                    continue
                if fld.field_id == "hero_desktop" and media != "image":
                    continue
                if media == "video":
                    if not ref.startswith("shopify://files/videos/"):
                        if ref.startswith("gid://shopify/Video/"):
                            issues.append(
                                ValidationIssue(
                                    "error",
                                    zone.label,
                                    "Film hero: zapisz ponownie (stary format GID) lub wgraj film jeszcze raz.",
                                )
                            )
                        else:
                            issues.append(ValidationIssue("error", zone.label, "Brak filmu hero (desktop)."))
                    elif bool(vals.get("hero_video_boomerang")):
                        rev = str(vals.get("hero_desktop_video_reversed") or "").strip()
                        if not rev.startswith("shopify://files/videos/"):
                            issues.append(
                                ValidationIssue(
                                    "error",
                                    zone.label,
                                    "Brak pliku pętli boomerang — zapisz ponownie (wymaga ffmpeg).",
                                )
                            )
                elif not ref.startswith("shopify://"):
                    issues.append(ValidationIssue("error", zone.label, "Brak slajdu hero (desktop)."))
            elif ("before" in fld.field_id or "after" in fld.field_id) and not ref.startswith("shopify://"):
                issues.append(ValidationIssue("error", zone.label, f"{fld.label}: brak obrazu."))

        if zone.zone_id == "hero":
            media = str(vals.get("hero_media_type") or "image").strip().lower()
            if media == "collage":
                from .video_collage import parse_collage, validate_collage

                for msg in validate_collage(parse_collage(vals.get("hero_video_collage"))):
                    issues.append(ValidationIssue("error", zone.label, msg))

        for fld in zone.fields:
            if fld.kind != "body":
                continue
            text = str(vals.get(fld.field_id) or "")
            if len(text) > 4000:
                issues.append(
                    ValidationIssue("warn", zone.label, f"{fld.label}: bardzo długa treść ({len(text)} znaków).")
                )

        cta_hidden = any(
            fld.kind == "blocks_visible" and not bool(vals.get(fld.field_id, True))
            for fld in zone.fields
        )

        for fld in zone.fields:
            if fld.kind != "link":
                continue
            if cta_hidden:
                continue
            link = str(vals.get(fld.field_id) or "").strip()
            label_key = fld.field_id.replace("_link", "_label")
            label = str(vals.get(label_key) or "").strip()
            if label and not link:
                issues.append(ValidationIssue("warn", zone.label, f"Przycisk «{label}» bez linku."))
            if link and not (link.startswith("shopify://") or link.startswith("http") or link.startswith("/")):
                issues.append(ValidationIssue("warn", zone.label, f"Nietypowy link: {link}"))

    return issues


def list_backups() -> list[dict[str, Any]]:
    root = _backups_dir()
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("index-*.json"), reverse=True):
        ts = path.stem.replace("index-", "", 1)
        settings = root / f"settings-{ts}.json"
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            label = mtime.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            label = ts
        rows.append(
            {
                "timestamp": ts,
                "label": label,
                "index_path": path,
                "settings_path": settings if settings.is_file() else None,
            }
        )
    return rows


def restore_backup(timestamp: str) -> None:
    root = _backups_dir()
    index_src = root / f"index-{timestamp}.json"
    settings_src = root / f"settings-{timestamp}.json"
    if not index_src.is_file():
        raise FileNotFoundError(f"Brak kopii index-{timestamp}.json")
    shutil.copy2(index_src, index_template_path())
    if settings_src.is_file():
        shutil.copy2(settings_src, settings_data_path())


def diff_against_file(current_text: str, backup_path: Path, *, label: str) -> str:
    if not backup_path.is_file():
        return f"({label}: brak pliku kopii)\n"
    old = backup_path.read_text(encoding="utf-8")
    lines = difflib.unified_diff(
        old.splitlines(keepends=True),
        current_text.splitlines(keepends=True),
        fromfile=f"backup/{backup_path.name}",
        tofile=label,
        lineterm="",
    )
    text = "".join(lines)
    return text or f"({label}: brak różnic względem kopii)\n"


@dataclass
class SectionScanResult:
    zone_id: str
    zone_label: str
    expected_key: str
    status: str
    found_key: str | None = None
    hint: str = ""


def scan_section_keys(template: dict[str, Any]) -> list[SectionScanResult]:
    sections = template.get("sections") if isinstance(template.get("sections"), dict) else {}
    results: list[SectionScanResult] = []
    for zone in HOME_ZONES:
        if zone.settings_only:
            continue
        expected = zone.section_key
        if expected in sections:
            results.append(SectionScanResult(zone.zone_id, zone.label, expected, "ok", expected))
            continue
        hints = SECTION_NAME_HINTS.get(zone.zone_id, [zone.label])
        found_key = None
        for key, sec in sections.items():
            if not isinstance(sec, dict):
                continue
            name = str(sec.get("name") or "").lower()
            for hint in hints:
                if hint.lower() in name or name in hint.lower():
                    found_key = key
                    break
            if found_key:
                break
        if found_key:
            results.append(
                SectionScanResult(
                    zone.zone_id,
                    zone.label,
                    expected,
                    "remapped",
                    found_key,
                    f"Zaktualizuj section_key w registry.py: «{expected}» → «{found_key}»",
                )
            )
        else:
            results.append(
                SectionScanResult(
                    zone.zone_id,
                    zone.label,
                    expected,
                    "missing",
                    None,
                    "Sekcja nie znaleziona po ID ani nazwie w index.json.",
                )
            )
    return results


def preview_url(*, local: bool = False) -> str:
    base = THEME_DEV_URL if local else HOMEPAGE_URL
    return f"{base.rstrip('/')}/?{PREVIEW_QUERY}"


def theme_dev_running(*, require_http: bool = False) -> bool:
    if _theme_dev_proc is not None and _theme_dev_proc.poll() is None:
        if not require_http:
            return True
        return theme_dev_http_ready(url=preview_url(local=True))
    if not theme_dev_port_open():
        return False
    if require_http:
        return theme_dev_http_ready(url=preview_url(local=True))
    return True


def restart_theme_dev_port(*, on_line: Callable[[str], None] | None = None) -> None:
    """Zatrzymaj theme dev i zwolnij port 9292 (zawieszone połączenia CLOSE_WAIT)."""
    stop_theme_dev()
    killed = kill_process_listening_on_port()
    if killed and on_line:
        on_line(f"Zatrzymano proces(y) na porcie 9292: {', '.join(str(p) for p in killed)}")


def start_theme_dev(*, on_line: Callable[[str], None] | None = None, force_restart: bool = False) -> None:
    global _theme_dev_proc
    if force_restart:
        restart_theme_dev_port(on_line=on_line)
    elif theme_dev_running(require_http=True):
        return
    elif theme_dev_port_open() and not theme_dev_http_ready(url=preview_url(local=True)):
        if on_line:
            on_line("Port 9292 otwarty, ale serwer nie odpowiada — restartuję theme dev…")
        restart_theme_dev_port(on_line=on_line)
    elif theme_dev_running():
        return
    proc = shopify_cli_popen(["theme", "dev", "--environment", "development"], cwd=theme_root())
    _theme_dev_proc = proc
    assert _theme_dev_proc.stdout is not None

    def _reader() -> None:
        assert _theme_dev_proc is not None
        assert _theme_dev_proc.stdout is not None
        for line in _theme_dev_proc.stdout:
            if line and on_line:
                on_line(line.rstrip())

    threading.Thread(target=_reader, daemon=True).start()


def stop_theme_dev() -> None:
    global _theme_dev_proc
    if _theme_dev_proc is not None:
        _theme_dev_proc.terminate()
        try:
            _theme_dev_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _theme_dev_proc.kill()
        _theme_dev_proc = None
    kill_process_listening_on_port()


def write_home_assets(
    template: dict[str, Any],
    *,
    mobile_slide_urls: list[str] | None = None,
) -> None:
    from .registry import ZONE_HOME_HOOK

    assets_dir = theme_root() / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    slides: list[str] = list(mobile_slide_urls or [])
    if not slides and mobile_hero_path().is_file():
        slides = ["MALE_ORG.webp"]

    mobile_js = "window.GICLEE_HOME_MOBILE_SLIDES = " + json.dumps(slides, ensure_ascii=False) + ";\n"
    (assets_dir / "giclee-home-mobile.js").write_text(mobile_js, encoding="utf-8")

    section_map: dict[str, str] = {}
    for zone in HOME_ZONES:
        if zone.settings_only:
            continue
        hook = ZONE_HOME_HOOK.get(zone.zone_id)
        if hook and zone.section_key:
            section_map[hook] = zone.section_key
    sections_js = "window.GICLEE_HOME_SECTIONS = " + json.dumps(section_map, ensure_ascii=False) + ";\n"
    (assets_dir / "giclee-home-sections.js").write_text(sections_js, encoding="utf-8")

    from .video_collage import empty_collage, parse_collage, write_collage_asset

    collage_path = (
        "sections",
        "slideshow_4LMfx7",
        "blocks",
        "slide_NPidVp",
        "settings",
        "video_collage_json",
    )
    media_type = str(
        path_get(
            template,
            ("sections", "slideshow_4LMfx7", "blocks", "slide_NPidVp", "settings", "media_type_1"),
        )
        or ""
    )
    raw_collage = path_get(template, collage_path)
    if media_type == "collage":
        write_collage_asset(parse_collage(raw_collage or ""), assets_dir)
    else:
        write_collage_asset(empty_collage(), assets_dir)
