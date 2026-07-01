# Finanse — hub (kafelek: Księgowość)

Sekcja **Finanse** w launcherze, jeden kafelek **Księgowość** zamiast trzech osobnych (Dokumenty / KPiR / DNR).

## Ekran panelu

- Limit kwartalny **DNR**
- Próg zwolnienia **VAT 240k**
- Liczniki **przepływu** (bez dokumentu / szkice / DNR / KPiR)
- **Compliance** (WSTO/OSS, KSeF, art. 28b)
- **Wpłaty w tym miesiącu** (JDG): orientacyjnie ZUS + PIT, termin 20.
- **Checklist miesiąca** z linkami do zamówień i faktur
- **Zamknięcie miesiąca** — w trybie DNR → DNR (checklista bez KPiR); po JDG → pełne zamknięcie finansów (KPiR)
- Skróty: Dokumenty sprzedaży, KPiR, DNR, **Ustawienia księgowości** (otwiera KPiR → ustawienia trybu DNR/JDG, ZUS, VAT)
- Okno inline: **1060×900** (`component.json`); pasek akcji (Odśwież, Zamknięcie miesiąca…) **zawsze na dole**, poza scrollowaną treścią.

Kod: `Komponenty/finanse/view.py`, `hub_service.py`, `Komponenty/_shared/finance_navigation.py`

## Nawigacja

- **Wróć** w panelu Księgowość → ekran startowy launchera.
- **Wróć** w KPiR / DNR / Dokumenty otwartych **z panelu** → powrót do Księgowości (nie do startu).
- Ekran otwarty **bezpośrednio z checklisty** (np. Import DNR) — **Wróć** wraca do panelu Księgowość, nie do dashboardu modułu.
- Launcher: `giclee_app/launcher.py` — `_current_inline_folder`, `_return_to_finanse_hub()`.

## Testy osobne

```bash
python -m Komponenty.kpir.verify_flow_status
python -m Komponenty.kpir.verify_finance_pipeline
python -m Komponenty.dnr.verify_revert_exceed
```

## Przepływ sprzedaży (DNR)

Przy dostępnym module DNR przychody **nie** księguje się bezpośrednio z faktury w KPiR:

**faktura → import DNR → Import do KPiR** (moduł DNR).

Pipeline (krok 2) importuje do DNR tylko faktury **bez wpisu DNR i bez wpisu KPiR** — używany wewnętrznie / testy; w UI: **Import DNR (zaległe)** tylko w **Zamknięciu miesiąca**.
