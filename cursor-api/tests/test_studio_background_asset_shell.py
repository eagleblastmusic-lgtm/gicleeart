"""Testy read-only asset browser shell (F5.1)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_asset_shell import asset_library_rows, asset_library_section
from giclee_app.studio.background_asset_types import asset_type_labels_pl
from giclee_app.studio.background_capabilities import capability_for
from giclee_app.ui.background_panel import panel_rows

_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"
_MODULE_PATHS = (
    _ROOT / "background_asset_types.py",
    _ROOT / "background_asset_shell.py",
)


def test_stronaglowna_has_asset_library_section() -> None:
    section = asset_library_section("stronaglowna")
    assert section is not None
    assert section.title == "Biblioteka / Assety"
    assert "F5.1 to shell read-only" in section.body
    assert "Wybór assetu będzie dostępny w kolejnych fazach" in section.body


def test_stronaglowna_asset_types_present() -> None:
    rows = asset_library_rows("stronaglowna")
    assert len(rows) == 1
    body = rows[0][1]
    for label in asset_type_labels_pl():
        assert label in body
    assert "obraz" in body
    assert "wideo" in body
    assert "kolaż wideo" in body


def test_stronaglowna_section_zones_in_shell() -> None:
    body = asset_library_rows("stronaglowna")[0][1]
    assert "ga_background" in body
    assert "sd_background" in body
    assert "Strefy section_background (5):" in body


def test_tldobio_no_asset_library_section() -> None:
    assert asset_library_section("tldobio") is None
    assert asset_library_rows("tldobio") == ()


def test_panel_rows_stronaglowna_includes_biblioteka(tmp_path: Path) -> None:
    cap = capability_for("stronaglowna")
    assert cap is not None
    rows = dict(
        panel_rows(
            cap,
            component_name="Strona główna",
            folder_name="stronaglowna",
            package_path=tmp_path,
        )
    )
    assert "Biblioteka / Assety" in rows
    assert "kolaż wideo" in rows["Biblioteka / Assety"]


def test_panel_rows_tldobio_no_biblioteka(tmp_path: Path) -> None:
    cap = capability_for("tldobio")
    assert cap is not None
    rows = dict(
        panel_rows(
            cap,
            component_name="Tło do Bio",
            folder_name="tldobio",
            package_path=tmp_path,
        )
    )
    assert "Biblioteka / Assety" not in rows


def test_no_komponenty_imports() -> None:
    for path in _MODULE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("Komponenty")
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("Komponenty")


def test_no_write_text_or_glob() -> None:
    for path in _MODULE_PATHS:
        text = path.read_text(encoding="utf-8")
        assert "write_text" not in text
        assert "write_bytes" not in text
        assert "glob(" not in text
        assert "rglob(" not in text
        assert "read_text" not in text
