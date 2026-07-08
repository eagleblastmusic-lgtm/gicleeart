"""Rejestr typów efektów strony głównej — jedna zakładka = jeden pakiet efektów.

Nowy efekt: dodaj wpis do HOME_EFFECT_TYPES (lub register_home_effect_type).
Panel UI: home_effect_panels.py. Storage: section_effects_storage.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from tkinter import ttk

from .final_difference_settings import validate_final_difference_config
from .home_effect_panels import (
    build_gradient_bio_effect_tab,
    build_parallax_effect_tab,
    build_scroll_reveal_tab,
    build_text_hover_tab,
)
from .section_effects_storage import (
    load_gradient_bio_for_hook,
    load_parallax_for_hook,
    load_scroll_reveal_for_hook,
    load_text_hover_for_hook,
    save_gradient_parallax_for_hook,
    save_scroll_reveal_for_hook,
    save_text_hover_for_hook,
)
from .studio_reveal_settings import STUDIO_REVEAL_DEFAULTS, validate_studio_reveal_config

PanelBuilder = Callable[[ttk.Notebook, dict[str, Any], str], dict[str, Any]]
LoadFn = Callable[[str, str], dict[str, Any]]
SaveFn = Callable[[str, str, dict[str, Any]], Any]
ValidateFn = Callable[[dict[str, Any]], list[str]]


@dataclass(frozen=True)
class HomeEffectType:
    effect_id: str
    tab_label: str
    sort_order: int
    build_tab: PanelBuilder
    load_for_hook: LoadFn
    description: str = ""

    def validate(self, cfg: dict[str, Any]) -> list[str]:
        if self.effect_id == "scroll_reveal":
            merged = dict(STUDIO_REVEAL_DEFAULTS)
            merged.update(cfg)
            return validate_studio_reveal_config(merged)
        if self.effect_id == "text_hover":
            return validate_final_difference_config(cfg)
        return []


HOME_EFFECT_TYPES: list[HomeEffectType] = [
    HomeEffectType(
        effect_id="scroll_reveal",
        tab_label="Reveal i hover",
        sort_order=10,
        build_tab=lambda nb, cfg, hook: build_scroll_reveal_tab(nb, cfg, hook=hook),
        load_for_hook=load_scroll_reveal_for_hook,
        description="Scroll reveal, hover karty/tekstu, idle light.",
    ),
    HomeEffectType(
        effect_id="text_hover",
        tab_label="Hover tekstu",
        sort_order=20,
        build_tab=lambda nb, cfg, hook: build_text_hover_tab(nb, cfg, hook=hook),
        load_for_hook=load_text_hover_for_hook,
        description="Muzealny hover/focus centralnego tekstu i grafik.",
    ),
    HomeEffectType(
        effect_id="gradient_bio",
        tab_label="Gradient BIO",
        sort_order=30,
        build_tab=lambda nb, cfg, hook: build_gradient_bio_effect_tab(nb, cfg, hook=hook),
        load_for_hook=load_gradient_bio_for_hook,
        description="Presety gradientu jak w biografii kolekcji.",
    ),
    HomeEffectType(
        effect_id="parallax",
        tab_label="Parallax tła",
        sort_order=40,
        build_tab=lambda nb, cfg, hook: build_parallax_effect_tab(nb, cfg, hook=hook),
        load_for_hook=load_parallax_for_hook,
        description="Subtelny parallax tła od kursora (desktop).",
    ),
]


def register_home_effect_type(effect: HomeEffectType) -> None:
    """Dodaj nowy typ efektu (np. po wdrożeniu pakietu z Cursora)."""
    for i, existing in enumerate(HOME_EFFECT_TYPES):
        if existing.effect_id == effect.effect_id:
            HOME_EFFECT_TYPES[i] = effect
            return
    HOME_EFFECT_TYPES.append(effect)
    HOME_EFFECT_TYPES.sort(key=lambda e: e.sort_order)


def sorted_effect_types() -> list[HomeEffectType]:
    return sorted(HOME_EFFECT_TYPES, key=lambda e: (e.sort_order, e.tab_label))


def save_effect_for_hook(
    variant_id: str,
    hook: str,
    effect_id: str,
    cfg: dict[str, Any],
    *,
    gradient_cfg: dict[str, Any] | None = None,
    parallax_cfg: dict[str, Any] | None = None,
) -> Any:
    if effect_id == "scroll_reveal":
        return save_scroll_reveal_for_hook(variant_id, hook, cfg)
    if effect_id == "text_hover":
        return save_text_hover_for_hook(variant_id, hook, cfg)
    if effect_id == "gradient_bio" and gradient_cfg is not None and parallax_cfg is not None:
        return save_gradient_parallax_for_hook(variant_id, hook, cfg, parallax_cfg)
    if effect_id == "parallax" and gradient_cfg is not None and parallax_cfg is not None:
        return save_gradient_parallax_for_hook(variant_id, hook, gradient_cfg, cfg)
    return None


def save_all_effects_for_hook(
    variant_id: str,
    hook: str,
    collected: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Zapis wszystkich efektów dla jednego hooka (merge gradient + parallax)."""
    saved_sr = save_scroll_reveal_for_hook(variant_id, hook, collected["scroll_reveal"])
    saved_th = save_text_hover_for_hook(variant_id, hook, collected["text_hover"])
    grad = collected.get("gradient_bio") or {}
    par = collected.get("parallax") or {}
    saved_bg = save_gradient_parallax_for_hook(variant_id, hook, grad, par)
    return {
        "scroll_reveal": saved_sr,
        "text_hover": saved_th,
        "section_bg": saved_bg,
    }
