"""Konfiguracja komponentu Integracja z GPT."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from giclee_app.app_paths import atomic_write_text, config_path, data_path

COMPONENT_DIR = Path(__file__).resolve().parent
CURSOR_API_DIR = COMPONENT_DIR.parents[1]
THEME_ROOT = COMPONENT_DIR.parents[2]  # …/pusty (motyw Shopify)
MIRROR_DIR = CURSOR_API_DIR / ".gpt_mirror"
_LEGACY_DATA_DIR = COMPONENT_DIR / "data"
_LEGACY_CONFIG_FILE = _LEGACY_DATA_DIR / "gpt_config.json"
_RUNTIME_DATA = data_path(
    "Komponenty/integracjagpt/data/.path",
    legacy=_LEGACY_DATA_DIR / ".path",
)
_CONFIG = config_path(
    "Komponenty/integracjagpt/data/gpt_config.json",
    legacy=_LEGACY_CONFIG_FILE,
)
# Runtime ZIP-y i nagrania trafiają do Local AppData. CONFIG_FILE pozostaje
# kompatybilnym sentinelem dla testów, ale load/save rozwiązuje go przez AppPath.
DATA_DIR = _RUNTIME_DATA.write_path.parent
CONFIG_FILE = _LEGACY_CONFIG_FILE
VIDEOS_DIR = DATA_DIR / "nagrania"
REVIEW_DEMOS_DIR = THEME_ROOT / "docs" / "review-demos"
GPT_STARTER_DIR = THEME_ROOT / "Pliki startowe dla GPT"
GPT_STARTER_REL_PREFIX = "Pliki startowe dla GPT"
GPT_KNOWLEDGE_PACK_VERSION = "v40"
GPT_STARTER_ZIP_NAME = "giclee_cursor_architect_knowledge_v40.zip"
MONOREPO_BRANCH = "master"
STARTER_FILES_COMMIT_MESSAGE = "docs(gpt): refresh starter files checkpoint"

# --- Push Giclee Viewer (C:\Strona\giclee-viewer → giclee-viewer na GitHub) ---
GICLEE_VIEWER_DIR = Path(r"C:\Strona\giclee-viewer")
GICLEE_VIEWER_REMOTE_URL = "https://github.com/eagleblastmusic-lgtm/giclee-viewer.git"
GICLEE_VIEWER_BRANCH = "master"
GICLEE_VIEWER_COMMIT_MESSAGE = "feat: sync Giclee Viewer workspace"

GICLEE_VIEWER_RUNTIME_DIR_NAMES: frozenset[str] = frozenset({
    ".vs",
    "bin",
    "obj",
    "TestResults",
    "packages",
    ".cache",
    "ThumbnailsCache",
    "AppData",
    "artifacts",
    ".idea",
})

GICLEE_VIEWER_RUNTIME_FILE_SUFFIXES: tuple[str, ...] = (
    ".user",
    ".suo",
    ".sln.docstates",
    ".sln.iml",
    ".cache",
    ".log",
    ".trx",
    ".coverage",
    ".coveragexml",
    ".nupkg",
)
GPT_COMPACT_INSTRUCTIONS_FILE = "GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md"
GPT_MASTER_INDEX_FILE = "GICLEE_CURSOR_MASTER_INDEX_v40.md"
GPT_CLEAN_PACK_FILE = "GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v40.md"
GPT_README_UPDATE_FILE = "README_GICLEE_CURSOR_ARCHITECT_UPDATE_v40.md"
GPT_START_MESSAGE_FILE = "Wiadomość początkowa.txt"
# Kanoniczne nazwy nagrań — Custom GPT szuka tych ścieżek w repo (handoff / manifest).
GPT_RECORDING_DESKTOP = "latest-desktop.webm"
GPT_RECORDING_MOBILE = "latest-mobile.webm"
GPT_RECORDING_DESKTOP_REL = f"docs/review-demos/{GPT_RECORDING_DESKTOP}"
GPT_RECORDING_MOBILE_REL = f"docs/review-demos/{GPT_RECORDING_MOBILE}"

# Katalogi kopiowane do repo GPT (relative do korzenia motywu).
MIRROR_INCLUDE_DIRS: tuple[str, ...] = (
    "sections",
    "blocks",
    "snippets",
    "layout",
    "templates",
    "assets",
    "config",
    "docs/motyw",
    "docs/review-demos",
)

MIRROR_INCLUDE_FILES: tuple[str, ...] = (
    "docs/README.md",
    "MATKA.md",
    "shopify.theme.toml",
)

MIRROR_SKIP_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    "node_modules",
    ".git",
})

MIRROR_SKIP_SUFFIXES: frozenset[str] = frozenset({
    ".pyc",
    ".pyo",
    ".map",
})

# Pliki większe niż ten limit pomijamy (log ostrzeżenia).
MIRROR_MAX_FILE_BYTES = 25 * 1024 * 1024

# --- Push GicleeApp (cursor-api → staging → gicleeapp na GitHub) ---
GICLEEAPP_STAGING_DIR = Path(r"C:\Strona\_gicleeapp_staging")
GICLEEAPP_REMOTE_URL = "https://github.com/eagleblastmusic-lgtm/gicleeapp.git"
GICLEEAPP_BRANCH = "main"
GICLEEAPP_COMMIT_MESSAGE = "Refresh GicleeApp repository snapshot"

GICLEEAPP_REVIEW_ONLY_FILES: tuple[str, ...] = (
    "GPT_README.md",
    "SYNC_NOTES.md",
    "REVIEW_MANIFEST.json",
    "docs/GPT_KNOWLEDGE_PACK.md",
    "docs/SHOPIFY_THEME_INTEGRATION.md",
    "docs/UI_REDESIGN_PLAN.md",
    "Komponenty/integracjagpt/data/gpt_config.example.json",
    "Komponenty/kpir/dane/kpir_settings.example.json",
)

GICLEEAPP_NEVER_OVERWRITE: frozenset[str] = frozenset(
    {".gitignore", "README.md", *GICLEEAPP_REVIEW_ONLY_FILES}
)

GICLEEAPP_SYNC_SKIP_DIR_NAMES: frozenset[str] = frozenset({
    ".git",
    ".gpt_mirror",
    "gpt_mirror",
    "node_modules",
    "build",
    "dist",
    "logs",
    ".cache",
    ".pytest_cache",
    "pytest_cache",
    ".mypy_cache",
    "__pycache__",
    ".cursor",
    ".shopify",
    "shopify",
    "coverage",
    "Pliki startowe dla GPT",
    ".vscode",
    "vscode",
})

GICLEEAPP_SYNC_SKIP_FILE_NAMES: frozenset[str] = frozenset({
    ".env",
    ".env.example",
    "env",
    "env.example",
    ".shopify_session.json",
    "shopify_session.json",
    ".gitignore",
    "gitignore",
    ".graphqlrc.js",
    "graphqlrc.js",
    ".npmrc",
    "npmrc",
    "gpt_knowledge.zip",
    "giclee_cursor_architect_knowledge.zip",
    "giclee_cursor_architect_knowledge_v37.zip",
    "giclee_cursor_architect_knowledge_v38.zip",
    "giclee_cursor_architect_knowledge_v39.zip",
    "giclee_cursor_architect_knowledge_v40.zip",
})

GICLEEAPP_SYNC_SKIP_REL_PREFIXES: tuple[str, ...] = (
    "Komponenty/stronaglowna/data/backups/",
    "Komponenty/stronaglowna/data/tmp/",
    "Komponenty/dokumentysprzedazy/documents/",
    "Komponenty/kpir/documents/",
    "Komponenty/notatnik/notatki/",
    "Komponenty/integracjagpt/data/nagrania/",
    "Komponenty/bazapromptow/data/context_images/",
    "Komponenty/bazapromptow/data/context_files/",
    "Komponenty/bazapromptow/data/context_videos/",
    "Komponenty/stronyzobrazami/data/cache/",
    "Komponenty/print_optimize/data/",
    "Komponenty/socialmedia/data/cykl/Obrazy/",
    "_czesc7_parts/",
    "_test_out/",
    "backups/",
    "/backups/",
)

GICLEEAPP_RUNTIME_DENYLIST_PREFIXES: tuple[str, ...] = (
    "Komponenty/dokumentysprzedazy/documents/",
    "Komponenty/kpir/documents/",
    "Komponenty/notatnik/notatki/",
    "Komponenty/print_optimize/data/",
    "Komponenty/stronaglowna/data/tmp/",
    "Komponenty/stronaglowna/data/backups/",
    "_czesc7_parts/",
    "_test_out/",
)

# Ścieżki runtime/cache wykluczone z commit candidates Push GicleeApp (fnmatch na rel path).
GICLEEAPP_RUNTIME_DENYLIST_GLOBS: tuple[str, ...] = (
    "Komponenty/stronaglowna/data/variants/*/index.json",
    "Komponenty/stronaglowna/data/variants/*/settings.json",
    "Komponenty/wspolpraca/data/variants/manifest.json",
    "Komponenty/wspolpraca/data/variants/*/page.wspolpraca.json",
    "Komponenty/tldobio/data/collections.json",
    "Komponenty/tldobio/data/*.jpg",
    "Komponenty/tldobio/data/*.jpeg",
    "Komponenty/tldobio/data/*.png",
    "Komponenty/tldobio/data/*.webp",
)

# Root-level scratch (fnmatch on basename only — not nested paths).
GICLEEAPP_RUNTIME_ROOT_GLOBS: tuple[str, ...] = (
    "_tmp_*",
    "_test_*",
    "_test_squoosh.jpg",
    "_build_czesc7.py",
    "czesc5*.json",
    "czesc6*.json",
    "czesc7*.json",
    "tmp_getty*.txt",
    "tmp_getty*.json",
    "tmp_getty_row.json",
)

GICLEEAPP_RUNTIME_DENYLIST: frozenset[str] = frozenset({
    ".env",
    ".env.example",
    "env",
    "env.example",
    ".shopify_session.json",
    "shopify_session.json",
    ".gitignore",
    "gitignore",
    ".graphqlrc.js",
    "graphqlrc.js",
    ".npmrc",
    "npmrc",
    "README.md",
    "Komponenty/integracjagpt/data/gpt_config.json",
    "Komponenty/integracjagpt/data/gpt_knowledge.zip",
    "Komponenty/kpir/dane/kpir_settings.json",
    "Komponenty/dokumentysprzedazy/dane/orders_sync_state.json",
    "Komponenty/produkcja/dane/sync_state.json",
    "Komponenty/produkcja/dane/zamowienia.json",
    "Komponenty/produkcja/dane/notified.json",
    "Komponenty/_shared/data/activity_log.jsonl",
    "Komponenty/_shared/data/fx_cache.json",
    "Komponenty/analytics/dane/analytics.db",
    "Komponenty/socialmedia/data/cykl/meta_credentials.json",
    "Komponenty/socialmedia/data/cykl/meta_state.json",
    "Komponenty/blog/data/articles_cache.json",
    "Komponenty/blog/data/preview.html",
    "Komponenty/zadania/data/signals_cache.json",
    "giclee_cursor_architect_knowledge.zip",
    "giclee_cursor_architect_knowledge_v37.zip",
    "giclee_cursor_architect_knowledge_v38.zip",
    "giclee_cursor_architect_knowledge_v39.zip",
    "giclee_cursor_architect_knowledge_v40.zip",
    "gpt_knowledge.zip",
})

GICLEEAPP_THEME_PATH_PREFIXES: tuple[str, ...] = (
    "sections/",
    "snippets/",
    "layout/",
    "templates/",
    "assets/",
    "blocks/",
    "config/",
)

# --- Push GicleeArt-GPT (motyw → .gpt_mirror → gicleeart-gpt na GitHub) ---
GICLEEART_GPT_REMOTE_URL = "https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git"
GICLEEART_GPT_FALLBACK_COMMIT_DESC = "Refresh GicleeArt-GPT theme snapshot"

MIRROR_RUNTIME_DENYLIST: frozenset[str] = frozenset({
    ".env",
    ".env.example",
    ".shopify_session.json",
    "cursor-api/",
})

MIRROR_PROTECTED_DELETIONS: frozenset[str] = frozenset({
    "GPT_README.md",
    "SYNC_NOTES.md",
    "REVIEW_MANIFEST.json",
})


@dataclass
class GptConfig:
    remote_url: str = ""
    branch: str = "main"
    commit_prefix: str = "GPT sync"
    prefer_local_theme_dev: bool = True
    record_scroll_seconds: float = 55.0
    record_wait_hero_seconds: float = 4.0
    last_push_sha: str = ""
    last_push_at: str = ""
    knowledge_zip_name: str = ""
    knowledge_zip_loaded_at: str = ""
    obs_executable: str = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
    obs_websocket_host: str = "127.0.0.1"
    obs_websocket_port: int = 0
    obs_websocket_password: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> GptConfig:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict:
        return asdict(self)


def default_config() -> GptConfig:
    return GptConfig(
        remote_url="https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git",
    )


def _config_read_path() -> Path:
    if Path(CONFIG_FILE) != _LEGACY_CONFIG_FILE:
        return Path(CONFIG_FILE)
    return _CONFIG.read_path()


def _config_write_path() -> Path:
    if Path(CONFIG_FILE) != _LEGACY_CONFIG_FILE:
        return Path(CONFIG_FILE)
    return _CONFIG.write_path


def load_config() -> GptConfig:
    path = _config_read_path()
    if not path.is_file():
        cfg = default_config()
        save_config(cfg)
        return cfg
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return default_config()
    return GptConfig.from_dict(raw)


def save_config(cfg: GptConfig) -> None:
    atomic_write_text(
        _config_write_path(),
        json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2) + "\n",
    )
