"""Wspólny edytor szablonów motywu (strony menu) — wzorzec stronaglowna."""

from .config import PageEditorConfig
from .types import TemplateField, TemplateZone, zone_by_id, zone_enabled, set_zone_enabled

__all__ = [
    "PageEditorConfig",
    "TemplateField",
    "TemplateZone",
    "build_page_editor",
    "zone_by_id",
    "zone_enabled",
    "set_zone_enabled",
]


def __getattr__(name: str):
    if name == "build_page_editor":
        from .gui_shell import build_page_editor

        return build_page_editor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
