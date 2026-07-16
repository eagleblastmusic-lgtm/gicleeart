"""Jawne profile uruchomieniowe GicleeApp / Studio.

Profil jest niemutowalny i wybierany w composition root (entrypoint).
Nie zależy od kolejności importów ani od trwałego globalnego przełącznika runtime.
Scoped ``app_profile_context`` służy wyłącznie do przekazania profilu przez
legacy composition boundaries, które nie przyjmują jeszcze argumentu profilu.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator


_ALL_STABILITY_CHANNELS = (
    "stable",
    "preview",
    "experimental",
    "legacy",
)


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
    allowed_component_stability: tuple[str, ...] = _ALL_STABILITY_CHANNELS

    def allows_component_stability(self, stability: str) -> bool:
        """Czy profil dopuszcza komponent o wskazanym kanale stabilności."""

        return stability in self.allowed_component_stability


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

STUDIO_PROFILE = AppProfile(
    profile_id="studio",
    display_name="Giclée Studio",
    channel="stable",
    is_preview=False,
    state_namespace="GicleeStudio",
    log_namespace="GicleeStudio",
    window_title="Giclée Studio",
    allowed_component_stability=("stable",),
)

PROFILES: dict[str, AppProfile] = {
    CLASSIC_PROFILE.profile_id: CLASSIC_PROFILE,
    STUDIO_PREVIEW_PROFILE.profile_id: STUDIO_PREVIEW_PROFILE,
    STUDIO_PROFILE.profile_id: STUDIO_PROFILE,
}

_PROFILE_CONTEXT: ContextVar[AppProfile | None] = ContextVar(
    "giclee_app_profile",
    default=None,
)


def get_profile(profile_id: str) -> AppProfile:
    """Zwraca znany profil albo ValueError dla nieznanego id."""

    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        known = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown app profile {profile_id!r}; known: {known}") from exc


def current_profile(default: AppProfile | None = None) -> AppProfile:
    """Zwraca profil aktywnego kontekstu albo jawny/default classic fallback."""

    active = _PROFILE_CONTEXT.get()
    if active is not None:
        return active
    if default is not None:
        return default
    return CLASSIC_PROFILE


@contextmanager
def app_profile_context(profile: AppProfile) -> Iterator[AppProfile]:
    """Ustawia profil wyłącznie w bieżącym kontekście wykonania."""

    token = _PROFILE_CONTEXT.set(profile)
    try:
        yield profile
    finally:
        _PROFILE_CONTEXT.reset(token)


__all__ = [
    "AppProfile",
    "CLASSIC_PROFILE",
    "PROFILES",
    "STUDIO_PREVIEW_PROFILE",
    "STUDIO_PROFILE",
    "app_profile_context",
    "current_profile",
    "get_profile",
]
