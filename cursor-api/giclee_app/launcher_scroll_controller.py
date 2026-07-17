"""Short frame-timed wheel scrolling without long inertia."""

from __future__ import annotations

from collections.abc import Callable


FrameCallback = Callable[[], None]
ScheduleCallback = Callable[[int, FrameCallback], object]
ApplyPixelsCallback = Callable[[float], None]


class WheelScrollController:
    """Aggregate wheel deltas and apply them over a short bounded tail."""

    def __init__(
        self,
        schedule: ScheduleCallback,
        apply_pixels: ApplyPixelsCallback,
        *,
        frame_ms: int = 16,
        pixels_per_notch: float = 72.0,
        smoothing: float = 0.6,
        max_tail_frames: int = 4,
        settle_pixels: float = 0.5,
    ) -> None:
        if frame_ms < 1:
            raise ValueError("frame_ms must be positive")
        if pixels_per_notch <= 0.0:
            raise ValueError("pixels_per_notch must be positive")
        if not 0.0 < smoothing <= 1.0:
            raise ValueError("smoothing must be in (0, 1]")
        if max_tail_frames < 1:
            raise ValueError("max_tail_frames must be positive")
        if settle_pixels < 0.0:
            raise ValueError("settle_pixels cannot be negative")

        self._schedule = schedule
        self._apply_pixels = apply_pixels
        self._frame_ms = int(frame_ms)
        self._pixels_per_notch = float(pixels_per_notch)
        self._smoothing = float(smoothing)
        self._max_tail_frames = int(max_tail_frames)
        self._settle_pixels = float(settle_pixels)

        self._pending_pixels = 0.0
        self._tail_frames_remaining = 0
        self._scheduled = False

    @property
    def pending_pixels(self) -> float:
        return self._pending_pixels

    @property
    def is_scheduled(self) -> bool:
        return self._scheduled

    def add_delta(self, delta: float) -> bool:
        """Queue one native wheel delta while preserving fractional movement."""

        value = float(delta)
        if value == 0.0:
            return False

        self._pending_pixels += (
            -value / 120.0
        ) * self._pixels_per_notch
        self._tail_frames_remaining = self._max_tail_frames

        if not self._scheduled:
            self._schedule_next()

        return True

    def reset(self) -> None:
        """Discard pending movement; an already queued frame becomes a no-op."""

        self._pending_pixels = 0.0
        self._tail_frames_remaining = 0

    def _schedule_next(self) -> None:
        self._scheduled = True
        try:
            self._schedule(self._frame_ms, self._run_frame)
        except Exception:
            self._scheduled = False
            raise

    def _run_frame(self) -> None:
        self._scheduled = False
        pending = self._pending_pixels

        if pending == 0.0:
            self._tail_frames_remaining = 0
            return

        if (
            abs(pending) <= self._settle_pixels
            or self._tail_frames_remaining <= 1
        ):
            movement = pending
            remainder = 0.0
            self._tail_frames_remaining = 0
        else:
            movement = pending * self._smoothing
            remainder = pending - movement
            self._tail_frames_remaining -= 1

        self._pending_pixels = remainder
        self._apply_pixels(movement)

        if self._pending_pixels != 0.0 and not self._scheduled:
            self._schedule_next()


__all__ = ["WheelScrollController"]
