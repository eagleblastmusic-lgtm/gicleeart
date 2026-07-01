"""Domyslne sciezki danych komponentu."""

from __future__ import annotations

from pathlib import Path

COMPONENT_DIR = Path(__file__).resolve().parent
DATA_DIR = COMPONENT_DIR / "data"
TEST_PHOTOS_DIR = DATA_DIR / "test_photos"
WW_PAIRS_DIR = DATA_DIR / "ww_pairs"


def ensure_data_dirs() -> None:
    TEST_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    WW_PAIRS_DIR.mkdir(parents=True, exist_ok=True)
