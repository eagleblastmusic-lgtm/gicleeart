# -*- coding: utf-8 -*-
"""Build complete czesc7 JSON (objects 25-28). Run: python _build_czesc7.py"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "czesc7_van_gogh_25-28.json"
PARTS = Path(__file__).parent / "_czesc7_parts"

def main():
    parts = []
    for name in ("01.json", "02.json", "03.json", "04.json"):
        p = PARTS / name
        if not p.exists():
            raise SystemExit(f"Missing {p}")
        parts.append(json.loads(p.read_text(encoding="utf-8")))
    OUT.write_text(
        json.dumps(parts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(parts)} objects to {OUT}")

if __name__ == "__main__":
    main()
