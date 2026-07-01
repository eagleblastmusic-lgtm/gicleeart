# Działalność nierejestrowana (`dnr`)



Kafelek w sekcji **Finanse** GicleeApp — osobna ewidencja DNR (niezależna od KPiR/JDG).



## Zakres



- Ewidencja **sprzedaży** i **kosztów** bez pełnej KPiR

- Kontrola **kwartalnego limitu przychodu należnego** (domyślnie **10 813,50 PLN** w 2026 — z `tax_config_2026.json`)

- **Guardrail miesięczny** 3 604,50 zł (ostrzeżenie, nie limit prawny)

- **Checklista warunków DNR** w ustawieniach (60 mies. bez DG itd.)
- **Zamknięcie miesiąca (DNR)** — checklista rachunków i importu DNR, eksport CSV; bez zamknięcia KPiR

- Wpisy: sprzedaż, zwrot, korekta, bonifikata/skonto (ostatnie **zmniejszają** limit)

- **Źródło sprzedaży**: ręczny, faktura, Shopify, **Allegro** + flaga **merchant of record** (poza limitem)

- **Rabaty**: opcjonalnie cena + rabat → do limitu idzie **przychód należny** (np. 500 − 100 = 400 zł)

- Import wystawionych faktur z modułu **Dokumenty sprzedaży** (`event_date` = data sprzedaży, `paid_at` = data wpływu)

- Eksport CSV z podsumowaniem kwartałów

- Alert **CEIDG / 7 dni** po przekroczeniu limitu kwartalnego

- **Kreator migracji DNR → JDG** — checklista CEIDG, przełączenie faktur na JDG, włączenie KPiR + ulga na start ZUS, **import ewidencji DNR → KPiR**

- **Import DNR → KPiR** (`kpir_import.py`) — przenosi wpisy sprzedaży/kosztów do daty rejestracji JDG; zwroty **po dacie JDG** importowane osobno; oznacza je w DNR jako `migrated_to_kpir_at`

- **Dwa liczniki przychodu** — limit: `przychód należny`; PIT: `sale_pit_cash_delta()` / `pit_cash_revenue_for_year()` (pola `payment_status`, `paid_at`, `amount_received_pln`)

- **Import Shopify → DNR** (`shopify_integration.py`) — opłacone zamówienia + zwroty; `destination_country`, `fulfillment_country`

- **Polityka importu** (`import_policy.py`) — gdy moduł faktur jest dostępny, bezpośredni import Shopify jest wyłączony (faktury wystawiasz w GicleeApp, nie w Shopify); import Shopify tylko awaryjnie bez modułu faktur

- **Monitory compliance** (`Komponenty/_shared/compliance_monitors.py`) — WSTO/OSS 42k, KSeF B2B 10k/mies., alerty art. 28b

- **Faktury Shopify** — zaokrąglanie VAT na poziomie linii (`shopify_tax_lines.py`), pola `taxes_included`, `fulfillment_country` na fakturze

- **`manual_review_required`** — pierwsze przekroczenie zapisane na stałe; po zwrocie/korekcie alert „weryfikacja ręczna” (korekta nie cofa JDG)
- **Jeden licznik limitu** — `dnr_settings.quarterly_limit` synchronizowany z KPiR; `dnr_tracker` czyta ewidencję DNR
- **`obligation_active`** — stan kwartału „poniżej limitu, obowiązek JDG trwa”
- **Sync migracji** — po każdej zmianie sprzedaży w `entry_service`
- **`acknowledge_manual_review()`** — potwierdzenie weryfikacji brzegowej (osobno od `complete_migration`)



Do limitu liczy się **przychód należny** (kwoty należne od klientów, towar + wysyłka w cenie), nie zysk po kosztach.



## Konfiguracja 2026



Stałe podatkowe: `Komponenty/_shared/tax_config/tax_config_2026.json` (`PL-JDG-2026-06-14`). Moduły `dnr`, `kpir`, `kalkulacja` czytają wartości przez `Komponenty._shared.tax_config`.



## Pliki



| Plik | Rola |

|------|------|

| `view.py` | UI: dashboard (4 kwartały), sprzedaż, koszty, podsumowanie, import, eksport, ustawienia, **kreator migracji** |

| `migration_service.py` | Wykrycie przekroczenia, checklista kroków, przełączenie faktur/KPiR |

| `shopify_integration.py` | Import opłaconych zamówień Shopify do DNR |

| `import_policy.py` | Blokada importu Shopify gdy dostępny moduł faktur / JDG |

| `kpir_import.py` | Import ewidencji DNR → KPiR |

| `storage.py` | `dane/dnr.json`, `dane/dnr_settings.json` (pole `migration` w ustawieniach) |

| `summary_service.py` | Limit kwartalny, guardrail miesięczny, `sale_limit_delta()`, dashboard |

| `entry_service.py` | CRUD; `entry_kind` na wpisach przychodu |

| `invoice_integration.py` | Import faktur `issued` / `corrected` |

| `constants.py` | Etykiety, checklista; wartości z `tax_config` |

| `verify_dnr.py` | Testy lokalne |



## Uruchomienie testów



```bash

python -m Komponenty.dnr.verify_dnr

python -m Komponenty._shared.verify_tax_config

```



## Relacja do KPiR



Moduł **JDG — KPiR** (`dnr_tracker.py`) przy trybie `dnr` też liczy limit **kwartalnie** z wpisów KPiR. Komponent `dnr` ma **osobną bazę** ewidencji.



## Migracja DNR → JDG i `manual_review_required`

Po pierwszym przekroczeniu kwartalnego limitu aplikacja zapisuje **pierwsze przekroczenie** (`first_exceed_*` w `dnr_settings.json` → `migration`) i nie kasuje tego wpisu po zwrocie ani korekcie. Skutek prawny JDG liczy się od dnia zdarzenia — korekta w ewidencji **nie cofa** obowiązku rejestracji.

`migration_service.sync_migration_status()` utrzymuje status `required` / `in_progress` dopóki kreator nie zostanie ukończony (`completed`).

**Przypadki brzegowe** (`assess_manual_review()` → `manual_review_required`):

- suma kwartalna spadła poniżej limitu, ale wcześniej było przekroczenie (zwrot/korekta);
- minimalne przekroczenie (≤ 50 zł lub ≤ 1% limitu).

UI: żółty baner na dashboardzie DNR oraz sekcja w kreatorze migracji z listą powodów weryfikacji. Po potwierdzeniu notatką baner znika, ale kreator migracji pozostaje aktywny do ukończenia wszystkich kroków.

**Cofnięcie zapisanego przekroczenia** (`revert_first_exceed`): gdy ewidencja jest z powrotem poniżej limitu (np. po zwrocie), można ręcznie usunąć zapis pierwszego przekroczenia i wyłączyć kreator — z uzasadnieniem (min. 3 znaki). Niedostępne po rozpoczęciu kroków migracji lub przy aktywnym przekroczeniu. Zapis audytu w `first_exceed_dismissed_*`; sync nie odtwarza przekroczenia z historii wpisów dopóki nie wystąpi nowe realne przekroczenie.

`complete_migration()` wymaga wszystkich kroków checklisty oraz potwierdzonej weryfikacji ręcznej (gdy dotyczy) — bez „zamknięcia na siłę”. Nie zamyka migracji, dopóki są wpisy DNR do importu (`kpir_import.preview_dnr_kpir_import().actionable > 0`).

Krok **`dnr_imported`** — okres DNR zaimportowany do KPiR; nie można go ręcznie zaznaczyć, gdy pozostały wpisy do przeniesienia.

Import obejmuje wpisy **do daty rejestracji JDG** (`kpir_settings.jdg_registered_at`). Wpisy późniejsze (np. zwrot po dniu JDG) pozostają w DNR — nie są dublowane w KPiR automatycznie.

## Płatności (UI Sprzedaż)

Ekran **Sprzedaż** obsługuje status płatności (`nieopłacone` / `opłacone` / `częściowo`), datę wpływu, kwotę kasową, edycję wpisu i kolumny w tabeli. Import faktur ustawia płatność z pola `payment_date` faktury (puste = nieopłacone).

→ [`README.md`](README.md)

