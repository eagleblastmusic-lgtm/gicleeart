"""ZIP wiedzy Custom GPT — lokalna kopia + schowek plików (Windows)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from .config import (
    DATA_DIR,
    GPT_COMPACT_INSTRUCTIONS_FILE,
    GPT_STARTER_DIR,
    GPT_STARTER_ZIP_NAME,
    GPT_START_MESSAGE_FILE,
)

KNOWLEDGE_ZIP_BASENAME = "gpt_knowledge.zip"
# Alias kompatybilnościowy — lokalny runtime ZIP w DATA_DIR (testy / starsze importy).
KNOWLEDGE_ZIP_FILE = DATA_DIR / KNOWLEDGE_ZIP_BASENAME

# Zgodne z «Pliki startowe dla GPT/GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md».
CLEAN_PACK_V37_ACTIVE_FILES: tuple[str, ...] = (
    "CURRENT_APP_STATE.md",
    "GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md",
    GPT_COMPACT_INSTRUCTIONS_FILE,
    "GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md",
    "GICLEE_CURSOR_MASTER_INDEX_v37.md",
    "README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md",
    "GICLEE_AWWWARDS_MOTION_SYSTEM_v3.md",
    "GICLEE_BAD_EFFECTS_BLACKLIST_v31.md",
    "GICLEE_CODE_PLUS_PROMPT_WORKFLOW_v3.md",
    "GICLEE_CURSOR_EXAMPLES_v31.md",
    "GICLEE_EFFECT_LIBRARY_v31.md",
    "GICLEE_IMPLEMENTATION_PATTERNS_v31.md",
    "GICLEE_MOTION_QUALITY_RUBRIC_v31.md",
    "GICLEE_MOTION_REVIEW_LOOP_v33.md",
    "GICLEE_PROMPT_RESPONSE_MODES_v3.md",
    "GICLEE_RESEARCH_DRIVEN_EFFECTS_v3.md",
    "GICLEE_SECTION_PLAYBOOK_v32.md",
    "GICLEE_SIGNATURE_MOMENTS_v33.md",
    "GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md",
    "GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md",
    "GICLEE_ANALYST_BASE_PROMPT_v1.md",
    "GICLEE_ANALYST_MODE_PERFORMANCE_v1.md",
    "GICLEE_ANALYST_MODE_DEBUG_REGRESSION_v1.md",
    "GICLEE_ANALYST_MODE_CURSOR_REVIEW_v1.md",
    "GICLEE_ANALYST_MODE_STAGE_ARCHITECT_v1.md",
    "GICLEE_ANALYST_MODE_UI_UX_PREMIUM_v1.md",
    "GICLEE_ANALYST_MODE_SHOPIFY_SNAPSHOT_v1.md",
    "GICLEE_ANALYST_MODE_GPT_ZIP_INTEGRATION_v1.md",
    "GICLEE_SHOPIFY_MODE_HOMEPAGE_ART_DIRECTION_v1.md",
    "GICLEE_SHOPIFY_MODE_PRODUCT_PAGE_PDP_v1.md",
    "GICLEE_SHOPIFY_MODE_COLLECTION_CATALOG_v1.md",
    "GICLEE_SHOPIFY_MODE_COPY_BRAND_STORY_v1.md",
    "GICLEE_SHOPIFY_MODE_MOTION_INTERACTION_v1.md",
    "GICLEE_SHOPIFY_MODE_CONVERSION_TRUST_v1.md",
    "GICLEE_SHOPIFY_MODE_RESPONSIVE_ACCESSIBILITY_v1.md",
    "GICLEE_SHOPIFY_MODE_SEO_CONTENT_v1.md",
    "GICLEE_SHOPIFY_MODE_TRANSLATION_MARKETS_v1.md",
)


def _knowledge_zip_file() -> Path:
    return DATA_DIR / KNOWLEDGE_ZIP_BASENAME


def knowledge_zip_path() -> Path | None:
    path = _knowledge_zip_file()
    if path.is_file() and path.stat().st_size > 0:
        return path
    return None


def gpt_starter_files_dir() -> Path:
    return GPT_STARTER_DIR


def list_starter_markdown_files(folder: Path | None = None) -> list[Path]:
    """Pliki z manifestu CLEAN_PACK v37 (bez archiwalnych wersji na dysku)."""
    root = (folder or gpt_starter_files_dir()).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Brak folderu z plikami startowymi GPT: {root}")

    files: list[Path] = []
    missing: list[str] = []
    for name in CLEAN_PACK_V37_ACTIVE_FILES:
        path = root / name
        if path.is_file():
            files.append(path)
        else:
            missing.append(name)

    if missing:
        raise FileNotFoundError(
            f"Brak plików CLEAN_PACK v37 w {root}: {', '.join(missing)}"
        )
    return files


def build_starter_knowledge_zip(folder: Path | None = None) -> Path:
    """Tworzy giclee_cursor_architect_knowledge_v37.zip wg manifestu CLEAN_PACK v37."""
    root = (folder or gpt_starter_files_dir()).resolve()
    md_files = list_starter_markdown_files(root)
    zip_path = root / GPT_STARTER_ZIP_NAME

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for md in md_files:
            zf.write(md, arcname=md.name)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(zip_path, _knowledge_zip_file())
    return zip_path


def read_compact_instructions(folder: Path | None = None) -> str:
    """Treść GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md (główne instrukcje w ZIP-ie)."""
    root = (folder or gpt_starter_files_dir()).resolve()
    path = root / GPT_COMPACT_INSTRUCTIONS_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Plik jest pusty: {path}")
    return text


def read_start_message(folder: Path | None = None) -> str:
    root = (folder or gpt_starter_files_dir()).resolve()
    path = root / GPT_START_MESSAGE_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Plik jest pusty: {path}")
    return text


def read_start_message_draft(folder: Path | None = None) -> str:
    """Pełna treść pliku do edycji w GUI (bez strip)."""
    root = (folder or gpt_starter_files_dir()).resolve()
    path = root / GPT_START_MESSAGE_FILE
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def write_start_message(text: str, folder: Path | None = None) -> Path:
    """Zapisuje «Wiadomość początkowa.txt» w folderze plików startowych GPT."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Wiadomość początkowa nie może być pusta.")
    root = (folder or gpt_starter_files_dir()).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Brak folderu z plikami startowymi GPT: {root}")
    path = root / GPT_START_MESSAGE_FILE
    path.write_text(cleaned, encoding="utf-8")
    return path


def import_knowledge_zip(source: Path) -> tuple[str, str]:
    """Kopiuje ZIP do data/gpt_knowledge.zip. Zwraca (oryginalna_nazwa, loaded_at ISO)."""
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Brak pliku: {source}")
    if source.suffix.lower() != ".zip":
        raise ValueError("Wybierz plik .zip")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, _knowledge_zip_file())
    loaded_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return source.name, loaded_at


def copy_zip_path_to_clipboard(path: Path) -> None:
    """Schowek plików Windows (do wklejenia ZIP w ChatGPT)."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku: {path}")

    if sys.platform != "win32":
        raise OSError("Kopiowanie pliku do schowka działa tylko na Windows.")

    ps_path = str(path).replace("'", "''")
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Set-Clipboard -Path '{ps_path}'",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"Nie udało się skopiować ZIP do schowka: {err or proc.returncode}")


def copy_knowledge_zip_to_clipboard() -> None:
    """Schowek plików Windows (do wklejenia ZIP w ChatGPT)."""
    path = knowledge_zip_path()
    if path is None:
        raise FileNotFoundError("Brak załadowanego ZIP — użyj «Załaduj zip do rozmowy».")
    copy_zip_path_to_clipboard(path)
