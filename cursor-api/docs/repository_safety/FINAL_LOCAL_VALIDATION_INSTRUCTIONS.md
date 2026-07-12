# Final local repository-safety validation

Run this only after fetching the latest `gpt-work/repo-safety-foundation` head.

This is a copy-free preflight. It does not authorize or execute migration copy, deletion, Git mutation or Shopify deployment.

## Update the detached validation worktree

```powershell
cd C:\Strona\_gicleeapp_staging

git fetch origin --prune

$wt = "C:\Strona\gicleeapp-repo-safety-validation"

git -C $wt status --short
```

The status command must produce no output. Then move the detached worktree to the latest remote branch head:

```powershell
git -C $wt checkout --detach `
  origin/gpt-work/repo-safety-foundation

git -C $wt rev-parse HEAD
```

The resolved head must include code head `a6dc723fc60da7959ba110a2a614c5ff0b1566bc` or a later descendant.

## Execute the copy-free runbook

```powershell
powershell -ExecutionPolicy Bypass `
  -File "$wt\scripts\repository-safety-local-validation.ps1" `
  -ScanRoot "C:\Strona\pusty\cursor-api" `
  -StagingRoot "C:\Strona\_gicleeapp_staging"
```

Expected behavior:

- focused repository-safety tests execute;
- compileall executes;
- tracked-tree audit can return non-zero while prohibited tracked paths remain;
- migration executes with `--profile all` in dry-run mode;
- allowlist snapshot executes in dry-run mode;
- reports replace the previous files under `%TEMP%\gicleeapp-repository-safety`;
- no data is copied, moved, overwritten or deleted;
- no Git mutation or Shopify deployment occurs.

## Preserve these reports outside Git

- `gicleeapp-tracked-tree.json`
- `gicleeapp-migration-dry-run.json`
- `gicleeapp-snapshot-dry-run.json`

Do not execute a separate `--copy` command after the run. The final reports must first be reviewed for profile counts, hashes and destination conflicts.
