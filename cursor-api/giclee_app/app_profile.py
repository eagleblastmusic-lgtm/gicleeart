"""Jawne profile uruchomieniowe GicleeApp / Studio Preview.

Profil jest niemutowalny i wybierany w composition root (entrypoint).
Nie zależy od kolejności importów ani od globalnego przełącznika runtime.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppProfile:
    """Kontrakt profilu aplikacji (shell + namespace stanu/logów)."""

    profile_id: str
    display_name: str
    channel: str
    is_preview: bool
    state_namespace: str
    log_namespace: str
    window_title: str


CLASSIC_PROFILE = AppProfile(
    profile_id="classic",
    display_name="GicleeApp",
    channel="stable",
    is_preview=False,
    state_namespace="GicleeApp",
    log_namespace="GicleeApp",
    window_title="GicleeApp",
)

STUDIO_PREVIEW_PROFILE = AppProfile(
    profile_id="studio_preview",
    display_name="Giclée Studio Preview",
    channel="preview",
    is_preview=True,
    state_namespace="GicleeStudioPreview",
    log_namespace="GicleeStudioPreview",
    window_title="Giclée Studio Preview · PREVIEW",
)

# Przyszły profil produkcyjny Studio — poza STUDIO-ISOLATION-1.
# STUDIO_PROFILE = AppProfile(profile_id="studio", ...)

PROFILES: dict[str, AppProfile] = {
    CLASSIC_PROFILE.profile_id: CLASSIC_PROFILE,
    STUDIO_PREVIEW_PROFILE.profile_id: STUDIO_PREVIEW_PROFILE,
}


def get_profile(profile_id: str) -> AppProfile:
    """Zwraca znany profil albo ValueError dla nieznanego id."""

    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        known = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown app profile {profile_id!r}; known: {known}") from exc


__all__ = [
    "AppProfile",
    "CLASSIC_PROFILE",
    "PROFILES",
    "STUDIO_PREVIEW_PROFILE",
    "get_profile",
]
