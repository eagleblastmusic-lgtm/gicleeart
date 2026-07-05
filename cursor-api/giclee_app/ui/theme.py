"""Design tokens — GicleeApp Studio (dark premium)."""

from __future__ import annotations

import customtkinter as ctk

# Kolory
AppBg = "#1a1a1c"
PanelBg = "#252528"
SidebarBg = "#1e1e21"
SidebarActive = "#2a2a2e"
SidebarHover = "#252528"
CardBg = "#252528"
CardHover = "#2e2e32"
TextPrimary = "#f5f0e8"
TextMuted = "#8a8580"
AccentGold = "#c9a962"
AccentGoldDim = "#8a7344"
BorderSubtle = "#3a3a3e"
StatusOk = "#6b9e7a"
StatusWarn = "#c9a962"
StatusErr = "#b85c5c"
StatusUnknown = "#6a6a6e"

# Wymiary
SidebarWidth = 220
TopbarHeight = 48
WindowDefault = (1280, 820)
WindowMin = (1024, 680)
CardAccentWidth = 4

# Fonty
FontUi = ("Segoe UI",)
FontBrand = ("Cambria", "Georgia", "Times New Roman")
FontMono = ("Consolas", "Courier New")

APP_TITLE = "GicleeApp Studio"
PREVIEW_BADGE = "PREVIEW"

# --- Cache fontów CTk (reuse, bez wielokrotnego tkfont.families()) ---
_font_cache: dict[tuple, ctk.CTkFont] = {}
_resolved_brand_family: str | None = None


def _resolve_brand_family() -> str:
    global _resolved_brand_family
    if _resolved_brand_family is not None:
        return _resolved_brand_family
    family = FontBrand[0]
    try:
        import tkinter.font as tkfont

        available = {f.lower(): f for f in tkfont.families()}
        for name in FontBrand:
            if name.lower() in available:
                family = available[name.lower()]
                break
    except Exception:  # noqa: BLE001
        pass
    _resolved_brand_family = family
    return family


def get_font(
    size: int = 12,
    weight: str = "normal",
    *,
    family: str | None = None,
    brand: bool = False,
) -> ctk.CTkFont:
    """Zwraca CTkFont z cache — jedna instancja na kombinację parametrów."""
    resolved = _resolve_brand_family() if brand else (family or FontUi[0])
    key = (size, weight, resolved)
    if key not in _font_cache:
        _font_cache[key] = ctk.CTkFont(family=resolved, size=size, weight=weight)
    return _font_cache[key]


def clear_font_cache() -> None:
    """Tylko dla testów."""
    global _resolved_brand_family
    _font_cache.clear()
    _resolved_brand_family = None
