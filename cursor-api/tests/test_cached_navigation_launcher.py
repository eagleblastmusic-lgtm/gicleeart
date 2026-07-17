from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from giclee_app import cached_navigation_launcher
from giclee_app.cached_navigation_launcher import CachedNavigationGicleeApp
from giclee_app.category_navigation import CategoryNavigationPlan, CategoryViewKind
from giclee_app.dragdrop_category_launcher import DragDropCategoryGicleeApp
from giclee_app.launcher_navigation_cache import (
    NavigationViewCache,
    navigation_view_key,
    navigation_view_signature,
)


@dataclass
class FakeFrame:
    exists: bool = True
    pack_calls: list[dict[str, object]] = field(default_factory=list)
    forget_calls: int = 0
    destroy_calls: int = 0

    def pack(self, **kwargs: object) -> None:
        self.pack_calls.append(dict(kwargs))

    def pack_forget(self) -> None:
        self.forget_calls += 1

    def winfo_exists(self) -> bool:
        return self.exists

    def destroy(self) -> None:
        self.destroy_calls += 1
        self.exists = False


class FakeRoot:
    def __init__(self, title: str = "Initial") -> None:
        self.value = title

    def title(self, value: str | None = None) -> str:
        if value is not None:
            self.value = value
        return self.value


class FakeSubtitle:
    def __init__(self, text: str = "Initial subtitle") -> None:
        self.text = text

    def cget(self, key: str) -> str:
        assert key == "text"
        return self.text

    def configure(self, *, text: str) -> None:
        self.text = text


class FakeHover:
    def __init__(self) -> None:
        self.clear_calls = 0

    def clear_active(self) -> None:
        self.clear_calls += 1


def _plan() -> CategoryNavigationPlan:
    return CategoryNavigationPlan(
        kind=CategoryViewKind.CATEGORY_INDEX,
        active_section=None,
        sections=(),
    )


def _bare_app() -> CachedNavigationGicleeApp:
    app = CachedNavigationGicleeApp.__new__(CachedNavigationGicleeApp)
    app._navigation_views = NavigationViewCache()
    app._navigation_cache_host = None
    app._active_navigation_frame = None
    app._all_components = []
    app._layout = object()
    app._normally_visible = set()
    app._active_section = None
    app._tile_hover = FakeHover()
    app._clear_drag_state = lambda: None
    app._dnd_tiles = []
    app.root = FakeRoot()
    app._subtitle_widget = FakeSubtitle()
    return app


def test_cache_hit_reuses_frame_and_restores_drag_targets_and_chrome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    app = _bare_app()
    host = FakeFrame()
    previous = FakeFrame()
    cached_frame = FakeFrame()
    cached_tile = FakeFrame()
    app._navigation_cache_host = host
    app.tiles_frame = previous
    app._active_navigation_frame = previous
    cached = cached_navigation_launcher._CachedNavigationView(
        frame=cached_frame,
        dnd_tiles=(cached_tile,),
        window_title="Cached title",
        subtitle="Cached subtitle",
    )
    app._navigation_views.put(
        navigation_view_key(plan),
        navigation_view_signature(plan),
        cached,
    )

    monkeypatch.setattr(
        cached_navigation_launcher,
        "resolve_category_navigation",
        lambda *_args, **_kwargs: plan,
    )

    def fail_render(_self: object) -> None:
        raise AssertionError("cache hit must not rebuild widgets")

    monkeypatch.setattr(DragDropCategoryGicleeApp, "_render_tiles", fail_render)

    app._render_tiles()

    assert previous.forget_calls == 1
    assert cached_frame.pack_calls == [{"fill": "both", "expand": True}]
    assert app.tiles_frame is cached_frame
    assert app._dnd_tiles == [cached_tile]
    assert app.root.title() == "Cached title"
    assert app._subtitle_widget.text == "Cached subtitle"
    assert app._tile_hover.clear_calls == 1


def test_cache_miss_builds_nested_frame_and_stores_finished_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    app = _bare_app()
    host = FakeFrame()
    created = FakeFrame()
    built_tile = FakeFrame()
    app.tiles_frame = host

    monkeypatch.setattr(
        cached_navigation_launcher,
        "resolve_category_navigation",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        cached_navigation_launcher.tk,
        "Frame",
        lambda _parent, **_kwargs: created,
    )

    def fake_render(self: CachedNavigationGicleeApp) -> None:
        self._dnd_tiles = [built_tile]
        self.root.title("Built title")
        self._set_subtitle("Built subtitle")

    monkeypatch.setattr(DragDropCategoryGicleeApp, "_render_tiles", fake_render)

    app._render_tiles()

    stored = app._navigation_views.get(
        navigation_view_key(plan),
        navigation_view_signature(plan),
    )
    assert stored is not None
    assert stored.frame is created
    assert stored.dnd_tiles == (built_tile,)
    assert stored.window_title == "Built title"
    assert stored.subtitle == "Built subtitle"
    assert app._navigation_cache_host is host
    assert app.tiles_frame is created
    assert app._active_navigation_frame is created
    assert created.pack_calls == [{"fill": "both", "expand": True}]


def test_stale_cached_frame_is_destroyed_before_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    app = _bare_app()
    host = FakeFrame()
    stale_frame = FakeFrame()
    created = FakeFrame()
    app.tiles_frame = host
    key = navigation_view_key(plan)
    app._navigation_views.put(
        key,
        ("stale",),
        cached_navigation_launcher._CachedNavigationView(
            frame=stale_frame,
            dnd_tiles=(),
            window_title="Stale",
            subtitle="Stale",
        ),
    )

    monkeypatch.setattr(
        cached_navigation_launcher,
        "resolve_category_navigation",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        cached_navigation_launcher.tk,
        "Frame",
        lambda _parent, **_kwargs: created,
    )
    monkeypatch.setattr(
        DragDropCategoryGicleeApp,
        "_render_tiles",
        lambda self: None,
    )

    app._render_tiles()

    assert stale_frame.destroy_calls == 1
    assert app._navigation_views.get(
        key,
        navigation_view_signature(plan),
    ) is not None
