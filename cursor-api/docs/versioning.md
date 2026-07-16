# Desktop version source contract

The canonical editable version of the desktop application lives in:

```text
giclee_app/version.py
```

`giclee_app.__version__` only re-exports that value. Do not add a second literal version assignment to `giclee_app/__init__.py`.

`package.json` must keep a literal `version` field for npm tooling, so it is treated as a synchronized mirror rather than an independent source.

## Version update workflow

1. Edit `giclee_app/version.py`.
2. From `cursor-api/`, run:

```powershell
python tools/sync_desktop_version.py
```

3. Commit both the canonical file and the synchronized `package.json` change.
4. Run the version contract tests and the normal Stage 2 CI baseline.

The synchronization tool parses the Python file with `ast`; it does not import the application or execute runtime code. Running it repeatedly is idempotent.

## Guardrails

- `giclee_app/version.py` must contain a non-empty string-literal `__version__` assignment.
- `giclee_app/__init__.py` must re-export the canonical value.
- `package.json` must match the canonical value exactly.
- Version changes do not imply a deploy, Shopify mutation, release publication, tag, or package build. Those remain separate explicit actions.
