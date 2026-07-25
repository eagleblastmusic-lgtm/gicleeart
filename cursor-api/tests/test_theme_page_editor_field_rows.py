from __future__ import annotations

import inspect

from Komponenty._shared.theme_page_editor import gui_shell
from Komponenty._shared.theme_page_editor.image_object_y import build_object_y_controls


def test_build_field_widget_documents_row_return() -> None:
    source = inspect.getsource(gui_shell)
    assert "def _build_field_widget" in source
    assert "Zwraca indeks następnego wolnego wiersza" in source
    assert "row = _build_field_widget(zone, fld, row)" in source
    # Stary bug: stałe +2 kolidowało z wierszem kadrowania
    assert "row += 2" not in source


def test_object_y_controls_use_stacked_layout() -> None:
    source = inspect.getsource(build_object_y_controls)
    assert "Kadrowanie góra–dół" in source
    assert 'width=18' not in source
