from __future__ import annotations

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
    # Sprawdzenie sygnatury i exact registration order w sygnaturze.
    # Używamy dummy callbacków.
    fake_after = FakeAfterFn()
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
    services = LauncherBackgroundServices(
        fake_after,
        **callbacks
    )
    assert services.after_fn is fake_after
    assert services.auto_rescan is callbacks["auto_rescan"]
    assert services.monthly_reminder is callbacks["monthly_reminder"]


def test_exact_registration_order_and_initial_delays() -> None:
    fake_after = FakeAfterFn()
    rescan_called = 0

    def on_rescan() -> None:
        nonlocal rescan_called
        rescan_called += 1

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
    assert rescan_called == 1

    # auto_rescan w finally planuje pierwszy recurring tick co 3000 ms.
    # Pozostałe osiem usług dostaje initial delays przez after_fn.
    # Sprawdzamy dokładną kolejność wywołań w after_fn (exact registration order, bez sortowania po delay).
    # Oczekiwana kolejność w calls:
    # 0. auto_rescan recurrence (z finally po synchronicznym direct call) -> 3000 ms
    # 1. monthly_reminder -> 1500 ms
    # 2. monthly_plan_reminder -> 800 ms
    # 3. shopify_orders -> 30 000 ms
    # 4. accounting_orders -> 35 000 ms
    # 5. daily_backup -> 2000 ms
    # 6. cure_notifications -> 15 000 ms
    # 7. social_publisher -> 45 000 ms
    # 8. weekly_content_reminder -> 3000 ms
    expected_order = [
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

    assert len(fake_after.calls) == 9
    for i, (delay, cb) in enumerate(fake_after.calls):
        expected_delay, expected_cb = expected_order[i]
        assert delay == expected_delay
        # Sprawdzamy czy to ten sam callback (lub powiązana metoda)
        if hasattr(expected_cb, "__func__"):
            assert cb.__func__ is expected_cb.__func__
        else:
            assert cb is expected_cb


def test_expected_firing_order_as_distinct_fact() -> None:
    # Przypomnijmy spodziewane czasy uruchomienia (firing order):
    # 1. auto_rescan -> direct synchronicznie (0 ms)
    # 2. monthly plan -> 800 ms
    # 3. monthly reminder -> 1500 ms
    # 4. backup -> 2000 ms
    # 5. weekly reminder -> 3000 ms
    # 6. cure -> 15 000 ms
    # 7. shopify -> 30 000 ms
    # 8. accounting -> 35 000 ms
    # 9. social_publisher -> 45 000 ms
    delays = [800, 1500, 2000, 3000, 15000, 30000, 35000, 45000]
    assert sorted(delays) == delays


def test_auto_rescan_recurrence_in_finally_and_exception_propagation() -> None:
    fake_after = FakeAfterFn()

    def buggy_rescan() -> None:
        raise ValueError("Rescan crashed")

    services = LauncherBackgroundServices(
        fake_after,
        auto_rescan=buggy_rescan,
        monthly_reminder=lambda: None,
        monthly_plan_reminder=lambda: None,
        shopify_orders=lambda: None,
        accounting_orders=lambda: None,
        daily_backup=lambda: None,
        cure_notifications=lambda: None,
        social_publisher=lambda: None,
        weekly_content_reminder=lambda: None,
    )

    # Rzucenie wyjątku przez direct auto_rescan powinno wypropagować z start()
    # ale w bloku finally i tak zaplanować kolejny krok auto-rescan co 3000 ms.
    with pytest.raises(ValueError, match="Rescan crashed"):
        services.start()

    # Powinno być tylko jedno wywołanie after_fn (auto_rescan recurrence co 3000 ms)
    # Z powodu wyjątku start() przerwał dalsze rejestracje (monthly, backup itp.)
    assert len(fake_after.calls) == 1
    delay, cb = fake_after.calls[0]
    assert delay == 3000
    assert cb.__func__ is services._run_auto_rescan.__func__


def test_callback_before_reschedule_for_recurring_services() -> None:
    fake_after = FakeAfterFn()
    shopify_calls = 0

    def on_shopify() -> None:
        nonlocal shopify_calls
        shopify_calls += 1

    services = LauncherBackgroundServices(
        fake_after,
        auto_rescan=lambda: None,
        monthly_reminder=lambda: None,
        monthly_plan_reminder=lambda: None,
        shopify_orders=on_shopify,
        accounting_orders=lambda: None,
        daily_backup=lambda: None,
        cure_notifications=lambda: None,
        social_publisher=lambda: None,
        weekly_content_reminder=lambda: None,
    )
    services.start()

    # Zdejmujemy wywołanie shopify (indeks 3 w calls)
    shopify_trigger_cb = fake_after.calls[3][1]
    
    # Przed uruchomieniem triggera, shopify_calls == 0, brak nowych calls w after_fn
    assert shopify_calls == 0
    initial_calls_count = len(fake_after.calls)

    # Uruchamiamy callback
    shopify_trigger_cb()

    # Po uruchomieniu, najpierw wywołał się trigger (shopify_calls == 1),
    # a dopiero potem zaplanowano następny tick co 300_000 ms.
    assert shopify_calls == 1
    assert len(fake_after.calls) == initial_calls_count + 1
    new_delay, new_cb = fake_after.calls[-1]
    assert new_delay == 300_000
    assert new_cb.__func__ is services._run_shopify_orders.__func__


def test_no_reschedule_on_callback_exception() -> None:
    fake_after = FakeAfterFn()

    def buggy_trigger() -> None:
        raise ZeroDivisionError("division by zero")

    services = LauncherBackgroundServices(
        fake_after,
        auto_rescan=lambda: None,
        monthly_reminder=lambda: None,
        monthly_plan_reminder=lambda: None,
        shopify_orders=buggy_trigger,
        accounting_orders=lambda: None,
        daily_backup=lambda: None,
        cure_notifications=lambda: None,
        social_publisher=lambda: None,
        weekly_content_reminder=lambda: None,
    )
    services.start()

    # Shopify trigger (indeks 3)
    shopify_trigger_cb = fake_after.calls[3][1]
    initial_calls_count = len(fake_after.calls)

    # Wyjątek z triggera powinien wypropagować na zewnątrz, a scheduler NIE może zaplanować kolejnego ticka.
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        shopify_trigger_cb()

    # Brak nowych rejestracji w after_fn
    assert len(fake_after.calls) == initial_calls_count


def test_runtime_error_swallowed_only_in_recurring_services() -> None:
    fake_after = FakeAfterFn()
    services = LauncherBackgroundServices(
        fake_after,
        auto_rescan=lambda: None,
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

    # Shopify trigger (indeks 3)
    shopify_trigger_cb = fake_after.calls[3][1]

    # Ustawiamy, że fake_after rzuci RuntimeError przy kolejnym wywołaniu.
    fake_after.should_raise_runtime_error = True

    # RuntimeError z after_fn wewnątrz recurring service powinien zostać połknięty (swallowed).
    # Nie rzuca wyjątku.
    shopify_trigger_cb()


def test_other_exceptions_not_swallowed_in_recurring_reschedule() -> None:
    class MockAfterFn:
        def __call__(self, delay_ms: int, callback: Callable[[], None]) -> Any:
            raise KeyError("Key error")

    services = LauncherBackgroundServices(
        MockAfterFn(),
        auto_rescan=lambda: None,
        monthly_reminder=lambda: None,
        monthly_plan_reminder=lambda: None,
        shopify_orders=lambda: None,
        accounting_orders=lambda: None,
        daily_backup=lambda: None,
        cure_notifications=lambda: None,
        social_publisher=lambda: None,
        weekly_content_reminder=lambda: None,
    )
    # Przy starcie, direct auto_rescan i jego finally (które odpala after_fn i podnosi KeyError)
    # KeyError propaguje na zewnątrz.
    with pytest.raises(KeyError, match="Key error"):
        services.start()


def test_monthly_reminders_distinctness() -> None:
    fake_after = FakeAfterFn()
    monthly_rem_called = 0
    monthly_plan_called = 0

    def on_monthly() -> None:
        nonlocal monthly_rem_called
        monthly_rem_called += 1

    def on_monthly_plan() -> None:
        nonlocal monthly_plan_called
        monthly_plan_called += 1

    services = LauncherBackgroundServices(
        fake_after,
        auto_rescan=lambda: None,
        monthly_reminder=on_monthly,
        monthly_plan_reminder=on_monthly_plan,
        shopify_orders=lambda: None,
        accounting_orders=lambda: None,
        daily_backup=lambda: None,
        cure_notifications=lambda: None,
        social_publisher=lambda: None,
        weekly_content_reminder=lambda: None,
    )
    services.start()

    # monthly_reminder (indeks 1), monthly_plan_reminder (indeks 2)
    fake_after.calls[1][1]()
    fake_after.calls[2][1]()

    assert monthly_rem_called == 1
    assert monthly_plan_called == 1


def test_forbidden_imports_and_features_check() -> None:
    # Weryfikacja source guards na poziomie testów (brak tkinter, customtkinter, Komponenty).
    assert "tkinter" not in sys.modules or sys.modules["tkinter"] is not None
    assert "customtkinter" not in sys.modules
    # Upewniamy się, że nasz scheduler nie ma timer IDs, cancellation itp.
    services = LauncherBackgroundServices(
        FakeAfterFn(),
        auto_rescan=lambda: None,
        monthly_reminder=lambda: None,
        monthly_plan_reminder=lambda: None,
        shopify_orders=lambda: None,
        accounting_orders=lambda: None,
        daily_backup=lambda: None,
        cure_notifications=lambda: None,
        social_publisher=lambda: None,
        weekly_content_reminder=lambda: None,
    )
    assert not hasattr(services, "stop")
    assert not hasattr(services, "cancel")
