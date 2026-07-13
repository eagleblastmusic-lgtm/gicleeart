# Blog preview cache outside the checkout

`Komponenty/blog/preview.py` generates a disposable multilingual HTML preview.
The file is runtime cache, not source code, and must not be written next to the
component implementation.

## Runtime contract

- new output:
  `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/blog/data/preview.html`,
- the historical `Komponenty/blog/data/preview.html` path is never modified,
- `_PREVIEW_FILE` remains an explicit override point for tests and controlled callers,
- normal writes use `giclee_app.app_paths.cache_path`,
- replacement is atomic through `atomic_write_text`,
- `build_preview_html()` and `open_preview_in_browser()` return/use the resolved
  external path.

No automatic copy or deletion of a historical preview is needed because the file
is fully regenerable.

## Tests

`tests/test_blog_preview_appdata_cache.py` verifies:

1. Local AppData output and preservation of a legacy file,
2. atomic replacement and Unicode content,
3. compatibility of an explicit `_PREVIEW_FILE` override,
4. browser opening of the external file URI,
5. removal of `Komponenty/blog/preview.py` from runtime-write inventory findings.
