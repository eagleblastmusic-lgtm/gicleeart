# Social Media cycle directory store

## Purpose

`Komponenty/socialmedia/cykl/storage.py` owns two writable directory boundaries:

- the cycle runtime-data directory;
- the cycle image-library directory.

Mutable cycle state and images belong to the user profile, not to the source checkout.

## Runtime locations

Normal writes use Local AppData through `giclee_app.app_paths.data_path`:

```text
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\socialmedia\data\cykl\
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\socialmedia\data\cykl\Obrazy\
```

Configuration and Meta credentials continue to use their existing Roaming AppData paths. Historical source-tree directories remain read-only fallbacks.

## Explicit override contract

Tests and controlled tools may replace:

- `_DATA_DIR`;
- `IMAGES_DIR`.

The directory resolver accepts only the closed public keys `DATA_DIR` and `IMAGES_DIR`. At each call it:

1. validates the key;
2. reads the current monkeypatched directory constant;
3. reads the current `_LEGACY_DATA_DIR`;
4. determines whether an explicit override is active;
5. creates that override directory only for a write request;
6. otherwise delegates to the normal external-first AppData boundary.

This avoids passing a path derived from the source checkout directly to `mkdir()` while preserving all compatibility overrides.

## Compatibility

- queue, generation state, Meta audit log, config and credentials formats are unchanged;
- image relative paths and naming are unchanged;
- external data continues to shadow legacy fallback data;
- explicit test/tool overrides remain authoritative;
- read-only calls do not create override directories;
- no automatic migration, deletion, move or overwrite of legacy content occurs.

## Safety guarantees

- no normal directory creation in the repository checkout;
- only validated explicit overrides may be created outside AppData;
- Local AppData remains the normal writable owner of cycle data and images;
- runtime-write inventory must report no finding for `Komponenty/socialmedia/cykl/storage.py`.
