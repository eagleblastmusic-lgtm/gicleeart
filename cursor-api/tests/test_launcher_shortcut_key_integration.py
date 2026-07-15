"""Integracja neutralnego kontraktu klawiszy z modułami launchera."""

from __future__ import annotations

from giclee_app import launcher_shortcut_keys as keys
from giclee_app import launcher_shortcuts as config
from giclee_app import launcher_windows_shortcuts as windows
from giclee_app.launcher_shortcut_controller import (
    ShortcutActivationKind,
    resolve_shortcut_activation,
    resolve_shortcut_poll,
)


def test_configuration_and_windows_adapter_reexport_shared_contract() -> None:
    assert config.normalize_shortcut_key is keys.normalize_shortcut_key
    assert windows.shortcut_virtual_key is keys.shortcut_virtual_key


def test_poll_filters_invalid_keys_from_current_and_previous_state() -> None:
    decision = resolve_shortcut_poll(
        [" A ", "F2", "ą", "٧", "f١", "invalid"],
        ["a", "ą", "٧"],
        active=True,
        modifiers_down=False,
    )

    assert decision.pressed_keys == ("f2",)
    assert decision.next_down == frozenset({"a", "f2"})


def test_invalid_activation_key_is_unmapped_before_mapping_lookup() -> None:
    decision = resolve_shortcut_activation(
        {"": "should-never-launch", "ą": "unicode-component"},
        "ą",
        component_exists=True,
        launch_pending=False,
    )

    assert decision.kind is ShortcutActivationKind.UNMAPPED
    assert decision.handled is False
    assert decision.key == ""
    assert decision.folder_name is None


def test_supported_activation_still_uses_canonical_key() -> None:
    decision = resolve_shortcut_activation(
        {"f2": "faq"},
        " F02 ",
        component_exists=True,
        launch_pending=False,
    )

    assert decision.kind is ShortcutActivationKind.READY
    assert decision.key == "f2"
    assert decision.folder_name == "faq"
