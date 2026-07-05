"""Wspólny edytor szablonów motywu (strony menu) — wzorzec stronaglowna."""

from .config import PageEditorConfig
from .gui_shell import build_page_editor
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
