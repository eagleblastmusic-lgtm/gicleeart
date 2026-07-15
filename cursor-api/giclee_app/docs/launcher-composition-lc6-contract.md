# ETAP 4B / LC-6 — Canonical LauncherApp Composition Root

**Status:** implementation revision in progress after Stage 2 finding  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Reconnaissance base:** `master` @ `0cecf29238c044a4ccb672d52a82ee78a277bede`  
**Contract merge:** `master` @ `b3ddc60d23ef629d7e9f43a93c6947459a56e3fc`  
**Implementation base:** `master` @ `b3ddc60d23ef629d7e9f43a93c6947459a56e3fc`  
**Data:** 2026-07-15

---

## 1. Cel LC-6

LC-6 domyka ETAP 4B przez utworzenie jednego, jawnego i kanonicznego composition root dla produkcyjnego klasycznego launchera.

Przed LC-6 `giclee_app/__main__.py` wybierał finalną aplikację przez bezpośredni import z ostatniej warstwy funkcjonalnej:

```python
from .dragdrop_category_launcher import main
```

W rezultacie `dragdrop_category_launcher.py` był jednocześnie właścicielem:

- zachowania drag-and-drop;
- finalnego wyboru produkcyjnej klasy;
- package entrypointu.

LC-6 rozdziela te odpowiedzialności. `launcher_app.py` jest właścicielem wyłącznie finalnej kompozycji, a warstwa DnD zachowuje własne zachowanie i samodzielny entrypoint diagnostyczny.

---

## 2. Stan architektury po LC-1 — LC-5

Aktualne MRO finalnej klasy:

```text
DragDropCategoryGicleeApp
  -> OptionsCategoryGicleeApp
  -> StyledCategoryGicleeApp
  -> CategoryGicleeApp
  -> launcher.GicleeApp
  -> object
```

Wydzielone granice:

- LC-2: navigation model, category renderer i grid placement;
- LC-3: shortcut decisions, WinAPI, Tk bindings oraz DnD;
- LC-4: classic subprocess adapter i neutralne wywołanie builderów inline;
- LC-5: scheduler dziewięciu usług tła.

Repozytorium zachowuje dwa osobne shelle:

```text
python -m giclee_app
python -m giclee_app.studio_preview
```

Studio używa `GicleeAppStudio`, CustomTkintera oraz własnego lifecycle. LC-6 nie scala shelli i nie przenosi usług tła do Studio.

---

## 3. Zamrożone rozwiązanie

Nowy moduł:

```text
cursor-api/giclee_app/launcher_app.py
```

Publiczny kontrakt:

```python
from . import launcher as _launcher
from .dragdrop_category_launcher import DragDropCategoryGicleeApp

LauncherApp = DragDropCategoryGicleeApp


def main() -> None:
    _launcher.main(app_factory=LauncherApp)


__all__ = ["LauncherApp", "main"]
```

### 3.1. Alias zamiast pustej podklasy

LC-6 nie tworzy nowego typu. Wymagane jest:

```python
LauncherApp is DragDropCategoryGicleeApp
```

Dzięki temu identity, MRO i runtime semantics pozostają niezmienione.

### 3.2. Package entrypoint

`giclee_app/__main__.py` importuje:

```python
from .launcher_app import main
```

Nie importuje bezpośrednio `dragdrop_category_launcher.main`.

### 3.3. Entrypointy warstw

Istniejące `main()` pozostają w:

- `category_launcher.py`;
- `styled_category_launcher.py`;
- `options_category_launcher.py`;
- `dragdrop_category_launcher.py`.

---

## 4. Zachowanie, które pozostaje identyczne

- exact identity finalnej klasy;
- exact MRO bez dodatkowej klasy;
- `launcher.main(app_factory=LauncherApp)`;
- startup order: root → withdraw → splash → factory raz → deiconify → mainloop;
- kategorie, styl, Opcje, skróty i DnD;
- inline, subprocess, URL i logi;
- dziewięć usług tła;
- AppData, legacy fallbacki i formaty JSON;
- samodzielny entrypoint DnD;
- osobny `studio_preview.py` i `GicleeAppStudio`.

---

## 5. Semantyka importów i side effects

`launcher_app.py`:

- importuje wyłącznie `launcher` oraz `DragDropCategoryGicleeApp`;
- nie tworzy root Tk podczas importu;
- nie uruchamia `main()` podczas importu;
- nie importuje Studio, CustomTkintera ani `Komponenty`;
- nie wykonuje I/O;
- nie tworzy wątków ani timerów;
- nie modyfikuje globalnie `launcher.GicleeApp`.

---

## 6. Jawnie poza zakresem

LC-6 nie:

- zmienia `launcher.GicleeApp` ani `DragDropCategoryGicleeApp`;
- przenosi metod pomiędzy klasami;
- zmienia MRO;
- usuwa entrypointów warstw;
- tworzy nowej podklasy finalnej;
- scala klasycznego launchera ze Studio;
- zmienia UI, skróty, DnD, inline, subprocess lub scheduler;
- zmienia dane, AppData, Shopify, komponenty albo workflow CI;
- rozpoczyna refaktoru motywu Shopify.

---

## 7. Findings implementacyjne i finalna allowlista

### 7.1. Osobny focused suite LC-6

Pierwotny kontrakt wskazywał rozbudowę `tests/test_launcher_composition.py`. Fresh implementation review wykazał, że plik ten ma ponad 400 linii i łączy kontrakty LC-1 oraz LC-5. LC-6 otrzymał osobny suite:

```text
cursor-api/tests/test_launcher_app_composition.py
```

### 7.2. Finding z pierwszego pełnego Stage 2

Pierwszy pełny baseline implementacji wykazał przestarzały test LC-1:

```text
test_package_main_still_targets_final_dragdrop_entrypoint
```

Test wymagał dokładnego tekstu:

```python
from .dragdrop_category_launcher import main
```

To jest poprzedni kontrakt package entrypointu i dokładnie odpowiedzialność celowo zastępowana przez LC-6. Nowy focused suite poprawnie zamraża delegację przez `launcher_app`, ale stara asercja pozostała równolegle aktywna. Jest to finding testowy, nie regresja runtime.

`tests/test_launcher_composition.py` zostaje dodany do allowlisty wyłącznie w celu aktualizacji tej jednej asercji do nowego kanonicznego root. Pozostałe testy LC-1 i LC-5 w tym pliku nie mogą zostać zmienione ani osłabione.

Ten sam baseline zawierał niezależny błąd środowiska Tcl/Tk:

```text
couldn't read .../tk8.6/ttk/clamTheme.tcl
```

Dedykowany Tk GUI smoke był zielony. Błąd środowiskowy nie uzasadnia zmiany kodu produkcyjnego ani testów aplikacji.

### 7.3. Finalna implementation allowlista

Po findingu Stage 2 dokładnie pięć plików:

1. `cursor-api/giclee_app/launcher_app.py` — nowy composition root;
2. `cursor-api/giclee_app/__main__.py` — package delegation;
3. `cursor-api/tests/test_launcher_app_composition.py` — focused suite LC-6;
4. `cursor-api/tests/test_launcher_composition.py` — wyłącznie aktualizacja starej asercji package entrypointu;
5. `cursor-api/giclee_app/docs/launcher-composition-lc6-contract.md` — findings i status.

`launcher.md` zostanie ujednolicony w osobnym stabilization pass po LC-6.

Każde dalsze rozszerzenie wymaga nowego findingu przed edycją.

---

## 8. Testy kontraktowe

Focused suite LC-6 potwierdza:

1. `launcher_app.LauncherApp is DragDropCategoryGicleeApp`;
2. exact MRO pozostaje bez zmian;
3. `launcher_app.main()` przekazuje dokładnie `LauncherApp` do `_launcher.main`;
4. factory jest przekazany dokładnie raz;
5. `__main__.py` importuje wyłącznie `launcher_app.main`;
6. package entrypoint nie importuje bezpośrednio `dragdrop_category_launcher.main`;
7. `launcher_app.py` nie definiuje klasy `LauncherApp` i nie używa `type()`;
8. brak przypisania do `_launcher.GicleeApp`;
9. brak importów Studio, CustomTkinter i `Komponenty`;
10. brak import-time root, mainloop, I/O, wątków i timerów;
11. cztery layer entrypointy nadal przekazują swoje klasy jawnie;
12. samodzielny DnD entrypoint nadal przekazuje `DragDropCategoryGicleeApp`;
13. `studio_preview.py` nie importuje `launcher_app` ani klasycznego `launcher.py`.

Stary test LC-1 ma potwierdzać nową trasę package entrypointu przez `launcher_app` i nadal zabraniać Studio w `__main__.py`.

Focused regression set:

```text
cursor-api/tests/test_launcher_app_composition.py
cursor-api/tests/test_launcher_composition.py
cursor-api/tests/test_launcher_background_services.py
cursor-api/tests/test_launcher_shortcut_controller.py
cursor-api/tests/test_launcher_drag_gesture.py
cursor-api/tests/test_launcher_inline_builder.py
cursor-api/tests/test_launcher_delegate.py
cursor-api/tests/test_studio_imports.py
cursor-api/tests/test_giclee_app_packaging.py
```

Po focused PASS obowiązują pełny Stage 2, JUnit, inventory i exact-head lock.

---

## 9. Wynik implementacji

- `launcher_app.LauncherApp` jest aliasem istniejącej finalnej klasy DnD;
- `launcher_app.main()` deleguje dokładnie raz do `launcher.main(app_factory=LauncherApp)`;
- package `__main__.py` deleguje do `launcher_app.main`;
- warstwa DnD zachowuje samodzielny `main()`;
- Studio pozostaje odseparowane;
- nie zmieniono `launcher.py`, warstw funkcjonalnych, danych ani workflow CI.

---

## 10. Manual smoke

Na Windows:

1. `python -m giclee_app` pokazuje ten sam finalny launcher DnD;
2. splash i startup order są identyczne;
3. kategorie, Opcje, skróty i DnD działają;
4. inline, subprocess i URL działają;
5. background services startują jak przed LC-6;
6. `python -m giclee_app.dragdrop_category_launcher` nadal działa;
7. `python -m giclee_app.studio_preview` pozostaje osobnym shellem.

---

## 11. Rollback

Rollback nie wymaga migracji danych:

- `__main__.py` wraca do importu `dragdrop_category_launcher.main`;
- `launcher_app.py` zostaje usunięty;
- testy i zmiana kontraktu są revertowane.

---

## 12. Kryterium zakończenia ETAPU 4B

ETAP 4B jest architektonicznie zakończony, gdy:

- istnieje kanoniczny `launcher_app.py`;
- package entrypoint deleguje do niego;
- `LauncherApp` zachowuje identity i MRO finalnej klasy;
- warstwa DnD nie jest już właścicielem package composition;
- Studio pozostaje osobnym shellem;
- exact pięcioplikowy diff przechodzi focused tests i pełny Stage 2;
- merge następuje z expected head SHA;
- kolejny etap to stabilization/release-candidate pass, nie LC-7.
