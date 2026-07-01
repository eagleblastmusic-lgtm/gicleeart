"""Test walidacji strefy drag-and-drop (preview / Full / pozostale)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestRoleMismatchMessage:
    def test_preview_zone_accepts_preview_file(self) -> None:
        from Komponenty.dodajobraz.gui import App
        from Komponenty.dodajobraz.parser import IMAGE_ROLE_PREVIEW

        p = Path("Pieter Bruegel (starszy) - The Harvesters - (preview).webp")
        assert App._role_mismatch_message(None, p, IMAGE_ROLE_PREVIEW, IMAGE_ROLE_PREVIEW) == ""

    def test_preview_zone_rejects_full(self) -> None:
        from Komponenty.dodajobraz.gui import App
        from Komponenty.dodajobraz.parser import IMAGE_ROLE_FULL, IMAGE_ROLE_PREVIEW

        p = Path("Artysta - Tytul - Full.webp")
        msg = App._role_mismatch_message(None, p, IMAGE_ROLE_PREVIEW, IMAGE_ROLE_FULL)
        assert msg and "preview" in msg.lower()
