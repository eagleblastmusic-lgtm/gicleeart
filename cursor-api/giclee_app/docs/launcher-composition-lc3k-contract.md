# ETAP 4B / LC-3K — Component Order Persistence Adapter

**Status:** LC-3K implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`
**Base:** `master` @ `6075ac30579eb8241fb022c0ed1a5b187a854ff9`
**Data weryfikacji:** 2026-07-15

---

## 1. Cel pakietu

Wydzielić z `DragDropCategoryGicleeApp._reorder_component()` wyłącznie warstwę persistence
odpowiedzialną za utrwalenie nowej kolejności komponentów w obrębie sekcji:

- kopię `visible_order`;
- `reorder_relative()`;
- wykrycie no-op;
- zebranie wpisów `layout.entries` należących do aktywnej sekcji;
- sortowanie przez `(entry.sort_key, entry.folder.lower())`;
- zbudowanie pełnej kolejności folderów;
- zachowanie ukrytych slotów przez `replace_subset_order()`;
- przeliczenie `sort_key` do `index * 10`;
- pojedynczy `save_layout(layout)` po pełnej mutacji.

Pakiet nie tworzy szerokiego `DragDropController`. Nie łączy adapter kategorii (LC-3J)
z adapterem komponentów w jeden generyczny writer. Nie przejmuje renderowania, nawigacji
ani visual feedback.

---

## 2. Fresh reconnaissance — ocena `_reorder_component()`

Przed zamrożeniem kontraktu zweryfikowano bieżącą semantykę metody w
`cursor-api/giclee_app/dragdrop_category_launcher.py` (linie 314–362).

### 2.1. Kontrola `_active_section`

```python
section = self._active_section
if not section:
    return
```

Jeżeli nie ma aktywnej sekcji, metoda kończy się natychmiast bez żadnego efektu ubocznego.
`resolve_sections()` nie jest wtedy wywoływana.

### 2.2. `resolve_sections()` i `category_map()`

```python
sections = resolve_sections(
    self._all_components,
    self._layout,
    normally_visible=self._normally_visible,
)
components = category_map(sections).get(section, [])
```

`resolve_sections()` buduje widoczne sekcje z komponentami w kolejności wynikającej z
`sort_key` i `folder.lower()`. `category_map()` przekształca tę listę w słownik
`{tytuł: [Component, ...]}`. Adapter LC-3K nie wywołuje żadnej z tych funkcji — są one
wywoływane przez `DragDropCategoryGicleeApp` i wynik przekazywany jako `visible_order`.

### 2.3. Kolejność widocznych komponentów

```python
visible_order = [component.folder_name for component in components]
```

Lista `visible_order` zawiera wyłącznie foldery komponentów **widocznych** w bieżącej
sekcji, w kolejności ustalonej przez `resolve_sections()`.

### 2.4. `reorder_relative()` i wykrycie no-op

```python
reordered_visible = reorder_relative(visible_order, source, target, after=after)
if reordered_visible == visible_order:
    return
```

`reorder_relative()` przenosi `source` bezpośrednio przed albo za `target`. Gdy wynik
jest identyczny z wejściem — bo `source == target`, brakuje `source` lub brakuje
`target` — metoda kończy się bez mutacji i zapisu.

### 2.5. Zebranie wszystkich wpisów sekcji

```python
all_in_section = [
    entry.folder
    for entry in sorted(
        (
            entry
            for entry in self._layout.entries.values()
            if entry.section == section
        ),
        key=lambda entry: (entry.sort_key, entry.folder.lower()),
    )
]
```

Wybierane są **wszystkie** wpisy — łącznie z ukrytymi — których `entry.section == section`.
Sortowanie odbywa się wyłącznie przez `(sort_key, folder.lower())`, a nie przez tytuł
prezentacyjny, `Component.order`, kolejność z `resolve_sections()` ani nazwę kategorii.

### 2.6. Zachowanie ukrytych komponentów przez `replace_subset_order()`

```python
full_order = replace_subset_order(all_in_section, reordered_visible)
```

`replace_subset_order()` podmiania sloty zajmowane przez elementy z `reordered_visible`
w oryginalnej liście `all_in_section`, zachowując pozycje folderów, których nie ma w
`reordered_visible` (ukryte komponenty). Adapter nie implementuje własnego algorytmu
podmiany slotów.

### 2.7. Reindeksacja `sort_key` do `index * 10`

```python
for index, folder in enumerate(full_order):
    entry = self._layout.entries.get(folder)
    if entry is not None:
        entry.sort_key = index * 10
```

Pierwszy wpis otrzymuje `0`, kolejne `10`, `20`, `30` itd. Komponenty ukryte w tej samej
sekcji są reindeksowane. Wpisy innych sekcji pozostają bez zmian. Brakujący wpis jest
pomijany.

### 2.8. Pojedynczy `save_layout()` po pełnej mutacji

```python
save_layout(self._layout)
```

Zapis następuje po pełnej reindeksacji tego samego obiektu `LauncherLayout`. Zapis jest
dokładnie jeden per zmianę.

### 2.9. Rerender i status

```python
self._render_tiles()
self._finish_navigation_render()
self.status_var.set(
    f"{category_display_title(section)}: zapisano kolejność kafelków"
)
```

Te trzy operacje pozostają w `DragDropCategoryGicleeApp`. Adapter LC-3K ich nie wykonuje.

---

## 3. Zamrożona granica LC-3K

### 3.1. Nowy moduł

```text
cursor-api/giclee_app/launcher_drag_component_persistence.py
```

### 3.2. Publiczny kontrakt

```python
from collections.abc import Sequence

from .launcher_layout import LauncherLayout


def persist_component_reorder(
    layout: LauncherLayout,
    section: str,
    visible_order: Sequence[str],
    source: str,
    target: str,
    *,
    after: bool,
) -> bool:
    ...
```

### 3.3. Semantyka zwracanej wartości

- `True` — model został zmutowany i zapisany; wywołujący powinien wykonać UI effects.
- `False` — operacja jest no-op; nie zmieniono żadnego `sort_key` i nie wywołano
  `save_layout()`; wywołujący powinien pominąć UI effects i return bez renderowania.

### 3.4. `__all__`

Adapter ma jawne `__all__`:

```python
__all__ = ["persist_component_reorder"]
```

---

## 4. Szczegółowa semantyka adaptera

### 4.1. Kopia `visible_order`

Adapter nie modyfikuje przekazanej sekwencji `visible_order`. Wewnętrznie może
pracować na kopii. Widoczna kolejność przekazana przez wywołującego pozostaje bez zmian
po powrocie z funkcji.

### 4.2. `reorder_relative()`

Adapter wywołuje `reorder_relative(list(visible_order), source, target, after=after)`.

### 4.3. Wykrycie no-op

Jeżeli `reordered_visible == list(visible_order)`:

- zwróć `False`;
- nie zmieniaj żadnego `sort_key`;
- nie wywołuj `save_layout()`.

Przypadki no-op obejmują między innymi:

- `source == target`;
- `source` nie istnieje w `visible_order`;
- `target` nie istnieje w `visible_order`;
- ruch bez zmiany pozycji.

### 4.4. Pełna kolejność sekcji

```python
all_in_section = [
    entry.folder
    for entry in sorted(
        (
            entry
            for entry in layout.entries.values()
            if entry.section == section
        ),
        key=lambda entry: (entry.sort_key, entry.folder.lower()),
    )
]
```

Nie sortuj po:

- tytule prezentacyjnym;
- `Component.order`;
- kolejności z `resolve_sections()`;
- nazwie kategorii.

### 4.5. Podmiana slotów

```python
full_order = replace_subset_order(all_in_section, reordered_visible)
```

Nie implementuj własnego algorytmu podmiany slotów.

### 4.6. Reindeksacja

```python
for index, folder in enumerate(full_order):
    entry = layout.entries.get(folder)
    if entry is not None:
        entry.sort_key = index * 10
```

Wymagania:

- pierwszy wpis: `0`;
- następne: `10`, `20`, `30` itd.;
- komponenty ukryte w tej samej sekcji również są reindeksowane;
- wpisy innych sekcji pozostają bez zmian;
- brakujący wpis jest pomijany;
- krok reindeksacji wynosi dokładnie `10` — nie zmieniaj go.

### 4.7. Zapis

```python
save_layout(layout)
return True
```

`save_layout()`:

- dokładnie raz;
- ten sam obiekt `LauncherLayout`, który był przekazany jako `layout`;
- po pełnej reindeksacji.

### 4.8. Propagacja błędu zapisu

Jeżeli `save_layout()` zgłosi wyjątek:

- wyjątek propaguje się do wywołującego;
- wcześniejsze mutacje `sort_key` pozostają — adapter nie wykonuje rollbacku;
- wywołujący nie powinien wykonywać UI orchestration, jeżeli propagacja nastąpiła.

---

## 5. Dozwolone i zabronione zależności

### 5.1. Dozwolone

- biblioteka standardowa;
- `LauncherLayout` z `.launcher_layout`;
- `save_layout` z `.launcher_layout`;
- `reorder_relative` z `.launcher_tile_order`;
- `replace_subset_order` z `.launcher_tile_order`.

### 5.2. Zabronione

- `tkinter` (w tym `tk`, `ttk`, `TclError`);
- `Component` z `.component_loader`;
- `category_map` z `.category_launcher`;
- `resolve_sections` z `.launcher_layout`;
- `category_launcher` (cały moduł);
- `DragDropCategoryGicleeApp` i jej podklasy;
- renderery UI;
- Studio;
- `Komponenty`;
- Shopify;
- warstwy deploymentu.

---

## 6. Docelowa orchestration w `DragDropCategoryGicleeApp._reorder_component()`

Po implementacji adaptera metoda powinna mieć postać:

```python
def _reorder_component(
    self,
    source: str,
    target: str,
    *,
    after: bool,
) -> None:
    section = self._active_section
    if not section:
        return

    sections = resolve_sections(
        self._all_components,
        self._layout,
        normally_visible=self._normally_visible,
    )
    components = category_map(sections).get(section, [])
    visible_order = [component.folder_name for component in components]

    changed = persist_component_reorder(
        self._layout,
        section,
        visible_order,
        source,
        target,
        after=after,
    )
    if not changed:
        return

    self._render_tiles()
    self._finish_navigation_render()
    self.status_var.set(
        f"{category_display_title(section)}: zapisano kolejność kafelków"
    )
```

### 6.1. Odpowiedzialności pozostające w klasie

`DragDropCategoryGicleeApp` nadal odpowiada za:

- kontrolę `_active_section`;
- wywołanie `resolve_sections()`;
- wywołanie `category_map()`;
- zbudowanie `visible_order`;
- wywołanie `persist_component_reorder()`;
- decyzję o UI effects na podstawie zwróconego `bool`;
- `_render_tiles()`;
- `_finish_navigation_render()`;
- dokładny komunikat statusu:
  ```python
  f"{category_display_title(section)}: zapisano kolejność kafelków"
  ```

### 6.2. Co znika z klasy po implementacji

Z `DragDropCategoryGicleeApp._reorder_component()` usuwane są wyłącznie:

- komponentowe `reorder_relative()` (wewnętrzne wywołanie i zmienną `reordered_visible`);
- wybór i sortowanie wszystkich wpisów sekcji (blok `all_in_section`);
- komponentowe `replace_subset_order()` (wywołanie i zmienną `full_order`);
- pętla przypisująca `sort_key` (`for index, folder in enumerate(full_order)`);
- komponentowe `save_layout()`.

### 6.3. Co pozostaje bez zmian

- `_reorder_category()` i adapter LC-3J pozostają bez żadnych zmian;
- kolejność kategorii, `section_order`, `replace_subset_order()` dla sekcji — bez zmian;
- `LauncherLayout`, format JSON i ścieżki runtime — bez zmian;
- `save_layout()` i atomic writer — bez zmian;
- widoczność komponentów, przypisanie do sekcji — bez zmian;
- `resolve_sections()`, `category_map()` — bez zmian (nadal wywoływane przez klasę);
- drag gesture, target lookup, visual feedback, auto-scroll — bez zmian;
- Studio, Shopify, deployment, pliki startowe GPT — poza zakresem.

---

## 7. Kolejność operacji

Wymagana kolejność wewnątrz `_reorder_component()` po refaktorze:

1. `persist_component_reorder()` — mutacja modelu i zapis;
2. `_render_tiles()` — rereder UI;
3. `_finish_navigation_render()` — scroll i fokus;
4. `status_var.set(...)` — komunikat statusu.

Jeżeli krok 1 zwróci `False` albo zgłosi wyjątek, kroki 2–4 nie są wykonywane.

---

## 8. Poza zakresem LC-3K

LC-3K nie zmienia:

- LC-3J ani adaptera kolejności kategorii;
- kolejności kategorii (`section_order`);
- `LauncherLayout` i formatu JSON;
- `save_layout()` i atomic writera;
- widoczności komponentów;
- sekcji komponentów;
- przypisywania komponentów do kategorii;
- `resolve_sections()`;
- `category_map()`;
- drag gesture;
- target lookup;
- visual feedback;
- auto-scroll;
- Studio Preview;
- Shopify;
- deploymentu;
- plików startowych GPT;
- ZIP-a wiedzy.

---

## 9. Allowlista implementacyjna

Implementation PR musi zawierać dokładnie sześć plików:

1. `cursor-api/giclee_app/launcher_drag_component_persistence.py` — **nowy**;
2. `cursor-api/giclee_app/dragdrop_category_launcher.py` — usunięcie bloku persistence z `_reorder_component()`;
3. `cursor-api/tests/test_launcher_drag_component_persistence.py` — **nowy**;
4. `cursor-api/giclee_app/docs/launcher.md` — wpis LC-3K;
5. `cursor-api/giclee_app/docs/launcher-composition-lc3k-contract.md` — ten plik;
6. `cursor-api/tests/test_launcher_drag_category_persistence.py` — minimalna aktualizacja
   starego guardu LC-3J: test wcześniej zamrażał inline komponentowy writer
   (`reorder_relative`, `replace_subset_order`, `sort_key`, `save_layout` bezpośrednio
   w metodzie), a po LC-3K musi sprawdzać cienką delegację do
   `persist_component_reorder()`. Zmiana nie wpływa na semantykę LC-3J ani na
   `persist_category_reorder()`.

Helpery one-shot, workflowy techniczne i pliki tymczasowe nie mogą pozostać w finalnym
diffie implementacyjnym.

---

## 10. Focused tests — zamrożony suite

Docelowy suite implementacyjny musi obejmować co najmniej 23 przypadki:

### 10.1. Ruch widocznych komponentów

1. Ruch przed target (`after=False`) — `source` ląduje bezpośrednio przed `target`.
2. Ruch za target (`after=True`) — `source` ląduje bezpośrednio za `target`.

### 10.2. Ukryte komponenty

3. Ukryty komponent w slocie pomiędzy widocznymi — jego pozycja w `full_order` jest
   zachowana przez `replace_subset_order()`.
4. Ukryty komponent jest reindeksowany razem z widocznymi z tej samej sekcji.

### 10.3. Sortowanie i reindeksacja

5. Pełna sekcja jest sortowana przez `(sort_key, folder.lower())` przed
   `replace_subset_order()`.
6. Po operacji `sort_key` wynoszą `0, 10, 20, ...` dla wszystkich folderów w `full_order`.
7. Wpisy innych sekcji mają niezmienione `sort_key`.

### 10.4. Niemutowalność wejścia

8. Wejściowy `visible_order` przekazany przez wywołującego nie jest modyfikowany po
   powrocie z `persist_component_reorder()`.

### 10.5. No-op

9. `source == target` — zwraca `False`, brak mutacji, brak zapisu.
10. `source` nie istnieje w `visible_order` — zwraca `False`, brak mutacji, brak zapisu.
11. `target` nie istnieje w `visible_order` — zwraca `False`, brak mutacji, brak zapisu.
12. Ruch bez zmiany pozycji — zwraca `False`, brak mutacji, brak zapisu.

### 10.6. Kontrakt zapisu

13. Przy zmianie kolejności wywoływany jest dokładnie jeden `save_layout()`.
14. Zapisywany jest ten sam obiekt `LauncherLayout`, który był przekazany jako `layout`.
15. `save_layout()` jest wywoływany po pełnej reindeksacji — wszystkie `sort_key` mają
    wartości docelowe w momencie wywołania zapisu.
16. Przy no-op `save_layout()` nie jest wywoływany w ogóle.

### 10.7. Propagacja błędu

17. Gdy `save_layout()` zgłosi wyjątek, wyjątek propaguje się do wywołującego.
18. Po błędzie zapisu wcześniejsze mutacje `sort_key` pozostają — brak rollbacku.

### 10.8. Izolacja od UI

19. Adapter nie importuje `tkinter` ani żadnej warstwy UI.
20. Adapter nie wywołuje renderera, `_finish_navigation_render()` ani `status_var`.

### 10.9. Orchestration `_reorder_component()`

21. Cienka delegacja — `_reorder_component()` wywołuje `persist_component_reorder()` z
    właściwymi argumentami: `layout`, `section`, `visible_order`, `source`, `target`,
    `after`.
22. Brak UI effects dla `False` — gdy adapter zwróci `False`, metoda kończy się bez
    `_render_tiles()`, `_finish_navigation_render()` i `status_var.set()`.
23. Kolejność persist → render → finish → status — przy zmianie operacje następują w
    tej dokładnej kolejności.
24. Brak UI effects po wyjątku persistence — gdy adapter zgłosi wyjątek, metoda nie
    wywołuje kroków 2–4.
25. Brak aktywnej sekcji — metoda kończy się przed `resolve_sections()` i przed
    wywołaniem adaptera.

### 10.10. Niezmieniony `_reorder_category()` i LC-3J

26. `_reorder_category()` zachowuje bieżącą semantykę i nie zmienia zachowania.
27. Adapter LC-3J (`persist_category_reorder`) nie jest importowany ani wywoływany przez
    LC-3K.

---

## 11. Kryterium zakończenia

LC-3K jest zakończony, gdy:

- logika persistence komponentów (reorder, zebranie sekcji, subset, reindeksacja,
  zapis) znajduje się wyłącznie w `launcher_drag_component_persistence.py`;
- `_reorder_component()` jest cienkim orkiestratorem: sekcja, `resolve_sections()`,
  `category_map()`, `visible_order`, delegacja, UI effects;
- finalny diff obejmuje dokładnie sześć allowlistowanych plików;
- suite testowy pokrywa wszystkie 27 przypadków;
- adapter nie importuje `tkinter` ani żadnej warstwy UI;
- `_reorder_category()` i adapter LC-3J pozostają bez zmian;
- `git diff --check` nie zgłasza błędów;
- review threads = 0.

---

## 12. Rollback

LC-3K nie zmienia formatu danych ani ścieżek runtime. Rollback implementation PR to
zwykły revert pojedynczego squash commitu.

Nie wymaga migracji, czyszczenia AppData ani operacji Shopify.
