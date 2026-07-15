# ETAP 4B / LC-3F — Tk Drag Binding Adapter

**Status:** LC-3F implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `fb3f8b5e342e7da651dea86ae3fba158c693e6bb`  
**Data weryfikacji:** 2026-07-15

## 1. Cel pakietu

Wydzielić z `DragDropCategoryGicleeApp._enable_tile_drag()` wyłącznie rekursywną instalację bindingów myszy Tk dla jednego drzewa kafelka.

Pakiet nie tworzy jeszcze pełnego `DragDropController`. Nie przenosi stanu gestu, decyzji LC-3E, geometrii LC-3D, hit-testingu, feedbacku, auto-scrollu ani trwałego zapisu kolejności.

## 2. Finding z fresh review

Po LC-3D i LC-3E metoda `_enable_tile_drag()` nadal łączy dwie odpowiedzialności:

1. własność aplikacyjna kafelka:
   - zapis `_launcher_dnd_kind`;
   - zapis `_launcher_dnd_key`;
   - dodanie root tile do `_dnd_tiles`;
   - closure press z `tile`, `kind`, `key` i `activate`;
2. mechanika Tk:
   - rekursywne przejście przez `winfo_children()`;
   - best-effort `unbind("<Button-1>")`;
   - binding `"<ButtonPress-1>"`, `"<B1-Motion>"`, `"<ButtonRelease-1>"` z `add="+"`;
   - best-effort ustawienie kursora `hand2`.

Druga część jest samodzielną granicą platformową i może zostać wydzielona bez zmiany UX ani własności stanu.

## 3. Zamrożona granica

Nowy moduł:

- `cursor-api/giclee_app/launcher_tk_drag_bindings.py`

Publiczny kontrakt:

```python
DragEventCallback = Callable[[tk.Event], str | None]


def install_tile_drag_bindings(
    tile: tk.Misc,
    *,
    on_press: DragEventCallback,
    on_motion: DragEventCallback,
    on_release: DragEventCallback,
) -> None:
    ...
```

Adapter:

- nie zna `DragDropCategoryGicleeApp`;
- nie zna `_DragState`;
- nie importuje modułów aplikacyjnych ani `Komponenty`;
- nie zapisuje metadanych `_launcher_dnd_kind` / `_launcher_dnd_key`;
- nie rejestruje kafelków w `_dnd_tiles`;
- nie tworzy callbacku `activate`;
- nie interpretuje wyników eventów;
- nie modyfikuje geometrii, targetu, kolejności ani storage.

## 4. Zachowanie, które musi pozostać identyczne

### 4.1. Kolejność i zasięg

Dla root tile i każdego potomka, w bieżącej kolejności `winfo_children()`:

1. best-effort usunąć bazowy `"<Button-1>"`;
2. dodać `"<ButtonPress-1>"` z `add="+"`;
3. dodać `"<B1-Motion>"` z `add="+"`;
4. dodać `"<ButtonRelease-1>"` z `add="+"`;
5. best-effort ustawić `cursor="hand2"`;
6. przejść rekursywnie do dzieci.

Traversal ma pozostać depth-first i zachować naturalną kolejność dzieci zwróconą przez Tk.

### 4.2. Semantyka błędów

- `tk.TclError` z `unbind("<Button-1>")` jest ignorowany jak obecnie;
- `tk.TclError` z `configure(cursor="hand2")` jest ignorowany jak obecnie;
- błędy wymaganych trzech operacji `bind(...)` nie mogą być cicho maskowane;
- błąd `winfo_children()` nie może zostać automatycznie zamieniony na częściowy sukces;
- adapter nie dodaje retry, markera deduplikacji ani class bindtagu.

### 4.3. Brak deduplikacji

Obecny lifecycle buduje nowe widgety i wywołuje `_enable_tile_drag()` raz na kafelek. LC-3F nie dodaje markerów ani logiki „bind only once”, ponieważ zmieniłoby to kontrakt ponownej instalacji na istniejącym drzewie.

## 5. Odpowiedzialności pozostające w klasie

`DragDropCategoryGicleeApp` nadal:

- ustawia `_launcher_dnd_kind` i `_launcher_dnd_key` na root tile;
- dodaje root tile do `_dnd_tiles`;
- tworzy closure `on_press`, która przekazuje dokładnie:
  - event;
  - root tile;
  - `kind`;
  - `key`;
  - `activate`;
- posiada `_on_tile_press`, `_on_tile_motion`, `_on_tile_release`;
- posiada `_DragState` i jego lifecycle;
- posiada feedback source/target i root cursor `fleur`;
- posiada auto-scroll;
- posiada direct widget lookup, fallback nearest target i geometrię LC-3D;
- posiada decyzje LC-3E;
- posiada `_reorder_category()` i `_reorder_component()` oraz `save_layout()`.

Po wdrożeniu `_enable_tile_drag()` ma pozostać cienkim adapterem:

```python
setattr(tile, "_launcher_dnd_kind", kind)
setattr(tile, "_launcher_dnd_key", key)
self._dnd_tiles.append(tile)
install_tile_drag_bindings(
    tile,
    on_press=lambda event: self._on_tile_press(
        event, tile, kind, key, activate
    ),
    on_motion=self._on_tile_motion,
    on_release=self._on_tile_release,
)
```

## 6. Jawnie poza zakresem

LC-3F nie zmienia:

- `_DragState` ani jego pól;
- progu 8 px;
- ratio `0.22`;
- kolorów ramek;
- kursora root `fleur` podczas drag;
- hit-testingu i nearest fallback;
- `launcher_drag_geometry.py`;
- `launcher_drag_gesture.py`;
- `launcher_tile_order.py`;
- `launcher_layout.py` ani ścieżek runtime;
- kategorii, gridu, skrótów, ComponentLauncher, Studio i background services;
- entrypointu `python -m giclee_app`;
- Stage 2 CI;
- plików startowych, ZIP-a i Shopify.

## 7. Allowlista implementacyjna

Kod:

- nowy `cursor-api/giclee_app/launcher_tk_drag_bindings.py`;
- `cursor-api/giclee_app/dragdrop_category_launcher.py`.

Testy i dokumentacja:

- nowy `cursor-api/tests/test_launcher_tk_drag_bindings.py`;
- `cursor-api/giclee_app/docs/launcher.md`;
- ten kontrakt.

Dokładnie pięć plików. Każde rozszerzenie wymaga osobnego uzasadnienia przed edycją.

## 8. Focused tests

Nowy suite musi potwierdzić:

1. root tile i wszystkie potomki otrzymują trzy wymagane bindingi;
2. wszystkie bindingi używają `add="+"`;
3. bazowy `"<Button-1>"` jest zdejmowany przed `"<ButtonPress-1>"`;
4. traversal jest depth-first i zachowuje kolejność dzieci;
5. każdy widget dostaje best-effort `cursor="hand2"`;
6. `tk.TclError` z unbind i configure nie zatrzymuje instalacji;
7. błąd wymaganej operacji bind propaguje się;
8. callback press otrzymuje event i nadal używa root tile/kind/key/activate z closure klasy;
9. `_dnd_tiles` zawiera tylko root tile, nie dzieci;
10. metadane DnD pozostają wyłącznie na root tile;
11. moduł adaptera nie importuje aplikacji, geometrii, gestu, storage ani `Komponenty`;
12. nie pojawia się marker deduplikacji, `bind_class` ani zmiana bindtagów.

Focused regression set:

- `tests/test_launcher_tk_drag_bindings.py`;
- `tests/test_launcher_drag_gesture.py`;
- `tests/test_launcher_drag_geometry.py`;
- `tests/test_launcher_tile_order.py`;
- `tests/test_launcher_composition.py`;
- `tests/test_launcher_category_renderer.py`;
- `tests/test_launcher_grid_layout.py`;
- `tests/test_giclee_app_packaging.py`.

Dopiero po focused PASS: `git diff --check`, scope guard, Hermetic, Tk GUI smoke, mirror/`VerifyOnly`, pełny baseline, JUnit i runtime-write inventory.

## 9. Manual smoke

Na Windows po implementacji:

1. uruchomić `python -m giclee_app`;
2. kliknąć kategorię i komponent — akcja ma nastąpić dopiero na release bez drag;
3. przeciągnąć kategorię przez tekst i inne dzieci widgetu;
4. przeciągnąć komponent przez tekst i inne dzieci widgetu;
5. potwierdzić kursor `hand2` przed drag i `fleur` podczas drag;
6. potwierdzić brak podwójnej aktywacji;
7. zrestartować launcher i potwierdzić trwałość kolejności.

## 10. Rollback

LC-3F nie zmienia formatu danych ani ścieżek runtime. Rollback to zwykły revert pojedynczego commitu implementacyjnego. Nie wymaga migracji ani czyszczenia AppData.

## 11. Kryterium zakończenia

LC-3F jest zakończony, gdy:

- mechanika rekursywnych bindingów znajduje się w jednym adapterze Tk;
- `_enable_tile_drag()` pozostaje cienkim właścicielem metadanych i callbacków;
- finalny diff obejmuje dokładnie pięć allowlistowanych plików;
- focused suite, Hermetic, Tk GUI, pełny baseline i inventory są zielone na tym samym exact headzie;
- nie zmieniono zachowania click/drag, persistence ani entrypointu.
