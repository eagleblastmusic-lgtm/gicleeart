"""Rejestracja fontów TTF z obsługą polskich znaków (reportlab)."""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_COMPONENT_DIR = Path(__file__).resolve().parent
_FONT_REG = "InvoiceRegular"
_FONT_BOLD = "InvoiceBold"
_registered = False


def _candidate_pairs() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    local = _COMPONENT_DIR / "fonts"
    pairs.append((local / "DejaVuSans.ttf", local / "DejaVuSans-Bold.ttf"))
    pairs.append((local / "arial.ttf", local / "arialbd.ttf"))

    if sys.platform.startswith("win"):
        win = Path(r"C:\Windows\Fonts")
        pairs.append((win / "arial.ttf", win / "arialbd.ttf"))
        pairs.append((win / "calibri.ttf", win / "calibrib.ttf"))
    elif sys.platform == "darwin":
        mac = Path("/Library/Fonts")
        pairs.append((mac / "Arial.ttf", mac / "Arial Bold.ttf"))
        pairs.append((mac / "Arial Unicode.ttf", mac / "Arial Unicode.ttf"))
    else:
        for base in (
            Path("/usr/share/fonts/truetype/dejavu"),
            Path("/usr/share/fonts/TTF"),
            Path("/usr/share/fonts/dejavu"),
        ):
            pairs.append((base / "DejaVuSans.ttf", base / "DejaVuSans-Bold.ttf"))

    return pairs


def register_invoice_fonts() -> tuple[str, str]:
    global _registered
    if _registered:
        return _FONT_REG, _FONT_BOLD

    for regular, bold in _candidate_pairs():
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont(_FONT_REG, str(regular)))
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(bold)))
            _registered = True
            return _FONT_REG, _FONT_BOLD

    raise RuntimeError(
        "Brak fontu TTF z polskimi znakami. "
        "Dodaj DejaVuSans.ttf i DejaVuSans-Bold.ttf do Komponenty/dokumentysprzedazy/fonts/ "
        "lub zainstaluj Arial/DejaVu w systemie."
    )
