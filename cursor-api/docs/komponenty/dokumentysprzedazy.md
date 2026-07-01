# Dokumenty sprzedaży (`dokumentysprzedazy`)

Faktury **bez VAT** / **Invoice without VAT** — z zamówień Shopify lub **sprzedaży poza sklepem**.

## Uruchomienie

GicleeApp → **Finanse** → **Dokumenty sprzedaży**

```powershell
pip install -r Komponenty/dokumentysprzedazy/requirements.txt
python -m Komponenty.dokumentysprzedazy.verify_invoices
```

## Kluczowe pliki

| Plik | Rola |
|------|------|
| `view.py` | UI: sprzedaż poza Shopify, zamówienia, ustawienia, eksport |
| `invoice_service.py` | Wystawianie, walidacja, korekty |
| `invoice_builder.py` | Szkic z zamówienia Shopify lub ręczny (`build_manual_draft`) |
| `pdf_generator.py` | PDF A4 (reportlab) |
| `orders_sync.py` | Polling nowych zamówień Shopify (panel księgowy) |
| `order_review.py` | Przegląd zamówienia przed wystawieniem dokumentu |
| `email_compose.py` | Wysyłka dokumentów — SMTP Gmail (PDF w załączniku) lub szkic `.eml` / Gmail Web |
| `i18n.py` | Tłumaczenia PDF — 7 języków rynków (pl/en/de/fr/es/nl/it) |
| `nbp_service.py` | Kursy NBP historyczne → PLN |
| `shopify_orders.py` | Pobieranie zamówień, tagi |
| `export_monthly.py` | CSV miesięczny |
| `dane/invoices.json` | Ewidencja wystawionych dokumentów |

## Zasady

- **Automatyczna synchronizacja Shopify** (co 5 min w GicleeApp): powiadomienie systemowe + toast w panelu księgowym; licznik „nowych do obsługi”
- **Przegląd zamówienia** przed wystawieniem: pozycje, kraj→język, prośba o fakturę, wiadomość do klienta (opcjonalnie **szacowany czas realizacji** 1–7 dni → język marketu)
- Przycisk **Wystaw rachunek** (DNR) lub **Wystaw fakturę bez VAT** (JDG) — wg trybu księgowości
- Po wystawieniu: **Wyślij fakturę/rachunek** gdy klient prosił; PDF **automatycznie** przez SMTP (`GMAIL_IMAP_APP_PASSWORD` w `.env`) lub szkic `.eml` z załącznikiem; bez hasła — Gmail Web (ręczny załącznik)
- **Numeracja:** PL → FBV/DN; zagranica → INV (JDG) lub **DN-INV** (DNR, rachunki zagraniczne)
- **Auto-księgowanie:** DNR (pod limitem) lub KPiR (JDG / po przekroczeniu limitu kwartalnego DNR)
- PL → „Faktura bez VAT” / rachunek DNR; DE → „Rechnung ohne USt.”; FR → „Facture sans TVA”; ES → „Factura sin IVA”; NL → „Factuur zonder BTW”; IT → „Fattura senza IVA”; EN → „Invoice without VAT”
- **Sprzedaż poza Shopify:** zakładka Zamówienia → **Nowa faktura bez VAT** (produkcja) lub **Faktura testowa** (TEST/TST) → DNR → KPiR
- **Faktura testowa:** numeracja `TEST/n/rok` / `TST/n/rok`, znak wodny na PDF; **można** importować do DNR i KPiR (test przepływu faktura→DNR→KPiR); **nie** trafia do eksportu ani licznika VAT; w pełni usuwalna — przy usunięciu znika też wpis DNR/KPiR i numer TEST/TST wraca do puli
- Zakładka **Zamówienia**: wystawianie faktur; **Status KPiR (podgląd)** — bez księgowania (przycisk „Otwórz KPiR → Przychody”)
- **Usuwanie:** zaznacz w tabeli → **Usuń zaznaczone** (szkice bez ograniczeń; wystawione niezaksięgowane — numer zwalniany do ponownego użycia, jeśli nie ma wyższych w serii; DNR/KPiR tylko gdy faktura jest tam powiązana)
- Brak kolumny VAT 23%; adnotacja zwolnienia / DNR
- **Tryb DNR (działalność nierejestrowana):** dokument **Rachunek** (nie faktura VAT), numeracja **DN/n/rok** (np. `DN/1/2026`), korekty **KDN/n/rok** — ten sam styl co FBV; PDF z adnotacją o DN, datą wpływu płatności, telefonem; **bez NIP sprzedawcy** (przy czystej DNR wystarczy imię i nazwisko)
- **Tryb JDG:** **Faktura bez VAT**, numeracja FBV/n/rok (PL), INV/n/rok (EN), KOR/COR dla korekt
- **Numeracja bez duplikatów:** serie DNR (`numbering_dnr_pl`) i JDG (`numbering_pl`) są oddzielne — zmiana trybu lub danych sprzedawcy nie resetuje licznika; `next_number` synchronizuje się z wystawionymi dokumentami przy zapisie ustawień i wystawieniu faktury
- **Tryb DNR/JDG (faktury)** synchronizowany z **Ustawieniami księgowości** (KPiR → „Tryb księgowości”); zapis w jednym miejscu aktualizuje `invoice_settings.json` i `kpir_settings.json`
- PDF: `documents/invoices/YYYY/MM/`
- Zakładka **Ustawienia faktur**: przycisk **Podgląd faktury** (PL/DE/FR/ES/NL/IT/EN); tryb DNR/JDG zgodny z KPiR przy otwarciu zakładki
- **Próg VAT 240 000 zł** — licznik obrotu w ustawieniach (faktury wystawione + wpisy DNR bez faktury; bez merchant of record)
- Pola faktury: `sales_channel` (shopify / manual / allegro), `merchant_of_record` — przygotowanie pod Allegro
- **Data wpływu (opcjonalna)** w edytorze faktury — puste = nieopłacone w imporcie DNR
- Ustawienia: panel **Compliance** (WSTO/OSS, KSeF, art. 28b) pod progiem VAT 240k
- PDF: font TTF z polskimi znakami (Windows: Arial; opcjonalnie DejaVu w `fonts/`)
- **Koszyk (motyw):** sekcja „Chcę fakturę” — osoba prywatna / firma; atrybuty `_Invoice requested`, `_Invoice type`, `_Company name`, `_Tax ID` → `note_attributes` zamówienia

## Zależności

- `dodajobraz/shopify_client.py` — `read_orders`, `write_orders` (tagi)
- `_shared/fx_rates.py` — fallback kursów
- `reportlab`

→ [`dokumentysprzedazy/README.md`](../../Komponenty/dokumentysprzedazy/README.md)
