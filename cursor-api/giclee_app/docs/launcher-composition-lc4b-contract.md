# ETAP 4B / LC-4B — Neutral Inline Builder Invocation

**Status:** LC-4B implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`
**Base:** `master` @ `c2d5f927a9958f3f34e7a16f010455b3ed2825e5`
**Data weryfikacji:** 2026-07-15

---

## 1. Cel pakietu

Wydzielić logiczne wywołanie funkcji `build_view` komponentów (inline) do neutralnego, współdzielonego helpera:
- Analiza sygnatury buildera przy użyciu `inspect.signature` w celu detekcji obsługi parametru `on_open_component` (lub obecności `**kwargs`);
- Bezpieczne wywołanie buildera dokładnie raz;
- Usunięcie niebezpiecznego mechanizmu catch-and-retry na `TypeError` z klasycznego launchera (który maskował błędy wewnętrzne komponentów i powodował podwójne wykonanie side-effectów);
- Współdzielenie tej samej, czystej logiki wywołania między klasycznym launcherem (`launcher.py`) a Studio (`giclee_app/ui/inline_host.py`).

---

## 2. Stan po LC-4A

Ścieżka klasycznego uruchamiania w osobnym procesie (subprocess) została w pełni odizolowana w module `launcher_classic_subprocess.py`. W `launcher.py` pozostała jedynie cienka orkiestracja. Następnym logicznym krokiem w reorganizacji launchera jest uporządkowanie sposobu montowania i uruchamiania komponentów w trybie `inline`.

---

## 3. Pełny wynik fresh reconnaissance

Klasyczny launcher (`launcher.py`) w metodzie `_show_inline()` wykonuje synchroniczny import modułu komponentu, weryfikuje obecność callable `build_view` i wywołuje go z obsługą wsteczną:
```python
try:
    try:
        view = builder(
            self._inline_host,
            on_back,
            on_open_component=self._open_component_by_folder,
        )
    except TypeError:
        view = builder(self._inline_host, on_back)
except Exception as e:
    messagebox.showerror(comp.name, f"Blad budowy widoku:\n{e}")
```

Studio (`giclee_app/ui/inline_host.py`) z kolei importuje moduł asynchronicznie i montuje go w CustomTkinterze, używając do wywołania prywatnych helperów `_supports_on_open_component` i `_invoke_build_view`, które bazują na `inspect.signature`.

---

## 4. Inwentaryzacja build_view

W repozytorium zidentyfikowano 32 komponenty posiadające funkcję `build_view`. Oto szczegółowa inwentaryzacja:

| Ścieżka pliku | Folder | Sygnatura | on_open_component | **kwargs / *args | Typ wyniku | Uwagi |
|---|---|---|---|---|---|---|
| `Komponenty/analytics/view.py` | `analytics` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/blog/view.py` | `blog` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/cenyMarketing/view.py` | `cenyMarketing` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/dnr/view.py` | `dnr` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/dokumentysprzedazy/view.py` | `dokumentysprzedazy` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/faq/view.py` | `faq` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/filozofiamarki/view.py` | `filozofiamarki` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/finanse/view.py` | `finanse` | `(parent, on_back, on_open_component=None)` | Tak | Nie | `tk.Widget` | Zwraca Frame, jawna obsługa cross-nawigacji |
| `Komponenty/gicleeframe/view.py` | `gicleeframe` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/kalkulacja/view.py` | `kalkulacja` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/karuzela/view.py` | `karuzela` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/katalog/view.py` | `katalog` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/kontakt/view.py` | `kontakt` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/kpir/view.py` | `kpir` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/ksiegowosc/view.py` | `ksiegowosc` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/limity/view.py` | `limity` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/losujobraz/view.py` | `losujobraz` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/obrazy/view.py` | `obrazy` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/passepartout/view.py` | `passepartout` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/planer/view.py` | `planer` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/poczta/view.py` | `poczta` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/produkcja/view.py` | `produkcja` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/socialmedia/view.py` | `socialmedia` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/stronablogu/view.py` | `stronablogu` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/stronaglowna/view.py` | `stronaglowna` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/stronaproduktu/view.py` | `stronaproduktu` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/submenukatalog/view.py` | `submenukatalog` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/tldobio/view.py` | `tldobio` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/wlasnafotografia/view.py` | `wlasnafotografia` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/wspolpraca/view.py` | `wspolpraca` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/wzorzecszablonu/view.py` | `wzorzecszablonu` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |
| `Komponenty/zadania/view.py` | `zadania` | `(parent, on_back)` | Nie | Nie | `tk.Widget` | Zwraca Frame |

**Kluczowy wniosek:** Jedynym komponentem wymagającym trzeciego parametru (`on_open_component`) jest `finanse`. Wszystkie pozostałe komponenty deklarują wyłącznie `(parent, on_back)`. Żaden z builderów nie jest dekorowany w sposób uniemożliwiający analizę sygnatury.

---

## 5. Porównanie klasycznego launchera i Studio

### Klasyczny launcher (`launcher.py`):
- Montuje widok w `self._inline_host` (typu `ttk.Frame`);
- Używa synchronicznego importu;
- Obsługuje `on_open_component` poprzez `self._open_component_by_folder`;
- Posiada podatność na podwójne wywołanie buildera przy błędach typu `TypeError` (retry block);
- Dokonuje manualnego `pack(fill="both", expand=True)` na zwróconym widoku, jeśli ten dziedziczy po `tk.Widget` lub `ttk.Frame`.

### Studio (`giclee_app/ui/inline_host.py`):
- Dziedziczy po `ctk.CTkFrame`;
- Importuje asynchronicznie za pomocą wątku roboczego (`run_async`);
- Wykorzystuje `inspect.signature` do selektywnego przekazywania `on_open_component`;
- Nie ponawia prób po wystąpieniu `TypeError` wewnątrz buildera;
- Maskuje hasła i sekrety z komunikatów o błędach za pomocą regexów.

---

## 6. Analiza TypeError retry

Obecna implementacja w `launcher.py` przechwytuje **dowolny** `TypeError` zgłoszony podczas wywołania buildera z trzema argumentami. Jeśli `builder()` rzuci `TypeError` wewnątrz swojego kodu (np. z powodu błędnej operacji na typach wewnątrz logiki komponentu), klasyczny launcher zakłada błędną sygnaturę i wykonuje ponowne wywołanie: `builder(self._inline_host, on_back)`.

### Zagrożenia:
1. **Maskowanie błędów:** Oryginalny błąd (np. błąd typowania wewnątrz komponentu) jest całkowicie ukrywany, a programista widzi jedynie ewentualny błąd z drugiego wywołania (lub sukces, jeśli drugie wywołanie też ulegnie awarii, ale w inny sposób).
2. **Double execution side-effects:** Komponent podczas pierwszej próby może wykonać częściową inicjalizację (np. zapisać dane, założyć sub-widgety, zarejestrować globalne listenery), a ponowne wywołanie uruchomi te efekty uboczne po raz drugi, co może doprowadzić do niespójności lub awarii.

---

## 7. Ocenione kandydatury granicy

### A. URL launch adapter
- **Zakres:** Wydzielenie obsługi linków URL z `_launch()`.
- **Decyzja:** Odrzucono. Logika ta zajmuje zaledwie kilka linii bez żadnej złożoności algorytmicznej. Jej wydzielenie wygenerowałoby niepotrzebny boilerplate bez realnych korzyści architektonicznych.

### B. Neutral Inline Builder Invocation
- **Zakres:** Wydzielenie logiki analizy sygnatury oraz wywołania buildera do małego, neutralnego i współdzielonego modułu `launcher_inline_builder.py`.
- **Decyzja:** **Wybrana**. Ujednolica zachowanie obu launcherów (klasycznego oraz Studio) w kwestii analizy i wywoływania komponentów, zapobiega duplikacji kodu, eliminuje zagrożenie podwójnego wykonania (`TypeError` retry) i nie wprowadza żadnych zależności od CustomTkintera do klasycznego launchera.

### C. Classic Inline Import / Build Adapter
- **Zakres:** Wydzielenie całego importowania, weryfikacji i ładowania widoków wraz z dedykowanymi strukturami wyników (`Outcome`, `BuildResult`) do osobnego modułu.
- **Decyzja:** Odrzucono. Klasyczny launcher oraz Studio mają skrajnie różne podejścia do importu (synchroniczne vs asynchroniczne za pomocą `run_async()`) oraz prezentacji błędów (messagebox vs CustomTkinter error panel). Próba ujednolicenia całego procesu importu doprowadziłaby do zbytniego skomplikowania kodu lub naruszenia wymagań asynchroniczności Studio.

### D. Classic Inline Host Lifecycle
- **Zakres:** Wydzielenie niszczenia hosta, zarządzania rozmiarem okna, ukrywania kafelków i rejestracji callbacków nawigacji finansowej.
- **Decyzja:** Odrzucono. Te zadania stanowią czystą orkiestrację UI powiązaną ze stanem konkretnych klas aplikacji Tkinter. Ich wydzielenie naruszyłoby zasadę spójności (High Cohesion) i wymusiło przekazywanie zbyt wielu prywatnych referencji do zewnętrznych funkcji.

---

## 8. Wybrana granica i uzasadnienie

Wybrano **LC-4B — Neutral Inline Builder Invocation**.

### Uzasadnienie:
Pozwala na usunięcie krytycznego błędu projektowego (podatności na ponowne wywołanie po `TypeError`) z klasycznego launchera. Przenosi logikę inspekcji sygnatury do jednego, w pełni przetestowanego i współdzielonego modułu, bez narzucania klasycznemu launcherowi zależności od CustomTkintera. Cykl życia hostów (Tk Frame) oraz specyfika importu pozostają w gestii poszczególnych klas orkiestrujących.

---

## 9. Publiczne API

Nowy moduł zostanie utworzony w pliku:
`cursor-api/giclee_app/launcher_inline_builder.py`

### Sygnatury funkcji:

```python
from __future__ import annotations

from collections.abc import Callable
from typing import Any
import tkinter as tk


def supports_on_open_component(builder: Callable[..., Any]) -> bool:
    """Sprawdza za pomocą inspect.signature, czy builder akceptuje on_open_component."""
    ...


def invoke_inline_builder(
    builder: Callable[..., Any],
    parent: tk.Widget,
    on_back: Callable[[], None],
    *,
    on_open_component: Callable[[str], None] | None = None,
) -> Any:
    """Bezpiecznie wywołuje builder dokładnie raz, przekazując callback jeśli jest obsługiwany.

    Wszelkie TypeError wygenerowane wewnątrz buildera są propagowane bez ponownej próby.
    """
    ...
```

Jawna definicja eksportów:
```python
__all__ = [
    "supports_on_open_component",
    "invoke_inline_builder",
]
```

---

## 10. Dokładna semantyka

1. **`supports_on_open_component`:**
   - Próbuje pobrać sygnaturę przekazanego obiektu callable za pomocą `inspect.signature()`.
   - W przypadku przechwycenia `TypeError` lub `ValueError` (np. obiekty wbudowane bez sygnatury), zwraca `False`.
   - Zwraca `True`, jeśli w sygnaturze występuje parametr o nazwie `"on_open_component"`, pod warunkiem, że jego typ to `POSITIONAL_OR_KEYWORD` lub `KEYWORD_ONLY`.
   - Zwraca `True`, jeśli w parametrach zadeklarowano `VAR_KEYWORD` (czyli `**kwargs`).
   - Zwraca `False`, jeśli parametr o nazwie `"on_open_component"` ma typ `POSITIONAL_ONLY`.
   - Zwraca `False`, jeśli zadeklarowano samo `*args` (typ `VAR_POSITIONAL`) bez obecności `**kwargs`.
   - Publiczny helper służy do wykrywania możliwości wstrzyknięcia argumentu poprzez keyword: `on_open_component=callback`. Parametr `POSITIONAL_ONLY` z definicji nie pozwala na przekazanie go w ten sposób, dlatego callback nie jest do niego wstrzykiwany.
2. **`invoke_inline_builder`:**
   - Wywołuje `supports_on_open_component()`.
   - Jeśli wynik to `True`, uruchamia: `builder(parent, on_back, on_open_component=on_open_component)`.
   - Jeśli wynik to `False` (w tym dla builderów z parametrem positional-only `"on_open_component"`), uruchamia: `builder(parent, on_back)`.
   - Jeśli opcjonalny parametr positional-only ma wartość domyślną, builder zadziała ze swoją wartością domyślną. Jeśli jest on wymagany (brak wartości domyślnej), naturalny błąd `TypeError` (brakujący argument pozycyjny) propaguje się z wywołania bezpośrednio do wywołującego. Nie wolno wykonywać żadnego retry ani próbować zgadywać kolejności argumentów pozycyjnych.
   - Wywołanie następuje **dokładnie raz**. Błędy typu `TypeError` oraz inne wyjątki rzucane z wnętrza funkcji `builder` propagują się bezpośrednio do wywołującego.
   - Brak jakichkolwiek efektów ubocznych w layoucie czy Tkinterze (funkcja nie pakuje widoku ani nie wywołuje `.pack()`).

---

## 11. Ownership odpowiedzialności

| Odpowiedzialność | Kto realizuje |
|---|---|
| Import modułu (`importlib.import_module`) | Caller (`launcher.py` / `inline_host.py`) |
| Pobranie i walidacja callable `build_view` | Caller |
| Detekcja obsługi `on_open_component` | Helper (`launcher_inline_builder.py`) |
| Wywołanie buildera dokładnie raz | Helper |
| Obsługa i prezentacja wyjątków z buildera | Caller |
| Pakowanie (`pack()`) zwróconego widgetu | Caller |
| Zarządzanie rozmiarem okna (`_apply_inline_window_size`) | Caller |
| Rejestracja callbacka nawigacji finansowej | Caller (`launcher.py`) |

---

## 12. Zależności dozwolone
- Biblioteka standardowa (`inspect`, `collections.abc.Callable`, `typing.Any`);
- `tkinter` (wyłącznie do typowania `tk.Widget`).

## 13. Zależności zabronione
- `customtkinter` i powiązane widgety;
- `giclee_app.launcher` i `giclee_app.launcher_studio`;
- `giclee_app.ui.inline_host`;
- `giclee_app.component_loader.Component` (brak potrzeby przekazywania całego komponentu do helpera).

---

## 14. Zmiany klasycznego launchera

W `launcher.py` w metodzie `_show_inline()` zostanie usunięty blok:
```python
        try:
            try:
                view = builder(
                    self._inline_host,
                    on_back,
                    on_open_component=self._open_component_by_folder,
                )
            except TypeError:
                view = builder(self._inline_host, on_back)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(comp.name, f"Blad budowy widoku:\n{e}")
            self._show_tiles()
            return
```
i zastąpiony przez bezpieczne wywołanie helpera:
```python
        try:
            view = invoke_inline_builder(
                builder,
                self._inline_host,
                on_back,
                on_open_component=self._open_component_by_folder,
            )
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(comp.name, f"Blad budowy widoku:\n{e}")
            self._show_tiles()
            return
```

LC-4B nie zmienia importów runtime w launcher.py; get_bundle_root pozostaje używany.

---

## 15. Zmiany Studio

W `giclee_app/ui/inline_host.py` zostaną usunięte funkcje `_supports_on_open_component` oraz `_invoke_build_view`. W ich miejsce zostaną zaimportowane funkcje z `giclee_app.launcher_inline_builder`.
W metodzie `_mount_inline` wywołanie:
```python
        try:
            view = _invoke_build_view(
                builder,
                self._tk_mount,
                self._on_back,
                self._on_open_component,
            )
```
zostanie zastąpione przez:
```python
        try:
            view = invoke_inline_builder(
                builder,
                self._tk_mount,
                self._on_back,
                on_open_component=self._on_open_component,
            )
```

---

## 16. Zachowania pozostające bez zmian
- Synchroniczny i asynchroniczny import modułów komponentów;
- Niszczenie poprzednich instancji hosta;
- Zmiana geometrii okna (zarówno w Studio, jak i w klasycznym launcherze);
- Treść i logika okien dialogowych z błędami;
- Rejestracja callbacków nawigacji finansowej;
- Cała warstwa `launcher_classic_subprocess.py` (LC-4A).

---

## 17. Out-of-scope
- Zmiana implementacji URL;
- Wdrażanie tła orkiestracji subprocessów;
- Zmiana zachowania Studio w zakresie pre-warmingu/cache'owania widoków;
- Modyfikowanie plików komponentów w `Komponenty/`.

---

## 18. Finalna allowlista implementation PR

Przyszły PR implementacyjny musi zawierać **dokładnie siedem plików**:
1. `cursor-api/giclee_app/launcher_inline_builder.py` — **nowy**;
2. `cursor-api/giclee_app/launcher.py` — integracja z neutralnym helperem;
3. `cursor-api/giclee_app/ui/inline_host.py` — integracja Studio z neutralnym helperem;
4. `cursor-api/tests/test_launcher_inline_builder.py` — **nowy** suite testowy dla helpera;
5. `cursor-api/tests/test_studio_inline_host.py` — aktualizacja importów w testach Studio;
6. `cursor-api/giclee_app/docs/launcher.md` — aktualizacja dokumentacji architektonicznej o wpis LC-4B;
7. `cursor-api/giclee_app/docs/launcher-composition-lc4b-contract.md` — ten kontrakt (zmiana statusu).

---

## 19. Focused test matrix

Suite testowy w `tests/test_launcher_inline_builder.py` must cover:
1. **`supports_on_open_component`:**
   - builder z 2 argumentami (`parent, on_back`) -> `False`;
   - builder z jawnym parametrem `on_open_component` (typ `POSITIONAL_OR_KEYWORD`) -> `True`;
   - builder z keyword-only `on_open_component` (typ `KEYWORD_ONLY`) -> `True`;
   - builder z `**kwargs` -> `True`;
   - builder z `*args` (bez `**kwargs`) -> `False`;
   - builder z positional-only `on_open_component` (opcjonalnym lub wymaganym) -> `False`;
   - obiekt callable (klasa lub instancja z `__call__`) z odpowiednią sygnaturą;
   - dekorowana funkcja zachowująca sygnaturę;
   - obsługa błędów `inspect.signature` (TypeError/ValueError) -> `False`.
2. **`invoke_inline_builder`:**
   - przekazanie `parent` oraz `on_back` bez zmian;
   - wywołanie bez `on_open_component` dla buildera dwuargumentowego;
   - wymagany positional-only `on_open_component`: helper wywołuje builder raz z 2 argumentami, a `TypeError` o brakującym argumencie propaguje się bez retry;
   - opcjonalny positional-only `on_open_component`: `supports_on_open_component()` zwraca `False`, builder wywołany raz z 2 argumentami, używając wartości domyślnej;
   - parametr positional-or-keyword: callback przekazany jako keyword (`on_open_component=callback`);
   - parametr keyword-only: callback przekazany jako keyword (`on_open_component=callback`);
   - zwrócenie `tk.Widget` / `None` / innego obiektu bez zakłóceń;
   - propagowanie wyjątków (`RuntimeError`, `ValueError`) bezpośrednio z buildera;
   - propagowanie `TypeError` zgłoszonego **wewnątrz** buildera (weryfikacja braku retry);
   - gwarancja dokładnie jednego wywołania buildera.
3. **Izolacja:**
   - brak importu `customtkinter` w helperze;
   - brak importu `launcher.py` w helperze.

---

## 20. Source guards

Testy regresji i spójności zweryfikują, czy:
- `launcher.py` nie importuje `customtkinter` ani `giclee_app.ui.inline_host`;
- `launcher.py` nie posiada bloku `except TypeError:` z ponownym wywołaniem buildera;
- `launcher_delegate.py` nie uległ żadnym modyfikacjom.

---

## 21. Validation commands

Weryfikacja lokalna:
```powershell
python -m pytest -q `
  tests/test_launcher_inline_builder.py `
  tests/test_studio_inline_host.py `
  tests/test_launcher_classic_subprocess.py `
  tests/test_launcher_delegate.py `
  tests/test_launcher_composition.py `
  tests/test_studio_imports.py `
  tests/test_giclee_app_packaging.py
```

---

## 22. Completion criteria

LC-4B zostanie uznany za ukończony, gdy:
- helper sygnatury i wywołania znajduje się wyłącznie w `launcher_inline_builder.py`;
- klasyczny launcher i Studio używają tego samego helpera;
- wyeliminowano niebezpieczeństwo podwójnego wywołania po `TypeError`;
- suite testowy przechodzi w całości;
- finalny diff PR implementacyjnego obejmuje dokładnie 7 plików z allowlisty.
