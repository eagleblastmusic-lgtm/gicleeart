# Repository Safety Foundation

This package provides non-destructive tooling for classifying repository paths, auditing the complete tracked tree, planning copy-only migration of local data and building policy-driven GicleeApp snapshots.

## Safety boundaries

- Audit and migration dry-runs do not modify repository files.
- Migration copy never deletes source files.
- Migration copy never overwrites a different destination file.
- Snapshot copy includes only paths approved by the central policy.
- Snapshot copy blocks completely when the source scan has blockers.
- Snapshot copy preserves protected staging files.
- Snapshot writes files atomically through temporary sibling files and `os.replace()`.
- None of the CLI commands run `git add`, `git commit`, `git push`, merge or Shopify deploy.
- Reports may contain private local paths. Store them outside Git.

## Central classification

`tools/repository_safety/policy.py` defines:

- `SOURCE`
- `EXAMPLE`
- `RUNTIME`
- `CACHE`
- `BACKUP`
- `PRIVATE`
- `SECRET`
- `GENERATED`

A path outside the explicit source/example allowlist is classified by the fail-closed decision `UNCLASSIFIED_BLOCKED`.

## Full tracked-tree audit

```powershell
python -m tools.repository_safety audit `
  --repo . `
  --json-out "$env:TEMP\gicleeapp-tracked-tree.json"
```

The audit uses `git ls-files -z`, not only `git status`. It reports:

- paths whose classification cannot be tracked;
- likely secret content;
- likely customer/PII fields in JSON/JSONL/CSV/TSV;
- unapproved large binary files;
- the known accidental artifact name `10.0.0`;
- tracked paths missing from the worktree.

A blocker returns exit code 1.

## Copy-only data migration

Dry-run for tracked runtime/private files:

```powershell
python -m tools.repository_safety migrate `
  --repo . `
  --json-out "$env:TEMP\gicleeapp-migration-dry-run.json"
```

Include untracked local runtime files during discovery:

```powershell
python -m tools.repository_safety migrate `
  --repo . `
  --include-untracked `
  --json-out "$env:TEMP\gicleeapp-migration-all.json"
```

After reviewing the report, copy without deleting sources:

```powershell
python -m tools.repository_safety migrate `
  --repo . `
  --include-untracked `
  --copy `
  --json-out "$env:TEMP\gicleeapp-migration-copy.json"
```

Default target roots:

- `%LOCALAPPDATA%\GicleeArt\GicleeApp\data\`
- `%LOCALAPPDATA%\GicleeArt\GicleeApp\backups\`
- `%LOCALAPPDATA%\GicleeArt\GicleeApp\logs\`
- `%APPDATA%\GicleeArt\GicleeApp\config\`

Each source-relative path is preserved below its target bucket. The preflight computes SHA-256 and stops before copying anything when any destination contains different content.

## Allowlist-based snapshot

Dry-run:

```powershell
python -m tools.repository_safety snapshot `
  --source C:\Strona\pusty\cursor-api `
  --staging C:\Strona\_gicleeapp_staging `
  --json-out "$env:TEMP\gicleeapp-snapshot-plan.json"
```

Explicit copy after report review:

```powershell
python -m tools.repository_safety snapshot `
  --source C:\Strona\pusty\cursor-api `
  --staging C:\Strona\_gicleeapp_staging `
  --copy
```

The engine:

- selects files only through `classify_path(...).sync_allowed`;
- records every skipped path with its rule and classification;
- scans included files before copy;
- builds a deterministic tree SHA-256 from path and file content hashes;
- records the source Git SHA and application version;
- preserves review-only/protected staging files;
- writes `docs/repository_safety/GICLEEAPP_SNAPSHOT_MANIFEST.json`.

The manifest contains included/skipped/protected paths and the security/data scan result. It is regenerated and excluded from its own source tree hash.

The snapshot engine is currently independent from `Komponenty/integracjagpt/gicleeapp_push.py`. The existing Push GicleeApp GUI remains unchanged until the thin adapter receives characterization tests.

## Required local sequence

1. Checkout `gpt-work/repo-safety-foundation` in a clean local worktree.
2. Run focused tests and `compileall`.
3. Run tracked-tree audit and save the JSON report outside Git.
4. Run migration with `--include-untracked` without `--copy`.
5. Review every proposed source and destination.
6. Run snapshot dry-run against `_gicleeapp_staging`.
7. Do not use `--copy` until reports and destination roots are confirmed.
8. After an approved migration copy, compare every source/destination SHA-256.
9. Only then prepare removal of tracked runtime files in a separate reviewed commit.

## Tests

```powershell
python -m pytest tests/test_repository_safety.py tests/test_repository_snapshot.py -q
python -m compileall tools/repository_safety
```

## Not included yet

- removal of any tracked runtime file;
- first-run migrations in application components;
- automatic `.gitignore` generation from policy;
- direct integration into Push GicleeApp;
- stale-file deletion in staging;
- Git history rewrite;
- monorepo import;
- merge or deploy.
