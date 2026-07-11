from __future__ import annotations

from . import prehero_integration as integration
from .prehero_full_generator import FULL_PREHERO_CODE_ASSETS, INTRO_HOLD_KEY
from .registry import zone_by_id


def _source() -> str:
    return """{% comment %} auto-generated {% endcomment %}
<script>
window.GICLEE_HOME_SECTIONS = {"hero": "slideshow_4LMfx7"};
window.GICLEE_HOME_STACK = true;
</script>
<style>body { color: white; }</style>
"""


def test_full_prehero_generator_is_idempotent_and_keeps_all_assets() -> None:
    config = integration.export_prehero_config(
        {"current": {INTRO_HOLD_KEY: 2}}
    )

    first = integration.inject_prehero_into_snippet(_source(), config)
    second = integration.inject_prehero_into_snippet(first, config)

    assert first == second
    assert '"introHoldVh": 200' in first
    for asset in FULL_PREHERO_CODE_ASSETS:
        assert asset in first
        assert first.count(asset) == 1


def test_prehero_zone_exposes_intro_hold_field() -> None:
    zone = zone_by_id(integration.PREHERO_ZONE_ID)
    assert zone is not None
    field = next((row for row in zone.fields if row.field_id == INTRO_HOLD_KEY), None)
    assert field is not None
    assert field.kind == "int"


def test_export_includes_intro_hold_vh() -> None:
    config = integration.export_prehero_config(
        {"current": {INTRO_HOLD_KEY: 3}}
    )
    assert config["introHoldVh"] == 300
