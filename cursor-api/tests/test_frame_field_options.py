"""Listy wariantow ramki z szablonu (jak Shopify)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty.dodajobraz.templates import VariantTemplate  # noqa: E402
from Komponenty.produkcja.frame_variant import (  # noqa: E402
    combobox_values_with_current,
    frame_field_options_from_template,
)


def test_frame_options_from_giclee_like_template() -> None:
    t = VariantTemplate.new(
        name="x",
        options=[
            {
                "name": "Kolor",
                "values": ["Czarny", "Brąz"],
                "position": 1,
            },
            {
                "name": "Rozmiar",
                "values": ["M", "L"],
                "position": 2,
            },
            {
                "name": "Rodzaj drewna",
                "values": ["Sosna", "Dąb"],
                "position": 3,
            },
        ],
        variants=[],
    )
    fo = frame_field_options_from_template(t)
    assert fo.kolor_values == ("Czarny", "Brąz")
    assert fo.rozmiar_values == ("M", "L")
    assert fo.drewno_values == ("Sosna", "Dąb")
    assert "Kolor" in fo.label_kolor


def test_combobox_values_with_current_prepends_unknown() -> None:
    assert combobox_values_with_current(("A", "B"), "Z") == ("Z", "A", "B")
    assert combobox_values_with_current(("A", "B"), "A") == ("A", "B")

