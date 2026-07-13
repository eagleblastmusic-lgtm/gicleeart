# KPiR — Księga Przychodów i Rozchodów

> Komponent: `cursor-api/Komponenty/kpir/`  
> Launcher: sekcja **Finanse** → kafelek **JDG — KPiR**  
> Podstawa prawna: rozporządzenie MF Dz.U. 2025 poz. 1299 (obowiązuje od 1.01.2026)

Moduł PKPiR dla **samodzielnej księgowości JDG** — bez biura rachunkowego. Obejmuje wzór 19 kolumn, remanent, zamknięcie roku, eksport roczny XML i wzór dochodu z załącznika do rozporządzenia.

## Menu (w module)

| Ekran | Opis |
|-------|------|
| Dashboard | Metryki, przepływ sprzedaży, compliance |
| KPiR | Tabela wpisów — widok prosty lub **urzędowy (19 kolumn)** |
| **Remanent** | Spis z natury (1 I, 31 XII, start JDG), wycena (cena zakupu / koszt wytworzenia / …), wskaźnik k. ubocznych, ujęcie w kol. 12 |
| **Ewidencja sprzedaży** | Przychody nieudokumentowane fakturą (§ 17) → KPiR |
| **KSeF** | Numery e-faktur B2B, synchronizacja z kolumną 3 KPiR |
| **Środki trwałe** | Ewidencja ST, amortyzacja miesięczna → kol. 15 |
| **WNiP** | Wartości niematerialne i prawne, amortyzacja → kol. 15 |
| **Przebieg pojazdu** | Ewidencja przebiegu przy ST firmowym i 100% kosztów auta |
| **Dowody wewnętrzne** | UI: część kosztów mieszkania (§ 8), opis towaru przed fakturą (§ 9) |
| **Zamknięcie roku** | Checklist, dochód urzędowy, eksport roczny PKPiR |
| **Eksport urzędowy** | CSV/XLSX/PDF 19 kolumn + pakiet roczny |
| **Compliance PKPiR** | Termin 20., limit formy KPiR, retencja 5 lat |
| Przychody | Faktury → KPiR |
| Koszty | Ręczne, import banku, prowizje |
| Podsumowanie roku | Dochód uproszczony + **dochód urzędowy z remanentem** |
| Eksport księgowy | CSV, XLSX, PDF, JPK XML miesięczny |
| Ustawienia | Metoda kosztów (memoriał/kasa), rodzaj działalności, NIP |

## 19 kolumn PKPiR

Model `KpirEntry` + eksport `official_columns.py` / `official_export.py`:

| Kol. | Pole |
|------|------|
| 1–2 | Lp., data zdarzenia |
| 3–4 | Nr KSeF, nr dowodu |
| 5–7 | NIP kontrahenta (albo imię + adres) |
| 8 | Opis |
| 9–11 | Przychód tow./pozostały/razem |
| 12–16 | Zakupy, k. uboczne, wynagrodzenia, poz. wydatki, razem wydatki |
| 17–19 | Kolumna wolna, koszty B+R, uwagi |

W UI ekranu **KPiR** checkbox „Widok urzędowy (19 kolumn)” przełącza tabelę na pełny wzór; eksport urzędowy i JPK zawsze używają 19 kolumn.

## Remanent (§ 20–22)

Kod: `inventory_service.py`, UI: **Remanent**

- Spisy: `year_start`, `year_end`, `business_start`, zerowy
- Wycena w 14 dni (`valuation_deadline`)
- Metody wyceny pozycji: cena zakupu, koszt wytworzenia (półwyroby/wyroby), cena rynkowa, odpady
- **Wskaźnik kosztów ubocznych** — `compute_purchase_side_markup_pct` / `apply_year_side_cost_markup` podwyższa cenę jednostkową wg zakupów roku (00233)
- Ujęcie w KPiR → kol. 12 (`source=inventory`)
- Wartość remanentu **nie wchodzi** do sumy zakupów w wzorze dochodu (wyłączone w `annual_income.py`)

## Dochód roczny

Kod: `annual_income.py`

```
dochód = przychód (kol. 11)
       − (remanent_początkowy + kol.12 + kol.13 − remanent_końcowy + kol.16)
```

Używane w: PIT (`pit_calculator.py`), zamknięcie roku, podsumowanie roku.

## Koszty — metoda memoriałowa / kasowa

Ustawienie `cost_method` w **Ustawienia**:

- `accrual` — data faktury / `event_date`
- `cash` — data zapłaty (`payment_date`)

Kod: `cost_dates.py` → `book_cost_to_kpir`

## Termin zapisów

§ 11 ust. 2 — do **20. dnia** miesiąca następnego.  
Monitor: `kpir_compliance.py` → checklist miesiąca i ekran Compliance PKPiR.

## Zamknięcie roku

Kod: `year_close_service.py`

1. Checklist (`build_year_close_checklist`) — zamknięte miesiące, remanent 31 XII
2. `close_year` — remanent, dochód, pakiet `pkpir_annual_export.py`
3. Przeniesienie remanentu na 1 I następnego roku
4. Instrukcja obsługi programu w pakiecie rocznym (wymóg księgi elektronicznej)

## Eksporty

| Plik | Opis |
|------|------|
| `official_export.py` | CSV/XLSX/PDF — 19 kolumn |
| `pkpir_annual_export.py` | XML roczny + pakiet + INSTRUKCJA |
| `jpk_export.py` | JPK_PKPIR miesięczny (19 kolumn) |

Termin przekazania PKPiR do US: **do 30 kwietnia** po roku podatkowym.

## Środki trwałe

Kod: `fixed_assets_service.py` — próg 10 000 zł; amortyzacja liniowa → kol. 15.

## WNiP (wartości niematerialne i prawne)

Kod: `intangible_assets_service.py`, UI: **WNiP**

- Ewidencja WNiP łącznie z PKPiR (00233)
- Amortyzacja miesięczna → kol. 15 (`source=intangible_asset`)

## Przebieg pojazdu

Kod: `vehicle_log_service.py`, UI: **Przebieg pojazdu**

- Pojazd firmowy + wpisy przebiegu (data, trasa, km)
- Wymagane przy ST firmowym i 100% kosztów auta w KPiR

## Dowody wewnętrzne

Kod: `internal_doc_service.py`, UI: **Dowody wewnętrzne**

- Część kosztów mieszkania (§ 8), opis towaru przed fakturą (§ 9)
- Tworzenie dowodu i księgowanie do KPiR z ekranu modułu

## Różnice kursowe

Kod: `fx_diff_service.py`, UI: **Waluty obce**

- Rozliczenie: kurs zaksięgowany vs kurs rozliczenia (ręcznie lub z zapisu `fx_settlements`)
- Zyski/straty kursowe, księgowanie korekt miesiąca (`book_fx_diff_adjustments`)

## Poza zakresem (świadomie)

- Pełne API KSeF — ręczne numery wystarczą poniżej limitu B2B
- Automatyczna wysyłka rocznej PKPiR do US — eksport + przekazanie ręczne
- Moduł płac (kol. 14–15) — brak pracowników

## Ewidencja sprzedaży (§ 17)

Kod: `sales_register_service.py`, UI: **Ewidencja sprzedaży**

- Wpisy przychodów nieudokumentowanych fakturą
- `book_sales_register_to_kpir` → wpis KPiR (`source=sales_register`)

## KSeF

Kod: `ksef_service.py`, pole `ksef_number` na fakturze (`dokumentysprzedazy`) i wpisie KPiR

- Edycja w edytorze faktury (po wystawieniu: **Zapisz KSeF**)
- Ekran **KSeF** w module KPiR — lista, edycja, synchronizacja z zaksięgowanymi wpisami
- Przy księgowaniu faktury numer trafia do kol. 3 automatycznie

Pełny import z API KSeF — poza zakresem (ręczne numery + monitor B2B w compliance).

## Korekty

- Przychody: ujemne kwoty (`correction_service.py`)
- Koszty: `create_cost_correction`

## Persystencja i ownership danych

Kod: `storage.py`.

| Magazyn | Bucket | Aktywna lokalizacja |
|---------|--------|---------------------|
| `settings` | Roaming AppData / `config` | `Komponenty/kpir/dane/kpir_settings.json` |
| `db` | Local AppData / `data` | `Komponenty/kpir/dane/kpir.json` |
| `changelog` | Local AppData / `data` | `Komponenty/kpir/dane/kpir_changelog.jsonl` |
| dokumenty i eksporty | Local AppData / `data` | `Komponenty/kpir/documents/` |

Zasady:

- AppData jest nadrzędnym miejscem odczytu i jedynym domyślnym miejscem zapisu;
- legacy w checkoutcie pozostaje fallbackiem tylko do odczytu;
- changelog append-only może zostać jednorazowo skopiowany przez `seed_from_legacy()`, bez usuwania źródła;
- jawne override’y `_SETTINGS_FILE`, `_DB_FILE`, `_CHANGELOG_FILE`, `_DATA_DIR` i `_DOCUMENTS_DIR` pozostają dostępne dla testów oraz narzędzi;
- writery używają nazwanych granic `settings/db/changelog`, a nie source-derived argumentów `Path`;
- brak automatycznej migracji, scalania, kasowania i nadpisywania legacy.

Pełny kontrakt: `docs/repository_safety/KPIR_STORE_RESOLVER_CLARITY.md`.

## Testy

```powershell
cd cursor-api
python -m Komponenty.kpir.verify_kpir
```

Nowe testy: `test_annual_income_formula`, `test_official_export_csv`, `test_pkpir_annual_package`, `test_ksef_sync_to_kpir`, `test_sales_register_booking`, `test_kpir_store_resolver_clarity`.

## Twoja ścieżka (bez księgowego)

1. **Codziennie:** faktury → KPiR, koszty z PDF
2. **Do 20.:** zamknij poprzedni miesiąc (checklist)
3. **31 XII:** spis z natury + wycena + wpis do księgi
4. **Styczeń:** spis otwarcia (= zamknięcie poprzedniego roku)
5. **Do 30 IV:** eksport roczny PKPiR → US (XML z pakietu)
6. **PIT-36/PIT-36L:** dochód z ekranu Zamknięcie roku / PIT
