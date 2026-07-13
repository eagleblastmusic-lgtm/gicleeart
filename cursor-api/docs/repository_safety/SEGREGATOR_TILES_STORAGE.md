# Segregator Plików tile configuration outside the checkout

`Komponenty/segregatorplikow/storage.py` stores user-defined destination tiles.
This is mutable user configuration and must not be written next to the component
source code.

## Runtime contract

- new writes target:
  `%APPDATA%/GicleeArt/GicleeApp/config/Komponenty/segregatorplikow/tiles.json`,
- normal resolution uses `giclee_app.app_paths.config_path`,
- external configuration takes precedence over the historical source-tree file,
- legacy `Komponenty/segregatorplikow/data/tiles.json` is a read-only fallback,
- reading does not create directories or migrate data,
- saving uses `atomic_write_text`,
- no automatic copy, deletion or mutation of the legacy file occurs,
- `TILES_FILE` remains an explicit override point for controlled callers and tests.

The first successful save after reading legacy configuration writes the complete
current state to Roaming AppData. The legacy file remains untouched.

## Tests

`tests/test_segregator_tiles_appdata_storage.py` verifies:

1. external-first reads,
2. read-only legacy fallback without read side effects,
3. atomic Unicode writes to Roaming AppData,
4. preservation of the legacy file,
5. compatibility of an explicit `TILES_FILE` override,
6. safe handling of missing or invalid JSON,
7. removal of `Komponenty/segregatorplikow/storage.py` from runtime-write findings.
