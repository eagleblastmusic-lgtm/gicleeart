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
    # 2. Rzeczywisty test expected firing order oraz registration order z tożsamością callbacków
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

    assert rescan_calls == 1

    # Funkcja do sprawdzania tożsamości callbacków (bound/unbound)
    def is_match(cb: Any, target_method: Any) -> bool:
        if cb is target_method:
            return True
        self1 = getattr(cb, "__self__", None)
        func1 = getattr(cb, "__func__", None)
        self2 = getattr(target_method, "__self__", None)
        func2 = getattr(target_method, "__func__", None)
        if self1 is not None and self2 is not None:
            return self1 is self2 and func1 is func2
        return False

    # 1. Registration order
    expected_reg = [
        (3000, services._run_auto_rescan),
        (1500, services.monthly_reminder),
        (800, services.monthly_plan_reminder),
        (30_000, services._run_shopify_orders),
        (35_000, services._run_accounting_orders),
        (2000, services.daily_backup),
        (15_000, services._run_cure_notifications),
        (45_000, services._run_social_publisher),
        (3000, services.weekly_content_reminder),
    ]

    assert len(fake_after.calls) == len(expected_reg)
    for i, (delay, cb) in enumerate(fake_after.calls):
        exp_delay, exp_cb = expected_reg[i]
        assert delay == exp_delay
        assert is_match(cb, exp_cb), f"Callback mismatch at index {i}"

    # 2. Initial firing order (bez recurrence auto_rescan)
    initial_calls = []
    first_rescan_skipped = False
    for delay, cb in fake_after.calls:
        if delay == 3000 and is_match(cb, services._run_auto_rescan) and not first_rescan_skipped:
            first_rescan_skipped = True
            continue
        initial_calls.append((delay, cb))

    # Sortowanie initial_calls według delayu
    sorted_initial = sorted(initial_calls, key=lambda x: x[0])

    expected_firing = [
        (800, services.monthly_plan_reminder),
        (1500, services.monthly_reminder),
        (2000, services.daily_backup),
        (3000, services.weekly_content_reminder),
        (15_000, services._run_cure_notifications),
        (30_000, services._run_shopify_orders),
        (35_000, services._run_accounting_orders),
        (45_000, services._run_social_publisher),
    ]

    assert len(sorted_initial) == len(expected_firing)
    for i, (delay, cb) in enumerate(sorted_initial):
        exp_delay, exp_cb = expected_firing[i]
        assert delay == exp_delay
        assert is_match(cb, exp_cb), f"Firing order callback mismatch at index {i}"


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
    # 5. Prawdziwe source guards schedulera poprzez AST
    services_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_background_services.py"
    source = services_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_patterns = [
        "timer_id", "timer_ids", "after_id", "after_ids",
        "cancel", "cancelled", "cancellation", "retry", "retries", "backoff", "jitter"
    ]

    for node in ast.walk(tree):
        # 5.1. Zakazane definicje metod i funkcji
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.name not in ["stop", "cancel", "retry", "backoff", "jitter"]
            if not node.name.startswith("_"):
                assert node.name in ["__init__", "start"]

            # Argumenty funkcji
            for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                assert arg.arg.lower() not in forbidden_patterns

        # 5.2. Zakazane atrybuty i identyfikatory
        if isinstance(node, ast.Name):
            assert node.id.lower() not in forbidden_patterns
        elif isinstance(node, ast.Attribute):
            assert node.attr.lower() not in forbidden_patterns

        # Przypisania do self (self.attr = ...)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name) and target.value.id == "self":
                        assert target.attr.lower() not in forbidden_patterns

        # 5.3. Zakazane wywołania i importy
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
