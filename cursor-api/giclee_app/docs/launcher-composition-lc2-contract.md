# ETAP 4B / LC-2 — Category Navigator and Tile Grid Boundaries

**Status:** LC-2A implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `14e76263602ac08cd098e4537f8f9ebf09176ff2`  
**Data weryfikacji:** 2026-07-15

## 1. Cel

Kontynuować refaktor klasycznego launchera po LC-1 bez zmiany zachowania użytkowego. LC-2 ma rozdzielić:

1. decyzję **jaki ekran kategorii powinien być aktywny**;
2. budowanie widgetów Tk dla indeksu kategorii i listy komponentów;
3. rozmieszczenie kafelków w siatce;
4. warstwy interakcji dziedziczone przez styl, skróty i drag-and-drop.

Pełne rozdzielenie nie może nastąpić w jednym pakiecie, ponieważ aktualne klasy potomne wykorzystują konkretne hooki renderera.

## 2. Zweryfikowany stan wejściowy

### 2.1 `CategoryGicleeApp._render_tiles()` ma cztery odpowiedzialności

Metoda w `category_launcher.py` obecnie:

- czyści istniejące widgety i konfigurację hover;
- wywołuje `resolve_sections(...)`;
- waliduje `_active_section` i wybiera ekran;
- wywołuje renderer pustego stanu, indeksu kategorii albo komponentów kategorii.

To łączy model nawigacji, odczyt układu, przejścia stanu i Tk rendering.

### 2.2 Renderer Tk jest aktywnym kontraktem dziedziczenia

Nie wolno jeszcze przenieść lub zastąpić następujących hooków:

- `_render_tiles()`;
- `_render_category_index()`;
- `_render_category_components()`;
- `_build_category_tile()`;
- `_build_tile()`.

Powody:

- `StyledCategoryGicleeApp` zastępuje wygląd `_build_tile()`;
- `DragDropCategoryGicleeApp` rozszerza `_render_tiles()`, `_build_category_tile()` i `_build_tile()`;
- DnD przechowuje rzeczywiste ramki Tk i ponownie renderuje po zapisie kolejności;
- `OptionsCategoryGicleeApp` ponownie instaluje skróty po renderze.

Pierwszy pakiet LC-2 nie może zmieniać MRO ani tych punktów rozszerzeń.

### 2.3 Obecne zachowanie nawigacji

Należy zachować dokładnie:

- brak wykrytych komponentów → pusty ekran i wyzerowana aktywna kategoria;
- komponenty istnieją, ale brak widocznych sekcji → pusty ekran i wyzerowana aktywna kategoria;
- brak aktywnej kategorii → indeks kategorii;
- aktywna kategoria istnieje → ekran jej komponentów;
- aktywna kategoria zniknęła lub stała się pusta → bezpieczny powrót do indeksu;
- kolejność i widoczność nadal pochodzą z `launcher_layout.resolve_sections()`;
- wejście, powrót i statusy pozostają w `CategoryGicleeApp`;
- scroll reset, fokus i tytuł okna pozostają bez zmian.

## 3. Podział LC-2

### LC-2A — Pure Category Navigation Model — **pakiet implementacyjny teraz**

Wydzielić czysty, niezależny od Tk moduł, który na podstawie aktualnego katalogu komponentów, layoutu i żądanej aktywnej kategorii zwraca jednoznaczny plan ekranu.

Plan ma rozróżniać:

- `no_components`;
- `no_visible_sections`;
- `category_index`;
- `category_components`.

Plan ma zawierać:

- znormalizowaną aktywną kategorię (`str | None`);
- uporządkowane sekcje;
- komponenty aktywnej kategorii;
- stabilną mapę tytuł → komponenty, jeżeli jest potrzebna przez konsumenta.

### LC-2B — Tk Category Renderer Boundary — **później, po fresh review**

Dopiero po stabilizacji LC-2A można rozważyć wydzielenie widgetów indeksu i nagłówka kategorii. Musi to zachować hooki dla Styled i DnD.

### LC-2C — Tile Grid Placement Boundary — **później, po fresh review**

Dopiero osobny pakiet może ujednolicić rozmieszczenie kafelków i konfigurację kolumn. Nie należy tworzyć abstrakcji tylko wokół pojedynczego `divmod`; granica musi mieć co najmniej dwóch realnych konsumentów i zachować row offset, paddingi oraz trzy kolumny.

## 4. Zamrożony projekt LC-2A

Nowy moduł:

```text
cursor-api/giclee_app/category_navigation.py
```

Minimalny kontrakt:

```python
class CategoryViewKind(str, Enum):
    NO_COMPONENTS = "no_components"
    NO_VISIBLE_SECTIONS = "no_visible_sections"
    CATEGORY_INDEX = "category_index"
    CATEGORY_COMPONENTS = "category_components"


@dataclass(frozen=True)
class CategoryNavigationPlan:
    kind: CategoryViewKind
    active_section: str | None
    sections: tuple[tuple[str, tuple[Component, ...]], ...]
    active_components: tuple[Component, ...]


def resolve_category_navigation(
    all_components: Sequence[Component],
    layout: LauncherLayout,
    *,
    normally_visible: set[str],
    active_section: str | None,
) -> CategoryNavigationPlan:
    ...
```

Dopuszczalna jest równoważna nazwa typu lub funkcji, jeżeli zachowuje wszystkie poniższe własności.

### Własności

- funkcja nie importuje `tkinter`;
- nie odczytuje ani nie zapisuje plików;
- nie mutuje layoutu, komponentów ani wejściowej kolekcji;
- deleguje kolejność i widoczność do istniejącego `resolve_sections()`;
- wynik używa niemutowalnych kolekcji;
- nieważna aktywna sekcja normalizuje się do `None` i `CATEGORY_INDEX`;
- `CategoryGicleeApp._render_tiles()` staje się konsumentem planu, ale nadal odpowiada za widgety, tekst pustych stanów i przejścia UI.

## 5. Allowlista LC-2A

Kod:

- nowy `cursor-api/giclee_app/category_navigation.py`;
- `cursor-api/giclee_app/category_launcher.py`.

Testy i dokumentacja:

- nowy `cursor-api/tests/test_launcher_category_navigation_model.py`;
- istniejący `cursor-api/tests/test_launcher_category_navigation.py` tylko jeśli wymagany jest kompatybilny import;
- `cursor-api/giclee_app/docs/launcher.md`;
- ten kontrakt.

Poza allowlistą:

- `launcher.py`;
- `styled_category_launcher.py`;
- `options_category_launcher.py`;
- `dragdrop_category_launcher.py`;
- `launcher_layout.py`;
- Studio Preview i `launcher_studio.py`;
- wszystkie `Komponenty/*`;
- workflow CI;
- pliki startowe.

## 6. Testy LC-2A

Nowy focused suite musi potwierdzić:

1. brak komponentów → `NO_COMPONENTS`, `active_section=None`;
2. komponenty istnieją, brak widocznych sekcji → `NO_VISIBLE_SECTIONS`;
3. brak aktywnej sekcji → `CATEGORY_INDEX`;
4. poprawna aktywna sekcja → `CATEGORY_COMPONENTS` i właściwa niemutowalna lista komponentów;
5. nieważna lub już niewidoczna sekcja → `CATEGORY_INDEX`, `active_section=None`;
6. kolejność sekcji i komponentów odpowiada `resolve_sections()`;
7. wejściowy layout i listy nie są mutowane;
8. nowy moduł nie importuje Tk ani modułów UI;
9. `_render_tiles()` używa resolvera, ale zachowuje istniejące komunikaty pustych stanów i hooki rendererów;
10. dotychczasowe testy kategorii, layoutu, DnD, skrótów i composition root pozostają zielone.

Focused regression set:

- `tests/test_launcher_category_navigation_model.py`;
- `tests/test_launcher_category_navigation.py`;
- `tests/test_launcher_composition.py`;
- `tests/test_launcher_tile_order.py`;
- `tests/test_launcher_shortcuts.py`;
- `tests/test_launcher_shortcuts_config.py`;
- testy `launcher_layout` znalezione podczas implementacji;
- `tests/test_studio_imports.py`.

Po focused PASS obowiązują `git diff --check`, Stage 2 Hermetic, Tk GUI smoke i full baseline.

## 7. Manual smoke LC-2A

Na Windows należy sprawdzić:

- start `python -m giclee_app`;
- indeks kategorii i liczniki;
- wejście do każdej kategorii i powrót przyciskiem, `Esc`, `Backspace`, `Alt+Left`;
- ukrycie wszystkich komponentów kategorii i bezpieczny powrót do indeksu;
- zmianę przypisania/widoczności w Opcjach;
- DnD kategorii i komponentów z zachowaniem kolejności po restarcie;
- otwarcie komponentu inline, subprocess i URL;
- brak regresji `python -m giclee_app.studio_preview`.

Canonical Windows Tk CI pozostaje automatycznym dowodem runtime; osobny manual smoke użytkownika nie jest warunkiem automatycznego merge, o ile diff nie zmienia widgetów ani event bindings.

## 8. Rollback i kryteria ukończenia

LC-2A nie zmienia danych ani formatów konfiguracji. Rollback to revert pojedynczego commitu implementacyjnego.

Pakiet jest gotowy, gdy:

- finalny diff mieści się w allowliście;
- model jest czysty i niemutowalny;
- renderer Tk nadal posiada dotychczasowe hooki;
- MRO i entrypoint pozostają niezmienione;
- focused i pełna brama Stage 2 są zielone;
- runtime-write inventory pozostaje bez nowych findings;
- `behind_by=0`, review threads=0;
- brak Shopify mutation, deployu, migracji, ZIP-a i pracy nad plikami startowymi.
