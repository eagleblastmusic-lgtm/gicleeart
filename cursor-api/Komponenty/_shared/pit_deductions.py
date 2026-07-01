"""Wspólne reguły PIT — odliczenia i zaokrąglenia deklaracji."""



from __future__ import annotations



from Komponenty._shared.tax_config import health_linear_annual_deduction_limit





def round_declaration_pln(amount: float) -> int:

    """Zaokrąglenie do pełnych złotych (≥50 gr w górę)."""

    if amount >= 0:

        return int(amount + 0.5)

    return -int(-amount + 0.5)





def health_from_income_monthly(monthly_income: float, tax_form: str) -> float:

    """Uproszczona składka zdrowotna od dochodu (miesięcznie, bez minimum)."""

    if monthly_income <= 0:

        return 0.0

    rate = 0.049 if tax_form in ("linear", "liniowy") else 0.09

    return round(monthly_income * rate, 2)





def health_deductible_annual(

    monthly_income: float,

    tax_form: str,

    *,

    health_floor_monthly: float = 0.0,

) -> tuple[float, float, str]:

    """

    Roczna kwota zdrowotnej odliczana od podstawy PIT.

    Zwraca: (użyta, wyliczona bez limitu, opis).

    """

    form = str(tax_form)

    calc = health_from_income_monthly(monthly_income, form) * 12

    floor = round(float(health_floor_monthly or 0) * 12, 2)



    if form in ("linear", "liniowy"):

        cap = health_linear_annual_deduction_limit()

        used = min(calc, cap)

        if calc > cap:

            return used, calc, f"od dochodu (limit {cap:,.0f} zł/rok)"

        return used, calc, "od dochodu (liniowy 4,9%)"



    if form in ("scale", "skala"):

        used = max(floor, calc)

        if floor >= calc:

            return used, calc, "minimum ustawowe"

        return used, calc, "od dochodu (skala 9%)"



    return floor, calc, "stała kwota"


