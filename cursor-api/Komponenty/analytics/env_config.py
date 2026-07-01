"""Konfiguracja środowiskowa modułu analityki."""

from __future__ import annotations

import os
from pathlib import Path

_COMPONENT_DIR = Path(__file__).resolve().parent
_CURSOR_API = _COMPONENT_DIR.parents[1]
_ENV_FILE = _CURSOR_API / ".env"


def _load_dotenv(*, force_analytics: bool = False) -> None:
    if not _ENV_FILE.is_file():
        return
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not key:
            continue
        if force_analytics and key.startswith("ANALYTICS_"):
            os.environ[key] = val
        elif key not in os.environ:
            os.environ[key] = val


_load_dotenv()


def reload_analytics_env() -> None:
    """Odśwież ANALYTICS_* z pliku .env (np. po edycji bez restartu)."""
    _load_dotenv(force_analytics=True)


def collect_secret() -> str:
    return (os.environ.get("ANALYTICS_COLLECT_SECRET") or "").strip()


def allowed_shop_domain() -> str:
    return (os.environ.get("ANALYTICS_ALLOWED_SHOP_DOMAIN") or "gicleeart.eu").strip().lower()


def server_port() -> int:
    try:
        return int(os.environ.get("ANALYTICS_SERVER_PORT") or "5100")
    except ValueError:
        return 5100


def auto_sync_interval_seconds() -> int:
    """Interwał auto-sync Worker → SQLite (0 = wyłączone). Domyślnie 300 s (5 min)."""
    try:
        return int(os.environ.get("ANALYTICS_AUTO_SYNC_SECONDS") or "300")
    except ValueError:
        return 300


def collect_public_url() -> str:
    reload_analytics_env()
    return (os.environ.get("ANALYTICS_COLLECT_URL") or "").strip()


def default_collect_url(port: int | None = None) -> str:
    p = port or server_port()
    return f"http://127.0.0.1:{p}/api/analytics/collect"


def effective_collect_url(port: int | None = None) -> str:
    """URL do pixela: Worker z .env, inaczej lokalny (tylko test)."""
    url = collect_public_url()
    if url:
        return url
    return default_collect_url(port)


def worker_base_url() -> str:
    explicit = (os.environ.get("ANALYTICS_WORKER_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    collect = collect_public_url()
    if not collect:
        return ""
    if "/api/analytics/collect" in collect:
        return collect.split("/api/analytics/collect")[0].rstrip("/")
    return collect.rstrip("/")


def db_path() -> Path:
    override = (os.environ.get("ANALYTICS_DB_PATH") or "").strip()
    if override:
        return Path(override)
    return _COMPONENT_DIR / "dane" / "analytics.db"
