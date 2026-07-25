from __future__ import annotations

import inspect

from Komponenty._shared.theme_page_editor import gui_shell
from Komponenty._shared.theme_page_editor.image_object_x import (
    build_object_x_controls,
    normalize_object_x,
    object_x_path,
    supports_object_x,
)
from Komponenty._shared.theme_page_editor.image_object_y import build_object_y_controls


def test_build_field_widget_documents_row_return() -> None:
    source = inspect.getsource(gui_shell)
    assert "def _build_field_widget" in source
    assert "Zwraca indeks następnego wolnego wiersza" in source
    assert "row = _build_field_widget(zone, fld, row)" in source
    # Stary bug: stałe +2 kolidowało z wierszem kadrowania
    assert "row += 2" not in source
    assert "build_object_x_controls" in source


def test_object_y_controls_use_stacked_layout() -> None:
    source = inspect.getsource(build_object_y_controls)
    assert "Kadrowanie góra–dół" in source
    assert 'width=18' not in source


def test_object_x_only_for_faq_accordion_artwork() -> None:
    assert supports_object_x("heading_background_image")
    assert supports_object_x("answer_background_image")
    assert not supports_object_x("image_1")
    assert object_x_path(("sections", "x", "settings", "heading_background_image")) == (
        "sections",
        "x",
        "settings",
        "heading_background_image_object_x",
    )
    assert object_x_path(("sections", "x", "settings", "image_1")) is None
    assert normalize_object_x(None) == 72
    assert normalize_object_x(-50) == -50
    assert normalize_object_x(-80) == -50
    assert normalize_object_x(150) == 150
    assert normalize_object_x(200) == 150
    source = inspect.getsource(build_object_x_controls)
    assert "Kadrowanie lewo–prawo" in source
