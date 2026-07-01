"""Prosty dziennik zdarzen (JSONL) wspoldzielony miedzy launcherem a komponentami."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
LOG_FILE = _DATA_DIR / "activity_log.jsonl"
MAX_TAIL_LINES = 200


def append_activity(
    component: str,
    message: str,
    level: str = "info",
    *,
    detail: str = "",
) -> None:
    """Dopisuje jedna linie JSON (komponent, poziom, czas UTC, tresc)."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
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
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def read_tail(max_lines: int = MAX_TAIL_LINES) -> list[str]:
    """Ostatnie N linii jako czytelny tekst (jedna linia = jedno zdarzenie)."""
    if not LOG_FILE.is_file():
        return []
    try:
        raw = LOG_FILE.read_text(encoding="utf-8")
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
            line = f"{ts}  [{comp}]  {msg}"
            if detail:
                line = f"{line}  ({detail})"
            out.append(line)
        except (json.JSONDecodeError, TypeError):
            out.append(ln)
    return out
