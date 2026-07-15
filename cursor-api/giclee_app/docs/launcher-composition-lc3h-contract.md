# ETAP 4B / LC-3H — Tk Drag Visual Feedback Adapter

**Status:** LC-3H implemented  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `718e8a561d49c9aca63a191173004bc756e955f6`  
**Data weryfikacji:** 2026-07-15

## 1. Cel pakietu

Wydzielić z `DragDropCategoryGicleeApp` wyłącznie best-effort efekty Tk odpowiedzialne za wizualną informację zwrotną podczas drag-and-drop:

- kolor ramki kafelka źródłowego;
- kolor ramki aktualnego celu;
- przywracanie normalnych ramek;
- kursor root `fleur` na początku drag;
- reset kursora po wyczyszczeniu gestu.

Pakiet nie tworzy szerokiego `DragDropController`. Nie przejmuje `_DragState`, wyboru targetu, decyzji `after`, auto-scrollu ani persistence.

## 2. Fresh reconnaissance — pozostałe skupiska DnD

Po scaleniu LC-3G w `dragdrop_category_launcher.py` pozostają trzy odrębne skupiska odpowiedzialności.

### 2.1. Visual feedback / czyszczenie UI — wybrane jako LC-3H

Obejmuje:

- `_BORDER_NORMAL = "#dcdce2"`;
- `_BORDER_DRAG_SOURCE = "#7b8798"`;
- `_BORDER_DROP_TARGET = "#496a9b"`;
- `tile.configure(highlightbackground=..., highlightcolor=...)`;
- `root.configure(cursor="fleur")` przy `DragMotionKind.START`;
- reset poprzedniego targetu przy zmianie celu;
- przywrócenie source/target do normalnej ramki;
- `root.configure(cursor="")` podczas `_clear_drag_state()`.

To spójna granica platformowa Tk. Wszystkie operacje są efektami wizualnymi i nie zapisują danych aplikacji.

### 2.2. Auto-scroll — późniejszy osobny mikro-adapter

Obejmuje wyłącznie geometrię `canvas`, margin `42 px` i `yview_scroll(-1/+1, "units")`. Nie należy łączyć go z feedbackiem.

### 2.3. Persistence — późniejszy writer boundary

Obejmuje `_reorder_category()`, `_reorder_component()`, `resolve_sections()`, `replace_subset_order()`, `save_layout()`, rerender i statusy. Jest większą granicą aplikacyjną i nie należy mieszać jej z adapterem Tk.

## 3. Zamrożona granica LC-3H

Nowy moduł:

- `cursor-api/giclee_app/launcher_tk_drag_feedback.py`

Publiczny kontrakt:

```python
import tkinter as tk


BORDER_NORMAL = "#dcdce2"
BORDER_DRAG_SOURCE = "#7b8798"
BORDER_DROP_TARGET = "#496a9b"


def begin_drag_feedback(root: tk.Misc, source: tk.Frame) -> None:
    ...


def clear_previous_drop_target(
    previous_target: tk.Frame | None,
    next_target: tk.Frame | None,
) -> None:
    ...


def show_drop_target(target: tk.Frame) -> None:
    ...


def clear_drag_tile_feedback(
    source: tk.Frame,
    target: tk.Frame | None,
) -> None:
    ...


def reset_drag_cursor(root: tk.Misc) -> None:
    ...
```

Moduł może importować wyłącznie bibliotekę standardową i `tkinter`.

Nie może importować:

- `DragDropCategoryGicleeApp`;
- `_DragState`;
- geometrii LC-3D;
- decyzji LC-3E;
- target lookup LC-3G;
- layoutu, persistence ani komponentów;
- `Komponenty`.

## 4. Zachowanie, które musi pozostać identyczne

### 4.1. Kolory i kursor

Wartości pozostają dokładnie:

```text
normal:      #dcdce2
source:      #7b8798
drop target: #496a9b
drag cursor: fleur
reset cursor: ""
```

Nie zmieniać nazw kursora, kolorów ani sposobu konfiguracji ramek.

Każde ustawienie ramki używa obu opcji:

```python
tile.configure(
    highlightbackground=color,
    highlightcolor=color,
)
```

### 4.2. Początek drag

Przy `DragMotionKind.START` kolejność w klasie pozostaje:

1. `state.dragging = True`;
2. `begin_drag_feedback(self.root, state.source)`;
3. auto-scroll;
4. target lookup;
5. aktualizacja targetu.

`begin_drag_feedback()`:

1. best-effort ustawia source border na `BORDER_DRAG_SOURCE`;
2. best-effort ustawia `root.configure(cursor="fleur")`.

`tk.TclError` z konfiguracji ramki lub kursora jest ignorowany jak obecnie. Funkcja nie dodaje retry i nie modyfikuje stanu gestu.

Visual start ma zostać wykonany tylko raz przy przejściu `START`, a nie przy kolejnych `CONTINUE`.

### 4.3. Zmiana targetu

`_set_drop_target()` pozostaje właścicielem `_DragState` i zachowuje kolejność:

1. jeżeli poprzedni target istnieje i różni się od nowego, przywrócić jego normalną ramkę przez `clear_previous_drop_target(previous, target)`;
2. przypisać `state.target = target`;
3. jeżeli target jest `None`, ustawić `state.after = False` i zakończyć;
4. obliczyć `state.after` przez istniejące `_drop_after()`;
5. ustawić ramkę targetu przez `show_drop_target(target)`.

`clear_previous_drop_target()`:

- nic nie robi, gdy previous jest `None`;
- nic nie robi, gdy previous i next są tym samym obiektem;
- w przeciwnym razie best-effort ustawia previous na `BORDER_NORMAL`.

`show_drop_target()` best-effort ustawia `BORDER_DROP_TARGET` także przy ponownym wskazaniu tego samego targetu, zgodnie z bieżącym zachowaniem.

Adapter nie oblicza `after`, nie zna współrzędnych i nie zwraca nowego stanu.

### 4.4. Czyszczenie gestu

`_clear_drag_state()` pozostaje właścicielem lifecycle i zachowuje kolejność:

1. odczytać bieżący `state`;
2. jeżeli istnieje, wywołać `clear_drag_tile_feedback(state.source, state.target)`;
3. ustawić `self._drag_state = None`;
4. wywołać `reset_drag_cursor(self.root)`.

`clear_drag_tile_feedback()`:

- best-effort ustawia source na `BORDER_NORMAL`;
- jeśli target istnieje, best-effort ustawia target na `BORDER_NORMAL`;
- zachowuje kolejność source przed target;
- nie resetuje kursora;
- nie mutuje `_DragState`.

`reset_drag_cursor()` wywołuje `root.configure(cursor="")` i ignoruje `AttributeError` oraz `tk.TclError`, zgodnie z bieżącą semantyką `_clear_drag_state()`.

Nawet gdy `_drag_state` jest `None`, kursor root nadal jest resetowany.

### 4.5. Semantyka błędów

- błędy wizualne pozostają best-effort;
- nie propagować `tk.TclError` z konfiguracji ramek ani kursora;
- nie logować, nie ponawiać i nie pokazywać dialogów;
- nie maskować błędów spoza jawnie zamrożonych wyjątków;
- begin cursor zachowuje obecne ignorowanie `tk.TclError`;
- reset cursor zachowuje obecne ignorowanie `AttributeError` i `tk.TclError`.

## 5. Odpowiedzialności pozostające w klasie

`DragDropCategoryGicleeApp` nadal:

- posiada `_DragState` i wszystkie jego pola;
- ustawia `state.dragging`;
- posiada `_set_drop_target()` jako orchestration stanu;
- przypisuje `state.target` i `state.after`;
- oblicza `after` przez LC-3D z ratio `0.22`;
- posiada `_clear_drag_state()` i ustawia referencję na `None`;
- posiada eventy press/motion/release;
- posiada target lookup LC-3G;
- posiada auto-scroll z marginem `42 px`;
- posiada persistence kategorii i komponentów;
- zachowuje clear-before-reorder.

Nie przenosić `_DragState` ani `_set_drop_target()` do nowego modułu.

## 6. Jawnie poza zakresem

LC-3H nie zmienia:

- `_DragState` ani jego pól;
- progu drag `8 px`;
- ratio `0.22`;
- target lookup i `launcher_tk_drag_targets.py`;
- bindingów i `launcher_tk_drag_bindings.py`;
- geometrii LC-3D;
- decyzji LC-3E;
- `_auto_scroll_drag()` ani marginu `42 px`;
- `_reorder_category()`;
- `_reorder_component()`;
- `resolve_sections()`, `save_layout()` ani formatu danych;
- click-vs-drag;
- kolejności clear-before-reorder;
- entrypointu, MRO, kategorii, gridu, skrótów, Studio i background services;
- Stage 2 CI;
- Shopify, deployu, plików startowych GPT i ZIP-a wiedzy.

## 7. Allowlista implementacyjna

### Finding z focused validation

Pierwszy focused run wykazał jedną przestarzałą source assertion w `test_launcher_drag_geometry.py`, która nadal wymagała bezpośredniego `self.root.configure(cursor="fleur")` w launcherze. Po LC-3H odpowiedzialność jest delegowana do `begin_drag_feedback()`. To finding testowy, nie regresja runtime; kontrakt zostaje rozszerzony o ten jeden plik przed jego edycją.

Kod:

1. nowy `cursor-api/giclee_app/launcher_tk_drag_feedback.py`;
2. `cursor-api/giclee_app/dragdrop_category_launcher.py`.

Testy:

3. nowy `cursor-api/tests/test_launcher_tk_drag_feedback.py`;
4. `cursor-api/tests/test_launcher_drag_gesture.py` — przeniesienie szczegółowych asercji efektów Tk do adaptera i potwierdzenie orchestration klasy;
5. `cursor-api/tests/test_launcher_drag_geometry.py` — aktualizacja przestarzałej source assertion kursora do delegacji LC-3H.

Dokumentacja:

6. `cursor-api/giclee_app/docs/launcher.md`;
7. ten kontrakt.

Finalny implementation PR obejmuje dokładnie siedem plików. Każde dalsze rozszerzenie wymaga osobnego findingu i aktualizacji kontraktu przed edycją.

Docs-only contract PR obejmuje wyłącznie ten jeden plik.

## 8. Focused tests

Nowy suite musi potwierdzić:

1. `begin_drag_feedback()` ustawia dokładny source border i `cursor="fleur"`;
2. kolejność efektów begin: source border przed root cursor;
3. `tk.TclError` source border nie blokuje ustawienia kursora;
4. `tk.TclError` kursora nie propaguje się;
5. previous target jest resetowany wyłącznie przy zmianie obiektu;
6. previous `None` nie powoduje konfiguracji;
7. ten sam previous/next nie powoduje resetu;
8. `show_drop_target()` ustawia oba pola na dokładny target color;
9. clear resetuje source przed targetem;
10. clear bez targetu resetuje tylko source;
11. błędy ramek podczas clear są best-effort i nie blokują kolejnych operacji;
12. reset kursora działa także bez aktywnego stanu;
13. reset ignoruje `AttributeError` i `tk.TclError`;
14. adapter nie importuje aplikacji, geometrii, gestu, target lookupu, layoutu, persistence ani `Komponenty`;
15. adapter nie przechowuje mutable state i nie zna `_DragState`;
16. motion klasy ustawia `state.dragging=True` przed begin feedback;
17. begin feedback jest wywołany tylko przy `START`, nie `WAITING` ani kolejnym `CONTINUE`;
18. `_set_drop_target()` zachowuje kolejność reset previous → przypisanie target → obliczenie after → show target;
19. target `None` zeruje `after` i nie pokazuje target feedbacku;
20. `_clear_drag_state()` czyści kafelki, zeruje stan, a następnie resetuje kursor;
21. release nadal czyści stan przed reorder;
22. kolory i cursor nie pozostają zduplikowane w launcherze.

Focused regression set:

- `tests/test_launcher_tk_drag_feedback.py`;
- `tests/test_launcher_drag_gesture.py`;
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
- dokładny scope guard siedmiu plików;
- finalny diff bez helperów i workflowów one-shot;
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
2. kliknąć kafelek bez drag i potwierdzić brak pozostawionego feedbacku;
3. rozpocząć drag i potwierdzić source border oraz kursor `fleur`;
4. przesunąć przez dwa cele i potwierdzić reset poprzedniego oraz podświetlenie bieżącego;
5. wyjechać poza obszar targetów i potwierdzić reset poprzedniego celu;
6. zwolnić przycisk i potwierdzić normalne ramki oraz pusty kursor;
7. zmienić ekran podczas gestu i potwierdzić pełne czyszczenie;
8. potwierdzić brak regresji auto-scrollu i trwałego zapisu kolejności.

## 10. Rollback

LC-3H nie zmienia formatu danych ani ścieżek runtime. Rollback implementation PR to zwykły revert pojedynczego squash commitu.

Nie wymaga migracji, czyszczenia AppData ani operacji Shopify.

## 11. Kryterium zakończenia

LC-3H jest zakończony, gdy:

- wszystkie best-effort efekty ramek i kursora znajdują się w jednym adapterze Tk;
- klasa zachowuje ownership stanu, targetu, `after`, auto-scrollu i persistence;
- kolejność efektów oraz clear-before-reorder pozostają bez zmian;
- finalny diff obejmuje dokładnie siedem allowlistowanych plików;
- focused suite, scope guard, Hermetic, Tk GUI, pełny baseline i inventory są zielone na tym samym exact headzie;
- review threads = 0;
- branch jest `behind_by=0`;
- nie zmieniono UX drag-and-drop, click-vs-drag, target selection, auto-scrollu, persistence ani entrypointu.
