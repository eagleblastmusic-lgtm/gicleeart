from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from giclee_app.launcher_shortcuts import (
    DEFAULT_LAUNCHER_SHORTCUTS,
    assign_component_shortcut,
    load_launcher_shortcuts,
    normalize_shortcut_key,
    remove_component_shortcut,
    save_launcher_shortcuts,
    shortcut_display_label,
    shortcut_for_component,
    shortcut_key_from_event,
)
from giclee_app.options_category_launcher import OptionsCategoryGicleeApp


def test_normalize_shortcut_key_accepts_direct_keys() -> None:
    assert normalize_shortcut_key("A") == "a"
    assert normalize_shortcut_key("7") == "7"
    assert normalize_shortcut_key("F12") == "f12"
    assert normalize_shortcut_key("F13") is None
    assert normalize_shortcut_key("Ctrl+A") is None


def test_shortcut_key_from_event_reads_letters_and_function_keys() -> None:
    assert shortcut_key_from_event(SimpleNamespace(char="N", keysym="n")) == "n"
    assert shortcut_key_from_event(SimpleNamespace(char="", keysym="F7")) == "f7"
    assert shortcut_key_from_event(SimpleNamespace(char=" ", keysym="space")) is None


def test_missing_file_uses_default_shortcut(tmp_path: Path) -> None:
    loaded = load_launcher_shortcuts(tmp_path / "missing.json")
    assert loaded == DEFAULT_LAUNCHER_SHORTCUTS


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "shortcuts.json"
    expected = {"n": "notatnik", "f4": "faq"}
    save_launcher_shortcuts(expected, path)
    assert load_launcher_shortcuts(path) == expected


def test_empty_saved_mapping_stays_empty(tmp_path: Path) -> None:
    path = tmp_path / "shortcuts.json"
    save_launcher_shortcuts({}, path)
    assert load_launcher_shortcuts(path) == {}


def test_assign_replaces_key_and_previous_component_binding() -> None:
    current = {"i": "integracjagpt", "n": "notatnik"}
    updated = assign_component_shortcut(current, "i", "notatnik")
    assert updated == {"i": "notatnik"}


def test_remove_and_lookup_component_shortcut() -> None:
    current = {"i": "integracjagpt", "n": "notatnik"}
    assert shortcut_for_component(current, "notatnik") == "n"
    assert remove_component_shortcut(current, "notatnik") == {"i": "integracjagpt"}


def test_shortcut_display_label_is_uppercase() -> None:
    assert shortcut_display_label("a") == "A"
    assert shortcut_display_label("f9") == "F9"


def test_shortcut_binding_is_replaced_instead_of_duplicated() -> None:
    class FakeRoot:
        def __init__(self) -> None:
            self.bound: list[tuple[str, object, str]] = []
            self.unbound: list[tuple[str, str]] = []

        def bind(self, sequence: str, callback: object, add: str = "") -> str:
            self.bound.append((sequence, callback, add))
            return f"bind-{len(self.bound)}"

        def unbind(self, sequence: str, funcid: str) -> None:
            self.unbound.append((sequence, funcid))

    app = OptionsCategoryGicleeApp.__new__(OptionsCategoryGicleeApp)
    app.root = FakeRoot()
    app._shortcut_bind_id = None

    app._bind_launcher_shortcuts()
    assert app._shortcut_bind_id == "bind-1"
    assert app.root.bound[0][0] == "<KeyPress>"
    assert app.root.bound[0][2] == "+"

    app._bind_launcher_shortcuts()
    assert app._shortcut_bind_id == "bind-2"
    assert app.root.unbound == [("<KeyPress>", "bind-1")]
