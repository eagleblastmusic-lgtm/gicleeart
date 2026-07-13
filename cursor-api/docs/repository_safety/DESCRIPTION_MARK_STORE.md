# Description mark store

## Purpose

`Komponenty/dodajobraz/description_update.py` keeps several small JSON files with local workflow marks, including:

- description updated / PL pending;
- title updated;
- GPT / Sonnet translation source;
- description from image;
- do tłumaczenia;
- bez 1–6.

These files are mutable user state. They are not source code and normal writes must not target the repository checkout.

## Runtime location

Normal writes use Local AppData through `giclee_app.app_paths.data_path`:

```text
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\dodajobraz\data\<filename>.json
```

The historical `Komponenty/dodajobraz/data/<filename>.json` path remains a read-only fallback when no external file exists.

## Boundary contract

Mark helpers receive the **name of a module file constant**, not a `Path` derived from the source checkout.

At call time the resolver:

1. validates the constant name;
2. reads its current module value;
3. preserves a monkeypatched explicit path when present;
4. otherwise resolves external-first read or Local AppData write;
5. writes complete JSON state atomically.

Resolving the constant at call time is required for compatibility with existing tests and tools that monkeypatch `_DESCRIPTION_*_FILE` or `_TITLE_UPDATE_MARKS_FILE`.

## Safety guarantees

- no normal write to the source checkout;
- legacy files are not deleted, moved or modified;
- external files shadow legacy files after the first write;
- JSON payload formats and mark semantics remain unchanged;
- temporary atomic-write files are cleaned up;
- runtime-write inventory must report no finding for `description_update.py`.
