from types import SimpleNamespace

from . import home_flow_section_render_authority as authority


class DummyHost:
    pass


def test_render_token_increments_and_invalidates_previous() -> None:
    host = DummyHost()

    first = authority._next_token(host)
    second = authority._next_token(host)

    assert first == 1
    assert second == 2
    assert getattr(host, authority._TOKEN_ATTR) == 2


def test_zone_index_is_resolved_from_stable_section_id(monkeypatch) -> None:
    zone_id = authority.HOME_ZONES[0].zone_id
    monkeypatch.setattr(authority, "active_variant_id", lambda: "home1")
    monkeypatch.setattr(
        authority,
        "flow_item_by_id",
        lambda _variant, stable_id: SimpleNamespace(
            kind="section",
            zone_id=zone_id,
        )
        if stable_id == "section:test"
        else None,
    )

    assert authority._zone_index_for_section("section:test") == 0
    assert authority._zone_index_for_section("phase:test") is None
