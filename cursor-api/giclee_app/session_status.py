"""Tekstowy raport: sesja Shopify, NBP, ostatnia modyfikacja konfiguracji aplikacji."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# cursor-api/ (nad giclee_app/)
CURSOR_API_ROOT = Path(__file__).resolve().parents[1]
SESSION_FILE = CURSOR_API_ROOT / ".shopify_session.json"
SHOPIFY_APP_TOML = CURSOR_API_ROOT / "shopify.app.toml"
PARTNERS_META = (
    Path(__file__).resolve().parents[1]
    / "Komponenty"
    / "_shared"
    / "data"
    / "partners_deploy_meta.json"
)


def _fmt_mtime(path: Path) -> str:
    if not path.is_file():
        return "(brak pliku)"
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except OSError:
        return "(nie mozna odczytac)"


def _git_last_commit_touching(rel_path: str) -> str | None:
    try:
        r = subprocess.run(
            [
                "git",
                "-C",
                str(CURSOR_API_ROOT),
                "log",
                "-1",
                "--format=%ci",
                "--",
                rel_path,
            ],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        if r.returncode != 0:
            return None
        line = (r.stdout or "").strip().splitlines()
        return line[0] if line else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def format_session_status_text() -> str:
    lines: list[str] = []
    lines.append("=== Sesja Shopify (.shopify_session.json) ===")
    if not SESSION_FILE.is_file():
        lines.append("  Brak pliku — uruchom w folderze cursor-api: npm run oauth")
    else:
        lines.append(f"  Plik: {SESSION_FILE}")
        lines.append(f"  Zapisano (mtime): {_fmt_mtime(SESSION_FILE)}")
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            shop = (data.get("shop") or "").strip()
            tok = (data.get("accessToken") or "").strip()
            lines.append(f"  Sklep: {shop or '(brak)'}")
            lines.append(
                f"  Token: {'OK (' + str(len(tok)) + ' zn.)' if tok else 'BRAK'}"
            )
        except (OSError, json.JSONDecodeError) as e:
            lines.append(f"  Nie mozna odczytac JSON: {e}")

    lines.append("")
    lines.append("=== Kursy NBP (cache EUR itd.) ===")
    try:
        from Komponenty._shared import fx_rates

        cache = fx_rates.load_cache()
        eur = cache.get("EUR") if isinstance(cache, dict) else None
        if isinstance(eur, dict):
            lines.append(f"  EUR: rate={eur.get('rate')}  zrodlo={eur.get('source')}")
            lines.append(f"  Ostatnie pobranie: {eur.get('fetched_at', '(brak)')}")
        else:
            lines.append("  Brak wpisu EUR w fx_cache.json (odswiez w dialogu Rynki).")
    except Exception as e:
        lines.append(f"  Blad odczytu cache: {e}")

    lines.append("")
    lines.append("=== Konfiguracja aplikacji Partners / CLI ===")
    lines.append(f"  shopify.app.toml (mtime): {_fmt_mtime(SHOPIFY_APP_TOML)}")
    git_line = _git_last_commit_touching("shopify.app.toml")
    if git_line:
        lines.append(f"  Ostatni commit dotykajacy pliku (git): {git_line}")
    else:
        lines.append(
            "  Ostatni commit (git): nie znaleziono (brak repo albo plik nie w historii)."
        )
    if PARTNERS_META.is_file():
        try:
            meta = json.loads(PARTNERS_META.read_text(encoding="utf-8"))
            when = meta.get("last_deploy_iso") or meta.get("note")
            if when:
                lines.append(f"  Zapis reczny (partners_deploy_meta.json): {when}")
        except (OSError, json.JSONDecodeError):
            lines.append("  partners_deploy_meta.json: nie mozna odczytac.")
    else:
        lines.append(
            "  Opcjonalnie: po deploy wpisz date do Komponenty/_shared/data/partners_deploy_meta.json"
        )

    lines.append("")
    lines.append(
        "Uwaga: Shopify nie zapisuje lokalnie daty 'deploy' — mtime i git to przyblizenie."
    )
    return "\n".join(lines)
