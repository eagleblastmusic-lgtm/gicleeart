# Kolaż export safety

## Purpose

The Kolaż component has two distinct export flows:

1. a user export whose final path is selected in the operating-system Save dialog;
2. an application-owned default/staging export used as the dialog start directory and by the BIO upload workflow when no explicit path is supplied.

The application-owned directory must not live inside the source checkout.

## Runtime location

Normal application-owned exports use Local AppData:

```text
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\kolaz\data\exports\
```

The historical source-tree directory `Komponenty/kolaz/data/exports/` is never created, moved, deleted or overwritten by the new boundary.

## Explicit target contract

When the caller passes a `Path` to `export_collage(...)`, that exact path remains authoritative. The Kolaż GUI obtains it from `filedialog.asksaveasfilename`, so the user chooses the destination and the operating-system dialog owns overwrite confirmation.

The service does not redirect an explicit user target into AppData.

## Application-owned directory contract

`exports_dir()`:

- preserves a dynamic `_EXPORT_DIR` override for tests and controlled tools;
- otherwise resolves the writable directory through `data_path(...)`;
- creates only the explicit override or the Local AppData directory;
- never creates the legacy repository directory.

Automatic export names remain slugged and timestamped. If the generated path already exists, a deterministic `-2`, `-3`, and so on suffix is selected instead of silently overwriting it.

## Shopify boundary

The BIO upload call and its confirmation flow are unchanged. This stage only changes where the temporary application-owned collage is written before the existing upload function receives it.

No Shopify mutation is performed by tests or migration code.

## Compatibility and safety

- supported formats remain JPEG, WebP and PNG;
- quality parameters are unchanged;
- explicit paths are unchanged;
- `_EXPORT_DIR` test/tool overrides remain authoritative;
- no automatic data migration occurs;
- no legacy export is removed;
- runtime-write inventory must report no finding for `Komponenty/kolaz/service.py`.
