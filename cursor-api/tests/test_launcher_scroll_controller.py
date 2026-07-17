from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from giclee_app.launcher import GicleeApp
from giclee_app.launcher_scroll_controller import WheelScrollController


class FakeScheduler:
    def __init__(self) -> None:
        self.callbacks: list[tuple[int, Callable[[], None]]] = []

    def __call__(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> object:
        self.callbacks.append((delay_ms, callback))
        return len(self.callbacks)

    def run_next(self) -> None:
        _delay, callback = self.callbacks.pop(0)
        callback()

    def run_all(self, limit: int = 20) -> int:
        runs = 0
        while self.callbacks:
            if runs >= limit:
                raise AssertionError("scroll controller did not settle")
            self.run_next()
            runs += 1
        return runs


def test_deltas_are_aggregated_into_one_scheduled_frame() -> None:
    scheduler = FakeScheduler()
    applied: list[float] = []
    controller = WheelScrollController(
        scheduler,
        applied.append,
        pixels_per_notch=120.0,
        smoothing=0.5,
        max_tail_frames=3,
        settle_pixels=0.01,
    )

    assert controller.add_delta(30)
    assert controller.add_delta(30)

    assert len(scheduler.callbacks) == 1
    assert controller.pending_pixels == pytest.approx(-60.0)

    scheduler.run_next()

    assert applied == pytest.approx([-30.0])
    assert len(scheduler.callbacks) == 1


def test_touchpad_delta_preserves_fractional_pixel_distance() -> None:
    scheduler = FakeScheduler()
    applied: list[float] = []
    controller = WheelScrollController(scheduler, applied.append)

    controller.add_delta(30)
    runs = scheduler.run_all()

    assert 1 <= runs <= 4
    assert sum(applied) == pytest.approx(-18.0)
    assert controller.pending_pixels == 0.0
    assert not controller.is_scheduled


def test_single_input_has_short_bounded_tail_without_long_inertia() -> None:
    scheduler = FakeScheduler()
    applied: list[float] = []
    controller = WheelScrollController(scheduler, applied.append)

    controller.add_delta(120)
    runs = scheduler.run_all()

    assert runs == 4
    assert sum(applied) == pytest.approx(-72.0)


def test_opposite_deltas_cancel_before_the_frame_runs() -> None:
    scheduler = FakeScheduler()
    applied: list[float] = []
    controller = WheelScrollController(scheduler, applied.append)

    controller.add_delta(120)
    controller.add_delta(-120)
    scheduler.run_all()

    assert applied == []
    assert controller.pending_pixels == 0.0


def test_reset_turns_already_scheduled_frame_into_no_op() -> None:
    scheduler = FakeScheduler()
    applied: list[float] = []
    controller = WheelScrollController(scheduler, applied.append)

    controller.add_delta(120)
    controller.reset()
    scheduler.run_all()

    assert applied == []
    assert controller.pending_pixels == 0.0


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("frame_ms", 0),
        ("pixels_per_notch", 0.0),
        ("smoothing", 0.0),
        ("max_tail_frames", 0),
        ("settle_pixels", -1.0),
    ],
)
def test_invalid_configuration_is_rejected(
    keyword: str,
    value: float,
) -> None:
    scheduler = FakeScheduler()
    kwargs = {keyword: value}

    with pytest.raises(ValueError):
        WheelScrollController(scheduler, lambda _pixels: None, **kwargs)


class FakeMappedView:
    def __init__(self, mapped: bool = True) -> None:
        self.mapped = mapped

    def winfo_ismapped(self) -> bool:
        return self.mapped


class FakeHover:
    def __init__(self) -> None:
        self.suspensions: list[float] = []

    def suspend_for(self, seconds: float) -> None:
        self.suspensions.append(seconds)


class FakeScroll:
    def __init__(self) -> None:
        self.deltas: list[float] = []

    def add_delta(self, delta: float) -> None:
        self.deltas.append(delta)


def test_launcher_wheel_event_suspends_hover_and_queues_native_delta() -> None:
    app = GicleeApp.__new__(GicleeApp)
    app.tiles_view = FakeMappedView()
    app._pointer_is_over_tiles_canvas = lambda _event: True
    app._tile_hover = FakeHover()
    app._wheel_scroll = FakeScroll()

    app._on_canvas_mousewheel(SimpleNamespace(delta=30))

    assert app._tile_hover.suspensions == [0.18]
    assert app._wheel_scroll.deltas == [30]


class FakeCanvas:
    def __init__(
        self,
        *,
        content_height: int = 1000,
        viewport_height: int = 200,
        first: float = 0.1,
    ) -> None:
        self.content_height = content_height
        self.viewport_height = viewport_height
        self.first = first
        self.moves: list[float] = []

    def bbox(self, _tag: str) -> tuple[int, int, int, int]:
        return (0, 0, 100, self.content_height)

    def winfo_height(self) -> int:
        return self.viewport_height

    def yview(self) -> tuple[float, float]:
        visible = self.viewport_height / self.content_height
        return self.first, min(1.0, self.first + visible)

    def yview_moveto(self, fraction: float) -> None:
        self.first = fraction
        self.moves.append(fraction)


def test_launcher_applies_pixel_scroll_and_clamps_to_content_bounds() -> None:
    app = GicleeApp.__new__(GicleeApp)
    canvas = FakeCanvas()
    app.canvas = canvas

    app._scroll_tiles_by_pixels(50.0)
    assert canvas.moves[-1] == pytest.approx(0.15)

    app._scroll_tiles_by_pixels(-1000.0)
    assert canvas.moves[-1] == pytest.approx(0.0)

    canvas.first = 0.79
    app._scroll_tiles_by_pixels(1000.0)
    assert canvas.moves[-1] == pytest.approx(0.8)


def test_launcher_source_uses_frame_controller_without_old_idle_accumulator() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher.py"
    ).read_text(encoding="utf-8")

    assert "WheelScrollController(" in source
    assert "self._wheel_scroll.add_delta(delta)" in source
    assert "self.canvas.yview_moveto(" in source
    assert "_wheel_delta_acc" not in source
    assert "_wheel_idle_id" not in source
    assert "_flush_tiles_canvas_wheel" not in source
    assert "yview_scroll(int(step)" not in source
