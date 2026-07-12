# Runtime source-write inventory

## Cel

`tools.repository_safety runtime-writes` tworzy diagnostyczny spis wywołań
Pythona, których cel zapisu jest wyprowadzony z `__file__`, a więc może wskazywać
na modyfikowanie source checkoutu przez dane runtime.

Narzędzie wspiera dalsze małe pakiety Runtime Foundation. Nie zastępuje
istniejącego `audit`, nie zmienia baseline'u Stage 1F i domyślnie nie blokuje CI.

## Uruchomienie

Z katalogu `cursor-api`:

```powershell
python -m tools.repository_safety runtime-writes `
  --repo . `
  --json-out "$env:TEMP\giclee-runtime-writes.json"
```

Tryb blokujący jest jawny:

```powershell
python -m tools.repository_safety runtime-writes --repo . --fail-on-findings
```

Bez `--fail-on-findings`:

- błędy parsowania kończą polecenie kodem `1`,
- znalezione miejsca do review są raportowane, ale polecenie kończy się kodem `0`,
- narzędzie nie zapisuje ani nie przenosi danych użytkownika.

## Zakres

Skanowane są śledzone przez Git pliki `.py` pod:

- `Komponenty/`,
- `giclee_app/`.

Analiza AST propaguje symbole wyprowadzone z `__file__` przez przypisania w
module, klasach i funkcjach. Rozpoznawane są między innymi:

- `Path.write_text()` i `Path.write_bytes()`,
- `open(..., "w" / "a" / "x" / "+")`,
- `touch`, `mkdir`, `unlink`, `rename`, `replace`,
- znane operacje `os` i `shutil`,
- `atomic_write_text` / `atomic_write_bytes`,
- helpery o nazwach typu `save_*`, `write_*`, `persist_*`, gdy otrzymują
  source-rooted path.

Wywołania `AppPath`, `data_path`, `config_path`, `cache_path`, `log_path` i
`backup_path` przerywają propagację. Dzięki temu jawny argument
`legacy=Path(__file__)...` nie jest traktowany jako nowy zapis do source tree.

## Interpretacja wyników

Każdy wpis zawiera:

- plik i linię,
- regułę,
- nazwę wywołania,
- symbole źródłowe,
- komunikat review.

Reguły:

- `DIRECT_SOURCE_PATH_WRITE` — bezpośrednia mutacja ścieżki wyprowadzonej z
  source checkoutu,
- `SOURCE_PATH_PASSED_TO_WRITER` — taka ścieżka trafia do znanego lub
  heurystycznie rozpoznanego writera.

Wpis jest kandydatem do review, nie automatycznym dowodem błędu. Trzeba
rozróżnić:

- mutable runtime/config,
- świadomy writer kodu lub szablonu,
- backup przed kontrolowanym Save,
- operację testową,
- false positive wymagający doprecyzowania skanera.

## CI

`tests/test_runtime_write_inventory.py`:

- chroni podstawowe kontrakty skanera,
- wykonuje inventory na aktualnym tracked tree,
- wymaga braku błędów parsowania,
- zapisuje `runtime-write-inventory.json` i `.txt` do istniejącego katalogu
  raportów Stage 2, gdy test działa na self-hosted runnerze.

Same findings pozostają diagnostyczne. Po sklasyfikowaniu bieżącego raportu można
w osobnym pakiecie dodać zatwierdzony baseline lub przełączyć wybrane reguły na
bramkę blokującą.

## Ograniczenia

Analiza jest celowo statyczna i konserwatywna:

- nie wykonuje importów ani kodu aplikacji,
- nie śledzi arbitralnie wartości między modułami,
- nie rozstrzyga biznesowego przeznaczenia pliku,
- może nie wykryć ścieżki budowanej przez bardzo dynamiczny helper,
- heurystyczne helpery zapisu wymagają review człowieka.

Nie należy usuwać testów ani dodawać szerokich wyjątków tylko po to, aby raport
był pusty. Findings mają kierować kolejnymi małymi migracjami.
