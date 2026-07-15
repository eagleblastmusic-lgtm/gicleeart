"""Kontrakt LC-1: jawny composition root klasycznego launchera."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app import launcher
from giclee_app import category_launcher
from giclee_app import dragdrop_category_launcher
from giclee_app import options_category_launcher
from giclee_app import styled_category_launcher


class _FakeRoot:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def withdraw(self) -> None:
        self._events.append("withdraw")

    def deiconify(self) -> None:
        self._events.append("deiconify")

    def mainloop(self) -> None:
        self._events.append("mainloop")


def _install_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
) -> _FakeRoot:
    root = _FakeRoot(events)
    fake_tkdnd = SimpleNamespace(TkinterDnD=SimpleNamespace(Tk=lambda: root))
    monkeypatch.setitem(sys.modules, "tkinterdnd2", fake_tkdnd)

    from giclee_app import splash_screen

    def run_splash_then(_root: object, callback: Callable[[], None]) -> None:
        events.append("splash")
        callback()

    monkeypatch.setattr(splash_screen, "run_splash_then", run_splash_then)
    return root


def test_final_launcher_mro_is_unchanged() -> None:
    assert dragdrop_category_launcher.DragDropCategoryGicleeApp.__mro__ == (
        dragdrop_category_launcher.DragDropCategoryGicleeApp,
        options_category_launcher.OptionsCategoryGicleeApp,
        styled_category_launcher.StyledCategoryGicleeApp,
        category_launcher.CategoryGicleeApp,
        launcher.GicleeApp,
        object,
    )


@pytest.mark.parametrize(
    ("module", "expected_factory"),
    [
        (category_launcher, category_launcher.CategoryGicleeApp),
        (styled_category_launcher, styled_category_launcher.StyledCategoryGicleeApp),
        (options_category_launcher, options_category_launcher.OptionsCategoryGicleeApp),
        (dragdrop_category_launcher, dragdrop_category_launcher.DragDropCategoryGicleeApp),
    ],
)
def test_layer_entrypoints_pass_factory_without_runtime_class_replacement(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    expected_factory: object,
) -> None:
    captured: list[object] = []
    original_class = launcher.GicleeApp

    def fake_main(*, app_factory: object = None) -> None:
        captured.append(app_factory)

    monkeypatch.setattr(module._launcher, "main", fake_main)
    module.main()

    assert captured == [expected_factory]
    assert launcher.GicleeApp is original_class


@pytest.mark.parametrize(
    "filename",
    [
        "category_launcher.py",
        "styled_category_launcher.py",
        "options_category_launcher.py",
        "dragdrop_category_launcher.py",
    ],
)
def test_layer_sources_do_not_assign_launcher_class(filename: str) -> None:
    source = (Path(__file__).resolve().parents[1] / "giclee_app" / filename).read_text(
        encoding="utf-8"
    )
    assert "_launcher.GicleeApp =" not in source
    assert "original_class = _launcher.GicleeApp" not in source
    assert "_launcher.main(app_factory=" in source


def test_launcher_main_uses_explicit_factory_once_after_splash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    root = _install_fake_runtime(monkeypatch, events)
    calls: list[object] = []

    def factory(received_root: object) -> object:
        events.append("factory")
        calls.append(received_root)
        return object()

    launcher.main(app_factory=factory)

    assert calls == [root]
    assert events == ["withdraw", "splash", "factory", "deiconify", "mainloop"]


def test_launcher_main_defaults_to_base_launcher_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    root = _install_fake_runtime(monkeypatch, events)
    calls: list[object] = []

    def base_factory(received_root: object) -> object:
        events.append("factory")
        calls.append(received_root)
        return object()

    monkeypatch.setattr(launcher, "GicleeApp", base_factory)
    launcher.main()

    assert calls == [root]
    assert events == ["withdraw", "splash", "factory", "deiconify", "mainloop"]


def test_package_main_still_targets_final_dragdrop_entrypoint() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "giclee_app" / "__main__.py"
    ).read_text(encoding="utf-8")
    assert "from .dragdrop_category_launcher import main" in source
    assert "studio_preview" not in source


def test_launcher_uses_background_services_scheduler() -> None:
    # 1. Sprawdzenie, czy launcher.py importuje LauncherBackgroundServices
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")
    assert "from .launcher_background_services import LauncherBackgroundServices" in source

    # 2. Sprawdzenie, czy w __init__ jest tworzony i startowany scheduler
    assert "self._background_services = LauncherBackgroundServices(" in source
    assert "self._background_services.start()" in source

    # 3. Sprawdzenie, czy w launcher.py nie ma już bezpośrednich initial schedules
    # (powinny być zastąpione schedulerem)
    assert "self.root.after(1500, self._check_monthly_reminder)" not in source
    assert "self.root.after(800, self._check_monthly_plan_reminder)" not in source
    assert "self.root.after(30_000, self._poll_orders_from_shopify)" not in source
    assert "self.root.after(35_000, self._poll_accounting_orders)" not in source
    assert "self.root.after(2000, self._run_daily_backup)" not in source
    assert "self.root.after(15_000, self._check_cure_done_notifications)" not in source
    assert "self.root.after(45_000, self._poll_cykl_publisher)" not in source
    assert "self.root.after(3000, self._check_cykl_weekly_reminder)" not in source

    # 4. Sprawdzenie, czy metody cykliczne nie mają już własnego trailing after()
    # (muszą być czystymi workerami wywoływanymi raz przez scheduler)
    import re
    # Metoda _auto_rescan
    auto_rescan_body = re.search(r"def _auto_rescan\(self\)[^:]*:(.*?)(?=def|$)", source, re.DOTALL)
    assert auto_rescan_body is not None
    assert "self.root.after(" not in auto_rescan_body.group(1)

    # Metoda _poll_orders_from_shopify
    shopify_body = re.search(r"def _poll_orders_from_shopify\(self\)[^:]*:(.*?)(?=def|$)", source, re.DOTALL)
    assert shopify_body is not None
    assert "self.root.after(5 * 60 * 1000" not in shopify_body.group(1)

    # Metoda _poll_accounting_orders
    accounting_body = re.search(r"def _poll_accounting_orders\(self\)[^:]*:(.*?)(?=def|$)", source, re.DOTALL)
    assert accounting_body is not None
    assert "self.root.after(5 * 60 * 1000" not in accounting_body.group(1)

    # Metoda _check_cure_done_notifications
    cure_body = re.search(r"def _check_cure_done_notifications\(self\)[^:]*:(.*?)(?=def|$)", source, re.DOTALL)
    assert cure_body is not None
    assert "self.root.after(60_000" not in cure_body.group(1)

    # Metoda _poll_cykl_publisher
    publisher_body = re.search(r"def _poll_cykl_publisher\(self\)[^:]*:(.*?)(?=def|$)", source, re.DOTALL)
    assert publisher_body is not None
    assert "self.root.after(60_000" not in publisher_body.group(1)


def test_daemon_threads_existence_in_launcher() -> None:
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")

    # Powinno istnieć dokładnie 6 wątków daemon=True w metodach (w tym watch_proc w launcher.py):
    # 1. _run_daily_backup
    # 2. _check_cure_done_notifications
    # 3. _poll_orders_from_shopify
    # 4. _poll_accounting_orders
    # 5. _poll_cykl_publisher
    # 6. _watch_proc (watcher subprocessu)
    daemon_thread_count = source.count("daemon=True")
    assert daemon_thread_count == 6


def test_studio_does_not_import_background_services() -> None:
    studio_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    if studio_path.is_file():
        source = studio_path.read_text(encoding="utf-8")
        assert "launcher_background_services" not in source
        assert "LauncherBackgroundServices" not in source


def test_excluded_timers_remain_untouched() -> None:
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")

    # after_idle canvas focus
    assert "self.canvas.focus_set()" in source or "self.root.after_idle(self._focus_tiles_canvas)" in source
    # after_idle wheel
    assert "after_idle(self._flush_tiles_canvas_wheel)" in source
    # after(500, ...) in task generator delay
    assert "self.root.after(500, lambda: open_tasks_generator" in source
    # win.after(2000, _auto) in log preview
    assert "win.after(2000, _auto)" in source


def test_monthly_reminders_remain_distinct_methods() -> None:
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")

    # Obie metody muszą istnieć
    assert "def _check_monthly_reminder" in source
    assert "def _check_monthly_plan_reminder" in source


def test_lazy_imports_remain_inside_worker_methods() -> None:
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"

    # Importy z Komponenty nie mogą być na poziomie modułu (poza try-except geometry center)
    import ast
    node = ast.parse(launcher_path.read_text(encoding="utf-8"))
    for item in node.body:
        if isinstance(item, ast.ImportFrom):
            if item.module:
                assert not item.module.startswith("Komponenty")
        elif isinstance(item, ast.Import):
            for name in item.names:
                assert not name.name.startswith("Komponenty")
