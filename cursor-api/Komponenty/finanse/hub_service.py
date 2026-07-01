"""Dane zbiorcze dla ekranu Hub Finanse."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from Komponenty._shared.compliance_ui import compliance_monitors
from Komponenty.kpir.month_checklist import ChecklistItem, build_month_checklist


@dataclass
class FinanceHubData:
    year: int
    month: int
    dnr_limit_message: str = ""
    dnr_limit_level: str = "ok"
    dnr_quarter_revenue: float = 0.0
    dnr_quarter_limit: float = 0.0
    dnr_quarter_pct: float = 0.0
    vat_message: str = ""
    vat_level: str = "ok"
    vat_turnover_pln: float = 0.0
    vat_threshold_pln: float = 0.0
    vat_pct: float = 0.0
    sales_flow: dict[str, Any] = field(default_factory=dict)
    compliance: list[dict[str, Any]] = field(default_factory=list)
    checklist_items: list[ChecklistItem] = field(default_factory=list)
    checklist_blocking: int = 0
    checklist_warnings: int = 0
    migration_alert: str = ""
    can_revert_exceed: bool = False
    payment_message: str = ""
    payment_active: bool = False


def load_finance_hub(*, year: int | None = None, month: int | None = None) -> FinanceHubData:
    today = date.today()
    y = year or today.year
    m = month or today.month
    hub = FinanceHubData(year=y, month=m)

    try:
        from Komponenty.dnr.summary_service import dashboard_summary
        from Komponenty.dnr.migration_service import migration_overview

        dnr = dashboard_summary(y)
        hub.dnr_limit_message = str(dnr.get("message") or "")
        hub.dnr_limit_level = str(dnr.get("level") or "ok")
        hub.dnr_quarter_revenue = float(dnr.get("quarter_revenue") or 0)
        hub.dnr_quarter_limit = float(dnr.get("quarterly_limit") or 0)
        hub.dnr_quarter_pct = float(dnr.get("pct") or 0)
        mig = migration_overview()
        if mig.get("manual_review_alert"):
            hub.migration_alert = str(mig.get("manual_review_message") or "Wymagana weryfikacja przekroczenia limitu.")
        hub.can_revert_exceed = bool(mig.get("can_revert_first_exceed"))
    except Exception:
        pass

    try:
        from Komponenty._shared.vat_exemption import vat_exemption_status
        from Komponenty.kpir.storage import load_settings

        kpir = load_settings()
        vat = vat_exemption_status(y, jdg_registered_at=kpir.jdg_registered_at)
        hub.vat_message = str(vat.get("message") or "")
        hub.vat_level = str(vat.get("level") or "ok")
        hub.vat_turnover_pln = float(vat.get("turnover_pln") or 0)
        hub.vat_threshold_pln = float(vat.get("threshold_pln") or 0)
        hub.vat_pct = float(vat.get("pct") or 0)
    except Exception:
        pass

    try:
        from Komponenty.kpir.flow_status import sales_flow_summary

        hub.sales_flow = sales_flow_summary(year=y).to_dict()
    except Exception:
        pass

    hub.compliance = compliance_monitors(y)
    cl = build_month_checklist(y, m)
    hub.checklist_items = cl.items[:20]
    hub.checklist_blocking = cl.blocking_count
    hub.checklist_warnings = cl.warning_count

    try:
        from Komponenty.kpir.payment_due import upcoming_payment_summary
        from Komponenty.kpir.storage import load_settings as load_kpir_settings

        pay = upcoming_payment_summary(load_kpir_settings(), ref_year=y, ref_month=m)
        hub.payment_active = bool(pay.get("active"))
        hub.payment_message = str(pay.get("message") or "")
    except Exception:
        pass

    return hub
