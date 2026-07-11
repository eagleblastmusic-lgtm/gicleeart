"""Bootstrap cienkich komponentów stron menu."""

from __future__ import annotations
from pathlib import Path

from Komponenty._shared.theme_page_editor import gui_shell
from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.service_base import shopify_ref_label
from Komponenty._shared.theme_page_editor.types import TemplateZone
from Komponenty._shared.theme_page_editor.writer_safety import build_safe_page_editor
from Komponenty._shared.theme_page_editor.writer_safety_runtime_fix import (
    install_deferred_context_fix,
)
from Komponenty._shared.theme_page_editor.writer_safety_delta_fix import (
    install_delta_only_fix,
)

# Hotfix zgodności: gui_shell używa shopify_ref_label przy budowie miniatur i
# statusu tła, ale starsza powłoka nie importowała tej funkcji bezpośrednio.
# Wstrzyknięcie na poziomie bootstrapu obejmuje wszystkie cienkie edytory stron.
gui_shell.shopify_ref_label = shopify_ref_label


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
    )


def build_page_ui(host, config: PageEditorConfig, *, inline: bool = False) -> None:
    install_deferred_context_fix()
    install_delta_only_fix()
    build_safe_page_editor(host, config, inline=inline)
