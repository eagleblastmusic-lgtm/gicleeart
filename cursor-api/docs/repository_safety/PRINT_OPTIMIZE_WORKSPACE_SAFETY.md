# Print Optimize Workspace Safety

## Status

Stage Runtime Foundation dla komponentu `Komponenty/print_optimize`.

Base:

`master` @ `8acc43af905b9c72b1dc821866c9e7ab583558f4`

Inventory przed etapem: **12**.

Oczekiwana delta: **12 → 10**.

## Klasyfikacja danych

`test_photos` i `ww_pairs` są **workspace'em użytkownika**.

Nie są:

- cache'em,
- fixture testowym,
- tymczasowym stagingiem,
- danymi przeznaczonymi do automatycznego usunięcia.

Workspace zawiera między innymi własne zdjęcia użytkownika, pobrane pary Whitewall, manifesty, `ours70.jpg`, raporty kalibracji oraz wyniki dE i SSIM.

## Problem przed etapem

`Komponenty/print_optimize/paths.py` wyznaczał domyślne katalogi bezpośrednio pod checkoutem:

- `Komponenty/print_optimize/data/test_photos`;
- `Komponenty/print_optimize/data/ww_pairs`.

`ensure_data_dirs()` tworzył oba katalogi, a GUI wywoływało go podczas startu.

## Przyjęty kontrakt

1. Domyślny workspace znajduje się w Local AppData:
   - `data/Komponenty/print_optimize/data/test_photos`;
   - `data/Komponenty/print_optimize/data/ww_pairs`.
2. Jawne override'y `TEST_PHOTOS_DIR` i `WW_PAIRS_DIR` pozostają autorytatywne.
3. Jawne ścieżki przekazane w GUI lub CLI pozostają dokładnie niezmienione.
4. Resolver wywołany w trybie odczytu nie tworzy katalogów.
5. `ensure_data_dirs()` tworzy wyłącznie aktywny workspace AppData albo jawny override.
6. Legacy nie jest automatycznie kopiowane, przenoszone, scalane, usuwane ani nadpisywane.
7. Nie ma automatycznego fallbacku do legacy, ponieważ dwa niezależne workspace'y nie mogą być niejawnie mieszane.
8. Publiczne importy `TEST_PHOTOS_DIR`, `WW_PAIRS_DIR` i `ensure_data_dirs` pozostają dostępne.
9. Algorytmy optymalizacji, Gemini, Playwright, Whitewall, dE, SSIM i format datasetu pozostają bez zmian.

## Testy kontraktu

`tests/test_print_optimize_workspace_boundary.py` sprawdza:

- domyślną lokalizację Local AppData;
- brak `mkdir` przy samym odczycie resolvera;
- tworzenie wyłącznie zewnętrznego workspace'u;
- brak zmian w legacy;
- dynamiczne override'y obu katalogów;
- bezpieczne wartości domyślne widoczne przez GUI;
- wartości domyślne i jawne ścieżki CLI;
- brak findingów analizatora runtime writes dla `paths.py`.

## Wyłączenia

Etap nie obejmuje:

- migracji istniejących zdjęć lub par;
- deduplikacji albo scalania workspace'ów;
- zmiany formatu manifestów i raportów;
- zmiany algorytmów obrazu;
- operacji Shopify;
- deployu;
- usuwania historycznych katalogów.

## Rollback

Rollback kodu polega na rewercie dokładnego commita/merge'a tego etapu.

Dane utworzone w Local AppData pozostają nietknięte. Nie należy ich automatycznie kopiować z powrotem do checkoutu ani usuwać.
