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
from giclee_app.options_category_launcher import (
    OptionsCategoryGicleeApp,
    shortcut_virtual_key,
)


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


def test_windows_virtual_key_mapping() -> None:
    assert shortcut_virtual_key("n") == ord("N")
    assert shortcut_virtual_key("7") == ord("7")
    assert shortcut_virtual_key("f1") == 0x70
    assert shortcut_virtual_key("F12") == 0x7B
    assert shortcut_virtual_key("f13") is None
    assert shortcut_virtual_key("ctrl+n") is None


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


def test_shortcut_binding_uses_bindtag_and_direct_fallback_without_duplicates() -> None:
    class FakeWidget:
        def __init__(self, tags: tuple[str, ...], children: list["FakeWidget"] | None = None) -> None:
            self._tags = tags
            self._children = children or []
            self.direct_bindings: list[tuple[str, object, str]] = []

        def bindtags(self, tags: tuple[str, ...] | None = None) -> tuple[str, ...]:
            if tags is not None:
                self._tags = tuple(tags)
            return self._tags

        def winfo_children(self) -> list["FakeWidget"]:
            return list(self._children)

        def bind(self, sequence: str, callback: object, add: str = "") -> str:
            self.direct_bindings.append((sequence, callback, add))
            return f"direct-{len(self.direct_bindings)}"

    class FakeRoot(FakeWidget):
        def __init__(self) -> None:
            self.child = FakeWidget(("child", "TFrame", ".", "all"))
            super().__init__(("root", "Tk", "all"), [self.child])
            self.bound_classes: list[tuple[str, str, object]] = []
            self.unbound_classes: list[tuple[str, str]] = []

        def bind_class(self, tag: str, sequence: str, callback: object) -> None:
            self.bound_classes.append((tag, sequence, callback))

        def unbind_class(self, tag: str, sequence: str) -> None:
            self.unbound_classes.append((tag, sequence))

    app = OptionsCategoryGicleeApp.__new__(OptionsCategoryGicleeApp)
    app.root = FakeRoot()
    app._shortcut_bindtag = "GicleeLauncherShortcuts_test"
    app._windows_user32 = None

    app._bind_launcher_shortcuts()

    assert app.root.unbound_classes == [
        ("GicleeLauncherShortcuts_test", "<KeyPress>")
    ]
    assert app.root.bound_classes[0][0:2] == (
        "GicleeLauncherShortcuts_test",
        "<KeyPress>",
    )
    assert app.root.bindtags()[0] == "GicleeLauncherShortcuts_test"
    assert app.root.child.bindtags()[0] == "GicleeLauncherShortcuts_test"
    assert app.root.direct_bindings[0][0::2] == ("<KeyPress>", "+")
    assert app.root.child.direct_bindings[0][0::2] == ("<KeyPress>", "+")

    app._bind_launcher_shortcuts()

    assert len(app.root.bound_classes) == 2
    assert len(app.root.unbound_classes) == 2
    assert app.root.bindtags().count("GicleeLauncherShortcuts_test") == 1
    assert app.root.child.bindtags().count("GicleeLauncherShortcuts_test") == 1
    assert len(app.root.direct_bindings) == 1
    assert len(app.root.child.direct_bindings) == 1
