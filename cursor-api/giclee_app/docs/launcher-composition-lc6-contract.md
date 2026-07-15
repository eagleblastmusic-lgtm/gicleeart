# ETAP 4B / LC-6 — Canonical LauncherApp Composition Root

**Status:** contract frozen; implementation not started  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `0cecf29238c044a4ccb672d52a82ee78a277bede`  
**Data reconnaissance:** 2026-07-15

---

## 1. Cel LC-6

LC-6 domyka ETAP 4B przez utworzenie jednego, jawnego i kanonicznego composition root dla produkcyjnego klasycznego launchera.

Po LC-1 wszystkie warstwy przekazują klasę jawnie do `launcher.main(app_factory=...)`, ale produkcyjny pakiet nadal wybiera finalną aplikację przez bezpośredni import:

```python
from .dragdrop_category_launcher import main
```

w `giclee_app/__main__.py`.

W efekcie ostatnia warstwa funkcjonalna DnD jest jednocześnie właścicielem:

- zachowania drag-and-drop;
- finalnego wyboru produkcyjnej klasy;
- produkcyjnego entrypointu pakietu.

LC-6 rozdziela te odpowiedzialności. Nowy moduł `launcher_app.py` będzie jedynym właścicielem finalnej kompozycji klasycznego launchera, natomiast warstwa DnD pozostanie właścicielem wyłącznie zachowania DnD i swojego samodzielnego entrypointu diagnostycznego.

---

## 2. Stan po LC-1 — LC-5

### 2.1. Jawny factory root

`launcher.main()` przyjmuje jawny `app_factory`. Warstwy nie podmieniają globalnie `launcher.GicleeApp`.

### 2.2. Aktualne MRO produkcyjnej klasy

Zamrożona kolejność pozostaje:

```text
DragDropCategoryGicleeApp
  -> OptionsCategoryGicleeApp
  -> StyledCategoryGicleeApp
  -> CategoryGicleeApp
  -> launcher.GicleeApp
  -> object
```

### 2.3. Wydzielone granice

- LC-2: model nawigacji, renderer kategorii i grid placement;
- LC-3: decyzje skrótów, WinAPI, bindtagi Tk, geometria/gest DnD, target lookup, feedback, auto-scroll i persistence;
- LC-4: klasyczny subprocess adapter oraz neutralne wywołanie builderów inline;
- LC-5: neutralny scheduler dziewięciu usług tła.

### 2.4. Dwa celowo osobne shelle

1. Klasyczny launcher:

```text
python -m giclee_app
```

2. Studio Preview:

```text
python -m giclee_app.studio_preview
```

Studio używa `GicleeAppStudio`, CustomTkintera, własnego lifecycle, cache widoków i routingu. LC-6 nie scala shelli i nie przenosi usług tła do Studio.

---

## 3. Fresh reconnaissance aktualnego master

### 3.1. Produkcyjny entrypoint

`giclee_app/__main__.py` importuje `main` bezpośrednio z `dragdrop_category_launcher.py`.

### 3.2. Ostatnia warstwa funkcjonalna

`dragdrop_category_launcher.py` definiuje:

- `_DragState`;
- `DragDropCategoryGicleeApp`;
- event orchestration DnD;
- persistence category/component reorder;
- samodzielne `main()`, które wywołuje:

```python
_launcher.main(app_factory=DragDropCategoryGicleeApp)
```

### 3.3. Problem własności

Finalny wybór klasy jest obecnie poprawny technicznie, ale nadal pośrednio przywiązany do modułu konkretnej funkcji. Dodanie w przyszłości kolejnej warstwy wymagałoby ponownej zmiany `__main__.py` na import z nowego „ostatniego” modułu.

Brakuje nazwanego punktu, który odpowiada wyłącznie na pytanie:

> Jaka klasa jest produkcyjnym klasycznym LauncherApp i jak jest uruchamiana?

### 3.4. Brak potrzeby nowego runtime frameworka

Reconnaissance nie wykazał potrzeby:

- kontenera dependency injection;
- service locatora;
- dynamicznego buildera klas;
- mixin factory;
- nowego lifecycle managera;
- scalenia Studio i klasycznego launchera;
- zmiany MRO.

Najmniejszym prawidłowym rozwiązaniem jest osobny statyczny composition root.

---

## 4. Zamrożone rozwiązanie

Nowy moduł:

```text
cursor-api/giclee_app/launcher_app.py
```

Kontrakt publiczny:

```python
from . import launcher as _launcher
from .dragdrop_category_launcher import DragDropCategoryGicleeApp

LauncherApp = DragDropCategoryGicleeApp


def main() -> None:
    _launcher.main(app_factory=LauncherApp)


__all__ = ["LauncherApp", "main"]
```

### 4.1. Dlaczego alias, a nie pusta podklasa

LC-6 nie tworzy:

```python
class LauncherApp(DragDropCategoryGicleeApp):
    pass
```

Pusta podklasa zmieniłaby MRO, runtime identity klasy, nazwy w diagnostyce i potencjalne założenia testów bez dodania zachowania.

Alias:

```python
LauncherApp = DragDropCategoryGicleeApp
```

ustanawia kanoniczną nazwę kompozycji bez zmiany runtime semantics.

### 4.2. Produkcyjny package entrypoint

`giclee_app/__main__.py` będzie importował:

```python
from .launcher_app import main
```

Nie będzie importował bezpośrednio `dragdrop_category_launcher.main`.

### 4.3. Samodzielne entrypointy warstw

Istniejące `main()` pozostają w:

- `category_launcher.py`;
- `styled_category_launcher.py`;
- `options_category_launcher.py`;
- `dragdrop_category_launcher.py`.

Są użyteczne jako entrypointy diagnostyczne poszczególnych warstw i nie są usuwane.

---

## 5. Zachowanie, które musi pozostać identyczne

### 5.1. Finalna klasa

```python
LauncherApp is DragDropCategoryGicleeApp
```

### 5.2. MRO

Dokładnie:

```text
DragDropCategoryGicleeApp
OptionsCategoryGicleeApp
StyledCategoryGicleeApp
CategoryGicleeApp
GicleeApp
object
```

Bez dodatkowej klasy pomiędzy nimi.

### 5.3. Startup order

`launcher.main(app_factory=LauncherApp)` zachowuje kolejność:

1. utworzenie root Tk/TkinterDnD;
2. `withdraw`;
3. splash;
4. konstrukcja `LauncherApp(root)` dokładnie raz;
5. `deiconify`;
6. `mainloop`.

### 5.4. Klasyczny launcher

Bez zmian pozostają:

- root UI;
- kategorie i nawigacja;
- styl kafelków;
- menu Opcje;
- skróty Tk/WinAPI;
- DnD;
- inline;
- subprocess;
- URL;
- logi;
- dziewięć usług tła;
- ścieżki AppData i formaty JSON.

### 5.5. Studio

Bez zmian pozostają:

- `python -m giclee_app.studio_preview`;
- `GicleeAppStudio`;
- CustomTkinter;
- Studio routing/cache/state;
- brak importu klasycznego `launcher.py` w ścieżce importowej Studio;
- brak usług tła klasycznego launchera w Studio.

---

## 6. Semantyka importów i side effects

`launcher_app.py`:

- może importować wyłącznie `launcher` i `DragDropCategoryGicleeApp` z pakietu;
- nie tworzy root Tk podczas importu;
- nie uruchamia `main()` podczas importu;
- nie importuje `studio_preview`, `launcher_studio`, `customtkinter` ani modułów `Komponenty`;
- nie wykonuje I/O;
- nie odczytuje konfiguracji;
- nie tworzy wątków;
- nie planuje timerów;
- nie modyfikuje globalnie `launcher.GicleeApp`.

---

## 7. Jawnie poza zakresem

LC-6 nie:

- zmienia implementacji `launcher.GicleeApp`;
- przenosi metod między klasami;
- zmienia `DragDropCategoryGicleeApp`;
- zmienia MRO;
- usuwa entrypointów warstw;
- tworzy nowej podklasy finalnej;
- tworzy DI container/service locator;
- scala klasycznego launchera ze Studio;
- zmienia Studio Preview;
- zmienia UI, style, teksty, skróty, DnD ani grid;
- zmienia component launch, inline host ani scheduler;
- zmienia formaty danych, AppData ani legacy fallbacks;
- zmienia Shopify, komponentów, deployu ani workflow CI;
- rozpoczyna refaktoru motywu Shopify.

---

## 8. Allowlista implementacyjna

Implementacja może zmienić dokładnie pięć plików:

1. `cursor-api/giclee_app/launcher_app.py` — nowy kanoniczny composition root;
2. `cursor-api/giclee_app/__main__.py` — delegacja package entrypointu;
3. `cursor-api/tests/test_launcher_composition.py` — kontrakt finalnej kompozycji;
4. `cursor-api/giclee_app/docs/launcher.md` — opis finalnego root;
5. `cursor-api/giclee_app/docs/launcher-composition-lc6-contract.md` — status po implementacji.

Każde rozszerzenie allowlisty wymaga osobnego findingu i aktualizacji kontraktu przed edycją.

Docs-only contract PR zmienia wyłącznie ten plik.

---

## 9. Focused tests implementacji

Testy muszą potwierdzić:

1. `launcher_app.LauncherApp is dragdrop_category_launcher.DragDropCategoryGicleeApp`;
2. exact MRO finalnej klasy pozostaje bez zmian;
3. `launcher_app.main()` przekazuje dokładnie `LauncherApp` do `_launcher.main(app_factory=...)`;
4. factory jest przekazany dokładnie raz;
5. `giclee_app/__main__.py` importuje `main` wyłącznie z `launcher_app`;
6. package entrypoint nie importuje bezpośrednio `dragdrop_category_launcher.main`;
7. `launcher_app.py` nie definiuje klasy `LauncherApp` przez `class` ani `type()`;
8. `launcher_app.py` nie przypisuje do `_launcher.GicleeApp`;
9. `launcher_app.py` nie importuje Studio, CustomTkinter ani `Komponenty`;
10. import `launcher_app` nie tworzy root, nie uruchamia mainloop i nie wykonuje I/O;
11. istniejące cztery layer entrypointy nadal przekazują swoje klasy jawnie;
12. `dragdrop_category_launcher.main()` nadal działa jako samodzielny entrypoint warstwy;
13. `studio_preview.py` pozostaje niezależny od `launcher_app.py` i klasycznego `launcher.py`;
14. dotychczasowe testy LC-1 — LC-5 pozostają zielone.

Focused regression set:

```text
cursor-api/tests/test_launcher_composition.py
cursor-api/tests/test_launcher_background_services.py
cursor-api/tests/test_launcher_shortcut_controller.py
cursor-api/tests/test_launcher_drag_gesture.py
cursor-api/tests/test_launcher_inline_builder.py
cursor-api/tests/test_launcher_delegate.py
cursor-api/tests/test_studio_imports.py
cursor-api/tests/test_giclee_app_packaging.py
```

Po focused PASS obowiązują:

- `git diff --check`;
- exact scope guard;
- Hermetic smoke;
- Tk GUI smoke;
- pełny Windows pytest baseline;
- JUnit;
- runtime-write inventory;
- exact-head/review-thread/mergeability lock.

---

## 10. Manual smoke po implementacji

Na Windows:

1. `python -m giclee_app` pokazuje ten sam finalny launcher DnD;
2. splash i startup order pozostają identyczne;
3. kategorie, component tiles, Opcje, skróty i DnD działają;
4. inline, subprocess i URL działają;
5. background services startują jak przed LC-6;
6. `python -m giclee_app.dragdrop_category_launcher` nadal uruchamia warstwę DnD samodzielnie;
7. `python -m giclee_app.studio_preview` nadal uruchamia Studio bez klasycznego composition root.

---

## 11. Rollback

LC-6 nie zmienia danych ani formatów runtime.

Rollback to zwykły revert commita implementacyjnego:

- `__main__.py` wraca do importu `dragdrop_category_launcher.main`;
- nowy `launcher_app.py` zostaje usunięty;
- nie jest potrzebna migracja AppData ani czyszczenie danych.

---

## 12. Kryterium zakończenia ETAPU 4B

ETAP 4B jest architektonicznie zakończony, gdy:

- istnieje jeden kanoniczny `launcher_app.py`;
- package entrypoint deleguje do niego;
- finalna klasa ma jawną nazwę `LauncherApp` bez zmiany identity i MRO;
- warstwy funkcjonalne nie są właścicielami package composition;
- Studio pozostaje osobnym shellem;
- pięcioplikowy implementation diff przechodzi focused tests i pełny Stage 2;
- merge następuje na exact head SHA;
- po merge rozpoczyna się osobny stabilization/release-candidate pass, a nie kolejny pakiet architektoniczny LC.
