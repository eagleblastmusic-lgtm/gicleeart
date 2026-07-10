"""Regresja: wspólny edytor stron musi mieć helper etykiet Shopify."""

from Komponenty._shared.theme_page_editor import gui_shell
from Komponenty._shared.theme_page_editor import service_base
from Komponenty._shared.theme_page_editor import bootstrap  # noqa: F401


def test_bootstrap_exposes_shopify_ref_label_to_gui_shell() -> None:
    assert gui_shell.shopify_ref_label is service_base.shopify_ref_label
