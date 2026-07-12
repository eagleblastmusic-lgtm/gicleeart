# Final local repository-safety validation — 2026-07-11

> Sanitized checkpoint for the final copy-free Windows preflight. No private values, file contents or local hashes are reproduced here.

## Tool and source

- Tool checkout head: `9d67cf3599ac2bc465535f957315b1fe2aa52757`
- Canonical scan root: `C:\Strona\pusty\cursor-api`
- Source Git SHA reported by snapshot: `69a796274de9b9fdee2418707d8dc356b7732e07`
- Application version: `1.54.2`
- Snapshot tree SHA-256: `d20b96bb1bcf917cfd3acf00c46450bb67e5cb8d4d67b4c41827f16a3d054aed`

## Validation result

- focused repository-safety tests: **64 PASS**;
- repository-safety package compile: **PASS**;
- local validation script: **COMPLETE**;
- no migration copy, delete, overwrite, Git mutation or deploy was executed.

## Tracked-tree audit

- tracked files: **1587**;
- blocker findings: **305**;
- warnings: **0**;
- source: **1284**;
- examples: **1**;
- backups: **216**;
- runtime: **56**;
- private: **23**;
- cache: **3**;
- secret/config: **1**;
- generated: **3**.

The non-zero audit exit remains expected before Stage 1E removes accepted prohibited paths from active tracking.

## Migration preflight

Aggregate dry-run:

- total items: **534**;
- blocked: **false**;
- errors: **0**;
- conflicts: **0**;
- duplicate sources: **0**;
- duplicate destinations: **0**;
- copied: **0**;
- verified existing destinations: **0**;
- all statuses: `planned`.

Profile split:

| Profile | Total | Tracked | Untracked |
|---|---:|---:|---:|
| `critical` | **177** | **80** | **97** |
| `archive` | **342** | **216** | **126** |
| `cache` | **15** | **3** | **12** |

Critical composition:

- private data: **112**;
- runtime data: **47**;
- runtime config: **14**;
- secret/config files: **4**.

Archive composition:

- backups: **243**;
- logs and performance reports: **99**.

Cache remains regenerable and is not approved for copy by default.

## Allowlist snapshot preflight

- included files: **1317**;
- skipped files: **8534**;
- stale staging paths: **114**, report-only;
- security/data scan blockers: **0**;
- security/data scan findings: **0**;
- intersection between included paths and migration sources: **0**;
- intersection between included paths and tracked-tree blocker paths: **0**.

This confirms that the final allowlist snapshot excludes every path currently identified as secret, private, mutable runtime/config, backup, cache or generated data.

## Gate decision

The final local copy-free preflight is **PASS**.

Stage 1E may advance only after separate explicit approval for `--profile critical --copy`. The copy operation must remain no-overwrite, source-preserving and SHA-256 verified. `archive` is a separate optional decision. `cache` remains un-copied by default.

Still forbidden without separate approval:

- migration copy;
- source deletion or move;
- tracked-file cleanup;
- merge or monorepo import;
- deploy or Shopify mutation;
- history rewrite;
- `CURRENT_APP_STATE.md` write;
- GPT ZIP generation.
