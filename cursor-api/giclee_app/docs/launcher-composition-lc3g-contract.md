# ETAP 4B / LC-3G — Tk Drag Target Lookup Adapter

**Status:** fresh reconnaissance · contract freeze  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `d27b9e15caefe89364896473ce80512636a0ff29`  
**Data weryfikacji:** 2026-07-15

## 1. Cel pakietu

Wydzielić z `DragDropCategoryGicleeApp` wyłącznie odczytową mechanikę Tk odpowiedzialną za znalezienie kafelka docelowego podczas drag-and-drop:

- bezpośredni lookup przez `root.winfo_containing()`;
- przejście po łańcuchu `master` od potomka do root tile;
- bezpieczny fallback do najbliższego żywego kafelka tego samego rodzaju;
- odczyt prostokątów widgetów Tk i delegację geometrii do LC-3D.

Pakiet nie tworzy szerokiego `DragDropController`. Nie przejmuje stanu gestu, feedbacku, auto-scrollu ani persistence.

## 2. Fresh reconnaissance — ocena pozostałych skupisk DnD

Po scaleniu LC-3F w `dragdrop_category_launcher.py` pozostają cztery odrębne skupiska odpowiedzialności.

### 2.1. Tk target lookup / widget traversal — wybrane jako LC-3G

Obejmuje:

- ochronę przed wyborem sąsiada, gdy wskaźnik nadal znajduje się wewnątrz source tile;
- `root.winfo_containing(x_root, y_root)`;
- przejście po `widget.master`;
- rozpoznanie `_launcher_dnd_kind`;
- ograniczenie fallbacku do obszaru `canvas`;
- filtrowanie `_dnd_tiles` po rodzaju, istnieniu i poprawnej geometrii;
- wybór nearest target przy użyciu `nearest_rect_index()`.

Jest to spójna, odczytowa granica platformowa. Nie mutuje aplikacji ani layoutu.

### 2.2. Visual feedback / czyszczenie UI — późniejszy osobny pakiet

Obejmuje:

- source border;
- target border;
- root cursor `fleur` i reset;
- `_set_drop_target()`;
- `_clear_drag_state()`.

Ten zakres nadal jest sprzężony z mutable `_DragState`, dlatego nie należy łączyć go z target lookupiem.

### 2.3. Auto-scroll — późniejszy osobny adapter

Obejmuje:

- geometrię `canvas`;
- stały margin `42 px`;
- `yview_scroll(-1/+1, "units")`.

Zakres jest mały i niezależny, ale nie uzasadnia rozszerzania LC-3G.

### 2.4. Persistence kategorii i komponentów — późniejszy większy pakiet

Obejmuje:

- `_reorder_category()`;
- `_reorder_component()`;
- `resolve_sections()`;
- `replace_subset_order()`;
- `save_layout()`;
- rerender, navigation finish i status text.

To warstwa aplikacyjna i writer boundary. Nie należy jej mieszać z adapterem Tk.

## 3. Zamrożona granica LC-3G

Nowy moduł:

- `cursor-api/giclee_app/launcher_tk_drag_targets.py`

Publiczny kontrakt:

```python
from collections.abc import Sequence
import tkinter as tk

from .launcher_drag_geometry import DragPoint, DragRect


def widget_drag_rect(widget: tk.Misc) -> DragRect | None:
    ...


def find_drop_target(
    root: tk.Misc,
    *,
    tiles_area: tk.Misc,
    tiles: Sequence[tk.Frame],
    drag_kind: str,
    point: DragPoint,
    exclude: tk.Frame,
) -> tk.Frame | None:
    ...
```

Adapter może importować wyłącznie:

- bibliotekę standardową;
- `tkinter`;
- `launcher_drag_geometry`.

Nie może importować `DragDropCategoryGicleeApp`, `_DragState`, layoutu, persistence, komponentów ani innych warstw aplikacji.

## 4. Zachowanie, które musi pozostać identyczne

### 4.1. Source containment guard

Jeżeli `point` znajduje się wewnątrz `exclude`, wynik ma być `None` przed wywołaniem `root.winfo_containing()`.

Cel: ruch dłoni wewnątrz źródłowego kafelka nie może sam wybrać najbliższego sąsiada.

Jeżeli geometria source tile jest niedostępna z powodu `tk.TclError`, guard zachowuje dotychczasowe fail-closed `False` i lookup może przejść dalej.

### 4.2. Direct widget lookup

1. Wywołać `root.winfo_containing(point.x, point.y)`.
2. `tk.TclError` oznacza brak direct widgetu, ale nie blokuje fallbacku nearest.
3. Przechodzić po `current.master` od znalezionego widgetu ku górze.
4. Pierwszy obiekt, który:
   - nie jest `exclude`;
   - ma `_launcher_dnd_kind == drag_kind`;
   ma zachować bieżącą semantykę:
   - jeżeli jest `tk.Frame`, zwrócić ten sam obiekt;
   - jeżeli nie jest `tk.Frame`, zwrócić `None`.
5. `AttributeError` lub `tk.TclError` podczas odczytu `master` kończy direct traversal i pozwala przejść do fallbacku.

Adapter nie dodaje nowych markerów i nie przenosi metadanych na dzieci widgetu. LC-3F pozostawia metadane wyłącznie na root tile.

### 4.3. Ograniczenie fallbacku do tiles area

Jeżeli `point` nie znajduje się wewnątrz prostokąta `tiles_area`, wynik ma być `None`.

Brak poprawnej geometrii `tiles_area` również daje `None`.

Granice pozostają półotwarte zgodnie z `point_inside()` z LC-3D.

### 4.4. Filtrowanie kandydatów

Fallback iteruje `tiles` w istniejącej kolejności i pomija:

- `exclude`;
- kafelki z innym `_launcher_dnd_kind`;
- kafelki, dla których `winfo_exists()` rzuca `tk.TclError`;
- kafelki, dla których `winfo_exists()` zwraca false;
- kafelki bez poprawnego `DragRect`.

Adapter nie sortuje, nie kopiuje metadanych i nie mutuje przekazanej sekwencji.

### 4.5. Nearest fallback

Dla zachowanych kandydatów:

- zbudować prostokąty w tej samej kolejności;
- wywołać `nearest_rect_index(rects, point)`;
- zwrócić kandydat o tym samym indeksie;
- przy remisie zachować pierwszy kafelek, zgodnie z LC-3D;
- dla pustej listy zwrócić `None`.

### 4.6. Odczyt geometrii widgetu

`widget_drag_rect()` odczytuje:

- `winfo_rootx()`;
- `winfo_rooty()`;
- `winfo_width()`;
- `winfo_height()`.

`tk.TclError` daje `None`. Funkcja nie wywołuje `update()` ani `update_idletasks()` i nie mutuje widgetu.

## 5. Odpowiedzialności pozostające w klasie

`DragDropCategoryGicleeApp` nadal:

- posiada `_dnd_tiles`;
- posiada `_DragState`;
- wywołuje target lookup z bieżącymi `root`, `canvas`, rodzajem, punktem i source tile;
- posiada `_on_tile_motion()` i `_on_tile_release()`;
- oblicza `after` przez `drop_after()` i ratio `0.22`;
- posiada visual feedback i czyszczenie UI;
- posiada auto-scroll;
- posiada persistence kategorii i komponentów;
- zachowuje click-vs-drag oraz kolejność clear-before-reorder.

Metoda `_find_drop_target()` może pozostać cienkim wrapperem, aby zachować obecny punkt rozszerzenia i testowalność klasy.

`_drop_after()` korzysta z `widget_drag_rect()` z nowego adaptera, ale sama decyzja `after` pozostaje w klasie i LC-3D.

## 6. Jawnie poza zakresem

LC-3G nie zmienia:

- `_DragState` ani jego pól;
- progu drag `8 px`;
- ratio `0.22`;
- kolorów ramek;
- kursora `hand2` lub `fleur`;
- `_set_drop_target()`;
- `_clear_drag_state()`;
- `_auto_scroll_drag()` i marginu `42 px`;
- `_reorder_category()`;
- `_reorder_component()`;
- `resolve_sections()`, `save_layout()` ani formatu danych;
- `launcher_drag_geometry.py`;
- `launcher_drag_gesture.py`;
- `launcher_tk_drag_bindings.py`;
- entrypointu, MRO, kategorii, gridu, skrótów, Studio i background services;
- Stage 2 CI;
- Shopify, deployu, plików startowych GPT i ZIP-a wiedzy.

## 7. Allowlista implementacyjna

Kod:

1. nowy `cursor-api/giclee_app/launcher_tk_drag_targets.py`;
2. `cursor-api/giclee_app/dragdrop_category_launcher.py`.

Testy:

3. nowy `cursor-api/tests/test_launcher_tk_drag_targets.py`;
4. `cursor-api/tests/test_launcher_drag_geometry.py` — usunięcie testów wrapperów przeniesionych do adaptera i aktualizacja source assertions.

Dokumentacja:

5. `cursor-api/giclee_app/docs/launcher.md`;
6. ten kontrakt.

Finalny implementation PR obejmuje dokładnie sześć plików. Każde rozszerzenie wymaga osobnego findingu i aktualizacji kontraktu przed edycją.

Docs-only contract PR obejmuje wyłącznie ten jeden plik.

## 8. Focused tests

Nowy suite musi potwierdzić:

1. source containment zwraca `None` przed direct lookupem;
2. direct lookup z potomka zwraca właściwy root tile przez traversal `master`;
3. `exclude` nigdy nie jest zwracany;
4. inny `drag_kind` nie jest zwracany;
5. matching tagged non-Frame zachowuje wynik `None`;
6. `winfo_containing()` z `tk.TclError` przechodzi do fallbacku;
7. traversal zatrzymuje się bez wyjątku na `AttributeError` i `tk.TclError`;
8. punkt poza `tiles_area` blokuje fallback;
9. fallback pomija martwe, błędne geometrycznie i niezgodne rodzajem kafelki;
10. fallback zachowuje kolejność kandydatów i first-tie semantics;
11. pusta lista kandydatów zwraca `None`;
12. `widget_drag_rect()` zachowuje dokładne wartości i fail-closed na `tk.TclError`;
13. adapter nie wykonuje konfiguracji widgetów i nie mutuje `tiles`;
14. adapter nie importuje aplikacji, layoutu, persistence ani `Komponenty`;
15. wrapper klasy przekazuje dokładnie `root`, `canvas`, `_dnd_tiles`, kind, point i source;
16. `_drop_after()` nadal używa ratio `0.22` i LC-3D.

Focused regression set:

- `tests/test_launcher_tk_drag_targets.py`;
- `tests/test_launcher_drag_geometry.py`;
- `tests/test_launcher_drag_gesture.py`;
- `tests/test_launcher_tk_drag_bindings.py`;
- `tests/test_launcher_tile_order.py`;
- `tests/test_launcher_composition.py`;
- `tests/test_launcher_category_renderer.py`;
- `tests/test_launcher_grid_layout.py`;
- `tests/test_giclee_app_packaging.py`.

Dopiero po focused PASS:

- `git diff --check`;
- dokładny scope guard sześciu plików;
- finalny diff bez one-shot helperów i workflowów;
- Hermetic;
- Tk GUI smoke;
- mirror Tcl/Tk, warmup i `VerifyOnly`;
- pełny baseline;
- JUnit;
- runtime-write inventory;
- exact-head review.

## 9. Manual smoke

Na Windows po implementacji:

1. uruchomić `python -m giclee_app`;
2. przeciągnąć kategorię, chwytając tekst lub dowolne dziecko kafelka;
3. przeciągnąć komponent, chwytając tekst lub dowolne dziecko kafelka;
4. potwierdzić brak wyboru sąsiada podczas ruchu wewnątrz source tile;
5. upuścić w pustym miejscu pomiędzy kafelkami i potwierdzić nearest fallback;
6. wyjechać kursorem poza obszar listy i potwierdzić brak targetu;
7. potwierdzić brak regresji click-vs-drag;
8. potwierdzić, że zapis kolejności nadal działa i przetrwa restart.

## 10. Rollback

LC-3G nie zmienia formatu danych ani ścieżek runtime. Rollback implementation PR to zwykły revert pojedynczego squash commitu.

Nie wymaga migracji, czyszczenia AppData ani operacji Shopify.

## 11. Kryterium zakończenia

LC-3G jest zakończony, gdy:

- direct widget lookup, traversal i nearest fallback znajdują się w jednym adapterze Tk;
- klasa zachowuje cienki wrapper oraz ownership stanu, feedbacku, scrollu i persistence;
- finalny diff obejmuje dokładnie sześć allowlistowanych plików;
- focused suite, scope guard, Hermetic, Tk GUI, pełny baseline i inventory są zielone na tym samym exact headzie;
- review threads = 0;
- branch jest `behind_by=0`;
- nie zmieniono zachowania target selection, click-vs-drag, `after`, auto-scrollu, persistence ani entrypointu.
