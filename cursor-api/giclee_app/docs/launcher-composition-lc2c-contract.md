# ETAP 4B / LC-2C — Launcher Tile Grid Placement

**Status:** LC-2C implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `d85cdfb08138a6baaca20e8d626e68bed9cbe011`  
**Data weryfikacji:** 2026-07-15

## 1. Kontekst po LC-2B

LC-2B wydzielił callback-driven renderer ekranów kategorii do `giclee_app/category_renderer.py`. Po tym podziale istnieją dwa realne i identyczne konsumery placementu kafelków:

1. indeks kategorii;
2. ekran komponentów aktywnej kategorii.

Oba wykonują obecnie:

```python
row, column = divmod(index, config.columns)
tile.grid(
    row=row + 1,
    column=column,
    padx=config.tile_pad_x,
    pady=config.tile_pad_y,
    sticky="",
)
```

To jest wystarczająca granica do wydzielenia małego kontraktu siatki. Nie uzasadnia jednak frameworka layoutu ani migracji innych ekranów.

## 2. Sprawdzone istniejące rozwiązanie

Repozytorium ma `Komponenty/_shared/tile_grid.py`, ale jest ono przeznaczone dla inline views komponentów (`blog`, `socialmedia`, `zadania`) i ma inny zakres odpowiedzialności.

LC-2C nie może uzależnić composition root launchera od warstwy `Komponenty._shared`, ponieważ:

- launcher ma być możliwy do importu niezależnie od konkretnych komponentów;
- istniejący helper jest kontraktem UI komponentów, nie klasycznego launchera;
- LC-2C nie zmienia ustawień ani formatu danych siatki;
- nie wolno scalać dwóch semantycznie różnych systemów tylko z powodu podobnej nazwy.

Nowa granica pozostaje w `giclee_app`.

## 3. Cel LC-2C

Wydzielić:

- walidację liczby kolumn i indeksu;
- obliczenie `row` / `column`;
- stały `row_offset` nagłówka;
- parametry `padx`, `pady`, `sticky`;
- pojedyncze, testowalne wywołanie `widget.grid(...)`.

Nie zmieniać:

- fabryk kafelków;
- typów widgetów;
- kolejności danych;
- DnD i przechowywania realnych `tk.Frame`;
- liczby kolumn, offsetu, paddingów ani `sticky`;
- rendererów nagłówków i pustych stanów.

## 4. Zamrożony projekt

Nowy moduł:

```text
cursor-api/giclee_app/launcher_grid_layout.py
```

Minimalny kontrakt:

```python
from dataclasses import dataclass
from typing import Protocol


class GridWidget(Protocol):
    def grid(self, **kwargs: object) -> object:
        ...


@dataclass(frozen=True)
class TileGridSpec:
    columns: int
    row_offset: int = 0
    padx: int = 0
    pady: int = 0
    sticky: str = ""


@dataclass(frozen=True)
class TileGridSlot:
    row: int
    column: int
    padx: int
    pady: int
    sticky: str

    def grid_kwargs(self) -> dict[str, object]:
        ...


def resolve_tile_grid_slot(index: int, spec: TileGridSpec) -> TileGridSlot:
    ...


def place_tile(widget: GridWidget, index: int, spec: TileGridSpec) -> TileGridSlot:
    ...
```

Dopuszczalne są równoważne nazwy, jeśli zachowane zostaną własności poniżej.

## 5. Własności kontraktu

- moduł nie importuje `tkinter`, CustomTkinter, launchera, rendererów ani komponentów;
- `TileGridSpec` i `TileGridSlot` są niemutowalne;
- `columns <= 0` powoduje `ValueError`;
- `index < 0` powoduje `ValueError`;
- `row_offset` może być zerowy lub dodatni; wartość ujemna powoduje `ValueError`;
- `resolve_tile_grid_slot()` jest czyste i bez I/O;
- `place_tile()` wykonuje dokładnie jedno `grid()` z danymi slotu i zwraca slot do diagnostyki/testów;
- obecny launcher używa `row_offset=1`;
- obecny launcher zachowuje `columns=3`, aktualne paddingi i `sticky=""` przez `CategoryRendererConfig`;
- funkcje renderera nadal najpierw wywołują właściwy builder hook, a dopiero potem `place_tile()`.

## 6. Integracja z `category_renderer.py`

`CategoryRendererConfig` pozostaje publicznym kontraktem renderera. Może otrzymać metodę:

```python
def tile_grid_spec(self, *, row_offset: int = 1) -> TileGridSpec:
    ...
```

albo renderer może lokalnie zbudować `TileGridSpec`. Preferowana jest metoda configu, jeśli eliminuje powielanie bez wprowadzania dodatkowego stanu.

Oba konsumery:

- `render_category_index()`;
- `render_category_components()`

mają używać jednego specu i `place_tile()`.

## 7. Allowlista

Kod:

- nowy `cursor-api/giclee_app/launcher_grid_layout.py`;
- `cursor-api/giclee_app/category_renderer.py`.

Testy i dokumentacja:

- nowy `cursor-api/tests/test_launcher_grid_layout.py`;
- rozszerzenie `cursor-api/tests/test_launcher_category_renderer.py` tylko jeśli wymaga tego integracja;
- `cursor-api/giclee_app/docs/launcher.md`;
- ten kontrakt.

Poza allowlistą:

- `category_launcher.py`;
- `category_navigation.py`;
- `launcher.py`;
- Styled / Options / DragDrop;
- `launcher_layout.py`;
- `Komponenty/_shared/tile_grid.py`;
- Studio;
- workflow CI;
- pliki startowe.

## 8. Testy

Focused suite musi potwierdzić:

1. sloty dla indeksów `0`, `2`, `3`, `5` przy trzech kolumnach i `row_offset=1`;
2. przeniesienie `padx`, `pady`, `sticky` bez modyfikacji;
3. błędy dla ujemnego indeksu, niepoprawnej liczby kolumn i ujemnego offsetu;
4. niemutowalność specu i slotu;
5. `place_tile()` wywołuje `grid()` dokładnie raz i zwraca ten sam logiczny slot;
6. nowy moduł nie importuje Tk/UI/Komponenty;
7. oba rendery używają `place_tile()`;
8. builder hook jest nadal wywoływany przed placementem;
9. istniejące testy renderera zachowują oczekiwane `grid_kwargs` 1:1;
10. focused suite LC-2A, LC-2B, composition root, DnD-order i skrótów pozostaje zielony.

Po focused PASS obowiązują:

- `git diff --check`;
- Stage 2 Hermetic;
- Tk GUI smoke;
- full baseline;
- runtime-write inventory.

## 9. Manual smoke

Ponieważ LC-2C nie zmienia widgetów ani event bindings, canonical Tk GUI CI jest podstawowym dowodem. Należy zachować:

- trzy kolumny;
- pierwszy rząd kafelków pod nagłówkiem (`row=1`);
- identyczne odstępy;
- identyczne pozycje po wejściu do kategorii;
- DnD kategorii i komponentów;
- zwykły klik po DnD;
- powrót do indeksu;
- widoki inline, subprocess i URL bez zmian.

## 10. Rollback i ukończenie

Brak formatu danych, I/O i migracji. Rollback to revert pojedynczego commitu.

LC-2C jest ukończony, gdy:

- finalny diff mieści się w allowliście;
- helper ma dwóch realnych konsumentów;
- zachowanie placementu jest 1:1;
- DnD nadal otrzymuje i przechowuje rzeczywiste ramki utworzone przez buildery;
- focused i pełna brama Stage 2 są zielone;
- runtime-write inventory nie ma nowych findings;
- `behind_by=0`, review threads=0;
- brak Shopify mutation, deployu, ZIP-a i pracy nad plikami startowymi.
