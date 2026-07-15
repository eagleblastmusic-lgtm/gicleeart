from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.launcher_background_services import LauncherBackgroundServices


class FakeAfterFn:
    def __init__(self) -> None:
        self.calls: list[tuple[int, Callable[[], None]]] = []
        self.should_raise_runtime_error = False

    def __call__(self, delay_ms: int, callback: Callable[[], None]) -> Any:
        if self.should_raise_runtime_error:
            raise RuntimeError("Tkinter is destroyed")
        self.calls.append((delay_ms, callback))
        return None


def test_public_constructor_signature() -> None:
    # 1. Rzeczywisty test publicznej sygnatury przy użyciu inspect
    sig = inspect.signature(LauncherBackgroundServices.__init__)
    params = list(sig.parameters.values())

    expected_names = [
        "self",
        "after_fn",
        "auto_rescan",
        "monthly_reminder",
        "monthly_plan_reminder",
        "shopify_orders",
        "accounting_orders",
        "daily_backup",
        "cure_notifications",
        "social_publisher",
        "weekly_content_reminder",
    ]

    assert len(params) == len(expected_names)
    for i, name in enumerate(expected_names):
        assert params[i].name == name

    # after_fn musi być POSITIONAL_OR_KEYWORD lub POSITIONAL_ONLY
    assert params[1].kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY)

    # Wszystkie callbacki muszą być KEYWORD_ONLY
    for param in params[2:]:
        assert param.kind == inspect.Parameter.KEYWORD_ONLY


def test_registration_and_firing_order() -> None:
    # 2. Rzeczywisty test expected firing order oraz registration order
    fake_after = FakeAfterFn()
    rescan_calls = 0

    def on_rescan() -> None:
        nonlocal rescan_calls
        rescan_calls += 1

    services = LauncherBackgroundServices(
        fake_after,
        auto_rescan=on_rescan,
        monthly_reminder=lambda: None,
        monthly_plan_reminder=lambda: None,
        shopify_orders=lambda: None,
        accounting_orders=lambda: None,
        daily_backup=lambda: None,
        cure_notifications=lambda: None,
        social_publisher=lambda: None,
        weekly_content_reminder=lambda: None,
    )
    services.start()

    # auto_rescan wywoływany synchronicznie na początku (direct call)
    assert rescan_calls == 1

    # Registration order: rejestracje w after_fn po wywołaniu start()
    # Oczekiwane opóźnienia w calls:
    # 1. recurrence auto-rescan — 3000
    # 2. monthly reminder — 1500
    # 3. monthly plan — 800
    # 4. Shopify — 30 000
    # 5. accounting — 35 000
    # 6. backup — 2000
    # 7. cure — 15 000
    # 8. social — 45 000
    # 9. weekly — 3000
    reg_delays = [call[0] for call in fake_after.calls]
    assert reg_delays == [3000, 1500, 800, 30_000, 35_000, 2000, 15_000, 45_000, 3000]

    # Initial firing order: wyjmujemy auto-rescan recurrence (pierwsze 3000 ms)
    initial_calls = []
    first_rescan_skipped = False
    for delay, cb in fake_after.calls:
        if delay == 3000 and hasattr(cb, "__func__") and cb.__func__ is services._run_auto_rescan.__func__ and not first_rescan_skipped:
            first_rescan_skipped = True
            continue
        initial_calls.append((delay, cb))

    # Sortowanie initial_calls według delay
    sorted_initial = sorted(initial_calls, key=lambda x: x[0])
    sorted_delays = [x[0] for x in sorted_initial]
    assert sorted_delays == [800, 1500, 2000, 3000, 15_000, 30_000, 35_000, 45_000]


@pytest.mark.parametrize(
    ("run_method_name", "trigger_attr", "interval_ms"),
    [
        ("_run_shopify_orders", "shopify_orders", 300_000),
        ("_run_accounting_orders", "accounting_orders", 300_000),
        ("_run_cure_notifications", "cure_notifications", 60_000),
        ("_run_social_publisher", "social_publisher", 60_000),
    ],
)
def test_recurring_services_behavior(run_method_name: str, trigger_attr: str, interval_ms: int) -> None:
    # 3. Parametryzowane testy wszystkich czterech usług recurring
    events: list[str] = []

    class TrackedAfterFn:
        def __init__(self) -> None:
            self.calls: list[tuple[int, Callable[[], None]]] = []
            self.should_raise_runtime_error = False
            self.should_raise_key_error = False

        def __call__(self, delay_ms: int, callback: Callable[[], None]) -> Any:
            events.append(f"after_{delay_ms}")
            if self.should_raise_runtime_error:
                raise RuntimeError("Tkinter error")
            if self.should_raise_key_error:
                raise KeyError("Other error")
            self.calls.append((delay_ms, callback))
            return None

    def trigger_cb() -> None:
        events.append("trigger_called")

    fake_after = TrackedAfterFn()
    callbacks = {
        "auto_rescan": lambda: None,
        "monthly_reminder": lambda: None,
        "monthly_plan_reminder": lambda: None,
        "shopify_orders": lambda: None,
        "accounting_orders": lambda: None,
        "daily_backup": lambda: None,
        "cure_notifications": lambda: None,
        "social_publisher": lambda: None,
        "weekly_content_reminder": lambda: None,
    }
    callbacks[trigger_attr] = trigger_cb

    services = LauncherBackgroundServices(fake_after, **callbacks)
    run_method = getattr(services, run_method_name)

    # A. Callback-before-reschedule
    events.clear()
    fake_after.calls.clear()
    run_method()
    assert events == ["trigger_called", f"after_{interval_ms}"]
    assert len(fake_after.calls) == 1
    assert fake_after.calls[0][0] == interval_ms

    # B. No reschedule on trigger exception
    def buggy_trigger() -> None:
        events.append("trigger_called")
        raise ZeroDivisionError("division by zero")

    setattr(services, trigger_attr, buggy_trigger)
    events.clear()
    fake_after.calls.clear()
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        run_method()
    assert events == ["trigger_called"]
    assert len(fake_after.calls) == 0

    # C. RuntimeError from recurring after
    setattr(services, trigger_attr, trigger_cb)
    fake_after.should_raise_runtime_error = True
    events.clear()
    fake_after.calls.clear()
    # Ignorowane, brak błędu
    run_method()
    assert events == ["trigger_called", f"after_{interval_ms}"]
    assert len(fake_after.calls) == 0

    # D. Other exception from recurring after
    fake_after.should_raise_runtime_error = False
    fake_after.should_raise_key_error = True
    events.clear()
    fake_after.calls.clear()
    with pytest.raises(KeyError, match="Other error"):
        run_method()
    assert events == ["trigger_called", f"after_{interval_ms}"]


def test_background_services_source_guards() -> None:
    # 4. Prawdziwe source guards schedulera poprzez AST
    services_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_background_services.py"
    source = services_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        # Sprawdzamy importy
        if isinstance(node, ast.Import):
            for name in node.names:
                forbidden = ["Komponenty", "tkinter", "customtkinter", "threading", "time", "json", "os", "pathlib"]
                for f in forbidden:
                    assert f not in name.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                forbidden = ["Komponenty", "tkinter", "customtkinter", "threading", "time", "json", "os", "pathlib"]
                for f in forbidden:
                    assert f not in node.module

        # Sprawdzamy niedozwolone wywołania, nazwy i definicje
        if isinstance(node, ast.Name):
            forbidden_names = [
                "sleep", "Thread", "open", "Path", "status_var", "messagebox",
                "show_toast", "notify", "stop", "cancel", "jitter", "retry", "backoff"
            ]
            assert node.id not in forbidden_names
        elif isinstance(node, ast.Attribute):
            assert node.attr not in [
                "sleep", "Thread", "open", "Path", "status_var", "messagebox",
                "show_toast", "notify", "stop", "cancel"
            ]
