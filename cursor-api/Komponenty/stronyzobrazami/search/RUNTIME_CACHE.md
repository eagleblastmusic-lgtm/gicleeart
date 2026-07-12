# Runtime cache wyszukiwania obrazów

Moduły `wikidata_artists.py` i `fng_local.py` przechowują regenerowalne dane
wyszukiwania poza source checkoutem.

## Lokalizacje

Legacy read fallback:

- `Komponenty/stronyzobrazami/data/cache/wikidata_artist_aliases.json`,
- `Komponenty/stronyzobrazami/data/cache/fng_objects.json.gz`.

Nowy odczyt i zapis:

- `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/stronyzobrazami/data/cache/wikidata_artist_aliases.json`,
- `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/stronyzobrazami/data/cache/fng_objects.json.gz`.

Pełna ścieżka względna jest zachowana celowo, aby runtime był zgodny z
copy-only plannerem `tools.repository_safety migration`.

## Kontrakt

- external cache ma pierwszeństwo przed legacy,
- legacy pozostaje read-only fallbackiem,
- brak automatycznego kopiowania lub usuwania legacy plików,
- cache Wikidata jest zapisywany przez `atomic_write_text`,
- cache FNG jest zapisywany przez `atomic_write_bytes`,
- istniejące stałe `CACHE_DIR`, `CACHE_FILE` i `FNG_OBJECTS_GZ` pozostają
  kompatybilnymi punktami podmiany,
- testy nie wykonują live requestów do Wikidata ani Finnish National Gallery.

FNG może ponownie wykorzystać duży legacy cache bez kopiowania. Nowy download
zawsze trafia do Local AppData. Cache aliasów Wikidata ładuje dane external-first
i zachowuje pamięciowe mapy `_qid_labels` / `_query_labels`.

## Testy

`tests/test_search_cache_appdata.py` obejmuje:

- external-first i legacy fallback,
- atomowe zapisy,
- zachowanie legacy bytes,
- kompatybilne override’y,
- brak sieci przy istniejącym cache,
- zapis i odczyt skompresowanego FNG JSON,
- brak findings obu modułów w runtime-write inventory.
