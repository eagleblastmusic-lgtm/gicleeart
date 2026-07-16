# Tracked large-file policy

Git history is permanent operational data. Large generated files, exports, caches, videos, archives, model assets, and runtime backups must not be added to normal Git history by accident.

## Guard

The repository test suite runs:

```text
tools/audit_tracked_file_sizes.py
```

The current blocking threshold is **25 MiB per tracked file**. Files represented by a valid Git LFS pointer are recognized separately.

The audit uses `git ls-files`, so ignored and untracked local runtime data are outside its scope. It does not read credentials, external application data, or files outside the repository.

## Before adding a large asset

1. Confirm that the file is a durable source asset rather than generated output.
2. Prefer deterministic generation or an external artifact store when appropriate.
3. Decide explicitly whether Git LFS is required.
4. Add or update `.gitattributes` only in a dedicated reviewed change.
5. Verify clone, CI, packaging, and deployment implications.
6. Never solve an existing history problem through an unreviewed force-push or history rewrite.

## Existing history

A newly added guard prevents future regressions; it does not remove objects already present in Git history. Any history cleanup requires a separate backup, impact inventory, credential review, branch/tag plan, and explicit destructive-action approval.
