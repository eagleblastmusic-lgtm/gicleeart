"""Test generatora kafelkow zoom."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestZoomTiles:
    def test_generate_small_grid(self, tmp_path: Path) -> None:
        from PIL import Image  # type: ignore

        from Komponenty.dodajobraz.zoom_tiles import TILE_SIZE, generate_zoom_package

        src = tmp_path / "test.webp"
        Image.new("RGB", (TILE_SIZE + 100, TILE_SIZE + 50), color=(40, 80, 120)).save(
            src, format="WEBP"
        )
        pkg = generate_zoom_package(src)
        try:
            assert pkg.manifest["cols"] == 2
            assert pkg.manifest["rows"] == 2
            assert len(pkg.upload_items) == 1 + 4  # overview + 4 tiles
            assert (pkg.root / "overview.webp").is_file()
        finally:
            pkg.cleanup()
