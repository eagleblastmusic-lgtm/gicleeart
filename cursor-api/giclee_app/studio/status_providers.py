"""Read-only statusy dla GicleeApp Studio — crash-safe, bez sekretów."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CURSOR_API_ROOT = Path(__file__).resolve().parents[2]
SESSION_FILE = CURSOR_API_ROOT / ".shopify_session.json"
ORDERS_FILE = (
    CURSOR_API_ROOT / "Komponenty" / "produkcja" / "dane" / "zamowienia.json"
)


@dataclass(frozen=True)
class StatusResult:
    ok: bool | None  # True=ok, False=problem, None=unknown
    label: str
    detail: str = ""


def shopify_status() -> StatusResult:
    try:
        if not SESSION_FILE.is_file():
            return StatusResult(False, "Brak sesji", "Uruchom npm run oauth w cursor-api")
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return StatusResult(None, "Sesja", "Nieprawidłowy format pliku")
        shop = str(data.get("shop") or "").strip()
        tok = str(data.get("accessToken") or "").strip()
        if not tok:
            return StatusResult(False, "Shopify", shop or "Brak tokena")
        shop_label = shop or "Połączono"
        return StatusResult(True, "Shopify OK", shop_label)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return StatusResult(None, "Shopify", "unknown")


def theme_dev_status() -> StatusResult:
    try:
        from Komponenty.stronaglowna.service import theme_dev_port_open

        if theme_dev_port_open():
            return StatusResult(True, "Theme Dev", "Port 9292 aktywny")
        return StatusResult(False, "Theme Dev", "Nie uruchomiony")
    except Exception:  # noqa: BLE001
        return StatusResult(None, "Theme Dev", "unknown")


def customtkinter_available() -> bool:
    try:
        import customtkinter  # noqa: F401

        return True
    except ImportError:
        return False


def github_status() -> StatusResult:
    """Local-only — bez GitHub API; bez git status dirty."""
    root = CURSOR_API_ROOT
    git_dir = root / ".git"
    if not git_dir.is_dir():
        return StatusResult(None, "Git", "—")
    detail = "repo lokalne"
    try:
        import subprocess

        proc = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0:
            sha = (proc.stdout or "").strip()
            if sha and len(sha) <= 12:
                detail = f"HEAD {sha}"
    except (OSError, Exception):  # noqa: BLE001 — timeout/subprocess errors
        pass
    return StatusResult(True, "Git", detail)


def gpt_snapshot_status() -> StatusResult:
    """Local-only — istnienie integracjagpt + .gpt_mirror, bez odczytu config."""
    root = CURSOR_API_ROOT
    integracjagpt_dir = root / "Komponenty" / "integracjagpt"
    mirror_dir = root / ".gpt_mirror"
    has_module = integracjagpt_dir.is_dir()
    has_mirror = mirror_dir.is_dir()
    if has_module and has_mirror:
        return StatusResult(True, "GPT", "local mirror")
    if has_module:
        return StatusResult(None, "GPT", "mirror missing")
    return StatusResult(None, "GPT", "local only")


def app_version_status() -> StatusResult:
    try:
        from .. import __version__
        from ..component_loader import find_components_dir

        comp_dir = find_components_dir()
        return StatusResult(True, f"v{__version__}", str(comp_dir))
    except Exception:  # noqa: BLE001
        return StatusResult(None, "Wersja", "unknown")


def component_counts(
    *,
    all_components: list | None = None,
    visible_components: list | None = None,
) -> tuple[int, int]:
    """(wszystkie, widoczne bez hidden). Opcjonalnie z cache Studio — bez discover."""
    if all_components is not None and visible_components is not None:
        return len(all_components), len(visible_components)
    try:
        from ..component_loader import discover_components, find_components_dir

        root = find_components_dir()
        all_c = discover_components(root, include_hidden=True)
        if visible_components is not None:
            return len(all_c), len(visible_components)
        vis = discover_components(root, include_hidden=False)
        return len(all_c), len(vis)
    except Exception:  # noqa: BLE001
        return 0, 0


def activity_log_lines(max_lines: int = 8) -> list[str]:
    try:
        from Komponenty._shared.activity_log import read_tail

        return read_tail(max_lines)
    except Exception:  # noqa: BLE001
        return []


def nbp_eur_status() -> StatusResult:
    try:
        from Komponenty._shared import fx_rates

        cache = fx_rates.load_cache()
        eur = cache.get("EUR") if isinstance(cache, dict) else None
        if isinstance(eur, dict) and eur.get("rate") is not None:
            return StatusResult(
                True,
                "EUR/NBP",
                f"rate={eur.get('rate')} ({eur.get('fetched_at', '')})",
            )
        return StatusResult(None, "EUR/NBP", "Brak cache")
    except Exception:  # noqa: BLE001
        return StatusResult(None, "EUR/NBP", "unknown")


def production_orders_count() -> int | None:
    try:
        if not ORDERS_FILE.is_file():
            return None
        data = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            orders = data.get("orders")
            if isinstance(orders, list):
                return len(orders)
        return None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def refresh_all_topbar() -> dict[str, StatusResult]:
    return {
        "shopify": shopify_status(),
        "theme_dev": theme_dev_status(),
        "github": github_status(),
        "gpt_snapshot": gpt_snapshot_status(),
    }
