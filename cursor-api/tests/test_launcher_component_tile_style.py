from __future__ import annotations

from pathlib import Path

from giclee_app.component_loader import Component
from giclee_app.styled_category_launcher import (
    component_action_label,
    component_display_icon,
    component_mode_label,
)


def test_component_mode_labels_match_launch_destination() -> None:
    assert component_mode_label("inline") == "W aplikacji"
    assert component_mode_label("url") == "WWW"
    assert component_mode_label("subprocess") == "Nowe okno"
    assert component_mode_label("unknown") == "Komponent"


def test_component_action_labels_match_mode() -> None:
    assert component_action_label("inline") == "Otwórz komponent  →"
    assert component_action_label("url") == "Otwórz stronę  →"
    assert component_action_label("subprocess") == "Uruchom  →"
    assert component_action_label("unknown") == "Otwórz  →"


def test_component_icon_uses_manifest_icon() -> None:
    component = Component(
        folder_name="example",
        package_path=Path("example"),
        name="Example",
        description="",
        icon="🧭",
    )
    assert component_display_icon(component) == "🧭"


def test_component_icon_has_neutral_fallback() -> None:
    component = Component(
        folder_name="example",
        package_path=Path("example"),
        name="Example",
        description="",
        icon="",
    )
    assert component_display_icon(component) == "◆"
