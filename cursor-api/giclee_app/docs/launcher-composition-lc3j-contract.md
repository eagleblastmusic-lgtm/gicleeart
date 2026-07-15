# LC-3J — Category Order Persistence Adapter

Status: fresh reconnaissance · contract freeze

## 1. Kontekst

Bazą kontraktu jest:

```text
master@b30ac9c7ae215977cfdff3b2d7746c2d10300a77
```

Etap aktywny:

```text
ETAP 4B — Launcher Composition
```

Po LC-3G, LC-3H i LC-3I z klasy `DragDropCategoryGicleeApp` wydzielono już:

- wyszukiwanie celu Tk;
- wizualny feedback drag-and-drop;
- auto-scroll Tk.

Pozostały writer boundary dzieli się na dwie niezależne ścieżki:

1. zapis kolejności kategorii przez `LauncherLayout.section_order`;
2. zapis kolejności komponentów przez przeliczenie `TileLayoutEntry.sort_key` w aktywnej sekcji.

LC-3J obejmuje wyłącznie pierwszą ścieżkę. Persistence komponentów zostaje na późniejszy, osobny pakiet.

## 2. Problem

`DragDropCategoryGicleeApp._reorder_category()` wykonuje obecnie jednocześnie:

- odczyt widocznych sekcji;
- obliczenie nowej kolejności;
- zachowanie slotów kategorii niewidocznych lub pustych;
- mutację `layout.section_order`;
- zapis przez `save_layout()`;
- rerender;
- reset nawigacji i scrolla;
- komunikat statusu.

Logika modelu i zapisu powinna zostać wydzielona z klasy Tk, ale orchestration UI ma pozostać w klasie.

## 3. Wybrana granica

Nowy moduł:

```text
cursor-api/giclee_app/launcher_drag_category_persistence.py
```

Publiczny kontrakt:

```python
from collections.abc import Sequence

from .launcher_layout import LauncherLayout


def persist_category_reorder(
    layout: LauncherLayout,
    visible_titles: Sequence[str],
    source: str,
    target: str,
    *,
    after: bool,
) -> bool:
    ...
```

Funkcja zwraca:

- `True`, jeżeli kolejność została zmieniona i zapisana;
- `False`, jeżeli operacja jest no-op i zapis nie został wykonany.

## 4. Odpowiedzialność adaptera

Adapter posiada wyłącznie:

- obliczenie nowej kolejności widocznych kategorii przez `reorder_relative()`;
- rozpoznanie no-op;
- wybór bazowej pełnej kolejności;
- zachowanie pustych, ukrytych i niewidocznych slotów przez `replace_subset_order()`;
- mutację `LauncherLayout.section_order`;
- pojedyncze wywołanie `save_layout(layout)` po skutecznej mutacji.

Adapter nie posiada Tk ani UI.

## 5. Dokładna semantyka

### 5.1 Widoczna kolejność

Adapter traktuje `visible_titles` jako bieżącą kolejność kategorii widocznych w UI.

Powinien wykonać odpowiednik:

```python
visible = list(visible_titles)
reordered = reorder_relative(
    visible,
    source,
    target,
    after=after,
)
```

Nie może mutować wejściowej sekwencji `visible_titles`.

### 5.2 No-op

Jeżeli:

```python
reordered == visible
```

adapter musi:

- zwrócić `False`;
- nie zmieniać `layout.section_order`;
- nie wywoływać `save_layout()`.

Dotyczy to między innymi:

- source == target;
- brak source;
- brak target;
- operacja, która nie zmienia kolejności.

### 5.3 Pełna kolejność

Jeżeli `layout.section_order` jest niepuste, jest ono pełną kolejnością bazową.

Jeżeli `layout.section_order` jest puste, bazą jest bieżące `visible`.

Dokładna semantyka:

```python
existing = layout.section_order or visible
```

Nie należy wprowadzać dodatkowego fallbacku do `DEFAULT_SECTIONS` ani `section_titles()`.

### 5.4 Zachowanie niewidocznych slotów

Nowa pełna kolejność musi powstać przez:

```python
replace_subset_order(existing, reordered)
```

Ma to zachować istniejącą semantykę:

- puste kategorie pozostają w swoich slotach;
- kategorie aktualnie niewidoczne pozostają w pełnej kolejności;
- nowe elementy podzbioru są dopisywane przez istniejący helper;
- przypadkowe duplikaty są obsługiwane zgodnie z LC-3D/`launcher_tile_order.py`.

Adapter nie może implementować własnego algorytmu podmiany slotów.

### 5.5 Mutacja i zapis

Po obliczeniu nowej pełnej kolejności adapter wykonuje dokładnie:

```python
layout.section_order = new_order
save_layout(layout)
return True
```

`save_layout()` ma zostać wywołane:

- dokładnie raz;
- z tym samym obiektem `LauncherLayout`;
- po mutacji `section_order`.

### 5.6 Błędy zapisu

Nie dodawać rollbacku, kopii transakcyjnej ani maskowania wyjątków.

Jeżeli `save_layout()` zgłosi wyjątek:

- wyjątek ma propagować się do wywołującego;
- `layout.section_order` pozostaje zmutowane, tak jak w obecnej implementacji;
- adapter nie zwraca wartości sukcesu;
- UI orchestration nie może wykonać rerenderu ani komunikatu statusu, ponieważ wyjątek przerywa wywołanie.

To jest świadome zachowanie kompatybilne z bieżącym kodem.

## 6. Zależności

Adapter może importować wyłącznie:

- bibliotekę standardową;
- `LauncherLayout` i `save_layout` z `.launcher_layout`;
- `reorder_relative` i `replace_subset_order` z `.launcher_tile_order`.

Adapter nie może importować:

- `tkinter`;
- `DragDropCategoryGicleeApp`;
- `category_launcher`;
- `category_map`;
- rendererów;
- komponentów;
- Studio;
- `Komponenty`;
- deploymentu ani warstw zewnętrznych.

Moduł ma mieć jawne `__all__`.

## 7. Zmiana launchera

W:

```text
cursor-api/giclee_app/dragdrop_category_launcher.py
```

należy zaimportować:

```python
from .launcher_drag_category_persistence import persist_category_reorder
```

`_reorder_category()` zachowuje odpowiedzialność za:

- `resolve_sections(...)`;
- zbudowanie `visible_titles`;
- przekazanie `source`, `target` i `after`;
- decyzję o dalszych efektach UI na podstawie wartości bool;
- `_render_tiles()`;
- `_finish_navigation_render()`;
- dokładny komunikat:

```text
Zapisano nową kolejność kategorii
```

Docelowa orchestration:

```python
sections = resolve_sections(...)
visible_titles = [title for title, _components in sections]
changed = persist_category_reorder(
    self._layout,
    visible_titles,
    source,
    target,
    after=after,
)
if not changed:
    return

self._render_tiles()
self._finish_navigation_render()
self.status_var.set("Zapisano nową kolejność kategorii")
```

Z klasy należy usunąć bezpośrednie:

- `reorder_relative()` dla kategorii;
- `replace_subset_order()` dla kategorii;
- mutację `section_order` dla kategorii;
- `save_layout()` dla kategorii.

Importy nadal potrzebne przez `_reorder_component()` pozostają bez zmian.

## 8. Poza zakresem

LC-3J nie zmienia:

- `_reorder_component()`;
- `TileLayoutEntry.sort_key`;
- aktywnej sekcji;
- filtrowania widoczności;
- `resolve_sections()`;
- `category_map()`;
- `save_layout()` i formatu JSON;
- atomic writera;
- rerenderu i nawigacji;
- tekstów UI;
- drag gesture, target lookup, feedback ani auto-scrollu;
- Studio, Shopify, deploymentu, plików startowych GPT ani ZIP-a.

Nie tworzyć szerokiego `DragDropController`, repozytorium persistence ani nowej warstwy storage.

## 9. Testy

Nowy focused suite:

```text
cursor-api/tests/test_launcher_drag_category_persistence.py
```

Musi pokryć co najmniej:

1. przeniesienie kategorii przed target;
2. przeniesienie kategorii za target;
3. zachowanie pustego/ukrytego slotu w `section_order`;
4. fallback do `visible_titles`, gdy `section_order` jest puste;
5. brak mutacji wejściowej sekwencji;
6. no-op dla source == target;
7. no-op dla brakującego source;
8. no-op dla brakującego target;
9. brak `save_layout()` przy no-op;
10. dokładnie jedno `save_layout()` przy zmianie;
11. zapis tego samego obiektu layoutu;
12. zapis po mutacji `section_order`;
13. propagację wyjątku zapisu;
14. brak rollbacku mutacji po wyjątku zapisu;
15. brak importu Tk i warstw UI;
16. cienką delegację `_reorder_category()`;
17. brak rerenderu, finish i statusu przy `False`;
18. kolejność efektów przy `True`: persist → render → finish → status;
19. brak efektów UI, gdy persistence zgłasza wyjątek;
20. niezmienioną implementację `_reorder_component()`.

Testy adaptera nie mogą wymagać prawdziwego ekranu GUI.

## 10. Finalna allowlista implementacji

Implementation PR może zmienić dokładnie pięć plików:

```text
cursor-api/giclee_app/launcher_drag_category_persistence.py
cursor-api/giclee_app/dragdrop_category_launcher.py
cursor-api/tests/test_launcher_drag_category_persistence.py
cursor-api/giclee_app/docs/launcher.md
cursor-api/giclee_app/docs/launcher-composition-lc3j-contract.md
```

Żadne helpery one-shot ani workflowy techniczne nie mogą pozostać w finalnym diffie.

## 11. Focused validation

Minimalny zestaw focused tests powinien objąć:

```text
tests/test_launcher_drag_category_persistence.py
tests/test_launcher_tile_order.py
tests/test_launcher_drag_gesture.py
tests/test_launcher_tk_drag_auto_scroll.py
tests/test_launcher_tk_drag_feedback.py
tests/test_launcher_tk_drag_targets.py
tests/test_launcher_composition.py
tests/test_giclee_app_packaging.py
```

Po focused PASS wymagane są:

- `git diff --check`;
- dokładny pięcioplikowy scope guard;
- brak helperów i workflowów technicznych;
- draft PR;
- Hermetic;
- exact-head ready review;
- Stage 2;
- artifact/JUnit/inventory;
- squash merge.

## 12. Następna granica

Po LC-3J należy wykonać ponowne fresh reconnaissance komponentowej ścieżki writer boundary.

Nie zakładać automatycznie, że komponenty powinny użyć tego samego adaptera lub publicznego API. Ich semantyka obejmuje pełną listę wpisów sekcji, zachowanie ukrytych slotów oraz przeliczenie `sort_key`, więc wymaga osobnego kontraktu.