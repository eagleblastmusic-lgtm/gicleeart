"""Testy walidacji pary preview+Full w kolejce dodajobraz."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _item(artist: str, title: str, *, role: str | None = None, fnum: int | None = None) -> dict:
    return {
        "artist": artist,
        "base_title": title,
        "image_role": role,
        "follow_up_number": fnum,
    }


class TestQueueAudit:
    def test_complete_pair(self) -> None:
        from Komponenty.dodajobraz.queue_audit import audit_preview_full_pairs

        items = [
            _item("Monet", "Lilie", role="preview"),
            _item("Monet", "Lilie", role="full"),
        ]
        assert audit_preview_full_pairs(items) == []

    def test_missing_full(self) -> None:
        from Komponenty.dodajobraz.queue_audit import audit_preview_full_pairs

        miss = audit_preview_full_pairs([_item("Monet", "Lilie", role="preview")])
        assert len(miss) == 1
        assert "Full" in miss[0]

    def test_f2_only_skipped(self) -> None:
        from Komponenty.dodajobraz.queue_audit import audit_preview_full_pairs

        items = [_item("Monet", "Lilie", fnum=2)]
        assert audit_preview_full_pairs(items) == []
