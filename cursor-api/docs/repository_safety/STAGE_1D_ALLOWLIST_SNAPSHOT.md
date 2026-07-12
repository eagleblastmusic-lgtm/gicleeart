# Stage 1D checkpoint — allowlist snapshot and Push GicleeApp integration

Date: 2026-07-11

Repository: `eagleblastmusic-lgtm/gicleeapp`

Branch: `gpt-work/repo-safety-foundation`

## Status

**AUTOMATED INTEGRATION COMPLETE / LOCAL CANONICAL CHECKOUT VALIDATION REQUIRED**

The policy-driven snapshot engine is connected directly to the existing `Komponenty/integracjagpt/gicleeapp_push.py` workflow. The GUI continues to call the same public functions:

- `dry_run_gicleeapp_push()`
- `commit_and_push_gicleeapp()`

No parallel push path, runtime monkey patch or hidden deployment path was added.

## Implemented snapshot contract

- source files are selected through `tools.repository_safety.policy.classify_path()`;
- runtime, cache, backup, private, secret and generated paths are recorded as skipped;
- allowed files are scanned for likely secrets, PII fields and unapproved large binaries before copy;
- any source blocker prevents all copying;
- the source tree gets a deterministic SHA-256 based on relative path and file content hash;
- application version is read from `giclee_app/__init__.py`;
- source Git SHA is read from the repository containing the source root;
- approved files are copied atomically through a temporary sibling and `os.replace()`;
- protected staging files remain protected from replacement;
- the generated manifest is written to:

  `docs/repository_safety/GICLEEAPP_SNAPSHOT_MANIFEST.json`

## Manifest contract

The manifest contains:

- schema version and snapshot type;
- generation timestamp in UTC;
- source Git SHA;
- GicleeApp version;
- deterministic `cursor-api` tree SHA-256;
- included file list;
- skipped path list with policy rule and classification;
- protected path list;
- security/data scan status and findings.

The manifest is excluded from its own input tree hash. When its semantic content is unchanged, the existing timestamp and file bytes are preserved, preventing a no-op dry-run from creating a permanent Git diff.

## Push workflow gates

### Dry-run gate

`dry_run_gicleeapp_push()` now performs:

1. staging-repository and remote validation;
2. allowlist snapshot planning;
3. source security/data scan;
4. atomic copy only when the plan is clean;
5. full `git ls-files` tracked-tree audit in staging;
6. current working-tree change audit;
7. explicit commit-candidate construction.

### Commit gate

After `git pull --ff-only` and before `git add`, `commit_and_push_gicleeapp()` runs the full tracked-tree audit again. This blocks a remote fast-forward from introducing runtime/private/secret files between the dry-run and commit phases.

The existing safeguards remain:

- explicit `git add -- <paths>`;
- staged path verification;
- review-only file protection;
- no `git add -A`;
- no hidden Shopify deploy;
- starter checkpoint synchronization only after a successful push.

## CLI

Snapshot dry-run only:

```powershell
python -m tools.repository_safety snapshot `
  --source C:\Strona\pusty\cursor-api `
  --staging C:\Strona\_gicleeapp_staging `
  --json-out "$env:TEMP\gicleeapp-snapshot-plan.json"
```

Explicit standalone copy after reviewing the dry-run:

```powershell
python -m tools.repository_safety snapshot `
  --source C:\Strona\pusty\cursor-api `
  --staging C:\Strona\_gicleeapp_staging `
  --copy
```

The CLI does not commit or push anything.

## Validation

- repository safety and snapshot unit tests: **12/12 PASS** in isolated validation;
- focused integration compatibility package: **19/19 PASS** in isolated validation;
- GitHub Actions **Security / push workflow tests: PASS** after direct integration;
- existing Studio CI failure remains unchanged and belongs to Stage 2.

## Explicit boundaries

This checkpoint does not:

- delete or move source data;
- remove tracked runtime files;
- remove stale files from staging;
- call Shopify deploy;
- modify `CURRENT_APP_STATE.md`;
- merge the draft PR;
- rewrite Git history;
- generate the GPT ZIP.

The temporary `.gitignore` merge remains for compatibility and must be characterized before legacy denylist configuration is removed.

## Required local validation

From the canonical local checkout or a dedicated worktree of PR #4:

```powershell
python -m pytest `
  tests/test_gicleeapp_push.py `
  tests/test_gicleeapp_push_allowlist.py `
  tests/test_repository_safety.py `
  tests/test_repository_snapshot.py -q

python -m compileall `
  Komponenty/integracjagpt/gicleeapp_push.py `
  tools/repository_safety

python -m tools.repository_safety audit `
  --repo . `
  --json-out "$env:TEMP\gicleeapp-tracked-tree.json"

python -m tools.repository_safety migrate `
  --repo . `
  --include-untracked `
  --json-out "$env:TEMP\gicleeapp-migration-dry-run.json"

python -m tools.repository_safety snapshot `
  --source . `
  --staging C:\Strona\_gicleeapp_staging `
  --json-out "$env:TEMP\gicleeapp-snapshot-plan.json"
```

Do not use migration `--copy`, remove tracked files or include deletions in Push GicleeApp until all reports are reviewed.

## Remaining Stage 1 work

- run the real local audit and migration dry-run;
- verify destination conflicts and SHA reports;
- characterize stale staging files without deleting them;
- add first-run behavior for components whose runtime files will be removed;
- only then prepare the separately reviewed Stage 1E removal/import package.
