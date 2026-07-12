# Stage 2 Tcl/Tk transient retry

## Problem

Self-hosted Windows runner potrafi sporadycznie zwrócić:

```text
_tkinter.TclError: Can't find a usable init.tcl
...
init.tcl: couldn't read file ...: No error
```

Błąd pojawiał się po udanym preflighcie i po wielu wcześniejszych testach Tk.
Ten sam niezmieniony commit przechodził po ponownym uruchomieniu Full baseline.
Oznacza to przejściowy problem odczytu pliku runtime, a nie regresję aplikacji.

## Dwie warstwy ochrony

### Unikalny runtime dla każdego runu

`.github/scripts/prepare-tk-runtime.ps1` buduje katalog na podstawie:

- `RuntimeName`,
- `GITHUB_RUN_ID`,
- `GITHUB_RUN_ATTEMPT`,
- `GITHUB_JOB`.

Rerun nie używa więc katalogu poprzedniej próby i nie usuwa plików aktywnego lub
historycznego joba o tej samej nazwie.

### Dokładnie jeden retry konstrukcji Tk

`tests/conftest.py` aktywuje adapter wyłącznie, gdy:

- `GITHUB_ACTIONS=true`,
- istnieje jawne `TCL_LIBRARY` przygotowane przez Stage 2.

Adapter przechwytuje wyłącznie `tk.TclError` zawierający dokładną sygnaturę:

```text
Can't find a usable init.tcl
```

Przed drugą próbą wykonuje krótki read probe `TCL_LIBRARY/init.tcl`. Następnie
ponawia `tk.Tk.__init__` jeden raz.

Nie są ponawiane:

- inne `TclError`,
- błędy aplikacji,
- assertions,
- exceptions testów,
- drugi identyczny błąd init.tcl.

Druga porażka pozostaje normalnym, blokującym failure.

## Zakres

Rozwiązanie działa tylko w testach GitHub Actions. Nie zmienia produkcyjnego
GicleeApp i nie jest aktywne przy zwykłym lokalnym uruchomieniu pytest bez
zmiennych CI.

## Testy kontraktu

`tests/test_tcl_transient_retry.py` sprawdza:

1. aktywację wyłącznie dla GitHub Actions z `TCL_LIBRARY`,
2. jedną udaną ponowną próbę dokładnej sygnatury,
3. brak retry dla innego `TclError`,
4. blokowanie po drugiej porażce,
5. unikalną tożsamość katalogu w skrypcie PowerShell.

## Interpretacja CI

Retry jednej konstrukcji Tk nie zastępuje pełnego rerunu joba przy innych
problemach środowiska. Artifact i JUnit nadal są źródłem prawdy. Powtarzający się
drugi failure init.tcl należy traktować jako realny problem runnera i pozostawić
job czerwony.
