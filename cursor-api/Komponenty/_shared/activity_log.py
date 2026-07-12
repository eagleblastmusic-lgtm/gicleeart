"""Prosty dziennik zdarzen (JSONL) wspoldzielony miedzy launcherem a komponentami."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from giclee_app.app_paths import log_path

_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_LEGACY_LOG_FILE = _LEGACY_DATA_DIR / "activity_log.jsonl"

# Zachowany publiczny symbol dla starszych wywolan i testow. Domyslnie wskazuje
# zewnetrzny AppData; odczyt legacy i copy-on-first-append obsluguje AppPath.
_DEFAULT_LOG_FILE = log_path(
    "Komponenty/_shared/activity_log.jsonl",
    legacy=_LEGACY_LOG_FILE,
).write_path
LOG_FILE = _DEFAULT_LOG_FILE
MAX_TAIL_LINES = 200


def _store():
    return log_path(
        "Komponenty/_shared/activity_log.jsonl",
        legacy=_LEGACY_LOG_FILE,
    )


def _write_file() -> Path:
    # Pozwala starszym testom/callerom jawnie podmienic LOG_FILE, a normalny
    # runtime nadal rozstrzyga korzen AppData dynamicznie z env.
    if LOG_FILE != _DEFAULT_LOG_FILE:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        return LOG_FILE
    return _store().seed_from_legacy()


def _read_file() -> Path:
    if LOG_FILE != _DEFAULT_LOG_FILE:
        return LOG_FILE
    return _store().read_path()


def append_activity(
    component: str,
    message: str,
    level: str = "info",
    *,
    detail: str = "",
) -> None:
    """Dopisuje jedna linie JSON; nowe zapisy trafiaja poza source checkout."""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "level": level,
        "message": message,
    }
    if detail:
        rec["detail"] = detail
    line = json.dumps(rec, ensure_ascii=False)
    try:
        with _write_file().open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def read_tail(max_lines: int = MAX_TAIL_LINES) -> list[str]:
    """Ostatnie N linii jako czytelny tekst (jedna linia = jedno zdarzenie)."""
    source = _read_file()
    if not source.is_file():
        return []
    try:
        raw = source.read_text(encoding="utf-8")
    except OSError:
        return []
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    tail = lines[-max_lines:]
    out: list[str] = []
    for ln in tail:
        try:
            d = json.loads(ln)
            ts = d.get("ts", "")
            comp = d.get("component", "")
            msg = d.get("message", ln)
            detail = d.get("detail", "")
            rendered = f"{ts}  [{comp}]  {msg}"
            if detail:
                rendered = f"{rendered}  ({detail})"
            out.append(rendered)
        except (json.JSONDecodeError, TypeError):
            out.append(ln)
    return out
