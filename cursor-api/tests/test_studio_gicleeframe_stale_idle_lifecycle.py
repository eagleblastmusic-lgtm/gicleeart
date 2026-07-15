from __future__ import annotations

from types import SimpleNamespace

from giclee_app.ui.gicleeframe_view_lifecycle_inventory import (
    GicleeFrameLifecycleInventoryMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin


class _LifecycleHarness(GicleeFrameLifecycleInventoryMixin):
    def __init__(self) -> None:
        self._view_lifecycle_visible = True
        self._view_lifecycle_generation = 0
        self._atomic_reveal_after_id = None
        self._visual_bootstrap_complete = False
        self._after_idle_callback = None
        self._cancelled = []
        self._try_calls = []
        self._exists = True
        self._selected_id = None
        self._merged = []
        self._page_draft = SimpleNamespace(draft_edit_count=lambda: 0)

    def winfo_exists(self):
        return self._exists

    def after_idle(self, callback):
        self._after_idle_callback = callback
        return "idle-1"

    def after_cancel(self, after_id):
        self._cancelled.append(after_id)

    def _ensure_atomic_reveal_prerequisites(self):
        return None

    def _try_atomic_reveal(self, *, trigger=None):
        self._try_calls.append(trigger)

    def _cancel_selection_jobs(self):
        return None

    def _cancel_page_context_jobs(self):
        return None

    def _cancel_details_on_demand_jobs(self):
        return None


def test_atomic_reveal_is_deduplicated_and_cancelled_on_hide() -> None:
    view = _LifecycleHarness()

    view._schedule_atomic_reveal_check(trigger="first")
    view._schedule_atomic_reveal_check(trigger="second")

    assert view._atomic_reveal_after_id == "idle-1"
    callback = view._after_idle_callback
    assert callback is not None

    view.on_hide()

    assert view._cancelled == ["idle-1"]
    callback()
    assert view._try_calls == []


def test_destroy_invalidates_pending_reveal() -> None:
    view = _LifecycleHarness()
    view._schedule_atomic_reveal_check(trigger="destroyed")
    callback = view._after_idle_callback
    assert callback is not None

    view._on_lifecycle_destroy(SimpleNamespace(widget=view))
    callback()

    assert view._try_calls == []


class _Widget:
    def __init__(self, exists=True) -> None:
        self.exists = exists

    def winfo_exists(self):
        return self.exists


class _TopBarHarness(GicleeFrameTopBarMixin):
    def __init__(self) -> None:
        self._top_bar_actions_late_done = False
        self._context_bar_actions_building = False
        self._context_bar_row = _Widget(True)
        self._context_bar_actions_slot = _Widget(False)
        self.build_calls = 0

    def _should_suppress_visible_prewarm(self):
        return False

    def _view_lifecycle_alive(self):
        return True

    def winfo_exists(self):
        return True

    def _build_context_bar_actions(self, _row):
        self.build_calls += 1


def test_context_actions_skip_destroyed_slot() -> None:
    view = _TopBarHarness()

    view._build_context_bar_actions_late()

    assert view.build_calls == 0
