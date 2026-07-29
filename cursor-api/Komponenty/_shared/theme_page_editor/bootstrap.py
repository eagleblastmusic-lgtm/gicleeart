"""Bootstrap cienkich komponentów stron menu."""

from __future__ import annotations

from pathlib import Path

from Komponenty._shared.theme_page_editor.safe_writes import (
    install_atomic_theme_page_writes,
)

install_atomic_theme_page_writes()

from Komponenty._shared.theme_page_editor import gui_shell
from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.types import TemplateZone



def component_dir_from_module(module_file: str) -> Path:
    return Path(module_file).resolve().parent



def build_editor_config(
    *,
    module_file: str,
    component_id: str,
    app_title: str,
    intro_title: str,
    intro_body: str,
    template_rel: str,
    preview_path: str,
    variant_id_prefix: str,
    zones: tuple[TemplateZone, ...],
    variant_label_default: str = "Wersja 1",
    extra_toolbar: tuple[tuple[str, object], ...] = (),
    section_effects_asset_enabled: bool = True,
    extra_deploy_relpaths: tuple[str, ...] = (),
    extra_deploy_globs: tuple[str, ...] = (),
) -> PageEditorConfig:
    return PageEditorConfig(
        component_id=component_id,
        component_dir=component_dir_from_module(module_file),
        app_title=app_title,
        intro_title=intro_title,
        intro_body=intro_body,
        template_rel=template_rel,
        preview_path=preview_path,
        variant_id_prefix=variant_id_prefix,
        zones=zones,
        variant_label_default=variant_label_default,
        extra_toolbar=extra_toolbar,
        section_effects_asset_enabled=section_effects_asset_enabled,
        extra_deploy_relpaths=extra_deploy_relpaths,
        extra_deploy_globs=extra_deploy_globs,
    )



def build_page_ui(host, config: PageEditorConfig, *, inline: bool = False) -> None:
    gui_shell.build_page_editor(host, config, inline=inline)
