"""Odczyt konfiguracji Gmail IMAP z cursor-api/.env."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_USER = "gicleeartpl@gmail.com"


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


def gmail_imap_user() -> str:
    load_dotenv_once()
    return (os.environ.get("GMAIL_IMAP_USER") or DEFAULT_USER).strip() or DEFAULT_USER


def gmail_imap_password() -> str:
    load_dotenv_once()
    return (
        os.environ.get("GMAIL_IMAP_APP_PASSWORD")
        or os.environ.get("GMAIL_APP_PASSWORD")
        or ""
    ).strip().replace(" ", "")


def credentials_configured() -> bool:
    return bool(gmail_imap_password())


def client_orders_base_dir() -> Path:
    load_dotenv_once()
    raw = (os.environ.get("CLIENT_ORDERS_DIR") or r"E:\Firma\1. Obrazy\3. Klienci").strip()
    return Path(raw)
