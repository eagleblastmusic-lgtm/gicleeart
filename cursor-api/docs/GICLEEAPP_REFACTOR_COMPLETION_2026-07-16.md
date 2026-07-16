# GicleeApp — zakończenie izolacji i refaktoru

Data zamknięcia zakresu: **2026-07-16**  
Stan bazowy po zakończeniu: `master@a104922df35d0cd0dfe80fc5fce5ea7f470678ec`

## Decyzja końcowa

Zakres stabilizacji RC1, izolacji runtime oraz bezpiecznego refaktoru repozytorium jest zakończony.

Klasyczny GicleeApp pozostaje stabilnym produkcyjnym launcherem. Studio Preview i produkcyjne Giclée Studio są osobnymi profilami uruchomieniowymi korzystającymi ze wspólnego kodu komponentów i wspólnych danych biznesowych, lecz z rozdzielonym stanem shella i logami.

Przebudowa wizualna Studio nie była częścią tego etapu i pozostaje zamrożona do osobnej decyzji produktowej.

## Kanoniczne entrypointy

```text
python -m giclee_app                  # klasyczny GicleeApp
python -m giclee_app.studio_preview   # Giclée Studio Preview
python -m giclee_app.studio           # produkcyjne Giclée Studio
```

## Zakończone strumienie

### Stabilizacja launchera i lifecycle

- deferred exception callbacks oraz bezpieczne raportowanie błędów;
- blokada skrótów launchera podczas aktywnych dialogów;
- lifecycle guards dla asynchronicznych callbacków widoków;
- scoped mouse-wheel bindings i dokładne unbind przy teardown;
- ochrona Giclée Frame przed nieaktualnymi `after_idle` i generacjami widoku;
- manualne smoke Windows dla kluczowych przepływów launchera i Studio.

### Izolacja Studio

- jawne, niemutowalne profile aplikacji;
- osobne namespace stanu i shell/perf logów;
- kontrakt `availability` komponentów: `classic`, `studio_preview`, `studio`;
- kanały `stability`: `stable`, `preview`, `experimental`, `legacy`;
- produkcyjne Studio dopuszcza wyłącznie komponenty dostępne dla `studio` w kanale `stable`;
- brak kopiowania katalogu `Komponenty/` i brak osobnego forka aplikacji.

### Granice danych i bezpieczeństwo

- mutable state, cache, logi i backupy kierowane poza source checkout;
- lokalna sesja Shopify jawnie ignorowana przez Git;
- polityka prywatnego raportowania podatności i rotacji po ekspozycji sekretu;
- guard przeciw plikom śledzonym większym niż 25 MiB poza Git LFS;
- runtime source-write inventory jako blokująca kontrola CI.

### Konsolidacja architektury

- jedno kanoniczne źródło wersji aplikacji;
- Theme Page Editor korzysta z bezpośredniego importu usług zamiast bootstrap monkey-patcha;
- `layout/theme.liquid` zredukowany do cienkiego pliku kompozycyjnego;
- warstwa conditional CSS przeniesiona do `giclee-theme-inline-overrides.liquid`;
- post-layout runtime przeniesiony i podzielony na domeny:
  - `giclee-theme-runtime-general.liquid`;
  - `giclee-theme-runtime-navigation.liquid`;
  - `giclee-theme-runtime-photo-mockup.liquid`;
  - `giclee-theme-runtime-footer.liquid`;
- testy SHA-256 i rekonstrukcji byte-for-byte zabezpieczają mechaniczne ekstrakcje.

### CI

- Hermetic smoke na Windows/Python 3.13;
- blokujący Tk GUI smoke;
- pełny pytest baseline;
- jednorazowy retry całej suity wyłącznie dla dokładnie rozpoznanej przejściowej awarii odczytu `init.tcl`/`tk.tcl`;
- retry nie maskuje assertion failures, błędów aplikacji ani innych wyjątków Tcl;
- artefakty JUnit, raport pytest i inventory są zachowywane dla każdego finalnego przebiegu.

## Łańcuch zatwierdzonych zmian

| PR | Zakres |
|---:|---|
| #119–#122 | stabilizacja launchera, lifecycle guards i izolacja runtime/state |
| #123 | availability i stability komponentów |
| #125 | produkcyjny profil Giclée Studio |
| #126 | kanoniczne źródło wersji |
| #127 | security i secret-handling contract |
| #128 | kontrolowany retry przejściowych awarii Tcl/Tk |
| #129 | usunięcie ostrzeżeń deprecacyjnych |
| #130 | tracked large-file guard |
| #131 | bezpośrednie wiring usług Theme Page Editor |
| #132 | ekstrakcja inline CSS z `theme.liquid` |
| #133 | ekstrakcja post-layout runtime |
| #134 | podział runtime motywu na domeny |

PR #124 był superseded po squash-merge zależnego PR i został zastąpiony czystym branchem bez przepisywania historii.

## Finalny baseline

Ostatni pełny przebieg zatwierdzający podział runtime motywu:

```text
Stage 2 CI run #507
Hermetic smoke: PASS
Tk GUI smoke: PASS
pytest: 2885 passed, 1 skipped
warnings: 0
runtime inventory: 737 plików Python, 0 parse errors, 0 findings
review threads: 0
```

## Świadomie niezakończone poza tym zakresem

Poniższe punkty nie są defektem zamkniętego refaktoru i wymagają osobnej decyzji:

- przebudowa wizualna i rozwój produktu Giclée Studio;
- uruchomienie Shopify theme preview oraz wizualny smoke w przeglądarce;
- deploy lub mutacja aktywnego motywu Shopify;
- masowa klasyfikacja istniejących komponentów do nowych kanałów;
- centralny `_shared/file_utils.py`, ujednolicenie legacy parserów DnD i kosmetyczna migracja lokalnego toastu;
- usunięcie albo implementacja placeholdera `stronaglownav2`;
- historia Git / Git LFS migration — wyłącznie jako osobny destrukcyjny projekt z backupem.

## Granica dalszych prac

Od tego punktu nowe zadania powinny zaczynać się z aktualnego `master`, na osobnym branchu, z małym kontraktem i dokładnym finalnym CI. Nie należy kontynuować refaktoru dla samego refaktoru. Każda kolejna zmiana powinna odpowiadać konkretnemu celowi produktu, defektowi lub mierzalnemu ryzyku.
