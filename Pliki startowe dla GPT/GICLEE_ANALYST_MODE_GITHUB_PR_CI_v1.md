# TRYB GITHUB / PR / CI — GicleeArt monorepo

Tryb operacyjny dla pracy na `eagleblastmusic-lgtm/gicleeart` przez draft PR, Hermetic, Full baseline, artifact review i kontrolowany merge.

Stosuj razem z: `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md`, `CURRENT_APP_STATE.md`, `GICLEE_ANALYST_LESSONS_LEARNED_v1.md`, [GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md](GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md).

---

## Autoryzacja merge (obowiązkowa)

Model może wykonać squash merge z `expected_head_sha` **wyłącznie** wtedy, gdy:

- użytkownik zlecił **bezpośrednią implementację** i zakres zadania obejmuje doprowadzenie PR-a do merge'u, **albo**
- użytkownik udzielił **wyraźnej zgody** na merge.

**Zielone CI samo w sobie nie stanowi autoryzacji.**

Samo review, dostęp do repo lub przygotowanie brancha **nie** daje zgody na merge.

---

## Przed rozpoczęciem zmiany

Ustal i zapisz:

```text
repository
current master SHA
branch base SHA
open PRs
changed files
existing tests
current inventory
expected inventory delta
protected files
allowed final diff
```

Następnie:

1. Utwórz branch z **dokładnego** aktualnego `master`.
2. Wykonaj pierwszy mały commit (GitHub nie otworzy PR bez różnicy base/head).
3. Otwórz **draft PR**.
4. Opisz cel, kontrakt, guardraile i plan walidacji.

---

## Draft PR

Draft uruchamia szybki **Hermetic smoke**.

W draftcie model:

- wdraża zmianę,
- dodaje focused tests,
- sprawdza finalną listę plików,
- aktualizuje opis PR,
- **nie** uruchamia pełnego merge workflow przed zielonym Hermetic.

---

## Ready for review

Dopiero po zielonym Hermetic:

1. Oznacz PR jako **ready for review**.
2. Uruchom Tk GUI.
3. Uruchom Full baseline.
4. Pobierz **wszystkie** artifacty.
5. Odczytaj `pytest.txt`, `junit.xml`, runtime-write inventory.
6. Sprawdź oczekiwaną deltę inventory.

---

## Po failure

**Bezwzględna zasada: nie wykonuj blind rerun.**

Po failure:

1. Cofnij PR do **draft**.
2. Pobierz artifact.
3. Odczytaj dokładny traceback.
4. Porównaj failure z poprzednim przebiegiem.
5. **Sklasyfikuj:** product / test / environment / API.
6. Ustal root cause.
7. Popraw **tylko** realną przyczynę.
8. **Retry wyłącznie czerwonego joba** — dopiero po artifact analysis i klasyfikacji środowiskowej.

### Run attempt vs artifact z retry

- Odróżniaj numer **run attempt** od **finalnego artifactu**.
- Finalny artifact musi pochodzić z **exact head** brancha PR — nie z wcześniejszego attemptu po nowym pushu.
- Merge gate i ready gate wymagają artifactu z head SHA widocznego w PR w momencie review.

Nie wolno maskować testu, zmieniać go na skip ani łapać dowolnego wyjątku tylko po to, aby CI stało się zielone.

---

## Finalny review przed merge

Potwierdź:

```text
behind_by: 0
review threads: 0
PR mergeable
head SHA niezmieniony
dokładna finalna lista plików
brak plików tymczasowych
brak workflowu diagnostycznego
brak patchera
wszystkie wymagane joby green
artifacty pobrane i przeczytane
inventory zgodne z oczekiwaną deltą
użytkownik autoryzował merge (patrz sekcja Autoryzacja)
```

---

## Merge

- Domyślnie **squash merge**.
- Zawsze z **`expected_head_sha`**.
- Nigdy nie merge'uj czerwonego lub nieprzeczytanego pipeline'u.
- Po merge odczytaj nowy commit `master`.
- Dopiero wtedy rozpocznij następny etap.

---

## Synchronizacja brancha z nowym masterem

Gdy branch jest za `master`:

- **nie** używaj force-push,
- wykonaj kontrolowany **true merge** `master` do brancha,
- ponownie sprawdź diff produktu,
- upewnij się, że odziedziczone pliki infrastruktury nie pojawiły się jako dodatkowy produktowy zakres.

---

## Tcl/Tk i CI — trwałe zasady runnera

### Windows runner

- `windows-latest` może zmienić system operacyjny bez zmiany konfiguracji projektu.
- Stage 2 Tk GUI powinien być jawnie przypięty do **`windows-2022`**.
- Nie zakładaj, że `windows-latest` jest stabilną platformą.
- Zmiana obrazu runnera = zmiana zależności.

### Retry Tk — antywzorzec

Nie wolno ponawiać `Tk.__init__()` na tym samym obiekcie po częściowo nieudanym `_tkinter.create(...)`.

Obiekt może pozostać częściowo zainicjalizowany (błędy typu `invalid command name "tcl_findLibrary"`).

### Runtime Tcl/Tk

Bezpieczny model:

- używać bezpośrednio runtime Tcl/Tk z `actions/setup-python`,
- jawnie ustawić `TCL_LIBRARY` i `TK_LIBRARY`,
- sprawdzić obecność `init.tcl`, `tk.tcl`, `spinbox.tcl`, `ttk/defaults.tcl`, `ttk/winTheme.tcl`,
- preflight: `tk.Tk`, `tk.Spinbox`, `ttk.Style`, `tcl_library`, `tk_library`.

### Full-suite warm-up

Szybki Tk smoke **nie** gwarantuje stabilności po długim pełnym suite.

Historyczny failing test Tk powinien być:

- wykonywany w Tk GUI smoke,
- wykonywany jako blokujący warm-up na tej samej maszynie Full baseline,
- nadal wykonywany ponownie w normalnym pełnym zestawie.

To nie jest skip ani maskowanie — to jawna stabilizacja runtime runnera przy zachowaniu pełnego pokrycia.

### Artifacty

Zielony status GitHuba **nie wystarcza**.

Czytaj: liczbę passed/skipped/failures/errors, JUnit, inventory, parse errors, scanned files.

Szczegóły historycznych przebiegów → `CURRENT_APP_STATE.md` (sekcja `gicleeart`) lub `GICLEE_ANALYST_LESSONS_LEARNED_v1.md` (przykłady **HISTORICAL**).
