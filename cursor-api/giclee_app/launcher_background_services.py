from collections.abc import Callable
from typing import Any, Protocol


class AfterScheduler(Protocol):
    def __call__(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> Any:
        ...


class LauncherBackgroundServices:
    def __init__(
        self,
        after_fn: AfterScheduler,
        *,
        auto_rescan: Callable[[], None],
        monthly_reminder: Callable[[], None],
        monthly_plan_reminder: Callable[[], None],
        shopify_orders: Callable[[], None],
        accounting_orders: Callable[[], None],
        daily_backup: Callable[[], None],
        cure_notifications: Callable[[], None],
        social_publisher: Callable[[], None],
        weekly_content_reminder: Callable[[], None],
    ) -> None:
        self.after_fn = after_fn
        self.auto_rescan = auto_rescan
        self.monthly_reminder = monthly_reminder
        self.monthly_plan_reminder = monthly_plan_reminder
        self.shopify_orders = shopify_orders
        self.accounting_orders = accounting_orders
        self.daily_backup = daily_backup
        self.cure_notifications = cure_notifications
        self.social_publisher = social_publisher
        self.weekly_content_reminder = weekly_content_reminder

    def start(self) -> None:
        """Uruchamia planowanie wszystkich usług tła."""
        # 1. auto_rescan — direct synchronous call
        self._run_auto_rescan()

        # 2. monthly_reminder — initial after(1500)
        self.after_fn(1500, self.monthly_reminder)

        # 3. monthly_plan_reminder — initial after(800)
        self.after_fn(800, self.monthly_plan_reminder)

        # 4. shopify_orders — initial after(30_000)
        self.after_fn(30_000, self._run_shopify_orders)

        # 5. accounting_orders — initial after(35_000)
        self.after_fn(35_000, self._run_accounting_orders)

        # 6. daily_backup — initial after(2000)
        self.after_fn(2000, self.daily_backup)

        # 7. cure_notifications — initial after(15_000)
        self.after_fn(15_000, self._run_cure_notifications)

        # 8. social_publisher — initial after(45_000)
        self.after_fn(45_000, self._run_social_publisher)

        # 9. weekly_content_reminder — initial after(3000)
        self.after_fn(3000, self.weekly_content_reminder)

    def _run_auto_rescan(self) -> None:
        try:
            self.auto_rescan()
        finally:
            self.after_fn(3000, self._run_auto_rescan)

    def _run_shopify_orders(self) -> None:
        self.shopify_orders()
        try:
            self.after_fn(300_000, self._run_shopify_orders)
        except RuntimeError:
            pass

    def _run_accounting_orders(self) -> None:
        self.accounting_orders()
        try:
            self.after_fn(300_000, self._run_accounting_orders)
        except RuntimeError:
            pass

    def _run_cure_notifications(self) -> None:
        self.cure_notifications()
        try:
            self.after_fn(60_000, self._run_cure_notifications)
        except RuntimeError:
            pass

    def _run_social_publisher(self) -> None:
        self.social_publisher()
        try:
            self.after_fn(60_000, self._run_social_publisher)
        except RuntimeError:
            pass
