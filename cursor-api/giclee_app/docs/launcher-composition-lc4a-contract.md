# ETAP 4B / LC-4A — Classic Subprocess Launch Adapter

**Status:** LC-4A implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`
**Base:** `master` @ `9c66274e61e0cab2ca3c75f460a550c317f1d4fd`
**Data weryfikacji:** 2026-07-15

---

## 1. Cel pakietu

Wydzielić z `launcher.GicleeApp._launch()` wyłącznie klasyczną ścieżkę startu komponentu w osobnym procesie:

- ustalenie katalogu roboczego komponentu;
- rozwiązanie interpretera Pythona i budowa komendy `python -m ...`;
- przygotowanie zewnętrznego logu komponentu;
- start `subprocess.Popen()` z aktualnymi parametrami;
- bezpieczne zamknięcie uchwytu logu, jeżeli `Popen()` zgłosi błąd;
- zwrócenie strukturalnego wyniku do klasycznego launchera.

LC-4A nie zmienia trybu URL ani hosta inline. Nie scala klasycznego launchera ze Studio i nie zastępuje istniejącego `launcher_delegate.py`.

---

## 2. Wynik fresh reconnaissance

### 2.1 Stan klasycznego launchera

`launcher.GicleeApp._launch()` nadal posiada trzy różne ścieżki:

1. `url` — walidacja URL, `webbrowser.open()`, status lub dialog błędu;
2. `inline` — delegacja do `_show_inline()`;
3. `subprocess` — interpreter, komenda, log, `Popen`, lista procesów, status i watcher.

Ścieżka subprocess łączy obecnie dwie odpowiedzialności:

- start procesu i logu, które nie wymagają widgetów Tk;
- orchestration instancji aplikacji: `_running_procs`, `status_var`, `threading.Thread` i `_watch_proc()`.

LC-4A wydziela tylko pierwszą część.

### 2.2 Istniejący tor Studio

Studio używa `launcher_delegate.py`, który obsługuje URL i subprocess, ale ma inną semantykę:

- nie utrzymuje klasycznej listy `_running_procs`;
- używa nagłówka logu `start (studio)`;
- zwraca `LaunchResult` używany przez Studio;
- blokuje tryb inline, który Studio montuje przez własny `InlineHostView`;
- nie aktualizuje klasycznego statusu po zakończeniu procesu.

LC-4A nie importuje `launcher_delegate.py`, nie zmienia go i nie próbuje jeszcze tworzyć wspólnej abstrakcji dla obu shelli.

### 2.3 Granica po LC-3

Warstwa LC-3 jest zakończona. `_DragState`, event handlers i wybór ścieżki category/component pozostają poprawną orchestration Tk i nie wymagają dalszego `DragDropController`.

LC-4A rozpoczyna osobną granicę uruchamiania komponentów w `launcher.py`.

---

## 3. Nowy moduł

Implementacja utworzy:

```text
cursor-api/giclee_app/launcher_classic_subprocess.py
```

Moduł jest adapterem side-effectful, ale nie posiada UI ani stanu aplikacji.

### 3.1 Publiczne typy

```python
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, TextIO

from .component_loader import Component


class ClassicSubprocessOutcome(str, Enum):
    STARTED = "started"
    NO_PYTHON = "no_python"
    ERROR = "error"


@dataclass(frozen=True)
class ClassicSubprocessStart:
    outcome: ClassicSubprocessOutcome
    message: str = ""
    proc: subprocess.Popen[Any] | None = None
    log_file: TextIO | None = None


def start_classic_component_subprocess(
    comp: Component,
    *,
    logs_dir: Path,
) -> ClassicSubprocessStart:
    ...
```

Moduł ma jawne:

```python
__all__ = [
    "ClassicSubprocessOutcome",
    "ClassicSubprocessStart",
    "start_classic_component_subprocess",
]
```

### 3.2 Inwarianty wyniku

- `STARTED` oznacza, że `proc` nie jest `None`;
- `STARTED` może mieć `log_file=None`, gdy otwarcie logu nie powiodło się;
- `NO_PYTHON` ma `proc=None`, `log_file=None` i komunikat zwrócony przez `resolve_python_interpreter()`;
- `ERROR` ma `proc=None`, `log_file=None` i tekst wyjątku `OSError` z `Popen()`;
- adapter nie tworzy sztucznego procesu ani atrap wyniku.

Nie dodawać `assert` zależnych od optymalizacji Pythona jako jedynego zabezpieczenia runtime. Konstrukcja wyniku ma sama zachować powyższe inwarianty.

---

## 4. Zamrożona semantyka adaptera

### 4.1 Katalog roboczy i interpreter

Zachować aktualną kolejność operacji klasycznego launchera:

```python
cwd = get_component_cwd()
prefix, py_err = resolve_python_interpreter()
```

Jeżeli `prefix is None`:

```python
return ClassicSubprocessStart(
    ClassicSubprocessOutcome.NO_PYTHON,
    message=py_err,
)
```

Nie otwierać logu i nie wywoływać `Popen()`.

Komenda:

```python
cmd = [*prefix, "-m", comp.module_path]
```

Nie dodawać `shell=True`, dodatkowych flag interpretera ani zmiany `module_path`.

### 4.2 Log komponentu

Ścieżka zapisu:

```python
log_path = component_log_write_path(comp.folder_name, logs_dir=logs_dir)
```

`logs_dir` jest obowiązkowym argumentem keyword-only. Klasyczny launcher przekaże własne `_LOGS_DIR`, zachowując istniejący override point dla testów i kontrolowanych callerów.

Otwarcie:

```python
log_f = open(log_path, "a", encoding="utf-8", buffering=1)
```

Przed `Popen()` zapisać i wykonać `flush()`:

```python
f"\n\n========== {datetime.now().isoformat()} start ==========\n"
```

Nie zmieniać tekstu na `start (studio)`.

Jeżeli otwarcie lub przygotowanie logu zgłosi `OSError`:

- ustawić `log_f = None`;
- nadal spróbować uruchomić proces;
- nie propagować błędu logu;
- nie tworzyć alternatywnego pliku w checkoutcie.

### 4.3 Start procesu

Wywołanie ma zachować dokładnie:

```python
proc = subprocess.Popen(
    cmd,
    cwd=str(cwd),
    stdout=log_f or subprocess.DEVNULL,
    stderr=subprocess.STDOUT if log_f else subprocess.DEVNULL,
    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
)
```

Nie dodawać:

- `stdin`;
- `shell=True`;
- `close_fds`;
- zmiennych środowiskowych;
- ukrywania okna;
- timeoutu;
- waitera lub wątku.

### 4.4 Błąd `Popen()`

Jeżeli `subprocess.Popen()` zgłosi `OSError`:

1. jeżeli `log_f` istnieje, spróbować go zamknąć;
2. `OSError` z `close()` zignorować;
3. zwrócić:

```python
ClassicSubprocessStart(
    ClassicSubprocessOutcome.ERROR,
    message=str(exc),
)
```

Nie propagować `OSError` z `Popen()` i nie pozostawiać uchwytu logu w wyniku błędu.

### 4.5 Sukces

Po poprawnym `Popen()` zwrócić ten sam obiekt procesu i ten sam otwarty uchwyt logu:

```python
ClassicSubprocessStart(
    ClassicSubprocessOutcome.STARTED,
    proc=proc,
    log_file=log_f,
)
```

Adapter nie może:

- dopisywać procesu do `_running_procs`;
- uruchamiać `threading.Thread`;
- wywoływać `proc.wait()`;
- zapisywać exit markera;
- zamykać logu po sukcesie;
- aktualizować statusu;
- pokazywać dialogów.

Te obowiązki pozostają w klasie i `_watch_proc()`.

---

## 5. Dozwolone i zabronione zależności

### Dozwolone

- biblioteka standardowa: `subprocess`, `datetime`, `dataclasses`, `enum`, `pathlib`, typy;
- `.component_loader.Component`;
- `.component_logs.component_log_write_path`;
- `.runtime.get_component_cwd`;
- `.runtime.resolve_python_interpreter`.

### Zabronione

- `tkinter`, `messagebox`, `ttk`;
- `launcher.GicleeApp` lub import `launcher.py`;
- `launcher_delegate.py`;
- `launcher_studio.py`;
- `ui.inline_host`;
- Studio state lub routing;
- Shopify, backupy, remindery i usługi tła;
- bezpośredni import `Komponenty`.

---

## 6. Docelowa orchestration `GicleeApp._launch()`

Gałęzie URL i inline mają pozostać semantycznie niezmienione i występować przed ścieżką subprocess.

Klasyczny launcher zaimportuje:

```python
from .launcher_classic_subprocess import (
    ClassicSubprocessOutcome,
    start_classic_component_subprocess,
)
```

Po gałęziach URL i inline ścieżka subprocess ma mieć kształt:

```python
start = start_classic_component_subprocess(comp, logs_dir=_LOGS_DIR)

if start.outcome is ClassicSubprocessOutcome.NO_PYTHON:
    messagebox.showerror(
        "Brak Pythona",
        f"Nie mozna uruchomic komponentu '{comp.name}'.\n\n{start.message}",
    )
    return

if start.outcome is ClassicSubprocessOutcome.ERROR:
    messagebox.showerror(
        "Blad uruchomienia",
        f"Nie udalo sie uruchomic komponentu '{comp.name}':\n\n{start.message}",
    )
    return

proc = start.proc
if proc is None:
    raise RuntimeError("STARTED result without process")

self._running_procs.append(proc)
self.status_var.set(f"Uruchomiono: {comp.name} (PID {proc.pid})")
threading.Thread(
    target=self._watch_proc,
    args=(proc, comp.name, start.log_file),
    daemon=True,
).start()
```

Dopuszczalny jest równoważny fail-closed guard wyniku `STARTED`, ale nie wolno po cichu traktować niepoprawnego wyniku jako sukcesu lub no-op.

### W klasie pozostają

- wybór `url / inline / subprocess`;
- dialogi URL, brak Pythona i błąd startu;
- `webbrowser.open()`;
- `_show_inline()`;
- `_running_procs`;
- status sukcesu z PID;
- utworzenie wątku watchera;
- `_watch_proc()` i exit marker;
- `root.after()` po zakończeniu procesu.

### Z klasy znikają wyłącznie

- bezpośredni `get_component_cwd()` w ścieżce subprocess;
- bezpośredni `resolve_python_interpreter()` w ścieżce subprocess;
- budowa `cmd` dla subprocess;
- otwarcie startowego logu;
- bezpośredni `subprocess.Popen()` w `_launch()`;
- cleanup logu po błędzie `Popen()`.

---

## 7. Jawnie poza zakresem LC-4A

Nie zmieniać:

- `launcher_delegate.py` ani testów jego aktualnej semantyki;
- Studio Preview i `InlineHostView`;
- trybu URL klasycznego launchera;
- `_show_inline()`, `_show_tiles()` i geometrii inline;
- finance navigation callback;
- `_watch_proc()`;
- treści exit markera;
- listy `_running_procs`;
- zamykania launchera i pozostawiania subprocessów aktywnych;
- `component_logs.py` i runtime paths;
- `Component` ani `component.json`;
- pollingu, backupów i reminderów;
- DnD, shortcutów, kategorii i rendererów;
- workflow CI;
- Studio, Shopify, deploymentu, plików startowych GPT i ZIP-a wiedzy.

LC-4A nie jest autoryzacją do wspólnego `ComponentLauncher` dla klasycznego launchera i Studio. Taka decyzja wymaga fresh review po stabilizacji klasycznego adaptera.

---

## 8. Testy implementacyjne

Nowy focused suite:

```text
cursor-api/tests/test_launcher_classic_subprocess.py
```

Musi pokryć co najmniej:

1. `NO_PYTHON` zwraca dokładny komunikat interpretera;
2. `NO_PYTHON` nie otwiera logu i nie wywołuje `Popen()`;
3. komenda zachowuje `[*prefix, "-m", comp.module_path]`;
4. adapter używa `get_component_cwd()`;
5. adapter przekazuje dokładny `logs_dir` do `component_log_write_path()`;
6. log jest otwierany w trybie append, UTF-8 i line-buffered;
7. klasyczny start marker nie zawiera `(studio)`;
8. marker jest flushowany przed `Popen()`;
9. błąd otwarcia logu nie blokuje startu;
10. bez logu stdout i stderr trafiają do `DEVNULL`;
11. z logiem stdout trafia do uchwytu, a stderr do `STDOUT`;
12. `cwd` jest konwertowany do `str`;
13. `creationflags` zachowuje `CREATE_NEW_PROCESS_GROUP` lub `0`;
14. `Popen()` `OSError` daje `ERROR` z tekstem wyjątku;
15. uchwyt logu jest zamykany po błędzie `Popen()`;
16. błąd `close()` nie maskuje pierwotnego błędu startu;
17. sukces zwraca ten sam proces i uchwyt logu;
18. adapter nie uruchamia wątku i nie wywołuje `wait()`;
19. adapter nie importuje Tk, launchera, delegate ani Studio;
20. `__all__` zawiera publiczny kontrakt;
21. `_launch()` nadal najpierw obsługuje URL;
22. `_launch()` nadal deleguje inline do `_show_inline()`;
23. klasyczna gałąź subprocess deleguje do nowego adaptera z `_LOGS_DIR`;
24. `NO_PYTHON` zachowuje aktualny tytuł i tekst dialogu;
25. `ERROR` zachowuje aktualny tytuł i tekst dialogu;
26. sukces dopisuje proces do `_running_procs` dokładnie raz;
27. sukces ustawia aktualny status z nazwą i PID;
28. sukces uruchamia dokładnie jeden daemon watcher z `_watch_proc`, nazwą i zwróconym logiem;
29. błąd lub brak Pythona nie mutuje `_running_procs` i nie uruchamia watchera;
30. `_watch_proc()` pozostaje w `launcher.py` i zachowuje exit marker, usunięcie procesu oraz `root.after()`.

Testy nie mogą uruchamiać prawdziwego procesu, otwierać prawdziwej przeglądarki ani wymagać ekranu GUI.

Focused regression set powinien obejmować:

```text
tests/test_launcher_classic_subprocess.py
tests/test_launcher_delegate.py
tests/test_launcher_logs_appdata.py
tests/test_launcher_composition.py
tests/test_launcher_component_tile_style.py
tests/test_studio_imports.py
tests/test_giclee_app_packaging.py
```

Po focused PASS obowiązują `git diff --check`, scope guard, Hermetic, Tk GUI i full baseline z artifact/JUnit/inventory.

---

## 9. Allowlista implementacyjna

Implementation PR ma zawierać dokładnie pięć plików:

1. `cursor-api/giclee_app/launcher_classic_subprocess.py` — **nowy**;
2. `cursor-api/giclee_app/launcher.py` — cienka delegacja klasycznej ścieżki subprocess;
3. `cursor-api/tests/test_launcher_classic_subprocess.py` — **nowy**;
4. `cursor-api/giclee_app/docs/launcher.md` — wpis LC-4A;
5. `cursor-api/giclee_app/docs/launcher-composition-lc4a-contract.md` — status implementacji.

Każda konieczna aktualizacja istniejącego source guardu poza allowlistą wymaga najpierw jawnej korekty tego kontraktu. Helpery, workflowy techniczne i pliki tymczasowe nie mogą pozostać w finalnym diffie.

---

## 10. Kryteria ukończenia LC-4A

LC-4A jest zakończony, gdy:

- start klasycznego subprocessu znajduje się w `launcher_classic_subprocess.py`;
- adapter nie ma zależności Tk ani stanu aplikacji;
- `_launch()` zachowuje wybór trybu i UI orchestration;
- URL i inline pozostają bez zmiany semantyki;
- `_watch_proc()` pozostaje w klasie;
- `launcher_delegate.py` i Studio pozostają bez zmian;
- finalny diff obejmuje dokładnie pięć allowlistowanych plików;
- focused suite przechodzi;
- `git diff --check` jest czysty;
- finalny Stage 2 jest zielony na exact headzie;
- artifact potwierdza 0 failures/errors, a runtime inventory 0 parse errors/findings;
- PR nie ma nierozwiązanych review threads.

---

## 11. Następny krok po LC-4A

Dopiero po wdrożeniu i fresh review ocenić osobno:

1. klasyczny URL adapter lub pozostawienie URL w klasie jako małej orchestration;
2. klasyczny inline import/builder adapter;
3. lifecycle hosta inline i geometrię okna;
4. ewentualne współdzielenie czystych prymitywów ze Studio bez łączenia shelli;
5. przejście do LC-5 BackgroundServices.

Ten kontrakt nie autoryzuje żadnego z tych pakietów.