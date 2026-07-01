"""Kreator przejścia DNR → JDG po przekroczeniu limitu kwartalnego."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from Komponenty._shared.tax_config import ceidg_deadline_days

from .constants import QUARTER_LABELS
from .models import DnrSettings
from .dates import quarter_from_iso
from .storage import load_settings, save_settings
from .summary_service import quarter_limit_revenue, sale_limit_delta, sales_for_quarter


MIGRATION_STEPS: tuple[tuple[str, str], ...] = (
    ("ceidg_submitted", "Złożyłem/am wniosek CEIDG (lub mam wpis)"),
    ("invoices_switched", "Faktury przełączone na tryb JDG zwolniona z VAT"),
    ("kpir_enabled", "KPiR włączone (tryb JDG — KPiR)"),
    ("dnr_imported", "Okres DNR zaimportowany do KPiR (wpisy zamknięte w DNR)"),
    ("zus_configured", "ZUS: ulga na start + data rejestracji JDG"),
)

# Próg „minimalnego” przekroczenia — przypadek brzegowy do ręcznej weryfikacji.
_BOUNDARY_EXCESS_PLN = 50.0
_BOUNDARY_EXCESS_PCT = 1.0


class MigrationCompleteError(ValueError):
    """Nie można zamknąć migracji — brakujące kroki lub nierozpatrzona weryfikacja."""


def _parse_iso(iso: str) -> date | None:
    raw = (iso or "").strip()[:10]
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _default_migration() -> dict[str, Any]:
    return {
        "status": "none",
        "effective_date": "",
        "ceidg_deadline": "",
        "steps": {key: False for key, _ in MIGRATION_STEPS},
        "completed_at": "",
        "first_exceed_date": "",
        "first_exceed_ceidg_deadline": "",
        "first_exceed_year": 0,
        "first_exceed_quarter": 0,
        "first_exceed_cumulative_pln": 0.0,
        "first_exceed_excess_pln": 0.0,
        "first_exceed_entry_id": "",
        "manual_review_required": False,
        "manual_review_reasons": [],
        "manual_review_acknowledged": False,
        "manual_review_ack_at": "",
        "manual_review_ack_note": "",
        "first_exceed_dismissed_at": "",
        "first_exceed_dismissed_note": "",
        "first_exceed_dismissed_snapshot": {},
    }


def normalize_migration(raw: dict[str, Any] | None) -> dict[str, Any]:
    out = _default_migration()
    if not raw:
        return out
    out["status"] = str(raw.get("status") or "none")
    out["effective_date"] = str(raw.get("effective_date") or "")
    out["ceidg_deadline"] = str(raw.get("ceidg_deadline") or "")
    steps = raw.get("steps") or {}
    out["steps"] = {key: bool(steps.get(key)) for key, _ in MIGRATION_STEPS}
    out["completed_at"] = str(raw.get("completed_at") or "")
    out["first_exceed_date"] = str(raw.get("first_exceed_date") or "")
    out["first_exceed_ceidg_deadline"] = str(raw.get("first_exceed_ceidg_deadline") or "")
    out["first_exceed_year"] = int(raw.get("first_exceed_year") or 0)
    out["first_exceed_quarter"] = int(raw.get("first_exceed_quarter") or 0)
    out["first_exceed_cumulative_pln"] = round(float(raw.get("first_exceed_cumulative_pln") or 0), 2)
    out["first_exceed_excess_pln"] = round(float(raw.get("first_exceed_excess_pln") or 0), 2)
    out["first_exceed_entry_id"] = str(raw.get("first_exceed_entry_id") or "")
    out["manual_review_required"] = bool(raw.get("manual_review_required"))
    reasons = raw.get("manual_review_reasons") or []
    out["manual_review_reasons"] = [str(r) for r in reasons] if isinstance(reasons, list) else []
    out["manual_review_acknowledged"] = bool(raw.get("manual_review_acknowledged"))
    out["manual_review_ack_at"] = str(raw.get("manual_review_ack_at") or "")
    out["manual_review_ack_note"] = str(raw.get("manual_review_ack_note") or "")
    out["first_exceed_dismissed_at"] = str(raw.get("first_exceed_dismissed_at") or "")
    out["first_exceed_dismissed_note"] = str(raw.get("first_exceed_dismissed_note") or "")
    snap = raw.get("first_exceed_dismissed_snapshot")
    out["first_exceed_dismissed_snapshot"] = dict(snap) if isinstance(snap, dict) else {}
    return out


def _persist_first_exceed(mig: dict[str, Any], event: dict[str, Any]) -> None:
    """Zapisuje pierwsze przekroczenie — nie kasuje się po zwrocie/korekcie."""
    if mig.get("first_exceed_date"):
        return
    mig["first_exceed_date"] = str(event.get("effective_date") or "")
    mig["first_exceed_ceidg_deadline"] = str(event.get("ceidg_deadline") or "")
    mig["first_exceed_year"] = int(event.get("year") or 0)
    mig["first_exceed_quarter"] = int(event.get("quarter") or 0)
    mig["first_exceed_cumulative_pln"] = round(float(event.get("cumulative_pln") or 0), 2)
    mig["first_exceed_excess_pln"] = round(float(event.get("excess_pln") or 0), 2)
    mig["first_exceed_entry_id"] = str(event.get("entry_id") or "")


def _sticky_exceed_active(mig: dict[str, Any]) -> bool:
    return bool(mig.get("first_exceed_date")) and mig.get("status") != "completed"


def obligation_context(year: int | None = None, quarter: int | None = None) -> dict[str, Any]:
    """Stan obowiązku JDG po pierwszym przekroczeniu (niezależnie od bieżącej sumy kwartału)."""
    today = date.today()
    y = year or today.year
    q = quarter or quarter_from_iso(today.isoformat())
    mig = normalize_migration(load_settings().migration)
    sticky = _sticky_exceed_active(mig)
    fe_y = int(mig.get("first_exceed_year") or 0)
    fe_q = int(mig.get("first_exceed_quarter") or 0)
    quarter_obligation = sticky and fe_y == y and fe_q == q
    return {
        "obligation_active": sticky,
        "quarter_obligation": quarter_obligation,
        "first_exceed_date": str(mig.get("first_exceed_date") or ""),
        "first_exceed_quarter": fe_q,
        "first_exceed_year": fe_y,
        "first_exceed_excess_pln": float(mig.get("first_exceed_excess_pln") or 0),
        "migration_status": str(mig.get("status") or "none"),
    }


def assess_manual_review(
    mig: dict[str, Any],
    *,
    current_event: dict[str, Any] | None,
    quarterly_limit: float,
) -> dict[str, Any]:
    """Przypadki brzegowe: przekroczenie było, ewidencja już nie — wymaga oceny człowieka."""
    if mig.get("status") == "completed" or not mig.get("first_exceed_date"):
        return {"required": False, "reasons": [], "message": ""}

    reasons: list[str] = []
    eff = mig.get("first_exceed_date") or "?"
    deadline = mig.get("first_exceed_ceidg_deadline") or mig.get("ceidg_deadline") or "?"
    excess = float(mig.get("first_exceed_excess_pln") or 0)
    limit = float(quarterly_limit or 0)

    if current_event is None:
        reasons.append(
            f"Ewidencja jest znowu poniżej limitu, ale {eff} było pierwsze przekroczenie — "
            f"obowiązek JDG mógł powstać od tej daty (CEIDG do {deadline}). "
            f"Korekta/zwrot w księdze nie cofa tego automatycznie."
        )
    elif current_event.get("effective_date") != mig.get("first_exceed_date"):
        reasons.append(
            f"Data bieżącego przekroczenia ({current_event.get('effective_date')}) "
            f"różni się od zapisanego pierwszego ({eff}) — sprawdź wpisy i daty."
        )

    if limit > 0 and excess > 0:
        pct = excess / limit * 100
        if excess <= _BOUNDARY_EXCESS_PLN or pct <= _BOUNDARY_EXCESS_PCT:
            reasons.append(
                f"Minimalne przekroczenie (+{excess:.2f} zł, {pct:.1f}% limitu) — "
                f"upewnij się, że to realna sprzedaż, nie błąd wpisu."
            )

    required = bool(reasons)
    message = reasons[0] if reasons else ""
    return {"required": required, "reasons": reasons, "message": message}


def _find_first_exceed_moment(year: int, *, limit: float) -> dict[str, Any] | None:
    """Pierwszy chronologiczny moment przekroczenia w roku (niezależnie od stanu końcowego kwartału)."""
    days = ceidg_deadline_days()
    for quarter in range(1, 5):
        sales = sorted(sales_for_quarter(year, quarter), key=lambda s: s.event_date)
        cumulative = 0.0
        for entry in sales:
            cumulative = round(cumulative + sale_limit_delta(entry), 2)
            if cumulative > limit:
                eff = _parse_iso(entry.event_date) or date.today()
                deadline = eff + timedelta(days=days)
                return {
                    "year": year,
                    "quarter": quarter,
                    "quarter_label": QUARTER_LABELS.get(quarter, f"Q{quarter}"),
                    "effective_date": eff.isoformat(),
                    "ceidg_deadline": deadline.isoformat(),
                    "cumulative_pln": cumulative,
                    "excess_pln": round(cumulative - limit, 2),
                    "quarterly_limit": limit,
                    "entry_id": str(entry.id or ""),
                }
    return None


def find_limit_exceed_event(year: int | None = None) -> dict[str, Any] | None:
    """Bieżące przekroczenie limitu w roku — pierwszy moment w kwartale, który dziś jest nad limitem."""
    settings = load_settings()
    limit = round(float(settings.quarterly_limit or 0), 2)
    if limit <= 0:
        return None
    y = year or date.today().year
    days = ceidg_deadline_days()
    for quarter in range(1, 5):
        if quarter_limit_revenue(y, quarter) <= limit:
            continue
        sales = sorted(sales_for_quarter(y, quarter), key=lambda s: s.event_date)
        cumulative = 0.0
        for entry in sales:
            cumulative = round(cumulative + sale_limit_delta(entry), 2)
            if cumulative > limit:
                eff = _parse_iso(entry.event_date) or date.today()
                deadline = eff + timedelta(days=days)
                return {
                    "year": y,
                    "quarter": quarter,
                    "quarter_label": QUARTER_LABELS.get(quarter, f"Q{quarter}"),
                    "effective_date": eff.isoformat(),
                    "ceidg_deadline": deadline.isoformat(),
                    "cumulative_pln": cumulative,
                    "excess_pln": round(cumulative - limit, 2),
                    "quarterly_limit": limit,
                    "entry_id": str(entry.id or ""),
                }
    return None


def sync_migration_status(settings: DnrSettings | None = None) -> DnrSettings:
    """Aktualizuje status migracji po wykryciu przekroczenia limitu."""
    settings = settings or load_settings()
    mig = normalize_migration(settings.migration)
    limit = round(float(settings.quarterly_limit or 0), 2)
    y = date.today().year
    event = find_limit_exceed_event(y)

    if event:
        mig["first_exceed_dismissed_at"] = ""
        mig["first_exceed_dismissed_note"] = ""
        mig["first_exceed_dismissed_snapshot"] = {}
        _persist_first_exceed(mig, event)
        if not mig["effective_date"]:
            mig["effective_date"] = event["effective_date"]
            mig["ceidg_deadline"] = event["ceidg_deadline"]
        if mig["status"] in ("none", ""):
            mig["status"] = "required"
    elif not mig.get("first_exceed_date") and limit > 0 and not mig.get("first_exceed_dismissed_at"):
        hist = _find_first_exceed_moment(y, limit=limit)
        if hist:
            _persist_first_exceed(mig, hist)
    if _sticky_exceed_active(mig) and not event:
        if not mig["effective_date"]:
            mig["effective_date"] = mig["first_exceed_date"]
            mig["ceidg_deadline"] = mig["first_exceed_ceidg_deadline"]
        if mig["status"] in ("none", ""):
            mig["status"] = "required" if not any(mig["steps"].values()) else "in_progress"
        elif mig["status"] == "required" and any(mig["steps"].values()):
            mig["status"] = "in_progress"

    review = assess_manual_review(mig, current_event=event, quarterly_limit=limit)
    mig["manual_review_required"] = review["required"]
    mig["manual_review_reasons"] = review["reasons"]

    settings.migration = mig
    return settings


def persist_migration_sync() -> DnrSettings:
    """Sync migracji + zapis do pliku (po zmianach w ewidencji sprzedaży)."""
    settings = sync_migration_status()
    save_settings(settings)
    return settings


def migration_overview(settings: DnrSettings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    before = normalize_migration(settings.migration)
    settings = sync_migration_status(settings)
    after = normalize_migration(settings.migration)
    if before != after:
        save_settings(settings)
    mig = normalize_migration(settings.migration)
    event = find_limit_exceed_event()
    review = assess_manual_review(
        mig, current_event=event, quarterly_limit=float(settings.quarterly_limit or 0),
    )
    steps_done = sum(1 for v in mig["steps"].values() if v)
    total_steps = len(MIGRATION_STEPS)
    today = date.today()
    deadline = _parse_iso(mig["ceidg_deadline"]) or _parse_iso(mig["first_exceed_ceidg_deadline"])
    ceidg_overdue = bool(deadline and today > deadline and mig["status"] != "completed")
    sticky = _sticky_exceed_active(mig)
    wizard_needed = mig["status"] in ("required", "in_progress") or sticky
    manual_review_alert = review["required"] and not mig.get("manual_review_acknowledged")

    if mig["status"] == "completed":
        level = "ok"
        message = "Migracja DNR → JDG zakończona."
    elif ceidg_overdue:
        level = "over"
        message = f"Termin CEIDG ({deadline.isoformat() if deadline else '?'}) minął — złóż wniosek jak najszybciej."
    elif review["required"] and not event:
        level = "caution"
        message = review["message"]
    elif mig["status"] == "required" or (sticky and event is None):
        message = (
            f"Przekroczono limit — działalność gospodarcza od {mig['effective_date'] or mig.get('first_exceed_date') or '?'}. "
            f"CEIDG do {mig['ceidg_deadline'] or mig.get('first_exceed_ceidg_deadline') or '?'}."
        )
        if not event:
            message += " (ewidencja teraz poniżej limitu — patrz weryfikacja ręczna.)"
        level = "warn"
    elif mig["status"] == "in_progress":
        message = f"Kreator migracji: {steps_done}/{total_steps} kroków ukończonych."
        level = "caution"
    else:
        message = ""
        level = "ok"

    try:
        from .kpir_import import preview_dnr_kpir_import

        import_preview = preview_dnr_kpir_import()
    except ImportError:
        import_preview = None

    rev_ok, rev_reason = _can_revert_first_exceed(settings, mig, current_event=event)

    return {
        "migration": mig,
        "exceed_event": event,
        "sticky_exceed": sticky,
        "manual_review_required": review["required"],
        "manual_review_alert": manual_review_alert,
        "manual_review_reasons": review["reasons"],
        "manual_review_message": review["message"],
        "manual_review_acknowledged": bool(mig.get("manual_review_acknowledged")),
        "can_revert_first_exceed": rev_ok,
        "revert_first_exceed_reason": rev_reason,
        "steps_done": steps_done,
        "steps_total": total_steps,
        "ceidg_overdue": ceidg_overdue,
        "level": level,
        "message": message,
        "wizard_needed": wizard_needed,
        "dnr_import_preview": {
            "until_date": import_preview.until_date if import_preview else "",
            "to_import": import_preview.to_import if import_preview else 0,
            "to_link": import_preview.to_link if import_preview else 0,
            "skipped": import_preview.skipped if import_preview else 0,
            "actionable": import_preview.actionable if import_preview else 0,
        } if import_preview else None,
    }


def set_migration_step(step_key: str, *, done: bool = True) -> DnrSettings:
    settings = sync_migration_status()
    mig = normalize_migration(settings.migration)
    if step_key == "dnr_imported" and done:
        from .kpir_import import preview_dnr_kpir_import

        pending = preview_dnr_kpir_import().actionable
        if pending > 0:
            raise MigrationCompleteError(
                f"Nie można oznaczyć importu jako ukończonego — pozostało {pending} wpisów DNR do przeniesienia lub powiązania."
            )
    if step_key in mig["steps"]:
        mig["steps"][step_key] = done
    if mig["status"] == "required":
        mig["status"] = "in_progress"
    settings.migration = mig
    save_settings(settings)
    return settings


def apply_invoices_jdg_mode() -> str:
    from Komponenty.dokumentysprzedazy.constants import BUSINESS_MODE_JDG, DEFAULT_FOOTNOTES
    from Komponenty.dokumentysprzedazy.invoice_builder import resolve_footnote
    from Komponenty.dokumentysprzedazy.storage import load_settings as load_inv_settings
    from Komponenty.dokumentysprzedazy.storage import save_settings as save_inv_settings

    inv = load_inv_settings()
    inv.seller.business_mode = BUSINESS_MODE_JDG  # type: ignore[assignment]
    inv.seller.footnotes_pl = resolve_footnote(BUSINESS_MODE_JDG, inv.seller.footnotes_pl, "pl")
    inv.seller.footnotes_en = resolve_footnote(BUSINESS_MODE_JDG, inv.seller.footnotes_en, "en")
    save_inv_settings(inv)
    set_migration_step("invoices_switched")
    return DEFAULT_FOOTNOTES[BUSINESS_MODE_JDG]["pl"]


def apply_kpir_jdg_start(*, effective_date: str = "", owner_name: str = "") -> dict[str, Any]:
    from Komponenty.kpir.models import KpirSettings
    from Komponenty.kpir.storage import load_settings as load_kpir_settings
    from Komponenty.kpir.storage import save_settings as save_kpir_settings
    from Komponenty.kpir.zus_service import apply_auto_zus

    dnr = load_settings()
    mig = normalize_migration(dnr.migration)
    reg_date = (effective_date or mig["effective_date"] or date.today().isoformat())[:10]
    kpir = load_kpir_settings()
    kpir.accounting_mode = "jdg_kpir"
    kpir.tax_form = "scale"
    kpir.zus_stage = "ulga_na_start"
    kpir.zus_manual_override = False
    kpir.jdg_registered_at = reg_date
    kpir.zus_stage_started_at = reg_date
    if owner_name and not kpir.seller_name:
        kpir.seller_name = owner_name
    elif dnr.owner_name and not kpir.seller_name:
        kpir.seller_name = dnr.owner_name
    apply_auto_zus(kpir)
    save_kpir_settings(kpir)
    set_migration_step("kpir_enabled")
    set_migration_step("zus_configured")
    return {"jdg_registered_at": reg_date, "zus_stage": kpir.zus_stage}


def _can_revert_first_exceed(
    settings: DnrSettings,
    mig: dict[str, Any],
    *,
    current_event: dict[str, Any] | None,
) -> tuple[bool, str]:
    if not mig.get("first_exceed_date"):
        return False, "Brak zapisanego przekroczenia do cofnięcia."
    if mig.get("status") == "completed":
        return False, "Migracja DNR → JDG jest zakończona — cofnięcie niedostępne."
    if any(mig["steps"].values()):
        return False, "Rozpoczęto kreator migracji — cofnij kroki ręcznie lub skontaktuj się z księgowym."
    if current_event is not None:
        return False, "Kwartał nadal przekracza limit — najpierw korekta ewidencji lub rejestracja JDG."
    return True, ""


def _clear_first_exceed_record(mig: dict[str, Any]) -> None:
    mig["first_exceed_date"] = ""
    mig["first_exceed_ceidg_deadline"] = ""
    mig["first_exceed_year"] = 0
    mig["first_exceed_quarter"] = 0
    mig["first_exceed_cumulative_pln"] = 0.0
    mig["first_exceed_excess_pln"] = 0.0
    mig["first_exceed_entry_id"] = ""
    mig["effective_date"] = ""
    mig["ceidg_deadline"] = ""
    mig["manual_review_required"] = False
    mig["manual_review_reasons"] = []
    mig["manual_review_acknowledged"] = False
    mig["manual_review_ack_at"] = ""
    mig["manual_review_ack_note"] = ""
    if mig.get("status") in ("required", "in_progress") and not any(mig["steps"].values()):
        mig["status"] = "none"


def revert_first_exceed(*, note: str = "") -> DnrSettings:
    """Ręczne cofnięcie zapisanego pierwszego przekroczenia (np. po zwrocie poniżej limitu)."""
    settings = sync_migration_status()
    mig = normalize_migration(settings.migration)
    event = find_limit_exceed_event()
    ok, reason = _can_revert_first_exceed(settings, mig, current_event=event)
    if not ok:
        raise MigrationCompleteError(reason)
    cleaned = (note or "").strip()
    if len(cleaned) < 3:
        raise MigrationCompleteError("Podaj uzasadnienie cofnięcia (min. 3 znaki).")
    mig["first_exceed_dismissed_snapshot"] = {
        "first_exceed_date": mig.get("first_exceed_date"),
        "first_exceed_ceidg_deadline": mig.get("first_exceed_ceidg_deadline"),
        "first_exceed_year": mig.get("first_exceed_year"),
        "first_exceed_quarter": mig.get("first_exceed_quarter"),
        "first_exceed_cumulative_pln": mig.get("first_exceed_cumulative_pln"),
        "first_exceed_excess_pln": mig.get("first_exceed_excess_pln"),
        "first_exceed_entry_id": mig.get("first_exceed_entry_id"),
        "effective_date": mig.get("effective_date"),
        "ceidg_deadline": mig.get("ceidg_deadline"),
    }
    mig["first_exceed_dismissed_at"] = datetime.now().isoformat(timespec="seconds")
    mig["first_exceed_dismissed_note"] = cleaned[:500]
    _clear_first_exceed_record(mig)
    settings.migration = mig
    save_settings(settings)
    return settings


def acknowledge_manual_review(*, note: str = "") -> DnrSettings:
    """Potwierdzenie ręcznej weryfikacji przypadku brzegowego (nie zamyka migracji JDG)."""
    settings = sync_migration_status()
    mig = normalize_migration(settings.migration)
    review = assess_manual_review(
        mig,
        current_event=find_limit_exceed_event(),
        quarterly_limit=float(settings.quarterly_limit or 0),
    )
    if not review["required"]:
        raise MigrationCompleteError("Brak aktywnej weryfikacji ręcznej do potwierdzenia.")
    cleaned = (note or "").strip()
    if len(cleaned) < 3:
        raise MigrationCompleteError("Podaj krótką notatkę (min. 3 znaki) — np. ustalenia z księgowym.")
    mig["manual_review_acknowledged"] = True
    mig["manual_review_ack_at"] = datetime.now().isoformat(timespec="seconds")
    mig["manual_review_ack_note"] = cleaned[:500]
    settings.migration = mig
    save_settings(settings)
    return settings


def complete_migration() -> DnrSettings:
    settings = sync_migration_status()
    mig = normalize_migration(settings.migration)
    review = assess_manual_review(
        mig,
        current_event=find_limit_exceed_event(),
        quarterly_limit=float(settings.quarterly_limit or 0),
    )
    if review["required"] and not mig.get("manual_review_acknowledged"):
        raise MigrationCompleteError(
            "Najpierw potwierdź weryfikację ręczną przypadku brzegowego (notatka w kreatorze migracji)."
        )
    missing = [label for key, label in MIGRATION_STEPS if not mig["steps"].get(key)]
    if missing:
        raise MigrationCompleteError(
            "Ukończ wszystkie kroki migracji przed zamknięciem:\n• " + "\n• ".join(missing)
        )
    from .kpir_import import preview_dnr_kpir_import

    pending = preview_dnr_kpir_import().actionable
    if pending > 0:
        raise MigrationCompleteError(
            f"Pozostało {pending} wpisów DNR do importu do KPiR (sprzedaż/koszty przed datą JDG). "
            "Uruchom import w kreatorze migracji."
        )
    if mig["status"] not in ("required", "in_progress"):
        raise MigrationCompleteError("Brak aktywnej migracji do zamknięcia.")
    mig["status"] = "completed"
    mig["completed_at"] = datetime.now().isoformat(timespec="seconds")
    for key, _ in MIGRATION_STEPS:
        mig["steps"][key] = True
    settings.migration = mig
    save_settings(settings)
    return settings
