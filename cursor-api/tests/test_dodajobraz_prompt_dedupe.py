"""Test deduplikacji pozycji w prompcie LLM (preview + Full = jedno dzielo)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _q(path: str, **kw) -> dict:
    return {"path": Path(path), **kw}


class TestDedupePrompt:
    def test_preview_and_full_one_entry(self) -> None:
        from Komponenty.dodajobraz.parser import IMAGE_ROLE_FULL, IMAGE_ROLE_PREVIEW
        from Komponenty.dodajobraz.prompt_builder import (
            canonical_product_filename,
            dedupe_items_for_prompt,
            lookup_llm_entry,
        )

        items = [
            _q(
                "Pieter Bruegel (starszy) - Massacre of the Innocents - (preview).webp",
                artist="Pieter Bruegel (starszy)",
                base_title="Massacre of the Innocents",
                title="Massacre of the Innocents",
                image_role=IMAGE_ROLE_PREVIEW,
                follow_up_number=None,
                title_is_polish=False,
            ),
            _q(
                "Pieter Bruegel (starszy) - Massacre of the Innocents - Full.webp",
                artist="Pieter Bruegel (starszy)",
                base_title="Massacre of the Innocents",
                title="Massacre of the Innocents",
                image_role=IMAGE_ROLE_FULL,
                follow_up_number=None,
                title_is_polish=False,
            ),
        ]
        out = dedupe_items_for_prompt(items)
        assert len(out) == 1
        assert out[0]["filename"] == (
            "Pieter Bruegel (starszy) - Massacre of the Innocents.webp"
        )
        canon = canonical_product_filename(
            "Pieter Bruegel (starszy)", "Massacre of the Innocents", suffix=".webp"
        )
        llm_map = {canon: {"plik": canon, "tytul_polski": "x"}}
        assert lookup_llm_entry(items[1], llm_map) is not None
