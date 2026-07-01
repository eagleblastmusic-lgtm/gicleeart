"""Odczyt kluczy API z cursor-api/.env."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_RESEND_MONTHLY = 3_000
DEFAULT_RESEND_DAILY = 100
DEFAULT_SERPAPI_MONTHLY = 100


def _env_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
        if parent.name == "cursor-api":
            return parent / ".env"
    return here.parents[2] / ".env"


def load_dotenv_once() -> None:
    path = _env_path()
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def env_str(name: str) -> str:
    load_dotenv_once()
    return (os.environ.get(name) or "").strip()


def set_env_value(key: str, value: str) -> Path:
    """Ustawia/aktualizuje wartosc w cursor-api/.env oraz w os.environ."""
    if not key:
        raise ValueError("klucz nie moze byc pusty")
    path = _env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    new_line = f"{key}={value}"
    lines: list[str] = []
    found = False
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                lines.append(raw)
                continue
            k, _, _v = stripped.partition("=")
            if k.strip() == key:
                lines.append(new_line)
                found = True
            else:
                lines.append(raw)
    if not found:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(new_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value
    return path


def env_int(name: str, default: int) -> int:
    load_dotenv_once()
    raw = (os.environ.get(name) or "").strip().replace("_", "").replace(" ", "")
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def resend_api_key() -> str:
    return env_str("RESEND_API_KEY")


def serpapi_key() -> str:
    return env_str("SERPAPI_KEY")


def resend_monthly_quota() -> int:
    return env_int("RESEND_MONTHLY_QUOTA", DEFAULT_RESEND_MONTHLY)


def resend_daily_quota() -> int:
    return env_int("RESEND_DAILY_QUOTA", DEFAULT_RESEND_DAILY)


def serpapi_monthly_quota() -> int:
    return env_int("SERPAPI_MONTHLY_QUOTA", DEFAULT_SERPAPI_MONTHLY)
