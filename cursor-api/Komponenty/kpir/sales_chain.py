"""Łańcuch sprzedaży: faktura → DNR → KPiR (bez faktura → KPiR)."""



from __future__ import annotations





def uses_dnr_sales_chain() -> bool:

    """True gdy tryb księgowości to DNR i przychody idą przez ewidencję DNR."""

    try:

        from Komponenty.dnr import storage  # noqa: F401

        from Komponenty._shared.accounting_mode_sync import load_kpir_accounting_mode



        acc = load_kpir_accounting_mode()

        if acc in ("jdg_kpir", "jdg_ryczalt"):

            return False

        return True

    except ImportError:

        return False

