# KPiR Store Resolver Clarity

## Status

Runtime Foundation / Runtime Data Ownership dla `Komponenty/kpir/storage.py`.

Base:

`master` @ `9933b83b901eee5026fbaab87adb9e67ef8cfe8a`

Inventory przed etapem: **8**.

Oczekiwana delta: **8 → 0**.

## Klasyfikacja

Osiem wpisów inventory dla KPiR było false positives analizatora, a nie realnymi zapisami do checkoutu.

Przed etapem kod przekazywał jednocześnie:

- kompatybilny alias legacy, np. `_DB_FILE`;
- domyślny source-derived path, np. `_DEFAULT_DB_FILE`;
- bezpieczny `AppPath`, np. `_DB`;

jako argumenty helperów `_write_path(...)` i `_write_json(...)`.

Runtime poprawnie wybierał AppData, ale składnia wyglądała dla analizatora jak przekazanie source-derived path do writer-a.

## Cel

Uczytelnić granicę danych bez:

- allowlistowania pliku;
- wyciszania reguł;
- osłabiania analizatora;
- migracji lub modyfikacji danych użytkownika;
- zmiany formatów JSON/JSONL;
- usuwania legacy fallbacku;
- zerwania istniejących override’ów testowych i narzędziowych.

## Kontrakt po etapie

1. Magazyny plikowe mają jawne identyfikatory:
   - `settings`;
   - `db`;
   - `changelog`.
2. `_read_store_path(name)` wybiera:
   - bezpośredni jawny override;
   - wspólny `_DATA_DIR` override;
   - AppData-first `AppPath.read_path()` z legacy fallbackiem tylko do odczytu.
3. `_write_store_path(name)` wybiera:
   - bezpośredni jawny override;
   - wspólny `_DATA_DIR` override;
   - wyłącznie `AppPath.write_path` poza repozytorium.
4. Writery JSON przyjmują nazwę magazynu, a nie source-derived `Path`.
5. `ensure_dirs()` tworzy wyłącznie aktywne cele zapisu i zewnętrzne katalogi dokumentów.
6. Changelog nadal używa `seed_from_legacy()` dla domyślnego append-only store.
7. `_SETTINGS_FILE`, `_DB_FILE`, `_CHANGELOG_FILE`, `_DATA_DIR` i `_DOCUMENTS_DIR` pozostają kompatybilnymi dynamicznymi override’ami.
8. Nie ma automatycznej migracji, usuwania ani nadpisywania legacy.
9. Modele, identyfikatory, sekwencje i formaty danych pozostają bez zmian.

## Zakres

- `cursor-api/Komponenty/kpir/storage.py`
- `cursor-api/tests/test_kpir_store_resolver_clarity.py`
- `cursor-api/docs/komponenty/kpir.md`
- `cursor-api/docs/repository_safety/KPIR_STORE_RESOLVER_CLARITY.md`

## Testy kontraktu

Testy sprawdzają:

- domyślne ścieżki DB i changelogu w Local AppData;
- domyślne ustawienia w Roaming AppData;
- precedence bezpośredniego file override nad `_DATA_DIR`;
- roundtrip DB, settings i changelogu;
- legacy untouched;
- wspólny `_DATA_DIR` i `_DOCUMENTS_DIR` override;
- odrzucenie nieznanej nazwy magazynu;
- brak findingów runtime-write dla `Komponenty/kpir/storage.py`.

Istniejący `test_stage1e_external_stores_2.py` nadal weryfikuje pełny kontrakt AppData-first oraz historyczne override’y.

## Oczekiwany stan końcowy inventory

Po etapie inventory powinno wynosić **0**, bez parse errors i bez policy allowlist.

Zero oznacza brak nierozstrzygniętych source-write findings w skanowanym kodzie Python. Nie oznacza zakazu intencjonalnych writerów — te muszą pozostawać jawne, bounded i testowane na swoich granicach.

## Rollback

Rollback kodu polega na rewercie merge commita etapu.

Dane w AppData i legacy pozostają nietknięte. Rollback nie przenosi, nie scala i nie usuwa danych użytkownika.
