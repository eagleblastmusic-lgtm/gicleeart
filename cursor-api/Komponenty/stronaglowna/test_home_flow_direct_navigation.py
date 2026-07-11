from __future__ import annotations

from Komponenty.stronaglowna.home_flow_direct_navigation import (
    _closure_value,
    _resolve_bridge_from_callbacks,
)


def test_closure_value_reads_named_cell() -> None:
    marker = {"ok": True}

    def outer():
        state = marker

        def inner():
            return state

        return inner

    callback = outer()
    assert _closure_value(callback, "state") is marker
    assert _closure_value(callback, "missing") is None


def test_bridge_resolves_show_collect_and_state() -> None:
    state: dict = {"selected_zone_id": "prehero"}
    calls: list[str] = []

    def make_callback():
        def _collect_current_zone() -> None:
            calls.append("collect")

        def _show_zone(zone) -> None:
            _ = state
            _collect_current_zone()
            calls.append(str(zone))

        def _on_zone_select(_event=None) -> None:
            _show_zone("prehero")

        return _on_zone_select

    bridge = _resolve_bridge_from_callbacks([make_callback()])
    assert bridge is not None
    show_zone, collect, resolved_state = bridge
    assert resolved_state is state
    assert callable(collect)

    show_zone("hero")
    assert calls == ["collect", "hero"]
