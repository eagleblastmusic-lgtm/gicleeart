# ETAP 4B / LC-3I — Tk Drag Auto-Scroll Adapter

**Status:** LC-3I implemented  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `440a462e195f156c41b3af882cacc38c4172589c`  
**Data weryfikacji:** 2026-07-15

## 1. Cel pakietu

Wydzielić z `DragDropCategoryGicleeApp._auto_scroll_drag()` wyłącznie mechanikę Tk odpowiedzialną za pionowy auto-scroll obszaru kafelków podczas aktywnego drag-and-drop.

Pakiet obejmuje:

- odczyt pionowej geometrii `canvas`;
- zachowanie marginesu aktywacji `42 px`;
- pojedynczy scroll o `-1` lub `+1` jednostkę;
- zachowanie istniejącej semantyki błędów Tk.

Pakiet nie tworzy szerokiego `DragDropController`. Nie przejmuje `_DragState`, target lookupu, visual feedbacku ani persistence.

## 2. Fresh reconnaissance — pozostałe skupiska DnD

Po scaleniu LC-3H w `dragdrop_category_launcher.py` pozostają dwie odrębne granice.

### 2.1. Tk drag auto-scroll — wybrane jako LC-3I

Bieżąca metoda `_auto_scroll_drag()`:

1. odczytuje `canvas.winfo_rooty()`;
2. odczytuje `canvas.winfo_height()`;
3. oblicza dolną granicę `top + height`;
4. używa stałego marginesu `42 px`;
5. przewija o `-1` jednostkę przy górnej krawędzi;
6. przewija o `+1` jednostkę przy dolnej krawędzi;
7. nie przewija w strefie środkowej;
8. ignoruje wyłącznie `tk.TclError` z odczytu geometrii.

To mała, kompletna granica platformowa Tk, bez danych aplikacyjnych i bez mutable state.

### 2.2. Persistence kategorii i komponentów — późniejszy writer boundary

Pozostają:

- `_reorder_category()`;
- `_reorder_component()`;
- `resolve_sections()`;
- `category_map()`;
- `reorder_relative()` i `replace_subset_order()`;
- mutacja `section_order` i `sort_key`;
- `save_layout()`;
- rerender, navigation finish i status text.

To większa granica aplikacyjna z trwałym zapisem. Nie należy mieszać jej z adapterem auto-scrollu.

## 3. Zamrożona granica LC-3I

Nowy moduł:

- `cursor-api/giclee_app/launcher_tk_drag_auto_scroll.py`

Publiczny kontrakt:

```python
import tkinter as tk


DRAG_AUTO_SCROLL_MARGIN_PX = 42


def auto_scroll_drag(
    canvas: tk.Misc,
    y_root: int,
    *,
    margin: int = DRAG_AUTO_SCROLL_MARGIN_PX,
) -> None:
    ...
```

Moduł może importować wyłącznie bibliotekę standardową i `tkinter`.

Nie może importować:

- `DragDropCategoryGicleeApp` ani `_DragState`;
- geometrii LC-3D;
- decyzji LC-3E;
- bindingów LC-3F;
- target lookupu LC-3G;
- feedbacku LC-3H;
- layoutu, persistence ani komponentów;
- `Komponenty`.

## 4. Zachowanie, które musi pozostać identyczne

### 4.1. Odczyt geometrii

Adapter wykonuje dokładnie:

```python
top = canvas.winfo_rooty()
bottom = top + canvas.winfo_height()
```

Odczyt pozostaje w tej kolejności.

Jeżeli `winfo_rooty()` lub `winfo_height()` rzuci `tk.TclError`, funkcja zwraca `None` bez wywołania `yview_scroll()`.

Adapter:

- nie wywołuje `update()`;
- nie wywołuje `update_idletasks()`;
- nie zmienia geometrii widgetu;
- nie przechowuje wyniku między eventami.

### 4.2. Margin

Domyślny margin pozostaje dokładnie `42 px` i jest jawnie nazwanym kontraktem modułu.

Klasa wywołuje adapter z domyślnym marginem; nie duplikuje liczby `42` w `dragdrop_category_launcher.py`.

Publiczny parametr `margin` umożliwia focused testing granic bez zmiany runtime defaultu.

Margin musi być liczbą całkowitą nieujemną. Dla wartości ujemnej adapter podnosi `ValueError` przed odczytem geometrii i przed jakimkolwiek scrollem.

Walidacja ujemnego marginu jest jedynym nowym jawnie zdefiniowanym błędem wejścia i nie zmienia produkcyjnej ścieżki, która zawsze używa `42`.

### 4.3. Górna strefa

Jeżeli:

```python
y_root < top + margin
```

adapter wywołuje dokładnie:

```python
canvas.yview_scroll(-1, "units")
```

Równość `y_root == top + margin` nie uruchamia górnego scrollu.

### 4.4. Dolna strefa

Dolna strefa jest sprawdzana przez `elif`, dopiero gdy górny warunek był fałszywy.

Jeżeli:

```python
y_root > bottom - margin
```

adapter wywołuje dokładnie:

```python
canvas.yview_scroll(1, "units")
```

Równość `y_root == bottom - margin` nie uruchamia dolnego scrollu.

### 4.5. Strefa środkowa

Jeżeli żaden z warunków nie jest spełniony, `yview_scroll()` nie jest wywoływany.

Funkcja zawsze zwraca `None`.

### 4.6. Nakładające się strefy

Dla bardzo niskiego canvasu, gdy górna i dolna strefa matematycznie się nakładają, bieżąca kolejność `if/elif` ma zostać zachowana:

- jeżeli górny warunek jest prawdziwy, wykonywany jest scroll `-1`;
- dolny warunek nie jest już oceniany jako akcja;
- podczas jednego eventu może wystąpić maksymalnie jedno wywołanie `yview_scroll()`.

Nie dodawać normalizacji, clampowania, wyboru „bliższej” krawędzi ani dwóch scrolli.

### 4.7. Semantyka błędów

- `tk.TclError` z `winfo_rooty()` lub `winfo_height()` jest ignorowany i kończy funkcję;
- błąd z `yview_scroll()` nie jest maskowany, ponieważ bieżący kod go nie przechwytuje;
- nie dodawać retry, logowania, dialogów ani fallbacku;
- nie przechwytywać `AttributeError` ani innych wyjątków poza zamrożonym `tk.TclError` geometrii.

## 5. Odpowiedzialności pozostające w klasie

`DragDropCategoryGicleeApp` nadal:

- posiada `_DragState`;
- rozstrzyga `WAITING / START / CONTINUE` przez LC-3E;
- rozpoczyna visual feedback LC-3H;
- wywołuje auto-scroll przed target lookupem;
- przekazuje bieżące `event.y_root` jako `int`;
- posiada `_auto_scroll_drag()` jako cienki wrapper i punkt rozszerzenia testów;
- wykonuje target lookup LC-3G po auto-scrollu;
- aktualizuje target i `after`;
- posiada persistence kategorii i komponentów.

Metoda klasy ma pozostać cienkim wrapperem:

```python
def _auto_scroll_drag(self, y_root: int) -> None:
    auto_scroll_drag(self.canvas, y_root)
```

## 6. Kolejność orchestration motion

`_on_tile_motion()` zachowuje bieżącą kolejność:

1. odczyt stanu;
2. decyzja threshold i LC-3E;
3. przy `START`: `state.dragging = True`;
4. przy `START`: visual feedback LC-3H;
5. auto-scroll LC-3I;
6. target lookup LC-3G;
7. `_set_drop_target()`;
8. zwrot `"break"`.

Auto-scroll ma być wykonywany zarówno dla `START`, jak i każdego `CONTINUE`, ale nigdy dla `WAITING` ani braku stanu.

## 7. Jawnie poza zakresem

LC-3I nie zmienia:

- `_DragState` ani jego pól;
- progu drag `8 px`;
- decyzji LC-3E;
- kolorów, ramek ani kursora LC-3H;
- target lookupu LC-3G;
- ratio `0.22` ani decyzji `after`;
- bindingów LC-3F;
- `_reorder_category()`;
- `_reorder_component()`;
- `resolve_sections()`, `save_layout()` ani formatu danych;
- click-vs-drag;
- clear-before-reorder;
- entrypointu, MRO, kategorii, gridu, skrótów, Studio i background services;
- Stage 2 CI;
- Shopify, deployu, plików startowych GPT i ZIP-a wiedzy.

## 8. Allowlista implementacyjna

Kod:

1. nowy `cursor-api/giclee_app/launcher_tk_drag_auto_scroll.py`;
2. `cursor-api/giclee_app/dragdrop_category_launcher.py`.

Testy:

3. nowy `cursor-api/tests/test_launcher_tk_drag_auto_scroll.py`;
4. `cursor-api/tests/test_launcher_drag_gesture.py` — potwierdzenie orchestration i delegacji wrappera.

Dokumentacja:

5. `cursor-api/giclee_app/docs/launcher.md`;
6. ten kontrakt.

Finalny implementation PR obejmuje dokładnie sześć plików. Każde rozszerzenie wymaga osobnego findingu i aktualizacji kontraktu przed edycją.

Docs-only contract PR obejmuje wyłącznie ten jeden plik.

## 9. Focused tests

Nowy suite musi potwierdzić:

1. dokładny default margin `42`;
2. górny scroll `(-1, "units")` poniżej granicy;
3. brak scrollu dokładnie na górnej granicy;
4. dolny scroll `(1, "units")` powyżej granicy;
5. brak scrollu dokładnie na dolnej granicy;
6. brak scrollu w strefie środkowej;
7. odczyt `winfo_rooty()` przed `winfo_height()`;
8. `tk.TclError` z `winfo_rooty()` kończy bez odczytu wysokości i bez scrollu;
9. `tk.TclError` z `winfo_height()` kończy bez scrollu;
10. błąd `yview_scroll()` propaguje się;
11. przy nakładających się strefach górny scroll ma priorytet;
12. maksymalnie jeden scroll na event;
13. ujemny margin daje `ValueError` przed odczytem widgetu;
14. adapter nie konfiguruje widgetu i nie wywołuje update;
15. adapter nie importuje aplikacji, geometrii, gestu, target lookupu, feedbacku, layoutu, persistence ani `Komponenty`;
16. wrapper klasy przekazuje dokładnie `self.canvas` i `y_root`;
17. motion wywołuje auto-scroll po begin feedbacku i przed target lookupem;
18. auto-scroll działa przy `START` i `CONTINUE`;
19. auto-scroll nie działa przy `WAITING` ani braku `_drag_state`;
20. liczba `42` i bezpośrednie `yview_scroll()` nie pozostają zduplikowane w launcherze.

Focused regression set:

- `tests/test_launcher_tk_drag_auto_scroll.py`;
- `tests/test_launcher_drag_gesture.py`;
- `tests/test_launcher_tk_drag_feedback.py`;
- `tests/test_launcher_tk_drag_targets.py`;
- `tests/test_launcher_tk_drag_bindings.py`;
- `tests/test_launcher_drag_geometry.py`;
- `tests/test_launcher_tile_order.py`;
- `tests/test_launcher_composition.py`;
- `tests/test_launcher_category_renderer.py`;
- `tests/test_launcher_grid_layout.py`;
- `tests/test_giclee_app_packaging.py`.

Dopiero po focused PASS:

- `git diff --check`;
- dokładny scope guard sześciu plików;
- finalny diff bez helperów i workflowów one-shot;
- Hermetic;
- Tk GUI smoke;
- mirror Tcl/Tk, warmup i `VerifyOnly`;
- pełny baseline;
- JUnit;
- runtime-write inventory;
- exact-head review.

## 10. Manual smoke

Na Windows po implementacji:

1. uruchomić `python -m giclee_app`;
2. rozpocząć drag kafelka w środku canvasu — brak scrollu;
3. przesunąć wskaźnik w górny margin — scroll o jedną jednostkę w górę;
4. utrzymać ruch w górnym marginie — scroll przy kolejnych eventach motion;
5. przesunąć wskaźnik w dolny margin — scroll o jedną jednostkę w dół;
6. potwierdzić brak scrollu dokładnie na obu granicach;
7. potwierdzić, że po scrollu target lookup nadal wskazuje właściwe kafelki;
8. potwierdzić brak regresji visual feedbacku i trwałego zapisu kolejności.

## 11. Rollback

LC-3I nie zmienia formatu danych ani ścieżek runtime. Rollback implementation PR to zwykły revert pojedynczego squash commitu.

Nie wymaga migracji, czyszczenia AppData ani operacji Shopify.

## 12. Kryterium zakończenia

LC-3I jest zakończony, gdy:

- mechanika geometrii canvasu i `yview_scroll()` znajduje się w jednym adapterze Tk;
- klasa zachowuje cienki wrapper oraz orchestration motion;
- margin `42`, warunki graniczne, `if/elif` i semantyka błędów pozostają bez zmian;
- finalny diff obejmuje dokładnie sześć allowlistowanych plików;
- focused suite, scope guard, Hermetic, Tk GUI, pełny baseline i inventory są zielone na tym samym exact headzie;
- review threads = 0;
- branch jest `behind_by=0`;
- nie zmieniono UX drag-and-drop, target selection, visual feedbacku, persistence ani entrypointu.
