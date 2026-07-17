"""Koordynacja hovera kafelków launchera bez masowego repaintowania."""

from __future__ import annotations

from collections.abc import Callable
import time


HoverCallback = Callable[[], None]
Clock = Callable[[], float]


class TileHoverController:
    """Przechowuje najwyżej jeden aktywny hover kafelka.

    Kontroler nie zna Tkintera. Callbacki odpowiadają wyłącznie za zmianę
    wyglądu konkretnego kafelka.
    """

    def __init__(self, clock: Clock = time.monotonic) -> None:
        self._clock = clock
        self._active_key: object | None = None
        self._clear_active: HoverCallback | None = None
        self._suppressed_until = 0.0

    @property
    def active_key(self) -> object | None:
        return self._active_key

    @property
    def suppressed_until(self) -> float:
        return self._suppressed_until

    def is_suppressed(self) -> bool:
        return self._clock() < self._suppressed_until

    def enter(
        self,
        key: object,
        activate: HoverCallback,
        clear: HoverCallback,
    ) -> bool:
        """Aktywuje wskazany kafelek, czyszcząc tylko poprzednio aktywny."""

        if self.is_suppressed():
            return False

        if self._active_key is key:
            return False

        self.clear_active()
        activate()

        self._active_key = key
        self._clear_active = clear
        return True

    def leave(self, key: object) -> bool:
        """Czyści hover tylko wtedy, gdy opuszczono aktywny kafelek."""

        if self._active_key is not key:
            return False

        return self.clear_active()

    def clear_active(self) -> bool:
        """Czyści wyłącznie aktualnie aktywny kafelek."""

        clear = self._clear_active

        if clear is None:
            self._active_key = None
            return False

        # Najpierw zerujemy stan, aby callback mógł bezpiecznie wejść
        # ponownie do kontrolera.
        self._active_key = None
        self._clear_active = None
        clear()
        return True

    def suspend_for(self, seconds: float) -> bool:
        """Wyłącza hover na krótki czas i czyści tylko aktywny kafelek."""

        duration = max(0.0, float(seconds))
        self._suppressed_until = max(
            self._suppressed_until,
            self._clock() + duration,
        )
        return self.clear_active()


__all__ = ["TileHoverController"]
