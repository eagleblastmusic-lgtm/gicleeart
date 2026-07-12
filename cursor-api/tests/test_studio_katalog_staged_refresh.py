"""PERF-B — staged Katalog refresh pipeline (yield between stages)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.katalog_data_map import KatalogDataMap, build_katalog_data_map
from giclee_app.studio.katalog_inventory import (
    KatalogInventoryReport,
    build_katalog_inventory,
    inventory_display_rows,
)


def _make_view(tmp_path: Path):
    import customtkinter as ctk

    from giclee_app.ui.katalog_view import KatalogView

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    with patch.object(KatalogView, "_schedule_initial_refresh"):
        view = KatalogView(root, components_root=tmp_path)
    return root, view


def _noop_after(view, delay_ms: int, callback) -> None:  # noqa: ARG001
    pass


def _immediate_after(view, delay_ms: int, callback) -> None:  # noqa: ARG001
    view._run_if_alive(callback)


def _run_async_now(
    widget,
    func,
    on_done,
    *,
    on_error=None,
    poll_ms: int = 40,
) -> None:  # noqa: ANN001, ARG001
    """Deterministycznie wykonaj granicę worker/UI bez zmiany kodu produkcyjnego."""
    try:
        result = func()
    except BaseException as exc:  # noqa: BLE001
        if on_error is not None:
            on_error(exc)
        return
    on_done(result)


def _bind_after(view, mode: str, monkeypatch=None):  # noqa: ANN001
    if mode == "noop":
        view._safe_after = lambda delay_ms, callback: _noop_after(view, delay_ms, callback)
        return

    if monkeypatch is None:
        raise AssertionError("immediate mode requires monkeypatch")

    monkeypatch.setattr(
        "giclee_app.ui.katalog_view.run_async",
        _run_async_now,
    )
    view._safe_after = lambda delay_ms, callback: _immediate_after(view, delay_ms, callback)


def test_refresh_all_does_not_immediately_set_data_loaded(tmp_path: Path) -> None:
    root, view = _make_view(tmp_path)
    try:
        _bind_after(view, "noop")
        view._refresh_all()
        assert view._data_loaded is False
        assert view._refresh_in_progress is True
        assert view._pending_inventory is None
        assert view._pending_data_map is None
    finally:
        root.destroy()


def test_refresh_all_skips_second_start_while_in_progress(tmp_path: Path, monkeypatch) -> None:
    root, view = _make_view(tmp_path)
    events: list[str] = []
    try:
        monkeypatch.setattr(
            "giclee_app.ui.katalog_view.log_event",
            lambda name, **kwargs: events.append(name),  # noqa: ARG005
        )
        _bind_after(view, "noop")
        view._refresh_all()
        view._refresh_all()
        assert view._refresh_in_progress is True
        assert events.count("studio.katalog.refresh_pipeline.start") == 1
        assert "studio.katalog.refresh.skipped_in_progress" in events
    finally:
        root.destroy()


def test_refresh_pipeline_finalize_sets_loaded_and_clears_pending(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, view = _make_view(tmp_path)
    try:
        _bind_after(view, "immediate", monkeypatch)
        view._refresh_all()
        assert view._data_loaded is True
        assert view._refresh_in_progress is False
        assert view._pending_inventory is None
        assert view._pending_data_map is None
        assert view._last_inventory is not None
        assert view._last_data_map is not None
        assert isinstance(view._last_inventory, KatalogInventoryReport)
        assert isinstance(view._last_data_map, KatalogDataMap)
    finally:
        root.destroy()


def test_on_hide_resets_refresh_in_progress(tmp_path: Path) -> None:
    root, view = _make_view(tmp_path)
    try:
        _bind_after(view, "noop")
        view._refresh_all()
        assert view._refresh_in_progress is True
        view.on_hide()
        assert view._refresh_in_progress is False
        assert view._pending_inventory is None
        assert view._pending_data_map is None
    finally:
        root.destroy()


def test_refresh_pipeline_error_soft_fails(tmp_path: Path, monkeypatch) -> None:
    root, view = _make_view(tmp_path)
    events: list[str] = []
    statuses: list[str] = []

    def capture_status(msg: str) -> None:
        statuses.append(msg)

    view._on_status = capture_status
    try:
        monkeypatch.setattr(
            "giclee_app.ui.katalog_view.log_event",
            lambda name, **kwargs: events.append(name),  # noqa: ARG005
        )

        def boom(_root):  # noqa: ANN001
            raise RuntimeError("inventory boom")

        monkeypatch.setattr(
            "giclee_app.ui.katalog_view.build_katalog_inventory",
            boom,
        )
        _bind_after(view, "immediate", monkeypatch)
        view._refresh_all()
        assert view._refresh_in_progress is False
        assert view._data_loaded is False
        assert "studio.katalog.refresh_pipeline.error" in events
        assert any("przerwane" in s for s in statuses)
    finally:
        root.destroy()


def test_build_helpers_still_work_for_pipeline_data(tmp_path: Path) -> None:
    inv = build_katalog_inventory(tmp_path)
    dm = build_katalog_data_map(tmp_path)
    assert inv.katalog.root_exists is False
    assert dm.legacy_katalog is not None


def test_batch_row_fill_creates_complete_inventory_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, view = _make_view(tmp_path)
    try:
        _bind_after(view, "immediate", monkeypatch)
        view._refresh_all()
        assert view._inventory_frame is not None
        expected = len(inventory_display_rows(view._last_inventory))
        actual = len(view._inventory_frame.winfo_children())
        assert actual == expected
        assert expected > 0
    finally:
        root.destroy()


def test_deferred_done_logs_after_pipeline_not_at_start(tmp_path: Path, monkeypatch) -> None:
    root, view = _make_view(tmp_path)
    events: list[str] = []
    try:
        monkeypatch.setattr(
            "giclee_app.ui.katalog_view.log_event",
            lambda name, **kwargs: events.append(name),  # noqa: ARG005
        )
        _bind_after(view, "immediate", monkeypatch)
        view._refresh_all()
        assert "studio.katalog.refresh_pipeline.done" in events
        assert events.index("studio.katalog.refresh.deferred_done") > events.index(
            "studio.katalog.refresh_pipeline.start"
        )
        assert events.index("studio.katalog.refresh.deferred_done") >= events.index(
            "studio.katalog.refresh_pipeline.done"
        )
    finally:
        root.destroy()


def test_plan_dry_run_during_refresh_defers_without_sync_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    root, view = _make_view(tmp_path)
    events: list[str] = []
    statuses: list[str] = []

    def capture_status(msg: str) -> None:
        statuses.append(msg)

    view._on_status = capture_status
    try:
        monkeypatch.setattr(
            "giclee_app.ui.katalog_view.log_event",
            lambda name, **kwargs: events.append(name),  # noqa: ARG005
        )
        _bind_after(view, "noop")
        view._refresh_all()
        assert view._refresh_in_progress is True
        view._run_plan_dry_run()
        assert "studio.katalog.plan_dry_run.deferred_refresh_in_progress" in events
        assert any("odświeżają" in s for s in statuses)
        assert view._refresh_in_progress is True
    finally:
        root.destroy()


def test_plan_dry_run_without_data_starts_refresh_and_defers(tmp_path: Path, monkeypatch) -> None:
    root, view = _make_view(tmp_path)
    events: list[str] = []
    statuses: list[str] = []

    def capture_status(msg: str) -> None:
        statuses.append(msg)

    view._on_status = capture_status
    try:
        monkeypatch.setattr(
            "giclee_app.ui.katalog_view.log_event",
            lambda name, **kwargs: events.append(name),  # noqa: ARG005
        )
        view._last_inventory = None
        view._last_data_map = None
        view._data_loaded = False
        _bind_after(view, "noop")
        view._run_plan_dry_run()
        assert "studio.katalog.plan_dry_run.waiting_for_data" in events
        assert "studio.katalog.refresh_pipeline.start" in events
        assert any("odświeżają" in s for s in statuses)
        assert view._last_inventory is None
    finally:
        root.destroy()


def test_on_show_cache_hit_skips_refresh_when_data_loaded(tmp_path: Path, monkeypatch) -> None:
    root, view = _make_view(tmp_path)
    events: list[str] = []
    try:
        monkeypatch.setattr(
            "giclee_app.ui.katalog_view.log_event",
            lambda name, **kwargs: events.append(name),  # noqa: ARG005
        )
        view._data_loaded = True
        view._last_inventory = build_katalog_inventory(tmp_path)
        view._last_data_map = build_katalog_data_map(tmp_path)
        view.on_show(cache_hit=True)
        assert "studio.katalog.refresh.skipped_cache_fresh" in events
        assert "studio.katalog.refresh_pipeline.start" not in events
        assert view._refresh_in_progress is False
    finally:
        root.destroy()
