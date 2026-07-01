"""Konwersja WEBP/HEIC/PNG → JPG dla importu w Lightroom Classic (addPhoto)."""
from __future__ import annotations

import sys

from PIL import Image


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: convert_for_lr.py <source> <dest.jpg>", file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    with Image.open(src) as img:
        img.convert("RGB").save(dst, quality=95)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
