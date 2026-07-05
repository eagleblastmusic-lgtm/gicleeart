"""Stałe wdrożeń — Shopify (shopify.theme.toml) i GitHub (gicleeart.git)."""

from __future__ import annotations

GITHUB_REMOTE_URL = "https://github.com/eagleblastmusic-lgtm/gicleeart.git"
GITHUB_DEFAULT_BRANCH = "master"

SHOPIFY_DEV = {
    "key": "development",
    "label": "Motyw dev na Shopify (piaskownica)",
    "environment": "development",
    "allow_live": False,
    "hint": "Piaskownica — GicleeApp dev (theme 200713503068), shopify.theme.toml.",
}

SHOPIFY_LIVE = {
    "key": "live",
    "label": "Live shop (produkcja)",
    "environment": "live",
    "allow_live": True,
    "hint": "Produkcja — opublikowany motyw (theme 197314249052), wymaga --allow-live.",
}

# Ścieżki / pliki wykluczone z commit_candidates (runtime, sekrety lokalne, backupy).
RUNTIME_DENYLIST_PREFIXES: tuple[str, ...] = (
    "cursor-api/Komponenty/dokumentysprzedazy/dane/",
    "cursor-api/Komponenty/kpir/",
    "cursor-api/Komponenty/kpir/documents/",
    "cursor-api/Komponenty/produkcja/dane/",
    "cursor-api/Komponenty/stronaglowna/data/backups/",
    "Pliki startowe dla GPT/",
    ".gpt_mirror/",
    "cursor-api/.gpt_mirror/",
    "_gicleeapp_staging/",
    "cursor-api/logs/",
    "cursor-api/backups/",
    "cursor-api/build/",
    "cursor-api/dist/",
)

RUNTIME_DENYLIST_BASENAMES: frozenset[str] = frozenset({
    ".shopify_session.json",
    "giclee_cursor_architect_knowledge.zip",
    "gpt_knowledge.zip",
    "orders_sync_state.json",
    "sync_state.json",
    "notified.json",
    "zamowienia.json",
    "analytics.db",
})

RUNTIME_DENYLIST_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
})
