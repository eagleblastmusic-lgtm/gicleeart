from __future__ import annotations

from giclee_app.launcher_tile_hover import TileHoverController


class FakeClock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_enter_activates_one_tile_and_same_tile_is_idempotent() -> None:
    events: list[str] = []
    tile = object()
    controller = TileHoverController()

    assert controller.enter(
        tile,
        lambda: events.append("on"),
        lambda: events.append("off"),
    )
    assert controller.active_key is tile

    assert not controller.enter(
        tile,
        lambda: events.append("duplicate-on"),
        lambda: events.append("duplicate-off"),
    )

    assert events == ["on"]


def test_entering_second_tile_clears_only_previous_active_tile() -> None:
    events: list[str] = []
    first = object()
    second = object()
    controller = TileHoverController()

    controller.enter(
        first,
        lambda: events.append("first:on"),
        lambda: events.append("first:off"),
    )
    controller.enter(
        second,
        lambda: events.append("second:on"),
        lambda: events.append("second:off"),
    )

    assert events == [
        "first:on",
        "first:off",
        "second:on",
    ]
    assert controller.active_key is second


def test_leave_ignores_inactive_tile() -> None:
    events: list[str] = []
    active = object()
    inactive = object()
    controller = TileHoverController()

    controller.enter(
        active,
        lambda: events.append("active:on"),
        lambda: events.append("active:off"),
    )

    assert not controller.leave(inactive)
    assert controller.active_key is active
    assert events == ["active:on"]


def test_leave_clears_active_tile_once() -> None:
    events: list[str] = []
    tile = object()
    controller = TileHoverController()

    controller.enter(
        tile,
        lambda: events.append("on"),
        lambda: events.append("off"),
    )

    assert controller.leave(tile)
    assert not controller.leave(tile)
    assert controller.active_key is None
    assert events == ["on", "off"]


def test_suspend_clears_active_and_blocks_new_hover_until_deadline() -> None:
    events: list[str] = []
    clock = FakeClock(10.0)
    first = object()
    second = object()
    controller = TileHoverController(clock)

    controller.enter(
        first,
        lambda: events.append("first:on"),
        lambda: events.append("first:off"),
    )

    assert controller.suspend_for(0.18)
    assert controller.is_suppressed()
    assert controller.active_key is None

    assert not controller.enter(
        second,
        lambda: events.append("second:on"),
        lambda: events.append("second:off"),
    )

    clock.value = 10.19

    assert not controller.is_suppressed()
    assert controller.enter(
        second,
        lambda: events.append("second:on"),
        lambda: events.append("second:off"),
    )

    assert events == [
        "first:on",
        "first:off",
        "second:on",
    ]


def test_longer_existing_suppression_is_not_shortened() -> None:
    clock = FakeClock(20.0)
    controller = TileHoverController(clock)

    controller.suspend_for(1.0)
    first_deadline = controller.suppressed_until

    clock.value = 20.1
    controller.suspend_for(0.1)

    assert controller.suppressed_until == first_deadline

def test_all_tile_builders_use_the_single_hover_controller() -> None:
    import inspect

    from giclee_app.category_launcher import CategoryGicleeApp
    from giclee_app.launcher import GicleeApp
    from giclee_app.styled_category_launcher import StyledCategoryGicleeApp

    builders = (
        GicleeApp._build_tile,
        CategoryGicleeApp._build_category_tile,
        StyledCategoryGicleeApp._build_tile,
    )

    for builder in builders:
        source = inspect.getsource(builder)
        assert "self._tile_hover.enter(" in source
        assert "self._tile_hover.leave(outer)" in source
        assert "_tile_hover_clearers" not in source
        assert "_suppress_tile_hover_until" not in source
