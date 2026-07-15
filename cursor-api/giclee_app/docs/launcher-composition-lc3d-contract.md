# ETAP 4B / LC-3D — Pure Drag Geometry

**Status:** fresh reconnaissance · contract freeze  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `3486ccb6f1f803bc26d9e92d4dceb46a067fd646`  
**Data weryfikacji:** 2026-07-15

## 1. Kontekst po LC-3A–LC-3C

Warstwa skrótów została rozdzielona na:

- czyste decyzje aktywacji;
- adapter WinAPI;
- adapter bindingów Tk.

Fresh review `DragDropCategoryGicleeApp` potwierdził, że drag-and-drop nadal łączy w jednym pliku:

1. stan i lifecycle gestu;
2. geometrię i hit-testing;
3. orkiestrację eventów Tk;
4. wizualny feedback i cursor;
5. auto-scroll;
6. trwały zapis kolejności kategorii i komponentów.

Czysta logika kolejności danych jest już osobno w `launcher_tile_order.py` i nie może być duplikowana.

## 2. Finding i decyzja zakresowa

Najmniejszym bezpiecznym pierwszym pakietem DnD jest wydzielenie wyłącznie obliczeń geometrycznych, które nie potrzebują Tk, layoutu ani danych komponentów:

- rozpoznanie przekroczenia progu ruchu;
- reprezentacja prostokąta kafelka;
- test punktu wewnątrz prostokąta;
- wybór strony `before/after` względem środka kafelka;
- wybór najbliższego prostokąta według odległości od środka.

LC-3D nie tworzy jeszcze pełnego `DragDropController`. Stan `_DragState`, eventy i side effects pozostają w `DragDropCategoryGicleeApp`.

## 3. Docelowy moduł

Nowy plik:

`cursor-api/giclee_app/launcher_drag_geometry.py`

Moduł nie może importować:

- `tkinter`;
- launchera ani klas UI;
- komponentów;
- layoutu i storage;
- `launcher_tile_order`;
- Studio;
- DnD adaptera.

### Typy

```python
@dataclass(frozen=True)
class DragPoint:
    x: float
    y: float


@dataclass(frozen=True)
class DragRect:
    left: float
    top: float
    width: float
    height: float
```

`DragRect` udostępnia wyłącznie czyste właściwości geometryczne: `right`, `bottom`, `center_x`, `center_y`.

### Funkcje

1. `drag_threshold_reached(start, current, threshold) -> bool`
   - używa odległości euklidesowej;
   - dokładnie na progu zwraca `True`;
   - próg ujemny jest błędem kontraktu (`ValueError`);
   - nie mutuje wejść.

2. `point_inside(rect, point) -> bool`
   - lewa i górna granica są domknięte;
   - prawa i dolna granica są otwarte;
   - zachowuje dotychczasowy kontrakt kafelków Tk.

3. `drop_after(rect, point, *, vertical_ratio) -> bool`
   - gdy pionowe odchylenie od środka przekracza `height * vertical_ratio`, wynik zależy od góra/dół;
   - wewnątrz pasa środkowego wynik zależy od lewa/prawa;
   - dokładnie na osi środka zwraca `False`;
   - wysokość do obliczeń jest co najmniej `1`, zgodnie z obecnym kodem;
   - `vertical_ratio < 0` jest błędem kontraktu.

4. `nearest_rect_index(rects, point) -> int | None`
   - zwraca indeks prostokąta o najmniejszej odległości od środka;
   - pusty input zwraca `None`;
   - remis zachowuje pierwszy element, tak jak dotychczasowy `min(...)` nad listą kandydatów;
   - nie mutuje wejścia.

## 4. Adapter w `DragDropCategoryGicleeApp`

Klasa zachowuje istniejące nazwy i kontrakty metod.

### Próg gestu

`_on_tile_motion()` nadal posiada stan i side effects, ale deleguje decyzję progu do `drag_threshold_reached(...)` z niezmienionym `_DRAG_THRESHOLD_PX = 8`.

### Bounds adapter

Klasa otrzymuje prywatny helper `_widget_drag_rect(widget) -> DragRect | None`, który:

- odczytuje `winfo_rootx/y/width/height`;
- zamienia dane Tk na `DragRect`;
- przy `tk.TclError` zwraca `None`;
- nie przechowuje cache.

### Istniejące wrappery

- `_point_inside_tile()` pobiera bounds i deleguje do `point_inside()`;
- `_pointer_over_tiles_area()` pobiera bounds canvas i deleguje do `point_inside()`;
- `_drop_after()` pobiera bounds i deleguje do `drop_after()` z niezmienionym ratio `0.22`;
- fallback najbliższego celu w `_find_drop_target()` buduje listę istniejących kafelków z bounds, wywołuje `nearest_rect_index()` i zwraca odpowiadający frame.

Bezpośrednie `winfo_containing()` oraz przejście po `master` pozostają bez zmian i nadal mają pierwszeństwo przed fallbackiem najbliższego kafelka.

## 5. Zachowanie, które musi pozostać bez zmian

LC-3D musi zachować:

1. próg drag dokładnie `8 px`;
2. klik bez przekroczenia progu uruchamia `activate()` przy release;
3. drag zaczyna się dokładnie na progu;
4. ruch wewnątrz źródła nie wybiera sąsiada;
5. `winfo_containing()` ma pierwszeństwo nad fallbackiem nearest;
6. fallback nearest działa tylko nad obszarem canvas;
7. kandydaci są ograniczeni do tego samego `kind` i istniejących widgetów;
8. kolejność kandydatów rozstrzyga remis;
9. pionowy próg `0.22` wysokości kafelka;
10. lewa/góra są inside, prawa/dół outside;
11. wszystkie kolory, cursor i border feedback;
12. auto-scroll margin `42` i kierunek scrollu;
13. `_DragState`, target frame i `after` nadal należą do klasy;
14. trwały zapis kategorii i komponentów pozostaje bez zmian;
15. `launcher_tile_order.py` pozostaje jedynym miejscem czystej zmiany kolejności;
16. entrypoint i MRO pozostają bez zmian.

## 6. Allowlista implementacyjna

Dozwolone pliki:

- `cursor-api/giclee_app/launcher_drag_geometry.py` — nowy;
- `cursor-api/giclee_app/dragdrop_category_launcher.py` — wyłącznie delegacja geometrii;
- `cursor-api/tests/test_launcher_drag_geometry.py` — nowy;
- `cursor-api/giclee_app/docs/launcher.md` — krótki wpis LC-3D;
- ten kontrakt — zmiana statusu po implementacji.

Nie są dozwolone zmiany w:

- `launcher_tile_order.py`;
- layout/storage i formacie JSON;
- rendererze, gridzie i nawigacji;
- shortcut controllerach i adapterach;
- `launcher.py` i entrypointach;
- Studio;
- komponentach;
- workflowach CI;
- danych użytkownika;
- plikach startowych i ZIP-ie;
- Shopify, deployu i migracjach.

## 7. Focused tests

Nowy focused suite musi potwierdzić:

1. threshold poniżej, dokładnie na i powyżej `8 px`;
2. ujemny threshold zgłasza `ValueError`;
3. prostokąt ma poprawne right/bottom/center;
4. granice `point_inside` są zgodne z dotychczasowym kodem;
5. `drop_after` rozstrzyga góra/dół poza pasem `0.22`;
6. `drop_after` rozstrzyga lewa/prawa w pasie środkowym;
7. wysokość `0` nie powoduje dzielenia ani zmiany starego kontraktu;
8. nearest zwraca właściwy indeks;
9. remis nearest zachowuje pierwszy element;
10. empty nearest zwraca `None`;
11. funkcje nie mutują wejść;
12. moduł nie importuje Tk, launchera, komponentów, layoutu ani Studio;
13. `_on_tile_motion()` deleguje próg, zachowując side effects;
14. trzy istniejące wrappery delegują do geometrii;
15. fallback `_find_drop_target()` zachowuje kolejność kandydatów i mapowanie indeksu na frame;
16. błędy geometrii widgetu pozostają fail-closed;
17. `launcher_tile_order.py` i jego testy pozostają bez zmian.

Minimalny focused regression set:

- `tests/test_launcher_drag_geometry.py`;
- `tests/test_launcher_tile_order.py`;
- `tests/test_launcher_composition.py`;
- `tests/test_launcher_category_renderer.py`;
- `tests/test_launcher_grid_layout.py`;
- `tests/test_launcher_tk_shortcut_bindings.py`;
- `tests/test_giclee_app_packaging.py`.

Po focused PASS obowiązują:

- `git diff --check`;
- twardy scope guard;
- Hermetic Stage 2;
- Tk GUI smoke;
- full baseline z mirrorem i `VerifyOnly`;
- JUnit i runtime-write inventory;
- exact-head review przed merge.

## 8. Manual smoke

Manualny Windows smoke powinien potwierdzić:

1. klik kafelka nadal uruchamia akcję;
2. ruch poniżej 8 px pozostaje kliknięciem;
3. drag kategorii działa przed/za celem;
4. drag komponentu działa przed/za celem;
5. pionowe i poziome upuszczenia zachowują dotychczasową intuicję;
6. przeciąganie wewnątrz źródła nie zmienia kolejności;
7. upuszczenie poza canvas nie zmienia kolejności;
8. auto-scroll działa przy górnej i dolnej krawędzi;
9. wizualne bordery i cursor wracają do stanu normalnego;
10. kolejność pozostaje po restarcie launchera;
11. skróty, nawigacja i inline launch pozostają bez regresji.

## 9. Rollback

LC-3D nie zmienia danych ani formatów. Rollback to revert pojedynczego commitu implementacyjnego. Nie wymaga migracji ani czyszczenia AppData.

## 10. Kryteria ukończenia

LC-3D jest ukończone, gdy:

- czysta geometria nie importuje Tk ani aplikacji;
- klasa nadal posiada stan, eventy i side effects;
- finalny diff mieści się w pięciu allowlistowanych plikach;
- focused suite jest zielony;
- Hermetic, Tk GUI, mirror/VerifyOnly i full baseline są zielone na tym samym exact headzie;
- artifact ma 0 failures/errors;
- inventory ma 0 parse errors i 0 findings;
- branch ma `behind_by=0`;
- review threads są puste;
- merge używa expected exact head SHA.

## 11. Kolejny krok

Po LC-3D wymagany jest fresh review dla kolejnego pakietu DnD. Możliwe granice, jeszcze nieautoryzowane implementacyjnie:

- czysty model przejść stanu gestu;
- adapter wizualnego feedbacku i auto-scroll;
- persistence adapter kategorii/komponentów;
- finalny `DragDropController` dopiero po ustabilizowaniu poprzednich granic.
