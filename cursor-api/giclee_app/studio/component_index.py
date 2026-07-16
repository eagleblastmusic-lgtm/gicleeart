"""Indeks komponentów Studio — jednorazowy discover przy starcie shell."""

from __future__ import annotations

from dataclasses import dataclass

from ..app_profile import STUDIO_PREVIEW_PROFILE, AppProfile, current_profile
from ..component_loader import Component, discover_components, find_components_dir
from .categories import category_for_folder


@dataclass(frozen=True)
class StudioComponentIndex:
    profile_id: str
    all_components: list[Component]
    available_components: list[Component]
    visible_components: list[Component]
    by_folder: dict[str, Component]
    by_category: dict[str, list[Component]]

    @classmethod
    def build(cls, profile: AppProfile | None = None) -> StudioComponentIndex:
        active_profile = profile or current_profile(STUDIO_PREVIEW_PROFILE)
        root = find_components_dir()
        all_components = discover_components(root, include_hidden=True)
        available_components = [
            comp
            for comp in all_components
            if comp.is_available_in(active_profile.profile_id)
            and active_profile.allows_component_stability(comp.stability)
        ]
        visible_components = [c for c in available_components if not c.hidden]
        by_folder = {c.folder_name: c for c in available_components}
        by_category: dict[str, list[Component]] = {}
        for comp in available_components:
            cat_id = category_for_folder(comp.folder_name)
            by_category.setdefault(cat_id, []).append(comp)
        for items in by_category.values():
            items.sort(key=lambda c: (c.order, c.name.lower()))
        return cls(
            profile_id=active_profile.profile_id,
            all_components=all_components,
            available_components=available_components,
            visible_components=visible_components,
            by_folder=by_folder,
            by_category=by_category,
        )

    def components_for_category(self, category_id: str) -> list[Component]:
        if category_id == "dashboard":
            return []
        return list(self.by_category.get(category_id, []))

    def component_counts(self) -> tuple[int, int]:
        return len(self.all_components), len(self.visible_components)

    def availability_counts(self) -> tuple[int, int, int]:
        """Zwraca discovered, available i visible dla aktywnego profilu."""

        return (
            len(self.all_components),
            len(self.available_components),
            len(self.visible_components),
        )
