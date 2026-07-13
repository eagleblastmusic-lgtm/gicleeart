# Tytuły AI draft store

## Purpose

`Komponenty/tytulyai/storage.py` stores local work-in-progress title and description drafts:

- `title_drafts.json`;
- `description_drafts.json`.

These files contain mutable user state. They are not source code and normal writes must not target the repository checkout.

## Runtime location

Normal writes use Local AppData through `giclee_app.app_paths.data_path`:

```text
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\tytulyai\data\title_drafts.json
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\tytulyai\data\description_drafts.json
```

Historical files under `Komponenty/tytulyai/data/` remain read-only fallbacks when no external file exists.

## Boundary contract

Draft helpers receive the name of one of the two allowed runtime file constants instead of a `Path` derived from the source checkout:

- `TITLE_DRAFTS_FILE`;
- `DESCRIPTION_DRAFTS_FILE`.

At call time the resolver:

1. validates the constant against a closed mapping;
2. reads the current file constant, default path and `AppPath` value;
3. preserves an explicit monkeypatched path when present;
4. otherwise selects the external-first read path or Local AppData write path;
5. writes the complete JSON state atomically.

Resolving all values at call time preserves compatibility with tests and tools that replace the draft paths or AppData roots dynamically.

## Compatibility

- title draft JSON stays at schema version 2;
- description draft JSON stays at schema version 2;
- legacy flat description records remain readable as v1 data;
- draft model fields and sorting remain unchanged;
- no automatic migration, deletion, move or overwrite of legacy files occurs.

## Safety guarantees

- no normal write to the source checkout;
- external files shadow legacy files after the first write;
- explicit test/tool overrides remain authoritative;
- temporary atomic-write files are cleaned up;
- runtime-write inventory must report no finding for `Komponenty/tytulyai/storage.py`.
