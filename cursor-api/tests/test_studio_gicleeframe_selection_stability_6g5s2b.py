"""6G.5-S.2B — selection priority lane / populate enter queue reduction."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def gicleeframe_view():
    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    view = GicleeFrameView(root)
    view.pack()
    yield view
    root.destroy()


def _sample_merged(element_id: str, element_type: str = "divider"):
    from giclee_app.studio.gicleeframe_page_draft import MergedPageElement

    return MergedPageElement(
        element_id=element_id,
        section_key=f"section-{element_id}",
        element_type=element_type,
        group="body",
        order=0,
        label=f"Label {element_id}",
        title=f"Title {element_id}",
        text="",
        image_ref="",
        alt="",
        notes="",
        editable=True,
        source="inventory",
        status="ok",
        has_draft_patch=False,
        visible=True,
    )


def test_select_element_opens_selection_priority_window(gicleeframe_view) -> None:
    view = gicleeframe_view
    element = _sample_merged("elem-priority", "divider")
    view._merged = [element]
    view._rebuild_page_model_cache()
    logged: list[tuple[str, dict]] = []

    def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        logged.append((event, kwargs))

    with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
        with patch.object(view, "_schedule_selection_populate"):
            with patch.object(view, "_highlight_section_row"):
                with patch.object(view, "_show_editor_selection_pending_state"):
                    view._select_element("elem-priority")

    assert view._selection_priority_generation == view._selection_generation
    assert view._selection_priority_until_mono is not None
    assert view._selection_priority_active(view._selection_generation)

    started = [item for item in logged if item[0] == "studio.gicleeframe.selection.priority_start"]
    assert len(started) == 1
    assert started[0][1]["element_id"] == "elem-priority"
    assert started[0][1]["generation"] == view._selection_generation


def test_selection_populate_scheduled_on_priority_path(gicleeframe_view) -> None:
    view = gicleeframe_view
    element = _sample_merged("elem-pop", "section_legacy")
    view._merged = [element]
    view._rebuild_page_model_cache()
    swap_calls: list[tuple[str, int]] = []

    with patch.object(
        view,
        "_schedule_atomic_swap_populate",
        side_effect=lambda eid, gen: swap_calls.append((eid, gen)),
    ):
        with patch.object(view, "_highlight_section_row"):
            view._select_element("elem-pop")

    assert len(swap_calls) == 1
    assert swap_calls[0] == ("elem-pop", view._selection_generation)


def test_deferred_types_use_priority_schedule_path(gicleeframe_view) -> None:
    view = gicleeframe_view
    element = _sample_merged("elem-media", "media_section")
    view._merged = [element]
    view._rebuild_page_model_cache()
    swap_calls: list[tuple[str, int]] = []

    with patch.object(
        view,
        "_schedule_atomic_swap_populate",
        side_effect=lambda eid, gen: swap_calls.append((eid, gen)),
    ):
        with patch.object(view, "_highlight_section_row"):
            view._select_element("elem-media")

    assert len(swap_calls) == 1
    assert swap_calls[0] == ("elem-media", view._selection_generation)


def test_background_job_yields_during_active_selection_priority(gicleeframe_view) -> None:
    view = gicleeframe_view
    view._selection_priority_generation = 7
    view._selection_priority_until_mono = time.perf_counter() + 1.0
    logged: list[tuple[str, dict]] = []
    deferred: list[str] = []

    def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        logged.append((event, kwargs))

    def _fake_after(delay_ms: int, callback) -> str:  # type: ignore[no-untyped-def]
        deferred.append(f"{delay_ms}")
        return "after-1"

    with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
        with patch.object(view, "after", side_effect=_fake_after):
            yielded = view._defer_background_for_selection(
                job="control.late_cards",
                reason="selection_priority_active",
                callback=view._build_control_late_cards,
            )

    assert yielded is True
    assert deferred == ["60"]
    events = [
        item
        for item in logged
        if item[0] == "studio.gicleeframe.background.deferred_for_selection"
    ]
    assert len(events) == 1
    assert events[0][1]["job"] == "control.late_cards"
    assert events[0][1]["generation"] == 7


def test_background_job_does_not_yield_when_priority_expired(gicleeframe_view) -> None:
    view = gicleeframe_view
    view._selection_priority_generation = 3
    view._selection_priority_until_mono = time.perf_counter() - 0.01
    deferred: list[str] = []

    with patch.object(
        view,
        "after",
        side_effect=lambda delay_ms, callback: deferred.append("after"),  # type: ignore[misc]
    ):
        yielded = view._defer_background_for_selection(
            job="section_list.incremental",
            reason="selection_priority_active",
            callback=view._render_section_list_incremental,
        )

    assert yielded is False
    assert deferred == []


def test_rapid_clicks_cancel_stale_jobs_last_generation_wins(gicleeframe_view) -> None:
    view = gicleeframe_view
    first = _sample_merged("elem-a", "media_section")
    second = _sample_merged("elem-b", "media_section")
    view._merged = [first, second]
    view._rebuild_page_model_cache()
    swap_calls: list[tuple[str, int]] = []

    def _capture_swap(element_id: str, generation: int) -> None:
        swap_calls.append((element_id, generation))

    with patch.object(view, "_schedule_atomic_swap_populate", side_effect=_capture_swap):
        with patch.object(view, "_highlight_section_row"):
            with patch.object(view, "_populate_editor") as populate_mock:
                view._select_element("elem-a")
                gen_a = view._selection_generation
                view._select_element("elem-b")
                gen_b = view._selection_generation

                view._run_atomic_swap_populate("elem-a", gen_a)
                view._run_atomic_swap_populate("elem-b", gen_b)

    assert swap_calls[-1] == ("elem-b", gen_b)
    populate_mock.assert_called_once()
    assert view._selected_id == "elem-b"
