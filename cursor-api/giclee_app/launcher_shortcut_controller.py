"""Czyste decyzje pollingu i aktywacji skrótów launchera."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

from .launcher_shortcut_keys import normalize_shortcut_key


class ShortcutActivationKind(str, Enum):
    """Wynik próby uruchomienia skrótu bez efektów ubocznych."""

    UNMAPPED = "unmapped"
    MISSING_COMPONENT = "missing_component"
    LAUNCH_PENDING = "launch_pending"
    READY = "ready"


@dataclass(frozen=True)
class ShortcutPollDecision:
    """Nowe naciśnięcia oraz stan do zapamiętania po próbce."""

    pressed_keys: tuple[str, ...]
    next_down: frozenset[str]


@dataclass(frozen=True)
class ShortcutActivation:
    """Czysta decyzja aktywacji jednego znormalizowanego klawisza."""

    kind: ShortcutActivationKind
    key: str
    folder_name: str | None = None

    @property
    def handled(self) -> bool:
        return self.kind is not ShortcutActivationKind.UNMAPPED


def _normalize_keys(values: Iterable[str]) -> frozenset[str]:
    normalized: set[str] = set()
    for value in values:
        key = normalize_shortcut_key(value)
        if key is not None:
            normalized.add(key)
    return frozenset(normalized)


def resolve_shortcut_poll(
    current_down: Iterable[str],
    previous_down: Iterable[str],
    *,
    active: bool,
    modifiers_down: bool,
) -> ShortcutPollDecision:
    """Rozstrzyga zbocze klawiszy i zawsze zwraca aktualny stan próbki."""

    current = _normalize_keys(current_down)
    previous = _normalize_keys(previous_down)
    pressed: tuple[str, ...] = ()
    if active and not modifiers_down:
        pressed = tuple(sorted(current - previous))
    return ShortcutPollDecision(
        pressed_keys=pressed,
        next_down=current,
    )


def resolve_shortcut_activation(
    shortcuts: Mapping[str, str],
    key: str,
    *,
    component_exists: bool,
    launch_pending: bool,
) -> ShortcutActivation:
    """Rozstrzyga mapowanie, brak komponentu, pending albo gotowość launchu."""

    normalized_key = normalize_shortcut_key(key)
    if normalized_key is None:
        return ShortcutActivation(
            kind=ShortcutActivationKind.UNMAPPED,
            key="",
        )

    folder = str(shortcuts.get(normalized_key) or "").strip()
    if not folder:
        return ShortcutActivation(
            kind=ShortcutActivationKind.UNMAPPED,
            key=normalized_key,
        )
    if not component_exists:
        return ShortcutActivation(
            kind=ShortcutActivationKind.MISSING_COMPONENT,
            key=normalized_key,
            folder_name=folder,
        )
    if launch_pending:
        return ShortcutActivation(
            kind=ShortcutActivationKind.LAUNCH_PENDING,
            key=normalized_key,
            folder_name=folder,
        )
    return ShortcutActivation(
        kind=ShortcutActivationKind.READY,
        key=normalized_key,
        folder_name=folder,
    )
