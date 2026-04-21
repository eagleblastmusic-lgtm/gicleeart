"""Automatyczne backupy danych aplikacji Giclee.

Cel: raz dziennie zipujemy wszystkie wazne pliki (dane komponentow, notatki,
konfiguracje) do `backups/YYYY-MM-DD.zip`. Trzymamy maksymalnie N ostatnich
zipow (domyslnie 14).

Co backupujemy (wzgledem `cursor-api/`):
- `Komponenty/*/dane/*.json`        (zamowienia produkcji, planer, zadania, finanse)
- `Komponenty/*/data/*.json`        (dodajobraz templates, fx cache, socialmedia)
- `Komponenty/notatnik/notatki/`    (wszystkie notatki .md + ukryte .favorites.json)
- `Komponenty/*/markets_config.json`
- `shopify.app.toml`                (konfig OAuth)
- `.env.example`                    (NIE .env - zawiera sekrety, nie backup-ujemy)

Wywolanie:
    from Komponenty._shared.backup import run_daily_backup_if_needed
    run_daily_backup_if_needed()

Launcher wola to raz przy starcie - backup odpalany tylko jesli dzisiaj jeszcze
nie byl zrobiony (state w `backups/.last_run.json`).
"""

from __future__ import annotations

import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Callable

# Cursor-api/ (2 poziomy w gore: _shared -> Komponenty -> cursor-api)
_CURSOR_API_DIR = Path(__file__).resolve().parents[2]
_BACKUPS_DIR = _CURSOR_API_DIR / "backups"
_STATE_FILE = _BACKUPS_DIR / ".last_run.json"

# Wzorce co backupujemy (relative do cursor-api/)
_INCLUDE_PATTERNS: list[str] = [
    "Komponenty/*/dane/*.json",
    "Komponenty/*/data/*.json",
    "Komponenty/*/data/*.md",
    "Komponenty/notatnik/notatki/**/*.md",
    "Komponenty/notatnik/notatki/.favorites.json",
    "Komponenty/*/markets_config.json",
    "Komponenty/_shared/data/*.json",
    "shopify.app.toml",
    ".env.example",
]

# Co jawnie POMIJAMY (nawet jesli pasuje do powyzszego)
_EXCLUDE_PATTERNS: list[str] = [
    "Komponenty/zadania/data/signals_cache.json",  # cache Shopify - niepotrzebny
    "Komponenty/blog/data/articles_cache.json",    # cache Shopify
    "Komponenty/blog/data/preview.html",           # transient
    "Komponenty/*/data/fx_cache.json",             # FX cache - regeneruje sie
]

_MAX_BACKUPS = 14  # trzymamy ostatnie N dni


def _collect_files() -> list[Path]:
    """Zwraca posortowana liste plikow do backupu."""
    files: set[Path] = set()
    for pattern in _INCLUDE_PATTERNS:
        for p in _CURSOR_API_DIR.glob(pattern):
            if p.is_file():
                files.add(p)
    # Filtruj wykluczenia
    excluded: set[Path] = set()
    for pattern in _EXCLUDE_PATTERNS:
        for p in _CURSOR_API_DIR.glob(pattern):
            if p.is_file():
                excluded.add(p)
    return sorted(files - excluded)


def _read_state() -> dict:
    if not _STATE_FILE.is_file():
        return {}
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(state: dict) -> None:
    _BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _rotate_old_backups(keep: int = _MAX_BACKUPS) -> int:
    """Usuwa najstarsze zipy zostawiajac `keep` najnowszych. Zwraca liczbe usunietych."""
    if not _BACKUPS_DIR.is_dir():
        return 0
    zips = sorted(_BACKUPS_DIR.glob("*.zip"), key=lambda p: p.name)
    removed = 0
    while len(zips) > keep:
        oldest = zips.pop(0)
        try:
            oldest.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def create_backup(*, logger: Callable[[str], None] | None = None) -> Path | None:
    """Tworzy zip z biezacym stanem i zwraca sciezke (albo None przy bledzie)."""
    _BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    target = _BACKUPS_DIR / f"{today}.zip"
    # Jesli dzisiejszy zip juz istnieje - nadpisujemy (swiezsza wersja w ciagu dnia)
    files = _collect_files()
    if not files:
        if logger:
            logger("[backup] Nic nie znaleziono do zarchiwizowania.")
        return None
    try:
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for f in files:
                arcname = f.relative_to(_CURSOR_API_DIR).as_posix()
                try:
                    zf.write(f, arcname=arcname)
                except OSError as e:
                    if logger:
                        logger(f"[backup] pominieto {f}: {e}")
                    continue
            # Metadata manifest
            manifest = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "cursor_api_dir": str(_CURSOR_API_DIR),
                "file_count": len(files),
                "files": [f.relative_to(_CURSOR_API_DIR).as_posix() for f in files],
            }
            zf.writestr("_backup_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    except OSError as e:
        if logger:
            logger(f"[backup] BLAD tworzenia zipa: {e}")
        return None
    if logger:
        logger(f"[backup] OK {target.name} ({len(files)} plikow, "
               f"{target.stat().st_size / 1024:.1f} KB)")
    return target


def run_daily_backup_if_needed(
    *, logger: Callable[[str], None] | None = None,
) -> Path | None:
    """Wykonuje backup tylko jesli dzisiaj jeszcze nie byl zrobiony. Idempotentne."""
    state = _read_state()
    today = date.today().isoformat()
    if state.get("last_backup_date") == today:
        if logger:
            logger(f"[backup] Dzisiaj ({today}) juz byl backup - pomijam.")
        return None
    result = create_backup(logger=logger)
    if result is None:
        return None
    removed = _rotate_old_backups()
    if removed and logger:
        logger(f"[backup] Usunieto {removed} starych zipow (trzymamy {_MAX_BACKUPS} ostatnich).")
    state["last_backup_date"] = today
    state["last_backup_file"] = result.name
    _write_state(state)
    return result


def restore_from_backup(
    zip_path: Path,
    *,
    target_dir: Path | None = None,
    logger: Callable[[str], None] | None = None,
) -> int:
    """Rozpakowuje backup do `target_dir` (domyslnie cursor-api/). Zwraca liczbe plikow.

    UWAGA: **NADPISUJE** istniejace pliki. Wolaj po potwierdzeniu uzytkownika.
    """
    target_dir = target_dir or _CURSOR_API_DIR
    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member == "_backup_manifest.json":
                continue
            if member.startswith("/") or ".." in member.split("/"):
                continue  # bezpieczenstwo: path traversal
            zf.extract(member, path=target_dir)
            count += 1
    if logger:
        logger(f"[backup] Przywrocono {count} plikow z {zip_path.name}")
    return count


def list_backups() -> list[dict]:
    """Zwraca liste wszystkich backupow z meta-danymi."""
    if not _BACKUPS_DIR.is_dir():
        return []
    out: list[dict] = []
    for z in sorted(_BACKUPS_DIR.glob("*.zip"), reverse=True):
        try:
            st = z.stat()
            out.append({
                "path": str(z),
                "name": z.name,
                "size_kb": st.st_size / 1024,
                "created": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            })
        except OSError:
            continue
    return out
