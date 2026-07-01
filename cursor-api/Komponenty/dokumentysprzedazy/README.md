# Dokumenty sprzedaży — faktury bez VAT

Moduł **inline** w sekcji **Finanse** GicleeApp.

## Uruchomienie

GicleeApp → **Finanse** → **Dokumenty sprzedaży**

```powershell
cd cursor-api
pip install -r Komponenty/dokumentysprzedazy/requirements.txt
python -m Komponenty.dokumentysprzedazy.verify_invoices
```

## Zasady dokumentów

- **7 języków rynków Shopify:** PL, DE, FR, ES, NL, IT + EN (pozostałe kraje)
- Kraj dostawy z zamówienia → język dokumentu (np. DE → niemiecki, FR → francuski)
- Użytkownik może ręcznie przełączyć język przed wystawieniem (edytor + sprzedaż poza Shopify)
- **Nie** używamy nazwy „Faktura VAT” / „VAT Invoice”
- Brak naliczonego VAT i stawki 23%

## Funkcje

| Zakładka | Opis |
|----------|------|
| Zamówienia | Lista z Shopify, wystawianie / podgląd faktury, korekty |
| Sprzedaż poza Shopify | Nowa / otwórz / **usuń** fakturę — wybór języka (7 rynków) |
| Ustawienia faktur | Dane sprzedawcy, tryb DNR/JDG, adnotacje, numeracja FBV/INV |
| Eksport księgowy | CSV miesięczny z kursami NBP i PLN |

PDF: `Komponenty/dokumentysprzedazy/documents/invoices/YYYY/MM/`

Ewidencja: `dane/invoices.json`, zdarzenia: `dane/invoice_events.jsonl`

## Zależności

- `dodajobraz/shopify_client.py` — zamówienia, tagi
- `_shared/fx_rates.py` + `nbp_service.py` — kursy NBP (historyczne)
- `reportlab` — PDF

→ [`README.md`](../../docs/komponenty/README.md)
