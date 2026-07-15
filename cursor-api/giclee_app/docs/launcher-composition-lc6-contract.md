# ETAP 4B / LC-6 — Canonical LauncherApp Composition Root

**Status:** implementation scope amended; implementation in progress  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Reconnaissance base:** `master` @ `0cecf29238c044a4ccb672d52a82ee78a277bede`  
**Contract merge:** `master` @ `b3ddc60d23ef629d7e9f43a93c6947459a56e3fc`  
**Implementation base:** `master` @ `b3ddc60d23ef629d7e9f43a93c6947459a56e3fc`  
**Data:** 2026-07-15

---

## 1. Cel LC-6

LC-6 domyka ETAP 4B przez utworzenie jednego, jawnego i kanonicznego composition root dla produkcyjnego klasycznego launchera.

Po LC-1 wszystkie warstwy przekazują klasę jawnie do `launcher.main(app_factory=...)`, ale produkcyjny pakiet nadal wybiera finalną aplikację przez bezpośredni import z ostatniej warstwy funkcjonalnej:

```python
from .dragdrop_category_launcher import main
```

w `giclee_app/__main__.py`.

Oznacza to, że `dragdrop_category_launcher.py` jest jednocześnie właścicielem:

- zachowania drag-and-drop;
- finalnego wyboru produkcyjnej klasy;
- package entrypointu.

LC-6 rozdziela te odpowiedzialności. Nowy `launcher_app.py` będzie właścicielem wyłącznie finalnej kompozycji, a warstwa DnD zachowa wyłącznie swoje zachowanie i samodzielny entrypoint diagnostyczny.

---

## 2. Stan po LC-1 — LC-5

### 2.1. Aktualne MRO

```text
DragDropCategoryGicleeApp
  -> OptionsCategoryGicleeApp
  -> StyledCategoryGicleeApp
  -> CategoryGicleeApp
  -> launcher.GicleeApp
  -> object
```

### 2.2. Wydzielone granice

- LC-2: navigation model, category renderer i grid placement;
- LC-3: shortcut decisions, WinAPI, Tk bindings, DnD geometry/gesture/targets/feedback/auto-scroll/persistence;
- LC-4: classic subprocess adapter i neutralne wywołanie builderów inline;
- LC-5: scheduler dziewięciu usług tła.

### 2.3. Dwa osobne shelle

Klasyczny launcher:

```text
python -m giclee_app
```

Studio Preview:

```text
python -m giclee_app.studio_preview
```

Studio używa `GicleeAppStudio`, CustomTkintera i własnego lifecycle. LC-6 nie scala shelli i nie przenosi usług tła do Studio.

---

## 3. Fresh reconnaissance

### 3.1. Obecny package entrypoint

`giclee_app/__main__.py` importuje `main` bezpośrednio z `dragdrop_category_launcher.py`.

### 3.2. Obecna finalna warstwa

`dragdrop_category_launcher.py` posiada `_DragState`, event orchestration DnD, persistence reorder oraz:

```python
def main() -> None:
    _launcher.main(app_factory=DragDropCategoryGicleeApp)
```

### 3.3. Brak potrzeby frameworka kompozycji

Reconnaissance nie wykazał potrzeby:

- DI containera;
- service locatora;
- dynamicznego buildera klas;
- mixin factory;
- nowego lifecycle managera;
- zmiany MRO;
- scalenia klasycznego launchera ze Studio.

Najmniejszym prawidłowym rozwiązaniem jest statyczny, osobny composition root.

---

## 4. Zamrożone rozwiązanie

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

### 4.1. Alias zamiast pustej podklasy

LC-6 nie tworzy nowego typu:

```python
class LauncherApp(DragDropCategoryGicleeApp):
    pass
```

Pusta podklasa zmieniłaby MRO, identity i nazwę runtime bez dodania zachowania.

Wymagane jest:

```python
LauncherApp is DragDropCategoryGicleeApp
```

### 4.2. Package entrypoint

`giclee_app/__main__.py` importuje:

```python
from .launcher_app import main
```

Nie importuje bezpośrednio `dragdrop_category_launcher.main`.

### 4.3. Entrypointy warstw

Istniejące `main()` pozostają w:

- `category_launcher.py`;
- `styled_category_launcher.py`;
- `options_category_launcher.py`;
- `dragdrop_category_launcher.py`.

---

## 5. Zachowanie, które musi pozostać identyczne

- exact identity finalnej klasy;
- exact MRO bez dodatkowej klasy;
- `launcher.main(app_factory=LauncherApp)`;
- startup order: root → withdraw → splash → factory raz → deiconify → mainloop;
- kategorie, styl, Opcje, skróty, DnD, inline, subprocess, URL, logi i scheduler;
- wszystkie ścieżki AppData i formaty JSON;
- samodzielny entrypoint DnD;
- osobny `studio_preview.py` i `GicleeAppStudio`.

---

## 6. Semantyka importów i side effects

`launcher_app.py`:

- importuje wyłącznie `launcher` oraz `DragDropCategoryGicleeApp`;
- nie tworzy root Tk podczas importu;
- nie uruchamia `main()` podczas importu;
- nie importuje Studio, CustomTkintera ani `Komponenty`;
- nie wykonuje I/O;
- nie tworzy wątków ani timerów;
- nie modyfikuje globalnie `launcher.GicleeApp`.

---

## 7. Jawnie poza zakresem

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

## 8. Finding implementacyjny i finalna allowlista

Pierwotny kontrakt wskazywał rozbudowę `tests/test_launcher_composition.py`. Fresh implementation review wykazał, że plik ten ma ponad 400 linii i łączy kontrakty LC-1 oraz LC-5, w tym rozbudowane testy AST schedulera. Dodawanie do niego LC-6 rozszerzałoby coupling i utrudniało utrzymanie finalnego composition root.

LC-6 otrzymuje osobny focused suite:

```text
cursor-api/tests/test_launcher_app_composition.py
```

`launcher.md` nie wymaga zmiany w tym pakiecie: nadal poprawnie opisuje wszystkie zachowania launchera, a szczegółowa granica LC-6 jest dokumentowana w tym kontrakcie. Zbiorczy status dokumentacji zostanie ujednolicony w osobnym stabilization pass po LC-6.

Finalna implementation allowlista obejmuje dokładnie cztery pliki:

1. `cursor-api/giclee_app/launcher_app.py` — nowy composition root;
2. `cursor-api/giclee_app/__main__.py` — package delegation;
3. `cursor-api/tests/test_launcher_app_composition.py` — focused suite;
4. `cursor-api/giclee_app/docs/launcher-composition-lc6-contract.md` — finding i status.

Każde dalsze rozszerzenie wymaga nowego findingu przed edycją.

---

## 9. Focused tests

Suite musi potwierdzić:

1. `launcher_app.LauncherApp is DragDropCategoryGicleeApp`;
2. exact MRO pozostaje bez zmian;
3. `launcher_app.main()` przekazuje dokładnie `LauncherApp` do `_launcher.main`;
4. factory jest przekazany dokładnie raz;
5. `__main__.py` importuje wyłącznie `launcher_app.main`;
6. package entrypoint nie importuje bezpośrednio `dragdrop_category_launcher.main`;
7. `launcher_app.py` nie definiuje klasy `LauncherApp` i nie używa `type()`;
8. brak przypisania do `_launcher.GicleeApp`;
9. brak importów Studio, CustomTkinter i `Komponenty`;
10. import modułu nie tworzy root, nie uruchamia mainloop i nie wykonuje I/O;
11. cztery layer entrypointy nadal przekazują swoje klasy jawnie;
12. samodzielny DnD entrypoint nadal przekazuje `DragDropCategoryGicleeApp`;
13. `studio_preview.py` nie importuje `launcher_app` ani klasycznego `launcher.py`.

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
- test i zmiana kontraktu są revertowane.

---

## 12. Kryterium zakończenia ETAPU 4B

ETAP 4B jest architektonicznie zakończony, gdy:

- istnieje kanoniczny `launcher_app.py`;
- package entrypoint deleguje do niego;
- `LauncherApp` zachowuje identity i MRO finalnej klasy;
- warstwa DnD nie jest już właścicielem package composition;
- Studio pozostaje osobnym shellem;
- exact czteroplikowy diff przechodzi focused tests i pełny Stage 2;
- merge następuje z expected head SHA;
- kolejny etap to stabilization/release-candidate pass, nie LC-7.
