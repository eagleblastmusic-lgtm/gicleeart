# Second local validation instructions

Use these instructions only after fetching the latest `gpt-work/repo-safety-foundation` head.

The second run is required because the first local reports revealed path-policy gaps. The updated branch adds stricter classifications, explicit migration profiles and a PowerShell 5.1 fix.

## Update the detached validation worktree

```powershell
cd C:\Strona\_gicleeapp_staging

git fetch origin --prune

git -C C:\Strona\gicleeapp-repo-safety-validation status --short
```

The status command must return no output. Then update the detached worktree:

```powershell
git -C C:\Strona\gicleeapp-repo-safety-validation checkout --detach `
  origin/gpt-work/repo-safety-foundation

git -C C:\Strona\gicleeapp-repo-safety-validation rev-parse HEAD
```

## Run the copy-free validation

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\Strona\gicleeapp-repo-safety-validation\scripts\repository-safety-local-validation.ps1 `
  -ScanRoot C:\Strona\pusty\cursor-api `
  -StagingRoot C:\Strona\_gicleeapp_staging
```

`-ToolRoot` is no longer required on Windows PowerShell 5.1.

## Expected behavior

- focused tests run, including migration-profile tests;
- full tracked-tree audit may return a non-zero status because cleanup has not happened;
- migration runs with `--profile all` in dry-run mode;
- snapshot is dry-run only;
- reports overwrite the previous files under `%TEMP%\gicleeapp-repository-safety`;
- no data is copied, moved, overwritten or deleted;
- no Git mutation or Shopify deploy occurs.

## Required outputs

Preserve and review:

- `gicleeapp-tracked-tree.json`
- `gicleeapp-migration-dry-run.json`
- `gicleeapp-snapshot-dry-run.json`

Do not execute any `--copy` command after this run. The second reports must first be compared with the first set and divided into `critical`, `archive` and `cache` profiles.
