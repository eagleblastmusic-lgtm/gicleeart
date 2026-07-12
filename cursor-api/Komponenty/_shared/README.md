# Wspólna warstwa komponentów

Folder `Komponenty/_shared` zawiera współdzielone helpery używane przez komponenty
GicleeApp. Nie jest samodzielnym komponentem i nie ma własnego `component.json`.

## Ustawienia kafelków inline

`tile_grid.py` udostępnia:

- `TileSpec`,
- `InlineTileView`,
- `load_settings(component_dir)`,
- `save_settings(component_dir, data)`.

Kontrakt persystencji ustawień:

- legacy read: `Komponenty/<component>/settings.json`,
- nowy odczyt i zapis:
  `%APPDATA%/GicleeArt/GicleeApp/config/Komponenty/<component>/settings.json`,
- plik zewnętrzny ma pierwszeństwo przed legacy,
- legacy jest tylko fallbackiem odczytu,
- każdy nowy zapis jest wykonywany atomowo przez
  `giclee_app.app_paths.atomic_write_text`,
- katalog docelowy jest tworzony automatycznie,
- błędy zapisu są zgłaszane wywołującemu.

Klucz komponentu jest wyznaczany względem najbliższego nadrzędnego katalogu
`Komponenty`. Nietypowe ścieżki korzystają z bezpiecznego, stabilnego fallbacku
opartego na nazwie katalogu. Segmenty absolutne i `..` nie są przekazywane do
ścieżki runtime.

Aktualni konsumenci `InlineTileView`:

- `Komponenty/obrazy/view.py`,
- `Komponenty/cenyMarketing/view.py`,
- `Komponenty/ksiegowosc/view.py`.

Testy kontraktu: `tests/test_tile_grid_appdata_settings.py`.

## Cache kursów walut

`fx_rates.py` pobiera kursy z publicznego API NBP i przechowuje cache poza
source checkoutem.

Kontrakt persystencji:

- legacy read:
  `Komponenty/_shared/data/fx_cache.json`,
- nowy odczyt i zapis:
  `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/_shared/data/fx_cache.json`,
- plik zewnętrzny ma pierwszeństwo,
- legacy pozostaje tylko fallbackiem odczytu,
- zapis korzysta z `cache_path(...)` oraz `atomic_write_text(...)`,
- ręczny kurs, TTL i fallback sieciowy zachowują dotychczasowy kontrakt,
- `_DATA_DIR` i `_CACHE_FILE` pozostają punktami podmiany dla starszych testów
  oraz jawnych callerów.

Testy kontraktu: `tests/test_fx_rates_appdata_cache.py`.

Pełny indeks rozwiązań:
[`docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`](../../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md).
