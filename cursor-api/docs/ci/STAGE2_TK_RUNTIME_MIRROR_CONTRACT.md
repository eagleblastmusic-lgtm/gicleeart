# Stage 2 CI — Per-run Tcl/Tk Runtime Mirror Contract

**Status:** CI runtime mirror implemented  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `88fa1534e42156be89dccb0d43475da152dfd111`  
**Data weryfikacji:** 2026-07-15

## 1. Blokujący problem

Dwa kolejne pełne przebiegi Stage 2 dla niezmienionego headu LC-3C zakończyły się pojedynczymi, późnymi awariami środowiska Tcl/Tk:

1. run `29378091608`: po 2436 zaliczonych testach hostowany runtime utracił `tk8.6/icons.tcl`;
2. run `29378342719`: po 2436 zaliczonych testach kolejny świeży runner utracił `tk8.6/ttk/classicTheme.tcl`.

W obu przebiegach:

- Hermetic smoke był zielony;
- dedykowany Tk GUI smoke był zielony na tym samym SHA;
- preflight i warmup Tcl/Tk na full-baseline runnerze były zielone;
- failure wystąpił dopiero późno w pełnym pytest przy tworzeniu kolejnego `customtkinter.CTk()`;
- runtime-write inventory miał 720 plików, 0 parse errors i 0 findings;
- kod LC-3C nie dotyka Studio, CustomTkinter ani runtime Tcl/Tk.

To jest powtarzalna awaria integralności bezpośrednio używanego katalogu `actions/setup-python`, a nie regresja produktu.

## 2. Finding historyczny

Repozytorium wcześniej używało unikalnej kopii Tcl/Tk w `RUNNER_TEMP`, ale commit `bf1b0902eeadd5cde7b9e8b62a8ae96b03fc3ff1` zastąpił ją bezpośrednim użyciem toolcache i ograniczonym preflightem pięciu plików.

Obecny kontrakt sprawdza m.in.:

- `init.tcl`;
- `tk.tcl`;
- `spinbox.tcl`;
- `ttk/defaults.tcl`;
- `ttk/winTheme.tcl`.

Nie chroni jednak całego drzewa przed późniejszym brakiem innych zależności, takich jak `icons.tcl` lub `ttk/classicTheme.tcl`.

## 3. Decyzja architektoniczna

Stage 2 ma korzystać z **pełnego, per-run mirroru drzewa Tcl/Tk** utworzonego pod `RUNNER_TEMP`.

Mirror jest granicą CI, nie częścią aplikacji. Produkcyjny kod, testy GUI i zachowanie Tk nie mogą być zmieniane w celu ukrycia wadliwego runnera.

### Tożsamość mirroru

Katalog docelowy musi być jednoznaczny dla:

- `RuntimeName`;
- `GITHUB_RUN_ID`;
- `GITHUB_RUN_ATTEMPT`;
- `GITHUB_JOB`.

Nie wolno współdzielić mirroru między jobami, runami ani próbami.

### Zakres kopiowania

Kopiowane jest całe źródłowe drzewo:

`<python-root>/tcl/**`

Nie jest kopiowany interpreter Python, `Lib`, `site-packages` ani żaden katalog repozytorium.

### Integralność

Po kopiowaniu skrypt musi:

1. zbudować manifest wszystkich plików źródła i mirroru według ścieżki względnej;
2. wymagać identycznego zestawu ścieżek;
3. wymagać identycznych rozmiarów plików;
4. wymagać identycznych SHA-256 dla każdego pliku;
5. jawnie potwierdzić obecność co najmniej:
   - `tcl*/init.tcl`;
   - `tk*/tk.tcl`;
   - `tk*/icons.tcl`;
   - `tk*/spinbox.tcl`;
   - `tk*/ttk/ttk.tcl`;
   - `tk*/ttk/defaults.tcl`;
   - `tk*/ttk/classicTheme.tcl`;
   - `tk*/ttk/winTheme.tcl`.

Błąd kopiowania lub manifestu ma zatrzymać job przed testami.

### Zmienne środowiskowe

`TCL_LIBRARY` i `TK_LIBRARY` muszą wskazywać katalogi wewnątrz mirroru, nigdy bezpośredni toolcache.

Skrypt zapisuje je zarówno do bieżącego procesu, jak i do `GITHUB_ENV`.

### Preflight

Po ustawieniu mirroru skrypt tworzy prawdziwy `tk.Tk()`, sprawdza:

- `tcl_library` i `tk_library` wskazujące mirror;
- `info patchlevel`;
- utworzenie `Spinbox`;
- dostępność motywów `ttk.Style`.

Nie wolno retryować `Tk.__init__` na częściowo zainicjalizowanym obiekcie.

## 4. Weryfikacja przed pełnym baseline

Skrypt otrzyma tryb `-VerifyOnly`, który:

- nie kopiuje ponownie źródła;
- waliduje istniejące `TCL_LIBRARY` i `TK_LIBRARY`;
- ponownie sprawdza manifest mirroru zapisany podczas przygotowania;
- tworzy nowy, niezależny root Tk i widgety preflightu;
- kończy job czerwono przed pełnym pytest, gdy mirror został naruszony.

Workflow full-baseline wywołuje `-VerifyOnly` po warmupie, bezpośrednio przed całym pytest.

## 5. Zakres implementacji

Dozwolone pliki:

- `.github/scripts/prepare-tk-runtime.ps1`;
- `.github/workflows/stage2-ci-baseline.yml`;
- `cursor-api/tests/test_tcl_transient_retry.py`;
- `cursor-api/docs/ci/STAGE_2_CI_RUNBOOK.md`;
- `cursor-api/docs/repository_safety/STAGE2_TCL_TRANSIENT_RETRY.md`;
- ten kontrakt — wyłącznie aktualizacja statusu po wdrożeniu.

Nie są dozwolone zmiany w:

- kodzie produkcyjnym `giclee_app`;
- testach Studio/Giclée Frame poza testem kontraktu skryptu;
- konfiguracji pytest;
- wymaganiach i wersjach zależności;
- LC-3C PR #79;
- danych użytkownika;
- plikach startowych i ZIP-ie;
- Shopify, deployu ani migracjach.

## 6. Testy focused

Focused suite musi potwierdzić statycznie i behawioralnie:

1. skrypt tworzy unikalny katalog per run/job/attempt;
2. kopiowane jest wyłącznie pełne `<python-root>/tcl`;
3. mirror nie znajduje się w repozytorium ani toolcache;
4. `TCL_LIBRARY/TK_LIBRARY` wskazują mirror;
5. manifest obejmuje wszystkie pliki i SHA-256;
6. wymagane pliki zawierają `icons.tcl` i `classicTheme.tcl`;
7. `-VerifyOnly` nie wykonuje kopiowania;
8. preflight nadal tworzy Tk, Spinbox i `ttk.Style`;
9. retry tego samego obiektu Tk pozostaje wyłączony;
10. workflow wywołuje przygotowanie w Tk GUI i full baseline;
11. workflow wywołuje `-VerifyOnly` po warmupie, przed całym pytest;
12. full baseline pozostaje blokujący i zawsze publikuje artefakt.

Minimalny focused command:

```powershell
python -m pytest -q tests/test_tcl_transient_retry.py
```

Po focused PASS:

- `git diff --check`;
- twardy scope guard;
- draft Hermetic;
- ready Stage 2 z pełnym Tk GUI i full baseline;
- JUnit i runtime-write inventory;
- exact-head review.

## 7. Walidacja naprawy

CI fix jest zaakceptowany dopiero, gdy na jego exact headzie:

- Hermetic jest zielony;
- Tk GUI jest zielony;
- warmup jest zielony;
- `-VerifyOnly` jest zielony;
- full baseline jest zielony;
- artifact potwierdza 0 failures/errors;
- inventory ma 0 parse errors i 0 findings.

Po merge fixu PR #79 musi zostać zsynchronizowany z nowym `master` zwykłym merge commit, bez rebase/force push. Następnie Stage 2 PR #79 ma zostać uruchomiony ponownie na nowym exact headzie.

## 8. Rollback

Zmiana dotyczy wyłącznie CI. Rollback to revert jednego commitu implementacyjnego. Nie wymaga migracji, zmian AppData ani zmian kodu aplikacji.
