# ETAP 4B / LC-2B — Callback-driven Category Renderer

**Status:** LC-2B implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `cf90d38dc13ae14807220cd9930ca3522be41c1c`  
**Data weryfikacji:** 2026-07-15

## 1. Kontekst po LC-2A

LC-2A wydzielił czysty model trasy do `category_navigation.py`. `CategoryGicleeApp._render_tiles()` pobiera teraz niemutowalny plan, lecz trzy kolejne metody nadal łączą orchestration klasy z bezpośrednim konstruowaniem widgetów Tk:

- `_render_empty()`;
- `_render_category_index()`;
- `_render_category_components()`.

Jednocześnie nazwy tych metod oraz hooki `_build_category_tile()` i `_build_tile()` są aktywnym kontraktem dziedziczenia. `OptionsCategoryGicleeApp` i `DragDropCategoryGicleeApp` wykonują działania po `_render_tiles()`, a DnD rozszerza budowę obu typów kafelków.

## 2. Decyzja

LC-2B wydziela **implementację Tk renderera**, ale nie usuwa ani nie zmienia istniejących metod klasy.

Nowy moduł:

```text
cursor-api/giclee_app/category_renderer.py
```

`CategoryGicleeApp` zachowuje metody `_render_empty()`, `_render_category_index()` i `_render_category_components()` jako cienkie wrappery przekazujące jawne zależności do funkcji renderera.

## 3. Dlaczego callback-driven

Renderer nie może importować `category_launcher.py`, ponieważ utworzyłoby to cykl. Nie powinien także otrzymywać całego obiektu aplikacji i wywoływać prywatnych metod przez nieformalny duck typing.

Funkcje otrzymują jawnie:

- `root` i `parent` Tk;
- dane sekcji lub komponentów;
- callback ustawienia podtytułu;
- callback budowy kafelka kategorii;
- callback budowy kafelka komponentu;
- callback powrotu do indeksu;
- funkcje prezentacyjne `display_title` i `count_text`;
- stałą konfigurację tytułu, wersji, liczby kolumn i paddingów.

Dzięki temu:

- Styled nadal dostarcza swój `_build_tile()`;
- DnD nadal opakowuje `_build_category_tile()` oraz `_build_tile()`;
- testy mogą podmienić wyłącznie fabryki widgetów i callbacki;
- renderer nie zna launchera, layoutu, skrótów, DnD ani usług tła.

## 4. Minimalny kontrakt

Dopuszczalne równoważne nazwy, ale oczekiwany kształt to:

```python
@dataclass(frozen=True)
class CategoryRendererConfig:
    app_title: str
    version: str
    columns: int
    tile_pad_x: int
    tile_pad_y: int


def render_empty_state(
    parent: tk.Misc,
    message: str,
    *,
    columns: int,
) -> None:
    ...


def render_category_index(
    *,
    root: tk.Misc,
    parent: tk.Misc,
    sections: Sequence[tuple[str, Sequence[Component]]],
    config: CategoryRendererConfig,
    set_subtitle: Callable[[str], None],
    build_category_tile: Callable[[tk.Misc, str, int], tk.Frame],
) -> None:
    ...


def render_category_components(
    *,
    root: tk.Misc,
    parent: tk.Misc,
    title: str,
    components: Sequence[Component],
    config: CategoryRendererConfig,
    set_subtitle: Callable[[str], None],
    show_category_index: Callable[[], None],
    build_component_tile: Callable[[tk.Misc, Component], tk.Frame],
    display_title: Callable[[str], str],
    count_text: Callable[[int], str],
) -> None:
    ...
```

## 5. Zachowanie do zachowania 1:1

### Empty

- ten sam `Label`;
- ten sam background, foreground, font, justify i `pady`;
- `columnspan` zgodny z liczbą kolumn;
- komunikaty nadal należą do `CategoryGicleeApp._render_tiles()`.

### Category index

- ten sam tytuł okna i podtytuł;
- ten sam intro frame, nagłówki, tekst i spacing;
- kafelki budowane wyłącznie przez przekazany `build_category_tile`;
- identyczny row offset `+1`, paddingi i liczba kolumn.

### Category components

- ten sam tytuł okna, podtytuł i display title;
- ten sam przycisk powrotu i event command;
- ten sam nagłówek oraz licznik;
- kafelki budowane wyłącznie przez przekazany `build_component_tile`;
- identyczny row offset `+1`, paddingi i liczba kolumn.

## 6. Zakres i allowlista

Kod:

- nowy `cursor-api/giclee_app/category_renderer.py`;
- `cursor-api/giclee_app/category_launcher.py`.

Testy i dokumentacja:

- nowy `cursor-api/tests/test_launcher_category_renderer.py`;
- `cursor-api/giclee_app/docs/launcher.md`;
- ten kontrakt.

Poza allowlistą:

- `category_navigation.py`;
- `launcher.py`;
- `styled_category_launcher.py`;
- `options_category_launcher.py`;
- `dragdrop_category_launcher.py`;
- `launcher_layout.py`;
- Studio;
- `Komponenty/*`;
- workflow CI;
- pliki startowe.

## 7. Testy

Focused tests mają potwierdzić:

1. renderer nie importuje `launcher`, layoutu, skrótów, DnD ani Studio;
2. config jest niemutowalny;
3. empty renderer tworzy widget z właściwym `columnspan`;
4. index ustawia tytuł/podtytuł, wywołuje hook kategorii dla każdej sekcji i zachowuje pozycje siatki;
5. components ustawia tytuł/podtytuł, buduje przycisk powrotu z właściwym callbackiem i wywołuje hook komponentu;
6. wrappery w `CategoryGicleeApp` delegują do nowego modułu;
7. `_build_category_tile()`, `_build_tile()`, `_render_tiles()` oraz metody nawigacji pozostają w klasie;
8. MRO i composition root są bez zmian;
9. focused suite kategorii, modelu, composition, DnD-order i skrótów pozostaje zielony.

Po focused PASS: `git diff --check`, Stage 2 Hermetic, Tk GUI smoke, full baseline i runtime-write inventory.

## 8. Poza LC-2B

LC-2B nie tworzy jeszcze ogólnego TileGrid. Po przeniesieniu dwóch realnych konsumentów do jednego modułu można wykonać fresh review dla LC-2C i ocenić wspólny `grid_slot` / grid config bez sztucznej abstrakcji.

Nie obejmuje także:

- zmiany stylistyki;
- zmiany widget toolkit;
- cache widgetów;
- zmiany event bindings;
- zmiany DnD;
- zmiany widoczności lub layout JSON;
- połączenia klasycznego launchera ze Studio;
- Shopify, deployu lub migracji danych.

## 9. Rollback i ukończenie

Rollback to revert pojedynczego commitu; brak formatu danych i migracji.

LC-2B jest ukończony, gdy:

- finalny diff mieści się w allowliście;
- wrappery klasy zachowują publiczny/prywatny kontrakt dziedziczenia;
- widgety i callbacki zachowują parametry 1:1;
- focused oraz pełna brama Stage 2 są zielone;
- runtime-write inventory nie ma nowych findings;
- `behind_by=0`, review threads=0;
- brak plików startowych, ZIP-a, Shopify mutation i deployu.
