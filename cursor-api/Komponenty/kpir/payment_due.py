"""Orientacyjne kwoty do wpłaty ZUS / PIT przy terminach kalendarza."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty._shared.pit_deductions import health_from_income_monthly
from Komponenty._shared.tax_config import compliance
from Komponenty._shared.zus_stages import health_minimum_monthly

from .models import KpirSettings
from .zus_service import is_jdg_mode, resolve_zus_for_pit


def _parse_iso(iso: str) -> date | None:
    try:
        return date.fromisoformat(iso[:10])
    except (TypeError, ValueError):
        return None


def period_before_due(due_year: int, due_month: int) -> tuple[int, int]:
    """Za termin w due_year/due_month — okres rozliczeniowy to poprzedni miesiąc."""
    if due_month == 1:
        return due_year - 1, 12
    return due_year, due_month - 1


def _period_active_jdg(settings: KpirSettings, period_year: int, period_month: int) -> bool:
    if not is_jdg_mode(settings):
        return False
    reg = _parse_iso(settings.jdg_registered_at)
    if not reg:
        return False
    return date(period_year, period_month, 1) >= date(reg.year, reg.month, 1)


def _monthly_income(settings: KpirSettings, year: int, month: int) -> float:
    try:
        from .summary_service import monthly_summary

        return float(monthly_summary(year, month).get("income") or 0)
    except Exception:
        return 0.0


def health_payment_monthly(settings: KpirSettings, monthly_income: float) -> float:
    """Składka zdrowotna do wpłaty (max minimum vs % dochodu)."""
    form = settings.tax_form or "scale"
    if form == "lump_sum":
        return round(health_minimum_monthly(form), 2)
    floor = float(settings.health_insurance_monthly or 0)
    if floor <= 0:
        floor = health_minimum_monthly(form)
    calc = health_from_income_monthly(monthly_income, form)
    return round(max(floor, calc), 2)


def zus_obligation_for_period(
    settings: KpirSettings,
    period_year: int,
    period_month: int,
) -> dict[str, Any] | None:
    """Kwoty ZUS za okres (miesiąc poprzedni względem terminu wpłaty)."""
    if not _period_active_jdg(settings, period_year, period_month):
        return None

    income = _monthly_income(settings, period_year, period_month)
    zus = resolve_zus_for_pit(settings, monthly_income=income)
    social = float(zus.get("zus_social_monthly") or 0)
    fp_fs = float(zus.get("fp_fs_monthly") or 0)
    health = health_payment_monthly(settings, income)
    total = round(social + fp_fs + health, 2)

    parts: list[str] = []
    if social > 0:
        parts.append(f"społeczne {social:.2f} zł")
    if fp_fs > 0:
        parts.append(f"FP/FS {fp_fs:.2f} zł")
    if health > 0:
        parts.append(f"zdrowotna {health:.2f} zł")
    if not parts and settings.zus_stage == "ulga_na_start":
        parts.append(f"zdrowotna {health:.2f} zł")

    return {
        "period_year": period_year,
        "period_month": period_month,
        "income_pln": round(income, 2),
        "social_pln": round(social, 2),
        "fp_fs_pln": round(fp_fs, 2),
        "health_pln": round(health, 2),
        "total_pln": total,
        "summary": " + ".join(parts) if parts else "0,00 zł",
        "detail": (
            f"Za {period_month:02d}.{period_year}"
            + (f" (dochód {income:.2f} zł)" if income else "")
            + f": {' + '.join(parts)} → razem {total:.2f} zł."
            if parts
            else f"Za {period_month:02d}.{period_year}: brak składek społecznych (ulga na start)."
        ),
    }


def pit_advance_for_period(
    settings: KpirSettings,
    period_year: int,
    period_month: int,
) -> dict[str, Any] | None:
    """Orientacyjna zaliczka PIT za okres."""
    if not _period_active_jdg(settings, period_year, period_month):
        return None
    if settings.tax_form == "lump_sum":
        return {
            "advance_pln": 0,
            "summary": "ryczałt — brak zaliczki PIT",
            "detail": "Ryczałt — zaliczki PIT nie dotyczą (ewidencja przychodów).",
        }

    try:
        from .pit_calculator import estimate_pit

        est = estimate_pit(period_year, settings)
    except Exception:
        return None

    advance = int(est.get("estimated_monthly_advance") or 0)
    if not est.get("advance_payment_required"):
        return {
            "advance_pln": 0,
            "summary": "0 zł (poniżej progu)",
            "detail": (
                f"Szacowany roczny PIT {est.get('estimated_tax', 0)} zł — "
                f"poniżej progu zaliczek ({est.get('advance_minimum_exempt_pln', 1000):.0f} zł/rok)."
            ),
        }

    return {
        "advance_pln": advance,
        "summary": f"{advance} zł",
        "detail": (
            f"Za {period_month:02d}.{period_year} — szac. zaliczka {advance} zł "
            f"(dochód roczny {est.get('income', 0):.2f} zł, forma: {settings.tax_form})."
        ),
    }


def enrich_deadline_amounts(
    row: dict[str, Any],
    settings: KpirSettings | None,
) -> dict[str, Any]:
    """Uzupełnia wiersz kalendarza o kwoty (amount_pln, amount_label)."""
    if not settings or not is_jdg_mode(settings):
        return row

    due = str(row.get("due_date") or "")
    if not due or len(due) < 7:
        return row

    try:
        due_d = date.fromisoformat(due[:10])
    except ValueError:
        return row

    period_year, period_month = period_before_due(due_d.year, due_d.month)
    category = str(row.get("category") or "")
    title = str(row.get("title") or "").lower()

    if category == "zus" and "składki" in title:
        ob = zus_obligation_for_period(settings, period_year, period_month)
        if ob:
            row = {**row, "amount_pln": ob["total_pln"], "amount_label": ob["summary"]}
            base = str(row.get("description") or "").strip()
            row["description"] = f"{base} {ob['detail']}".strip() if base else ob["detail"]
    elif category == "pit" and "zaliczka" in title:
        ob = pit_advance_for_period(settings, period_year, period_month)
        if ob:
            row = {**row, "amount_pln": float(ob["advance_pln"]), "amount_label": ob["summary"]}
            base = str(row.get("description") or "").strip()
            row["description"] = f"{base} {ob['detail']}".strip() if base else ob["detail"]
    elif category == "zus" and "dra" in title:
        ob = zus_obligation_for_period(settings, period_year, period_month)
        if ob:
            row = {**row, "amount_pln": ob["total_pln"], "amount_label": ob["summary"]}
            base = str(row.get("description") or "").strip()
            row["description"] = (
                f"{base} Deklaracja DRA — orientacyjnie te same składki "
                f"(razem {ob['total_pln']:.2f} zł)."
            ).strip()

    return row


def upcoming_payment_summary(
    settings: KpirSettings,
    *,
    ref_year: int | None = None,
    ref_month: int | None = None,
) -> dict[str, Any]:
    """Orientacyjne wpłaty na bieżący (lub wskazany) miesiąc — termin 20."""
    today = date.today()
    y = ref_year or today.year
    m = ref_month or today.month

    if not is_jdg_mode(settings):
        return {
            "active": False,
            "message": "Składki ZUS i zaliczki PIT pojawią się po rejestracji JDG.",
        }

    due_day = int(compliance().get("zus_due_day") or 20)
    due = date(y, m, min(due_day, 28))
    period_y, period_m = period_before_due(y, m)

    if not _period_active_jdg(settings, period_y, period_m):
        return {
            "active": False,
            "message": (
                f"Brak obowiązków JDG za {period_m:02d}.{period_y} "
                f"(przed datą rejestracji {settings.jdg_registered_at or '?'})."
            ),
        }

    zus = zus_obligation_for_period(settings, period_y, period_m)
    pit = pit_advance_for_period(settings, period_y, period_m)
    zus_total = float(zus["total_pln"]) if zus else 0.0
    pit_amt = int(pit["advance_pln"]) if pit else 0
    pit_label = str(pit["summary"]) if pit else "—"
    days_left = (due - today).days

    message = (
        f"Termin {due_day:02d}.{m:02d}.{y} (za {period_m:02d}.{period_y}): "
        f"ZUS {zus_total:.2f} zł, PIT {pit_label}"
    )
    if days_left < 0:
        message += " — termin minął"
    elif days_left == 0:
        message += " — dziś"
    elif days_left <= 7:
        message += f" — za {days_left} dni"

    return {
        "active": True,
        "due_date": due.isoformat(),
        "due_day": due_day,
        "period_year": period_y,
        "period_month": period_m,
        "zus_total_pln": zus_total,
        "zus_detail": zus["summary"] if zus else "",
        "pit_advance_pln": pit_amt,
        "pit_label": pit_label,
        "days_left": days_left,
        "message": message,
    }
