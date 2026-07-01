"""Synchronizuje title_update_marks.json z product_id w scripts/fix_*_titles.py."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz.description_update import (
    load_title_update_marks,
    save_title_update_marks,
)

_SCRIPTS = ROOT / "scripts"
_ID_RE = re.compile(
    r'(?:PRODUCT_ID\s*=\s*|["\']product_id["\']\s*:\s*)(\d+)',
)


def collect_ids_from_fix_scripts() -> set[int]:
    out: set[int] = set()
    for path in sorted(_SCRIPTS.glob("fix_*_titles.py")):
        text = path.read_text(encoding="utf-8")
        for m in _ID_RE.finditer(text):
            out.add(int(m.group(1)))
    return out


def main() -> int:
    from_scripts = collect_ids_from_fix_scripts()
    existing = load_title_update_marks()
    merged = existing | from_scripts
    save_title_update_marks(merged)
    added = len(merged) - len(existing)
    print(f"Skrypty fix_*_titles.py: {len(from_scripts)} id")
    print(f"Bylo w marks: {len(existing)}, teraz: {len(merged)} (+{added} nowych)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
