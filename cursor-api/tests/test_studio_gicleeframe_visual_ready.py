from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
SELECTION_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_selection_orchestration.py"
)
EDITOR_SHELL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
LIFECYCLE_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_lifecycle_inventory.py"
DETAILS_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_details_on_demand.py"


def _view_text() -> str:
    return VIEW_PATH.read_text(encoding="utf-8")


def _lifecycle_text() -> str:
    return LIFECYCLE_PATH.read_text(encoding="utf-8")


def _editor_shell_text() -> str:
    return EDITOR_SHELL_PATH.read_text(encoding="utf-8")


def _selection_text() -> str:
    return SELECTION_PATH.read_text(encoding="utf-8")


def _details_text() -> str:
    return DETAILS_PATH.read_text(encoding="utf-8")


def _selection_source_text() -> str:
    return (
        _view_text()
        + "\n"
        + _selection_text()
        + "\n"
        + _editor_shell_text()
        + "\n"
        + _details_text()
    )


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_gicleeframe_has_visual_state_fields() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_visual_bootstrap_complete" in text
    assert "_loading_overlay" in text
    assert "_visual_enter_mono" in text


def test_gicleeframe_logs_all_visual_events() -> None:
    view_text = _view_text()
    lifecycle_text = _lifecycle_text()
    editor_text = _editor_shell_text()
    event_sources = {
        "studio.gicleeframe.visual.enter": (view_text, lifecycle_text),
        "studio.gicleeframe.visual.shell_built": (lifecycle_text,),
        "studio.gicleeframe.visual.inventory_loaded": (lifecycle_text,),
        "studio.gicleeframe.visual.first_selection_done": (view_text, editor_text, _selection_text()),
        "studio.gicleeframe.visual.idle_ready": (lifecycle_text,),
        "studio.gicleeframe.visual.visible_ready": (lifecycle_text,),
        "studio.gicleeframe.visual.full_ready_progressive": (lifecycle_text,),
        "studio.gicleeframe.atomic_reveal.overlay_shown": (lifecycle_text,),
        "studio.gicleeframe.atomic_reveal.minimal_ready": (lifecycle_text,),
        "studio.gicleeframe.atomic_reveal.ready": (lifecycle_text,),
        "studio.gicleeframe.atomic_reveal.revealed": (lifecycle_text,),
        "studio.gicleeframe.atomic_reveal.waiting_for": (lifecycle_text,),
    }
    for event, sources in event_sources.items():
        assert any(event in source for source in sources), event


def test_on_show_schedules_atomic_reveal_when_not_complete() -> None:
    lifecycle_text = _lifecycle_text()
    block = _method_block(lifecycle_text, "on_show")

    assert "_schedule_atomic_reveal_check" in block
    assert "cache_hit" in block


def test_schedule_atomic_reveal_uses_after_idle() -> None:
    lifecycle_text = _lifecycle_text()
    block = _method_block(lifecycle_text, "_schedule_atomic_reveal_check")

    assert "after_idle" in block
    assert "_try_atomic_reveal" in block


def test_loading_overlay_copy() -> None:
    lifecycle_text = _lifecycle_text()

    assert "Przygotowuję GICLÉE FRAME" in lifecycle_text
    assert "_GF_LOADING_OVERLAY_TEXT" in lifecycle_text


def test_launcher_gicleeframe_open_passes_cache_hit_without_update_idletasks() -> None:
    """GICLÉE FRAME re-entry uses mount lane; async views skip update_idletasks."""
    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    shell_block = _method_block(text, "_show_gicleeframe_shell")
    mount_block = _method_block(text, "_mount_view_lane")
    idletasks_block = _method_block(text, "_maybe_update_idletasks_for_view")

    # Cache re-entry delegates to mount lane instead of inline on_show/update_idletasks.
    assert "_mount_view_lane" in shell_block
    assert "cache_hit=True" in shell_block
    assert "on_show" not in shell_block
    assert "update_idletasks" not in shell_block

    # Navigation is wired via pre_grid before grid/on_show.
    assert "pre_grid" in shell_block
    assert "set_navigation" in shell_block

    # Mount lane is the single place that calls on_show with cache_hit.
    assert "on_show(cache_hit=cache_hit)" in mount_block
    assert mount_block.index("on_show") < mount_block.index("_maybe_update_idletasks_for_view")

    # GicleeFrameView opts out of synchronous update_idletasks.
    assert GicleeFrameView.uses_async_first_paint is True
    assert "uses_async_first_paint" in idletasks_block
    assert "studio.show_view.update_idletasks.skipped" in idletasks_block


def test_gicleeframe_has_section_visual_cache() -> None:
    view_text = _view_text()
    selection_text = _selection_text()
    editor_text = _editor_shell_text()
    details_text = _details_text()

    assert "_section_visual_cache" in view_text
    assert "SectionVisualCacheEntry" in view_text
    for event in (
        "studio.gicleeframe.selection.minimal_cache_hit",
        "studio.gicleeframe.selection.minimal_cache_miss",
        "studio.gicleeframe.selection.cache_hit_skip_visible_refresh",
        "studio.gicleeframe.selection.cache_hit_partial",
        "studio.gicleeframe.selection.cache_miss_stable_shell",
        "studio.gicleeframe.selection.visual_cache_saved",
        "studio.gicleeframe.selection.minimal_editor_ready",
        "studio.gicleeframe.selection.atomic_swap.scheduled",
        "studio.gicleeframe.selection.atomic_swap.ready",
        "studio.gicleeframe.selection.atomic_swap.applied",
        "studio.gicleeframe.editor.stable_shell_ready",
        "studio.gicleeframe.editor.stale_content_kept",
        "studio.gicleeframe.editor.content_swapped",
        "studio.gicleeframe.editor.skeleton_suppressed",
        "studio.gicleeframe.editor.layout_shift_guard",
        "studio.gicleeframe.details_on_demand.available",
    ):
        assert (
            event in view_text
            or event in selection_text
            or event in editor_text
            or event in details_text
        )


def test_gicleeframe_has_minimal_and_details_cache_events() -> None:
    view_text = _view_text()
    lifecycle_text = _lifecycle_text()
    selection_text = _selection_text()
    editor_text = _editor_shell_text()
    details_text = _details_text()

    assert "_minimal_cache_entry" in editor_text
    assert "_details_cache_entry" in details_text
    assert "details_cache_preview" in details_text
    event_sources = {
        "studio.gicleeframe.selection.minimal_cache_hit": (selection_text, editor_text),
        "studio.gicleeframe.selection.minimal_cache_miss": (selection_text, editor_text),
        "studio.gicleeframe.selection.minimal_editor_ready": (editor_text,),
        "studio.gicleeframe.details_on_demand.available": (details_text,),
        "studio.gicleeframe.details_on_demand.requested": (details_text,),
        "studio.gicleeframe.details_on_demand.full_auto_suppressed": (details_text,),
        "studio.gicleeframe.details_shell.requested": (details_text,),
        "studio.gicleeframe.details_shell.ready": (details_text,),
        "studio.gicleeframe.details_shell.applied": (details_text,),
        "studio.gicleeframe.details_module.requested": (details_text,),
        "studio.gicleeframe.details_module.ready": (details_text,),
        "studio.gicleeframe.details_module.applied": (details_text,),
        "studio.gicleeframe.details_module.cache_hit": (details_text,),
        "studio.gicleeframe.details_module.batch": (details_text,),
        "studio.gicleeframe.details_on_demand.cancelled": (selection_text, details_text),
        "studio.gicleeframe.details_on_demand.applied": (details_text,),
        "studio.gicleeframe.visible_prewarm.suppressed": (lifecycle_text,),
    }
    for event, sources in event_sources.items():
        assert any(event in source for source in sources), event


def test_gicleeframe_section_reentry_uses_minimal_cache() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.studio.gicleeframe_page_draft import MergedPageElement
    from giclee_app.ui.gicleeframe_view import GicleeFrameView, SectionVisualCacheEntry

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        elem_a = MergedPageElement(
            element_id="elem-a",
            section_key="section-a",
            element_type="divider",
            group="body",
            order=0,
            label="Sekcja A",
            title="Tytuł A",
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
        elem_b = MergedPageElement(
            element_id="elem-b",
            section_key="section-b",
            element_type="divider",
            group="body",
            order=1,
            label="Sekcja B",
            title="Tytuł B",
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
        view._merged_by_id = {"elem-a": elem_a, "elem-b": elem_b}

        logged: list[tuple[str, dict]] = []
        populate_calls: list[bool] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        def _populate_with_flag(m, *, visual_cache_refresh: bool = False, atomic_swap: bool = False) -> None:  # type: ignore[no-untyped-def]
            populate_calls.append(visual_cache_refresh)

        with patch(
            "giclee_app.ui.gicleeframe_view_selection_orchestration.log_event",
            side_effect=_capture,
        ):
            with patch(
                "giclee_app.ui.gicleeframe_view_details_on_demand.log_event",
                side_effect=_capture,
            ):
                with patch(
                    "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
                    side_effect=_capture,
                ):
                    with patch.object(view, "after_idle", side_effect=lambda cb: cb()):
                        with patch.object(view, "_populate_editor", side_effect=_populate_with_flag):
                            view._select_element("elem-a")
                            view._section_visual_cache["elem-a"] = SectionVisualCacheEntry(
                                element_type="divider",
                                status="ok",
                                has_draft_patch=False,
                                title="Tytuł A",
                                text="",
                                alt="",
                                image_ref="",
                                notes="",
                                visible=True,
                                subtitle_text="Sekcja A",
                                page_context_summary=(("Typ sekcji", "divider"),),
                                fields_title=False,
                                fields_text=False,
                                fields_alt=False,
                                fields_image_ref=False,
                                fields_notes=True,
                                fields_visible=True,
                                fields_children=False,
                                fields_page_context=True,
                                media_details_built=False,
                                preview_key="",
                                layer_nav_visible=False,
                                layer_nav_titles=(),
                            )
                            view._select_element("elem-b")
                            view._select_element("elem-a")

        minimal_hits = [
            item
            for item in logged
            if item[0] == "studio.gicleeframe.selection.minimal_cache_hit"
        ]
        assert len(minimal_hits) == 1
        assert minimal_hits[0][1]["element_id"] == "elem-a"

        minimal_ready = [
            item
            for item in logged
            if item[0] == "studio.gicleeframe.selection.minimal_editor_ready"
        ]
        assert any(item[1].get("element_id") == "elem-a" and item[1].get("from_cache") for item in minimal_ready)

        skip_events = [
            item
            for item in logged
            if item[0] == "studio.gicleeframe.selection.cache_hit_skip_visible_refresh"
        ]
        assert len(skip_events) == 1
        assert skip_events[0][1]["element_id"] == "elem-a"

        miss_shell_events = [
            item
            for item in logged
            if item[0] == "studio.gicleeframe.selection.cache_miss_stable_shell"
        ]
        assert len(miss_shell_events) == 2

        details_on_demand = [
            item for item in logged if item[0] == "studio.gicleeframe.details_on_demand.requested"
        ]
        assert len(details_on_demand) == 0

        assert populate_calls == [False, False]
        swap_applied = [
            item
            for item in logged
            if item[0] == "studio.gicleeframe.selection.atomic_swap.applied"
        ]
        assert len(swap_applied) == 2
    finally:
        root.destroy()


def _media_element(element_id: str = "media-1"):
    from giclee_app.studio.gicleeframe_page_draft import MergedPageElement

    return MergedPageElement(
        element_id=element_id,
        section_key=f"section-{element_id}",
        element_type="media_section",
        group="body",
        order=0,
        label="Media" if element_id == "media-1" else "Other",
        title="Media title",
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


def test_details_available_keeps_since_click_ms() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = _media_element()
        view._merged_by_id = {"media-1": media}
        view._selected_id = "media-1"
        view._selection_click_mono = __import__("time").perf_counter()
        view._identity_card = ctk.CTkFrame(view)

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch(
            "giclee_app.ui.gicleeframe_view_details_on_demand.log_event",
            side_effect=_capture,
        ):
            view._show_details_on_demand_block(media)

        available = next(
            item for item in logged if item[0] == "studio.gicleeframe.details_on_demand.available"
        )
        assert "since_click_ms" in available[1]
        assert "since_details_cta_ms" not in available[1]
    finally:
        root.destroy()


def test_details_shell_on_cta_click_without_auto_stages() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = _media_element()
        view._merged_by_id = {"media-1": media}
        view._selected_id = "media-1"
        view._details_on_demand_element_id = "media-1"
        view._identity_card = ctk.CTkFrame(view)

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch(
            "giclee_app.ui.gicleeframe_view_details_on_demand.log_event",
            side_effect=_capture,
        ):
            with patch.object(view, "_update_section_preview") as preview_mock:
                with patch.object(view, "_update_layer_nav") as layer_mock:
                    with patch.object(view, "_fill_children_overview_buttons_range"):
                        view._on_details_on_demand_clicked()

                        assert any(
                            item[0] == "studio.gicleeframe.details_shell.ready" for item in logged
                        )
                        assert any(
                            item[0] == "studio.gicleeframe.details_shell.applied"
                            for item in logged
                        )
                        assert any(
                            item[0] == "studio.gicleeframe.details_on_demand.full_auto_suppressed"
                            for item in logged
                        )
                        preview_mock.assert_not_called()
                        layer_mock.assert_not_called()
                        assert not any(
                            item[0] == "studio.gicleeframe.details_on_demand.stage_scheduled"
                            for item in logged
                        )
                        assert not any(
                            item[0] == "studio.gicleeframe.details_module.requested"
                            for item in logged
                        )

                        requested = next(
                            item
                            for item in logged
                            if item[0] == "studio.gicleeframe.details_on_demand.requested"
                        )
                        assert requested[1]["since_details_cta_ms"] == 0.0
                        assert "since_click_ms" not in requested[1]

                        applied = next(
                            item
                            for item in logged
                            if item[0] == "studio.gicleeframe.details_on_demand.applied"
                        )
                        assert "since_details_cta_ms" in applied[1]
                        assert "since_request_ms" in applied[1]
                        assert "since_click_ms" not in applied[1]

                        shell_applied = next(
                            item
                            for item in logged
                            if item[0] == "studio.gicleeframe.details_shell.applied"
                        )
                        assert "since_details_cta_ms" in shell_applied[1]
                        assert "since_click_ms" not in shell_applied[1]
    finally:
        root.destroy()


def test_details_module_preview_loads_only_preview() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = _media_element()
        view._merged_by_id = {"media-1": media}
        view._selected_id = "media-1"
        view._details_on_demand_active_element_id = "media-1"

        scheduled: list[tuple[int, object]] = []

        def _after(delay, cb):  # type: ignore[no-untyped-def]
            scheduled.append((delay, cb))
            return f"job-{len(scheduled)}"

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch(
            "giclee_app.ui.gicleeframe_view_details_on_demand.log_event",
            side_effect=_capture,
        ):
            with patch.object(view, "after", side_effect=_after):
                with patch.object(view, "_update_section_preview") as preview_mock:
                    with patch.object(view, "_update_layer_nav") as layer_mock:
                        with patch.object(view, "_fill_children_overview_buttons_range"):
                            view._on_details_module_clicked("preview")
                            while scheduled:
                                _, cb = scheduled.pop(0)
                                cb()

                            preview_mock.assert_called_once()
                            layer_mock.assert_not_called()
                            module_applied = [
                                item
                                for item in logged
                                if item[0] == "studio.gicleeframe.details_module.applied"
                            ]
                            assert len(module_applied) == 1
                            assert module_applied[0][1]["module"] == "preview"
    finally:
        root.destroy()


def test_details_module_layer_nav_loads_only_layer_nav() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = _media_element()
        view._merged_by_id = {"media-1": media}
        view._selected_id = "media-1"
        view._details_on_demand_active_element_id = "media-1"

        scheduled: list[tuple[int, object]] = []

        def _after(delay, cb):  # type: ignore[no-untyped-def]
            scheduled.append((delay, cb))
            return f"job-{len(scheduled)}"

        with patch.object(view, "after", side_effect=_after):
            with patch.object(view, "_update_section_preview") as preview_mock:
                with patch.object(view, "_update_layer_nav") as layer_mock:
                    view._on_details_module_clicked("layer_nav")
                    while scheduled:
                        _, cb = scheduled.pop(0)
                        cb()

                    layer_mock.assert_called_once()
                    preview_mock.assert_not_called()
    finally:
        root.destroy()


def test_details_module_children_batches_when_more_than_two() -> None:
    import customtkinter as ctk
    from unittest.mock import MagicMock, patch

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = _media_element()
        view._merged_by_id = {"media-1": media}
        view._selected_id = "media-1"
        view._details_on_demand_active_element_id = "media-1"

        child_rows = [MagicMock() for _ in range(4)]
        for index, row in enumerate(child_rows):
            row.children = ()
            row.element_id = f"child-{index}"

        scheduled: list[tuple[int, object]] = []

        def _after(delay, cb):  # type: ignore[no-untyped-def]
            scheduled.append((delay, cb))
            return f"job-{len(scheduled)}"

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch(
            "giclee_app.ui.gicleeframe_view_details_on_demand.log_event",
            side_effect=_capture,
        ):
            with patch.object(view, "after", side_effect=_after):
                with patch.object(view, "_tree_row_for_element", return_value=MagicMock(children=child_rows)):
                    with patch.object(view, "_fill_children_overview_buttons_range") as children_mock:
                        view._on_details_module_clicked("children")
                        while scheduled:
                            _, cb = scheduled.pop(0)
                            cb()

                        assert children_mock.call_count >= 2
                        batch_events = [
                            item
                            for item in logged
                            if item[0] == "studio.gicleeframe.details_module.batch"
                        ]
                        assert len(batch_events) >= 1
                        assert batch_events[0][1]["module"] == "children"
    finally:
        root.destroy()


def test_details_modules_are_separate_not_monolithic() -> None:
    text = DETAILS_PATH.read_text(encoding="utf-8")
    module_block = _method_block(text, "_execute_details_module")

    assert "_update_section_preview(" in module_block
    assert "_update_layer_nav(" in module_block
    assert module_block.count("_update_section_preview(") == 1
    assert "_run_children_details_module_batched" in text
    assert "_on_details_module_clicked" in text
    assert "_show_details_shell" in text


def test_details_module_cache_hit_on_second_click() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.ui.gicleeframe_view import GicleeFrameView, SectionVisualCacheEntry

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = _media_element()
        view._merged_by_id = {"media-1": media}
        view._selected_id = "media-1"
        view._details_on_demand_active_element_id = "media-1"
        view._section_visual_cache["media-1"] = SectionVisualCacheEntry(
            element_type="media_section",
            status="ok",
            has_draft_patch=False,
            title="Media title",
            text="",
            alt="",
            image_ref="",
            notes="",
            visible=True,
            subtitle_text="Media",
            page_context_summary=(("Typ sekcji", "media_section"),),
            fields_title=False,
            fields_text=False,
            fields_alt=False,
            fields_image_ref=False,
            fields_notes=True,
            fields_visible=True,
            fields_children=True,
            fields_page_context=True,
            media_details_built=False,
            preview_key="media-1",
            layer_nav_visible=False,
            layer_nav_titles=(),
            details_cache_preview=True,
            details_cache_page_context=False,
            details_cache_layer_nav=False,
            details_cache_children=False,
        )

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch(
            "giclee_app.ui.gicleeframe_view_details_on_demand.log_event",
            side_effect=_capture,
        ):
            with patch.object(view, "_apply_cached_preview_module") as preview_cache_mock:
                with patch.object(view, "_apply_cached_layer_nav_module") as layer_cache_mock:
                    view._on_details_module_clicked("preview")

        cache_hits = [
            item for item in logged if item[0] == "studio.gicleeframe.details_module.cache_hit"
        ]
        assert len(cache_hits) == 1
        assert cache_hits[0][1]["module"] == "preview"
        preview_cache_mock.assert_called_once()
        layer_cache_mock.assert_not_called()
    finally:
        root.destroy()


def test_details_module_cancelled_when_selecting_other_section() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = _media_element("media-1")
        other = _media_element("media-2")
        view._merged_by_id = {"media-1": media, "media-2": other}
        view._selected_id = "media-1"
        view._details_on_demand_element_id = "media-1"
        view._details_on_demand_active_element_id = "media-1"
        view._details_on_demand_generation = 3
        view._details_on_demand_after_ids.append("fake-job")

        scheduled: list[tuple[int, object]] = []

        def _after(delay, cb):  # type: ignore[no-untyped-def]
            scheduled.append((delay, cb))
            return f"job-{len(scheduled)}"

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch(
            "giclee_app.ui.gicleeframe_view_selection_orchestration.log_event",
            side_effect=_capture,
        ):
            with patch(
                "giclee_app.ui.gicleeframe_view_details_on_demand.log_event",
                side_effect=_capture,
            ):
                with patch.object(view, "after", side_effect=_after):
                    with patch.object(view, "after_cancel"):
                        with patch.object(view, "_update_section_preview") as preview_mock:
                            view._on_details_module_clicked("preview")
                            with patch.object(view, "_schedule_atomic_swap_populate"):
                                with patch.object(view, "_highlight_section_row"):
                                    with patch.object(view, "_update_section_list_trigger"):
                                        view._select_element("media-2")
                            while scheduled:
                                _, cb = scheduled.pop(0)
                                cb()

                            preview_mock.assert_not_called()
        cancelled = [
            item for item in logged if item[0] == "studio.gicleeframe.details_on_demand.cancelled"
        ]
        assert len(cancelled) == 1
        assert cancelled[0][1]["previous_details_element_id"] == "media-1"
        assert "request_open_ms" in cancelled[0][1]
        assert "since_request_ms" not in cancelled[0][1]
    finally:
        root.destroy()
