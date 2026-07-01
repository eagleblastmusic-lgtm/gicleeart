"""VAT prorata — proporcjonalny limit zwolnienia przy starcie JDG w trakcie roku."""



from __future__ import annotations



from datetime import date

from typing import Any



from Komponenty._shared.tax_config import vat_exemption_threshold, vat_prorata_divisor





def _parse_iso(iso: str) -> date | None:

    raw = (iso or "").strip()[:10]

    if not raw:

        return None

    try:

        return date.fromisoformat(raw)

    except ValueError:

        return None





def activity_days_in_year(jdg_start: date, year: int) -> int:

    """Dni prowadzenia działalności w roku (od startu do 31.12 włącznie)."""

    year_end = date(year, 12, 31)

    year_start = date(year, 1, 1)

    if jdg_start > year_end:

        return 0

    effective = max(jdg_start, year_start)

    return (year_end - effective).days + 1





def vat_prorata_threshold(

    jdg_registered_at: str,

    year: int | None = None,

    *,

    full_threshold: float | None = None,

) -> dict[str, Any]:

    """

    Limit zwolnienia VAT: 240 000 zł × dni aktywności / 365.

    Przy starcie 1.01 lub braku daty — pełny próg roczny.

    """

    y = year or date.today().year

    full = float(full_threshold if full_threshold is not None else vat_exemption_threshold())

    divisor = vat_prorata_divisor()

    start = _parse_iso(jdg_registered_at)



    if not start or start <= date(y, 1, 1):

        return {

            "year": y,

            "full_threshold_pln": round(full, 2),

            "threshold_pln": round(full, 2),

            "prorata_applied": False,

            "activity_days": divisor if not start else activity_days_in_year(start, y),

            "divisor": divisor,

            "jdg_registered_at": jdg_registered_at or "",

            "message": f"Pełny próg zwolnienia VAT: {full:,.0f} zł.",

        }



    days = activity_days_in_year(start, y)

    threshold = round(full * days / divisor, 2)

    return {

        "year": y,

        "full_threshold_pln": round(full, 2),

        "threshold_pln": threshold,

        "prorata_applied": True,

        "activity_days": days,

        "divisor": divisor,

        "jdg_registered_at": start.isoformat(),

        "message": (

            f"Próg VAT prorata ({start.isoformat()} → 31.12.{y}): "

            f"{threshold:,.2f} zł ({days} dni / {divisor} × {full:,.0f} zł)."

        ),

    }


