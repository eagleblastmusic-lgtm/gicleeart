# ETAP 4B / LC-3E — Pure Drag Gesture Decisions

**Status:** LC-3E implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `e53a0d605ada8cf273d964aee2855cce50c23a13`  
**Data weryfikacji:** 2026-07-15

## 1. Kontekst po LC-3D

LC-3D wydzielił czyste obliczenia geometryczne:

- próg ruchu;
- prostokąty i hit-testing;
- `drop_after`;
- wybór najbliższego celu.

`DragDropCategoryGicleeApp` nadal poprawnie posiada:

- mutable `_DragState` z referencjami do widgetów i callbackiem;
- eventy press/motion/release;
- wizualny feedback;
- auto-scroll;
- lookup celu;
- czyszczenie stanu;
- faktyczny reorder i zapis layoutu.

Fresh review aktualnego `master` pokazał jednak dwa małe, czyste rozstrzygnięcia nadal zapisane jako warunki wewnątrz handlerów:

1. czy motion ma jeszcze czekać, rozpocząć drag czy kontynuować już aktywny drag;
2. czy release ma uruchomić klik, wykonać reorder czy zakończyć się bez zmiany.

## 2. Decyzja zakresowa

LC-3E wydziela wyłącznie **decyzje przejścia gestu**, bez przenoszenia stanu, widgetów ani efektów.

Nie jest to jeszcze pełny `DragDropController`.

LC-3E nie przenosi:

- `_DragState`;
- `state.dragging = True`;
- `state.target` i `state.after`;
- `activate()`;
- `_find_drop_target()`;
- `_drop_after()`;
- `_clear_drag_state()`;
- borderów, kursora i auto-scrollu;
- `_reorder_category()` ani `_reorder_component()`;
- storage i renderu.

## 3. Docelowy moduł

Nowy plik:

`cursor-api/giclee_app/launcher_drag_gesture.py`

Moduł nie może importować:

- `tkinter`;
- launchera ani klas UI;
- geometrii LC-3D;
- layoutu, storage i kolejności danych;
- komponentów;
- Studio;
- `Komponenty`.

### Motion

```python
class DragMotionKind(str, Enum):
    WAITING = "waiting"
    START = "start"
    CONTINUE = "continue"


def resolve_drag_motion(*, dragging: bool, threshold_reached: bool) -> DragMotionKind:
    ...
```

Kontrakt:

- `dragging=True` zawsze zwraca `CONTINUE`, niezależnie od progu;
- `dragging=False` i próg osiągnięty zwraca `START`;
- `dragging=False` i próg nieosiągnięty zwraca `WAITING`;
- funkcja nie ma efektów ubocznych.

### Release

```python
class DragReleaseKind(str, Enum):
    ACTIVATE = "activate"
    REORDER = "reorder"
    NOOP = "noop"


@dataclass(frozen=True)
class DragReleaseDecision:
    kind: DragReleaseKind
    drag_kind: str
    source_key: str
    target_key: str
    after: bool
```

```python
def resolve_drag_release(
    *,
    dragging: bool,
    drag_kind: str,
    source_key: str,
    target_key: str,
    after: bool,
) -> DragReleaseDecision:
    ...
```

Kontrakt:

1. `dragging=False` zawsze zwraca `ACTIVATE`;
2. drag bez celu zwraca `NOOP`;
3. drag na ten sam klucz zwraca `NOOP`;
4. rodzaj inny niż `category` lub `component` zwraca `NOOP`;
5. prawidłowy cel dla `category` lub `component` zwraca `REORDER`;
6. `after` jest zachowane bez zmiany;
7. wejścia nie są mutowane ani normalizowane;
8. decision object jest niemutowalny.

Priorytet `ACTIVATE` przed pozostałymi warunkami zachowuje obecne zachowanie kliknięcia: nieprzekroczony próg uruchamia callback nawet wtedy, gdy nie ma celu DnD.

## 4. Adapter w `DragDropCategoryGicleeApp`

### `_on_tile_motion()`

Handler nadal:

- pobiera `_drag_state`;
- oblicza threshold przez LC-3D;
- ustawia `state.dragging = True` przy rozpoczęciu;
- ustawia border źródła i cursor;
- wykonuje auto-scroll;
- znajduje target i ustawia feedback;
- zwraca istniejące `None` albo `"break"`.

Zmiana:

- wywołuje `resolve_drag_motion(...)`;
- `WAITING` zwraca `None`;
- `START` uruchamia istniejący blok startowych efektów;
- `CONTINUE` pomija blok startowy i wykonuje dalszą orkiestrację.

### `_on_tile_release()`

Handler nadal:

- rozwiązuje fallback targetu;
- oblicza `after` przez LC-3D;
- odczytuje target key z widgetu;
- czyści stan dokładnie raz przed reorderem;
- uruchamia callback lub faktyczny reorder;
- zwraca `"break"` dla każdego istniejącego stanu.

Dopuszczalna struktura:

1. ścieżka click tworzy decyzję z `dragging=False`, czyści `_drag_state` bez wizualnego teardownu, uruchamia callback dla `ACTIVATE`;
2. ścieżka drag rozwiązuje target/after, tworzy decyzję, wywołuje `_clear_drag_state()`, a potem wykonuje `REORDER` tylko dla właściwego rodzaju.

LC-3E nie może zmienić momentu wywołania `_clear_drag_state()` względem persistence.

## 5. Zachowanie wymagane 1:1

1. event bez `_drag_state` nadal zwraca `None`;
2. motion poniżej progu nadal nie zmienia stanu i zwraca `None`;
3. dokładnie na progu nadal rozpoczyna drag;
4. startowe bordery/cursor są ustawiane tylko raz;
5. każdy motion po rozpoczęciu wykonuje auto-scroll i target lookup;
6. click ustawia `_drag_state = None`, wywołuje callback i zwraca `"break"`;
7. release drag zawsze czyści wizualny stan przed reorderem;
8. brak targetu nie zapisuje layoutu;
9. target równy source nie zapisuje layoutu;
10. nieznany `kind` nie zapisuje layoutu;
11. `category` deleguje tylko do `_reorder_category()`;
12. `component` deleguje tylko do `_reorder_component()`;
13. `after` jest przekazane bez zmiany;
14. target zapisany w stanie nadal ma pierwszeństwo nad lookupiem release;
15. fallback `after` jest liczony tylko, gdy target znaleziono dopiero na release;
16. geometry, feedback, auto-scroll, persistence, entrypoint i MRO pozostają bez zmian.

## 6. Allowlista implementacyjna

Dozwolone pliki:

- `cursor-api/giclee_app/launcher_drag_gesture.py` — nowy;
- `cursor-api/giclee_app/dragdrop_category_launcher.py` — wyłącznie delegacja motion/release decisions;
- `cursor-api/tests/test_launcher_drag_gesture.py` — nowy;
- `cursor-api/giclee_app/docs/launcher.md` — krótki wpis LC-3E;
- ten kontrakt — aktualizacja statusu.

Nie są dozwolone zmiany w:

- `launcher_drag_geometry.py`;
- `launcher_tile_order.py`;
- layout/storage i formacie JSON;
- rendererze, gridzie, nawigacji i skrótach;
- `launcher.py` i entrypointach;
- Studio i komponentach;
- CI;
- danych użytkownika;
- plikach startowych, ZIP-ie i Shopify.

## 7. Focused tests

Nowy focused suite musi potwierdzić:

1. trzy wyniki motion;
2. `dragging=True` ma priorytet nad progiem;
3. click release zwraca `ACTIVATE` także bez targetu;
4. missing/self/unknown release zwraca `NOOP`;
5. category/component zwracają `REORDER`;
6. `after` zachowuje wartość;
7. decision jest frozen;
8. moduł nie importuje Tk, aplikacji, geometrii, layoutu ani Studio;
9. motion handler deleguje resolver i zachowuje istniejące efekty;
10. startowe efekty są wykonywane tylko dla `START`;
11. click nadal czyści referencję i uruchamia callback;
12. drag czyści stan przed wywołaniem reorderu;
13. category/component trafiają do właściwych metod;
14. NOOP nie wywołuje persistence;
15. target ze stanu ma pierwszeństwo;
16. fallback target/after pozostaje bez zmian;
17. LC-3D geometry i tile order tests nadal są zielone.

Minimalny focused regression set:

- `tests/test_launcher_drag_gesture.py`;
- `tests/test_launcher_drag_geometry.py`;
- `tests/test_launcher_tile_order.py`;
- `tests/test_launcher_composition.py`;
- `tests/test_launcher_category_renderer.py`;
- `tests/test_launcher_tk_shortcut_bindings.py`;
- `tests/test_giclee_app_packaging.py`.

Po focused PASS obowiązują standardowe bramy:

- `git diff --check`;
- strict scope guard;
- Hermetic;
- Tk GUI;
- mirror/warmup/`VerifyOnly`;
- pełny baseline;
- JUnit i runtime-write inventory;
- exact-head review.

## 8. Manual smoke

1. zwykły klik nadal uruchamia kategorię lub komponent;
2. ruch poniżej progu pozostaje kliknięciem;
3. pierwszy ruch na progu rozpoczyna drag i zmienia cursor/border;
4. dalszy ruch nie powtarza startowych efektów;
5. category reorder działa before/after;
6. component reorder działa before/after;
7. self-drop i drop poza canvas nie zapisują zmian;
8. auto-scroll i feedback pozostają bez regresji;
9. kolejność pozostaje po restarcie;
10. skróty, nawigacja i inline launch pozostają bez regresji.

## 9. Rollback

LC-3E nie zmienia danych ani formatów. Rollback to revert pojedynczego commitu implementacyjnego bez migracji.

## 10. Kryteria ukończenia

- moduł decyzji jest czysty i niemutowalny;
- klasa nadal posiada stan, widgety i efekty;
- diff mieści się w pięciu plikach;
- focused i wszystkie Stage 2 gates są zielone na jednym exact headzie;
- artifact ma 0 failures/errors;
- inventory ma 0 parse errors i 0 findings;
- `behind_by=0` i brak review threads;
- merge używa expected exact head SHA.

## 11. Następny krok

Po LC-3E wymagany jest fresh review kolejnej granicy DnD. Nadal nieautoryzowane implementacyjnie pozostają:

- adapter feedbacku i auto-scrollu;
- persistence adapter kategorii/komponentów;
- finalny stateful `DragDropController`.
