# Stage 1E.1 runtime paths checkpoint — 2026-07-12

> Sanitized branch checkpoint. No private values, credential contents, local file hashes, or customer data are reproduced here.

## Preconditions

- Repository safety foundation branch: `gpt-work/repo-safety-foundation`.
- Critical data copy: **177/177 copied and SHA-256 verified**.
- Critical copy source deletion: **0**.
- Archive copy: **not executed**.
- Cache copy: **not executed**.

## Stage 1E.1 scope

Branch: `gpt-work/runtime-paths-stage1e`  
Draft PR: `#5`, stacked on the repository safety foundation.

Implemented:

- central `giclee_app.app_paths` contract;
- Local AppData root for data, cache-compatible data, logs, and backups;
- Roaming AppData config root for mutable configuration;
- external-first reads;
- read-only fallback to legacy repository files;
- AppData-only writes;
- atomic file replacement;
- one-time source-preserving legacy seed for append-only stores;
- first-run behavior when neither external nor legacy data exists;
- environment overrides for isolated tests and validation.

Initial migrated stores:

- shared recent image history;
- Blog topics and articles cache;
- DNR database, settings, and exports;
- sales-document settings, database, exchange-rate cache, event log, and generated document directories.

## Test and validation contract

Automated tests cover:

- exact migration-manifest-compatible destinations;
- external-first and legacy fallback reads;
- AppData-only writes;
- atomic replacement;
- unsafe relative path rejection;
- first run without source-tree data;
- append-only legacy history preservation;
- legacy source byte preservation;
- isolated Windows runbook guardrails.

Local validation script:

`powershell -ExecutionPolicy Bypass -File scripts/stage1e-runtime-paths-local-validation.ps1`

The script uses unique `%TEMP%` roots. It contains no migration copy, source removal, Git mutation, merge, deploy, Shopify mutation, or history rewrite command.

## Current gate

Stage 1E.1 requires final CI and isolated local Windows validation before the next store lane is accepted.

Still forbidden:

- removing or moving legacy source files;
- removing paths from Git tracking;
- copying `archive` or `cache` profiles;
- merging PR #4 or PR #5;
- importing into the canonical monorepo;
- deploying or mutating Shopify;
- rewriting history;
- writing `CURRENT_APP_STATE.md`;
- generating the GPT knowledge ZIP.
