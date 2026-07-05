"""Konfiguracja edytora strony menu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .types import TemplateZone


@dataclass(frozen=True)
class PageEditorConfig:
    component_id: str
    component_dir: Path
    app_title: str
    intro_title: str
    intro_body: str
    template_rel: str
    preview_path: str
    variant_id_prefix: str
    zones: tuple[TemplateZone, ...]
    variant_label_default: str = "Wersja 1"
    extra_toolbar: tuple[tuple[str, Callable[[], None]], ...] = field(default_factory=tuple)
    preview_query: str = "giclee_skip_splash=1&giclee_skip_notice=1"

    @property
    def template_basename(self) -> str:
        return Path(self.template_rel).name
